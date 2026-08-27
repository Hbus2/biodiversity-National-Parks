"""
app.py
------
Homepage for the National Parks Biodiversity Dashboard.

Run:
    streamlit run app.py
"""

import html
import math

import folium
import plotly.express as px
import requests
import streamlit as st
from nps_api import get_nps_park_data, NPS_PARK_CODES
from streamlit_folium import st_folium

from data_utils import (
    apply_filters,
    kpis,
    unique_values,
    value_breakdown,
    breakdown_table,
    park_accepted_table,
    species_list,
    build_park_map_df,
    rollup_top_n,
    group_category_breakdown,
    unassigned_categories,
    CATEGORY_GROUP_ORDER,
)

from park_coordinates import get_coordinates

from shared import (
    inject_css,
    get_data,
    species_card,
    DATA_PATH,
    ACCENT,
    TEXT,
    MUTED,
    PALETTE,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Parks Biodiversity Dashboard",
    layout="wide",
)

st.sidebar.page_link(
    "app.py",
    label="Homepage"
)

st.sidebar.page_link(
    "pages/1_Species_Gallery.py",
    label="Species Gallery"
)

st.sidebar.divider()

inject_css()


# ============================================================
# CHART STYLING
# ============================================================

def style_fig(
    fig,
    height=320,
    show_legend=True,
):

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",

        font=dict(
            color=TEXT,
            family="Segoe UI, sans-serif",
            size=12,
        ),

        margin=dict(
            l=10,
            r=10,
            t=10,
            b=10,
        ),

        height=height,
        showlegend=show_legend,

        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(
                color=TEXT,
                size=11,
            ),
        ),
    )

    fig.update_xaxes(
        gridcolor="#E5E7EB",
        zerolinecolor="#E5E7EB",
    )

    fig.update_yaxes(
        gridcolor="#E5E7EB",
        zerolinecolor="#E5E7EB",
    )

    return fig


# ============================================================
# DONUT CHART
# ============================================================

def render_donut(
    bd,
    center_units="records",
    n=6,
    height=240,
):

    bd = rollup_top_n(
        bd,
        n,
    )

    labels = [
        str(x)
        for x in bd["label"]
    ]

    counts = [
        int(x)
        for x in bd["count"]
    ]

    total = sum(counts)


    # --------------------------------------------------------
    # COLORS
    # --------------------------------------------------------

    colors = []
    pi = 0

    for lab in labels:

        if lab.lower() == "other":

            colors.append(
                "#C7CBD1"
            )

        else:

            colors.append(
                PALETTE[
                    pi % len(PALETTE)
                ]
            )

            pi += 1


    # --------------------------------------------------------
    # DONUT CHART
    # --------------------------------------------------------

    fig = px.pie(
        bd,
        names="label",
        values="count",
        hole=0.62,
        color_discrete_sequence=colors,
    )


    fig.update_traces(
        sort=False,
        textinfo="none",

        marker=dict(
            line=dict(
                color="#FFFFFF",
                width=2,
            )
        ),

        hovertemplate=(
            "%{label}: %{value:,} "
            "(%{percent})"
            "<extra></extra>"
        ),
    )


    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",

        showlegend=False,

        height=height,

        margin=dict(
            l=6,
            r=6,
            t=6,
            b=6,
        ),

        annotations=[
            dict(
                text=f"<b>{total:,}</b>",
                x=0.5,
                y=0.54,
                showarrow=False,

                font=dict(
                    size=18,
                    color=TEXT,
                ),
            ),

            dict(
                text=center_units,
                x=0.5,
                y=0.43,
                showarrow=False,

                font=dict(
                    size=10,
                    color=MUTED,
                ),
            ),
        ],
    )


    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False
        },
    )


    # --------------------------------------------------------
    # CUSTOM LEGEND
    # --------------------------------------------------------

    rows = ""

    for lab, c, cnt in zip(
        labels,
        colors,
        counts,
    ):

        pct = (
            cnt / total * 100
            if total
            else 0
        )

        rows += (
            f"<div class='lg-item'>"

            f"<span "
            f"class='lg-dot' "
            f"style='background:{c}'>"
            f"</span>"

            f"<span "
            f"class='lg-label' "
            f"title='{lab}'>"
            f"{lab}"
            f"</span>"

            f"<span "
            f"class='lg-pct'>"
            f"{pct:.1f}%"
            f"</span>"

            f"</div>"
        )


    st.markdown(
        f"<div class='lg-wrap'>{rows}</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# ADAPTIVE HORIZONTAL BAR CHART
# ============================================================

def hbar(
    bd,
    height=None,
    color=ACCENT,
):
    """
    Adaptive horizontal bar chart.

    The chart automatically changes height and bar thickness
    depending on how many categories are currently displayed.
    """

    n_bars = len(
        bd
    )


    # --------------------------------------------------------
    # DYNAMIC CHART HEIGHT
    # --------------------------------------------------------

    if height is None:

        if n_bars == 1:

            height = 160

        elif n_bars == 2:

            height = 190

        elif n_bars == 3:

            height = 220

        elif n_bars == 4:

            height = 250

        else:

            height = min(
                380,
                120 + (n_bars * 38),
            )


    # --------------------------------------------------------
    # DYNAMIC BAR THICKNESS
    # --------------------------------------------------------

    if n_bars == 1:

        bar_width = 0.32

    elif n_bars == 2:

        bar_width = 0.40

    elif n_bars <= 4:

        bar_width = 0.52

    else:

        bar_width = 0.64


    # --------------------------------------------------------
    # CREATE BAR CHART
    # --------------------------------------------------------

    fig = px.bar(
        bd,
        x="count",
        y="label",
        orientation="h",
        text="count",
        color_discrete_sequence=[
            color
        ],
    )


    fig.update_traces(
        marker_line_width=0,
        textposition="outside",
        textfont_color=TEXT,
        cliponaxis=False,
        width=bar_width,
    )


    fig.update_layout(

        yaxis=dict(
            autorange="reversed",
            title=None,
            automargin=True,
        ),

        xaxis=dict(
            title=None,
            showticklabels=False,
        ),
    )


    fig = style_fig(
        fig,
        height=height,
        show_legend=False,
    )


    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
    )


    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
    )


    fig.update_layout(
        margin=dict(
            l=10,
            r=55,
            t=10,
            b=10,
        ),

        bargap=0.28,
    )


    return fig


# ============================================================
# INTERACTIVE NATIONAL PARK MAP
# ============================================================

# Complete fallback mapping for the 15 parks used by this project.
# We still import NPS_PARK_CODES from nps_api.py, but keeping this
# fallback here prevents a missing dictionary entry or small name
# mismatch from causing the hover photo to disappear.
DEFAULT_NPS_PARK_CODES = {
    "Acadia National Park": "acad",
    "Bryce Canyon National Park": "brca",
    "Cuyahoga Valley National Park": "cuva",
    "Glacier National Park": "glac",
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


def normalize_park_name(value):
    """Normalize park names so small formatting differences still match."""

    value = str(value or "").strip().lower()
    value = value.replace("&", "and")
    value = value.replace("–", "-").replace("—", "-")
    value = " ".join(value.split())
    return value


def resolve_nps_park_code(park_name):
    """Return an NPS park code for a park name, using tolerant matching."""

    combined_codes = dict(DEFAULT_NPS_PARK_CODES)

    try:
        if isinstance(NPS_PARK_CODES, dict):
            combined_codes.update(NPS_PARK_CODES)
    except Exception:
        pass

    # First try the exact park name.
    exact = combined_codes.get(park_name)
    if exact:
        return exact

    # Then try a normalized comparison.
    target = normalize_park_name(park_name)

    for name, code in combined_codes.items():
        if normalize_park_name(name) == target:
            return code

    # A few common shortened forms, just in case the CSV uses them.
    aliases = {
        "acadia": "acad",
        "bryce canyon": "brca",
        "cuyahoga valley": "cuva",
        "glacier": "glac",
        "grand canyon": "grca",
        "grand teton": "grte",
        "great smoky mountains": "grsm",
        "hot springs": "hosp",
        "indiana dunes": "indu",
        "joshua tree": "jotr",
        "olympic": "olym",
        "rocky mountain": "romo",
        "yellowstone": "yell",
        "yosemite": "yose",
        "zion": "zion",
    }

    shortened = target
    shortened = shortened.replace(" national park", "")
    shortened = shortened.replace(" np", "")
    shortened = shortened.strip()

    return aliases.get(shortened)


def get_map_park_details(park_name):
    """
    Load NPS details for a map marker.

    The API helper itself is cached in nps_api.py, so rebuilding the map
    does not repeatedly hit the NPS endpoint for every Streamlit rerun.
    """

    park_code = resolve_nps_park_code(park_name)

    if not park_code:
        return None

    try:
        return get_nps_park_data(park_code)
    except Exception:
        return None


def park_map(map_df):
    """
    Interactive National Parks map.

    Default:
        Esri World Physical Map

    Provides:
        - colored land
        - terrain / elevation
        - blue water
        - minimal road clutter
        - interactive biodiversity markers
        - official NPS park photos on hover

    Optional layers:
        - Light Map
        - USGS Topographic
        - USGS Imagery + Topo
    """

    # --------------------------------------------------------
    # MAP POSITION
    # --------------------------------------------------------

    if len(map_df) == 1:

        center_lat = float(
            map_df.iloc[0]["lat"]
        )

        center_lon = float(
            map_df.iloc[0]["lon"]
        )

        zoom_start = 8

    else:

        center_lat = 39.5
        center_lon = -98.35
        zoom_start = 4


    # --------------------------------------------------------
    # CREATE MAP
    # --------------------------------------------------------

    m = folium.Map(
        location=[
            center_lat,
            center_lon,
        ],

        zoom_start=zoom_start,

        tiles=None,

        control_scale=True,

        prefer_canvas=True,

        min_zoom=2,

        max_zoom=12,
    )


    # ========================================================
    # DEFAULT PHYSICAL TERRAIN MAP
    # ========================================================

    folium.TileLayer(
        tiles=(
            "https://services.arcgisonline.com/"
            "ArcGIS/rest/services/"
            "World_Physical_Map/MapServer/tile/"
            "{z}/{y}/{x}"
        ),

        attr=(
            "Esri | U.S. National Park Service "
            "| Natural Earth"
        ),

        name="Physical Terrain",

        overlay=False,

        control=True,

        show=True,

        max_native_zoom=8,

        max_zoom=12,
    ).add_to(m)


    # ========================================================
    # OPTIONAL LIGHT MAP
    # ========================================================

    folium.TileLayer(
        tiles="CartoDB Positron",

        name="Light Map",

        overlay=False,

        control=True,

        show=False,
    ).add_to(m)


    # ========================================================
    # OPTIONAL USGS TOPOGRAPHIC MAP
    # ========================================================

    folium.TileLayer(
        tiles=(
            "https://basemap.nationalmap.gov/"
            "arcgis/rest/services/"
            "USGSTopo/MapServer/tile/"
            "{z}/{y}/{x}"
        ),

        attr=(
            "U.S. Geological Survey "
            "| The National Map"
        ),

        name="USGS Topographic",

        overlay=False,

        control=True,

        show=False,

        max_zoom=16,
    ).add_to(m)


    # ========================================================
    # OPTIONAL USGS IMAGERY + TOPO
    # ========================================================

    folium.TileLayer(
        tiles=(
            "https://basemap.nationalmap.gov/"
            "arcgis/rest/services/"
            "USGSImageryTopo/MapServer/tile/"
            "{z}/{y}/{x}"
        ),

        attr=(
            "U.S. Geological Survey "
            "| The National Map"
        ),

        name="Imagery + Topo",

        overlay=False,

        control=True,

        show=False,

        max_zoom=16,
    ).add_to(m)


    # ========================================================
    # PARK MARKER SCALING
    # ========================================================

    if len(map_df):

        max_records = max(
            int(
                map_df["Records"].max()
            ),
            1,
        )

    else:

        max_records = 1


    # ========================================================
    # PARK MARKERS
    # ========================================================

    for _, row in map_df.iterrows():

        park_name = str(
            row["ParkName"]
        )

        records = int(
            row["Records"]
        )

        latitude = float(
            row["lat"]
        )

        longitude = float(
            row["lon"]
        )


        # ----------------------------------------------------
        # MARKER SIZE
        # ----------------------------------------------------

        radius = (
            6
            + math.sqrt(
                records / max_records
            )
            * 12
        )


        # ----------------------------------------------------
        # LOAD NPS PARK INFORMATION
        # ----------------------------------------------------

        nps_data = get_map_park_details(
            park_name
        )

        photo_url = None
        official_name = park_name
        states = ""

        if isinstance(nps_data, dict):

            photo_url = (
                nps_data.get("photo_url")
                or ""
            )

            official_name = (
                nps_data.get("name")
                or park_name
            )

            states = (
                nps_data.get("states")
                or ""
            )

        safe_official_name = html.escape(
            str(official_name)
        )

        safe_states = html.escape(
            str(states)
        )

        safe_photo_url = html.escape(
            str(photo_url),
            quote=True,
        ) if photo_url else ""


        # ----------------------------------------------------
        # HOVER CARD
        # ----------------------------------------------------

        if safe_photo_url:

            image_html = f"""
                <img
                    src="{safe_photo_url}"
                    alt="{safe_official_name}"
                    style="
                        display:block;
                        width:250px;
                        height:140px;
                        object-fit:cover;
                        border-radius:8px;
                        margin:0 0 9px 0;
                    "
                >
            """

        else:

            image_html = ""


        states_html = ""

        if safe_states:

            states_html = f"""
                <div style="
                    margin-top:3px;
                    color:#6B7280;
                    font-size:11px;
                ">
                    {safe_states}
                </div>
            """


        if safe_photo_url:

            photo_credit_html = """
                <div style="
                    margin-top:6px;
                    font-size:10px;
                    color:#9CA3AF;
                ">
                    Park photo: National Park Service
                </div>
            """

        else:

            photo_credit_html = """
                <div style="
                    margin-top:6px;
                    font-size:10px;
                    color:#9CA3AF;
                ">
                    NPS photo unavailable
                </div>
            """


        tooltip_html = f"""
        <div style="
            width:260px;
            padding:5px;
            font-family:Arial,sans-serif;
            background:#FFFFFF;
            color:#1F2329;
        ">

            {image_html}

            <div style="
                font-size:15px;
                font-weight:700;
                line-height:1.25;
                margin-bottom:5px;
            ">
                {safe_official_name}
            </div>

            <div style="
                font-size:12px;
                color:#4B5563;
                line-height:1.4;
            ">
                <strong>{records:,}</strong>
                biodiversity records
            </div>

            {states_html}

            {photo_credit_html}

        </div>
        """


        tooltip = folium.Tooltip(
            tooltip_html,
            sticky=True,
            direction="top",
            opacity=0.98,
        )


        # ----------------------------------------------------
        # CLICK POPUP
        # ----------------------------------------------------

        popup_html = f"""
        <div style="
            width:270px;
            font-family:Arial,sans-serif;
            color:#1F2329;
        ">

            {image_html}

            <div style="
                font-size:15px;
                font-weight:700;
                line-height:1.25;
                margin-bottom:5px;
            ">
                {safe_official_name}
            </div>

            <div style="
                font-size:12px;
                color:#6B7280;
            ">
                {records:,} biodiversity records
            </div>

            {states_html}

        </div>
        """


        popup = folium.Popup(
            popup_html,
            max_width=300,
        )


        # ----------------------------------------------------
        # BLUE PARK MARKER
        # ----------------------------------------------------

        folium.CircleMarker(
            location=[
                latitude,
                longitude,
            ],

            radius=radius,

            tooltip=tooltip,

            popup=popup,

            color="#FFFFFF",

            weight=2,

            fill=True,

            fill_color=ACCENT,

            fill_opacity=0.90,
        ).add_to(m)


    # ========================================================
    # MAP LAYER CONTROL
    # ========================================================

    folium.LayerControl(
        position="topright",
        collapsed=True,
    ).add_to(m)


    return m


# ============================================================
# KPI CARD
# ============================================================

def kpi_html(
    label,
    value,
):

    return (
        f'<div class="kpi-card">'

        f'<div class="kpi-label">'
        f'{label}'
        f'</div>'

        f'<div class="kpi-value">'
        f'{value}'
        f'</div>'

        f'</div>'
    )


# ============================================================
# CARD TITLE
# ============================================================

def card_title(
    text,
    sub=None,
):

    st.markdown(
        f'<div class="card-title">'
        f'{text}'
        f'</div>',
        unsafe_allow_html=True,
    )


    if sub:

        st.markdown(
            f'<div class="card-sub">'
            f'{sub}'
            f'</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# YOUTUBE API KEY
# ============================================================

def get_api_key():

    try:

        key = st.secrets[
            "YOUTUBE_API_KEY"
        ]

    except Exception:

        return ""


    if (
        not key
        or str(key).startswith("YOUR_")
    ):

        return ""


    return str(key)


# ============================================================
# YOUTUBE VIDEO SEARCH
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def fetch_youtube_videos(
    query,
    api_key,
    max_results=4,
):

    url = (
        "https://www.googleapis.com/"
        "youtube/v3/search"
    )


    params = {
        "part": "snippet",

        "q": query,

        "type": "video",

        "maxResults": max_results,

        "videoEmbeddable": "true",

        "order": "relevance",

        "key": api_key,
    }


    response = requests.get(
        url,
        params=params,
        timeout=10,
    )


    response.raise_for_status()


    out = []


    for item in response.json().get(
        "items",
        [],
    ):

        vid = (
            item
            .get("id", {})
            .get("videoId")
        )


        if vid:

            out.append(
                {
                    "id": vid,

                    "title": (
                        item
                        .get("snippet", {})
                        .get("title", "")
                    ),
                }
            )


    return out


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
        f"Put your CSV in this folder "
        f"or update DATA_PATH in shared.py."
    )

    st.stop()


# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.markdown(
    "## Filters"
)


selected_parks = st.sidebar.multiselect(
    "Park name",

    unique_values(
        df,
        cols["park_name"],
    ),

    placeholder="All parks",
)


selected_categories = st.sidebar.multiselect(
    "Category",

    unique_values(
        df,
        cols["category"],
    ),

    placeholder="All categories",
)


search_text = st.sidebar.text_input(
    "Search species",

    placeholder=(
        "Scientific or common name..."
    ),
)


st.sidebar.caption(
    "Search by park or species "
    "to view more detailed information."
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
# DASHBOARD HEADER
# ============================================================

st.markdown(
    '<div class="dash-title">'
    'National Parks Biodiversity Discovery'
    '</div>',

    unsafe_allow_html=True,
)


st.markdown(
    '<div class="dash-sub">'
    'Species records across the 15 most visited '
    'U.S. National Parks'
    '</div>',

    unsafe_allow_html=True,
)


# ============================================================
# KPI CARDS
# ============================================================

total, n_parks, n_species, pct_accepted = kpis(
    fdf,
    cols,
)


st.markdown(
    '<div class="kpi-row">'

    + kpi_html(
        "Total records",
        f"{total:,}",
    )

    + kpi_html(
        "National parks",
        f"{n_parks:,}",
    )

    + kpi_html(
        "Species",
        f"{n_species:,}",
    )

    + kpi_html(
        "Park-accepted",
        f"{pct_accepted:.0f}%",
    )

    + "</div>",

    unsafe_allow_html=True,
)


# ============================================================
# PARK MAP
# ============================================================

with st.container(
    border=True
):

    card_title(
        "Park locations",
        "Interactive physical terrain map",
    )


    map_df, missing = build_park_map_df(
        fdf,
        cols,
        get_coordinates,
    )


    if len(map_df):

        terrain_map = park_map(
            map_df
        )


        # ----------------------------------------------------
        # FORCE MAP TO RECENTER WHEN ONE PARK IS SELECTED
        # ----------------------------------------------------

        if len(selected_parks) == 1:

            map_key = (
                "national_parks_map_"
                + selected_parks[0]
            )

        else:

            map_key = (
                "national_parks_map_all"
            )


        st_folium(
            terrain_map,

            use_container_width=True,

            height=520,

            returned_objects=[],

            key=map_key,
        )


    else:

        st.info(
            "No mapped parks "
            "for the current filter."
        )


    if missing:

        st.caption(
            "No coordinates on file for: "
            + ", ".join(
                sorted(missing)
            )
        )


# ============================================================
# BIODIVERSITY VIDEOS
# ============================================================

with st.container(
    border=True
):

    card_title(
        "Biodiversity videos"
    )


    api_key = get_api_key()


    if not api_key:

        st.info(
            "Add a YouTube Data API key "
            "to .streamlit/secrets.toml "
            "to enable videos."
        )


    elif len(
        selected_parks
    ) != 1:

        st.info(
            "Select a single park "
            "to load related biodiversity videos."
        )


    else:

        park = selected_parks[0]


        try:

            videos = fetch_youtube_videos(
                f"{park} "
                f"biodiversity "
                f"wildlife "
                f"nature",

                api_key,
            )


        except Exception:

            videos = []

            st.warning(
                "Couldn't load videos. "
                "Check the API key "
                "or daily quota."
            )


        if videos:

            for col, video in zip(
                st.columns(
                    len(videos)
                ),
                videos,
            ):

                with col:

                    st.video(
                        "https://www.youtube.com/"
                        f"watch?v={video['id']}"
                    )

                    st.caption(
                        video["title"]
                    )


        else:

            st.caption(
                f"No videos found for {park}."
            )


# ============================================================
# CATEGORY GROUP CHARTS
# ============================================================

group_subs = {

    "Flora, Fungi & Microbiota":
        "Sessile / non-motile life",

    "Terrestrial fauna":
        "Land animals",

    "Aquatic fauna":
        "Water animals",
}


for col, group_name in zip(
    st.columns(3),
    CATEGORY_GROUP_ORDER,
):

    with col:

        with st.container(
            border=True
        ):

            card_title(
                group_name,

                group_subs.get(
                    group_name
                ),
            )


            bd = group_category_breakdown(
                fdf,
                cols,
                group_name,
            )


            if len(bd):

                render_donut(
                    bd,
                    center_units="records",
                    n=6,
                )


            else:

                st.info(
                    "No records "
                    "in this group."
                )


# ============================================================
# UNASSIGNED CATEGORIES
# ============================================================

unassigned = unassigned_categories(
    fdf,
    cols,
)


if unassigned:

    st.caption(
        "Categories not assigned to a group "
        "(edit CATEGORY_GROUPS in data_utils.py): "
        + ", ".join(
            unassigned
        )
    )


# ============================================================
# TAXONOMIC ORDER + ABUNDANCE
# ============================================================

oc, ac = st.columns(2)


# ------------------------------------------------------------
# TAXONOMIC ORDER
# ------------------------------------------------------------

with oc:

    with st.container(
        border=True
    ):

        card_title(
            "Taxonomic Order",
            "Top orders",
        )


        bd = value_breakdown(
            fdf,
            cols["order"],
        )


        if len(bd):

            render_donut(
                bd,
                center_units="records",
                n=6,
                height=300,
            )


        else:

            st.info(
                "No order data."
            )


# ------------------------------------------------------------
# ABUNDANCE
# ------------------------------------------------------------

with ac:

    with st.container(
        border=True
    ):

        card_title(
            "Abundance",
            "Records by abundance",
        )


        ab = value_breakdown(
            fdf,
            cols["abundance"],
            blank_label="Unknown",
        )


        if len(ab):

            st.plotly_chart(
                hbar(
                    ab,

                    # Same dashboard blue as the
                    # other primary visual elements
                    color=ACCENT,
                ),

                use_container_width=True,

                config={
                    "displayModeBar": False
                },
            )


        else:

            st.info(
                "No abundance data."
            )


# ============================================================
# FAMILY + NATIVENESS + PARK ACCEPTED
# ============================================================

c4, c5, c6 = st.columns(3)


# ------------------------------------------------------------
# FAMILY
# ------------------------------------------------------------

with c4:

    with st.container(
        border=True
    ):

        card_title(
            "Family"
        )


        fam_tbl = breakdown_table(
            fdf,
            cols["family"],
            "Family",
            top_n=15,
        )


        if len(fam_tbl):

            st.dataframe(
                fam_tbl,

                use_container_width=True,

                hide_index=True,

                height=330,
            )


        else:

            st.info(
                "No family data."
            )


# ------------------------------------------------------------
# NATIVENESS
# ------------------------------------------------------------

with c5:

    with st.container(
        border=True
    ):

        card_title(
            "Nativeness"
        )


        nat_tbl = breakdown_table(
            fdf,
            cols["nativeness"],
            "Nativeness",
        )


        if len(nat_tbl):

            st.dataframe(
                nat_tbl,

                use_container_width=True,

                hide_index=True,
            )


        else:

            st.info(
                "No nativeness data."
            )


# ------------------------------------------------------------
# PARK ACCEPTED
# ------------------------------------------------------------

with c6:

    with st.container(
        border=True
    ):

        card_title(
            "Park accepted"
        )


        pa_tbl = park_accepted_table(
            fdf,
            cols,
        )


        if len(pa_tbl):

            st.dataframe(
                pa_tbl,

                use_container_width=True,

                hide_index=True,
            )


        else:

            st.info(
                "No ParkAccepted data."
            )


# ============================================================
# SPECIES SPOTLIGHT
# ============================================================

spotlight_df = species_list(
    fdf,
    cols,
)


filter_key = (
    f"{selected_parks}|"
    f"{selected_categories}|"
    f"{search_text}"
)


if (
    st.session_state.get(
        "spotlight_filter_key"
    )
    != filter_key
):

    st.session_state[
        "spotlight_filter_key"
    ] = filter_key

    st.session_state[
        "spotlight_i"
    ] = 0


# ============================================================
# ROTATING SPECIES CARDS
# ============================================================

@st.fragment(
    run_every="6s"
)
def species_spotlight(
    sp_df,
    page_size=5,
):

    total_sp = len(
        sp_df
    )


    if total_sp == 0:

        st.info(
            "No species for "
            "the current filter."
        )

        return


    n_pages = max(
        1,

        (
            total_sp
            + page_size
            - 1
        )
        // page_size,
    )


    i = st.session_state.get(
        "spotlight_i",
        0,
    )


    page = (
        i % n_pages
    )


    start = (
        page * page_size
    )


    chunk = sp_df.iloc[
        start:
        start + page_size
    ]


    for col, (_, row) in zip(
        st.columns(
            max(
                1,
                len(chunk),
            )
        ),

        chunk.iterrows(),
    ):

        with col:

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


    st.caption(
        f"Showing "
        f"{start + 1}-"
        f"{min(start + page_size, total_sp)} "
        f"of {total_sp:,} species "
        f"(auto-rotating, photos via iNaturalist)"
    )


    st.session_state[
        "spotlight_i"
    ] = i + 1


# ============================================================
# SPECIES SPOTLIGHT CONTAINER
# ============================================================

with st.container(
    border=True
):

    card_title(
        "Species spotlight"
    )


    species_spotlight(
        spotlight_df
    )


# ============================================================
# FULL DATA TABLE
# ============================================================

with st.container(
    border=True
):

    card_title(
        "All records"
    )


    st.caption(
        f"{len(fdf):,} rows"
    )


    st.dataframe(
        fdf,

        use_container_width=True,

        height=430,

        hide_index=True,
    )
