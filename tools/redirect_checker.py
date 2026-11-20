import streamlit as st
import requests
import pandas as pd
from urllib.parse import urlparse, unquote

from utils.http import safe_get, BlockedURLError
from utils.ui import (page_header, step, result_banner, metric_row, read_csv, to_csv_bytes,
                      filterable_table, run_parallel)

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
        resp = safe_get(start_url, allow_redirects=True, timeout=timeout, stream=True)
        resp.close()  # we only need headers / status, not the body
    except BlockedURLError:
        return {**base, "Sonuç": LABEL["error"], "Gerçek Hedef": "İç ağ adresi engellendi", "Durum Zinciri": "Engellendi",
                "Adım": None, "Yönlendirme Zinciri": "", "_cat": "error"}
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


def _guess_column(columns, hints, fallback):
    for col in columns:
        if any(h in col.lower() for h in hints):
            return col
    return columns[fallback] if len(columns) > fallback else columns[0]


def _template_csv():
    return to_csv_bytes(pd.DataFrame({
        "Kaynak Adres": ["/eski-urun", "/kategori/eski"],
        "Yönlendirilecek Adres": ["/yeni-urun", "/kategori/yeni"],
    }))


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

    result_banner(f"Kontrol tamamlandı: **{total}** yönlendirme test edildi "
                  f"(`{st.session_state.get('redirect_domain') or 'tam URL'}`).",
                  "redirect_reset", _reset_redirect)
    metric_row([("Toplam", total), ("✅ Doğru", ok), ("🟡 İyileştirilmeli", warn), ("❌ Sorunlu", total - ok - warn)])
    if total:
        st.progress(ok / total, text=f"Başarı oranı: %{ok / total * 100:.1f}")

    with st.expander("Sonuç kategorileri ne anlama geliyor?"):
        for key, label, desc in CATEGORIES:
            st.markdown(f"**{label}** ({counts.get(key, 0)}): {desc}")

    filterable_table(
        df, key="redirect", file_stem="yonlendirme_sonuclari",
        ok_labels=(LABEL["ok"],), order=[label for _, label, _ in CATEGORIES],
        search_cols=("Kaynak Adres", "Beklenen Hedef", "Gerçek Hedef"), search_placeholder="örn. /kategori",
        column_order=["#", "Sonuç", "Kaynak Adres", "Beklenen Hedef", "Gerçek Hedef",
                      "Durum Zinciri", "Adım", "Başlangıç URL", "Yönlendirme Zinciri"],
        column_config={
            "#": st.column_config.NumberColumn("#", width="small"),
            "Başlangıç URL": st.column_config.LinkColumn("Başlangıç URL"),
            "Adım": st.column_config.NumberColumn("Adım", help="Yönlendirme adımı sayısı", width="small"),
        },
    )


# ── Main entry ───────────────────────────────────────────────
def show_redirect_checker():
    page_header("↪️", "Redirect Checker",
                "Yönlendirmeler alanından aldığınız 301 CSV'sini yükleyin; her yönlendirmenin doğru hedefe, "
                "tek adımda ve kalıcı olarak gidip gitmediğini kontrol edin.")

    if st.session_state.get("redirect_ran"):
        _show_results()
        return

    # Step 1: upload
    step(1, "CSV dosyasını yükleyin")
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
        df = read_csv(uploaded)
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
    step(2, "Alan adını yazın")
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
        rows = list(enumerate(zip(pairs[src_col], pairs[tgt_col])))
        results = run_parallel(lambda r: _check_redirect(r[0], r[1][0], r[1][1], domain, timeout),
                               rows, workers=workers, text="Yönlendirmeler kontrol ediliyor")
        st.session_state["redirect_df"] = pd.DataFrame(results)
        st.session_state["redirect_domain"] = domain
        st.session_state["redirect_ran"] = True
        st.rerun()
