import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from agno.os import AgentOS
from agno.os.settings import AgnoAPISettings

from app.api.routes import router as chat_router
from app.agents.orchestrator_agent import orchestrator_agent
from app.agents.satinalma_agent import satinalma_agent
from app.configs.settings import settings
from app.configs.logging import setup_logging
from app.configs.helpers import format_error_message

setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KUAgentOS",
    version="1.0.0",
    description="Koç Üniversitesi Agent OS",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    error_msg = format_error_message(exc, user_friendly=True)
    return JSONResponse(
        status_code=500,
        content={"detail": error_msg},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

api_settings = AgnoAPISettings(
    os_security_key=settings.os_security_key,
)

logger.info("Initializing AgentOS...")
agent_os = AgentOS(
    description="Koç Üniversitesi Agent OS",
    agents=[
        orchestrator_agent,
        satinalma_agent,
    ],
    base_app=app,
    settings=api_settings,
)

app = agent_os.get_app()

logger.info("Application initialized successfully")


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("🚀 KUAgentOS Started")
    logger.info("=" * 60)
    logger.info(f"Project ID: {settings.project_id}")
    logger.info(f"Location: {settings.location}")
    logger.info(f"Model: {settings.gemini_model_name}")
    logger.info(f"Available Agents: orchestrator-agent, satinalma-pdf-agent")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    logger.info("Database connections closed (if applicable)")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting development server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
