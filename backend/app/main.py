from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import agent_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous Governed dbt Change Agent powered by DataHub for the DataHub Agent Hackathon.",
    version="1.0.0"
)

# Configurable CORS origins (replaces allow_origins=["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
