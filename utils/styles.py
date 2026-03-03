import streamlit as st

def apply_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ── Hide sidebar collapse button ──────────────── */
    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }

    /* ── Global ────────────────────────────────────── */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
        background-color: #ffffff !important;
        color: #111111 !important;
    }
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* ── Sidebar shell ─────────────────────────────── */
    [data-testid="stSidebar"] {
        background-color: #0f0f0f !important;
        border-right: none !important;
    }
    
    /* 
       CRITICAL: Force backgrounds to be dark in sidebar 
       This targets the container and the menu items themselves
    */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        background-color: #0f0f0f !important;
    }
    
    /* Force option_menu transparency and dark theme */
    .nav-link {
        background-color: transparent !important;
        color: #bbb !important;
    }
    .nav-link:hover {
        background-color: rgba(111, 85, 255, 0.1) !important;
        color: white !important;
    }
    .nav-link.active {
        background-color: rgba(111, 85, 255, 0.15) !important;
        color: #6F55FF !important;
    }
    
    /* Remove any white backgrounds from the option menu container */
    .container-fluid {
        background-color: transparent !important;
    }

    /* ── Headings ───────────────────────────────────── */
    h1 { font-size:2.4rem !important; font-weight:800 !important; color:#111 !important; letter-spacing:-0.5px !important; }
    h2 { font-size:1.6rem !important; font-weight:700 !important; color:#111 !important; }
    h3 { font-size:1.1rem !important; font-weight:700 !important; color:#111 !important; }

    /* ── Buttons ────────────────────────────────────── */
    div.stButton > button {
        background-color: #6F55FF !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 22px !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        background-color: #5a42e0 !important;
        box-shadow: 0 4px 16px rgba(111,85,255,0.3) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Input styling ─────────────────────────────── */
    .stTextInput > div > div > input {
        background-color: #f7f7f7 !important;
        border: 1px solid #eee !important;
        border-radius: 10px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #6F55FF !important;
        box-shadow: 0 0 0 2px rgba(111,85,255,0.1) !important;
    }

    /* ── Quickstart tiles ───────────────────────────── */
    .qs-tile {
        background: #fff;
        border: 1px solid #e8e8e8;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        transition: all 0.25s ease;
    }
    .qs-tile:hover {
        border-color: #6F55FF;
        box-shadow: 0 8px 24px rgba(111,85,255,0.1);
        transform: translateY(-2px);
    }
    .qs-num {
        font-size: 10px;
        font-weight: 800;
        color: #DCFB3A;
        background: #111;
        padding: 2px 8px;
        border-radius: 5px;
        margin-bottom: 12px;
        display: inline-block;
    }
    .qs-icon { font-size: 24px; margin-bottom: 8px; }

    </style>
    """, unsafe_allow_html=True)
