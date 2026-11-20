"""Shared UI building blocks so every tool looks and behaves the same."""
from io import BytesIO

import pandas as pd
import streamlit as st


def page_header(emoji, title, description):
    st.markdown(f"""
    <div style="padding:16px 0 24px 0">
        <h1 style="margin:0;font-size:2rem;">{emoji} {title}</h1>
        <p style="color:#666;margin-top:8px;font-size:15px;max-width:760px;">{description}</p>
    </div>
    <hr style="border:none;border-top:1px solid #eee;margin-bottom:28px;">
    """, unsafe_allow_html=True)


def step(number, text):
    st.markdown(f"##### {number} · {text}")


def result_banner(message, reset_key, on_reset, reset_label="🔄 Yeni Test"):
    col_msg, col_btn = st.columns([4, 1])
    with col_msg:
        st.success(message)
    with col_btn:
        if st.button(reset_label, key=reset_key, use_container_width=True):
            on_reset()
            st.rerun()


def metric_row(items):
    """items: list of (label, value) or (label, value, help)."""
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        col.metric(item[0], item[1], help=item[2] if len(item) > 2 else None)


def to_csv_bytes(df):
    # utf-8-sig adds a BOM so Excel shows Turkish characters (ç, ş, ğ, ı) correctly
    return df.to_csv(index=False).encode("utf-8-sig")


def read_csv(raw):
    """Read CSV bytes, sniffing the delimiter and trying common Turkish encodings."""
    if hasattr(raw, "getvalue"):
        raw = raw.getvalue()
    for enc in ("utf-8-sig", "cp1254", "latin-1"):
        try:
            return pd.read_csv(BytesIO(raw), sep=None, engine="python", encoding=enc, dtype=str)
        except UnicodeDecodeError:
            continue
    raise ValueError("Dosya kodlaması okunamadı.")


def filterable_table(df, key, file_stem, label_col="Sonuç", ok_labels=(), order=None,
                     search_cols=(), search_placeholder="Ara...", column_config=None, column_order=None):
    """Filter-by-result + search + download + table. Defaults to showing only problem rows."""
    present_set = set(df[label_col].dropna())
    ordered = order or sorted(present_set)
    present = [l for l in ordered if l in present_set]
    problems = [l for l in present if l not in ok_labels]

    f1, f2 = st.columns([3, 2])
    with f1:
        selected = st.multiselect(
            "Sonuca göre filtrele", present, default=problems or present, key=f"{key}_filter",
            help="Varsayılan olarak yalnızca dikkat gerektiren satırlar gösterilir.",
        )
    with f2:
        query = st.text_input("Ara", placeholder=search_placeholder, key=f"{key}_search") if search_cols else ""

    view = df[df[label_col].isin(selected)]
    if query.strip():
        q = query.strip().lower()
        mask = pd.Series(False, index=view.index)
        for c in search_cols:
            mask |= view[c].astype(str).str.lower().str.contains(q, regex=False)
        view = view[mask]

    hidden = [c for c in df.columns if c.startswith("_")]
    d1, d2, _ = st.columns([1, 1, 3])
    with d1:
        st.download_button("⬇️ Tümünü İndir", to_csv_bytes(df.drop(columns=hidden)), f"{file_stem}.csv",
                           "text/csv", key=f"{key}_dl_all", use_container_width=True)
    with d2:
        st.download_button("⬇️ Filtrelenmişi İndir", to_csv_bytes(view.drop(columns=hidden)),
                           f"{file_stem}_filtreli.csv", "text/csv", key=f"{key}_dl_view",
                           use_container_width=True, disabled=view.empty)

    if view.empty:
        if not problems and present:
            st.info("Sorun bulunamadı. Her şey yolunda. 🎉")
        else:
            st.info("Bu filtreyle eşleşen satır yok.")
        return

    st.caption(f"{len(view)} / {len(df)} satır gösteriliyor")
    st.dataframe(view.drop(columns=hidden), use_container_width=True, hide_index=True,
                 column_config=column_config, column_order=column_order)


def http_summary(df, noun="URL"):
    """Standard metric row for tools whose rows come from utils.http.check_url."""
    g = df["_group"].value_counts()
    total = len(df)
    ok = int(g.get("ok", 0))
    metric_row([
        (f"Toplam {noun}", total),
        ("✅ Sağlıklı", ok),
        ("🟡 Yönlendirme", int(g.get("redirect", 0)), "Yönlendirilen URL'ler; sitemap/feed'de son adres kullanılmalı."),
        ("❌ Hatalı", int(g.get("broken", 0)), "4xx/5xx dönen veya döngüye giren URL'ler."),
        ("⚠️ Başarısız", int(g.get("error", 0)), "Zaman aşımı, DNS veya bağlantı hatası."),
    ])
    if total:
        st.progress(ok / total, text=f"Sağlıklı oranı: %{ok / total * 100:.1f}")


def run_parallel(func, items, workers=20, text="Kontrol ediliyor"):
    """Run func over items in a thread pool with a progress bar; returns results in input order."""
    import concurrent.futures
    results = [None] * len(items)
    if not items:
        return results
    pb = st.progress(0.0, text=f"{text}...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(func, item): i for i, item in enumerate(items)}
        for done, fut in enumerate(concurrent.futures.as_completed(futures), start=1):
            results[futures[fut]] = fut.result()
            pb.progress(done / len(items), text=f"{text}: {done}/{len(items)}")
    pb.empty()
    return results
