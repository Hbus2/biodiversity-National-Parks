"""
test_youtube.py  -  one-off diagnostic for the YouTube API key.
Run from the parks_dashboard folder:   python3 test_youtube.py
It reads your key from .streamlit/secrets.toml, makes one real API call,
and prints exactly what Google returns so we can see what's wrong.
"""

import tomllib
import requests

# Read the key from your secrets file
with open(".streamlit/secrets.toml", "rb") as f:
    key = tomllib.load(f).get("YOUTUBE_API_KEY", "")

if not key or key.startswith("YOUR_"):
    print("No real key found in .streamlit/secrets.toml (still the placeholder).")
    raise SystemExit

print("Key found, length:", len(key), "-> starts with:", key[:6] + "...")

url = "https://www.googleapis.com/youtube/v3/search"
params = {
    "part": "snippet",
    "q": "Yellowstone National Park biodiversity wildlife",
    "type": "video",
    "maxResults": 2,
    "key": key,
}

r = requests.get(url, params=params, timeout=10)
print("\nHTTP status:", r.status_code)
print("-" * 60)
print(r.text[:2500])
