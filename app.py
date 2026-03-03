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

# Apply global CSS
apply_styles()

# ── Session state ────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "Ana Sayfa"

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=70)
    else:
        st.markdown("<h2 style='color:white; margin-bottom:20px;'>242</h2>", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Use a highly styled option_menu
    selected = option_menu(
        menu_title=None,
        options=["Ana Sayfa", "Sitemap Checker", "Feed Checker", "Price Vortex"],
        icons=["house-door", "map", "link-45deg", "tornado"],
        menu_icon="cast",
        default_index=["Ana Sayfa", "Sitemap Checker", "Feed Checker", "Price Vortex"].index(
            st.session_state.page
        ),
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#888", "font-size": "16px"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left",
                "margin": "4px 0",
                "color": "#bbb",
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

    # Footer
    st.markdown("""
    <div style="position:fixed;bottom:20px;left:0;width:240px;padding:0 24px;box-sizing:border-box;">
        <p style="color:#555;font-size:11px;margin:0;">© 2024 242</p>
    </div>
    """, unsafe_allow_html=True)

# ── Main Content Area ──────────────────────────────────────────

# If selected from sidebar but want to show on "Home" logic
if st.session_state.page == "Ana Sayfa":
    # Hero
    st.markdown("""
    <div style="padding:48px 0 40px 0;">
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
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Hemen Başla", key="qs_sitemap", use_container_width=True):
            st.session_state.active_tool = "sitemap"
            
    with qs2:
        st.markdown("""
        <div class="qs-tile">
            <div class="qs-num">02</div>
            <div class="qs-icon">🔗</div>
            <h3>Feed URL'lerini kontrol et</h3>
            <p>Google veya Facebook feed'indeki URL durumlarını gör.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Hemen Başla", key="qs_feed", use_container_width=True):
            st.session_state.active_tool = "feed"

    with qs3:
        st.markdown("""
        <div class="qs-tile">
            <div class="qs-num">03</div>
            <div class="qs-icon">🌪️</div>
            <h3>Fiyat & stok karşılaştır</h3>
            <p>Ürün CSV'ni Google feed'iyle karşılaştır.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Hemen Başla", key="qs_vortex", use_container_width=True):
            st.session_state.active_tool = "vortex"

    # Render selected tool directly on home page if active_tool is set
    if "active_tool" in st.session_state:
        st.markdown("<hr style='margin: 40px 0; border:none; border-top:1px solid #eee;'>", unsafe_allow_html=True)
        if st.session_state.active_tool == "sitemap":
            show_sitemap_checker()
        elif st.session_state.active_tool == "feed":
            show_feed_checker()
        elif st.session_state.active_tool == "vortex":
            show_price_vortex()
            
elif st.session_state.page == "Sitemap Checker":
    show_sitemap_checker()

elif st.session_state.page == "Feed Checker":
    show_feed_checker()

elif st.session_state.page == "Price Vortex":
    show_price_vortex()
