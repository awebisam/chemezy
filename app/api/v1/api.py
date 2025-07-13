from fastapi import APIRouter

from app.api.v1.endpoints import users, reactions, chemicals, debug, awards, admin_awards, admin_monitoring, admin_config

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

# Include award-related endpoints
api_router.include_router(
    awards.router, prefix="/awards", tags=["awards"])

# Include admin award management endpoints
api_router.include_router(
    admin_awards.router, prefix="/admin/awards", tags=["admin-awards"])

# Include admin monitoring endpoints
api_router.include_router(
    admin_monitoring.router, prefix="/admin/monitoring", tags=["admin-monitoring"])

# Include admin configuration endpoints
api_router.include_router(
    admin_config.router, prefix="/admin/config", tags=["admin-config"])
