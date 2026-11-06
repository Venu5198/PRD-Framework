import sys
sys.path.insert(0, "backend")
import asyncio
from app.core.database import db_manager

async def inspect():
    await db_manager.connect()
    db = db_manager.db
    v246 = await db["prd_versions"].find({"version_number": "v2.4.6"}).to_list(100)
    print(f"Versions with v2.4.6: {len(v246)}")
    for v in v246:
        print(f"  _id={v.get('_id')}, prd_id={v.get('prd_id')}, project_id={v.get('project_id')}, status={v.get('status')}, created_at={v.get('created_at')}")

    all_vers = await db["prd_versions"].find({}, {"version_number": 1, "prd_id": 1, "status": 1}).to_list(500)
    ver_nums = [v.get("version_number") for v in all_vers]
    from collections import Counter
    print("Version numbers distribution:", Counter(ver_nums))

    # Check indexes on prd_versions
    indexes = await db["prd_versions"].index_information()
    print("Indexes on prd_versions:", indexes)

if __name__ == "__main__":
    asyncio.run(inspect())
