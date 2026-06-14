"""
app.py  -  National Parks Biodiversity dashboard (home page), light theme.
Run:  streamlit run app.py
"""

import plotly.express as px
import requests
import streamlit as st

from data_utils import (
    apply_filters, kpis, unique_values, value_breakdown, breakdown_table,
    park_accepted_table, species_list, build_park_map_df, rollup_top_n,
    group_category_breakdown, unassigned_categories, CATEGORY_GROUP_ORDER,
)
from park_coordinates import get_coordinates
from shared import inject_css, get_data, species_card, DATA_PATH, ACCENT, TEXT, MUTED, PALETTE

st.set_page_config(page_title="Parks Biodiversity Dashboard", page_icon="🌲", layout="wide")
inject_css()

# Sidebar navigation
st.sidebar.page_link("app.py", label="🏠 Dashboard")
st.sidebar.page_link("pages/1_Species_Gallery.py", label="📷 Species Gallery")
st.sidebar.divider()


def style_fig(fig, height=320, show_legend=True):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Segoe UI, sans-serif", size=12),
        margin=dict(l=10, r=10, t=10, b=10), height=height,
        showlegend=show_legend,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT, size=11)),
    )
    fig.update_xaxes(gridcolor="#E5E7EB", zerolinecolor="#E5E7EB")
    fig.update_yaxes(gridcolor="#E5E7EB", zerolinecolor="#E5E7EB")
    return fig


def render_donut(bd, center_units="records", n=6, height=240):
    """Clean donut: no slice clutter, center total, custom 2-column legend below."""
    bd = rollup_top_n(bd, n)
    labels = [str(x) for x in bd["label"]]
    counts = [int(x) for x in bd["count"]]
    total = sum(counts)

    colors, pi = [], 0
    for lab in labels:
        if lab.lower() == "other":
            colors.append("#C7CBD1")          # neutral grey for Other
        else:
            colors.append(PALETTE[pi % len(PALETTE)])
            pi += 1

    fig = px.pie(bd, names="label", values="count", hole=0.62,
                 color_discrete_sequence=colors)
    fig.update_traces(
        sort=False, textinfo="none",
        marker=dict(line=dict(color="#FFFFFF", width=2)),
        hovertemplate="%{label}: %{value:,} (%{percent})<extra></extra>",
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, height=height, margin=dict(l=6, r=6, t=6, b=6),
        annotations=[
            dict(text=f"<b>{total:,}</b>", x=0.5, y=0.54, showarrow=False,
                 font=dict(size=18, color=TEXT)),
            dict(text=center_units, x=0.5, y=0.43, showarrow=False,
                 font=dict(size=10, color=MUTED)),
        ],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    rows = ""
    for lab, c, cnt in zip(labels, colors, counts):
        pct = (cnt / total * 100) if total else 0
        rows += (f"<div class='lg-item'><span class='lg-dot' style='background:{c}'></span>"
                 f"<span class='lg-label' title='{lab}'>{lab}</span>"
                 f"<span class='lg-pct'>{pct:.1f}%</span></div>")
    st.markdown(f"<div class='lg-wrap'>{rows}</div>", unsafe_allow_html=True)


def hbar(bd, height=330, color=ACCENT):
    """Horizontal bar chart, largest on top, count labels at the ends."""
    fig = px.bar(bd, x="count", y="label", orientation="h", text="count",
                 color_discrete_sequence=[color])
    fig.update_traces(marker_line_width=0, textposition="outside",
                      textfont_color=TEXT, cliponaxis=False)
    fig.update_layout(
        yaxis=dict(autorange="reversed", title=None, automargin=True),
        xaxis=dict(title=None, showticklabels=False),
    )
    fig = style_fig(fig, height=height, show_legend=False)
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    fig.update_layout(margin=dict(l=10, r=46, t=6, b=6))
    return fig


def park_map(map_df):
    fig = px.scatter_mapbox(
        map_df, lat="lat", lon="lon", size="Records", color="Records",
        color_continuous_scale=["#70ADE7", "#2176C9", "#15569B"],
        size_max=26, zoom=2.7, hover_name="ParkName",
        hover_data={"Records": True, "lat": False, "lon": False},
    )
    fig.update_layout(
        mapbox_style="carto-positron", mapbox_center={"lat": 39.5, "lon": -98.35},
        paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=0, b=0),
        height=430, font=dict(color=TEXT), coloraxis_colorbar=dict(title="Records"),
    )
    return fig


def kpi_html(label, value, icon, icon_bg, icon_fg="#FFFFFF"):
    return (f'<div class="kpi-card">'
            f'<div class="kpi-icon" style="background:{icon_bg};color:{icon_fg};">{icon}</div>'
            f'<div><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div></div></div>')


def card_title(text, sub=None):
    st.markdown(f'<div class="card-title">{text}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="card-sub">{sub}</div>', unsafe_allow_html=True)


def get_api_key():
    try:
        key = st.secrets["YOUTUBE_API_KEY"]
    except Exception:
        return ""
    if not key or str(key).startswith("YOUR_"):
        return ""
    return str(key)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_youtube_videos(query, api_key, max_results=4):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {"part": "snippet", "q": query, "type": "video",
              "maxResults": max_results, "videoEmbeddable": "true",
              "order": "relevance", "key": api_key}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    out = []
    for item in r.json().get("items", []):
        vid = item.get("id", {}).get("videoId")
        if vid:
            out.append({"id": vid, "title": item.get("snippet", {}).get("title", "")})
    return out


# ---- data ----
try:
    df, cols = get_data(DATA_PATH)
except FileNotFoundError:
    st.error(f"Could not find '{DATA_PATH}'. Put your CSV in this folder "
             f"or update DATA_PATH in shared.py.")
    st.stop()

# ---- sidebar filters ----
st.sidebar.markdown("## Filters")
selected_parks = st.sidebar.multiselect(
    "Park name", unique_values(df, cols["park_name"]), placeholder="All parks")
selected_categories = st.sidebar.multiselect(
    "Category", unique_values(df, cols["category"]), placeholder="All categories")
search_text = st.sidebar.text_input(
    "Search species", placeholder="Scientific or common name...")
st.sidebar.caption("Empty filters show everything. Search matches both "
                   "SciName and CommonNames.")

fdf = apply_filters(df, cols, selected_parks, selected_categories, search_text)

# ---- header + KPIs ----
st.markdown('<div class="dash-title">🌲 National Parks Biodiversity Dashboard</div>',
            unsafe_allow_html=True)
st.markdown('<div class="dash-sub">Species records across U.S. National Parks</div>',
            unsafe_allow_html=True)

total, n_parks, n_species, pct_accepted = kpis(fdf, cols)
st.markdown(
    '<div class="kpi-row">'
    + kpi_html("Total records", f"{total:,}", "&#9638;", "#2176C9")
    + kpi_html("National parks", f"{n_parks:,}", "&#11042;", "#6952D2")
    + kpi_html("Species", f"{n_species:,}", "&#10022;", "#2D8AE1")
    + kpi_html("Park-accepted", f"{pct_accepted:.0f}%", "&#10003;", "#2E9E5B")
    + "</div>",
    unsafe_allow_html=True,
)

# ---- map ----
with st.container(border=True):
    card_title("Park locations")
    map_df, missing = build_park_map_df(fdf, cols, get_coordinates)
    if len(map_df):
        st.plotly_chart(park_map(map_df), use_container_width=True,
                        config={"displayModeBar": False})
    else:
        st.info("No mapped parks for the current filter.")
    if missing:
        st.caption("No coordinates on file for: " + ", ".join(sorted(missing)))

# ---- videos ----
with st.container(border=True):
    card_title("Biodiversity videos")
    api_key = get_api_key()
    if not api_key:
        st.info("Add a YouTube Data API key to .streamlit/secrets.toml to enable videos.")
    elif len(selected_parks) != 1:
        st.info("Select a single park in the filter to load related biodiversity videos.")
    else:
        park = selected_parks[0]
        try:
            videos = fetch_youtube_videos(f"{park} biodiversity wildlife nature", api_key)
        except Exception:
            videos = []
            st.warning("Couldn't load videos - check the API key or daily quota.")
        if videos:
            for col, v in zip(st.columns(len(videos)), videos):
                with col:
                    st.video(f"https://www.youtube.com/watch?v={v['id']}")
                    st.caption(v["title"])
        else:
            st.caption(f"No videos found for {park}.")

# ---- THREE CATEGORY-GROUP DONUTS, side by side ----
group_subs = {
    "Flora, Fungi & Microbiota": "Sessile / non-motile life",
    "Terrestrial fauna": "Land animals",
    "Aquatic fauna": "Water animals",
}
for col, group_name in zip(st.columns(3), CATEGORY_GROUP_ORDER):
    with col:
        with st.container(border=True):
            card_title(group_name, group_subs.get(group_name))
            bd = group_category_breakdown(fdf, cols, group_name)
            if len(bd):
                render_donut(bd, center_units="records", n=6)
            else:
                st.info("No records in this group.")

unassigned = unassigned_categories(fdf, cols)
if unassigned:
    st.caption("Categories not assigned to a group (edit CATEGORY_GROUPS in "
               "data_utils.py): " + ", ".join(unassigned))

# ---- ORDER donut + ABUNDANCE bar, side by side ----
oc, ac = st.columns(2)
with oc:
    with st.container(border=True):
        card_title("Taxonomic Order", "Top orders")
        bd = value_breakdown(fdf, cols["order"])
        if len(bd):
            render_donut(bd, center_units="records", n=6, height=300)
        else:
            st.info("No order data.")
with ac:
    with st.container(border=True):
        card_title("Abundance", "Records by abundance")
        ab = value_breakdown(fdf, cols["abundance"], blank_label="Unknown")
        if len(ab):
            st.plotly_chart(hbar(ab, height=360, color="#2E9E5B"),
                            use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No abundance data.")

# ---- family + nativeness + park accepted ----
c4, c5, c6 = st.columns(3)
with c4:
    with st.container(border=True):
        card_title("Family")
        fam_tbl = breakdown_table(fdf, cols["family"], "Family", top_n=15)
        if len(fam_tbl):
            st.dataframe(fam_tbl, use_container_width=True, hide_index=True, height=330)
        else:
            st.info("No family data.")
with c5:
    with st.container(border=True):
        card_title("Nativeness")
        nat_tbl = breakdown_table(fdf, cols["nativeness"], "Nativeness")
        if len(nat_tbl):
            st.dataframe(nat_tbl, use_container_width=True, hide_index=True)
        else:
            st.info("No nativeness data.")
with c6:
    with st.container(border=True):
        card_title("Park accepted")
        pa_tbl = park_accepted_table(fdf, cols)
        if len(pa_tbl):
            st.dataframe(pa_tbl, use_container_width=True, hide_index=True)
        else:
            st.info("No ParkAccepted data.")

# ---- rotating species spotlight (photos, respects filters) ----
spotlight_df = species_list(fdf, cols)
filter_key = f"{selected_parks}|{selected_categories}|{search_text}"
if st.session_state.get("spotlight_filter_key") != filter_key:
    st.session_state["spotlight_filter_key"] = filter_key
    st.session_state["spotlight_i"] = 0


@st.fragment(run_every="6s")
def species_spotlight(sp_df, page_size=5):
    total_sp = len(sp_df)
    if total_sp == 0:
        st.info("No species for the current filter.")
        return
    n_pages = max(1, (total_sp + page_size - 1) // page_size)
    i = st.session_state.get("spotlight_i", 0)
    page = i % n_pages
    start = page * page_size
    chunk = sp_df.iloc[start:start + page_size]
    for col, (_, row) in zip(st.columns(max(1, len(chunk))), chunk.iterrows()):
        with col:
            species_card(row.get("Scientific name", ""), row.get("Common names", ""))
    st.caption(f"Showing {start + 1}-{min(start + page_size, total_sp)} "
               f"of {total_sp:,} species (auto-rotating, photos via iNaturalist)")
    st.session_state["spotlight_i"] = i + 1


with st.container(border=True):
    card_title("Species spotlight")
    species_spotlight(spotlight_df)

# ---- full data table ----
with st.container(border=True):
    card_title("All records")
    st.caption(f"{len(fdf):,} rows")
    st.dataframe(fdf, use_container_width=True, height=430, hide_index=True)
