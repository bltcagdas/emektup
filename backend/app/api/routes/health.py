from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def check_health():
    # Additional checks like DB connection could be added here
    return {"status": "ok", "message": "Service is healthy"}
