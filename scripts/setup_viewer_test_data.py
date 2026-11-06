import asyncio
import os
import sys
import json
from pathlib import Path
from bson import ObjectId

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.core.database import db_manager
from app.core.security import create_access_token

async def get_or_create_project_with_prd():
    await db_manager.connect()
    
    # 1. Create or get user
    user = await db_manager.db["users"].find_one({"username": "viewer_qa_user"})
    if not user:
        user_doc = {
            "username": "viewer_qa_user",
            "email": "viewer_qa@example.com",
            "hashed_password": "test_hashed_password",
            "full_name": "QA Viewer Auditor"
        }
        res = await db_manager.db["users"].insert_one(user_doc)
        user_id = str(res.inserted_id)
    else:
        user_id = str(user["_id"])
        
    token = create_access_token(subject=user_id)
    
    # 2. Check if there's an existing project with 27 sections
    version = await db_manager.db["prd_versions"].find_one({"sections.functional_requirements": {"$exists": True}})
    
    if version:
        project_id = str(version["project_id"])
        # ensure user owns it or user_id matches
        await db_manager.db["projects"].update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"user_id": user_id}}
        )
        print(f"Using existing project with PRD: {project_id}")
    else:
        # Load PRD markdown and parse
        md_path = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "historical-prds" / "PRD_Customer_Support_v2_4_6.md"
        if not md_path.exists():
            md_path = Path(__file__).resolve().parent.parent / "docs" / "examples" / "customer_support_prd_example.md"
        if not md_path.exists():
            md_path = Path(__file__).resolve().parent.parent / "PRD_Customer_Support_v2_4_6.md"
        sections = {}
        if md_path.exists():
            content = md_path.read_text(encoding="utf-8")
            # Create a simple section map
            from app.models.prd import CANONICAL_SECTIONS, SECTION_TITLES
            lines = content.split("\n## ")
            for idx, key in enumerate(CANONICAL_SECTIONS):
                sections[key] = f"## {SECTION_TITLES.get(key, key)}\n\nContent for {SECTION_TITLES.get(key, key)}...\n\n```mermaid\ngraph TD\n  A[Customer] --> B[AI Assistant]\n  B --> C[Knowledge Base]\n  B --> D[Human Agent]\n```"
        
        proj_doc = {
            "title": "AI Customer Support Assistant (Viewer Test)",
            "description": "Real-world Customer Support Assistant PRD for Viewport Verification",
            "user_id": user_id,
            "status": "APPROVED",
            "lifecycle_state": "ACTIVE"
        }
        p_res = await db_manager.db["projects"].insert_one(proj_doc)
        project_id = str(p_res.inserted_id)
        
        ver_doc = {
            "project_id": ObjectId(project_id),
            "version_number": "v1.0",
            "sections": sections,
            "change_summary": "Initial PRD",
            "validation_status": "APPROVED"
        }
        await db_manager.db["prd_versions"].insert_one(ver_doc)
        print(f"Created new project with PRD: {project_id}")

    await db_manager.close()
    return project_id, token

if __name__ == "__main__":
    pid, tok = asyncio.run(get_or_create_project_with_prd())
    print(f"PID: {pid}")
    print(f"TOKEN: {tok}")
