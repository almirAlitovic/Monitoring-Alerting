import os
import requests
import argparse
from requests.auth import HTTPBasicAuth
import json

# ----------------- ARGUMENTS -----------------
parser = argparse.ArgumentParser(description="Create Jira Service Management incident.")
parser.add_argument("--email", required=True, help="User email for API authentication")
args = parser.parse_args()

EMAIL = args.email

# ----------------- ENV VARIABLES -----------------
JSM_SITE = os.getenv("JSM_SITE")
API_TOKEN = os.getenv("API_TOKEN")
PROJECT_KEY = os.getenv("PROJECT_KEY")
EMAIL = "almir.alitovic@logicpulse.ba"

auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# ----------------- CREATE INCIDENT -----------------
url = f"{JSM_SITE}/rest/api/3/issue"
payload = json.dumps({
    "fields": {
        "project": {"key": PROJECT_KEY},
        "summary": "Test Incident from API",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                "type": "paragraph",
                "content": [
                    {
                    "type": "text",
                    "text": "This incident is created via API for testing."
                    }
                ]
                }
            ]
        },
        "issuetype" : {"id": "10049"}
    }
})

response = requests.post(url, data=payload, headers=headers, auth=auth)

if response.status_code == 201:
    print("Incident created successfully:", response.json()["key"])
else:
    print("Error:", response.status_code, response.text)
