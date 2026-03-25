#!/usr/bin/env python
import argparse
import mimetypes
import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download all images from a web page.")
    parser.add_argument("url", help="Target page URL")
    parser.add_argument(
        "-o",
        "--output",
        default="images",
        help="Directory to save images (default: images)",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Use a real browser for JavaScript-heavy pages",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=5,
        help="Seconds to wait for browser-rendered content (default: 5)",
    )
    return parser.parse_args()


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
        guessed = mimetypes.guess_extension(ct)
        if guessed:
            return guessed
    return ".jpg"


def extract_img_urls(page_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    img_urls: list[str] = []
    seen: set[str] = set()
    candidate_attrs = (
        "src",
        "data-src",
        "data-original",
        "data-lazy-src",
        "data-ks-lazyload",
        "data-lazyload-src",
    )
    for img in soup.find_all("img"):
        raw_urls: list[str] = []

        for attr in candidate_attrs:
            value = img.get(attr)
            if value:
                raw_urls.append(value.strip())

        srcset = img.get("srcset")
        if srcset:
            for item in srcset.split(","):
                url_part = item.strip().split(" ")[0]
                if url_part:
                    raw_urls.append(url_part)

        for raw_url in raw_urls:
            if not raw_url or raw_url.startswith("data:"):
                continue
            # Handle protocol-relative URLs like //example.com/a.jpg
            if raw_url.startswith("//"):
                raw_url = "https:" + raw_url
            full = urljoin(page_url, raw_url)
            if full not in seen:
                img_urls.append(full)
                seen.add(full)
    return img_urls


def download_image(session: requests.Session, url: str, dest: Path) -> tuple[bool, str]:
    try:
        with session.get(url, stream=True, timeout=15) as r:
            r.raise_for_status()
            content_type = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if content_type and not content_type.startswith("image/"):
                return False, f"Skipped non-image content: {content_type}"
            ext = guess_ext(url, r.headers.get("Content-Type"))
            dest = dest.with_suffix(ext)
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True, f"Saved to {dest.name}"
    except requests.RequestException as exc:
        return False, str(exc)


def fetch_html_with_browser(page_url: str, wait_seconds: int) -> str:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    try:
        driver.get(page_url)
        WebDriverWait(driver, wait_seconds).until(
            EC.presence_of_element_located((By.TAG_NAME, "img"))
        )
        # Scroll once to trigger lazy-loaded images.
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        return driver.page_source
    finally:
        driver.quit()


def main() -> int:
    args = parse_args()
    page_url = args.url
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ImgDownloader/1.0)",
    }

    try:
        with requests.Session() as session:
            session.headers.update(headers)
            if args.browser:
                html = fetch_html_with_browser(page_url, args.wait)
            else:
                resp = session.get(page_url, timeout=15)
                resp.raise_for_status()
                html = resp.text

            img_urls = extract_img_urls(page_url, html)
            if not img_urls:
                if args.browser:
                    print("No images found, even after browser rendering.")
                else:
                    print("No images found. Try again with --browser for dynamic pages.")
                return 0

            success = 0
            total = len(img_urls)
            for i, url in enumerate(img_urls, start=1):
                filename = f"img_{i:03d}"
                dest = output_dir / filename
                ok, message = download_image(session, url, dest)
                if ok:
                    success += 1
                    print(f"[{i}/{total}] OK   {url} -> {message}")
                else:
                    print(f"[{i}/{total}] FAIL {url} -> {message}")

            print(f"Done. Downloaded {success}/{total} images to {output_dir}")
    except requests.RequestException as exc:
        print(f"Failed to load page: {exc}")
        return 1
    except Exception as exc:
        print(f"Failed in browser mode: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
