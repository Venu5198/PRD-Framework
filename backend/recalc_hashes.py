import asyncio
import hashlib
from bson import ObjectId
from app.core.database import db_manager
from app.models.prd import CANONICAL_SECTIONS

async def recalc():
    await db_manager.connect()
    db = db_manager.db

    for vid in ["6aebe9c1d3f5507c7da7f9a3", "6aebf2d2d3f5507c7da7f9a7"]:
        doc = await db.prd_versions.find_one({"_id": ObjectId(vid)})
        if not doc:
            doc = await db.prd_versions.find_one({"id": vid})
        if not doc:
            print(f"Version {vid} not found")
            continue
        sections = doc.get("sections", {})
        body_parts = []
        for sec_key in CANONICAL_SECTIONS:
            if sec_key != "document_information" and sec_key in sections:
                body_parts.append(sections[sec_key].get("content", "").strip())
        full_body = "\n\n".join(body_parts)
        computed = hashlib.sha256(full_body.encode("utf-8")).hexdigest()
        stored = doc.get("content_hash")
        job_id = doc.get("job_id")
        ver_num = doc.get("version_number")
        print(f"Version: {vid} (ver_num='{ver_num}')")
        print(f"  Stored Hash:   {stored}")
        print(f"  Computed Hash: {computed}")
        print(f"  Job ID:        {job_id}")

if __name__ == "__main__":
    asyncio.run(recalc())
