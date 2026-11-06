from typing import Optional, List, Dict, Any
from bson import ObjectId
from app.core.database import get_database

def fix_id(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc

def to_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        return id_str  # fallback if mock or string id

class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @property
    def collection(self):
        return get_database()[self.collection_name]

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = await self.collection.insert_one(data)
        data["id"] = str(result.inserted_id)
        if "_id" in data:
            del data["_id"]
        return data

    async def get_by_id(self, id_str: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"_id": to_object_id(id_str)})
        if not doc:
            doc = await self.collection.find_one({"id": id_str})
        return fix_id(doc)

    async def find(self, query: Dict[str, Any], sort: Optional[List] = None, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.collection.find(query)
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        docs = await cursor.to_list(length=limit)
        return [fix_id(d) for d in docs]

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one(query)
        return fix_id(doc)

    async def update(self, id_str: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        query = {"_id": to_object_id(id_str)}
        await self.collection.update_one(query, {"$set": update_data})
        return await self.get_by_id(id_str)

    async def delete(self, id_str: str) -> bool:
        result = await self.collection.delete_one({"_id": to_object_id(id_str)})
        return result.deleted_count > 0

class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__("users")

    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"username": username})
        return fix_id(doc)

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"email": email})
        return fix_id(doc)

class ProjectRepository(BaseRepository):
    def __init__(self):
        super().__init__("projects")

    async def get_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        return await self.find({"owner_id": owner_id}, sort=[("updated_at", -1)])

class SubmissionRepository(BaseRepository):
    def __init__(self):
        super().__init__("idea_submissions")

    async def get_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        return await self.find({"project_id": project_id}, sort=[("created_at", -1)])

class AnalysisRepository(BaseRepository):
    def __init__(self):
        super().__init__("analysis_records")

    async def get_latest_by_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        docs = await self.find({"project_id": project_id}, sort=[("created_at", -1)], limit=1)
        return docs[0] if docs else None

class ClarificationRepository(BaseRepository):
    def __init__(self):
        super().__init__("clarification_sessions")

    async def get_latest_by_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        docs = await self.find({"project_id": project_id}, sort=[("created_at", -1)], limit=1)
        return docs[0] if docs else None

class PRDRepository(BaseRepository):
    def __init__(self):
        super().__init__("prd_documents")

    async def get_by_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"project_id": project_id})

class PRDVersionRepository(BaseRepository):
    def __init__(self):
        super().__init__("prd_versions")

    async def get_by_prd(self, prd_id: str) -> List[Dict[str, Any]]:
        return await self.find({"prd_id": prd_id}, sort=[("created_at", -1)])

    async def get_by_prd_and_version(self, prd_id: str, version_number: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"prd_id": prd_id, "version_number": version_number})

    async def get_by_job_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"job_id": job_id})

    async def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"idempotency_key": idempotency_key})

    async def get_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        return await self.find({"project_id": project_id}, sort=[("created_at", -1)])

class ValidationRepository(BaseRepository):
    def __init__(self):
        super().__init__("validation_reports")

    async def get_latest_by_version(self, prd_version_id: str) -> Optional[Dict[str, Any]]:
        docs = await self.find({"prd_version_id": prd_version_id}, sort=[("created_at", -1)], limit=1)
        return docs[0] if docs else None

class GenerationRunRepository(BaseRepository):
    def __init__(self):
        super().__init__("generation_runs")

