"""
pages/2_Species_Guide.py
------------------------

Interactive Species Guide.

Species are selected from the National Parks biodiversity
dataset.

External factual information is retrieved from iNaturalist
and Wikipedia.

OpenAI is then used only to summarize the retrieved source
information into a concise visitor-friendly description.
"""

import html

import streamlit as st
from openai import OpenAI

from shared import (
    inject_css,
    get_data,
    DATA_PATH,
)

from data_utils import (
    species_list,
)

from species_info import (
    get_species_reference,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Species Guide",
    layout="wide",
)

inject_css()


# ============================================================
# OPENAI CLIENT
# ============================================================

@st.cache_resource
def get_openai_client():

    return OpenAI(
        api_key=st.secrets[
            "OPENAI_API_KEY"
        ]
    )


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text_value(value):

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
# LOAD NATIONAL PARK DATASET
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
# CREATE MASTER SPECIES LIST
# ============================================================

sp_df = species_list(
    df,
    cols,
)


# ============================================================
# BUILD SEARCH OPTIONS
# ============================================================

species_options = []

species_lookup = {}


for _, row in sp_df.iterrows():

    common_name = clean_text_value(
        row.get(
            "Common names",
            "",
        )
    )

    scientific_name = clean_text_value(
        row.get(
            "Scientific name",
            "",
        )
    )

    if not (
        common_name
        or scientific_name
    ):

        continue

    # --------------------------------------------------------
    # DISPLAY NAME
    # --------------------------------------------------------

    if (
        common_name
        and scientific_name
    ):

        display_name = (
            f"{common_name} "
            f"({scientific_name})"
        )

    elif common_name:

        display_name = (
            common_name
        )

    else:

        display_name = (
            scientific_name
        )

    species_options.append(
        display_name
    )

    species_lookup[
        display_name
    ] = {
        "common_name": common_name,
        "scientific_name": scientific_name,
    }


species_options = sorted(
    set(
        species_options
    ),
    key=str.casefold,
)


# ============================================================
# DATASET SPECIES DETAILS
# ============================================================

def get_dataset_species_details(
    scientific_name,
    common_name,
):
    """
    Retrieve National Park-specific information from
    our own CSV.

    This is the source of truth for which of our parks
    contain the species.
    """

    scientific_column = cols.get(
        "sci_name"
    )

    common_column = cols.get(
        "common_names"
    )

    park_column = cols.get(
        "park_name"
    )

    category_column = cols.get(
        "category"
    )

    nativeness_column = cols.get(
        "nativeness"
    )

    occurrence_column = cols.get(
        "occurrence"
    )

    abundance_column = cols.get(
        "abundance"
    )

    species_rows = df.copy()

    # --------------------------------------------------------
    # MATCH BY SCIENTIFIC NAME FIRST
    # --------------------------------------------------------

    if (
        scientific_column
        and scientific_name
    ):

        species_rows = species_rows[
            species_rows[
                scientific_column
            ]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.casefold()
            == scientific_name.casefold()
        ]

    # --------------------------------------------------------
    # FALLBACK TO COMMON NAME
    # --------------------------------------------------------

    elif (
        common_column
        and common_name
    ):

        species_rows = species_rows[
            species_rows[
                common_column
            ]
            .fillna("")
            .astype(str)
            .str.contains(
                common_name,
                case=False,
                regex=False,
                na=False,
            )
        ]

    # --------------------------------------------------------
    # HELPER FOR UNIQUE VALUES
    # --------------------------------------------------------

    def unique_clean_values(
        column_name,
    ):

        if (
            not column_name
            or column_name
            not in species_rows.columns
        ):

            return []

        values = []

        for value in (
            species_rows[
                column_name
            ]
            .dropna()
            .tolist()
        ):

            cleaned = (
                clean_text_value(
                    value
                )
            )

            if (
                cleaned
                and cleaned
                not in values
            ):

                values.append(
                    cleaned
                )

        return sorted(
            values,
            key=str.casefold,
        )

    return {
        "parks": (
            unique_clean_values(
                park_column
            )
        ),
        "categories": (
            unique_clean_values(
                category_column
            )
        ),
        "nativeness": (
            unique_clean_values(
                nativeness_column
            )
        ),
        "occurrence": (
            unique_clean_values(
                occurrence_column
            )
        ),
        "abundance": (
            unique_clean_values(
                abundance_column
            )
        ),
        "row_count": len(
            species_rows
        ),
    }


# ============================================================
# EXTERNAL REFERENCE LOOKUP
# ============================================================

@st.cache_data(
    ttl=60 * 60 * 24,
    show_spinner=False,
)
def cached_species_reference(
    scientific_name,
    common_name,
):

    return get_species_reference(
        scientific_name,
        common_name,
    )


# ============================================================
# AI SUMMARY
# ============================================================

@st.cache_data(
    ttl=60 * 60 * 24 * 7,
    show_spinner=False,
)
def create_species_summary(
    scientific_name,
    common_name,
    wikipedia_extract,
    inaturalist_common_name,
    iconic_taxon,
):
    """
    Create a visitor-friendly summary based ONLY on retrieved
    factual information.

    The model is explicitly told not to add outside facts.
    """

    if not wikipedia_extract:

        return ""

    client = get_openai_client()

    source_text = f"""
SCIENTIFIC NAME:
{scientific_name}

COMMON NAME FROM DATASET:
{common_name}

INATURALIST COMMON NAME:
{inaturalist_common_name}

INATURALIST TAXON GROUP:
{iconic_taxon}

REFERENCE ARTICLE:

{wikipedia_extract}
"""

    prompt = f"""
You are writing a species guide for an educational
U.S. National Parks biodiversity application.

Use ONLY the factual source information supplied below.

Do not rely on your own knowledge.

Do not invent:
- habitat
- diet
- behavior
- size
- lifespan
- conservation status
- geographic range
- interesting facts

unless the supplied source explicitly supports them.

Write a concise, visitor-friendly summary.

Requirements:

1. Write 2 to 3 short paragraphs.
2. Explain what the species is.
3. Include notable characteristics or behavior only when
   supported by the supplied source.
4. Keep the tone educational and easy to understand.
5. Do not mention Wikipedia, iNaturalist, the prompt,
   source text, or AI.
6. Do not use bullet points.
7. Do not make claims that are absent from the source.

SOURCE INFORMATION:

{source_text}
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt,
        max_output_tokens=450,
    )

    return (
        response
        .output_text
        .strip()
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
    'Search species from the National Parks dataset '
    'to learn more about them and discover where '
    'they occur across the parks.'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# SEARCH AREA
# ============================================================

st.markdown(
    """
<div style="
    margin-top:25px;
    margin-bottom:8px;
    font-size:14px;
    font-weight:600;
    color:#1F2329;
">
Search Species
</div>
""",
    unsafe_allow_html=True,
)


selected_species = st.selectbox(
    "Species",
    options=species_options,
    index=None,
    placeholder=(
        "Type a common or scientific name..."
    ),
    label_visibility="collapsed",
)


# ============================================================
# NOTHING SELECTED YET
# ============================================================

if not selected_species:

    st.markdown(
        """
<div style="
    margin-top:40px;
    padding:32px 0;
    border-top:1px solid #E4E7EA;
    color:#7A828A;
    font-size:14px;
">
Select a species above to open its guide.
</div>
""",
        unsafe_allow_html=True,
    )

    st.stop()


# ============================================================
# SELECTED SPECIES
# ============================================================

selected = species_lookup[
    selected_species
]


common_name = selected[
    "common_name"
]


scientific_name = selected[
    "scientific_name"
]


# ============================================================
# GET DATASET INFORMATION
# ============================================================

dataset_info = (
    get_dataset_species_details(
        scientific_name,
        common_name,
    )
)


# ============================================================
# GET EXTERNAL INFORMATION
# ============================================================

with st.spinner(
    "Loading species information..."
):

    reference = (
        cached_species_reference(
            scientific_name,
            common_name,
        )
    )


inat = (
    reference.get(
        "inaturalist"
    )
    or {}
)


wiki = (
    reference.get(
        "wikipedia"
    )
    or {}
)


# ============================================================
# PREFERRED DISPLAY NAME
# ============================================================

inat_common_name = (
    clean_text_value(
        inat.get(
            "common_name"
        )
    )
)


display_common_name = (
    common_name
    or inat_common_name
    or scientific_name
)


# ============================================================
# IMAGE
# ============================================================

image_url = (
    clean_text_value(
        inat.get(
            "image_url"
        )
    )
    or clean_text_value(
        wiki.get(
            "image_url"
        )
    )
)


# ============================================================
# PAGE DIVIDER
# ============================================================

st.markdown(
    """
<div style="
    border-top:1px solid #E4E7EA;
    margin-top:25px;
    margin-bottom:30px;
"></div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HERO SECTION
# ============================================================

left_col, right_col = st.columns(
    [1, 1.7],
    gap="large",
)


# ============================================================
# PHOTO
# ============================================================

with left_col:

    if image_url:

        st.image(
            image_url,
            use_container_width=True,
        )

        attribution = (
            clean_text_value(
                inat.get(
                    "photo_attribution"
                )
            )
        )

        if attribution:

            st.caption(
                attribution
            )

    else:

        st.info(
            "No reference photo was available "
            "for this species."
        )


# ============================================================
# SPECIES TITLE
# ============================================================

with right_col:

    safe_common_name = html.escape(
        display_common_name
    )

    safe_scientific_name = (
        html.escape(
            scientific_name
        )
    )

    st.markdown(
        f"""
<div style="
    font-size:32px;
    line-height:1.15;
    font-weight:700;
    color:#1F2329;
    margin-bottom:5px;
">
{safe_common_name}
</div>
""",
        unsafe_allow_html=True,
    )

    if scientific_name:

        st.markdown(
            f"""
<div style="
    font-size:17px;
    font-style:italic;
    color:#687078;
    margin-bottom:24px;
">
{safe_scientific_name}
</div>
""",
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # QUICK DETAILS
    # --------------------------------------------------------

    categories = dataset_info[
        "categories"
    ]

    iconic_taxon = clean_text_value(
        inat.get(
            "iconic_taxon"
        )
    )

    if categories:

        category_display = ", ".join(
            categories
        )

    elif iconic_taxon:

        category_display = (
            iconic_taxon
        )

    else:

        category_display = (
            "Not available"
        )

    parks = dataset_info[
        "parks"
    ]

    stat1, stat2 = st.columns(
        2
    )

    with stat1:

        st.markdown(
            "**Category**"
        )

        st.write(
            category_display
        )

    with stat2:

        st.markdown(
            "**National Parks in Dataset**"
        )

        st.write(
            len(parks)
        )


# ============================================================
# GENERATE SUMMARY
# ============================================================

wikipedia_extract = (
    clean_text_value(
        wiki.get(
            "extract"
        )
    )
)


summary = ""


if wikipedia_extract:

    try:

        with st.spinner(
            "Preparing species summary..."
        ):

            summary = (
                create_species_summary(
                    scientific_name,
                    common_name,
                    wikipedia_extract,
                    inat_common_name,
                    iconic_taxon,
                )
            )

    except Exception:

        # If OpenAI cannot generate the summary,
        # show the factual reference text instead.

        summary = wikipedia_extract


# ============================================================
# ABOUT
# ============================================================

st.markdown(
    "### About"
)


if summary:

    st.write(
        summary
    )

elif wikipedia_extract:

    st.write(
        wikipedia_extract
    )

else:

    st.info(
        "Reference information was not available "
        "for this species."
    )


# ============================================================
# NATIONAL PARKS
# ============================================================

st.markdown(
    "### Found in the National Parks Dataset"
)


parks = dataset_info[
    "parks"
]


if parks:

    park_html = ""

    for park in parks:

        safe_park = html.escape(
            park
        )

        park_html += (
            '<div style="'
            'padding:8px 0;'
            'border-bottom:1px solid #F0F1F2;'
            'font-size:14px;'
            'color:#3E454C;'
            '">'
            f'{safe_park}'
            '</div>'
        )

    st.markdown(
        park_html,
        unsafe_allow_html=True,
    )

else:

    st.write(
        "No park information was available."
    )


# ============================================================
# DATASET DETAILS
# ============================================================

st.markdown(
    "### Dataset Details"
)


detail_columns = st.columns(
    3
)


# ------------------------------------------------------------
# NATIVENESS
# ------------------------------------------------------------

with detail_columns[0]:

    st.markdown(
        "**Nativeness**"
    )

    nativeness = dataset_info[
        "nativeness"
    ]

    if nativeness:

        st.write(
            ", ".join(
                nativeness
            )
        )

    else:

        st.write(
            "Not available"
        )


# ------------------------------------------------------------
# OCCURRENCE
# ------------------------------------------------------------

with detail_columns[1]:

    st.markdown(
        "**Occurrence**"
    )

    occurrence = dataset_info[
        "occurrence"
    ]

    if occurrence:

        st.write(
            ", ".join(
                occurrence
            )
        )

    else:

        st.write(
            "Not available"
        )


# ------------------------------------------------------------
# ABUNDANCE
# ------------------------------------------------------------

with detail_columns[2]:

    st.markdown(
        "**Abundance**"
    )

    abundance = dataset_info[
        "abundance"
    ]

    if abundance:

        st.write(
            ", ".join(
                abundance
            )
        )

    else:

        st.write(
            "Not available"
        )


# ============================================================
# SOURCES
# ============================================================

st.markdown(
    "### Reference Sources"
)


source_available = False


inat_url = clean_text_value(
    inat.get(
        "taxon_url"
    )
)


wiki_url = clean_text_value(
    wiki.get(
        "url"
    )
)


source_cols = st.columns(
    2
)


if inat_url:

    source_available = True

    with source_cols[0]:

        st.link_button(
            "View on iNaturalist",
            inat_url,
            use_container_width=True,
        )


if wiki_url:

    source_available = True

    with source_cols[1]:

        st.link_button(
            "View reference article",
            wiki_url,
            use_container_width=True,
        )


if not source_available:

    st.caption(
        "No external reference links were available."
    )


# ============================================================
# SOURCE NOTE
# ============================================================

st.caption(
    "National Park occurrence and dataset details come "
    "from the biodiversity dataset used by this application. "
    "Species descriptions are generated from retrieved "
    "reference information rather than generated from "
    "unverified model knowledge."
)
