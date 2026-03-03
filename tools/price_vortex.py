import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import unicodedata
import requests
from io import BytesIO


# ── Helpers ────────────────────────────────────────────────
def find_text(parent, path, ns_map, default=""):
    el = parent.find(path, ns_map)
    if el is None or el.text is None:
        return default
    return el.text.strip()


def parse_price(val):
    if val is None: return None
    s = str(val).strip()
    if not s: return None
    s = s.replace("TRY", "").replace("USD", "").replace("TL", "").strip()
    s = s.replace("\u00a0", " ").replace(" ", "")
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."): s = s.replace(".", "").replace(",", ".")
        else: s = s.replace(",", "")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    try: return float(s)
    except: return None


def super_clean(s):
    if pd.isna(s): return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = s.strip().lower().replace(" ", "-").replace("\xa0", "")
    return "".join(c for c in s if c.isalnum() or c in ["-", "_"])


def process_xml_feed(content):
    tree = ET.fromstring(content)
    ns = {'g': 'http://base.google.com/ns/1.0'}

    first_item = tree.find(".//item")
    first_link = find_text(first_item, "g:link", ns, "") if first_item is not None else ""
    parsed_url = urlparse(first_link) if first_link else None
    base_url = (f"{parsed_url.scheme}://{parsed_url.netloc}") if parsed_url and parsed_url.scheme and parsed_url.netloc else ""

    feed_items = []
    for item in tree.findall(".//item"):
        link = find_text(item, "g:link", ns, "")
        price = find_text(item, "g:price", ns, "")
        sale_price = find_text(item, "g:sale_price", ns, "")
        availability = find_text(item, "g:availability", ns, "").lower().strip()

        if base_url and link.startswith(base_url + "/"):
            slug = link.replace(base_url + "/", "").split("?vid=")[0].strip()
        else:
            slug = link.split("://", 1)[-1].split("/", 1)[-1].split("?vid=")[0].strip()

        variant_id = link.split("?vid=")[1] if "?vid=" in link else ""

        feed_items.append({
            "Slug": slug,
            "Variant ID": variant_id,
            "Google Price": price,
            "Google Sale Price": sale_price,
            "Google Availability": availability,
            "Full URL": link
        })
    return pd.DataFrame(feed_items)


# ── Main View ──────────────────────────────────────────────
def show_price_vortex():
    st.markdown("""
    <div style="padding: 32px 0 24px 0">
        <p style="color:#6F55FF; font-size:13px; font-weight:600; letter-spacing:1px; margin-bottom:6px;">ARAÇ 3</p>
        <h1 style="margin:0; font-size:2rem;">🌪️ Price Vortex</h1>
        <p style="color:#666; margin-top:8px; font-size:15px;">ikas ürün CSV'nizi Google Merchant Center feed'iyle karşılaştırın. Fiyat ve stok uyuşmazlıklarını anında tespit edin.</p>
    </div>
    <hr style="border:none;border-top:1px solid #eee;margin-bottom:28px;">
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("**① ikas Ürün CSV'si**")
        csv_file = st.file_uploader("ikas CSV dışa aktarımını yükleyin", type=["csv"], key="csv_upload")
        if csv_file:
            st.success(f"Loaded: `{csv_file.name}`")

    with col2:
        st.markdown("**② Google Merchant XML Feed'i**")
        feed_source = st.radio("Feed kaynağı", ["🔗 URL", "📁 Yükle"], horizontal=True, key="feed_source")
        feed_content = None

        if feed_source == "🔗 URL":
            feed_url = st.text_input("Feed URL", placeholder="https://...", key="feed_url")
            if feed_url and st.button("Feed'i Getir", key="fetch_feed"):
                with st.spinner("Downloading feed..."):
                    try:
                        r = requests.get(feed_url.strip(), timeout=20)
                        r.raise_for_status()
                        feed_content = r.content
                        st.session_state["feed_content"] = feed_content
                        st.success("Feed downloaded successfully.")
                    except Exception as e:
                        st.error(f"Could not fetch feed: {e}")
        else:
            feed_file = st.file_uploader("XML feed'i yükleyin", type=["xml"], key="xml_upload")
            if feed_file:
                feed_content = feed_file.read()
                st.session_state["feed_content"] = feed_content
                st.success(f"Loaded: `{feed_file.name}`")

    # Allow persisting feed_content across interactions
    if "feed_content" in st.session_state:
        feed_content = st.session_state["feed_content"]

    st.markdown("<br>", unsafe_allow_html=True)

    if csv_file and feed_content:
        if st.button("🚀 Karşılaştırmayı Başlat"):
            with st.spinner("Processing data..."):
                df_csv = pd.read_csv(csv_file)
                df_feed = process_xml_feed(feed_content)

                stock_col = next((col for col in df_csv.columns if col.startswith("Stok:")), None)
                if not stock_col:
                    st.warning("⚠️ No column starting with `Stok:` found in CSV — stock comparison will be skipped.")

                df_csv["Slug_c"] = df_csv["Slug"].apply(super_clean)
                df_csv["VID_c"] = df_csv["Varyant ID"].fillna("").astype(str).apply(super_clean)
                df_feed["Slug_c"] = df_feed["Slug"].apply(super_clean)
                df_feed["VID_c"] = df_feed["Variant ID"].fillna("").astype(str).apply(super_clean)

                matched_rows = []
                for _, row in df_csv.iterrows():
                    mk_full = row["Slug_c"] + "-" + row["VID_c"]
                    mk_slug = row["Slug_c"]

                    match_row = df_feed[df_feed["Slug_c"] + "-" + df_feed["VID_c"] == mk_full]
                    if match_row.empty:
                        match_row = df_feed[df_feed["Slug_c"] == mk_slug]

                    if not match_row.empty:
                        match = match_row.iloc[0]

                        # Price
                        site_price_raw = row.get("İndirimli Fiyatı") if pd.notna(row.get("İndirimli Fiyatı")) else row.get("Satış Fiyatı")
                        feed_price_raw = match["Google Sale Price"] if str(match["Google Sale Price"]).strip() else match["Google Price"]
                        g_price = parse_price(feed_price_raw)
                        w_price = parse_price(site_price_raw)

                        if g_price is not None and w_price is not None:
                            price_match = "✅" if abs(g_price - w_price) < 0.01 else "❌"
                        else:
                            price_match = "⚠️"

                        # Stock
                        csv_stock = pd.to_numeric(row.get(stock_col, 0) if stock_col else 0, errors="coerce")
                        if pd.isna(csv_stock): csv_stock = 0
                        csv_status_str = "in stock" if csv_stock > 0 else "out of stock"
                        feed_status_str = match["Google Availability"]
                        stock_match = "✅" if csv_status_str == feed_status_str else "❌"

                        matched_rows.append({
                            "Product URL": match["Full URL"],
                            "Product Name": row.get("İsim", ""),
                            "Google Price": g_price,
                            "Website Price": w_price,
                            "Price Match": price_match,
                            "Google Stock": feed_status_str,
                            "Website Stock": csv_stock,
                            "Stock Match": stock_match,
                        })

                df_final = pd.DataFrame(matched_rows)

                df_csv["MK"] = df_csv["Slug_c"] + "-" + df_csv["VID_c"]
                df_feed["MK"] = df_feed["Slug_c"] + "-" + df_feed["VID_c"]
                missing_in_feed = df_csv[~df_csv["MK"].isin(df_feed["MK"])]
                missing_in_csv = df_feed[~df_feed["MK"].isin(df_csv["MK"])]

            st.success("✅ Comparison complete!")
            st.markdown("<br>", unsafe_allow_html=True)

            # Summary metrics
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Total Matched", len(df_final))
            m2.metric("Price ✅", (df_final["Price Match"] == "✅").sum())
            m3.metric("Price ❌", (df_final["Price Match"] == "❌").sum())
            m4.metric("Stock ✅", (df_final["Stock Match"] == "✅").sum())
            m5.metric("Stock ❌", (df_final["Stock Match"] == "❌").sum())
            m6.metric("Missing in Feed", len(missing_in_feed))

            st.markdown("<br>", unsafe_allow_html=True)

            dc1, dc2, dc3 = st.columns(3)
            dc1.download_button("📊 Karşılaştırma CSV", df_final.to_csv(index=False).encode("utf-8"), "karsilastirma.csv", "text/csv")
            dc2.download_button("❌ Feed'de Eksik", missing_in_feed.to_csv(index=False).encode("utf-8"), "feeddeki_eksikler.csv", "text/csv")
            dc3.download_button("❌ CSV'de Eksik", missing_in_csv.to_csv(index=False).encode("utf-8"), "csvdeki_eksikler.csv", "text/csv")

            st.dataframe(df_final, use_container_width=True)
    else:
        st.info("Başlamak için ikas CSV'nizi yükleyin ve bir Google feed'i sağlayın.")
