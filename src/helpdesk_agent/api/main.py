from fastapi import FastAPI
from helpdesk_agent.observability.logger import setup_logging
from helpdesk_agent.api.routes.health import router as health_router
from helpdesk_agent.api.routes.chat import router as chat_router
from helpdesk_agent.api.routes.tickets import router as tickets_router

# Setup logging with PII scrubbing
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Helpdesk Agent API",
    description="AI-powered helpdesk agent with RAG, tool execution, and escalation capabilities",
    version="1.0.0"
)

# Include routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(tickets_router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "Helpdesk Agent API",
        "version": "1.0.0",
        "endpoints": [
            "GET /health - Liveness check",
            "GET /metrics - Prometheus metrics",
            "POST /chat - Send message to agent",
            "GET /tickets/{ticket_id} - Get ticket details"
        ]
    }