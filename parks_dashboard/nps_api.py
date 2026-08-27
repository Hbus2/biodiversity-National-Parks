import requests
import streamlit as st


NPS_API_URL = "https://developer.nps.gov/api/v1/parks"


@st.cache_data(ttl=86400)
def get_nps_park_data(park_code):
    """
    Get National Park information from the National Park Service API.

    Cached for 24 hours so the API isn't called every time
    someone interacts with the app.
    """

    try:
        api_key = st.secrets["NPS_API_KEY"]

        params = {
            "parkCode": park_code,
            "fields": "images"
        }

        headers = {
            "X-Api-Key": api_key
        }

        response = requests.get(
            NPS_API_URL,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        results = response.json().get("data", [])

        if not results:
            return None

        park = results[0]

        images = park.get("images", [])

        photo_url = None

        if images:
            photo_url = images[0].get("url")

        return {
            "name": park.get("fullName"),
            "description": park.get("description"),
            "states": park.get("states"),
            "url": park.get("url"),
            "photo_url": photo_url,
            "images": images,
        }

    except Exception as e:
        print(f"NPS API error for {park_code}: {e}")
        return None


NPS_PARK_CODES = {
    "Acadia National Park": "acad",
    "Bryce Canyon National Park": "brca",
    "Cuyahoga Valley National Park": "cuva",
    "Grand Canyon National Park": "grca",
    "Grand Teton National Park": "grte",
    "Great Smoky Mountains National Park": "grsm",
    "Hot Springs National Park": "hosp",
    "Indiana Dunes National Park": "indu",
    "Joshua Tree National Park": "jotr",
    "Olympic National Park": "olym",
    "Rocky Mountain National Park": "romo",
    "Yellowstone National Park": "yell",
    "Yosemite National Park": "yose",
    "Zion National Park": "zion",
}
