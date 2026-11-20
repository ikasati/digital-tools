import unicodedata
import xml.etree.ElementTree as ET

import pandas as pd
import streamlit as st

from utils.http import fetch_bytes, is_http_url
from utils.ui import page_header, step, result_banner, metric_row, filterable_table, read_csv, to_csv_bytes

G_NS = {"g": "http://base.google.com/ns/1.0"}

R_OK = "✅ Uyumlu"
R_PRICE = "❌ Fiyat farkı"
R_STOCK = "❌ Stok farkı"
R_BOTH = "❌ Fiyat + stok farkı"
R_UNKNOWN = "⚠️ Fiyat okunamadı"
RESULT_ORDER = [R_OK, R_BOTH, R_PRICE, R_STOCK, R_UNKNOWN]


# ── Helpers ────────────────────────────────────────────────
def parse_price(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    for token in ("TRY", "USD", "EUR", "TL", "₺", " ", " "):
        s = s.replace(token, "")
    if not s:
        return None
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def super_clean(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).strip().lower().replace(" ", "-").replace("\xa0", "")
    return "".join(c for c in s if c.isalnum() or c in "-_")


def _text(item, path):
    el = item.find(path, G_NS)
    return el.text.strip() if el is not None and el.text else ""


def _norm_availability(v):
    return v.lower().strip().replace("_", " ")  # Google accepts both "in stock" and "in_stock"


def process_xml_feed(content):
    tree = ET.fromstring(content)
    items = tree.findall(".//item") or tree.findall(".//{http://www.w3.org/2005/Atom}entry")
    rows = []
    for item in items:
        link = _text(item, "g:link")
        if not is_http_url(link):
            continue  # skip javascript:/data:/empty links; they'd render as clickable links
        path = link.split("://", 1)[-1].split("/", 1)[-1] if "://" in link else link.lstrip("/")
        slug, _, vid = path.partition("?vid=")
        rows.append({
            "Slug": slug.strip().rstrip("/"),
            "Variant ID": vid.split("&")[0],
            "Google Price": _text(item, "g:price"),
            "Google Sale Price": _text(item, "g:sale_price"),
            "Google Availability": _norm_availability(_text(item, "g:availability")),
            "Full URL": link,
        })
    return pd.DataFrame(rows, columns=["Slug", "Variant ID", "Google Price", "Google Sale Price",
                                       "Google Availability", "Full URL"])


def compare(df_csv, df_feed):
    """Match site CSV rows to feed items (slug+variant, falling back to slug). Pure function, O(n+m)."""
    stock_col = next((c for c in df_csv.columns if c.startswith("Stok:")), None)
    vid_col = "Varyant ID" if "Varyant ID" in df_csv.columns else None

    feed_slug = df_feed["Slug"].map(super_clean)
    feed_full = feed_slug + "-" + df_feed["Variant ID"].fillna("").map(super_clean)
    by_full, by_slug = {}, {}
    for idx, full, slug in zip(df_feed.index, feed_full, feed_slug):
        by_full.setdefault(full, idx)
        by_slug.setdefault(slug, idx)

    rows, unmatched_csv, matched_feed = [], [], set()
    for idx, row in df_csv.iterrows():
        slug = super_clean(row.get("Slug"))
        full = slug + "-" + (super_clean(row.get(vid_col)) if vid_col else "")
        fidx = by_full.get(full, by_slug.get(slug))
        if fidx is None:
            unmatched_csv.append(idx)
            continue
        matched_feed.add(fidx)
        f = df_feed.loc[fidx]

        site_raw = row.get("İndirimli Fiyatı")
        if site_raw is None or pd.isna(site_raw) or not str(site_raw).strip():
            site_raw = row.get("Satış Fiyatı")
        feed_raw = f["Google Sale Price"] or f["Google Price"]
        g_price, w_price = parse_price(feed_raw), parse_price(site_raw)
        price_ok = None if g_price is None or w_price is None else abs(g_price - w_price) < 0.01

        site_stock = pd.to_numeric(row.get(stock_col) if stock_col else None, errors="coerce")
        site_stock = 0 if pd.isna(site_stock) else site_stock
        site_avail = "in stock" if site_stock > 0 else "out of stock"
        stock_ok = site_avail == f["Google Availability"] if stock_col else True

        if price_ok is None:
            result = R_UNKNOWN
        elif price_ok and stock_ok:
            result = R_OK
        elif not price_ok and not stock_ok:
            result = R_BOTH
        else:
            result = R_PRICE if not price_ok else R_STOCK

        rows.append({
            "Sonuç": result,
            "Ürün Adı": row.get("İsim", ""),
            "Ürün URL": f["Full URL"],
            "Site Fiyatı": w_price,
            "Google Fiyatı": g_price,
            "Fark": None if price_ok is None else round(g_price - w_price, 2),
            "Site Stok": site_stock,
            "Google Stok": f["Google Availability"],
        })

    return {
        "compare": pd.DataFrame(rows, columns=["Sonuç", "Ürün Adı", "Ürün URL", "Site Fiyatı", "Google Fiyatı",
                                               "Fark", "Site Stok", "Google Stok"]),
        "missing_in_feed": df_csv.loc[unmatched_csv],
        "missing_in_csv": df_feed.loc[[i for i in df_feed.index if i not in matched_feed]],
        "stock_checked": stock_col is not None,
    }


def _reset_vortex():
    for k in ["vortex_result", "vortex_feed_content", "vortex_feed_name"]:
        st.session_state.pop(k, None)


# ── Results ────────────────────────────────────────────────
def _show_results():
    res = st.session_state["vortex_result"]
    df = res["compare"]
    counts = df["Sonuç"].value_counts()
    price_bad = int(counts.get(R_PRICE, 0) + counts.get(R_BOTH, 0))
    stock_bad = int(counts.get(R_STOCK, 0) + counts.get(R_BOTH, 0))

    result_banner(f"Karşılaştırma tamamlandı: **{len(df)}** ürün eşleşti.", "vortex_reset", _reset_vortex)
    metric_row([
        ("Eşleşen", len(df)),
        ("✅ Uyumlu", int(counts.get(R_OK, 0))),
        ("❌ Fiyat farkı", price_bad),
        ("❌ Stok farkı", stock_bad if res["stock_checked"] else "–"),
        ("Feed'de yok", len(res["missing_in_feed"]), "Sitede olup feed'de bulunamayan ürünler."),
        ("Sitede yok", len(res["missing_in_csv"]), "Feed'de olup site CSV'sinde bulunamayan ürünler."),
    ])
    if not res["stock_checked"]:
        st.warning("CSV'de `Stok:` ile başlayan sütun bulunamadı; stok karşılaştırması atlandı.")

    t1, t2, t3 = st.tabs([f"Karşılaştırma ({len(df)})",
                          f"Feed'de eksik ({len(res['missing_in_feed'])})",
                          f"Sitede eksik ({len(res['missing_in_csv'])})"])
    with t1:
        if df.empty:
            st.info("Hiç ürün eşleşmedi. CSV'deki Slug değerleri feed linkleriyle uyuşmuyor olabilir.")
        else:
            filterable_table(
                df, key="vortex", file_stem="fiyat_stok_karsilastirma", ok_labels=(R_OK,), order=RESULT_ORDER,
                search_cols=("Ürün Adı", "Ürün URL"), search_placeholder="Ürün adı veya URL",
                column_config={
                    "Ürün URL": st.column_config.LinkColumn("Ürün URL"),
                    "Site Fiyatı": st.column_config.NumberColumn(format="%.2f"),
                    "Google Fiyatı": st.column_config.NumberColumn(format="%.2f"),
                    "Fark": st.column_config.NumberColumn(format="%+.2f", help="Google − Site"),
                },
            )
    for tab, name, file in ((t2, "missing_in_feed", "feeddeki_eksikler"), (t3, "missing_in_csv", "sitedeki_eksikler")):
        with tab:
            part = res[name]
            if part.empty:
                st.info("Eksik ürün yok. 🎉")
                continue
            st.download_button("⬇️ CSV İndir", to_csv_bytes(part), f"{file}.csv", "text/csv", key=f"vortex_dl_{name}")
            st.dataframe(part, use_container_width=True, hide_index=True)


# ── Main View ──────────────────────────────────────────────
def show_price_vortex():
    page_header("🌪️", "Price Vortex",
                "Ürün CSV'nizi Google Merchant Center feed'iyle karşılaştırın. Fiyat ve stok uyuşmazlıklarını anında tespit edin.")

    if "vortex_result" in st.session_state:
        _show_results()
        return

    col1, col2 = st.columns(2, gap="large")
    with col1:
        step(1, "Ürün CSV'si")
        csv_file = st.file_uploader("ikas ürün dışa aktarımı (CSV)", type=["csv"], key="vortex_csv_upload")
        st.caption("Gerekli sütun: **Slug**. Kullanılanlar: Varyant ID, İsim, Satış Fiyatı, İndirimli Fiyatı, Stok:…")

    with col2:
        step(2, "Google Merchant XML feed'i")
        if "vortex_feed_content" in st.session_state:
            st.success(f"Feed hazır: `{st.session_state['vortex_feed_name']}`")
            if st.button("↩️ Feed'i değiştir", key="vortex_feed_change"):
                for k in ["vortex_feed_content", "vortex_feed_name"]:
                    st.session_state.pop(k, None)
                st.rerun()
        else:
            tab_url, tab_file = st.tabs(["🔗 URL", "📁 Dosya"])
            with tab_url:
                feed_url = st.text_input("Feed URL", placeholder="https://...", key="vortex_feed_url",
                                         label_visibility="collapsed")
                if st.button("Feed'i Getir", key="vortex_fetch", disabled=not feed_url.strip()):
                    with st.spinner("Feed indiriliyor..."):
                        try:
                            st.session_state["vortex_feed_content"] = fetch_bytes(feed_url.strip())
                            st.session_state["vortex_feed_name"] = feed_url.strip()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Feed alınamadı: {e}")
            with tab_file:
                feed_file = st.file_uploader("XML feed", type=["xml"], key="vortex_xml_upload",
                                             label_visibility="collapsed")
                if feed_file:
                    st.session_state["vortex_feed_content"] = feed_file.getvalue()
                    st.session_state["vortex_feed_name"] = feed_file.name
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    ready = csv_file is not None and "vortex_feed_content" in st.session_state
    if not ready:
        st.info("Başlamak için ürün CSV'nizi yükleyin ve bir Google feed'i sağlayın.")
        return
    if not st.button("🚀 Karşılaştırmayı Başlat", key="vortex_run"):
        return

    with st.spinner("Karşılaştırılıyor..."):
        try:
            df_csv = read_csv(csv_file)
        except Exception as e:
            st.error(f"CSV okunamadı: {e}")
            return
        if "Slug" not in df_csv.columns:
            st.error(f"CSV'de **Slug** sütunu yok. Bulunan sütunlar: {', '.join(df_csv.columns)}")
            return
        try:
            df_feed = process_xml_feed(st.session_state["vortex_feed_content"])
        except ET.ParseError as e:
            st.error(f"Feed XML'i okunamadı: {e}")
            return
        if df_feed.empty:
            st.error("Feed'de hiç ürün (<item>) bulunamadı.")
            return
        st.session_state["vortex_result"] = compare(df_csv, df_feed)
    st.rerun()
