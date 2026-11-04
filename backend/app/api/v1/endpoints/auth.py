from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.models.user import UserCreate, UserLogin, UserResponse, Token
from app.db.repository import UserRepository
from app.api.deps import get_user_repo, get_current_user

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, user_repo: UserRepository = Depends(get_user_repo)):
    existing = await user_repo.get_by_username(user_in.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered.")
    
    existing_email = await user_repo.get_by_email(user_in.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered.")

    hashed_pw = get_password_hash(user_in.password)
    user_data = user_in.dict(exclude={"password"})
    user_data["hashed_password"] = hashed_pw
    user_data["created_at"] = datetime.utcnow()
    user_data["updated_at"] = datetime.utcnow()
    
    created = await user_repo.create(user_data)
    return UserResponse(
        id=created["id"],
        username=created["username"],
        email=created["email"],
        full_name=created.get("full_name"),
        role=created.get("role", "engineer"),
        created_at=created.get("created_at")
    )

@router.post("/login", response_model=Token)
async def login(login_in: UserLogin, user_repo: UserRepository = Depends(get_user_repo)):
    user = await user_repo.get_by_username(login_in.username)
    if not user or not verify_password(login_in.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token = create_access_token(user["id"])
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        full_name=current_user.get("full_name"),
        role=current_user.get("role", "engineer"),
        created_at=current_user.get("created_at")
    )
