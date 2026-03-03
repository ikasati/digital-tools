import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from collections import defaultdict
import concurrent.futures

HTTP_STATUS_MESSAGES = {
    200: "OK", 301: "Kalıcı Yönlendirme", 302: "Bulundu",
    400: "Hatalı İstek", 401: "Yetkisiz", 403: "Yasak",
    404: "Bulunamadı", 410: "Kaldırıldı", 500: "Sunucu Hatası",
    502: "Geçersiz Ağ Geçidi", 503: "Hizmet Kullanılamıyor",
    "Error": "İstek Başarısız", "Timeout (Future)": "Zaman Aşımı"
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _fetch_xml(url):
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.content


def _parse_index(xml):
    root = ET.fromstring(xml)
    return [e.text for e in root.findall(".//{*}loc") if e.text]


def _parse_urls(xml):
    root = ET.fromstring(xml)
    return [
        loc.text for loc in root.findall(".//{*}url/{*}loc")
        if loc is not None and loc.text and "/cdn." not in loc.text
    ]


def _check_url(url):
    try:
        r = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=10)
        return url, r.status_code
    except Exception:
        try:
            r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=10)
            return url, r.status_code
        except Exception:
            return url, "Error"


def _reset_sitemap():
    for k in ["sitemap_results", "sitemap_df", "sitemap_ran"]:
        st.session_state.pop(k, None)


def show_sitemap_checker():
    # ── Header ──────────────────────────────────────────────
    st.markdown("""
    <div style="padding:32px 0 24px 0">
        <p style="color:#6F55FF;font-size:13px;font-weight:600;letter-spacing:1px;margin-bottom:6px;">ARAÇ 1</p>
        <h1 style="margin:0;font-size:2rem;">🧭 Sitemap Checker</h1>
        <p style="color:#666;margin-top:8px;font-size:15px;">Sitemap'lerinizdeki tüm URL'leri tarayın; 404'leri, yönlendirmeleri ve hataları Google'dan önce yakalayın.</p>
    </div>
    <hr style="border:none;border-top:1px solid #eee;margin-bottom:28px;">
    """, unsafe_allow_html=True)

    # ── Show results if already ran ──────────────────────────
    if st.session_state.get("sitemap_ran"):
        df = st.session_state["sitemap_df"]
        status_counts = st.session_state["sitemap_status_counts"]

        col_title, col_btn = st.columns([4, 1])
        with col_title:
            st.success(f"✅ Kontrol tamamlandı — **{len(df)}** URL tarandı.")
        with col_btn:
            if st.button("🔄 Yeni Test", key="sitemap_reset"):
                _reset_sitemap()
                st.rerun()

        # Metrics
        cols = st.columns(min(len(status_counts), 5))
        for col, (code, count) in zip(cols, status_counts.items()):
            name = HTTP_STATUS_MESSAGES.get(code, str(code))
            col.metric(f"{code} — {name}", count)

        st.markdown("<br>", unsafe_allow_html=True)
        col_dl, _ = st.columns([1, 4])
        with col_dl:
            st.download_button(
                "⬇️ CSV İndir",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="sitemap_kontrol_sonuclari.csv",
                mime="text/csv",
                key="sitemap_csv_dl"
            )
        st.dataframe(df, use_container_width=True)
        return

    # ── Input form ───────────────────────────────────────────
    url_input = st.text_input(
        "Sitemap URL veya domain",
        placeholder="örn. example.com  ya da  https://example.com/sitemap.xml",
        key="sitemap_url_input"
    )

    # Show button immediately when there's any text
    if url_input.strip():
        if st.button("🚀 Kontrolü Başlat", key="sitemap_run"):
            raw = url_input.strip()
            if not raw.startswith("http"):
                raw = "https://" + raw
            if "/sitemap.xml" not in raw:
                raw = raw.rstrip("/") + "/sitemap.xml"

            with st.spinner("Sitemap index okunuyor..."):
                try:
                    index_xml = _fetch_xml(raw)
                except Exception as e:
                    st.error(f"Sitemap alınamadı: {e}")
                    return
                try:
                    sitemap_urls = _parse_index(index_xml)
                except Exception as e:
                    st.error(f"Sitemap ayrıştırılamadı: {e}")
                    return

                all_urls = []
                prog = st.progress(0, text="Alt sitemaplar okunuyor...")
                for i, s_url in enumerate(sitemap_urls):
                    try:
                        s_xml = _fetch_xml(s_url)
                        all_urls.extend(_parse_urls(s_xml))
                    except Exception:
                        pass
                    prog.progress((i + 1) / max(len(sitemap_urls), 1))
                prog.empty()

            if not all_urls:
                st.warning("Sitemapte hiç URL bulunamadı.")
                return

            st.info(f"**{len(sitemap_urls)}** sitemap · **{len(all_urls)}** URL kontrol edilecek")

            pb = st.progress(0, text="URL'ler kontrol ediliyor...")
            results = []
            status_counts = defaultdict(int)

            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                future_map = {executor.submit(_check_url, url): url for url in all_urls}
                for i, future in enumerate(concurrent.futures.as_completed(future_map)):
                    url = future_map[future]
                    try:
                        url, status = future.result(timeout=15)
                    except concurrent.futures.TimeoutError:
                        status = "Timeout (Future)"
                    except Exception:
                        status = "Error"
                    results.append({"URL": url, "Durum": status})
                    status_counts[status] += 1
                    pb.progress((i + 1) / len(all_urls), text=f"Kontrol ediliyor: {i+1}/{len(all_urls)}")

            pb.empty()
            st.session_state["sitemap_df"] = pd.DataFrame(results)
            st.session_state["sitemap_status_counts"] = dict(status_counts)
            st.session_state["sitemap_ran"] = True
            st.rerun()
