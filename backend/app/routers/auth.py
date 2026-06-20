from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import schemas, crud
from backend.app.database import get_db
from backend.app.security import create_access_token, verify_password
from backend.app.dependencies import get_current_active_user
from backend.app.limiter import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await crud.get_user_by_username(db, user.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    db_user = await crud.create_user(db, user)
    return db_user


@router.post("/login", response_model=schemas.Token)
@limiter.limit("10/minute")
async def login(request: Request, user_in: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    user = await crud.authenticate_user(db, user_in.username, user_in.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
async def me(current_user = Depends(get_current_active_user)):
    return current_user
