"""
data_utils.py
-------------
All data loading, column resolution, filtering, and aggregation logic.
No Streamlit imports here, so it stays testable and reusable. The column
resolver mirrors the FindHeaderColumn idea from the VBA dashboard: it matches
headers tolerantly (case / spaces / underscores).
"""

import re
import pandas as pd

COLUMN_CANDIDATES = {
    "park_name":     ["ParkName", "Park Name", "park_name"],
    "park_code":     ["ParkCode", "Park Code", "park_code"],
    "category":      ["CategoryName", "Category Name", "Category"],
    "order":         ["Order"],
    "family":        ["Family"],
    "sci_name":      ["SciName", "Scientific Name", "ScientificName"],
    "common_names":  ["CommonNames", "Common Names", "CommonName", "Common Name"],
    "park_accepted": ["ParkAccepted", "Park Accepted"],
    "abundance":     ["Abundance"],
    "nativeness":    ["Nativeness"],
    "occurrence":    ["Occurrence"],
    "record_status": ["RecordStatus", "Record Status"],
}


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def find_col(df, candidates):
    norm_map = {_norm(c): c for c in df.columns}
    for cand in candidates:
        actual = norm_map.get(_norm(cand))
        if actual is not None:
            return actual
    return None


def resolve_columns(df):
    return {key: find_col(df, names) for key, names in COLUMN_CANDIDATES.items()}


def load_data(path):
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="latin-1")
    df.columns = [str(c).strip() for c in df.columns]
    return df


_TRUTHY = {"true", "t", "1", "yes", "y"}
_FALSY = {"false", "f", "0", "no", "n"}


def to_bool_series(s):
    def conv(v):
        x = str(v).strip().lower()
        if x in _TRUTHY:
            return True
        if x in _FALSY:
            return False
        return None
    return s.map(conv)


def unique_values(df, col):
    if not col or df.empty:
        return []
    return sorted(df[col].replace("", pd.NA).dropna().unique())


def apply_filters(df, cols, parks, categories, search_text):
    out = df

    pn = cols.get("park_name")
    if parks and pn:
        out = out[out[pn].isin(parks)]

    cat = cols.get("category")
    if categories and cat:
        out = out[out[cat].isin(categories)]

    if search_text and str(search_text).strip():
        q = str(search_text).strip().lower()
        sci = cols.get("sci_name")
        com = cols.get("common_names")
        mask = pd.Series(False, index=out.index)
        if sci:
            mask = mask | out[sci].str.lower().str.contains(q, na=False, regex=False)
        if com:
            mask = mask | out[com].str.lower().str.contains(q, na=False, regex=False)
        out = out[mask]
    return out


def kpis(df, cols):
    pn = cols.get("park_name")
    sci = cols.get("sci_name")
    pa = cols.get("park_accepted")

    total = len(df)
    n_parks = df[pn].replace("", pd.NA).nunique(dropna=True) if pn else 0
    n_species = df[sci].replace("", pd.NA).nunique(dropna=True) if sci else 0

    pct_accepted = 0.0
    if pa:
        b = to_bool_series(df[pa]).dropna()
        if len(b):
            pct_accepted = b.mean() * 100.0
    return total, n_parks, n_species, pct_accepted


def value_breakdown(df, col, top_n=None, blank_label="(blank)"):
    if not col or df.empty:
        return pd.DataFrame(columns=["label", "count"])

    s = df[col].replace("", blank_label).fillna(blank_label)
    vc = s.value_counts().reset_index()
    vc.columns = ["label", "count"]

    if top_n and len(vc) > top_n:
        top = vc.iloc[: top_n - 1].copy()
        other_total = int(vc["count"].iloc[top_n - 1:].sum())
        other = pd.DataFrame({"label": ["Other"], "count": [other_total]})
        vc = pd.concat([top, other], ignore_index=True)
    return vc


def breakdown_table(df, col, label_name, top_n=None):
    vb = value_breakdown(df, col, top_n=top_n)
    if vb.empty:
        return pd.DataFrame(columns=[label_name, "Count", "Percentage"])
    total = vb["count"].sum()
    out = vb.rename(columns={"label": label_name, "count": "Count"})
    out["Percentage"] = (out["Count"] / total * 100).round(1).astype(str) + "%"
    return out


def park_accepted_table(df, cols):
    pa = cols.get("park_accepted")
    if not pa or df.empty:
        return pd.DataFrame(columns=["Park Accepted", "Count", "Percentage"])

    labels = to_bool_series(df[pa]).map({True: "True", False: "False"}).fillna("Unknown")
    vc = labels.value_counts().reset_index()
    vc.columns = ["Park Accepted", "Count"]
    total = vc["Count"].sum()
    vc["Percentage"] = (vc["Count"] / total * 100).round(1).astype(str) + "%"
    return vc


def species_list(df, cols):
    sci = cols.get("sci_name")
    com = cols.get("common_names")
    cat = cols.get("category")

    if not sci or df.empty:
        return pd.DataFrame(columns=["Scientific name", "Common names"])

    use = [c for c in [sci, com, cat] if c]
    out = df[use].copy()
    out = out[out[sci].astype(str).str.strip() != ""]
    out = out.drop_duplicates(subset=[sci]).sort_values(sci)

    rename = {sci: "Scientific name"}
    if com:
        rename[com] = "Common names"
    if cat:
        rename[cat] = "Category"
    out = out.rename(columns=rename).reset_index(drop=True)
    return out


def build_park_map_df(df, cols, coord_lookup):
    pn = cols.get("park_name")
    if not pn or df.empty:
        return pd.DataFrame(columns=["ParkName", "Records", "lat", "lon"]), []

    counts = df.groupby(pn).size().reset_index(name="Records")
    counts = counts.rename(columns={pn: "ParkName"})

    lats, lons, missing = [], [], []
    for name in counts["ParkName"]:
        coord = coord_lookup(name)
        if coord:
            lats.append(coord[0])
            lons.append(coord[1])
        else:
            lats.append(None)
            lons.append(None)
            if str(name).strip():
                missing.append(str(name))

    counts["lat"] = lats
    counts["lon"] = lons
    mapped = counts.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    return mapped, missing


# ==========================================================================
# CATEGORY GROUPING - splits the 16 CategoryName values into 3 charts.
# Edit any line to move a category between groups; the dashboard updates.
# Scientific framing: flora/fauna, terrestrial (land) / aquatic (water),
# sessile (non-motile) vs motile.
# ==========================================================================
CATEGORY_GROUP_ORDER = ["Flora, Fungi & Microbiota", "Terrestrial fauna", "Aquatic fauna"]

CATEGORY_GROUPS = {
    # --- Flora, Fungi & Microbiota (sessile / non-motile, "doesn't move") ---
    "Vascular Plant":        "Flora, Fungi & Microbiota",
    "Non-vascular Plant":    "Flora, Fungi & Microbiota",
    "Fungi":                 "Flora, Fungi & Microbiota",
    "Chromista":             "Flora, Fungi & Microbiota",   # algae, diatoms
    "Bacteria":              "Flora, Fungi & Microbiota",   # microbiota
    "Protozoa":              "Flora, Fungi & Microbiota",   # microbiota
    # --- Terrestrial fauna (land animals) ---
    "Mammal":                "Terrestrial fauna",
    "Bird":                  "Terrestrial fauna",
    "Reptile":               "Terrestrial fauna",
    "Amphibian":             "Terrestrial fauna",           # judgment call (breeds in water)
    "Insect":                "Terrestrial fauna",
    "Spider/Scorpion":       "Terrestrial fauna",
    "Slug/Snail":            "Terrestrial fauna",           # judgment call (some aquatic)
    "Other Non-vertebrates": "Terrestrial fauna",
    # --- Aquatic fauna (water animals) ---
    "Fish":                  "Aquatic fauna",
    "Crab/Lobster/Shrimp":   "Aquatic fauna",
}

_CAT_GROUP_NORM = {_norm(k): v for k, v in CATEGORY_GROUPS.items()}


def category_group_of(value):
    """Return the group name for a category value, or None if unassigned."""
    return _CAT_GROUP_NORM.get(_norm(value))


def group_category_breakdown(df, cols, group_name):
    """Counts per category, limited to categories belonging to one group."""
    cat = cols.get("category")
    if not cat or df.empty:
        return pd.DataFrame(columns=["label", "count"])
    mask = df[cat].map(lambda v: category_group_of(v) == group_name)
    return value_breakdown(df[mask], cat)


def unassigned_categories(df, cols):
    """Any category present in the data but not mapped to a group."""
    cat = cols.get("category")
    if not cat or df.empty:
        return []
    present = df[cat].replace("", pd.NA).dropna().unique()
    return sorted([c for c in present if category_group_of(c) is None])


def rollup_top_n(bd, n=6):
    """Keep the top n-1 rows of a (label,count) breakdown, sum the rest into 'Other'."""
    if bd is None or len(bd) <= n:
        return bd.reset_index(drop=True) if bd is not None else bd
    top = bd.iloc[: n - 1].copy()
    other = pd.DataFrame({"label": ["Other"], "count": [int(bd["count"].iloc[n - 1:].sum())]})
    return pd.concat([top, other], ignore_index=True)
