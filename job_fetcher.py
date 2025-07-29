import requests

APP_ID = 'acb861bf'
APP_KEY = 'aa3b402d110d32be2cf914e5dc28d0f6'

def fetch_jobs_from_adzuna(role):
    url = "https://api.adzuna.com/v1/api/jobs/in/search/1"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "what": role,
        "results_per_page": 50,
        "content-type": "application/json"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return []
