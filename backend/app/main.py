from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import agent_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous AI Data Engineering Agent powered by DataHub for the DataHub Agent Hackathon.",
    version="1.0.0"
)

# Enable CORS for Next.js frontend (Vercel + local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router.router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "agent": "Synex",
        "datahub_gms": settings.DATAHUB_GMS_URL
    }
