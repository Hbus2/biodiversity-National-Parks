import streamlit as st

from shared import (
    inject_css,
    get_data,
    DATA_PATH,
)

from data_utils import species_list


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Species Guide",
    layout="wide",
)

inject_css()


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

    df, cols = get_data(
        DATA_PATH
    )

except FileNotFoundError:

    st.error(
        f"Could not find '{DATA_PATH}'."
    )

    st.stop()


# ============================================================
# CREATE SPECIES LIST
# ============================================================

sp_df = species_list(
    df,
    cols,
)


# ============================================================
# PAGE HEADER
# ============================================================

st.markdown(
    '<div class="dash-title">'
    'Species Guide'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="dash-sub">'
    'Search for a species to learn more about it '
    'and see where it appears across the National Parks.'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# CREATE DISPLAY NAMES
# ============================================================

species_options = []

species_lookup = {}


for _, row in sp_df.iterrows():

    common_name = str(
        row.get(
            "Common names",
            "",
        )
    ).strip()

    scientific_name = str(
        row.get(
            "Scientific name",
            "",
        )
    ).strip()

    if common_name.lower() in {
        "",
        "nan",
        "none",
    }:
        common_name = ""

    if scientific_name.lower() in {
        "",
        "nan",
        "none",
    }:
        scientific_name = ""

    if common_name and scientific_name:

        display_name = (
            f"{common_name} "
            f"({scientific_name})"
        )

    elif common_name:

        display_name = common_name

    elif scientific_name:

        display_name = scientific_name

    else:
        continue

    species_options.append(
        display_name
    )

    species_lookup[
        display_name
    ] = {
        "common_name": common_name,
        "scientific_name": scientific_name,
    }


# Remove duplicate display names

species_options = sorted(
    set(species_options)
)


# ============================================================
# SPECIES SEARCH
# ============================================================

selected_species = st.selectbox(
    "Search for a species",
    options=species_options,
    index=None,
    placeholder="Type a species name...",
)


# ============================================================
# DISPLAY SELECTED SPECIES
# ============================================================

if selected_species:

    species_data = species_lookup[
        selected_species
    ]

    common_name = species_data[
        "common_name"
    ]

    scientific_name = species_data[
        "scientific_name"
    ]

    st.divider()

    if common_name:

        st.markdown(
            f"## {common_name}"
        )

    if scientific_name:

        st.markdown(
            f"*{scientific_name}*"
        )

    st.info(
        "Species information will appear here."
    )
