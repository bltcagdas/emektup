import httpx
# import time
# import sys

def trigger_webhook():
    print("Firing Webhook to Staging API...")
    url = "https://emektup-api-staging-393070663679.europe-west1.run.app/api/payments/webhook"
    
    payload = {
        "token": "c3fd5e11-0515-46f6-9d1b-1365840343d4",
        "status": "SUCCESS",
        "paymentId": "PRISTINE_MOCK_PAYMENT",
        "conversationId": "KlZtur7PnhH4s7oVjKPo"
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-iyz-signature": "mock_valid_signature"
    }
    
    r = httpx.post(url, json=payload, headers=headers)
    print(f"\nWebhook response status: {r.status_code}")
    print(f"Webhook response body: {r.text}")

if __name__ == "__main__":
    trigger_webhook()
