"""
pages/1_Species_Gallery.py
--------------------------

Full-page species photo gallery.

Users can:
- Search for a species
- Search for a National Park
- Search naturally, such as:
    "bears in Yellowstone"
    "birds in Grand Canyon"
    "mammals in Yosemite"

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
# OPENAI CLIENT
# ============================================================

@st.cache_resource
def get_openai_client():
    """
    Creates one reusable OpenAI client.

    API key is loaded from:

    .streamlit/secrets.toml
    """

    return OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )


# ============================================================
# SMART SEARCH
# ============================================================

def interpret_search(
    query,
    park_options,
    category_options,
):
    """
    Converts a natural-language search into the filters
    already used by the Species Gallery.

    Examples:

        Yellowstone

        bears in Yellowstone

        birds in Grand Canyon

        mammals in Yosemite
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

Your only job is to translate the user's search into the
filters used by the application.

AVAILABLE PARKS:

{park_text}

AVAILABLE SPECIES CATEGORIES:

{category_text}

RULES:

1. The park must match one of the AVAILABLE PARKS exactly.

2. The category must match one of the AVAILABLE SPECIES
   CATEGORIES exactly.

3. Understand casual park names and abbreviations.

Examples:

"Grand Canyon"
should match the appropriate Grand Canyon National Park.

"Yellowstone"
should match Yellowstone National Park.

"Smoky Mountains"
should match Great Smoky Mountains National Park.

4. Understand singular and plural animal categories.

Examples:

bird
birds

mammal
mammals

reptile
reptiles

fish

5. If the user specifies an individual animal or species,
   put a concise searchable term in "species".

Examples:

"bears in Yellowstone"
species = "bear"

"eagles in Grand Canyon"
species = "eagle"

"black bear"
species = "black bear"

6. Do not invent parks.

7. Do not invent categories.

8. If the user does not specify a park, use null.

9. If the user does not specify a category, use null.

10. If the user does not specify an individual species,
    use null.

Return ONLY valid JSON.

Use exactly this structure:

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
    # VALIDATE RETURNED VALUES
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
# TEXT CLEANING
# ============================================================

def clean_text_value(value):
    """
    Convert dataframe values into clean display text.

    Handles:
    - None
    - NaN
    - blank strings
    """

    if value is None:
        return ""

    try:

        if value != value:
            return ""

    except Exception:
        pass

    text = str(
        value
    ).strip()

    if text.lower() in {
        "",
        "nan",
        "none",
        "<na>",
    }:
        return ""

    return text


# ============================================================
# SPECIES LOOKUP KEY
# ============================================================

def species_lookup_key(
    scientific_name,
    common_names,
):
    """
    Create a consistent species key.

    Scientific name is preferred because it is generally
    more reliable for matching a species across parks.
    """

    scientific_name = clean_text_value(
        scientific_name
    )

    common_names = clean_text_value(
        common_names
    )

    if scientific_name:

        return (
            "scientific",
            scientific_name.casefold(),
        )

    if common_names:

        return (
            "common",
            common_names.casefold(),
        )

    return None


# ============================================================
# BUILD SPECIES -> PARK LOOKUP
# ============================================================

def build_species_park_lookup(
    source_df,
    column_map,
):
    """
    Creates a mapping between each species and every
    National Park where that species appears.

    Example:

    Ursus americanus
        -> Great Smoky Mountains National Park
        -> Yellowstone National Park
        -> Yosemite National Park
    """

    lookup = {}

    park_column = column_map.get(
        "park_name"
    )

    scientific_column = column_map.get(
        "sci_name"
    )

    common_column = column_map.get(
        "common_names"
    )

    if not park_column:
        return lookup

    for _, source_row in source_df.iterrows():

        scientific_name = ""

        common_names = ""

        if scientific_column:

            scientific_name = (
                source_row.get(
                    scientific_column,
                    "",
                )
            )

        if common_column:

            common_names = (
                source_row.get(
                    common_column,
                    "",
                )
            )

        key = species_lookup_key(
            scientific_name,
            common_names,
        )

        if key is None:
            continue

        park_name = clean_text_value(
            source_row.get(
                park_column,
                "",
            )
        )

        if not park_name:
            continue

        if key not in lookup:

            lookup[
                key
            ] = set()

        lookup[
            key
        ].add(
            park_name
        )

    return {

        key: sorted(
            parks
        )

        for key, parks in lookup.items()
    }


# ============================================================
# PARK DISPLAY UNDER SPECIES
# ============================================================

def render_species_parks(
    park_names,
):
    """
    Display National Park information underneath
    each species card.

    This version intentionally keeps the HTML aligned
    to the left so Streamlit renders it as HTML instead
    of displaying the markup as code.
    """

    if not park_names:
        return

    cleaned_parks = []

    for park in park_names:

        cleaned_park = clean_text_value(
            park
        )

        if cleaned_park:

            cleaned_parks.append(
                cleaned_park
            )

    if not cleaned_parks:
        return

    # --------------------------------------------------------
    # ONE PARK
    # --------------------------------------------------------

    if len(cleaned_parks) == 1:

        label = "National Park"

        park_text = (
            cleaned_parks[0]
        )

    # --------------------------------------------------------
    # MULTIPLE PARKS
    # --------------------------------------------------------

    else:

        label = "National Parks"

        park_text = ", ".join(
            cleaned_parks
        )

    label = html.escape(
        label
    )

    park_text = html.escape(
        park_text
    )

    # IMPORTANT:
    # HTML starts at the far left.
    # This prevents Streamlit Markdown from interpreting
    # the HTML as a code block.

    park_html = f"""
<div style="margin-top:8px; padding-top:9px; border-top:1px solid #ECEFF1;">
<div style="font-size:10px; line-height:1.2; font-weight:600; text-transform:uppercase; letter-spacing:0.45px; color:#9299A1; margin-bottom:4px;">
{label}
</div>
<div style="font-size:12px; line-height:1.45; font-weight:500; color:#5C646C; padding-bottom:2px;">
{park_text}
</div>
</div>
"""

    st.markdown(
        park_html,
        unsafe_allow_html=True,
    )


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
# LOAD DATA
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


if "smart_species_query" not in st.session_state:

    st.session_state[
        "smart_species_query"
    ] = ""


if "gallery_page" not in st.session_state:

    st.session_state[
        "gallery_page"
    ] = 1


if "search_error" not in st.session_state:

    st.session_state[
        "search_error"
    ] = ""


# ============================================================
# SEARCH CALLBACK
# ============================================================

def run_smart_search():

    query = st.session_state.get(
        "smart_species_query",
        "",
    ).strip()

    if not query:

        st.session_state[
            "search_error"
        ] = (
            "Enter a species or National Park to search."
        )

        return

    try:

        result = interpret_search(
            query,
            park_options,
            category_options,
        )

        # ----------------------------------------------------
        # PARK FILTER
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
        # CATEGORY FILTER
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
        # SPECIES FILTER
        # ----------------------------------------------------

        if result["species"]:

            st.session_state[
                "gallery_species_search"
            ] = result["species"]

        else:

            st.session_state[
                "gallery_species_search"
            ] = ""

        # ----------------------------------------------------
        # RETURN TO PAGE 1
        # ----------------------------------------------------

        st.session_state[
            "gallery_page"
        ] = 1

        # ----------------------------------------------------
        # CLEAR PREVIOUS ERROR
        # ----------------------------------------------------

        st.session_state[
            "search_error"
        ] = ""

    except json.JSONDecodeError:

        st.session_state[
            "search_error"
        ] = (
            "The search could not be understood. "
            "Try another search."
        )

    except Exception as error:

        st.session_state[
            "search_error"
        ] = (
            f"Search could not be completed: "
            f"{error}"
        )


# ============================================================
# CLEAR SEARCH
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
        "smart_species_query"
    ] = ""

    st.session_state[
        "gallery_page"
    ] = 1

    st.session_state[
        "search_error"
    ] = ""


# ============================================================
# MAIN SEARCH
# ============================================================

st.sidebar.markdown(
    "## Search"
)

st.sidebar.text_input(
    "Search species or National Park",
    placeholder="Species or National Park...",
    key="smart_species_query",
)

st.sidebar.button(
    "Search",
    use_container_width=True,
    on_click=run_smart_search,
)


# ============================================================
# SEARCH ERROR
# ============================================================

if st.session_state.get(
    "search_error"
):

    st.sidebar.error(
        st.session_state[
            "search_error"
        ]
    )


st.sidebar.button(
    "Clear Search",
    use_container_width=True,
    on_click=clear_gallery_search,
)

st.sidebar.divider()


# ============================================================
# FILTERS
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
    "Empty filters show all species."
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


# ============================================================
# SPECIES -> PARK LOOKUP
# ============================================================

species_park_lookup = (
    build_species_park_lookup(
        fdf,
        cols,
    )
)


# ============================================================
# SPECIES LIST
# ============================================================

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
    'Explore species found throughout '
    'the National Parks. Photos via iNaturalist.'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# PARK BANNER
# ============================================================

if len(selected_parks) == 1:

    park_banner_text = (
        selected_parks[0]
    )

elif len(selected_parks) > 1:

    park_banner_text = (
        f"{len(selected_parks)} National Parks Selected"
    )

else:

    park_banner_text = (
        "All National Parks"
    )


park_banner_text = html.escape(
    str(park_banner_text)
)


park_banner_html = (
    '<div style="'
    'background:transparent;'
    'border-bottom:1px solid #E4E7EA;'
    'padding:16px 0 15px 0;'
    'margin-top:18px;'
    'margin-bottom:20px;'
    '">'
    '<div style="'
    'font-size:12px;'
    'font-weight:500;'
    'color:#7A828A;'
    'margin-bottom:3px;'
    'letter-spacing:0.2px;'
    '">'
    'Currently viewing'
    '</div>'
    '<div style="'
    'font-size:23px;'
    'line-height:1.25;'
    'font-weight:650;'
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


# ============================================================
# NO RESULTS
# ============================================================

if total == 0:

    st.info(
        "No species match the current search or filters."
    )

    st.stop()


# ============================================================
# NUMBER OF PAGES
# ============================================================

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
<div class="card-sub" style="margin-top:28px;">
Showing {start + 1}-{end} of {total:,} species
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


# ============================================================
# RENDER SPECIES CARDS
# ============================================================

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

                # --------------------------------------------
                # SPECIES INFORMATION
                # --------------------------------------------

                scientific_name = (
                    clean_text_value(
                        row.get(
                            "Scientific name",
                            "",
                        )
                    )
                )

                common_names = (
                    clean_text_value(
                        row.get(
                            "Common names",
                            "",
                        )
                    )
                )


                # --------------------------------------------
                # EXISTING SPECIES PHOTO CARD
                # --------------------------------------------

                species_card(
                    scientific_name,
                    common_names,
                )


                # --------------------------------------------
                # FIND NATIONAL PARK(S)
                # --------------------------------------------

                lookup_key = (
                    species_lookup_key(
                        scientific_name,
                        common_names,
                    )
                )

                park_names = (
                    species_park_lookup.get(
                        lookup_key,
                        [],
                    )
                )


                # --------------------------------------------
                # DISPLAY NATIONAL PARK(S)
                # --------------------------------------------

                render_species_parks(
                    park_names
                )
