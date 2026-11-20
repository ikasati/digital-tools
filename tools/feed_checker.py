import xml.etree.ElementTree as ET

import pandas as pd
import streamlit as st

from utils.http import safe_get, check_url, OK_LABEL
from utils.ui import page_header, result_banner, http_summary, filterable_table, run_parallel, read_csv

G_NS = {"g": "http://base.google.com/ns/1.0"}


def _parse_feed(content, file_type):
    """Return a de-duplicated list of product URLs. Raises ValueError with a user-facing message."""
    if file_type == "csv":
        df = read_csv(content)
        cols = {c.lower().strip(): c for c in df.columns}
        if "link" not in cols:
            raise ValueError(f"CSV'de 'link' sütunu bulunamadı. Bulunan sütunlar: {', '.join(df.columns)}")
        urls = df[cols["link"]].dropna().astype(str).str.strip().tolist()
    else:
        try:
            tree = ET.fromstring(content)
        except ET.ParseError as e:
            raise ValueError(f"XML ayrıştırılamadı: {e}")
        urls = [e.text.strip() for e in tree.findall(".//g:link", G_NS) if e.text]
        if not urls:
            urls = [e.text.strip() for e in tree.findall(".//{*}link") if e.text and e.text.strip().startswith("http")]
    return list(dict.fromkeys(u for u in urls if u))


def _load(content, file_type):
    try:
        urls = _parse_feed(content, file_type)
    except ValueError as e:
        st.error(str(e))
        return
    if not urls:
        st.error("Feed'de hiç ürün URL'si bulunamadı.")
        return
    st.session_state["feed_urls"] = urls
    st.rerun()


def _reset_feed():
    for k in ["feed_urls", "feed_ran", "feed_df"]:
        st.session_state.pop(k, None)


def _show_results():
    df = st.session_state["feed_df"]
    result_banner(f"Kontrol tamamlandı: **{len(df)}** ürün URL'si tarandı.", "feed_reset", _reset_feed)
    http_summary(df, noun="ürün")
    filterable_table(
        df, key="feed", file_stem="feed_kontrol_sonuclari", ok_labels=(OK_LABEL,),
        search_cols=("URL", "Son URL"), search_placeholder="örn. ürün adı veya ?vid=",
        column_config={"URL": st.column_config.LinkColumn("URL"),
                       "Son URL": st.column_config.LinkColumn("Son URL")},
    )


def show_feed_checker():
    page_header("🔗", "Feed Checker",
                "Facebook veya Google Merchant Center feed'lerinizdeki tüm ürün URL'lerinin HTTP durumunu kontrol edin.")

    if st.session_state.get("feed_ran"):
        _show_results()
        return

    # ── Feed loaded, waiting to run ──────────────────────────
    if "feed_urls" in st.session_state:
        urls = st.session_state["feed_urls"]
        st.success(f"Feed yüklendi: **{len(urls)}** benzersiz ürün URL'si bulundu.")
        with st.expander("Önizleme (ilk 10 URL)"):
            st.dataframe(pd.DataFrame({"URL": urls[:10]}), use_container_width=True, hide_index=True)
        with st.expander("⚙️ Gelişmiş ayarlar"):
            workers = st.slider("Eşzamanlı istek", 1, 50, 20, key="feed_workers")

        c1, c2, _ = st.columns([1, 1, 3])
        with c1:
            run = st.button("🚀 Kontrolü Başlat", key="feed_run", use_container_width=True)
        with c2:
            if st.button("↩️ Farklı Feed", key="feed_change", use_container_width=True):
                _reset_feed()
                st.rerun()
        if run:
            results = run_parallel(lambda u: check_url(u, timeout=8, retries=1), urls,
                                   workers=workers, text="Ürün URL'leri kontrol ediliyor")
            st.session_state["feed_df"] = pd.DataFrame(results)
            st.session_state["feed_ran"] = True
            st.rerun()
        return

    # ── Input ────────────────────────────────────────────────
    tab_url, tab_file = st.tabs(["🔗 Feed URL'si", "📁 Dosya yükle"])
    with tab_url:
        feed_url = st.text_input("Feed URL", placeholder="https://magazaniz.com/feed.xml", key="feed_url_input")
        if st.button("Feed'i Getir", key="feed_fetch", disabled=not feed_url.strip()):
            with st.spinner("Feed indiriliyor..."):
                try:
                    r = safe_get(feed_url.strip(), timeout=30)
                    r.raise_for_status()
                except Exception as e:
                    st.error(f"Feed alınamadı: {e}")
                else:
                    ct = r.headers.get("Content-Type", "")
                    file_type = "csv" if (feed_url.strip().lower().endswith(".csv") or "csv" in ct) else "xml"
                    _load(r.content, file_type)
    with tab_file:
        uploaded = st.file_uploader("Feed dosyası", type=["xml", "csv"], key="feed_file_upload",
                                    help="Google feed'leri genellikle XML, Facebook feed'leri XML veya CSV olur.")
        if uploaded:
            _load(uploaded.getvalue(), "csv" if uploaded.name.lower().endswith(".csv") else "xml")
