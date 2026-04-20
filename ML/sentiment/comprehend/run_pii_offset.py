import requests
import json

url = "https://jkwbjq5lsg7p7gpo3moftljpue0xhtgc.lambda-url.us-east-1.on.aws/"

payload = {
    "data": [
        {
            "patient_id": "P-99",
            "text": "Contact Sarah at sarah.test@outlook.com regarding her appointment on 25/12/2025."
        },
        {
            "patient_id": "P-100",
            "text": "The patient lives in Sydney and their Medicare number is 1234 56789 0."
        }
    ]
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    print("Success!")
    print(json.dumps(response.json(), indent=4))
else:
    print(f"Failed with status code: {response.status_code}")
    print(response.text)