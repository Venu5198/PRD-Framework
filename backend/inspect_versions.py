import asyncio
from app.core.database import db_manager

async def inspect():
    await db_manager.connect()
    db = db_manager.db

    for pid in ["6aebe35f64a87cddc70faec6", "6aebebed11fc2fe17efb7dbf", "6aebfcaa8be39e85c6d4b549"]:
        print(f"\n==========================================")
        print(f"QUERYING PROJECT: {pid}")
        proj = await db.projects.find_one({"_id": pid})
        print(f"Project Doc: title={proj.get('title') if proj else None}, active_prd_id={proj.get('active_prd_id') if proj else None}")

        prds = await db.prds.find({"project_id": pid}).to_list(10)
        print(f"Found {len(prds)} PRD docs for project {pid}")
        for p in prds:
            print(f"  PRD doc: _id={p['_id']}, current_version_number={p.get('current_version_number')}, current_version_id={p.get('current_version_id')}")

        versions = await db.prd_versions.find({"project_id": pid}).to_list(20)
        print(f"Found {len(versions)} PRDVersion docs for project {pid}")
        for v in versions:
            sec1 = v.get("sections", {}).get("document_information", {}).get("content", "")
            first_lines = [line.strip() for line in sec1.split("\n") if line.strip()][:6]
            print(f"  PRDVersion doc: _id={v['_id']}, version_number={v.get('version_number')}, job_id={v.get('job_id')}, content_hash={v.get('content_hash')}")
            print(f"    Sec 1 Content lines: {first_lines}")

if __name__ == "__main__":
    asyncio.run(inspect())

