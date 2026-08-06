from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import sys
from loguru import logger
import time

from core.config import settings
from modules.auth.router import router as auth_router
from modules.bom.router import router as bom_router
from modules.inventory.router import router as inventory_router
from modules.sales.router import router as sales_router
from modules.ai_assistant.router import router as ai_router
from modules.purchasing.router import router as purchasing_router
from modules.production.router import router as production_router
from modules.mrp.router import router as mrp_router
from modules.admin.router import router as admin_router
from modules.quality.router import router as quality_router
from modules.costing.router import router as costing_router

# Configure Structured Logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

app = FastAPI(
    title=settings.APP_NAME,
    description="Deterministic multi-tenant Manufacturing Intelligence ERP API.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS for next.js app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, lock this down to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request duration logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"Method: {request.method} | Path: {request.url.path} | Status: {response.status_code} | Duration: {duration:.4f}s"
    )
    return response

# General exception handler for clean JSON responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhanded Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact system administrators."}
    )

# Register API Sub-Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(bom_router, prefix=settings.API_V1_STR)
app.include_router(inventory_router, prefix=settings.API_V1_STR)
app.include_router(sales_router, prefix=settings.API_V1_STR)
app.include_router(ai_router, prefix=settings.API_V1_STR)
app.include_router(purchasing_router, prefix=settings.API_V1_STR)
app.include_router(production_router, prefix=settings.API_V1_STR)
app.include_router(mrp_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(quality_router, prefix=settings.API_V1_STR)
app.include_router(costing_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["System Health"])
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}
