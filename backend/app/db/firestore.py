import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from app.core.config import settings

def init_firebase():
    """Initialize Firebase Admin SDK."""
    if not firebase_admin._apps:
        json_creds = settings.FIREBASE_SERVICE_ACCOUNT_JSON
        cred_path = settings.FIREBASE_SERVICE_ACCOUNT_PATH
        
        if json_creds:
            cred_dict = json.loads(json_creds)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'projectId': settings.FIREBASE_PROJECT_ID,
            })
            print("Firebase Admin SDK initialized successfully via Secret Manager JSON.")
        elif cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {
                'projectId': settings.FIREBASE_PROJECT_ID,
            })
            print("Firebase Admin SDK initialized successfully via local JSON file.")
        else:
            # Fallback for Cloud Run ADC emulator or default credentials
            print(f"Warning: Firebase service account key not found. Initializing with application default credentials.")
            firebase_admin.initialize_app(options={'projectId': settings.FIREBASE_PROJECT_ID})

def get_db():
    """Retrieve the Firestore client wrapper."""
    return firestore.client()
