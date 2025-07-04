from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db

router = APIRouter()


@router.get("/")
async def list_automation_rules(db: Session = Depends(get_db)):
    return {"rules": []}