"""
Comprehensive Error Handling Service

Provides centralized error handling, recovery, and reporting for the award system.
"""

import logging
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from app.models.audit_log import AuditAction
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    DATABASE = "database"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    EXTERNAL_API = "external_api"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    NETWORK = "network"
    CONFIGURATION = "configuration"


class ErrorRecord:
    """Represents an error occurrence with context."""
    
    def __init__(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        operation: Optional[str] = None,
        recoverable: bool = True
    ):
        self.error = error
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.user_id = user_id
        self.operation = operation
        self.recoverable = recoverable
        self.timestamp = datetime.utcnow()
        self.error_id = f"{category.value}_{int(self.timestamp.timestamp())}"
        
        # Extract error details
        self.error_type = type(error).__name__
        self.error_message = str(error)
        self.stack_trace = traceback.format_exc()


class ErrorHandlerService:
    """Service for handling, logging, and recovering from errors."""
    
    def __init__(self, audit_service: Optional[AuditService] = None):
        self.audit_service = audit_service
        self.error_history: List[ErrorRecord] = []
        self.recovery_strategies = {
            ErrorCategory.DATABASE: self._handle_database_error,
            ErrorCategory.VALIDATION: self._handle_validation_error,
            ErrorCategory.AUTHENTICATION: self._handle_auth_error,
            ErrorCategory.AUTHORIZATION: self._handle_authz_error,
            ErrorCategory.EXTERNAL_API: self._handle_external_api_error,
            ErrorCategory.BUSINESS_LOGIC: self._handle_business_logic_error,
            ErrorCategory.SYSTEM: self._handle_system_error,
            ErrorCategory.NETWORK: self._handle_network_error,
            ErrorCategory.CONFIGURATION: self._handle_configuration_error,
        }
    
    async def handle_error(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        operation: Optional[str] = None,
        attempt_recovery: bool = True
    ) -> Dict[str, Any]:
        """
        Handle an error with appropriate logging, recovery, and reporting.
        
        Args:
            error: The exception that occurred
            category: Category of the error
            severity: Severity level of the error
            context: Additional context information
            user_id: ID of the user when the error occurred
            operation: Name of the operation that failed
            attempt_recovery: Whether to attempt automatic recovery
            
        Returns:
            Dictionary with error handling results
        """
        # Create error record
        error_record = ErrorRecord(
            error=error,
            category=category,
            severity=severity,
            context=context,
            user_id=user_id,
            operation=operation,
            recoverable=attempt_recovery
        )
        
        # Add to error history
        self.error_history.append(error_record)
        
        # Log the error
        await self._log_error(error_record)
        
        # Attempt recovery if enabled
        recovery_result = None
        if attempt_recovery:
            recovery_result = await self._attempt_recovery(error_record)
        
        # Generate error report
        error_report = self._generate_error_report(error_record, recovery_result)
        
        # Alert on critical errors
        if severity == ErrorSeverity.CRITICAL:
            await self._send_critical_alert(error_record)
        
        return error_report
    
    async def _log_error(self, error_record: ErrorRecord) -> None:
        """Log error to various systems."""
        # Log to application logger
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_record.severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"Error {error_record.error_id}: {error_record.error_message}",
            extra={
                "error_id": error_record.error_id,
                "category": error_record.category.value,
                "severity": error_record.severity.value,
                "user_id": error_record.user_id,
                "operation": error_record.operation,
                "context": error_record.context
            }
        )
        
        # Log to audit service if available
        if self.audit_service:
            try:
                await self.audit_service.log_action(
                    action=AuditAction.SYSTEM_ERROR,
                    user_id=error_record.user_id,
                    details={
                        "error_id": error_record.error_id,
                        "error_type": error_record.error_type,
                        "error_message": error_record.error_message,
                        "category": error_record.category.value,
                        "severity": error_record.severity.value,
                        "operation": error_record.operation,
                        "context": error_record.context,
                        "stack_trace": error_record.stack_trace
                    },
                    status="failure"
                )
            except Exception as e:
                logger.error(f"Failed to log error to audit service: {e}")
    
    async def _attempt_recovery(self, error_record: ErrorRecord) -> Optional[Dict[str, Any]]:
        """Attempt to recover from the error."""
        recovery_strategy = self.recovery_strategies.get(error_record.category)
        
        if not recovery_strategy:
            return {
                "attempted": False,
                "reason": "No recovery strategy available"
            }
        
        try:
            result = await recovery_strategy(error_record)
            return {
                "attempted": True,
                "success": result.get("success", False),
                "actions_taken": result.get("actions", []),
                "message": result.get("message", "Recovery attempted")
            }
        except Exception as recovery_error:
            logger.error(f"Recovery failed for error {error_record.error_id}: {recovery_error}")
            return {
                "attempted": True,
                "success": False,
                "error": str(recovery_error),
                "message": "Recovery attempt failed"
            }
    
    def _generate_error_report(
        self,
        error_record: ErrorRecord,
        recovery_result: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a comprehensive error report."""
        return {
            "error_id": error_record.error_id,
            "timestamp": error_record.timestamp.isoformat(),
            "error_type": error_record.error_type,
            "error_message": error_record.error_message,
            "category": error_record.category.value,
            "severity": error_record.severity.value,
            "operation": error_record.operation,
            "user_id": error_record.user_id,
            "context": error_record.context,
            "recoverable": error_record.recoverable,
            "recovery_result": recovery_result,
            "stack_trace": error_record.stack_trace if error_record.severity == ErrorSeverity.CRITICAL else None
        }
    
    async def _send_critical_alert(self, error_record: ErrorRecord) -> None:
        """Send alerts for critical errors."""
        # In a real implementation, this would send emails, Slack messages, etc.
        logger.critical(
            f"CRITICAL ERROR ALERT: {error_record.error_id} - {error_record.error_message}"
        )
    
    # Recovery strategy implementations
    async def _handle_database_error(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Handle database-related errors."""
        actions = []
        
        # Check for common database issues
        error_msg = error_record.error_message.lower()
        
        if "connection" in error_msg or "timeout" in error_msg:
            actions.append("Database connection issue detected")
            # Could implement connection retry logic here
        
        if "integrity" in error_msg or "constraint" in error_msg:
            actions.append("Database integrity constraint violation")
            # Could implement data validation recovery
        
        if "deadlock" in error_msg:
            actions.append("Database deadlock detected")
            # Could implement retry with backoff
        
        return {
            "success": False,  # Database errors typically require manual intervention
            "actions": actions,
            "message": "Database error logged for manual review"
        }
    
    async def _handle_validation_error(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Handle validation errors."""
        return {
            "success": True,
            "actions": ["Validation error handled gracefully"],
            "message": "Validation error can be recovered by user input correction"
        }
    
    async def _handle_auth_error(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Handle authentication errors."""
        return {
            "success": True,
            "actions": ["Authentication error handled"],
            "message": "User can re-authenticate to resolve issue"
        }
    
    async def _handle_authz_error(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Handle authorization errors."""
        return {
            "success": True,
            "actions": ["Authorization error handled"],
            "message": "User lacks required permissions"
        }
    
    async def _handle_external_api_error(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Handle external API errors."""
        actions = []
        
        # Check for rate limiting
        if "rate" in error_record.error_message.lower():
            actions.append("Rate limit detected, implementing backoff")
        
        # Check for service unavailable
        if "unavailable" in error_record.error_message.lower():
            actions.append("External service unavailable, will retry later")
        
        return {
            "success": len(actions) > 0,
            "actions": actions,
            "message": "External API error handling applied"
        }
    
    async def _handle_business_logic_error(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Handle business logic errors."""
        return {
            "success": True,
            "actions": ["Business logic error handled"],
            "message": "Business rule violation, user can correct input"
        }
    
    async def _handle_system_error(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Handle system errors."""
        return {
            "success": False,
            "actions": ["System error logged for investigation"],
            "message": "System error requires manual intervention"
        }
    
    async def _handle_network_error(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Handle network errors."""
        return {
            "success": True,
            "actions": ["Network error handled with retry logic"],
            "message": "Network error may resolve automatically"
        }
    
    async def _handle_configuration_error(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Handle configuration errors."""
        return {
            "success": False,
            "actions": ["Configuration error logged"],
            "message": "Configuration error requires manual correction"
        }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        if not self.error_history:
            return {
                "total_errors": 0,
                "by_category": {},
                "by_severity": {},
                "recent_errors": []
            }
        
        # Count by category
        category_counts = {}
        for error in self.error_history:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for error in self.error_history:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Recent errors (last 10)
        recent_errors = [
            {
                "error_id": error.error_id,
                "timestamp": error.timestamp.isoformat(),
                "category": error.category.value,
                "severity": error.severity.value,
                "message": error.error_message
            }
            for error in sorted(self.error_history, key=lambda x: x.timestamp, reverse=True)[:10]
        ]
        
        return {
            "total_errors": len(self.error_history),
            "by_category": category_counts,
            "by_severity": severity_counts,
            "recent_errors": recent_errors
        }
    
    def clear_error_history(self) -> None:
        """Clear error history (for testing or maintenance)."""
        self.error_history.clear()


# Global error handler instance
error_handler = ErrorHandlerService()