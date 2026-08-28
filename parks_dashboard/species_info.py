"""
species_info.py
---------------

External species-information helper.

This module:

1. Looks up a species in iNaturalist.
2. Uses the iNaturalist taxon to identify the correct
   Wikipedia article when possible.
3. Retrieves factual introductory information from Wikipedia.
4. Returns structured reference data to the Streamlit app.

OpenAI summarization happens separately in the Species Guide.
"""

from urllib.parse import (
    unquote,
    urlparse,
)

import requests


# ============================================================
# SETTINGS
# ============================================================

INATURALIST_API = (
    "https://api.inaturalist.org/v1"
)

WIKIPEDIA_API = (
    "https://en.wikipedia.org/w/api.php"
)


HEADERS = {
    "User-Agent": (
        "NationalParksBiodiversityExplorer/1.0 "
        "(educational Streamlit application)"
    )
}


REQUEST_TIMEOUT = 12


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(value):
    """
    Convert a value to a clean string.
    """

    if value is None:
        return ""

    text = str(
        value
    ).strip()

    if text.lower() in {
        "",
        "none",
        "nan",
        "<na>",
    }:
        return ""

    return text


# ============================================================
# INATURALIST LOOKUP
# ============================================================

def get_inaturalist_taxon(
    scientific_name,
    common_name="",
):
    """
    Search iNaturalist for a taxon.

    Scientific name is preferred because it is much more
    reliable than the common name.

    Returns a dictionary or None.
    """

    scientific_name = clean_text(
        scientific_name
    )

    common_name = clean_text(
        common_name
    )

    if not scientific_name and not common_name:
        return None

    search_query = (
        scientific_name
        if scientific_name
        else common_name
    )

    try:

        response = requests.get(
            f"{INATURALIST_API}/taxa",
            params={
                "q": search_query,
                "rank": "species",
                "per_page": 10,
                "locale": "en",
            },
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        payload = response.json()

        results = payload.get(
            "results",
            [],
        )

        if not results:
            return None

        # ----------------------------------------------------
        # TRY EXACT SCIENTIFIC NAME FIRST
        # ----------------------------------------------------

        selected_taxon = None

        if scientific_name:

            for taxon in results:

                taxon_name = clean_text(
                    taxon.get(
                        "name"
                    )
                )

                if (
                    taxon_name.casefold()
                    == scientific_name.casefold()
                ):

                    selected_taxon = taxon
                    break

        # ----------------------------------------------------
        # OTHERWISE USE FIRST RESULT
        # ----------------------------------------------------

        if selected_taxon is None:

            selected_taxon = results[0]

        # ----------------------------------------------------
        # PHOTO
        # ----------------------------------------------------

        default_photo = (
            selected_taxon.get(
                "default_photo"
            )
            or {}
        )

        image_url = (
            default_photo.get(
                "medium_url"
            )
            or default_photo.get(
                "square_url"
            )
            or ""
        )

        photo_attribution = clean_text(
            default_photo.get(
                "attribution"
            )
        )

        taxon_id = selected_taxon.get(
            "id"
        )

        if taxon_id:

            taxon_url = (
                "https://www.inaturalist.org/taxa/"
                f"{taxon_id}"
            )

        else:

            taxon_url = ""

        return {
            "id": taxon_id,
            "scientific_name": clean_text(
                selected_taxon.get(
                    "name"
                )
            ),
            "common_name": clean_text(
                selected_taxon.get(
                    "preferred_common_name"
                )
            ),
            "rank": clean_text(
                selected_taxon.get(
                    "rank"
                )
            ),
            "iconic_taxon": clean_text(
                selected_taxon.get(
                    "iconic_taxon_name"
                )
            ),
            "observations_count": (
                selected_taxon.get(
                    "observations_count"
                )
            ),
            "wikipedia_url": clean_text(
                selected_taxon.get(
                    "wikipedia_url"
                )
            ),
            "image_url": image_url,
            "photo_attribution": (
                photo_attribution
            ),
            "taxon_url": taxon_url,
        }

    except (
        requests.RequestException,
        ValueError,
        TypeError,
    ):

        return None


# ============================================================
# GET WIKIPEDIA TITLE FROM URL
# ============================================================

def wikipedia_title_from_url(
    wikipedia_url,
):
    """
    Extract the article title from an existing
    Wikipedia URL.
    """

    wikipedia_url = clean_text(
        wikipedia_url
    )

    if not wikipedia_url:
        return ""

    try:

        parsed = urlparse(
            wikipedia_url
        )

        path = parsed.path

        marker = "/wiki/"

        if marker not in path:
            return ""

        title = path.split(
            marker,
            1,
        )[1]

        title = unquote(
            title
        )

        title = title.replace(
            "_",
            " ",
        )

        return title.strip()

    except Exception:

        return ""


# ============================================================
# WIKIPEDIA ARTICLE LOOKUP
# ============================================================

def get_wikipedia_article(
    scientific_name,
    common_name="",
    wikipedia_url="",
):
    """
    Retrieve the introductory factual content for a species
    from Wikipedia.

    We first use the Wikipedia URL supplied by iNaturalist
    when available.

    If there is no supplied article, we try the scientific
    name and then the common name.
    """

    scientific_name = clean_text(
        scientific_name
    )

    common_name = clean_text(
        common_name
    )

    wikipedia_url = clean_text(
        wikipedia_url
    )

    candidate_titles = []

    # --------------------------------------------------------
    # INATURALIST-PROVIDED WIKIPEDIA PAGE
    # --------------------------------------------------------

    supplied_title = (
        wikipedia_title_from_url(
            wikipedia_url
        )
    )

    if supplied_title:

        candidate_titles.append(
            supplied_title
        )

    # --------------------------------------------------------
    # SCIENTIFIC NAME
    # --------------------------------------------------------

    if (
        scientific_name
        and scientific_name
        not in candidate_titles
    ):

        candidate_titles.append(
            scientific_name
        )

    # --------------------------------------------------------
    # COMMON NAME
    # --------------------------------------------------------

    if (
        common_name
        and common_name
        not in candidate_titles
    ):

        candidate_titles.append(
            common_name
        )

    # --------------------------------------------------------
    # TRY EACH POSSIBLE ARTICLE
    # --------------------------------------------------------

    for title in candidate_titles:

        try:

            response = requests.get(
                WIKIPEDIA_API,
                params={
                    "action": "query",
                    "format": "json",
                    "formatversion": 2,
                    "redirects": 1,
                    "prop": (
                        "extracts|pageimages|info"
                    ),
                    "inprop": "url",
                    "exintro": 1,
                    "explaintext": 1,
                    "piprop": "thumbnail",
                    "pithumbsize": 1000,
                    "titles": title,
                },
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            payload = response.json()

            pages = (
                payload
                .get(
                    "query",
                    {},
                )
                .get(
                    "pages",
                    [],
                )
            )

            if not pages:
                continue

            page = pages[0]

            if page.get(
                "missing"
            ) is True:

                continue

            extract = clean_text(
                page.get(
                    "extract"
                )
            )

            if not extract:
                continue

            thumbnail = (
                page.get(
                    "thumbnail"
                )
                or {}
            )

            return {
                "title": clean_text(
                    page.get(
                        "title"
                    )
                ),
                "extract": extract,
                "url": clean_text(
                    page.get(
                        "fullurl"
                    )
                ),
                "image_url": clean_text(
                    thumbnail.get(
                        "source"
                    )
                ),
            }

        except (
            requests.RequestException,
            ValueError,
            TypeError,
        ):

            continue

    return None


# ============================================================
# COMPLETE REFERENCE LOOKUP
# ============================================================

def get_species_reference(
    scientific_name,
    common_name="",
):
    """
    Retrieve both iNaturalist and Wikipedia information.

    Returns one structured dictionary.
    """

    inat = get_inaturalist_taxon(
        scientific_name,
        common_name,
    )

    wikipedia_url = ""

    if inat:

        wikipedia_url = (
            inat.get(
                "wikipedia_url",
                "",
            )
        )

    wiki = get_wikipedia_article(
        scientific_name,
        common_name,
        wikipedia_url,
    )

    return {
        "inaturalist": inat,
        "wikipedia": wiki,
    }
