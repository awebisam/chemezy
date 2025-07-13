"""
Error Handling Middleware

Provides centralized error handling for FastAPI applications.
"""

import logging
from typing import Callable, Dict, Any
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from app.services.error_handler import (
    error_handler,
    ErrorCategory,
    ErrorSeverity
)

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling unhandled exceptions."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.error_mappings = {
            ValueError: (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM),
            TypeError: (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM),
            ValidationError: (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM),
            SQLAlchemyError: (ErrorCategory.DATABASE, ErrorSeverity.HIGH),
            ConnectionError: (ErrorCategory.NETWORK, ErrorSeverity.HIGH),
            TimeoutError: (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM),
            PermissionError: (ErrorCategory.AUTHORIZATION, ErrorSeverity.HIGH),
            FileNotFoundError: (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM),
            OSError: (ErrorCategory.SYSTEM, ErrorSeverity.HIGH),
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle any unhandled exceptions."""
        try:
            response = await call_next(request)
            return response
        
        except HTTPException as e:
            # Let FastAPI handle HTTP exceptions normally
            raise e
        
        except Exception as e:
            # Handle unhandled exceptions
            return await self._handle_unhandled_exception(request, e)
    
    async def _handle_unhandled_exception(
        self,
        request: Request,
        error: Exception
    ) -> JSONResponse:
        """Handle unhandled exceptions with proper error reporting."""
        
        # Determine error category and severity
        category, severity = self._classify_error(error)
        
        # Extract request context
        context = {
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "request_id": getattr(request.state, "request_id", None)
        }
        
        # Extract user ID from request if available
        user_id = getattr(request.state, "user_id", None)
        
        # Handle the error
        error_report = await error_handler.handle_error(
            error=error,
            category=category,
            severity=severity,
            context=context,
            user_id=user_id,
            operation=f"{request.method} {request.url.path}"
        )
        
        # Generate appropriate HTTP response
        status_code, response_body = self._generate_error_response(error, error_report)
        
        return JSONResponse(
            status_code=status_code,
            content=response_body,
            headers={"X-Error-ID": error_report["error_id"]}
        )
    
    def _classify_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error by type to determine category and severity."""
        error_type = type(error)
        
        # Check direct mappings
        if error_type in self.error_mappings:
            return self.error_mappings[error_type]
        
        # Check inheritance hierarchy
        for mapped_type, (category, severity) in self.error_mappings.items():
            if isinstance(error, mapped_type):
                return category, severity
        
        # Default for unknown errors
        return ErrorCategory.SYSTEM, ErrorSeverity.HIGH
    
    def _generate_error_response(
        self,
        error: Exception,
        error_report: Dict[str, Any]
    ) -> tuple[int, Dict[str, Any]]:
        """Generate appropriate HTTP response for the error."""
        
        # Map error categories to HTTP status codes
        status_code_mapping = {
            ErrorCategory.VALIDATION: 400,
            ErrorCategory.AUTHENTICATION: 401,
            ErrorCategory.AUTHORIZATION: 403,
            ErrorCategory.BUSINESS_LOGIC: 422,
            ErrorCategory.DATABASE: 500,
            ErrorCategory.EXTERNAL_API: 502,
            ErrorCategory.NETWORK: 503,
            ErrorCategory.SYSTEM: 500,
            ErrorCategory.CONFIGURATION: 500,
        }
        
        category = ErrorCategory(error_report["category"])
        status_code = status_code_mapping.get(category, 500)
        
        # Generate user-friendly error message
        user_message = self._get_user_friendly_message(error, category)
        
        # Response body
        response_body = {
            "error": True,
            "error_id": error_report["error_id"],
            "message": user_message,
            "category": error_report["category"],
            "timestamp": error_report["timestamp"]
        }
        
        # Add recovery suggestions if available
        if error_report.get("recovery_result"):
            recovery = error_report["recovery_result"]
            if recovery.get("success"):
                response_body["recovery_attempted"] = True
                response_body["recovery_message"] = recovery.get("message")
        
        # Add details for development environment
        if logger.isEnabledFor(logging.DEBUG):
            response_body["debug"] = {
                "error_type": error_report["error_type"],
                "operation": error_report["operation"],
                "context": error_report["context"]
            }
        
        return status_code, response_body
    
    def _get_user_friendly_message(
        self,
        error: Exception,
        category: ErrorCategory
    ) -> str:
        """Generate user-friendly error messages."""
        
        messages = {
            ErrorCategory.VALIDATION: "The provided data is invalid. Please check your input and try again.",
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please log in and try again.",
            ErrorCategory.AUTHORIZATION: "You don't have permission to perform this action.",
            ErrorCategory.BUSINESS_LOGIC: "The operation cannot be completed due to business rules.",
            ErrorCategory.DATABASE: "A database error occurred. Please try again later.",
            ErrorCategory.EXTERNAL_API: "An external service is temporarily unavailable. Please try again later.",
            ErrorCategory.NETWORK: "A network error occurred. Please check your connection and try again.",
            ErrorCategory.SYSTEM: "An internal system error occurred. Please try again later.",
            ErrorCategory.CONFIGURATION: "A configuration error occurred. Please contact support."
        }
        
        return messages.get(category, "An unexpected error occurred. Please try again later.")


def handle_service_error(
    category: ErrorCategory,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    operation: str = None
):
    """
    Decorator for handling service-level errors.
    
    Args:
        category: Error category
        severity: Error severity level
        operation: Operation name for logging
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Extract context from function arguments
                context = {
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()) if kwargs else []
                }
                
                # Handle the error
                error_report = await error_handler.handle_error(
                    error=e,
                    category=category,
                    severity=severity,
                    context=context,
                    operation=operation or func.__name__
                )
                
                # Re-raise the exception with additional context
                raise type(e)(
                    f"{str(e)} (Error ID: {error_report['error_id']})"
                ) from e
        
        return wrapper
    return decorator


def handle_database_error(operation: str = None):
    """Decorator specifically for database operations."""
    return handle_service_error(
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.HIGH,
        operation=operation
    )


def handle_validation_error(operation: str = None):
    """Decorator specifically for validation operations."""
    return handle_service_error(
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.MEDIUM,
        operation=operation
    )


def handle_business_logic_error(operation: str = None):
    """Decorator specifically for business logic operations."""
    return handle_service_error(
        category=ErrorCategory.BUSINESS_LOGIC,
        severity=ErrorSeverity.MEDIUM,
        operation=operation
    )