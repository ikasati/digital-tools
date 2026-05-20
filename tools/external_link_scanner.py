import streamlit as st
import requests
import re
from urllib.parse import urljoin, urlparse
import concurrent.futures
import threading
import pandas as pd

URL_REGEX = re.compile(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s"\'<>]*)?')

def get_domain(url):
    return urlparse(url).netloc.lower().replace('www.', '')

def scan_website(start_url, max_pages=100, max_threads=30, ignore_cdn=False, ignore_schema=False, progress_callback=None):
    start_domain = get_domain(start_url)
    visited = set()
    to_visit = [start_url]
    external_links = {}
    
    lock = threading.Lock()
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    })

    def fetch_url(url):
        try:
            resp = session.get(url, timeout=10)
            if 'text/html' not in resp.headers.get('Content-Type', ''):
                return url, [], []
            
            html = resp.text
            found_urls = URL_REGEX.findall(html)
            
            hrefs = re.findall(r'href=[\'"]?([^\'" >]+)', html)
            for href in hrefs:
                if href.startswith('http'):
                    found_urls.append(href)
                elif not href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                    found_urls.append(urljoin(url, href))
            
            internal = []
            external = []
            for found_url in set(found_urls):
                parsed = urlparse(found_url)
                found_domain = parsed.netloc.lower().replace('www.', '')
                clean_url = found_url.split('#')[0].rstrip('/')
                
                if not found_domain:
                    continue
                    
                if ignore_schema and any(d in found_domain for d in ['schema.org', 'w3.org', 'purl.org', 'ogp.me', 'xmlns.com', 'w3.com']):
                    continue
                    
                if ignore_cdn:
                    is_cdn = (
                        found_domain.startswith('cdn.') or 
                        '.cdn.' in found_domain or 
                        '-cdn.' in found_domain or
                        any(d in found_domain for d in ['cloudfront.net', 'akamaized.net', 'fastly.net', 'cloudflare.com', 'bootstrapcdn'])
                    )
                    if is_cdn:
                        continue
                
                if found_domain == start_domain:
                    internal.append(clean_url)
                else:
                    external.append(clean_url)
                    
            return url, internal, external
        except Exception:
            return url, [], []

    scanned_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        while to_visit and len(visited) < max_pages:
            remaining_slots = max_pages - len(visited)
            batch_size = min(max_threads, len(to_visit), remaining_slots)
            
            if batch_size <= 0:
                break
                
            batch = to_visit[:batch_size]
            to_visit = to_visit[batch_size:]
            
            with lock:
                for url in batch:
                    visited.add(url)
            
            futures = [executor.submit(fetch_url, url) for url in batch]
            for future in concurrent.futures.as_completed(futures):
                url, internal, external = future.result()
                
                with lock:
                    scanned_count += 1
                    if progress_callback:
                        progress_callback(scanned_count, len(visited) + len(to_visit))
                        
                    for ext in external:
                        if ext not in external_links:
                            external_links[ext] = set()
                        external_links[ext].add(url)
                    
                    for inc in internal:
                        if inc not in visited and inc not in to_visit:
                            to_visit.append(inc)

    results = []
    for ext, sources in external_links.items():
        results.append({
            "Dış Link": ext,
            "Bulunduğu Sayfa": "\n".join(list(sources)),
            "Sayfa Sayısı": len(sources)
        })
        
    return {
        "scanned_pages": len(visited), 
        "total_external_links": len(results),
        "external_links": sorted(results, key=lambda x: x['Sayfa Sayısı'], reverse=True)
    }

def _reset_scanner():
    for k in ["scanner_results", "scanner_ran", "scanner_stats"]:
        st.session_state.pop(k, None)

def show_external_link_scanner():
    st.markdown("""
    <div style="padding:16px 0 24px 0">
        <h1 style="margin:0;font-size:2rem;">🔍 External Link Scanner</h1>
        <p style="color:#666;margin-top:8px;font-size:15px;">Googlebot taklidi yapar ve sitenizdeki JS/HTML kaynağında gizli kalan tüm dış linkleri çıkartır.</p>
    </div>
    <hr style="border:none;border-top:1px solid #eee;margin-bottom:28px;">
    """, unsafe_allow_html=True)

    if st.session_state.get("scanner_ran"):
        df = st.session_state["scanner_results"]
        stats = st.session_state["scanner_stats"]

        col_title, col_btn = st.columns([4, 1])
        with col_title:
            st.success(f"✅ Tarama tamamlandı — **{stats['scanned_pages']}** sayfa tarandı, **{stats['total_external_links']}** dış link bulundu.")
        with col_btn:
            if st.button("🔄 Yeni Tarama", key="scanner_reset"):
                _reset_scanner()
                st.rerun()

        if len(df) > 0:
            col_dl, _ = st.columns([1, 4])
            with col_dl:
                st.download_button(
                    "⬇️ CSV İndir",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name="dis_link_raporu.csv",
                    mime="text/csv",
                    key="scanner_csv_dl"
                )
            
            # Show a slightly different view: explode the pages so it's easier to read, or keep it aggregated.
            # Using st.dataframe with adjusted column config for newlines
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Dış Link": st.column_config.LinkColumn("Dış Link"),
                    "Bulunduğu Sayfa": st.column_config.TextColumn("Bulunduğu Sayfa(lar)"),
                }
            )
        else:
            st.info("Hiç dış link bulunamadı. Çok temiz!")
        return

    # Input Form
    url_input = st.text_input("Taranacak URL", placeholder="https://example.com", key="scanner_url")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        max_threads = st.number_input("Eşzamanlı İstek (Thread)", min_value=1, max_value=200, value=50, step=10, key="scanner_threads", help="Aynı anda taranacak sayfa sayısı. Yüksek değerler siteyi yorabilir.")
    with col2:
        ignore_cdn = st.checkbox("CDN Hariç", value=True, help="CDN linklerini dahil etme")
        ignore_schema = st.checkbox("Schema/W3C Hariç", value=True, help="Schema.org, W3C vs. dahil etme")
        
    if st.button("🚀 Taramayı Başlat", type="primary", key="scanner_run"):
        if not url_input:
            st.error("Lütfen geçerli bir URL girin.")
            return
            
        raw_url = url_input.strip()
        if not raw_url.startswith("http"):
            raw_url = "https://" + raw_url
            
        progress_info = st.empty()
        
        def update_progress(scanned, discovered):
            progress_info.info(f"⏳ Taranıyor... Tamamlanan: **{scanned}** / Keşfedilen: **{discovered}**")
            
        with st.spinner("Site taranıyor... Bu işlem sayfa sayısına bağlı olarak uzun sürebilir."):
            results = scan_website(
                raw_url, 
                max_pages=100000, 
                max_threads=max_threads,
                ignore_cdn=ignore_cdn, 
                ignore_schema=ignore_schema,
                progress_callback=update_progress
            )
            
        progress_info.empty()
        
        df = pd.DataFrame(results['external_links'])
        st.session_state["scanner_results"] = df
        st.session_state["scanner_stats"] = {
            "scanned_pages": results["scanned_pages"],
            "total_external_links": results["total_external_links"]
        }
        st.session_state["scanner_ran"] = True
        st.rerun()
