import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from src.utils.log import Log


GITHUB_PROXY_PREFIXES = [
    "https://gh.llkk.cc",
    "https://ghproxy.cn",
    "https://ghproxy.net",
    "https://gitproxy.click",
]


class DownloadHelper:
    @staticmethod
    def _is_github_url(url: str) -> bool:
        try:
            host = (urlparse(str(url or "")).netloc or "").lower()
            return "github.com" in host or "githubusercontent.com" in host
        except Exception:
            return False

    @staticmethod
    def can_access_url(url: str, timeout: int = 3) -> bool:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                code = int(getattr(resp, "status", 200) or 200)
                return 200 <= code < 400
        except Exception:
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    code = int(getattr(resp, "status", 200) or 200)
                    return 200 <= code < 400
            except Exception:
                return False

    @staticmethod
    def supports_github(timeout: int = 3) -> bool:
        return DownloadHelper.can_access_url("https://github.com", timeout=timeout)

    @staticmethod
    def build_candidate_urls(url: str) -> list[str]:
        raw_url = str(url or "").strip()
        if not raw_url:
            return []

        candidates = [raw_url]
        if DownloadHelper._is_github_url(raw_url) and not DownloadHelper.supports_github(timeout=2):
            candidates = [f"{prefix}/{raw_url}" for prefix in GITHUB_PROXY_PREFIXES] + [raw_url]
        return candidates

    @staticmethod
    def download_file(url: str, target: Path, timeout: int = 30, progress_callback=None) -> str:
        candidates = DownloadHelper.build_candidate_urls(url)
        if not candidates:
            raise Exception("download url is empty")

        target.parent.mkdir(parents=True, exist_ok=True)
        last_error = None
        for candidate in candidates:
            try:
                with urllib.request.urlopen(candidate, timeout=timeout) as resp, open(target, "wb") as f:
                    total = 0
                    try:
                        total = int(resp.headers.get("Content-Length", "0") or 0)
                    except Exception:
                        total = 0

                    downloaded = 0
                    chunk_size = 256 * 1024
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if callable(progress_callback):
                            if total > 0:
                                percent = int(downloaded * 100 / total)
                                progress_callback(percent)
                            else:
                                progress_callback(50)

                Log.info(f"Download success via: {candidate}")
                return candidate
            except Exception as e:
                last_error = e
                Log.info(f"Download failed via: {candidate}, error: {e}")
                continue

        raise Exception(str(last_error) if last_error else "download failed")
