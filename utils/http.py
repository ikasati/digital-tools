import ipaddress
import os
import socket
import time
import zlib
from urllib.parse import urlparse

import requests

# Set ALLOW_PRIVATE_URLS=1 only for local development/testing against localhost.
_ALLOW_PRIVATE = os.environ.get("ALLOW_PRIVATE_URLS") == "1"


class BlockedURLError(requests.RequestException):
    """Raised when a URL (or a redirect hop) points at a non-public address."""


def ensure_public_url(url):
    """Reject non-http(s) schemes and hosts resolving to private/loopback/link-local/reserved IPs (SSRF guard)."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise BlockedURLError(f"Desteklenmeyen adres: {url}")
    if _ALLOW_PRIVATE:
        return
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80))
    except socket.gaierror:
        # Refuse rather than let a second (possibly different) lookup happen inside requests
        raise requests.ConnectionError(f"Alan adı çözümlenemedi: {p.hostname}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise BlockedURLError(f"Özel/iç ağ adresine izin verilmiyor: {p.hostname}")


class SafeSession(requests.Session):
    """requests.Session that validates every outgoing request, including each redirect hop."""

    def send(self, request, **kwargs):
        ensure_public_url(request.url)
        return super().send(request, **kwargs)


def safe_get(url, **kwargs):
    with SafeSession() as s:
        return s.get(url, headers=kwargs.pop("headers", HEADERS), **kwargs)


MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # sitemap spec limit; plenty for product feeds too


def is_http_url(url):
    """True only for http(s) URLs - keeps javascript:/data: values out of clickable link columns."""
    return urlparse(str(url).strip()).scheme in ("http", "https")


def fetch_bytes(url, timeout=30, max_bytes=MAX_DOWNLOAD_BYTES):
    """Download a file with a hard size cap, transparently gunzipping .gz bodies (also capped)."""
    with safe_get(url, timeout=timeout, stream=True) as r:
        r.raise_for_status()
        declared = r.headers.get("Content-Length", "")
        if declared.isdigit() and int(declared) > max_bytes:
            raise ValueError(f"Dosya çok büyük (>{max_bytes // 1024 // 1024} MB): {url}")
        # iter_content yields *decoded* bytes, so this cap also bounds Content-Encoding: gzip/br bodies.
        # urllib3>=2.6 (pinned in requirements.txt) keeps each decoded chunk bounded too.
        buf = bytearray()
        for chunk in r.iter_content(64 * 1024):
            buf += chunk
            if len(buf) > max_bytes:
                raise ValueError(f"Dosya çok büyük (>{max_bytes // 1024 // 1024} MB): {url}")
    data = bytes(buf)
    if data[:2] == b"\x1f\x8b":  # gzip served without Content-Encoding (e.g. sitemap.xml.gz)
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        out = d.decompress(data, max_bytes)
        if d.unconsumed_tail:
            raise ValueError(f"Açılmış dosya {max_bytes // 1024 // 1024} MB sınırını aşıyor: {url}")
        data = out
    return data


def safe_head(url, **kwargs):
    with SafeSession() as s:
        return s.head(url, headers=kwargs.pop("headers", HEADERS), **kwargs)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

HTTP_STATUS_MESSAGES = {
    200: "OK", 301: "Kalıcı Yönlendirme", 302: "Geçici Yönlendirme", 307: "Geçici Yönlendirme",
    308: "Kalıcı Yönlendirme", 400: "Hatalı İstek", 401: "Yetkisiz", 403: "Yasak",
    404: "Bulunamadı", 410: "Kaldırıldı", 429: "Çok Fazla İstek", 500: "Sunucu Hatası",
    502: "Geçersiz Ağ Geçidi", 503: "Hizmet Kullanılamıyor", 504: "Ağ Geçidi Zaman Aşımı",
}

# Groups used for metrics; labels within a group can vary (e.g. "❌ 404 Bulunamadı")
GROUP_OK, GROUP_REDIRECT, GROUP_BROKEN, GROUP_ERROR = "ok", "redirect", "broken", "error"
OK_LABEL = "✅ 200 OK"
REDIRECT_LABEL = "🟡 Yönlendiriliyor"
ERROR_LABEL = "⚠️ İstek başarısız"


def status_text(code):
    return f"{code} {HTTP_STATUS_MESSAGES.get(code, '')}".strip()


def _request(url, timeout):
    """HEAD first (cheap); confirm any non-2xx/3xx with GET since many servers mishandle HEAD."""
    r = safe_head(url, allow_redirects=True, timeout=timeout)
    if r.status_code >= 400:
        r = safe_get(url, allow_redirects=True, timeout=timeout, stream=True)
        r.close()
    return r


def check_url(url, timeout=10, retries=1):
    """Check a URL and return a result row with first/final status and a human label."""
    for attempt in range(retries + 1):
        try:
            r = _request(url, timeout)
            break
        except BlockedURLError:
            return _row(url, "Engellendi", "Engellendi", "", "Engellendi", "🚫 Engellendi (iç ağ)", GROUP_ERROR)
        except requests.TooManyRedirects:
            return _row(url, "Döngü", "Döngü", "", "Döngü", "❌ Yönlendirme döngüsü", GROUP_BROKEN)
        except Exception as e:
            if attempt < retries:
                time.sleep(1)
                continue
            return _row(url, "Hata", "Hata", "", type(e).__name__, ERROR_LABEL, GROUP_ERROR)

    codes = [h.status_code for h in r.history] + [r.status_code]
    final = r.status_code
    redirected = bool(r.history)

    if final >= 400:
        label, group = f"❌ {status_text(final)}", GROUP_BROKEN
    elif redirected:
        label, group = REDIRECT_LABEL, GROUP_REDIRECT
    elif final == 200:
        label, group = OK_LABEL, GROUP_OK
    else:
        label, group = f"✅ {status_text(final)}", GROUP_OK

    return _row(url, codes[0], final, r.url if redirected else "", " → ".join(map(str, codes)), label, group)


def _row(url, first, final, final_url, chain, label, group):
    return {
        "Sonuç": label,
        "URL": url,
        # str() keeps the column one type ("200" / "Hata"); mixed int+str breaks Arrow serialization
        "Durum": str(first),
        "Son Durum": str(final),
        "Son URL": final_url,
        "Durum Zinciri": chain,
        "_group": group,
    }
