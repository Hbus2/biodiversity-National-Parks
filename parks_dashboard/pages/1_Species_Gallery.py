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


park_banner_text = html.escape(
    str(park_banner_text)
)


park_banner_html = (
    '<div style="'
    'background:transparent;'
    'border-top:1px solid #E6E8EB;'
    'border-bottom:1px solid #E6E8EB;'
    'padding:14px 2px;'
    'margin-top:20px;'
    'margin-bottom:22px;'
    '">'
    '<div style="'
    'font-size:12px;'
    'font-weight:500;'
    'color:#7A828A;'
    'margin-bottom:2px;'
    'letter-spacing:0.2px;'
    '">'
    'Currently viewing'
    '</div>'
    '<div style="'
    'font-size:24px;'
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
