# api/scrap/software.py


import datetime
import logging
import re
from typing import Dict, List
from urllib.parse import urljoin

from aiohttp import ClientSession
from api.scrap.utils import (clean_text, extract_first_sentence,
                             extract_version, fetch_with_retry, get_html_soup,
                             utc_now_iso)
from bs4 import BeautifulSoup

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
    soup = await get_html_soup(session, url)
    if not soup:
        return []

    li = soup.select_one("#content > div:nth-child(8) > ul > li:nth-child(1)")
    if not li:
        logging.warning("Could not find cmus release list item.")
        return []

    full_text = clean_text(li.get_text())
    version = extract_version(full_text, r"(\d+\.\d+(?:\.\d+)*)")

    release_notes_link = li.find("a", href=True, string="release notes")
    release_url = release_notes_link["href"] if release_notes_link else url

    description = extract_first_sentence(full_text)

    return [
        {
            "title": "cmus",
            "latest_version": version,
            "description": description,
            "url": release_url,
            "fetched_at": utc_now_iso(),
        }
    ]


async def fetch_python_version(
    session: ClientSession, url: str
) -> List[Dict[str, str]]:
    soup = await get_html_soup(session, url)
    if not soup:
        return []

    release_li = soup.select_one(
        "#content > div > section > article > ul > li a[href*='/downloads/release/python']"
    )
    if not release_li:
        logging.warning("No release link found in Python source page.")
        return []

    title_text = clean_text(release_li.get_text())
    release_url = urljoin(url, release_li["href"])
    version = extract_version(title_text, r"(\d+\.\d+(?:\.\d+)*)")

    description = title_text

    return [
        {
            "title": "Python",
            "latest_version": version,
            "description": description,
            "url": release_url,
            "fetched_at": utc_now_iso(),
        }
    ]


async def fetch_vim_version(session: ClientSession, url: str) -> List[Dict[str, str]]:
    soup = await get_html_soup(session, url)
    if not soup:
        return []

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

    version_text = clean_text(text_node)
    version = extract_version(version_text, r"Vim\s+(\d+(?:\.\d+)*)")
    description = extract_first_sentence(version_text)

    return [
        {
            "title": "Vim",
            "latest_version": version,
            "description": description,
            "url": url,
            "fetched_at": utc_now_iso(),
        }
    ]


async def fetch_debian_stable_version(
    session: ClientSession, url: str
) -> List[Dict[str, str]]:
    soup = await get_html_soup(session, url)
    if not soup:
        return []

    target_p = soup.select_one("#content > dl > dd:nth-of-type(1) > p:nth-of-type(3)")
    if not target_p:
        logging.warning("Could not find Debian stable release paragraph.")
        return []

    raw_text = clean_text(target_p.get_text())
    version = extract_version(raw_text, r"version\s+(\d+(?:\.\d+)?)")
    description = extract_first_sentence(raw_text)

    return [
        {
            "title": "Debian",
            "latest_version": version,
            "description": description,
            "url": url,
            "fetched_at": utc_now_iso(),
        }
    ]


async def fetch_gpg_stable_version(
    session: ClientSession, url: str
) -> List[Dict[str, str]]:
    soup = await get_html_soup(session, url)
    if not soup:
        return []

    target_p = soup.select_one("#text-1 > p:nth-of-type(3)")
    if not target_p:
        logging.warning("No matching paragraph found on GnuPG page.")
        return []

    raw_text = clean_text(target_p.get_text())
    version = extract_version(raw_text, r"version(?:\s+\w+)*\s+(\d+(?:\.\d+)+)")
    description = extract_first_sentence(raw_text)

    return [
        {
            "title": "GnuPG",
            "latest_version": version,
            "description": description,
            "url": url,
            "fetched_at": utc_now_iso(),
        }
    ]


async def fetch_aShell_stable_version(
    session: ClientSession, url: str
) -> List[Dict[str, str]]:
    soup = await get_html_soup(session, url)
    if not soup:
        return []

    version_heading = soup.select_one("article h1[id^='version']")
    if not version_heading:
        logging.warning("No version heading found for aShell")
        return []

    version_text = version_heading.get_text(strip=True)
    version = extract_version(version_text, r"Version\s*([\d\.]+)")

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

    description = extract_first_sentence(raw_description)

    parts = [version_text]
    if whats_new:
        parts.append("\nWhat’s New:")
        parts.extend([f"• {item}" for item in whats_new])
    if improvements:
        parts.append("\nImprovements:")
        parts.extend([f"• {item}" for item in improvements])
    full_text = "\n".join(parts)

    max_len = 300
    if len(full_text) > max_len:
        full_text = full_text[:max_len].rstrip() + "..."

    return [
        {
            "title": "aShell",
            "latest_version": version,
            "description": description,
            "text": full_text,
            "url": url,
            "fetched_at": utc_now_iso(),
        }
    ]


async def fetch_pico_openpgp_stable_version(
    session: ClientSession, url: str
) -> List[Dict[str, str]]:
    soup = await get_html_soup(session, url)
    if not soup:
        return []

    latest_label = soup.select_one("a.Link span.Label--success")
    if not latest_label:
        logging.warning("Could not find 'Latest' release label")
        return []

    latest_url = urljoin(url, latest_label.parent["href"])

    release_soup = await get_html_soup(session, latest_url)
    if not release_soup:
        return []

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
                        description = clean_text(first_item.get_text())
                break

    return [
        {
            "title": "pico-openpgp",
            "latest_version": version,
            "description": description,
            "url": latest_url,
            "fetched_at": utc_now_iso(),
        }
    ]
