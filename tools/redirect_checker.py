import streamlit as st
import requests
import pandas as pd
import concurrent.futures
from io import BytesIO
from urllib.parse import urlparse, unquote

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Result categories, in display order: (key, label, short explanation)
CATEGORIES = [
    ("ok",        "✅ Doğru",            "Tek adımda 301/308 ile doğru hedefe gidiyor."),
    ("temporary", "🟡 Geçici (302/307)", "Doğru hedef ama kalıcı değil; 301 olmalı."),
    ("chain",     "🟡 Zincirli",         "Doğru hedef ama birden fazla yönlendirme adımı var."),
    ("target_bad","🟠 Hedef Hatalı",     "Doğru hedefe gidiyor ama hedef sayfa 200 dönmüyor."),
    ("wrong",     "❌ Yanlış Hedef",     "Beklenenden farklı bir sayfaya gidiyor."),
    ("none",      "❌ Yönlendirme Yok",  "Kaynak adres hiç yönlendirilmiyor."),
    ("loop",      "❌ Döngü",            "Sonsuz yönlendirme döngüsü."),
    ("error",     "⚠️ Hata",             "İstek başarısız (zaman aşımı, DNS vb.)."),
]
LABEL = {k: label for k, label, _ in CATEGORIES}

SOURCE_HINTS = ["kaynak", "source", "from", "eski", "old"]
TARGET_HINTS = ["yönlendirilecek", "yonlendirilecek", "hedef", "target", "to", "yeni", "new"]


# ── Helpers ──────────────────────────────────────────────────
def _normalize_domain(raw):
    raw = raw.strip().rstrip("/")
    if raw and not raw.startswith("http"):
        raw = "https://" + raw
    return raw


def _host(netloc):
    return netloc.lower().removeprefix("www.")


def _comparable(url):
    """Return (host or None, path, query) for loose-but-correct URL comparison."""
    p = urlparse(url.strip())
    path = unquote(p.path).rstrip("/") or "/"
    return (_host(p.netloc) if p.netloc else None, path, p.query)


def _targets_match(final_url, expected):
    f_host, f_path, f_query = _comparable(final_url)
    e_host, e_path, e_query = _comparable(expected)
    if e_host and e_host != f_host:
        return False
    return f_path == e_path and f_query == e_query


def _build_source_url(source, domain):
    source = source.strip()
    if source.startswith("http"):
        return source
    if not source.startswith("/"):
        source = "/" + source
    return domain + source


def _check_redirect(idx, source, expected, domain, timeout):
    start_url = _build_source_url(source, domain)
    base = {"#": idx + 1, "Kaynak Adres": source, "Beklenen Hedef": expected, "Başlangıç URL": start_url}
    try:
        resp = requests.get(start_url, headers=HEADERS, allow_redirects=True, timeout=timeout, stream=True)
        resp.close()  # we only need headers / status, not the body
    except requests.TooManyRedirects:
        return {**base, "Sonuç": LABEL["loop"], "Gerçek Hedef": "", "Durum Zinciri": "Döngü",
                "Adım": None, "Yönlendirme Zinciri": "", "_cat": "loop"}
    except Exception as e:
        return {**base, "Sonuç": LABEL["error"], "Gerçek Hedef": type(e).__name__, "Durum Zinciri": "Hata",
                "Adım": None, "Yönlendirme Zinciri": "", "_cat": "error"}

    hops = resp.history
    codes = [r.status_code for r in hops] + [resp.status_code]
    chain = [r.url for r in hops] + [resp.url]
    matched = _targets_match(resp.url, expected)

    if not hops:
        cat = "none"
    elif not matched:
        cat = "wrong"
    elif resp.status_code != 200:
        cat = "target_bad"
    elif len(hops) > 1:
        cat = "chain"
    elif hops[0].status_code in (302, 303, 307):
        cat = "temporary"
    else:
        cat = "ok"

    return {
        **base,
        "Sonuç": LABEL[cat],
        "Gerçek Hedef": resp.url,
        "Durum Zinciri": " → ".join(map(str, codes)),
        "Adım": len(hops),
        "Yönlendirme Zinciri": " → ".join(chain),
        "_cat": cat,
    }


def _read_csv(uploaded):
    raw = uploaded.getvalue()
    for enc in ("utf-8-sig", "cp1254", "latin-1"):
        try:
            # sep=None lets pandas sniff comma vs. semicolon exports
            return pd.read_csv(BytesIO(raw), sep=None, engine="python", encoding=enc, dtype=str)
        except UnicodeDecodeError:
            continue
    raise ValueError("Dosya kodlaması okunamadı.")


def _guess_column(columns, hints, fallback):
    for col in columns:
        if any(h in col.lower() for h in hints):
            return col
    return columns[fallback] if len(columns) > fallback else columns[0]


def _template_csv():
    return pd.DataFrame({
        "Kaynak Adres": ["/eski-urun", "/kategori/eski"],
        "Yönlendirilecek Adres": ["/yeni-urun", "/kategori/yeni"],
    }).to_csv(index=False).encode("utf-8")


def _reset_redirect():
    for k in ["redirect_df", "redirect_ran", "redirect_domain"]:
        st.session_state.pop(k, None)


# ── Results view ─────────────────────────────────────────────
def _show_results():
    df = st.session_state["redirect_df"]
    counts = df["_cat"].value_counts().to_dict()
    total = len(df)
    ok = counts.get("ok", 0)
    warn = sum(counts.get(k, 0) for k in ("temporary", "chain", "target_bad"))
    bad = total - ok - warn

    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.success(f"Kontrol tamamlandı: **{total}** yönlendirme test edildi "
                   f"(`{st.session_state.get('redirect_domain') or 'tam URL'}`).")
    with col_btn:
        if st.button("🔄 Yeni Test", key="redirect_reset", use_container_width=True):
            _reset_redirect()
            st.rerun()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam", total)
    m2.metric("✅ Doğru", ok, f"%{ok / total * 100:.0f}" if total else None, delta_color="off")
    m3.metric("🟡 İyileştirilmeli", warn)
    m4.metric("❌ Sorunlu", bad)

    if total:
        st.progress(ok / total, text=f"Başarı oranı: %{ok / total * 100:.1f}")

    with st.expander("Sonuç kategorileri ne anlama geliyor?"):
        for key, label, desc in CATEGORIES:
            st.markdown(f"**{label}** ({counts.get(key, 0)}): {desc}")

    present = [label for key, label, _ in CATEGORIES if counts.get(key)]
    problems = [l for l in present if l != LABEL["ok"]]

    f1, f2 = st.columns([3, 2])
    with f1:
        selected = st.multiselect(
            "Sonuca göre filtrele", present,
            default=problems or present, key="redirect_filter",
            help="Varsayılan olarak yalnızca dikkat gerektiren satırlar gösterilir.",
        )
    with f2:
        query = st.text_input("Adreste ara", placeholder="örn. /kategori", key="redirect_search")

    view = df[df["Sonuç"].isin(selected)]
    if query.strip():
        q = query.strip().lower()
        view = view[view["Kaynak Adres"].str.lower().str.contains(q, regex=False)
                    | view["Beklenen Hedef"].str.lower().str.contains(q, regex=False)]

    export = df.drop(columns="_cat")
    d1, d2, _ = st.columns([1, 1, 3])
    with d1:
        st.download_button("⬇️ Tümünü İndir", export.to_csv(index=False).encode("utf-8"),
                           "yonlendirme_sonuclari.csv", "text/csv", key="redirect_dl_all",
                           use_container_width=True)
    with d2:
        st.download_button("⬇️ Filtrelenmişi İndir", view.drop(columns="_cat").to_csv(index=False).encode("utf-8"),
                           "yonlendirme_filtreli.csv", "text/csv", key="redirect_dl_view",
                           use_container_width=True, disabled=view.empty)

    if view.empty:
        st.info("Bu filtreyle eşleşen satır yok." if not (ok == total) else "Tüm yönlendirmeler doğru çalışıyor. 🎉")
        return

    st.caption(f"{len(view)} / {total} satır gösteriliyor")
    st.dataframe(
        view.drop(columns="_cat"),
        use_container_width=True,
        hide_index=True,
        column_order=["#", "Sonuç", "Kaynak Adres", "Beklenen Hedef", "Gerçek Hedef",
                      "Durum Zinciri", "Adım", "Başlangıç URL", "Yönlendirme Zinciri"],
        column_config={
            "#": st.column_config.NumberColumn("#", width="small"),
            "Başlangıç URL": st.column_config.LinkColumn("Başlangıç URL"),
            "Gerçek Hedef": st.column_config.TextColumn("Gerçek Hedef"),
            "Adım": st.column_config.NumberColumn("Adım", help="Yönlendirme adımı sayısı", width="small"),
        },
    )


# ── Main entry ───────────────────────────────────────────────
def show_redirect_checker():
    st.markdown("""
    <div style="padding:16px 0 24px 0">
        <h1 style="margin:0;font-size:2rem;">↪️ Redirect Checker</h1>
        <p style="color:#666;margin-top:8px;font-size:15px;">Yönlendirmeler alanından aldığınız 301 CSV'sini yükleyin; her yönlendirmenin doğru hedefe, tek adımda ve kalıcı olarak gidip gitmediğini kontrol edin.</p>
    </div>
    <hr style="border:none;border-top:1px solid #eee;margin-bottom:28px;">
    """, unsafe_allow_html=True)

    if st.session_state.get("redirect_ran"):
        _show_results()
        return

    # Step 1: upload
    st.markdown("##### 1 · CSV dosyasını yükleyin")
    up_col, tpl_col = st.columns([4, 1])
    with up_col:
        uploaded = st.file_uploader("Yönlendirme CSV'si", type=["csv"], key="redirect_upload",
                                    label_visibility="collapsed")
    with tpl_col:
        st.download_button("📄 Örnek CSV", _template_csv(), "ornek_yonlendirmeler.csv", "text/csv",
                           key="redirect_template", use_container_width=True,
                           help="Doğru formatta boş bir şablon indirin.")

    if not uploaded:
        st.caption("Beklenen sütunlar: **Kaynak Adres** ve **Yönlendirilecek Adres**. "
                   "Farklı adlı sütunlar da seçilebilir.")
        return

    try:
        df = _read_csv(uploaded)
    except Exception as e:
        st.error(f"CSV okunamadı: {e}")
        return

    if df.empty or len(df.columns) < 2:
        st.error("CSV en az iki sütun ve bir satır içermeli.")
        return

    cols = list(df.columns)
    c1, c2 = st.columns(2)
    with c1:
        src_col = st.selectbox("Kaynak sütunu", cols, index=cols.index(_guess_column(cols, SOURCE_HINTS, 0)),
                               key="redirect_src_col")
    with c2:
        tgt_default = _guess_column([c for c in cols if c != src_col] or cols, TARGET_HINTS, 0)
        tgt_col = st.selectbox("Hedef sütunu", cols, index=cols.index(tgt_default), key="redirect_tgt_col")

    pairs = df[[src_col, tgt_col]].dropna().astype(str)
    pairs = pairs[(pairs[src_col].str.strip() != "") & (pairs[tgt_col].str.strip() != "")]
    skipped = len(df) - len(pairs)

    info = f"**{len(pairs)}** yönlendirme bulundu."
    if skipped:
        info += f" {skipped} boş satır atlandı."
    st.info(info)
    with st.expander("Önizleme (ilk 10 satır)"):
        st.dataframe(pairs.head(10), use_container_width=True, hide_index=True)

    if src_col == tgt_col:
        st.warning("Kaynak ve hedef için farklı sütunlar seçin.")
        return

    # Step 2: domain
    st.markdown("##### 2 · Alan adını yazın")
    needs_domain = not pairs[src_col].str.strip().str.startswith("http").all()
    domain = _normalize_domain(st.text_input(
        "Alan adı", placeholder="örn. magazaniz.com", key="redirect_domain_input",
        label_visibility="collapsed",
        help="Kaynak adresler göreli yol ise (ör. /eski-urun) bu alan adının önüne eklenir.",
    ))
    if domain:
        sample = _build_source_url(pairs[src_col].iloc[0], domain)
        st.caption(f"İlk istek şöyle görünecek: `{sample}`")

    with st.expander("⚙️ Gelişmiş ayarlar"):
        a1, a2 = st.columns(2)
        with a1:
            workers = st.slider("Eşzamanlı istek", 1, 50, 20, key="redirect_workers",
                                help="Yüksek değerler daha hızlıdır ama siteyi yorabilir.")
        with a2:
            timeout = st.slider("Zaman aşımı (sn)", 3, 30, 10, key="redirect_timeout")

    # Step 3: run
    ready = bool(domain) or not needs_domain
    if not ready:
        st.caption("Kontrolü başlatmak için alan adını girin.")
    if st.button("🚀 Kontrolü Başlat", key="redirect_run", disabled=not ready):
        rows = list(zip(pairs[src_col], pairs[tgt_col]))
        results = []
        pb = st.progress(0.0, text="Yönlendirmeler kontrol ediliyor...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(_check_redirect, i, s, t, domain, timeout) for i, (s, t) in enumerate(rows)]
            for done, fut in enumerate(concurrent.futures.as_completed(futures), start=1):
                results.append(fut.result())
                pb.progress(done / len(rows), text=f"Kontrol ediliyor: {done}/{len(rows)}")
        pb.empty()

        st.session_state["redirect_df"] = pd.DataFrame(results).sort_values("#").reset_index(drop=True)
        st.session_state["redirect_domain"] = domain
        st.session_state["redirect_ran"] = True
        st.rerun()
