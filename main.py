#!/usr/bin/env python
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def guess_ext(url: str, content_type: str | None) -> str:
    # Prefer extension from URL path
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext and re.match(r"^\.[a-z0-9]+$", ext):
        return ext

    # Fallback to content-type
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        mapping = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
            "image/svg+xml": ".svg",
            "image/x-icon": ".ico",
        }
        if ct in mapping:
            return mapping[ct]
    return ".jpg"


def extract_img_urls(page_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    img_urls: list[str] = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        if src.startswith("data:"):
            # Skip inline data URIs
            continue
        # Handle protocol-relative URLs like //example.com/a.jpg
        if src.startswith("//"):
            src = "https:" + src
        full = urljoin(page_url, src)
        img_urls.append(full)
    return img_urls


def download_image(session: requests.Session, url: str, dest: Path) -> bool:
    try:
        with session.get(url, stream=True, timeout=15) as r:
            r.raise_for_status()
            ext = guess_ext(url, r.headers.get("Content-Type"))
            dest = dest.with_suffix(ext)
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python main.py <URL> [output_dir]")
        return 1

    page_url = sys.argv[1]
    output_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else Path("images")
    output_dir.mkdir(parents=True, exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ImgDownloader/1.0)",
    }

    with requests.Session() as session:
        session.headers.update(headers)
        resp = session.get(page_url, timeout=15)
        resp.raise_for_status()

        img_urls = extract_img_urls(page_url, resp.text)
        if not img_urls:
            print("No images found.")
            return 0

        success = 0
        total = len(img_urls)
        for i, url in enumerate(img_urls, start=1):
            filename = f"img_{i:03d}"
            dest = output_dir / filename
            ok = download_image(session, url, dest)
            if ok:
                success += 1
                print(f"[{i}/{total}] OK   {url}")
            else:
                print(f"[{i}/{total}] FAIL {url}")

        print(f"Done. Downloaded {success}/{total} images to {output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
