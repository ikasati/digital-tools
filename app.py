import streamlit as st
import os
from datetime import date
from streamlit_option_menu import option_menu
from utils.styles import apply_styles
from tools.sitemap_checker import show_sitemap_checker
from tools.feed_checker import show_feed_checker
from tools.price_vortex import show_price_vortex
from tools.external_link_scanner import show_external_link_scanner
from tools.redirect_checker import show_redirect_checker

# ── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dijital Araçlar",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply global CSS
apply_styles()

# ── Tool registry ────────────────────────────────────────────
# Single source of truth: sidebar, home tiles and routing are all built from this list.
TOOLS = [
    {"page": "Sitemap Checker",  "icon": "map",          "emoji": "🧭", "title": "Sitemap kontrol et",
     "desc": "Kırık linkleri ve 404 sayfalarını tespit et.",                   "render": show_sitemap_checker},
    {"page": "Feed Checker",     "icon": "link-45deg",   "emoji": "🔗", "title": "Feed URL'lerini kontrol et",
     "desc": "Google veya Facebook feed'indeki URL durumlarını gör.",           "render": show_feed_checker},
    {"page": "Price Vortex",     "icon": "tornado",      "emoji": "🌪️", "title": "Fiyat & stok karşılaştır",
     "desc": "Ürün CSV'ni Google feed'iyle karşılaştır.",                       "render": show_price_vortex},
    {"page": "External Links",   "icon": "search",       "emoji": "🔍", "title": "Dış linkleri tara",
     "desc": "Sitedeki tüm gizli dış linkleri bul.",                            "render": show_external_link_scanner},
    {"page": "Redirect Checker", "icon": "arrow-left-right", "emoji": "↪️", "title": "301'leri doğrula",
     "desc": "Yönlendirme CSV'ni yükle, hatalı ve zincirli 301'leri bul.",      "render": show_redirect_checker},
]
TOOL_BY_PAGE = {t["page"]: t for t in TOOLS}
HOME = "Ana Sayfa"
PAGES = [HOME] + [t["page"] for t in TOOLS]

# ── Session state ────────────────────────────────────────────
if st.session_state.get("page") not in PAGES:
    st.session_state.page = HOME

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=70)
    else:
        st.markdown("<h2 style='color:white; margin:0; padding-top:12px;'>242</h2>", unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    selected = option_menu(
        menu_title=None,
        options=PAGES,
        icons=["house-door"] + [t["icon"] for t in TOOLS],
        default_index=PAGES.index(st.session_state.page),
        styles={
            "container": {"padding": "0!important", "background-color": "#0f0f0f"},
            "icon": {"color": "#888", "font-size": "16px"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left",
                "margin": "4px 0",
                "color": "#bbb",
                "background-color": "transparent",
                "border-radius": "12px",
                "padding": "12px 16px",
                "transition": "all 0.2s ease",
            },
            "nav-link-selected": {
                "background-color": "rgba(111, 85, 255, 0.15)",
                "color": "#6F55FF",
                "font-weight": "600",
                "border": "1px solid rgba(111, 85, 255, 0.2)"
            },
        }
    )

    if selected != st.session_state.page:
        st.session_state.page = selected
        st.rerun()

    st.markdown(f"""
    <div style="position:fixed;bottom:20px;left:0;width:240px;padding:0 24px;box-sizing:border-box; background-color:#0f0f0f;">
        <p style="color:#555;font-size:11px;margin:0;">© {date.today().year} 242</p>
    </div>
    """, unsafe_allow_html=True)

# ── Main Content Area ────────────────────────────────────────
if st.session_state.page == HOME:
    st.markdown(f"""
    <div style="padding:48px 0 40px 0;">
        <h1 style="font-size:2.8rem;font-weight:800;color:#111;line-height:1.15;margin:0 0 14px 0;">
            Dijital Kontrolleri.<br>Kolaylaştırılmış.
        </h1>
        <p style="color:#666;font-size:16px;margin:0;">{len(TOOLS)} araç hazır. Ne yapmak istiyorsun?</p>
    </div>
    """, unsafe_allow_html=True)

    # Tiles laid out 3 per row; "Hemen Başla" jumps straight to the tool page
    for row_start in range(0, len(TOOLS), 3):
        cols = st.columns(3, gap="large")
        for col, (i, tool) in zip(cols, enumerate(TOOLS[row_start:row_start + 3], start=row_start + 1)):
            with col:
                st.markdown(f"""
                <div class="qs-tile">
                    <div class="qs-num">{i:02d}</div>
                    <div class="qs-icon">{tool["emoji"]}</div>
                    <h3>{tool["title"]}</h3>
                    <p>{tool["desc"]}</p>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                if st.button("Hemen Başla", key=f"qs_{i}", use_container_width=True):
                    st.session_state.page = tool["page"]
                    st.rerun()
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
else:
    TOOL_BY_PAGE[st.session_state.page]["render"]()
