from fastapi import APIRouter

from app.api.v1.endpoints import platforms, accounts, profiles, chats, messages, automation

api_router = APIRouter()

api_router.include_router(platforms.router, prefix="/platforms", tags=["platforms"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])