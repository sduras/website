# api/scrap/software.py

import datetime
import logging
import re
from typing import Dict, List, cast
from urllib.parse import urljoin

from aiohttp import ClientSession
from api.scrap.utils import clean_text, fetch_with_retry
from bs4 import BeautifulSoup
from bs4.element import Tag

logging.debug(
    "software.py loaded, fetch_with_retry in globals? %s",
    "fetch_with_retry" in globals(),
)

__all__ = [
    "fetch_python_version",
    "fetch_cmus_stable_version",
    "fetch_vim_version",
    "fetch_debian_stable_version",
    "fetch_gpg_stable_version",
    "fetch_aShell_stable_version",
    "fetch_pico_openpgp_stable_version",
]


async def fetch_cmus_stable_version(
    session: ClientSession, url: str
) -> List[Dict[str, str]]:
    try:
        html = await fetch_with_retry(session, url)
        soup = BeautifulSoup(html, "html.parser")

        li = soup.select_one("#content > div:nth-child(8) > ul > li:nth-child(1)")
        if not li:
            logging.warning("Could not find cmus release list item.")
            return []

        full_text = clean_text(str(li.get_text()))

        version_match = re.search(r"(\d+\.\d+(?:\.\d+)*)", full_text)
        version = version_match.group(1) if version_match else "Unknown"

        release_notes_link = li.find("a", href=True, string="release notes")
        release_url = release_notes_link.get("href") if release_notes_link else url

        sentences = re.split(r"(?<=\.)\s+", full_text)
        description = sentences[0] if sentences else full_text

        fetched_at = datetime.datetime.utcnow().isoformat() + "Z"

        return [
            {
                "title": "cmus",
                "latest_version": version,
                "description": description,
                "url": release_url,
                "fetched_at": fetched_at,
            }
        ]

    except Exception as e:
        logging.error(f"Failed to scrape cmus page: {e}", exc_info=True)
        return []


async def fetch_python_version(
    session: ClientSession, url: str
) -> List[Dict[str, str]]:
    try:
        html = await fetch_with_retry(session, url)
        soup = BeautifulSoup(html, "html.parser")

        release_li = soup.select_one(
            "#content > div > section > article > ul > li a[href*='/downloads/release/python']"
        )
        if not release_li:
            logging.warning("No release link found in Python source page.")
            return []

        title_text = clean_text(str(release_li.get_text()))
        release_url = urljoin(url, str(release_li.get("href", "")))

        version_match = re.search(r"(\d+\.\d+(?:\.\d+)*)", title_text)
        version = version_match.group(1) if version_match else "Unknown"

        fetched_at = datetime.datetime.utcnow().isoformat() + "Z"

        return [
            {
                "title": "Python",
                "latest_version": version,
                "description": title_text,
                "url": release_url,
                "fetched_at": fetched_at,
            }
        ]

    except Exception as e:
        logging.error(f"Failed to scrape Python page: {e}", exc_info=True)
        return []


async def fetch_vim_version(session: ClientSession, url: str) -> List[Dict[str, str]]:
    try:
        html = await fetch_with_retry(session, url)
        soup = BeautifulSoup(html, "html.parser")

        version_heading = next(
            (h for h in soup.find_all("h1") if "version" in h.text.lower()), None
        )
        if not version_heading:
            logging.warning("Could not find <h1> with 'Version'")
            return []

        text_node = version_heading.find_next_sibling(string=True)
        if not text_node:
            logging.warning("No version description found after heading")
            return []

        version_text = clean_text(str(text_node))

        version_match = re.search(r"Vim\s+(\d+(?:\.\d+)*)", version_text)
        version = version_match.group(1) if version_match else "Unknown"

        sentences = re.split(r"(?<=\.)\s+", version_text)
        description = sentences[0] if sentences else version_text

        return [
            {
                "title": "Vim",
                "latest_version": version,
                "description": description,
                "url": url,
            }
        ]
    except Exception as e:
        logging.error(f"Failed to scrape Vim page: {e}")
        return []


async def fetch_debian_stable_version(
    session: ClientSession, url: str
) -> List[Dict[str, str]]:
    try:
        html = await fetch_with_retry(session, url)
        soup = BeautifulSoup(html, "html.parser")

        target_p = soup.select_one(
            "#content > dl > dd:nth-of-type(1) > p:nth-of-type(3)"
        )
        if not target_p:
            logging.warning("Could not find Debian stable release paragraph.")
            return []

        raw_text = clean_text(str(target_p.get_text()))

        version_match = re.search(r"version\s+(\d+(?:\.\d+)?)", raw_text, re.IGNORECASE)
        version = version_match.group(1) if version_match else "Unknown"

        sentences = re.split(r"(?<=\.)\s+", raw_text)
        description = sentences[0] if sentences else raw_text

        fetched_at = datetime.datetime.utcnow().isoformat() + "Z"

        return [
            {
                "title": "Debian",
                "latest_version": version,
                "description": description,
                "url": url,
                "fetched_at": fetched_at,
            }
        ]
    except Exception as e:
        logging.error(f"Failed to scrape Debian page: {e}", exc_info=True)
        return []


async def fetch_gpg_stable_version(
    session: ClientSession, url: str
) -> List[Dict[str, str]]:
    try:
        html = await fetch_with_retry(session, url)
        soup = BeautifulSoup(html, "html.parser")
        target_p = soup.select_one("#text-1 > p:nth-of-type(3)")

        if not target_p:
            logging.warning("No matching paragraph found on GnuPG page.")
            return []

        raw_text = clean_text(str(target_p.get_text()))

        version_match = re.search(
            r"version(?:\s+\w+)*\s+(\d+(?:\.\d+)+)", raw_text, re.IGNORECASE
        )
        version = version_match.group(1) if version_match else "Unknown"

        sentences = re.split(r"(?<=\.)\s+", raw_text)
        description = sentences[0] if sentences else raw_text

        fetched_at = datetime.datetime.utcnow().isoformat() + "Z"

        return [
            {
                "title": "GnuPG",
                "latest_version": version,
                "description": description,
                "url": url,
                "fetched_at": fetched_at,
            }
        ]
    except Exception as e:
        logging.error(f"Failed to scrape GnuPG page: {e}", exc_info=True)
        return []


async def fetch_aShell_stable_version(
    session: ClientSession, url: str
) -> List[Dict[str, str]]:
    try:
        html = await fetch_with_retry(session, url)
        soup = BeautifulSoup(html, "html.parser")

        version_heading = soup.select_one("article h1[id^='version']")
        if not version_heading:
            logging.warning("No version heading found for aShell")
            return []

        version_text = version_heading.get_text(strip=True)
        version_match = re.search(r"Version\s*([\d\.]+)", version_text, re.IGNORECASE)
        version = version_match.group(1) if version_match else "Unknown"

        whats_new, improvements = [], []
        current = version_heading.find_next_sibling()
        while current and current.name != "h1":
            if current.name == "h4":
                ul = current.find_next_sibling("ul")
                if ul:
                    items = [li.get_text(strip=True) for li in ul.select("li")]
                    if current.get("id") == "whats-new":
                        whats_new = items
                    elif current.get("id") == "improvements":
                        improvements = items
            current = current.find_next_sibling()

        if whats_new:
            raw_description = whats_new[0]
        elif improvements:
            raw_description = improvements[0]
        else:
            raw_description = version_text

        description = re.split(r"(?<=[.!?])\s", raw_description, maxsplit=1)[0]

        parts = [version_text]
        if whats_new:
            parts.append("\nWhat’s New:")
            parts.extend([f"• {item}" for item in whats_new])
        if improvements:
            parts.append("\nImprovements:")
            parts.extend([f"• {item}" for item in improvements])
        full_text = "\n".join(parts)

        if len(full_text) > 300:
            full_text = full_text[:300].rstrip() + "..."

        fetched_at = datetime.datetime.utcnow().isoformat() + "Z"

        return [
            {
                "title": "aShell",
                "latest_version": version,
                "description": description,
                "text": full_text,
                "url": url,
                "fetched_at": fetched_at,
            }
        ]

    except Exception as e:
        logging.error(f"Failed to scrape a-Shell page: {e}", exc_info=True)
        return []


async def fetch_pico_openpgp_stable_version(
    session: ClientSession, url: str
) -> List[Dict[str, str]]:
    try:
        html = await fetch_with_retry(session, url)
        soup = BeautifulSoup(html, "html.parser")

        latest_label = soup.select_one("a.Link span.Label--success")
        if not latest_label or not latest_label.parent:
            logging.warning("Could not find 'Latest' release label")
            return []

        href = latest_label.parent.get("href")
        if not href:
            return []

        latest_url = urljoin(url, href)
        release_html = await fetch_with_retry(session, latest_url)
        release_soup = BeautifulSoup(release_html, "html.parser")

        version = "Unknown"
        url_match = re.search(r"/tag/v?(\d+\.\d+(?:\.\d+)?)", latest_url)
        if url_match:
            version = url_match.group(1)
        else:
            body_text = release_soup.get_text(" ", strip=True)
            body_match = re.search(
                r"Version\s+(\d+\.\d+(?:\.\d+)?)", body_text, re.IGNORECASE
            )
            if body_match:
                version = body_match.group(1)

        description = version or "Release available"

        markdown_body = release_soup.select_one("div.markdown-body")
        if markdown_body:
            for heading in markdown_body.find_all("h2"):
                if "new" in heading.get_text(strip=True).lower():
                    ul = heading.find_next_sibling("ul")
                    if ul:
                        first_item = ul.select_one("li")
                        if first_item:
                            description = clean_text(str(first_item.get_text()))
                    break

        fetched_at = datetime.datetime.utcnow().isoformat() + "Z"

        return [
            {
                "title": "pico-openpgp",
                "latest_version": version,
                "description": description,
                "url": latest_url,
                "fetched_at": fetched_at,
            }
        ]

    except Exception as e:
        logging.error(f"Failed to scrape pico-openpgp page: {e}", exc_info=True)
        return []
