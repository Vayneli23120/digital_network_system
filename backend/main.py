"""
Backend application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import engine, Base
from app.api import deploy_stream, deploy_history, deploy_approval


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - create tables
    from app.core.database import engine, Base
    Base.metadata.create_all(bind=engine)
    print("Database tables created/updated")
    yield
    # Shutdown


app = FastAPI(
    title="Network Automation System API",
    description="API for network device management and configuration deployment",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(deploy_stream.router, prefix="/api")
app.include_router(deploy_history.router, prefix="/api")
app.include_router(deploy_approval.router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
