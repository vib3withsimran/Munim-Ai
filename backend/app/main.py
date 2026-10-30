import logging
from fastapi import FastAPI
from backend.app.core.config import settings
from backend.app.api.routes import webhook

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="Munim AI Backend",
    description="WhatsApp Assistant & Self-updating Ledger for Small Sellers",
    version="1.0.0"
)

# Include webhook route
app.include_router(webhook.router)

@app.get("/")
async def root():
    return {
        "app": "Munim AI",
        "status": "healthy",
        "env": settings.APP_ENV
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

