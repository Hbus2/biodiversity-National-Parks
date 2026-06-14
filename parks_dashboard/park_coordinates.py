"""
park_coordinates.py
-------------------
Approximate center coordinates (latitude, longitude) for U.S. National Parks,
used to plot each park on the dashboard map.

These are park-center approximations meant for a zoomed-out national map, not
survey-grade points. The lookup normalizes names, so "Yellowstone National
Park", "Yellowstone NP", and "yellowstone" all resolve to the same entry.

To add a park the dashboard reports as missing, just add one line to
_PARK_COORDS below in the form:   "Exact Park Name": (lat, lon),
"""

import re

# Full canonical park name -> (latitude, longitude)
_PARK_COORDS = {
    "Acadia National Park": (44.35, -68.21),
    "Arches National Park": (38.68, -109.57),
    "Badlands National Park": (43.75, -102.50),
    "Big Bend National Park": (29.25, -103.25),
    "Biscayne National Park": (25.65, -80.08),
    "Black Canyon of the Gunnison National Park": (38.57, -107.72),
    "Bryce Canyon National Park": (37.57, -112.18),
    "Canyonlands National Park": (38.20, -109.93),
    "Capitol Reef National Park": (38.20, -111.17),
    "Carlsbad Caverns National Park": (32.17, -104.44),
    "Channel Islands National Park": (34.01, -119.42),
    "Congaree National Park": (33.78, -80.78),
    "Crater Lake National Park": (42.94, -122.10),
    "Cuyahoga Valley National Park": (41.24, -81.55),
    "Death Valley National Park": (36.24, -116.82),
    "Denali National Park and Preserve": (63.13, -151.00),
    "Dry Tortugas National Park": (24.63, -82.87),
    "Everglades National Park": (25.32, -80.93),
    "Gates of the Arctic National Park and Preserve": (67.78, -153.30),
    "Glacier National Park": (48.76, -113.79),
    "Glacier Bay National Park and Preserve": (58.67, -136.90),
    "Grand Canyon National Park": (36.11, -112.11),
    "Grand Teton National Park": (43.79, -110.68),
    "Great Basin National Park": (38.98, -114.30),
    "Great Sand Dunes National Park and Preserve": (37.73, -105.51),
    "Great Smoky Mountains National Park": (35.61, -83.49),
    "Guadalupe Mountains National Park": (31.92, -104.87),
    "Haleakala National Park": (20.72, -156.17),
    "Hawaii Volcanoes National Park": (19.42, -155.29),
    "Hot Springs National Park": (34.51, -93.05),
    "Isle Royale National Park": (48.00, -88.91),
    "Joshua Tree National Park": (33.87, -115.90),
    "Katmai National Park and Preserve": (58.60, -154.80),
    "Kenai Fjords National Park": (59.92, -149.65),
    "Kings Canyon National Park": (36.89, -118.56),
    "Kobuk Valley National Park": (67.55, -159.28),
    "Lake Clark National Park and Preserve": (60.97, -153.42),
    "Lassen Volcanic National Park": (40.50, -121.42),
    "Mammoth Cave National Park": (37.19, -86.10),
    "Mesa Verde National Park": (37.23, -108.46),
    "Mount Rainier National Park": (46.85, -121.76),
    "North Cascades National Park": (48.77, -121.30),
    "Olympic National Park": (47.80, -123.60),
    "Petrified Forest National Park": (34.91, -109.81),
    "Pinnacles National Park": (36.49, -121.18),
    "Redwood National Park": (41.21, -124.00),
    "Rocky Mountain National Park": (40.34, -105.68),
    "Saguaro National Park": (32.25, -110.50),
    "Sequoia and Kings Canyon National Parks": (36.49, -118.57),
    "Sequoia National Park": (36.49, -118.57),
    "Shenandoah National Park": (38.49, -78.43),
    "Theodore Roosevelt National Park": (46.98, -103.54),
    "Voyageurs National Park": (48.48, -92.83),
    "Wind Cave National Park": (43.57, -103.48),
    "Wrangell - St Elias National Park and Preserve": (61.71, -142.99),
    "Yellowstone National Park": (44.43, -110.59),
    "Yosemite National Park": (37.87, -119.54),
    "Zion National Park": (37.30, -113.03),
    # A few newer parks (in case your export includes them)
    "Gateway Arch National Park": (38.62, -90.18),
    "Indiana Dunes National Park": (41.65, -87.05),
    "White Sands National Park": (32.78, -106.17),
    "New River Gorge National Park and Preserve": (38.07, -81.08),
}

# Tokens stripped during normalization so spelling/suffix differences still match
_STRIP_TOKENS = [
    "national park and preserve",
    "national park & preserve",
    "national parks",
    "national park",
    "national preserve",
    "and preserve",
    "preserve",
]


def _norm(name) -> str:
    """Lowercase, drop punctuation and common park suffixes, collapse spaces."""
    s = str(name).lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    for token in _STRIP_TOKENS:
        s = s.replace(token, " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Pre-normalized lookup built once at import
_NORM_LOOKUP = {_norm(k): v for k, v in _PARK_COORDS.items()}


def get_coordinates(name):
    """Return (lat, lon) for a park name, or None if it isn't in the table."""
    return _NORM_LOOKUP.get(_norm(name))
