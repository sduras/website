# api/scrap/scraping.py

import asyncio
import json
import os
import random
import datetime
from typing import Dict, List
from urllib.parse import urljoin

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from bs4 import BeautifulSoup

from api.scrap import software

from api.scrap.utils import fetch_with_retry, clean_text


import logging
logging.debug("scraping.py loaded")


HEADERS = {
    "Accept": "text/html",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "uk-UA,uk;en;q=0.5",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
}

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_MIN = 1
RETRY_BACKOFF_MAX = 3
MAX_HEADLINES = 5


SCRAPER_REGISTRY = {
    "Python": software.fetch_python_version,
    "cmus": software.fetch_cmus_stable_version,
    "Vim": software.fetch_vim_version,
    "Debian": software.fetch_debian_stable_version,
    "GnuPG": software.fetch_gpg_stable_version,
    "aShell": software.fetch_aShell_stable_version,
    "picoopenpgp": software.fetch_pico_openpgp_stable_version,
}

def load_config(config_path: str = None) -> List[Dict]:
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f).get("sources", [])
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return []


async def fetch_by_selector(session, url: str, css_selector: str) -> List[Dict[str, str]]:
    try:
        html = await fetch_with_retry(session, url)
        soup = BeautifulSoup(html, "html.parser")
        elements = soup.select(css_selector)[:MAX_HEADLINES]
        return [
            {"text": clean_text(el.text), "url": urljoin(url, el.get("href", "#"))}
            for el in elements if el.text.strip()
        ]
    except Exception as e:
        logging.error(f"Selector scraping failed for {url}: {e}")
        return []

async def get_updates() -> dict:
    sources = load_config()
    if not sources:
        logging.error("No sources found. Exiting.")
        return {}

    async with ClientSession(connector=TCPConnector(ssl=False), headers=HEADERS) as session:
        tasks = {}
        source_categories = {}

        for source in sources:
            name = source.get("name")
            url = source.get("url")
            selector = source.get("css_selector")
            mode = source.get("mode", "default")
            category = source.get("category", "uncategorized")

            if not name or not url:
                logging.warning(f"Skipping malformed source entry: {source}")
                continue

            source_categories[name] = category

            if mode == "custom":
                task_func = SCRAPER_REGISTRY.get(name)
                if task_func:
                    tasks[name] = task_func(session, url)
                else:
                    logging.warning(f"No custom scraper registered for '{name}'")
            elif selector:
                tasks[name] = fetch_by_selector(session, url, selector)
            else:
                logging.warning(f"Skipping '{name}' — no CSS selector or valid mode provided.")

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        categorized_results = {}
        for name, result in zip(tasks.keys(), results):
            category = source_categories.get(name, "uncategorized")

            if category not in categorized_results:
                categorized_results[category] = {}

            if isinstance(result, Exception):
                logging.error(f"Scraping for '{name}' failed: {result}")
                categorized_results[category][name] = []
            else:
                timestamp = datetime.datetime.utcnow().isoformat() + "Z"
                items_with_timestamp = []
                for item in result:
                    new_item = item.copy()
                    new_item["fetched_at"] = timestamp
                    items_with_timestamp.append(new_item)

                categorized_results[category][name] = items_with_timestamp

        metadata = {
            "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
            "total_sources": len(tasks),
            "categories": list(categorized_results.keys()),
        }

    return {"metadata": metadata, "updates": categorized_results}

def format_output(all_news: Dict[str, List[Dict[str, str]]]) -> str:
    parts = ["Updates\n"]
    for name, items in all_news.items():
        parts.append(f"**{name}**")
        for item in items:
            parts.append(f"{item['text']}\n[URL]({item['url']})\n")
        parts.append("-" * 20)
    return "\n".join(parts)