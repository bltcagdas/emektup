import httpx
import sys

try:
    print("Sending POST request to Staging...", flush=True)
    r = httpx.post(
        'https://emektup-api-staging-393070663679.europe-west1.run.app/api/payments/create-intent',
        json={'order_id': '7XiTlh4ILPL1NBYioLyK'},
        headers={'Origin': 'http://localhost:5173', 'Content-Type': 'application/json'},
        timeout=10.0
    )
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text}")
except Exception as e:
    print(f"Exception: {str(e)}")
