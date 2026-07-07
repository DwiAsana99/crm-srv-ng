from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import CurrentUser, get_current_user
from app.deps.db import get_db

router = APIRouter()


class TokenFcmIn(BaseModel):
    token_fcm: str = Field(min_length=1)


@router.post("/tokenfcm")
async def update_token_fcm(
    payload: TokenFcmIn,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await db.execute(
        text("UPDATE users SET token_fcm = :token WHERE id = :id"),
        {"token": payload.token_fcm, "id": current_user.user_id},
    )
    await db.commit()
    return {"message": "Token FCM berhasil diperbarui"}
