import streamlit as st
import requests
import xml.etree.ElementTree as ET
import concurrent.futures
import time
from collections import Counter
import pandas as pd
from io import BytesIO


def _get_status(url, retries=2):
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=6, allow_redirects=True)
            redirect_chain = " → ".join([r.url for r in response.history] + [response.url])
            redirect_codes = " → ".join([str(r.status_code) for r in response.history] + [str(response.status_code)])
            return url, response.status_code, redirect_chain, redirect_codes
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return url, "Error", "N/A", f"Error: {e}"


def _parse_feed(content, file_type="xml"):
    urls = []
    if file_type == "xml":
        try:
            tree = ET.fromstring(content)
            ns = {'g': 'http://base.google.com/ns/1.0'}
            urls = [e.text for e in tree.findall(".//g:link", ns) if e.text]
            if not urls:
                urls = [e.text for e in tree.findall(".//{*}link") if e.text and e.text.startswith("http")]
        except Exception as e:
            st.error(f"XML ayrıştırma hatası: {e}")
    else:
        try:
            df = pd.read_csv(BytesIO(content))
            df.columns = df.columns.str.lower()
            if "link" in df.columns:
                urls = df["link"].dropna().tolist()
            else:
                st.error("CSV dosyasında 'link' sütunu bulunamadı.")
        except Exception as e:
            st.error(f"CSV ayrıştırma hatası: {e}")
    return urls


def _reset_feed():
    for k in ["feed_urls", "feed_ran", "feed_df", "feed_status_counter"]:
        st.session_state.pop(k, None)


def show_feed_checker():
    # ── Header ──────────────────────────────────────────────
    st.markdown("""
    <div style="padding:32px 0 24px 0">
        <p style="color:#6F55FF;font-size:13px;font-weight:600;letter-spacing:1px;margin-bottom:6px;">ARAÇ 2</p>
        <h1 style="margin:0;font-size:2rem;">🔗 Feed Checker</h1>
        <p style="color:#666;margin-top:8px;font-size:15px;">Facebook veya Google Merchant Center feed'lerinizdeki tüm ürün URL'lerinin HTTP durumunu kontrol edin.</p>
    </div>
    <hr style="border:none;border-top:1px solid #eee;margin-bottom:28px;">
    """, unsafe_allow_html=True)

    # ── Show results if already ran ──────────────────────────
    if st.session_state.get("feed_ran"):
        df = st.session_state["feed_df"]
        status_counter = st.session_state["feed_status_counter"]

        col_title, col_btn = st.columns([4, 1])
        with col_title:
            st.success(f"✅ Kontrol tamamlandı — **{len(df)}** URL tarandı.")
        with col_btn:
            if st.button("🔄 Yeni Test", key="feed_reset"):
                _reset_feed()
                st.rerun()

        cols = st.columns(min(len(status_counter), 5))
        for col, (code, count) in zip(cols, sorted(status_counter.items())):
            col.metric(str(code), count)

        st.markdown("<br>", unsafe_allow_html=True)
        col_dl, _ = st.columns([1, 4])
        with col_dl:
            st.download_button(
                "⬇️ CSV İndir",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="feed_kontrol_sonuclari.csv",
                mime="text/csv",
                key="feed_csv_dl"
            )
        st.dataframe(df, use_container_width=True)
        return

    # ── Input: already fetched URLs waiting to run ───────────
    if "feed_urls" in st.session_state:
        urls = st.session_state["feed_urls"]
        st.success(f"Feed yüklendi — **{len(urls)} URL** bulundu.")

        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("🚀 Kontrolü Başlat", key="feed_run"):
                pb = st.progress(0, text="URL'ler kontrol ediliyor...")
                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                    futures = {executor.submit(_get_status, url): url for url in urls}
                    for i, future in enumerate(concurrent.futures.as_completed(futures)):
                        try:
                            results.append(future.result())
                        except Exception:
                            results.append((futures[future], "Error", "N/A", "Error"))
                        pb.progress((i + 1) / len(urls), text=f"Kontrol ediliyor: {i+1}/{len(urls)}")
                pb.empty()

                df = pd.DataFrame(results, columns=["Orijinal URL", "Son Durum Kodu", "Yönlendirme Zinciri", "Yönlendirme Kodları"])
                df["Yönlendirme Var mı"] = df["Yönlendirme Kodları"].apply(lambda x: "→" in str(x))

                all_statuses = []
                for _, _, _, rc in results:
                    if "Error" not in str(rc):
                        all_statuses.extend(str(rc).split(" → "))
                    else:
                        all_statuses.append("Error")

                st.session_state["feed_df"] = df
                st.session_state["feed_status_counter"] = dict(Counter(all_statuses))
                st.session_state["feed_ran"] = True
                st.rerun()
        with col2:
            if st.button("🔄 Farklı Feed", key="feed_change"):
                _reset_feed()
                st.rerun()
        return

    # ── Input form ───────────────────────────────────────────
    input_mode = st.radio(
        "Feed nasıl sağlamak istersiniz?",
        ["🔗 URL Girin", "📁 Dosya Yükle"],
        horizontal=True,
        key="feed_input_mode"
    )

    if input_mode == "🔗 URL Girin":
        feed_url = st.text_input(
            "Feed URL",
            placeholder="https://example.com/feed.xml  ya da  https://example.com/feed.csv",
            key="feed_url_input"
        )
        if feed_url.strip():
            if st.button("Feed'i Getir", key="feed_fetch"):
                with st.spinner("Feed indiriliyor..."):
                    try:
                        r = requests.get(feed_url.strip(), timeout=20)
                        r.raise_for_status()
                        ct = r.headers.get("Content-Type", "")
                        file_type = "csv" if (feed_url.strip().endswith(".csv") or "csv" in ct) else "xml"
                        urls = _parse_feed(r.content, file_type)
                        if urls:
                            st.session_state["feed_urls"] = urls
                            st.rerun()
                        else:
                            st.error("Feed'de hiç URL bulunamadı.")
                    except Exception as e:
                        st.error(f"Feed alınamadı: {e}")
    else:
        uploaded = st.file_uploader(
            "Feed dosyası seçin",
            type=["xml", "csv"],
            help="Google feed'leri genellikle XML, Facebook feed'leri XML veya CSV olabilir.",
            key="feed_file_upload"
        )
        if uploaded:
            file_type = "csv" if uploaded.name.endswith(".csv") else "xml"
            urls = _parse_feed(uploaded.read(), file_type)
            if urls:
                st.session_state["feed_urls"] = urls
                st.rerun()
