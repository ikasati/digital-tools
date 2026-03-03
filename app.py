import streamlit as st
import os
from streamlit_option_menu import option_menu
from utils.styles import apply_styles
from tools.sitemap_checker import show_sitemap_checker
from tools.feed_checker import show_feed_checker
from tools.price_vortex import show_price_vortex

# ── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dijital Araçlar",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_styles()

# ── Session state ────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "Ana Sayfa"

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=80)
    else:
        st.markdown("### 242")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    selected = option_menu(
        menu_title=None,
        options=["Ana Sayfa", "Sitemap Checker", "Feed Checker", "Price Vortex"],
        icons=["house", "map", "link-45deg", "tornado"],
        default_index=["Ana Sayfa", "Sitemap Checker", "Feed Checker", "Price Vortex"].index(
            st.session_state.page
        ),
        styles={
            "container": {
                "padding": "4px 0",
                "background-color": "transparent",
            },
            "icon": {
                "color": "#888",
                "font-size": "16px",
            },
            "nav-link": {
                "font-size": "13.5px",
                "font-weight": "500",
                "color": "#888",
                "padding": "10px 14px",
                "border-radius": "10px",
                "margin": "2px 0",
                "--hover-color": "#f0eeff",
            },
            "nav-link-selected": {
                "background-color": "#f0eeff",
                "color": "#6F55FF",
                "font-weight": "600",
            },
        },
    )

    if selected != st.session_state.page:
        st.session_state.page = selected
        st.rerun()

    st.markdown("""
    <div style="position:fixed;bottom:20px;left:0;width:230px;padding:0 20px;box-sizing:border-box;">
        <hr style="border:none;border-top:1px solid #eee;margin-bottom:10px;">
        <p style="color:#bbb;font-size:11px;margin:0;">© 2024 242</p>
    </div>
    """, unsafe_allow_html=True)

# ── Pages ────────────────────────────────────────────────────
if st.session_state.page == "Ana Sayfa":

    # Hero
    st.markdown("""
    <div style="padding:48px 0 40px 0;">
        <p style="color:#6F55FF;font-size:13px;font-weight:600;letter-spacing:1.5px;margin-bottom:10px;text-transform:uppercase;">Dijital Araçlar</p>
        <h1 style="font-size:2.8rem;font-weight:800;color:#111;line-height:1.15;margin:0 0 14px 0;">
            Dijital Kontrolleri.<br>Kolaylaştırılmış.
        </h1>
        <p style="color:#666;font-size:16px;margin:0;">Ne yapmak istiyorsun?</p>
    </div>
    """, unsafe_allow_html=True)

    # Quick-start tiles
    qs1, qs2, qs3 = st.columns(3, gap="large")

    with qs1:
        st.markdown("""
        <div class="qs-tile">
            <div class="qs-num">01</div>
            <div class="qs-icon">🧭</div>
            <h3>Sitemap kontrol et</h3>
            <p>Kırık linkleri ve 404 sayfalarını tespit et.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button("Sitemap URL gir →", key="qs_sitemap", use_container_width=True):
            st.session_state.page = "Sitemap Checker"
            st.rerun()

    with qs2:
        st.markdown("""
        <div class="qs-tile">
            <div class="qs-num">02</div>
            <div class="qs-icon">🔗</div>
            <h3>Feed URL'lerini kontrol et</h3>
            <p>Google veya Facebook feed'indeki URL durumlarını gör.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button("Feed URL veya dosya yükle →", key="qs_feed", use_container_width=True):
            st.session_state.page = "Feed Checker"
            st.rerun()

    with qs3:
        st.markdown("""
        <div class="qs-tile">
            <div class="qs-num">03</div>
            <div class="qs-icon">🌪️</div>
            <h3>Fiyat & stok karşılaştır</h3>
            <p>Ürün CSV'ni Google feed'iyle karşılaştır, uyuşmazlıkları bul.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button("CSV ve feed yükle →", key="qs_vortex", use_container_width=True):
            st.session_state.page = "Price Vortex"
            st.rerun()

elif st.session_state.page == "Sitemap Checker":
    show_sitemap_checker()

elif st.session_state.page == "Feed Checker":
    show_feed_checker()

elif st.session_state.page == "Price Vortex":
    show_price_vortex()
