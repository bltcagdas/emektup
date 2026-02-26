import os
from google.cloud import logging

def fetch_recent_errors():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r'c:\Users\ASUS\Python\emektup\emektup-staging-ecd0ca516af6.json'
    
    # Instantiate a client
    client = logging.Client()
    
    print("Fetching last 20 ERROR logs from emektup-api-staging...")
    
    # Filter for the Cloud Run service and severity
    filter_str = 'resource.type="cloud_run_revision" AND resource.labels.service_name="emektup-api-staging" AND severity>=ERROR'
    
    entries = client.list_entries(filter_=filter_str, order_by=logging.DESCENDING, max_results=20)
    
    count = 0
    for entry in entries:
        count += 1
        print(f"[{entry.timestamp}] {entry.severity}")
        if isinstance(entry.payload, dict):
            print(f"Message: {entry.payload.get('message', entry.payload)}")
        else:
            print(f"Payload: {entry.payload}")
        print("-" * 50)
        
    if count == 0:
        print("No errors found in recent logs.")

if __name__ == "__main__":
    fetch_recent_errors()
