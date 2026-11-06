import asyncio
from app.core.database import db_manager

async def inspect():
    await db_manager.connect()
    db = db_manager.db

    projects = await db.projects.find().to_list(100)
    print(f"=== TOTAL PROJECTS: {len(projects)} ===")
    for p in projects:
        print(f"Project ID: {p['_id']}, Title: {p.get('title')}, Owner: {p.get('owner_id')}, Active PRD: {p.get('active_prd_id')}")

    prds = await db.prds.find().to_list(100)
    print(f"\n=== TOTAL PRDS: {len(prds)} ===")
    for prd in prds:
        print(f"PRD ID: {prd['_id']}, Project ID: {prd.get('project_id')}, Curr Ver: {prd.get('current_version_number')}, Curr Ver ID: {prd.get('current_version_id')}")

    versions = await db.prd_versions.find().to_list(100)
    print(f"\n=== TOTAL PRD VERSIONS: {len(versions)} ===")
    for v in versions:
        h = v.get("content_hash")
        h_short = h[:16] if h else "None"
        print(f"Ver ID: {v['_id']}, PRD ID: {v.get('prd_id')}, Proj ID: {v.get('project_id')}, Ver: {v.get('version_number')}, Job ID: {v.get('job_id')}, Hash: {h_short}")

    jobs = await db.jobs.find().to_list(100)
    print(f"\n=== TOTAL JOBS: {len(jobs)} ===")
    for j in jobs:
        print(f"Job ID: {j.get('job_id')}, Proj ID: {j.get('project_id')}, Status: {j.get('status')}, Stage: {j.get('current_stage')}, Ver: {j.get('progress_metadata', {}).get('version_number')}, Result: {j.get('result_reference')}")

if __name__ == "__main__":
    asyncio.run(inspect())
