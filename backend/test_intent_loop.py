import httpx
import time
# import sys

URL = 'https://emektup-api-staging-393070663679.europe-west1.run.app/api/payments/create-intent'
PAYLOAD = {'order_id': '7XiTlh4ILPL1NBYioLyK'}
HEADERS = {'Origin': 'http://localhost:5173', 'Content-Type': 'application/json'}

def poll():
    print("Waiting for deployment... (expecting 400 or 200)", flush=True)
    while True:
        try:
            r = httpx.post(URL, json=PAYLOAD, headers=HEADERS, timeout=10.0)
            if r.status_code != 500:
                print(f"\nDEPLOYED! Status: {r.status_code}")
                print(f"Body: {r.text}")
                break
            else:
                print(".", end="", flush=True)
                time.sleep(10)
        except httpx.RequestError as e:
            print(f"X({e})", end="", flush=True)
            time.sleep(10)

if __name__ == '__main__':
    poll()
