from fastapi import APIRouter

from app.api.v1.endpoints import users, reactions, chemicals, debug

api_router = APIRouter()

# Include user-related endpoints
api_router.include_router(
    users.router, prefix="/auth", tags=["authentication"])

# Include reaction-related endpoints
api_router.include_router(
    reactions.router, prefix="/reactions", tags=["reactions"])

# Include chemical-related endpoints
api_router.include_router(
    chemicals.router, prefix="/chemicals", tags=["chemicals"])

# Include debug-related endpoints
api_router.include_router(
    debug.router, prefix="/debug", tags=["debug"])
