import asyncio
import json
import hashlib
from pathlib import Path
from app.core.database import db_manager

async def inspect():
    await db_manager.connect()
    db = db_manager.db

    # 1. Projects
    print("=== BENCHMARK PROJECTS IN MONGODB ===")
    cursor = db.projects.find({
        "title": {"$regex": "Customer Support|Attendance", "$options": "i"}
    })
    projects = await cursor.to_list(100)
    for p in projects:
        pid = str(p["_id"])
        print(f"\nPROJECT: id={pid}, title='{p.get('title')}', owner_id={p.get('owner_id')}, active_prd_id={p.get('active_prd_id')}, created_at={p.get('created_at')}")
        
        # PRD
        prd_cursor = db.prds.find({"project_id": pid})
        prds = await prd_cursor.to_list(10)
        for prd in prds:
            prdid = str(prd["_id"])
            print(f"  PRD: id={prdid}, curr_ver={prd.get('current_version_number')}, curr_ver_id={prd.get('current_version_id')}")
            
            # Versions
            v_cursor = db.prd_versions.find({"prd_id": prdid})
            versions = await v_cursor.to_list(20)
            for v in versions:
                vid = str(v["_id"])
                vh = v.get("content_hash")
                sec1 = v.get("sections", {}).get("document_information", {}).get("content", "")
                ver_in_sec1 = "Unknown"
                for line in sec1.split("\n"):
                    if "**Version:**" in line:
                        ver_in_sec1 = line.strip()
                print(f"    VERSION: id={vid}, ver_num={v.get('version_number')}, job_id={v.get('job_id')}, hash={vh}, sec1_ver='{ver_in_sec1}', created_at={v.get('created_at')}")

        # Jobs
        j_cursor = db.jobs.find({"project_id": pid})
        jobs = await j_cursor.to_list(10)
        for j in jobs:
            print(f"  JOB: id={j.get('job_id')}, status={j.get('status')}, stage={j.get('current_stage')}, provider={j.get('provider')}, model={j.get('model')}, result={j.get('result_reference')}, created_at={j.get('created_at')}")

if __name__ == "__main__":
    asyncio.run(inspect())

