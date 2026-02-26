from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import id_token
from google.auth.transport import requests
from app.core.config import settings
from app.core.logging import logger

security = HTTPBearer()

def verify_oidc_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verifies that the incoming request is authenticated by Cloud Tasks or Cloud Scheduler.
    It expects a valid Google OIDC token in the Authorization header.
    """
    token = credentials.credentials
    # In local development, we might want to bypass or mock this
    if settings.ENV in ["local", "development", "test"] and token == "ops-mock-token":
        logger.info("Local DEV mode: Accepted mock OIDC token.")
        return {"email": "local-dev@ops", "sub": "local"}

    audience = settings.OPS_AUDIENCE_URL # e.g. https://emektup-api-staging-xxxxxxxx-ew.a.run.app
    if not audience:
         raise HTTPException(status_code=500, detail="Server misconfiguration: OPS_AUDIENCE_URL not set")

    try:
        # Verify the token against Google's public certs
        request = requests.Request()
        claims = id_token.verify_oauth2_token(token, request, audience=audience)
        
        # Verify the issuer and email/subject
        if claims.get("email") != settings.OPS_SERVICE_ACCOUNT_EMAIL:
             logger.error(f"OIDC Verification failed: Unauthorized email target {claims.get('email')}")
             raise HTTPException(status_code=403, detail="Unauthorized OPS Service Account")
             
        # Add basic logging
        logger.info(f"OIDC verified for OPS request: {claims.get('email')}")
        return claims

    except ValueError as e:
        logger.error(f"OIDC Token Verification Error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid OPS access token")
