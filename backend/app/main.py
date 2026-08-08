from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import agent_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous Governed dbt Change Agent powered by DataHub for the DataHub Agent Hackathon.",
    version="1.0.0"
)

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from app.security.rate_limiter import RateLimitMiddleware

# Enforce token bucket rate limiting on public routes
app.add_middleware(RateLimitMiddleware)

# Configurable CORS origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Session-ID"],
)

# Global internal error handler to sanitize Stack Traces / System leaks
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the real traceback internally
    import logging
    logger = logging.getLogger("synex.error")
    logger.exception("Sanitized internal server error captured:")
    
    # Return a clean generic message to the client
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please contact the administrator."}
    )

app.include_router(agent_router.router)

@app.get("/health")
def health_check():
    config_issues = settings.validate_runtime_config()
    return {
        "status": "healthy" if not config_issues else "degraded",
        "agent": "Synex Governed dbt Change Agent",
        "datahub_gms": settings.DATAHUB_GMS_URL,
        "datahub_mcp_url": settings.DATAHUB_MCP_URL or "Not configured",
        "config_issues": config_issues,
    }
