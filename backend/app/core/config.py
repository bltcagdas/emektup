# import json
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Emektup Backend"
    ENV: str = "dev"
    FIREBASE_SERVICE_ACCOUNT_PATH: str = ""
    FIREBASE_SERVICE_ACCOUNT_JSON: str = ""
    FIREBASE_PROJECT_ID: str = "emektup"
    ALLOWED_ORIGINS: str = '["http://localhost:5173", "http://localhost:3000"]'
    
    # Payment Configs
    IYZICO_ENV: str = "sandbox"
    IYZICO_API_KEY: str = "mock_api_key"
    IYZICO_SECRET_KEY: str = "mock_secret_key"
    IYZICO_BASE_URL: str = "https://sandbox-api.iyzipay.com"

    # Background Jobs / OPS Security Configs
    OPS_AUDIENCE_URL: str = "https://mock-ops-url.run.app"
    OPS_SERVICE_ACCOUNT_EMAIL: str = "ops-service-account@emektup.iam.gserviceaccount.com"
    
    @property
    def get_allowed_origins(self) -> list[str]:
        # Provide a robust parser for environments that strip or inject unexpected quotes
        cleaned = self.ALLOWED_ORIGINS.strip().strip("'").strip('"')
        if cleaned.startswith("["):
            try:
                import json
                return json.loads(cleaned.replace("'", '"'))
            except Exception:
                pass
        # Fallback to comma separation
        return [x.strip() for x in cleaned.split(",")] if cleaned else []
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
