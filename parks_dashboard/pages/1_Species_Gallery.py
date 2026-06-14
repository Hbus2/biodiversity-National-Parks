"""
pages/1_Species_Gallery.py
--------------------------
A full-page species photo gallery. Filter by park / category, search by name,
and page through species shown as a photo grid (images from iNaturalist).
"""

import streamlit as st

from data_utils import apply_filters, unique_values, species_list
from shared import inject_css, get_data, species_card, DATA_PATH

st.set_page_config(page_title="Species Gallery", page_icon="📷", layout="wide")
inject_css()

# Sidebar navigation
st.sidebar.page_link("app.py", label="🏠 Dashboard")
st.sidebar.page_link("pages/1_Species_Gallery.py", label="📷 Species Gallery")
st.sidebar.divider()

# ---- data ----
try:
    df, cols = get_data(DATA_PATH)
except FileNotFoundError:
    st.error(f"Could not find '{DATA_PATH}'. Put your CSV in the project folder "
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
sp_df = species_list(fdf, cols)

# ---- header ----
st.markdown('<div class="dash-title">📷 Species Gallery</div>', unsafe_allow_html=True)
st.markdown('<div class="dash-sub">Photos via iNaturalist. Use the filters and '
            'search on the left to narrow the species shown.</div>',
            unsafe_allow_html=True)

PER_ROW = 5
PER_PAGE = 25
total = len(sp_df)

if total == 0:
    st.info("No species match the current filters.")
    st.stop()

n_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)

# ---- page selector ----
top_l, top_r = st.columns([3, 1])
with top_r:
    page = st.number_input("Page", min_value=1, max_value=n_pages, value=1, step=1)
with top_l:
    start = (int(page) - 1) * PER_PAGE
    end = min(start + PER_PAGE, total)
    st.markdown(f'<div class="card-sub" style="margin-top:28px;">'
                f'Showing {start + 1}-{end} of {total:,} species '
                f'(page {int(page)} of {n_pages})</div>', unsafe_allow_html=True)

# ---- photo grid ----
chunk = sp_df.iloc[start:end]
rows = [chunk.iloc[i:i + PER_ROW] for i in range(0, len(chunk), PER_ROW)]

for row_df in rows:
    grid_cols = st.columns(PER_ROW)
    for col, (_, row) in zip(grid_cols, row_df.iterrows()):
        with col:
            with st.container(border=True):
                species_card(row.get("Scientific name", ""),
                             row.get("Common names", ""))
