"""
shared.py
---------
Pieces used by BOTH pages (dashboard + gallery):
- Light-theme styling
- Data loading
- iNaturalist photos
- Name cleanup
- Species photo cards
"""

from pathlib import Path

import requests
import streamlit as st

from data_utils import load_data, resolve_columns


# ============================================================
# PATHS
# ============================================================

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


# Values treated as missing common names
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
# APPLICATION CSS
# ============================================================

def inject_css():
    """
    Apply consistent light-theme styling.

    Call once on every Streamlit page after st.set_page_config().
    """

    st.markdown(
        """
        <style>

        /* =====================================================
           GLOBAL APPLICATION
           ===================================================== */

        html,
        body,
        [data-testid="stAppViewContainer"],
        .stApp {
            background-color: #F4F5F7 !important;
            color: #1F2329 !important;
        }


        /*
        Extra top spacing prevents the dashboard title from
        getting clipped underneath Streamlit's toolbar.
        */
        .block-container {
            padding-top: 3.5rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 1500px !important;
        }


        /* =====================================================
           STREAMLIT HEADER
           ===================================================== */

        header[data-testid="stHeader"] {
            background-color: #FFFFFF !important;
            border-bottom: 1px solid #E2E5E9 !important;
        }


        [data-testid="stToolbar"] {
            background-color: #FFFFFF !important;
        }


        [data-testid="stToolbar"] button {
            color: #374151 !important;
        }


        [data-testid="stHeaderActionElements"] {
            color: #374151 !important;
        }


        /* =====================================================
           SIDEBAR
           ===================================================== */

        section[data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E5E9 !important;
        }


        section[data-testid="stSidebar"] > div {
            background-color: #FFFFFF !important;
        }


        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #1F2329 !important;
        }


        section[data-testid="stSidebar"] p {
            color: #374151;
        }


        /* =====================================================
           SIDEBAR NAVIGATION
           ===================================================== */

        section[data-testid="stSidebar"]
        a[data-testid="stPageLink-NavLink"] {
            color: #374151 !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }


        section[data-testid="stSidebar"]
        a[data-testid="stPageLink-NavLink"]:hover {
            background-color: #EEF4FB !important;
            color: #2176C9 !important;
        }


        section[data-testid="stSidebar"]
        a[data-testid="stPageLink-NavLink"][aria-current="page"] {
            background-color: #EAF2FB !important;
            color: #2176C9 !important;
        }


        /* =====================================================
           HEADINGS
           ===================================================== */

        h1,
        h2,
        h3,
        h4,
        h5,
        h6 {
            color: #1F2329 !important;
            font-family: "Segoe UI", Arial, sans-serif !important;
        }


        /* =====================================================
           DASHBOARD HEADER
           ===================================================== */

        .dash-title {
            color: #1F2329 !important;
            font-family: "Segoe UI", Arial, sans-serif !important;

            font-size: 30px !important;
            font-weight: 700 !important;

            line-height: 1.25 !important;

            margin-top: 0 !important;
            margin-bottom: 4px !important;

            padding-top: 2px !important;
        }


        .dash-sub {
            color: #6B7280 !important;

            font-size: 14px !important;

            margin-top: 0 !important;
            margin-bottom: 18px !important;
        }


        /* =====================================================
           GENERAL CARD CONTAINERS
           ===================================================== */

        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF !important;

            border: 1px solid #E2E5E9 !important;
            border-radius: 12px !important;

            padding: 8px 14px 14px 14px !important;

            box-shadow:
                0 1px 3px rgba(16, 24, 40, 0.06) !important;
        }


        .card-title {
            color: #1F2329 !important;

            font-family: "Segoe UI", Arial, sans-serif !important;

            font-size: 15px !important;
            font-weight: 700 !important;

            margin: 4px 0 2px 0 !important;
        }


        .card-sub {
            color: #6B7280 !important;

            font-size: 11.5px !important;

            margin: 0 0 6px 0 !important;
        }


        /* =====================================================
           KPI / SCORE CARDS
           ===================================================== */

        .kpi-row {
            display: grid !important;

            grid-template-columns:
                repeat(4, minmax(0, 1fr)) !important;

            gap: 14px !important;

            width: 100% !important;

            margin-top: 4px !important;
            margin-bottom: 16px !important;
        }


        .kpi-card {
            background-color: #FFFFFF !important;

            border: 1px solid #E2E5E9 !important;
            border-radius: 12px !important;

            min-height: 100px !important;

            padding: 17px 20px !important;

            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;

            box-shadow:
                0 1px 3px rgba(16, 24, 40, 0.06) !important;

            transition:
                transform 0.15s ease,
                box-shadow 0.15s ease !important;
        }


        .kpi-card:hover {
            transform: translateY(-1px);

            box-shadow:
                0 3px 8px rgba(16, 24, 40, 0.08) !important;
        }


        .kpi-label {
            color: #6B7280 !important;

            font-size: 12px !important;
            font-weight: 600 !important;

            text-transform: uppercase !important;
            letter-spacing: 0.035em !important;

            margin-bottom: 7px !important;
        }


        .kpi-value {
            color: #1F2329 !important;

            font-size: 30px !important;
            font-weight: 700 !important;

            line-height: 1.05 !important;
        }


        /* =====================================================
           SIDEBAR / FORM LABELS
           ===================================================== */

        label,
        section[data-testid="stSidebar"] label,
        .stSelectbox label,
        .stMultiSelect label,
        .stTextInput label {
            color: #374151 !important;

            font-size: 13px !important;
            font-weight: 600 !important;
        }


        /* =====================================================
           TEXT INPUTS
           ===================================================== */

        div[data-baseweb="input"],
        div[data-baseweb="base-input"] {
            background-color: #FFFFFF !important;

            border-color: #D1D5DB !important;

            color: #1F2329 !important;
        }


        div[data-baseweb="input"] input,
        div[data-baseweb="base-input"] input,
        .stTextInput input {
            background-color: #FFFFFF !important;

            color: #1F2329 !important;

            -webkit-text-fill-color: #1F2329 !important;
        }


        div[data-baseweb="input"] input::placeholder,
        div[data-baseweb="base-input"] input::placeholder,
        .stTextInput input::placeholder {
            color: #9CA3AF !important;

            -webkit-text-fill-color: #9CA3AF !important;

            opacity: 1 !important;
        }


        /* =====================================================
           SELECT BOX / MULTISELECT
           ===================================================== */

        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;

            border-color: #D1D5DB !important;

            color: #1F2329 !important;
        }


        div[data-baseweb="select"] span {
            color: #1F2329 !important;
        }


        div[data-baseweb="select"] input {
            color: #1F2329 !important;

            -webkit-text-fill-color: #1F2329 !important;
        }


        div[data-baseweb="select"] svg {
            fill: #6B7280 !important;
        }


        /* =====================================================
           SELECT DROPDOWN MENU
           ===================================================== */

        div[data-baseweb="popover"] {
            background-color: #FFFFFF !important;
        }


        div[data-baseweb="popover"] > div {
            background-color: #FFFFFF !important;
        }


        ul[role="listbox"] {
            background-color: #FFFFFF !important;

            color: #1F2329 !important;
        }


        li[role="option"] {
            background-color: #FFFFFF !important;

            color: #1F2329 !important;
        }


        li[role="option"]:hover {
            background-color: #EEF4FB !important;

            color: #2176C9 !important;
        }


        /* =====================================================
           MULTISELECT SELECTED TAGS
           ===================================================== */

        span[data-baseweb="tag"] {
            background-color: #2176C9 !important;

            color: #FFFFFF !important;
        }


        span[data-baseweb="tag"] * {
            color: #FFFFFF !important;
        }


        /* =====================================================
           BUTTONS
           ===================================================== */

        .stButton > button {
            background-color: #FFFFFF !important;

            color: #2176C9 !important;

            border: 1px solid #BBD6F2 !important;

            border-radius: 8px !important;
        }


        .stButton > button:hover {
            background-color: #EAF2FB !important;

            border-color: #2176C9 !important;
        }


        /* =====================================================
           ALERTS / INFO BOXES
           ===================================================== */

        [data-testid="stAlert"] {
            background-color: #EAF2FB !important;

            border: 1px solid #BBD6F2 !important;

            border-radius: 6px !important;
        }


        [data-testid="stAlert"] * {
            color: #1F4E79 !important;
        }


        /* =====================================================
           CAPTIONS
           ===================================================== */

        [data-testid="stCaptionContainer"] p {
            color: #6B7280 !important;
        }


        /* =====================================================
           DATAFRAMES
           ===================================================== */

        [data-testid="stDataFrame"] {
            background-color: #FFFFFF !important;
        }


        /* =====================================================
           SPECIES PHOTO CARDS
           ===================================================== */

        .sp-name {
            color: #1F2329 !important;

            font-size: 13px !important;
            font-weight: 700 !important;

            line-height: 1.2 !important;

            margin-top: 7px !important;
        }


        .sp-sci {
            color: #6B7280 !important;

            font-size: 11.5px !important;
            font-style: italic !important;

            margin-top: 2px !important;
        }


        .noimg {
            height: 120px !important;

            background-color: #FAFAFB !important;

            border: 1px solid #E2E5E9 !important;
            border-radius: 8px !important;

            display: flex !important;
            align-items: center !important;
            justify-content: center !important;

            color: #9AA0A6 !important;

            font-size: 12px !important;
        }


        /* Make Streamlit images fit nicely inside cards */

        [data-testid="stImage"] img {
            border-radius: 8px !important;
            object-fit: cover !important;
        }


        /* =====================================================
           DONUT CHART LEGEND
           ===================================================== */

        .lg-wrap {
            display: grid !important;

            grid-template-columns:
                1fr 1fr !important;

            gap: 4px 16px !important;

            margin-top: 6px !important;

            min-height: 58px !important;
        }


        .lg-item {
            display: flex !important;

            align-items: center !important;

            gap: 7px !important;

            font-size: 11.5px !important;

            min-width: 0 !important;
        }


        .lg-dot {
            width: 10px !important;
            height: 10px !important;

            border-radius: 3px !important;

            flex: none !important;
        }


        .lg-label {
            color: #374151 !important;

            flex: 1 !important;

            min-width: 0 !important;

            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }


        .lg-pct {
            color: #6B7280 !important;

            font-weight: 600 !important;
        }


        /* =====================================================
           DIVIDERS
           ===================================================== */

        hr {
            border-color: #E5E7EB !important;
        }


        /* =====================================================
           RESPONSIVE KPI CARDS
           ===================================================== */

        @media (max-width: 900px) {

            .kpi-row {
                grid-template-columns:
                    repeat(2, minmax(0, 1fr)) !important;
            }

        }


        @media (max-width: 550px) {

            .kpi-row {
                grid-template-columns:
                    1fr !important;
            }

            .dash-title {
                font-size: 25px !important;
            }

        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data
def get_data(path=DATA_PATH):
    """
    Load the National Parks dataset and resolve its column names.
    """

    df = load_data(path)

    return df, resolve_columns(df)


# ============================================================
# COMMON NAME CLEANUP
# ============================================================

def clean_common_name(com):
    """
    Clean common-name values and treat common NA tokens as blank.
    """

    c = str(com or "").strip()

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
    Search iNaturalist for a taxon and return its default photo.

    The public taxa endpoint does not require an API key.
    """

    name = str(name or "").strip()

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


        if response.status_code != 200:
            return None


        results = response.json().get(
            "results",
            [],
        )


        if not results:
            return None


        photo = (
            results[0].get(
                "default_photo"
            )
            or {}
        )


        return (
            photo.get("medium_url")
            or photo.get("square_url")
        )


    except requests.RequestException:
        return None


    except Exception:
        return None


# ============================================================
# SPECIES PHOTO LOOKUP
# ============================================================

def species_photo_url(sci, com):
    """
    Try to locate a species image.

    Scientific name is searched first.
    Common name is used as a fallback.
    """

    url = inat_photo(sci)

    if not url and com:
        url = inat_photo(com)

    return url


# ============================================================
# SPECIES CARD
# ============================================================

def species_card(sci, com):
    """
    Render one species photo card.
    """

    sci = str(
        sci or ""
    ).strip()


    com = clean_common_name(
        com
    )


    # Find species image
    url = species_photo_url(
        sci,
        com,
    )


    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    if url:

        st.image(
            url,
            use_container_width=True,
        )

    else:

        st.markdown(
            """
            <div class="noimg">
                No photo
            </div>
            """,
            unsafe_allow_html=True,
        )


    # --------------------------------------------------------
    # DISPLAY NAME
    # --------------------------------------------------------

    primary = (
        com
        if com
        else sci
    )


    st.markdown(
        f"""
        <div class="sp-name">
            {primary}
        </div>
        """,
        unsafe_allow_html=True,
    )


    # --------------------------------------------------------
    # SCIENTIFIC NAME
    # --------------------------------------------------------

    if com and sci:

        st.markdown(
            f"""
            <div class="sp-sci">
                {sci}
            </div>
            """,
            unsafe_allow_html=True,
        )
