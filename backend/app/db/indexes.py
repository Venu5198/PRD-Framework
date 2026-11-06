import logging
from pymongo import ASCENDING, IndexModel
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

async def initialize_database_indexes(db: AsyncIOMotorDatabase):
    """
    Idempotent initialization of unique, compound, and ownership indexes.
    Performs duplicate resolution checks prior to unique index creation.
    """
    logger.info("Initializing and verifying MongoDB collection indexes...")

    # 1. Users collection
    # Clean up duplicate usernames/emails if any exist prior to unique index enforcement
    users_col = db["users"]
    
    # Check duplicate usernames
    pipeline_un = [
        {"$group": {"_id": "$username", "count": {"$sum": 1}, "docs": {"$push": "$_id"}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    async for dup in users_col.aggregate(pipeline_un):
        # Keep the latest doc, delete prior duplicates
        docs_to_remove = dup["docs"][:-1]
        logger.warning(f"Removing {len(docs_to_remove)} duplicate username records for '{dup['_id']}'")
        await users_col.delete_many({"_id": {"$in": docs_to_remove}})

    # Check duplicate emails
    pipeline_em = [
        {"$group": {"_id": "$email", "count": {"$sum": 1}, "docs": {"$push": "$_id"}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    async for dup in users_col.aggregate(pipeline_em):
        docs_to_remove = dup["docs"][:-1]
        logger.warning(f"Removing {len(docs_to_remove)} duplicate email records for '{dup['_id']}'")
        await users_col.delete_many({"_id": {"$in": docs_to_remove}})

    await users_col.create_indexes([
        IndexModel([("username", ASCENDING)], unique=True, name="uniq_username"),
        IndexModel([("email", ASCENDING)], unique=True, name="uniq_email"),
        IndexModel([("created_at", ASCENDING)], name="idx_user_created")
    ])

    # Seed default developer user if missing in non-production environments
    from app.core.config import settings
    if settings.ENVIRONMENT.lower() != "production":
        existing_dev = await users_col.find_one({"username": "local_engineer"})
        if not existing_dev:
            from app.core.security import get_password_hash
            from datetime import datetime
            await users_col.insert_one({
                "username": "local_engineer",
                "email": "engineer@local.dev",
                "full_name": "Local Engineer",
                "role": "engineer",
                "hashed_password": get_password_hash("password123"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            logger.info("Auto-seeded default user 'local_engineer' ('password123').")

    # 2. Projects collection: owner_id index, updated_at index
    await db["projects"].create_indexes([
        IndexModel([("owner_id", ASCENDING), ("updated_at", -1)], name="idx_owner_updated"),
        IndexModel([("title", ASCENDING)], name="idx_project_title")
    ])

    # 3. Submissions collection: project_id compound index
    await db["idea_submissions"].create_indexes([
        IndexModel([("project_id", ASCENDING), ("created_at", -1)], name="idx_proj_submissions")
    ])

    # 4. Analysis records collection
    await db["analysis_records"].create_indexes([
        IndexModel([("project_id", ASCENDING), ("created_at", -1)], name="idx_proj_analysis")
    ])

    # 5. Clarification sessions collection
    await db["clarification_sessions"].create_indexes([
        IndexModel([("project_id", ASCENDING), ("created_at", -1)], name="idx_proj_clarifications")
    ])

    # 6. PRD documents collection
    await db["prd_documents"].create_indexes([
        IndexModel([("project_id", ASCENDING)], unique=True, name="uniq_proj_prd")
    ])

    # 7. PRD versions collection: compound prd_id + version_number uniqueness
    await db["prd_versions"].create_indexes([
        IndexModel([("prd_id", ASCENDING), ("version_number", ASCENDING)], unique=True, name="uniq_prd_version"),
        IndexModel([("project_id", ASCENDING), ("created_at", -1)], name="idx_proj_versions")
    ])

    # 8. Validation reports collection
    await db["validation_reports"].create_indexes([
        IndexModel([("prd_version_id", ASCENDING), ("created_at", -1)], name="idx_version_validation")
    ])

    # 9. Generation runs collection (telemetry)
    await db["generation_runs"].create_indexes([
        IndexModel([("project_id", ASCENDING), ("created_at", -1)], name="idx_proj_generation_runs")
    ])

    # 10. Jobs collection: unique job_id, project status, user ordering, worker queue, heartbeat
    await db["jobs"].create_indexes([
        IndexModel([("job_id", ASCENDING)], unique=True, name="uniq_job_id"),
        IndexModel([("project_id", ASCENDING), ("status", ASCENDING)], name="idx_proj_job_status"),
        IndexModel([("user_id", ASCENDING), ("created_at", -1)], name="idx_user_jobs"),
        IndexModel([("status", ASCENDING), ("created_at", ASCENDING)], name="idx_queue_status_created"),
        IndexModel([("status", ASCENDING), ("heartbeat_at", ASCENDING)], name="idx_status_heartbeat")
    ])

    logger.info("MongoDB index initialization successfully completed.")

