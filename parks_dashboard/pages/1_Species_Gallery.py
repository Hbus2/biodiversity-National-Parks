"""
pages/1_Species_Gallery.py
--------------------------

A full-page species photo gallery.

Filter by park / category, search by name,
or use AI to search naturally with phrases like:

    "birds in Grand Canyon"
    "mammals in Yellowstone"
    "bears in Yosemite"

Images are provided through iNaturalist.
"""

import json
import html
import streamlit as st
from openai import OpenAI

from data_utils import (
    apply_filters,
    unique_values,
    species_list,
)

from shared import (
    inject_css,
    get_data,
    species_card,
    DATA_PATH,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Species Gallery",
    layout="wide",
)

inject_css()


# ============================================================
# OPENAI
# ============================================================

@st.cache_resource
def get_openai_client():
    """
    Creates one reusable OpenAI client.

    The API key is loaded from:
    .streamlit/secrets.toml
    """

    return OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )


def interpret_ai_search(
    query,
    park_options,
    category_options,
):
    """
    Convert natural-language searches into the filters
    already used by the Species Gallery.

    Example:

        "birds in Grand Canyon"

    becomes:

        {
            "park": "Grand Canyon National Park",
            "category": "Bird",
            "species": None
        }
    """

    client = get_openai_client()

    park_text = "\n".join(
        f"- {park}"
        for park in park_options
    )

    category_text = "\n".join(
        f"- {category}"
        for category in category_options
    )

    prompt = f"""
You are a search interpreter for a biodiversity application
covering 15 highly visited U.S. National Parks.

Your ONLY job is to translate the user's natural-language
request into filters used by the application.

AVAILABLE PARKS:

{park_text}

AVAILABLE SPECIES CATEGORIES:

{category_text}

RULES:

1. The park must match one of the AVAILABLE PARKS exactly.

2. The category must match one of the AVAILABLE SPECIES
   CATEGORIES exactly.

3. Understand casual wording and abbreviations.

Examples:

"Grand Canyon"
should match the appropriate Grand Canyon park.

"Yellowstone"
should match Yellowstone National Park.

4. Understand singular and plural animal categories.

Examples:

birds -> appropriate bird category
mammals -> appropriate mammal category
reptiles -> appropriate reptile category
fish -> appropriate fish category

5. If the user specifies an individual animal or species,
   put a concise searchable term in "species".

Examples:

"bears in Yellowstone"
species = "bear"

"eagles in Grand Canyon"
species = "eagle"

6. Do NOT invent parks.

7. Do NOT invent categories.

8. If the user does not specify a park, use null.

9. If the user does not specify a category, use null.

10. If the user does not specify an individual species,
    use null.

Return ONLY valid JSON.

Use exactly this format:

{{
    "park": null,
    "category": null,
    "species": null
}}

USER SEARCH:

"{query}"
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt,
        max_output_tokens=120,
    )

    raw_response = response.output_text.strip()

    raw_response = (
        raw_response
        .replace("```json", "")
        .replace("```JSON", "")
        .replace("```", "")
        .strip()
    )

    result = json.loads(
        raw_response
    )

    park = result.get(
        "park"
    )

    category = result.get(
        "category"
    )

    species = result.get(
        "species"
    )


    # --------------------------------------------------------
    # VALIDATE AI RESULTS AGAINST REAL DATASET VALUES
    # --------------------------------------------------------

    if park not in park_options:
        park = None

    if category not in category_options:
        category = None

    if species is not None:

        species = str(
            species
        ).strip()

        if not species:
            species = None


    return {
        "park": park,
        "category": category,
        "species": species,
    }


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

st.sidebar.page_link(
    "app.py",
    label="Homepage",
)

st.sidebar.page_link(
    "pages/1_Species_Gallery.py",
    label="Species Gallery",
)

st.sidebar.divider()


# ============================================================
# DATA
# ============================================================

try:

    df, cols = get_data(
        DATA_PATH
    )

except FileNotFoundError:

    st.error(
        f"Could not find '{DATA_PATH}'. "
        f"Put your CSV in the project folder "
        f"or update DATA_PATH in shared.py."
    )

    st.stop()


# ============================================================
# FILTER OPTIONS
# ============================================================

park_options = unique_values(
    df,
    cols["park_name"],
)

category_options = unique_values(
    df,
    cols["category"],
)

park_options = list(
    park_options
)

category_options = list(
    category_options
)


# ============================================================
# SESSION STATE
# ============================================================

if "gallery_park_filter" not in st.session_state:

    st.session_state[
        "gallery_park_filter"
    ] = []


if "gallery_category_filter" not in st.session_state:

    st.session_state[
        "gallery_category_filter"
    ] = []


if "gallery_species_search" not in st.session_state:

    st.session_state[
        "gallery_species_search"
    ] = ""


if "ai_species_query" not in st.session_state:

    st.session_state[
        "ai_species_query"
    ] = ""


if "gallery_page" not in st.session_state:

    st.session_state[
        "gallery_page"
    ] = 1


if "ai_search_error" not in st.session_state:

    st.session_state[
        "ai_search_error"
    ] = ""


# ============================================================
# AI SEARCH CALLBACK
# ============================================================

def run_ai_search():

    query = st.session_state.get(
        "ai_species_query",
        "",
    ).strip()


    if not query:

        st.session_state[
            "ai_search_error"
        ] = (
            "Enter something to search for first."
        )

        return


    try:

        result = interpret_ai_search(
            query,
            park_options,
            category_options,
        )


        # ----------------------------------------------------
        # UPDATE PARK FILTER
        # ----------------------------------------------------

        if result["park"]:

            st.session_state[
                "gallery_park_filter"
            ] = [
                result["park"]
            ]

        else:

            st.session_state[
                "gallery_park_filter"
            ] = []


        # ----------------------------------------------------
        # UPDATE CATEGORY FILTER
        # ----------------------------------------------------

        if result["category"]:

            st.session_state[
                "gallery_category_filter"
            ] = [
                result["category"]
            ]

        else:

            st.session_state[
                "gallery_category_filter"
            ] = []


        # ----------------------------------------------------
        # UPDATE SPECIES SEARCH
        # ----------------------------------------------------

        if result["species"]:

            st.session_state[
                "gallery_species_search"
            ] = result["species"]

        else:

            st.session_state[
                "gallery_species_search"
            ] = ""


        # Always return to page 1 after a new search

        st.session_state[
            "gallery_page"
        ] = 1


        # Successful searches happen silently

        st.session_state[
            "ai_search_error"
        ] = ""


    except json.JSONDecodeError:

        st.session_state[
            "ai_search_error"
        ] = (
            "The AI search returned an unexpected "
            "response. Please try again."
        )


    except Exception as error:

        st.session_state[
            "ai_search_error"
        ] = (
            f"AI search could not be completed: "
            f"{error}"
        )


# ============================================================
# CLEAR SEARCH CALLBACK
# ============================================================

def clear_gallery_search():

    st.session_state[
        "gallery_park_filter"
    ] = []

    st.session_state[
        "gallery_category_filter"
    ] = []

    st.session_state[
        "gallery_species_search"
    ] = ""

    st.session_state[
        "ai_species_query"
    ] = ""

    st.session_state[
        "gallery_page"
    ] = 1

    st.session_state[
        "ai_search_error"
    ] = ""


# ============================================================
# AI SIDEBAR SEARCH
# ============================================================

st.sidebar.markdown(
    "## Find Species with AI"
)


st.sidebar.text_input(
    "What would you like to find?",
    placeholder="Try: birds in Grand Canyon",
    key="ai_species_query",
)


st.sidebar.button(
    "Search with AI",
    use_container_width=True,
    on_click=run_ai_search,
)


# ============================================================
# AI ERROR MESSAGE
# ============================================================

if st.session_state.get(
    "ai_search_error"
):

    st.sidebar.error(
        st.session_state[
            "ai_search_error"
        ]
    )


st.sidebar.button(
    "Clear Search",
    use_container_width=True,
    on_click=clear_gallery_search,
)


st.sidebar.divider()


# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.markdown(
    "## Filters"
)


selected_parks = st.sidebar.multiselect(
    "Park name",
    park_options,
    placeholder="All parks",
    key="gallery_park_filter",
)


selected_categories = st.sidebar.multiselect(
    "Category",
    category_options,
    placeholder="All categories",
    key="gallery_category_filter",
)


search_text = st.sidebar.text_input(
    "Search species",
    placeholder="Scientific or common name...",
    key="gallery_species_search",
)


st.sidebar.caption(
    "Empty filters show everything. "
    "Search matches both SciName and CommonNames."
)


# ============================================================
# APPLY FILTERS
# ============================================================

fdf = apply_filters(
    df,
    cols,
    selected_parks,
    selected_categories,
    search_text,
)


sp_df = species_list(
    fdf,
    cols,
)


# ============================================================
# PAGE HEADER
# ============================================================

st.markdown(
    '<div class="dash-title">'
    'Species Gallery'
    '</div>',
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="dash-sub">'
    'Photos via iNaturalist. '
    'Use the filters on the left '
    'to narrow the species shown.'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# PARK BANNER
# ============================================================

if len(selected_parks) == 1:

    park_banner_text = selected_parks[0]


elif len(selected_parks) > 1:

    park_banner_text = (
        f"{len(selected_parks)} National Parks Selected"
    )


else:

    park_banner_text = (
        "All National Parks"
    )


# Escape text before inserting into HTML

park_banner_text = html.escape(
    str(park_banner_text)
)


# IMPORTANT:
# This HTML is intentionally created without indented/newline
# HTML blocks. That prevents Streamlit/Markdown from treating
# the inner DIV tags as a code block.

park_banner_html = (
    '<div style="'
    'background:linear-gradient(90deg,#EAF4FC 0%,#F7FBFE 100%);'
    'border:1px solid #C9E1F4;'
    'border-radius:14px;'
    'padding:18px 24px;'
    'margin-top:20px;'
    'margin-bottom:22px;'
    'box-shadow:0 1px 2px rgba(0,0,0,0.03);'
    '">'
    '<div style="'
    'font-size:13px;'
    'font-weight:500;'
    'color:#5F6B75;'
    'margin-bottom:3px;'
    'letter-spacing:0.2px;'
    '">'
    'Currently viewing'
    '</div>'
    '<div style="'
    'font-size:26px;'
    'line-height:1.25;'
    'font-weight:700;'
    'color:#1F2329;'
    '">'
    f'{park_banner_text}'
    '</div>'
    '</div>'
)


st.markdown(
    park_banner_html,
    unsafe_allow_html=True,
)


# ============================================================
# GALLERY SETTINGS
# ============================================================

PER_ROW = 5

PER_PAGE = 25

total = len(
    sp_df
)


if total == 0:

    st.info(
        "No species match the current filters."
    )

    st.stop()


n_pages = max(
    1,
    (
        total
        + PER_PAGE
        - 1
    )
    // PER_PAGE,
)


# ============================================================
# KEEP PAGE NUMBER VALID
# ============================================================

if (
    st.session_state[
        "gallery_page"
    ]
    > n_pages
):

    st.session_state[
        "gallery_page"
    ] = 1


# ============================================================
# PAGE SELECTOR
# ============================================================

top_l, top_r = st.columns(
    [3, 1]
)


with top_r:

    page = st.number_input(
        "Page",
        min_value=1,
        max_value=n_pages,
        step=1,
        key="gallery_page",
    )


with top_l:

    start = (
        int(page) - 1
    ) * PER_PAGE

    end = min(
        start + PER_PAGE,
        total,
    )


    st.markdown(
        f"""
        <div
            class="card-sub"
            style="margin-top:28px;"
        >
            Showing {start + 1}-{end}
            of {total:,} species
            (page {int(page)} of {n_pages})
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# PHOTO GRID
# ============================================================

chunk = sp_df.iloc[
    start:end
]


rows = [

    chunk.iloc[
        i:i + PER_ROW
    ]

    for i in range(
        0,
        len(chunk),
        PER_ROW,
    )

]


for row_df in rows:

    grid_cols = st.columns(
        PER_ROW
    )


    for col, (_, row) in zip(
        grid_cols,
        row_df.iterrows(),
    ):

        with col:

            with st.container(
                border=True
            ):

                species_card(
                    row.get(
                        "Scientific name",
                        "",
                    ),
                    row.get(
                        "Common names",
                        "",
                    ),
                )
