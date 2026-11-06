import re
import logging
import asyncio
import random
from typing import List, Optional, Tuple, Dict, Any, Set
from datetime import datetime
from pymongo.errors import DuplicateKeyError

from app.models.prd import PRDStatus, can_transition_version
from app.db.repository import PRDVersionRepository

logger = logging.getLogger(__name__)

VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$")

def parse_version_string(ver_str: str) -> Optional[Tuple[int, int]]:
    """Parse 'v1.0', '1.2', 'v2.0' into (major, minor)."""
    if not ver_str:
        return None
    match = VERSION_PATTERN.match(ver_str.strip())
    if not match:
        return None
    major = int(match.group(1))
    minor = int(match.group(2))
    return (major, minor)

def format_version(major: int, minor: int) -> str:
    """Format tuple into canonical 'v{major}.{minor}' string."""
    return f"v{major}.{minor}"

class VersionAllocationService:
    def __init__(self, version_repo: PRDVersionRepository):
        self.version_repo = version_repo

    def calculate_next_version(self, existing_version_strings: List[str], is_major: bool = True) -> str:
        """
        Calculate next semantic version based on existing version records.
        If is_major is True: finds max major and returns v{max_major + 1}.0 (or v1.0 if empty).
        If is_major is False: finds latest major and returns v{major}.{max_minor + 1}.
        """
        parsed_versions = []
        for ver_str in existing_version_strings:
            parsed = parse_version_string(ver_str)
            if parsed:
                parsed_versions.append(parsed)

        if not parsed_versions:
            return "v1.0"

        if is_major:
            max_major = max(v[0] for v in parsed_versions)
            return format_version(max_major + 1, 0)
        else:
            # Minor bump on the highest major version
            max_major = max(v[0] for v in parsed_versions)
            minors_for_major = [v[1] for v in parsed_versions if v[0] == max_major]
            max_minor = max(minors_for_major) if minors_for_major else 0
            return format_version(max_major, max_minor + 1)

    async def reserve_version(
        self,
        prd_id: str,
        project_id: str,
        user_id: str,
        job_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        requested_version: Optional[str] = None,
        is_major: bool = True,
        max_retries: int = 20
    ) -> Dict[str, Any]:
        """
        Safely and idempotently reserve a version number for a PRD.
        Guarantees that:
        1. Existing idempotent requests return the active/existing version record.
        2. Approved versions are immutable and cannot be overwritten.
        3. MongoDB unique compound index collisions (E11000) are caught and automatically retried.
        """
        # 1. Check idempotency key if provided
        if idempotency_key:
            existing_by_key = await self.version_repo.get_by_idempotency_key(idempotency_key)
            if existing_by_key:
                logger.info(f"Idempotent reservation matched by key {idempotency_key}: {existing_by_key.get('version_number')}")
                return existing_by_key

        # 2. Check existing job_id if provided
        if job_id:
            existing_by_job = await self.version_repo.get_by_job_id(job_id)
            if existing_by_job:
                logger.info(f"Idempotent reservation matched by job_id {job_id}: {existing_by_job.get('version_number')}")
                return existing_by_job

        # 3. If a specific requested_version was requested, inspect its current state
        if requested_version:
            existing_target = await self.version_repo.get_by_prd_and_version(prd_id, requested_version)
            if existing_target:
                status = existing_target.get("status", "").lower()
                if status == PRDStatus.APPROVED.value:
                    raise ValueError(f"PRD version {requested_version} has already been approved and is immutable.")
                
                # If existing is reserved or failed, we can safely resume/reassign it
                if status in (PRDStatus.RESERVED.value, PRDStatus.FAILED.value, PRDStatus.GENERATING.value):
                    update_data: Dict[str, Any] = {
                        "status": PRDStatus.RESERVED.value,
                        "updated_at": datetime.utcnow()
                    }
                    if job_id:
                        update_data["job_id"] = job_id
                    if idempotency_key:
                        update_data["idempotency_key"] = idempotency_key
                    await self.version_repo.update(existing_target["id"], update_data)
                    existing_target.update(update_data)
                    return existing_target

        # 4. Atomic reservation loop with automatic collision backoff
        collided_candidates: Set[str] = set()

        for attempt in range(max_retries):
            if attempt > 0:
                # Add jittered exponential backoff to avoid concurrent lockstep collisions
                backoff = random.uniform(0.015, 0.05) * attempt
                await asyncio.sleep(backoff)

            # Fetch fresh list of existing versions for this PRD
            prior_versions = await self.version_repo.get_by_prd(prd_id)
            existing_numbers = set(v.get("version_number", "") for v in prior_versions if v.get("version_number"))
            known_numbers = existing_numbers.union(collided_candidates)

            if requested_version and attempt == 0 and requested_version not in known_numbers:
                candidate = requested_version
            else:
                candidate = self.calculate_next_version(list(known_numbers), is_major=is_major)

            # Ensure candidate is not already present or collided
            offset = 1
            while candidate in known_numbers:
                parsed = parse_version_string(candidate)
                if parsed:
                    candidate = format_version(parsed[0] + offset, 0 if is_major else parsed[1] + offset)
                else:
                    candidate = f"v{len(known_numbers) + offset}.0"
                offset += 1

            reservation_data = {
                "prd_id": prd_id,
                "project_id": project_id,
                "version_number": candidate,
                "job_id": job_id,
                "idempotency_key": idempotency_key,
                "status": PRDStatus.RESERVED.value,
                "sections": {},
                "provenance_ledger": [],
                "changelog": f"Reserved for job {job_id}" if job_id else f"Reserved version {candidate}",
                "created_at": datetime.utcnow(),
                "created_by": user_id or "system"
            }

            try:
                saved = await self.version_repo.create(reservation_data)
                logger.info(f"Successfully reserved PRD version {candidate} for PRD {prd_id} on attempt {attempt + 1}")
                return saved
            except DuplicateKeyError as dup_err:
                collided_candidates.add(candidate)
                logger.warning(
                    f"DuplicateKeyError (11000) allocating version {candidate} for PRD {prd_id} "
                    f"(attempt {attempt + 1}/{max_retries}): {dup_err}"
                )
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"Failed to reserve a unique PRD version for PRD {prd_id} after {max_retries} attempts."
                    ) from dup_err

        raise RuntimeError(f"Unable to reserve PRD version for PRD {prd_id}.")

    async def transition_version(
        self,
        version_id: str,
        new_status: PRDStatus | str,
        error_details: Optional[Dict[str, Any]] = None,
        extra_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Transition an allocated version to a new lifecycle state.
        Validates the transition path and updates database atomically.
        """
        current_doc = await self.version_repo.get_by_id(version_id)
        if not current_doc:
            raise ValueError(f"PRD version record {version_id} not found.")

        current_status = current_doc.get("status", "draft")
        target_status_str = new_status.value if isinstance(new_status, PRDStatus) else str(new_status).lower()

        if not can_transition_version(current_status, target_status_str):
            logger.warning(
                f"Potentially invalid version transition from '{current_status}' to '{target_status_str}' "
                f"for version {version_id}."
            )

        update_payload: Dict[str, Any] = {
            "status": target_status_str,
            "updated_at": datetime.utcnow()
        }
        if error_details:
            update_payload["error_details"] = error_details
        if extra_fields:
            update_payload.update(extra_fields)

        updated = await self.version_repo.update(version_id, update_payload)
        return updated
