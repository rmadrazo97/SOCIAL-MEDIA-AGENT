from fastapi import Header, HTTPException
from app.config import settings


async def verify_password(x_app_password: str = Header(...)):
    if x_app_password != settings.APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    return True
