from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.dspy_manager import setup_dspy

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="The source code of reality for the Chemezy game universe",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_init_oauth={
        "tokenUrl": "/api/v1/auth/token",
    }
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Disable rate limiting for tests
if settings.testing:
    app.dependency_overrides[limiter.limit] = lambda: None

# Add CORS middleware - locked down for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    Initializes necessary components like the DSPy language model.
    """
    setup_dspy()

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint serves the index.html file."""
    file_path = "./index.html"
    with open(file_path, "r") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return Response(status_code=200)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
