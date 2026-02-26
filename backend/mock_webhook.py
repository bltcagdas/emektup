import httpx
import time
import sys

def trigger_webhook():
    print("Polling Webhook until deployment is live...")
    url = "https://emektup-api-staging-393070663679.europe-west1.run.app/api/payments/webhook"
    
    payload = {
        "token": "5a23a317-b62f-4b2c-aaf0-38b353bea673",
        "status": "SUCCESS",
        "paymentId": "MOCK_PAYMENT_999",
        "conversationId": "7XiTlh4ILPL1NBYioLyK"
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-iyz-signature": "mock_valid_signature"
    }
    
    while True:
        try:
            r = httpx.post(url, json=payload, headers=headers)
            if r.status_code != 500:
                print(f"\nDEPLOYED! Status: {r.status_code}")
                print(f"Body: {r.text}")
                break
            else:
                print(".", end="", flush=True)
                time.sleep(10)
        except Exception as e:
            print(f"E({e})", end="", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    trigger_webhook()
