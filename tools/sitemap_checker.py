import gzip
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from utils.http import safe_get, check_url, OK_LABEL
from utils.ui import page_header, result_banner, http_summary, filterable_table, run_parallel

MAX_SITEMAPS = 500  # safety cap for runaway / circular sitemap indexes


def _fetch_xml(url):
    r = safe_get(url, timeout=15)
    r.raise_for_status()
    content = r.content
    if content[:2] == b"\x1f\x8b":  # .xml.gz served without Content-Encoding
        content = gzip.decompress(content)
    return ET.fromstring(content)


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _page_urls(root):
    return [
        loc.text.strip() for loc in root.findall(".//{*}url/{*}loc")
        if loc.text and "/cdn." not in loc.text
    ]


def _normalize_input(raw):
    raw = raw.strip()
    if not raw.startswith("http"):
        raw = "https://" + raw
    # Only append /sitemap.xml when the user gave a bare domain
    if urlparse(raw).path in ("", "/"):
        raw = raw.rstrip("/") + "/sitemap.xml"
    return raw


def _collect(start_url, on_progress):
    """Walk a sitemap or (nested) sitemap index. Returns (sitemaps_read, page_urls, failed_sitemaps)."""
    queue, seen = [start_url], set()
    read, urls, failed = [], [], []
    while queue and len(seen) < MAX_SITEMAPS:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        try:
            root = _fetch_xml(sm)
        except Exception as e:
            if sm == start_url:
                raise
            failed.append({"Sitemap": sm, "Hata": type(e).__name__})
            continue
        if _local(root.tag) == "sitemapindex":
            queue.extend(l.text.strip() for l in root.findall("{*}sitemap/{*}loc") if l.text)
        else:
            read.append(sm)
            urls.extend(_page_urls(root))
        on_progress(len(seen), len(seen) + len(queue))
    return read, list(dict.fromkeys(urls)), failed


def _reset_sitemap():
    for k in ["sitemap_df", "sitemap_ran", "sitemap_meta"]:
        st.session_state.pop(k, None)


def _show_results():
    df = st.session_state["sitemap_df"]
    meta = st.session_state["sitemap_meta"]

    result_banner(f"Kontrol tamamlandı: **{meta['sitemaps']}** sitemap içinden **{len(df)}** URL tarandı.",
                  "sitemap_reset", _reset_sitemap)
    http_summary(df)

    if meta["failed"]:
        with st.expander(f"⚠️ {len(meta['failed'])} alt sitemap okunamadı"):
            st.dataframe(pd.DataFrame(meta["failed"]), use_container_width=True, hide_index=True)

    filterable_table(
        df, key="sitemap", file_stem="sitemap_kontrol_sonuclari", ok_labels=(OK_LABEL,),
        search_cols=("URL", "Son URL"), search_placeholder="örn. /urun",
        column_config={"URL": st.column_config.LinkColumn("URL"),
                       "Son URL": st.column_config.LinkColumn("Son URL")},
    )


def show_sitemap_checker():
    page_header("🧭", "Sitemap Checker",
                "Sitemap'lerinizdeki tüm URL'leri tarayın; 404'leri, yönlendirmeleri ve hataları Google'dan önce yakalayın.")

    if st.session_state.get("sitemap_ran"):
        _show_results()
        return

    url_input = st.text_input(
        "Sitemap URL veya alan adı",
        placeholder="örn. magazaniz.com  ya da  https://magazaniz.com/sitemap.xml",
        key="sitemap_url_input",
    )
    if url_input.strip():
        st.caption(f"Okunacak sitemap: `{_normalize_input(url_input)}`")

    with st.expander("⚙️ Gelişmiş ayarlar"):
        workers = st.slider("Eşzamanlı istek", 1, 50, 20, key="sitemap_workers",
                            help="Yüksek değerler daha hızlıdır ama siteyi yorabilir.")

    if not st.button("🚀 Kontrolü Başlat", key="sitemap_run", disabled=not url_input.strip()):
        return

    start = _normalize_input(url_input)
    status = st.empty()
    try:
        sitemaps, urls, failed = _collect(
            start, lambda done, total: status.info(f"Sitemap okunuyor: {done} / {total}"))
    except Exception as e:
        status.empty()
        st.error(f"Sitemap okunamadı (`{start}`): {e}")
        return
    status.empty()

    if not urls:
        st.warning("Sitemap'te hiç URL bulunamadı.")
        return

    st.info(f"**{len(sitemaps)}** sitemap · **{len(urls)}** URL kontrol edilecek")
    results = run_parallel(check_url, urls, workers=workers, text="URL'ler kontrol ediliyor")

    st.session_state["sitemap_df"] = pd.DataFrame(results)
    st.session_state["sitemap_meta"] = {"sitemaps": len(sitemaps), "failed": failed}
    st.session_state["sitemap_ran"] = True
    st.rerun()
