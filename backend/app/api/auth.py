from fastapi import APIRouter, HTTPException
from app.config import settings
from app.schemas.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    if req.password != settings.APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    return LoginResponse(authenticated=True, message="Login successful")
