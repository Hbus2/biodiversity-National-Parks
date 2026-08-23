"""
shared.py
---------
Pieces used by BOTH pages (dashboard + gallery): light-theme styling,
data loading, iNaturalist photos, name cleanup, and the species photo card.
"""

from pathlib import Path

import requests
import streamlit as st

from data_utils import load_data, resolve_columns


BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "national_park.csv"


# ============================================================
# COLOR PALETTE
# ============================================================

PALETTE = [
    "#2176C9",
    "#2D8AE1",
    "#70ADE7",
    "#EE4E56",
    "#B4B4AA",
    "#5FA05F",
    "#15569B",
]

ACCENT = "#2176C9"

TEXT = "#1F2329"

MUTED = "#6B7280"

CARD_BG = "#FFFFFF"


_NA_TOKENS = {
    "",
    "na",
    "n/a",
    "none",
    "null",
    "unknown",
    "-",
}


# ============================================================
# CSS / DASHBOARD STYLING
# ============================================================

def inject_css():
    """
    Light theme styling.

    Call once per page after st.set_page_config().
    """

    st.markdown(
        """
        <style>

          /* Main app background */
          .stApp {
              background-color: #F4F5F7;
          }


          /* Sidebar */
          section[data-testid="stSidebar"] {
              background-color: #FFFFFF;
              border-right: 1px solid #E2E5E9;
          }


          /* Main content spacing */
          .block-container {
              padding-top: 1.6rem;
              padding-bottom: 2rem;
              max-width: 1500px;
          }


          /* Headings */
          h1, h2, h3, h4, h5 {
              color: #1F2329;
              font-family: 'Segoe UI', sans-serif;
          }


          /* Dashboard title */
          .dash-title {
              font-size: 26px;
              font-weight: 700;
              color: #1F2329;
              margin-bottom: 2px;
          }


          /* Dashboard subtitle */
          .dash-sub {
              font-size: 13px;
              color: #6B7280;
              margin-bottom: 14px;
          }


          /* Main card containers */
          [data-testid="stVerticalBlockBorderWrapper"] {
              background-color: #FFFFFF;
              border: 1px solid #E2E5E9 !important;
              border-radius: 12px;
              padding: 8px 14px 14px 14px;
              box-shadow: 0 1px 3px rgba(16,24,40,0.06);
          }


          /* Card title */
          .card-title {
              font-size: 15px;
              font-weight: 700;
              color: #1F2329;
              margin: 4px 0 2px 0;
              font-family: 'Segoe UI', sans-serif;
          }


          /* Card subtitle */
          .card-sub {
              font-size: 11.5px;
              color: #6B7280;
              margin: 0 0 6px 0;
          }


          /* ==================================================
             KPI CARDS
             ================================================== */

          .kpi-row {
              display: flex;
              gap: 12px;
              margin-bottom: 14px;
          }


          .kpi-card {
              flex: 1;
              background: #FFFFFF;
              border: 1px solid #E2E5E9;
              border-radius: 12px;
              padding: 14px 16px;

              display: flex;
              align-items: center;
              gap: 12px;

              box-shadow: 0 1px 3px rgba(16,24,40,0.06);
          }


          .kpi-icon {
              width: 40px;
              height: 40px;
              border-radius: 10px;
              flex: none;

              display: flex;
              align-items: center;
              justify-content: center;

              font-size: 19px;
              font-weight: 700;
          }


          .kpi-label {
              color: #6B7280;
              font-size: 12px;
              font-weight: 600;
          }


          .kpi-value {
              color: #1F2329;
              font-size: 23px;
              font-weight: 700;
              line-height: 1.15;
          }


          /* ==================================================
             SPECIES PHOTO CARDS
             ================================================== */

          .sp-name {
              color: #1F2329;
              font-weight: 700;
              font-size: 13px;
              margin-top: 6px;
              line-height: 1.2;
          }


          .sp-sci {
              color: #6B7280;
              font-style: italic;
              font-size: 11.5px;
              margin-top: 1px;
          }


          .noimg {
              height: 120px;

              border: 1px solid #E2E5E9;
              border-radius: 8px;

              background: #FAFAFB;

              display: flex;
              align-items: center;
              justify-content: center;

              color: #9AA0A6;
              font-size: 12px;
          }


          /* ==================================================
             DONUT CHART LEGEND
             ================================================== */

          .lg-wrap {
              display: grid;
              grid-template-columns: 1fr 1fr;
              gap: 4px 16px;

              margin-top: 6px;
              min-height: 58px;
          }


          .lg-item {
              display: flex;
              align-items: center;
              gap: 7px;

              font-size: 11.5px;
              min-width: 0;
          }


          .lg-dot {
              width: 10px;
              height: 10px;
              border-radius: 3px;
              flex: none;
          }


          .lg-label {
              color: #374151;

              flex: 1;
              min-width: 0;

              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
          }


          .lg-pct {
              color: #6B7280;
              font-weight: 600;
          }


          /* ==================================================
             STREAMLIT WIDGET LABELS
             ================================================== */

          section[data-testid="stSidebar"] label,
          .stSelectbox label,
          .stMultiSelect label,
          .stTextInput label {

              color: #374151 !important;

              font-weight: 600 !important;

              font-size: 13px !important;
          }


          /* Selected multiselect tags */
          span[data-baseweb="tag"] {
              background-color: #2176C9 !important;
              color: #FFFFFF !important;
          }


          /* Alert styling */
          [data-testid="stAlert"] {
              background-color: #EAF2FB !important;
              border: 1px solid #BBD6F2 !important;
          }


          [data-testid="stAlert"] * {
              color: #1F4E79 !important;
          }


          /* Captions */
          [data-testid="stCaptionContainer"] p {
              color: #6B7280 !important;
          }


          /* Sidebar links */
          section[data-testid="stSidebar"]
          a[data-testid="stPageLink-NavLink"] {

              color: #374151 !important;
              font-weight: 600;
          }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def get_data(path=DATA_PATH):

    df = load_data(path)

    return (
        df,
        resolve_columns(df),
    )


# ============================================================
# COMMON NAME CLEANUP
# ============================================================

def clean_common_name(com):

    c = str(
        com or ""
    ).strip()

    if c.lower() in _NA_TOKENS:

        return ""

    return c


# ============================================================
# INATURALIST PHOTO LOOKUP
# ============================================================

@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def inat_photo(name):

    """
    Search iNaturalist for a species and return
    its default photo URL.

    No API key is required for this request.
    """

    name = str(
        name or ""
    ).strip()


    if not name:

        return None


    try:

        response = requests.get(

            "https://api.inaturalist.org/v1/taxa",

            params={
                "q": name,
                "per_page": 1,
            },

            headers={
                "User-Agent":
                    "NPS-Biodiversity-Dashboard/1.0 "
                    "(educational use)"
            },

            timeout=8,
        )


        # Request failed
        if response.status_code != 200:

            return None


        results = response.json().get(
            "results",
            [],
        )


        if not results:

            return None


        # Get default photo information
        photo = (
            results[0].get(
                "default_photo"
            )
            or {}
        )


        # Prefer medium photo
        url = (
            photo.get("medium_url")
            or photo.get("square_url")
        )


        return url


    except requests.RequestException:

        return None


    except Exception:

        return None


# ============================================================
# SPECIES PHOTO URL
# ============================================================

def species_photo_url(
    sci,
    com,
):

    """
    First try the scientific name.

    If that doesn't find an image,
    try the common name.
    """

    url = inat_photo(
        sci
    )


    if not url and com:

        url = inat_photo(
            com
        )


    return url


# ============================================================
# SPECIES CARD
# ============================================================

def species_card(
    sci,
    com,
):

    sci = str(
        sci or ""
    ).strip()


    com = clean_common_name(
        com
    )


    # Find species photo
    url = species_photo_url(
        sci,
        com,
    )


    # --------------------------------------------------------
    # PHOTO
    # --------------------------------------------------------

    if url:

        st.image(
            url,
            use_container_width=True,
        )

    else:

        st.markdown(

            "<div class='noimg'>"
            "No photo"
            "</div>",

            unsafe_allow_html=True,
        )


    # --------------------------------------------------------
    # PRIMARY DISPLAY NAME
    # --------------------------------------------------------

    primary = (
        com
        if com
        else sci
    )


    st.markdown(

        f"<div class='sp-name'>"
        f"{primary}"
        f"</div>",

        unsafe_allow_html=True,
    )


    # --------------------------------------------------------
    # SCIENTIFIC NAME
    # --------------------------------------------------------

    if com and sci:

        st.markdown(

            f"<div class='sp-sci'>"
            f"{sci}"
            f"</div>",

            unsafe_allow_html=True,
        )
