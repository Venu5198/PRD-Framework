import asyncio
from datetime import datetime, timedelta
from app.core.database import db_manager
from app.db.job_repository import JobRepository
from app.models.job import JobStatus

async def debug():
    await db_manager.connect()
    repo = JobRepository()
    stale_cutoff = datetime.utcnow() - timedelta(seconds=60)
    print(f"stale_cutoff: {stale_cutoff}")

    q1 = {"status": JobStatus.RUNNING}
    docs1 = await repo.collection.find(q1).to_list(10)
    print(f"Docs with status running: {len(docs1)}")
    if docs1:
        doc = docs1[0]
        hb = doc.get("heartbeat_at")
        rc = doc.get("retry_count")
        print(f"Doc heartbeat: {hb} (type: {type(hb)}), is < stale_cutoff: {hb < stale_cutoff if hb else None}")
        print(f"Doc retry_count: {rc} (type: {type(rc)})")

    q2 = {"status": JobStatus.RUNNING, "heartbeat_at": {"$lt": stale_cutoff}}
    docs2 = await repo.collection.find(q2).to_list(10)
    print(f"Docs with status running and heartbeat < cutoff: {len(docs2)}")

    q3 = {"status": JobStatus.RUNNING, "retry_count": {"$lt": 3}}
    docs3 = await repo.collection.find(q3).to_list(10)
    print(f"Docs with status running and retry_count < 3: {len(docs3)}")

    q4 = {"status": JobStatus.RUNNING, "$or": [{"retry_count": {"$lt": 3}}, {"retry_count": None}, {"retry_count": {"$exists": False}}]}
    docs4 = await repo.collection.find(q4).to_list(10)
    print(f"Docs with status running and retry_count < 3 or null/missing: {len(docs4)}")

if __name__ == "__main__":
    asyncio.run(debug())
