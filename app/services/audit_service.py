"""
Audit Logging Service

Service for logging and monitoring award-related actions.
"""

from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, desc, and_, func
from datetime import datetime, timedelta
import logging
from collections import defaultdict

from app.models.audit_log import AuditLog, AuditAction, AuditLogCreate
from app.models.user import User

logger = logging.getLogger(__name__)


class AuditServiceError(Exception):
    """Base exception for audit service operations."""
    pass


class AuditService:
    """Service for managing audit logs and monitoring system health."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def log_action(
        self,
        action: AuditAction,
        user_id: Optional[int] = None,
        target_user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditLog:
        """
        Log an audit action to the database.
        
        Args:
            action: The type of action being logged
            user_id: ID of the user performing the action
            target_user_id: ID of the user affected by the action
            entity_type: Type of entity (award, template, etc.)
            entity_id: ID of the affected entity
            details: Additional details about the action
            ip_address: IP address of the user
            user_agent: User agent string
            status: Status of the action
            error_message: Error message if action failed
            session_id: Session ID if available
            
        Returns:
            The created audit log entry
        """
        try:
            audit_log = AuditLog(
                action=action,
                user_id=user_id,
                target_user_id=target_user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                error_message=error_message,
                session_id=session_id
            )
            
            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)
            
            return audit_log
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log audit action {action}: {e}")
            raise AuditServiceError(f"Failed to log audit action: {e}")
    
    async def get_audit_logs(
        self,
        action: Optional[AuditAction] = None,
        user_id: Optional[int] = None,
        target_user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Retrieve audit logs with filtering options.
        
        Args:
            action: Filter by action type
            user_id: Filter by user ID
            target_user_id: Filter by target user ID
            entity_type: Filter by entity type
            status: Filter by status
            start_date: Filter by start date
            end_date: Filter by end date
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of audit log entries
        """
        try:
            query = select(AuditLog)
            
            # Apply filters
            if action:
                query = query.where(AuditLog.action == action)
            if user_id:
                query = query.where(AuditLog.user_id == user_id)
            if target_user_id:
                query = query.where(AuditLog.target_user_id == target_user_id)
            if entity_type:
                query = query.where(AuditLog.entity_type == entity_type)
            if status:
                query = query.where(AuditLog.status == status)
            if start_date:
                query = query.where(AuditLog.created_at >= start_date)
            if end_date:
                query = query.where(AuditLog.created_at <= end_date)
            
            # Apply ordering and pagination
            query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
            
            return list(self.db.exec(query).all())
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {e}")
            raise AuditServiceError(f"Failed to retrieve audit logs: {e}")
    
    async def get_system_health_stats(self) -> Dict[str, Any]:
        """
        Get system health statistics from audit logs.
        
        Returns:
            Dictionary with system health metrics
        """
        try:
            # Get stats for the last 24 hours
            cutoff_date = datetime.utcnow() - timedelta(hours=24)
            
            # Total actions in last 24 hours
            total_actions = self.db.exec(
                select(func.count(AuditLog.id))
                .where(AuditLog.created_at >= cutoff_date)
            ).first()
            
            # Failed actions in last 24 hours
            failed_actions = self.db.exec(
                select(func.count(AuditLog.id))
                .where(
                    AuditLog.created_at >= cutoff_date,
                    AuditLog.status == "failure"
                )
            ).first()
            
            # Error rate
            error_rate = (failed_actions / total_actions * 100) if total_actions > 0 else 0
            
            # Action breakdown
            action_stats = self.db.exec(
                select(AuditLog.action, func.count(AuditLog.id))
                .where(AuditLog.created_at >= cutoff_date)
                .group_by(AuditLog.action)
            ).all()
            
            action_breakdown = {action: count for action, count in action_stats}
            
            # Recent errors
            recent_errors = self.db.exec(
                select(AuditLog)
                .where(
                    AuditLog.created_at >= cutoff_date,
                    AuditLog.status == "failure"
                )
                .order_by(desc(AuditLog.created_at))
                .limit(10)
            ).all()
            
            health_stats = {
                "period": "24_hours",
                "total_actions": total_actions,
                "failed_actions": failed_actions,
                "error_rate_percentage": round(error_rate, 2),
                "action_breakdown": action_breakdown,
                "recent_errors": [
                    {
                        "action": error.action,
                        "error_message": error.error_message,
                        "created_at": error.created_at,
                        "user_id": error.user_id
                    }
                    for error in recent_errors
                ],
                "health_status": "healthy" if error_rate < 5 else "warning" if error_rate < 10 else "critical"
            }
            
            return health_stats
            
        except Exception as e:
            logger.error(f"Failed to get system health stats: {e}")
            raise AuditServiceError(f"Failed to get system health stats: {e}")
    
    async def get_user_activity_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get activity statistics for a specific user.
        
        Args:
            user_id: User ID to get stats for
            
        Returns:
            Dictionary with user activity metrics
        """
        try:
            # Get stats for the last 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # Total actions by user
            total_actions = self.db.exec(
                select(func.count(AuditLog.id))
                .where(
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= cutoff_date
                )
            ).first()
            
            # Actions where user was the target
            actions_received = self.db.exec(
                select(func.count(AuditLog.id))
                .where(
                    AuditLog.target_user_id == user_id,
                    AuditLog.created_at >= cutoff_date
                )
            ).first()
            
            # Action breakdown
            action_stats = self.db.exec(
                select(AuditLog.action, func.count(AuditLog.id))
                .where(
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= cutoff_date
                )
                .group_by(AuditLog.action)
            ).all()
            
            activity_stats = {
                "user_id": user_id,
                "period": "30_days",
                "total_actions_performed": total_actions,
                "total_actions_received": actions_received,
                "action_breakdown": {action: count for action, count in action_stats},
                "most_active_day": None,  # Would need daily breakdown
                "recent_activity": []
            }
            
            # Get recent activity
            recent_activity = self.db.exec(
                select(AuditLog)
                .where(
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= cutoff_date
                )
                .order_by(desc(AuditLog.created_at))
                .limit(20)
            ).all()
            
            activity_stats["recent_activity"] = [
                {
                    "action": activity.action,
                    "entity_type": activity.entity_type,
                    "entity_id": activity.entity_id,
                    "status": activity.status,
                    "created_at": activity.created_at
                }
                for activity in recent_activity
            ]
            
            return activity_stats
            
        except Exception as e:
            logger.error(f"Failed to get user activity stats for user {user_id}: {e}")
            raise AuditServiceError(f"Failed to get user activity stats: {e}")
    
    async def get_monitoring_alerts(self) -> List[Dict[str, Any]]:
        """
        Get monitoring alerts based on audit log patterns.
        
        Returns:
            List of alert dictionaries
        """
        try:
            alerts = []
            
            # Check for high error rate in last hour
            cutoff_date = datetime.utcnow() - timedelta(hours=1)
            
            total_actions = self.db.exec(
                select(func.count(AuditLog.id))
                .where(AuditLog.created_at >= cutoff_date)
            ).first()
            
            failed_actions = self.db.exec(
                select(func.count(AuditLog.id))
                .where(
                    AuditLog.created_at >= cutoff_date,
                    AuditLog.status == "failure"
                )
            ).first()
            
            if total_actions > 0:
                error_rate = (failed_actions / total_actions) * 100
                
                if error_rate > 10:
                    alerts.append({
                        "type": "high_error_rate",
                        "severity": "critical" if error_rate > 25 else "warning",
                        "message": f"High error rate detected: {error_rate:.1f}% in the last hour",
                        "value": error_rate,
                        "threshold": 10,
                        "created_at": datetime.utcnow()
                    })
            
            # Check for unusual activity patterns
            recent_actions = self.db.exec(
                select(AuditLog.action, func.count(AuditLog.id))
                .where(AuditLog.created_at >= cutoff_date)
                .group_by(AuditLog.action)
            ).all()
            
            for action, count in recent_actions:
                if action == AuditAction.AWARD_REVOKED and count > 5:
                    alerts.append({
                        "type": "unusual_revocation_activity",
                        "severity": "warning",
                        "message": f"Unusual number of award revocations: {count} in the last hour",
                        "value": count,
                        "threshold": 5,
                        "created_at": datetime.utcnow()
                    })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get monitoring alerts: {e}")
            raise AuditServiceError(f"Failed to get monitoring alerts: {e}")
    
    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """
        Clean up old audit logs to prevent database bloat.
        
        Args:
            days_to_keep: Number of days of logs to keep
            
        Returns:
            Number of deleted logs
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Get count of logs to delete
            logs_to_delete = self.db.exec(
                select(func.count(AuditLog.id))
                .where(AuditLog.created_at < cutoff_date)
            ).first()
            
            # Delete old logs
            old_logs = self.db.exec(
                select(AuditLog)
                .where(AuditLog.created_at < cutoff_date)
            ).all()
            
            for log in old_logs:
                self.db.delete(log)
            
            self.db.commit()
            
            logger.info(f"Cleaned up {logs_to_delete} old audit logs")
            return logs_to_delete
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to cleanup old audit logs: {e}")
            raise AuditServiceError(f"Failed to cleanup old audit logs: {e}")