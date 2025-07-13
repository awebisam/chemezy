"""
Admin monitoring and audit endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import Optional, List
from datetime import datetime

from app.api.v1.endpoints.users import get_current_admin_user
from app.db.session import get_session
from app.models.user import User
from app.models.audit_log import AuditAction, AuditLogResponse
from app.services.audit_service import AuditService, AuditServiceError

router = APIRouter()


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    action: Optional[AuditAction] = Query(None, description="Filter by action type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    target_user_id: Optional[int] = Query(None, description="Filter by target user ID"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Retrieve audit logs with filtering options.
    
    Only admin users can access audit logs.
    """
    try:
        audit_service = AuditService(db)
        logs = await audit_service.get_audit_logs(
            action=action,
            user_id=user_id,
            target_user_id=target_user_id,
            entity_type=entity_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
        
        return [AuditLogResponse.from_orm(log) for log in logs]
        
    except AuditServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit logs: {str(e)}"
        )


@router.get("/system-health")
async def get_system_health(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Get system health statistics.
    
    Only admin users can access system health data.
    """
    try:
        audit_service = AuditService(db)
        health_stats = await audit_service.get_system_health_stats()
        
        return {
            "system_health": health_stats,
            "checked_at": datetime.utcnow(),
            "checked_by": admin_user.username
        }
        
    except AuditServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system health: {str(e)}"
        )


@router.get("/user-activity/{user_id}")
async def get_user_activity(
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Get activity statistics for a specific user.
    
    Only admin users can access user activity data.
    """
    try:
        audit_service = AuditService(db)
        activity_stats = await audit_service.get_user_activity_stats(user_id)
        
        return {
            "user_activity": activity_stats,
            "checked_at": datetime.utcnow(),
            "checked_by": admin_user.username
        }
        
    except AuditServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user activity: {str(e)}"
        )


@router.get("/alerts")
async def get_monitoring_alerts(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Get monitoring alerts based on system behavior.
    
    Only admin users can access monitoring alerts.
    """
    try:
        audit_service = AuditService(db)
        alerts = await audit_service.get_monitoring_alerts()
        
        return {
            "alerts": alerts,
            "alert_count": len(alerts),
            "checked_at": datetime.utcnow(),
            "checked_by": admin_user.username
        }
        
    except AuditServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve monitoring alerts: {str(e)}"
        )


@router.post("/cleanup-logs")
async def cleanup_old_logs(
    days_to_keep: int = Query(90, ge=7, le=365, description="Number of days of logs to keep"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Clean up old audit logs to prevent database bloat.
    
    Only admin users can perform log cleanup.
    """
    try:
        audit_service = AuditService(db)
        deleted_count = await audit_service.cleanup_old_logs(days_to_keep)
        
        # Log the cleanup action
        await audit_service.log_action(
            action=AuditAction.SYSTEM_ERROR,  # Using as generic system action
            user_id=admin_user.id,
            details={
                "action": "log_cleanup",
                "days_to_keep": days_to_keep,
                "deleted_count": deleted_count
            }
        )
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "days_kept": days_to_keep,
            "cleaned_at": datetime.utcnow(),
            "cleaned_by": admin_user.username
        }
        
    except AuditServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup logs: {str(e)}"
        )


@router.get("/dashboard")
async def get_admin_dashboard(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Get comprehensive admin dashboard with system statistics.
    
    Only admin users can access the admin dashboard.
    """
    try:
        audit_service = AuditService(db)
        
        # Get system health
        health_stats = await audit_service.get_system_health_stats()
        
        # Get alerts
        alerts = await audit_service.get_monitoring_alerts()
        
        # Get recent audit logs
        recent_logs = await audit_service.get_audit_logs(limit=20)
        
        dashboard_data = {
            "system_health": health_stats,
            "alerts": {
                "items": alerts,
                "count": len(alerts),
                "critical_count": len([a for a in alerts if a.get("severity") == "critical"]),
                "warning_count": len([a for a in alerts if a.get("severity") == "warning"])
            },
            "recent_activity": [
                {
                    "id": log.id,
                    "action": log.action,
                    "user_id": log.user_id,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "status": log.status,
                    "created_at": log.created_at
                }
                for log in recent_logs
            ],
            "generated_at": datetime.utcnow(),
            "generated_by": admin_user.username
        }
        
        return dashboard_data
        
    except AuditServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve admin dashboard: {str(e)}"
        )