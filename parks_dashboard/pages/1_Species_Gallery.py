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
import re

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
    Create one reusable OpenAI client.

    API key is loaded from:
    .streamlit/secrets.toml
    """

    return OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )


# ============================================================
# CACHED DATA LOADER
# ============================================================

@st.cache_data(show_spinner=False)
def load_gallery_data(path):
    """
    Cache the source dataset so Streamlit does not reload
    the CSV every time a widget causes a rerun.
    """

    return get_data(path)


# ============================================================
# SEARCH INTERPRETER
# ============================================================

@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def interpret_search(
    query,
    park_options,
    category_options,
):
    """
    Convert natural-language searches into gallery filters.

    Search results are cached for 24 hours so repeated
    searches do not require another API request.
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

Your job is to translate the user's search into filters used
by the application.

AVAILABLE PARKS:

{park_text}

AVAILABLE SPECIES CATEGORIES:

{category_text}

RULES:

1. The park must match one of the AVAILABLE PARKS exactly.

2. The category must match one of the AVAILABLE SPECIES
   CATEGORIES exactly.

3. Understand casual park names.

Examples:

"Grand Canyon"
should match Grand Canyon National Park.

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

5. If the user specifies an animal or species, put the
   meaningful animal name in "species".

Examples:

"bear"
species = "bear"

"bears"
species = "bear"

"deer"
species = "deer"

"eagle"
species = "eagle"

"bears in Yellowstone"
species = "bear"

"black bears in Yellowstone"
species = "black bear"

"white tailed deer"
species = "white tailed deer"

6. Do not return unrelated broader terms.

7. Do not invent parks.

8. Do not invent categories.

9. If the user does not specify a park, use null.

10. If the user does not specify a category, use null.

11. If the user does not specify an individual animal or
    species, use null.

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

    park = result.get("park")
    category = result.get("category")
    species = result.get("species")

    # Validate park
    if park not in park_options:
        park = None

    # Validate category
    if category not in category_options:
        category = None

    # Clean species
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
# CLEAN TEXT
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
# SMART SPECIES SEARCH
# ============================================================

@st.cache_data(show_spinner=False)
def apply_smart_species_search(
    source_df,
    column_map,
    search_term,
):
    """
    Apply word-aware matching to scientific and common names.
    """

    search_term = clean_text_value(
        search_term
    )

    if not search_term:
        return source_df

    scientific_column = column_map.get(
        "sci_name"
    )

    common_column = column_map.get(
        "common_names"
    )

    search_term = (
        search_term
        .strip()
        .casefold()
    )

    # --------------------------------------------------------
    # BASIC PLURAL NORMALIZATION
    # --------------------------------------------------------

    simple_plural_map = {
        "bears": "bear",
        "deer": "deer",
        "eagles": "eagle",
        "wolves": "wolf",
        "foxes": "fox",
        "elk": "elk",
        "moose": "moose",
        "birds": "bird",
        "snakes": "snake",
        "frogs": "frog",
        "toads": "toad",
        "rabbits": "rabbit",
        "hares": "hare",
        "squirrels": "squirrel",
        "mice": "mouse",
        "ducks": "duck",
        "hawks": "hawk",
        "owls": "owl",
    }

    search_term = simple_plural_map.get(
        search_term,
        search_term,
    )

    # --------------------------------------------------------
    # WORD-AWARE REGEX
    # --------------------------------------------------------

    escaped_term = re.escape(
        search_term
    )

    escaped_term = escaped_term.replace(
        r"\ ",
        r"[\s\-]+",
    )

    pattern = (
        rf"(?<!\w){escaped_term}(?!\w)"
    )

    masks = []

    # --------------------------------------------------------
    # COMMON NAME SEARCH
    # --------------------------------------------------------

    if common_column:

        common_mask = (
            source_df[common_column]
            .fillna("")
            .astype(str)
            .str.contains(
                pattern,
                case=False,
                regex=True,
                na=False,
            )
        )

        masks.append(
            common_mask
        )

    # --------------------------------------------------------
    # SCIENTIFIC NAME SEARCH
    # --------------------------------------------------------

    if scientific_column:

        scientific_mask = (
            source_df[scientific_column]
            .fillna("")
            .astype(str)
            .str.contains(
                pattern,
                case=False,
                regex=True,
                na=False,
            )
        )

        masks.append(
            scientific_mask
        )

    if not masks:
        return source_df

    final_mask = masks[0]

    for mask in masks[1:]:

        final_mask = (
            final_mask
            | mask
        )

    return source_df[
        final_mask
    ].copy()


# ============================================================
# SPECIES LOOKUP KEY
# ============================================================

def species_lookup_key(
    scientific_name,
    common_names,
):
    """
    Create a consistent key for matching species
    back to the source dataframe.

    Scientific name is preferred.
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
# OPTIMIZED / VECTORIZED
# ============================================================

@st.cache_data(show_spinner=False)
def build_species_park_lookup(
    source_df,
    column_map,
):
    """
    Create a mapping containing every National Park
    associated with each species.

    This version avoids iterating over every dataframe
    row with iterrows(), which improves rerun performance.
    """

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
        return {}

    temp = source_df.copy()

    # --------------------------------------------------------
    # CLEAN PARK
    # --------------------------------------------------------

    temp["_park"] = (
        temp[park_column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # CLEAN SCIENTIFIC NAME
    # --------------------------------------------------------

    if scientific_column:

        temp["_scientific"] = (
            temp[scientific_column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    else:

        temp["_scientific"] = ""

    # --------------------------------------------------------
    # CLEAN COMMON NAME
    # --------------------------------------------------------

    if common_column:

        temp["_common"] = (
            temp[common_column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    else:

        temp["_common"] = ""

    # --------------------------------------------------------
    # REMOVE INVALID TEXT VALUES
    # --------------------------------------------------------

    invalid_values = {
        "",
        "nan",
        "none",
        "<na>",
    }

    scientific_invalid = (
        temp["_scientific"]
        .str.casefold()
        .isin(invalid_values)
    )

    common_invalid = (
        temp["_common"]
        .str.casefold()
        .isin(invalid_values)
    )

    park_invalid = (
        temp["_park"]
        .str.casefold()
        .isin(invalid_values)
    )

    temp.loc[
        scientific_invalid,
        "_scientific",
    ] = ""

    temp.loc[
        common_invalid,
        "_common",
    ] = ""

    temp.loc[
        park_invalid,
        "_park",
    ] = ""

    # --------------------------------------------------------
    # SPECIES LOOKUP TYPE
    # --------------------------------------------------------

    temp["_key_type"] = "scientific"

    temp.loc[
        temp["_scientific"] == "",
        "_key_type",
    ] = "common"

    # --------------------------------------------------------
    # SPECIES LOOKUP VALUE
    # --------------------------------------------------------

    temp["_key_value"] = (
        temp["_scientific"]
        .str.casefold()
    )

    use_common = (
        temp["_scientific"] == ""
    )

    temp.loc[
        use_common,
        "_key_value",
    ] = (
        temp.loc[
            use_common,
            "_common",
        ]
        .str.casefold()
    )

    # --------------------------------------------------------
    # REMOVE RECORDS WITHOUT USABLE SPECIES/PARK
    # --------------------------------------------------------

    temp = temp[
        (temp["_key_value"] != "")
        & (temp["_park"] != "")
    ]

    if temp.empty:
        return {}

    # --------------------------------------------------------
    # GROUP PARKS BY SPECIES
    # --------------------------------------------------------

    grouped = (
        temp.groupby(
            [
                "_key_type",
                "_key_value",
            ],
            sort=False,
        )["_park"]
        .agg(
            lambda values: sorted(
                set(values)
            )
        )
    )

    return {
        (
            key_type,
            key_value,
        ): parks

        for (
            key_type,
            key_value,
        ), parks in grouped.items()
    }


# ============================================================
# CACHED SPECIES LIST
# ============================================================

@st.cache_data(show_spinner=False)
def get_species_list_cached(
    source_df,
    column_map,
):
    """
    Cache species-list generation.
    """

    return species_list(
        source_df,
        column_map,
    )


# ============================================================
# CACHED STANDARD FILTER
# ============================================================

@st.cache_data(show_spinner=False)
def apply_gallery_filters_cached(
    source_df,
    column_map,
    selected_parks,
    selected_categories,
    search_text,
):
    """
    Cache the standard dataframe filtering step.
    """

    return apply_filters(
        source_df,
        column_map,
        selected_parks,
        selected_categories,
        search_text,
    )


# ============================================================
# PARK DISPLAY UNDER SPECIES
# ============================================================

def render_species_parks(
    park_names,
):
    """
    Display National Park information underneath
    each species card.
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

    if len(cleaned_parks) == 1:

        label = "National Park"

        park_text = cleaned_parks[0]

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

    park_html = f"""
<div style="
    margin-top:8px;
    padding-top:9px;
    border-top:1px solid #ECEFF1;
">
    <div style="
        font-size:10px;
        line-height:1.2;
        font-weight:600;
        text-transform:uppercase;
        letter-spacing:0.45px;
        color:#9299A1;
        margin-bottom:4px;
    ">
        {label}
    </div>

    <div style="
        font-size:12px;
        line-height:1.45;
        font-weight:500;
        color:#5C646C;
        padding-bottom:2px;
    ">
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

st.sidebar.page_link(
    "pages/2_Species_Guide.py",
    label="Species Guide",
)

st.sidebar.divider()


# ============================================================
# LOAD DATA
# ============================================================

try:

    df, cols = load_gallery_data(
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

park_options = list(
    unique_values(
        df,
        cols["park_name"],
    )
)

category_options = list(
    unique_values(
        df,
        cols["category"],
    )
)


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "gallery_park_filter": [],
    "gallery_category_filter": [],
    "gallery_species_search": "",
    "smart_species_query": "",
    "smart_species_term": "",
    "gallery_page": 1,
    "search_error": "",
}

for key, default_value in defaults.items():

    if key not in st.session_state:

        st.session_state[
            key
        ] = default_value


# ============================================================
# SMART SEARCH FUNCTION
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
            tuple(park_options),
            tuple(category_options),
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
        # SMART SPECIES TERM
        # ----------------------------------------------------

        if result["species"]:

            st.session_state[
                "smart_species_term"
            ] = result["species"]

        else:

            st.session_state[
                "smart_species_term"
            ] = ""

        # Prevent old manual search from interfering
        st.session_state[
            "gallery_species_search"
        ] = ""

        # Return to first page
        st.session_state[
            "gallery_page"
        ] = 1

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
            f"Search could not be completed: {error}"
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
        "smart_species_term"
    ] = ""

    st.session_state[
        "gallery_page"
    ] = 1

    st.session_state[
        "search_error"
    ] = ""


# ============================================================
# SMART SEARCH FORM
# ============================================================

st.sidebar.markdown(
    "## Search"
)

with st.sidebar.form(
    "gallery_smart_search_form",
    clear_on_submit=False,
):

    st.text_input(
        "Search species or National Park",
        placeholder="Species or National Park...",
        key="smart_species_query",
    )

    smart_search_submitted = st.form_submit_button(
        "Search",
        use_container_width=True,
    )


# IMPORTANT:
# This runs BEFORE the filter widgets below are created,
# which allows us to safely update their session-state values.

if smart_search_submitted:

    run_smart_search()


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


# ============================================================
# CLEAR SEARCH BUTTON
# ============================================================

st.sidebar.button(
    "Clear Search",
    use_container_width=True,
    on_click=clear_gallery_search,
)

st.sidebar.divider()


# ============================================================
# FILTER FORM
# ============================================================

st.sidebar.markdown(
    "## Filters"
)

with st.sidebar.form(
    "gallery_filters_form",
    clear_on_submit=False,
):

    selected_parks = st.multiselect(
        "Park name",
        park_options,
        placeholder="All parks",
        key="gallery_park_filter",
    )

    selected_categories = st.multiselect(
        "Category",
        category_options,
        placeholder="All categories",
        key="gallery_category_filter",
    )

    search_text = st.text_input(
        "Search species",
        placeholder="Scientific or common name...",
        key="gallery_species_search",
    )

    filters_submitted = st.form_submit_button(
        "Apply Filters",
        use_container_width=True,
    )


if filters_submitted:

    # Clear AI-generated species term so manual filtering
    # becomes the active filter mode.

    st.session_state[
        "smart_species_term"
    ] = ""

    st.session_state[
        "gallery_page"
    ] = 1


st.sidebar.caption(
    "Empty filters show all species."
)


# ============================================================
# CURRENT FILTER VALUES
# ============================================================

selected_parks = st.session_state.get(
    "gallery_park_filter",
    [],
)

selected_categories = st.session_state.get(
    "gallery_category_filter",
    [],
)

search_text = st.session_state.get(
    "gallery_species_search",
    "",
)


# ============================================================
# APPLY STANDARD FILTERS
# ============================================================

fdf = apply_gallery_filters_cached(
    df,
    cols,
    tuple(selected_parks),
    tuple(selected_categories),
    search_text,
)


# ============================================================
# APPLY SMART SPECIES SEARCH
# ============================================================

fdf = apply_smart_species_search(
    fdf,
    cols,
    st.session_state.get(
        "smart_species_term",
        "",
    ),
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

sp_df = get_species_list_cached(
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

# Reduced from 25.
# Rendering fewer species cards per page makes interaction
# noticeably lighter, especially if species_card() performs
# an iNaturalist lookup.
PER_PAGE = 15

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
                # SPECIES PHOTO CARD
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
