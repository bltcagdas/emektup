from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health, orders, admin, payments
from app.core.config import settings
from app.db.firestore import init_firebase
from app.core.logging import RequestIdMiddleware, logger
from app.core.rate_limit import setup_rate_limiting, limiter
from app.api.deps import get_current_user, require_admin

app = FastAPI(title=settings.PROJECT_NAME)

# 1. Setup Rate Limiting
setup_rate_limiting(app)

# 2. Add Middlewares (Filters top-down)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)

# 3. Application startup events
@app.on_event("startup")
def startup_event():
    init_firebase()
    logger.info("Application started and Firebase initialized.")

# 4. Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])

@app.get("/")
def root():
    return {"message": "Emektup API is running"}


