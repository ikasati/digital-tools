import streamlit as st
import os
from utils.styles import apply_styles
from tools.sitemap_checker import show_sitemap_checker
from tools.feed_checker import show_feed_checker
from tools.price_vortex import show_price_vortex

# ── Page Config ────────────────────────────────────────────
st.set_page_config(
    page_title="Dijital Araçlar",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_styles()

# ── Session state for page navigation ─────────────────────
if "page" not in st.session_state:
    st.session_state.page = "home"

# ── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=90)
    else:
        st.markdown("### 242")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    nav_items = [
        ("home",    "🏠", "Ana Sayfa"),
        ("sitemap", "🧭", "Sitemap Checker"),
        ("feed",    "🔗", "Feed Checker"),
        ("vortex",  "🌪️", "Price Vortex"),
    ]

    for key, icon, label in nav_items:
        active = st.session_state.page == key
        if st.sidebar.button(
            f"{icon}  {label}",
            key=f"nav_{key}",
            use_container_width=True,
        ):
            st.session_state.page = key
            st.rerun()

    st.markdown("""
    <div style="position:fixed;bottom:20px;left:0;width:230px;padding:0 20px;box-sizing:border-box;">
        <hr style="border:none;border-top:1px solid #eee;margin-bottom:10px;">
        <p style="color:#aaa;font-size:11px;margin:0;">© 2024 242 · Tüm hakları saklıdır.</p>
        <p style="color:#ccc;font-size:10px;margin:4px 0 0 0;">Yalnızca iç kullanım içindir.</p>
    </div>
    """, unsafe_allow_html=True)

# ── Pages ──────────────────────────────────────────────────
if st.session_state.page == "home":

    st.markdown("""
    <div style="padding:48px 0 32px 0;">
        <p style="color:#6F55FF;font-size:13px;font-weight:600;letter-spacing:1.5px;margin-bottom:8px;text-transform:uppercase;">Dijital Araçlar</p>
        <h1 style="font-size:2.8rem;font-weight:800;color:#111;line-height:1.15;margin:0;">
            E-ticaret araçların.<br>Güçlendirilmiş.
        </h1>
        <p style="color:#555;font-size:16px;margin-top:16px;">Sitemap denetimleri, feed sağlık kontrolleri ve fiyat karşılaştırmaları için hızlı ve güvenilir dahili araçlar.</p>
    </div>
    <hr style="border:none;border-top:1px solid #eee;margin-bottom:36px;">
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3, gap="large")

    with c1:
        st.markdown("""
        <div class="tool-card">
            <div class="card-icon">🧭</div>
            <h3>Sitemap Checker</h3>
            <p>Sitemap'lerinizdeki 404'leri ve kırık linkleri tarayın. Arama motorlarının yalnızca en iyi sayfalarınızı bulduğundan emin olun.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Araca Git →", key="btn_sitemap", use_container_width=True):
            st.session_state.page = "sitemap"
            st.rerun()

    with c2:
        st.markdown("""
        <div class="tool-card">
            <div class="card-icon">🔗</div>
            <span class="yellow-tag">YENİ</span>
            <h3>Feed Checker</h3>
            <p>Facebook ve Google feed'lerinizdeki tüm ürün URL'lerinin HTTP durumunu ve yönlendirme zincirlerini doğrulayın.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Araca Git →", key="btn_feed", use_container_width=True):
            st.session_state.page = "feed"
            st.rerun()

    with c3:
        st.markdown("""
        <div class="tool-card">
            <div class="card-icon">🌪️</div>
            <h3>Price Vortex</h3>
            <p>E-ticaret CSV'nizi Google Merchant Center feed'iyle karşılaştırın. Fiyat ve stok uyuşmazlıklarını anında tespit edin.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Araca Git →", key="btn_vortex", use_container_width=True):
            st.session_state.page = "vortex"
            st.rerun()

    st.markdown("""
    <div style="text-align:center;margin-top:60px;padding-top:24px;border-top:1px solid #f0f0f0;">
        <p style="color:#bbb;font-size:12px;margin:0;">© 2024 242 · Tüm hakları saklıdır · Yalnızca iç kullanım içindir</p>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.page == "sitemap":
    show_sitemap_checker()

elif st.session_state.page == "feed":
    show_feed_checker()

elif st.session_state.page == "vortex":
    show_price_vortex()
