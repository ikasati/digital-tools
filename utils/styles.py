import streamlit as st

def apply_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ── Hide sidebar collapse button (keep expand arrow) ── */
    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }


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
        min-width: 220px !important;
    }
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }

    /* ── Sidebar nav buttons ────────────────────────── */
    [data-testid="stSidebar"] div.stButton > button {
        background: transparent !important;
        color: #999 !important;
        border: none !important;
        border-radius: 10px !important;
        text-align: left !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        padding: 10px 14px !important;
        margin: 2px 0 !important;
        box-shadow: none !important;
        letter-spacing: 0 !important;
        text-transform: none !important;
        transition: background 0.18s, color 0.18s !important;
    }
    [data-testid="stSidebar"] div.stButton > button:hover {
        background: rgba(111,85,255,0.15) !important;
        color: #ffffff !important;
        box-shadow: none !important;
        transform: none !important;
    }

    /* ── Headings ───────────────────────────────────── */
    h1 { font-size:2.4rem !important; font-weight:800 !important; color:#111 !important; letter-spacing:-0.5px !important; }
    h2 { font-size:1.6rem !important; font-weight:700 !important; color:#111 !important; }
    h3 { font-size:1.1rem !important; font-weight:700 !important; color:#111 !important; }

    /* ── Main action buttons ────────────────────────── */
    div.stButton > button {
        background-color: #6F55FF !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 22px !important;
        transition: all 0.2s ease !important;
        letter-spacing: 0.2px !important;
    }
    div.stButton > button:hover {
        background-color: #5a42e0 !important;
        box-shadow: 0 4px 16px rgba(111,85,255,0.35) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Download buttons ───────────────────────────── */
    div.stDownloadButton > button {
        background-color: #111 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 22px !important;
        transition: all 0.2s ease !important;
    }
    div.stDownloadButton > button:hover {
        background-color: #333 !important;
        transform: translateY(-1px) !important;
    }

    /* ── Text inputs ────────────────────────────────── */
    .stTextInput > div > div > input {
        background-color: #f7f7f7 !important;
        color: #111 !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 10px !important;
        font-size: 15px !important;
        padding: 10px 14px !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #6F55FF !important;
        box-shadow: 0 0 0 3px rgba(111,85,255,0.12) !important;
    }

    /* ── File uploader ──────────────────────────────── */
    [data-testid="stFileUploader"] {
        background-color: #f7f7f7 !important;
        border: 1.5px dashed #d0d0d0 !important;
        border-radius: 12px !important;
        padding: 8px !important;
        transition: border-color 0.2s !important;
    }
    [data-testid="stFileUploader"]:hover { border-color: #6F55FF !important; }

    /* ── Progress bar ───────────────────────────────── */
    .stProgress > div > div > div > div {
        background-color: #6F55FF !important;
        border-radius: 99px !important;
    }
    .stProgress > div > div {
        background-color: #eee !important;
        border-radius: 99px !important;
    }

    /* ── Metrics ────────────────────────────────────── */
    [data-testid="stMetric"] {
        background: #f8f8f8;
        border-radius: 12px;
        padding: 16px 20px;
        border: 1px solid #eee;
    }
    [data-testid="stMetricLabel"] { color:#666 !important; font-size:12px !important; font-weight:500 !important; }
    [data-testid="stMetricValue"] { color:#6F55FF !important; font-weight:800 !important; font-size:2rem !important; }

    /* ── Radio ──────────────────────────────────────── */
    .stRadio > div { gap: 8px !important; }
    .stRadio label { font-size: 14px !important; }

    /* ── Alert ──────────────────────────────────────── */
    .stAlert { border-radius: 12px !important; font-size:14px !important; }

    /* ── Quickstart tiles on home ───────────────────── */
    .qs-tile {
        background: #fff;
        border: 1px solid #e8e8e8;
        border-radius: 16px;
        padding: 28px 24px 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        transition: all 0.25s ease;
        min-height: 160px;
    }
    .qs-tile:hover {
        border-color: #6F55FF;
        box-shadow: 0 8px 24px rgba(111,85,255,0.13);
        transform: translateY(-3px);
    }
    .qs-num {
        font-size: 11px;
        font-weight: 700;
        color: #DCFB3A;
        background: #111;
        display: inline-block;
        padding: 2px 8px;
        border-radius: 5px;
        letter-spacing: 1px;
        margin-bottom: 12px;
    }
    .qs-icon {
        font-size: 26px;
        margin-bottom: 8px;
    }
    .qs-tile h3 {
        font-size: 16px !important;
        font-weight: 700 !important;
        margin: 0 0 6px 0 !important;
    }
    .qs-tile p {
        color: #777;
        font-size: 13.5px;
        line-height: 1.5;
        margin: 0;
    }

    </style>
    """, unsafe_allow_html=True)
