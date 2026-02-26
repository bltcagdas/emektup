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
    def allowed_origins_list(self) -> list[str]:
        # Foolproof parser: strip all potential outer arrays/quotes and split by comma
        val = self.ALLOWED_ORIGINS.strip("'").strip('"').strip()
        val = val.strip("[]")
        return [x.strip().strip("'").strip('"') for x in val.split(",") if x.strip()]
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
