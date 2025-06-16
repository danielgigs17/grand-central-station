from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.base import get_db

router = APIRouter()


@router.get("/")
async def list_platforms(db: Session = Depends(get_db)):
    return {"platforms": ["grindr", "sniffies", "alibaba"]}