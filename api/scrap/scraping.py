# api/scrap/scraping.py

import asyncio
import datetime
import json
import logging
import os
import random
from typing import Dict, List
from urllib.parse import urljoin

import pytz
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from api.scrap import news, software
from api.scrap.utils import clean_text, fetch_with_retry
from bs4 import BeautifulSoup

logging.debug("scraping.py loaded")


HEADERS = {
    "Accept": "text/html",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "uk-UA,uk;q=0.5",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
}


RETRY_ATTEMPTS = 3
RETRY_BACKOFF_MIN = 1
RETRY_BACKOFF_MAX = 3
MAX_HEADLINES = 5


SCRAPER_REGISTRY = {
    "Debian": software.fetch_debian_stable_version,
    "Python": software.fetch_python_version,
    "Vim": software.fetch_vim_version,
    "aShell": software.fetch_aShell_stable_version,
    "cmus": software.fetch_cmus_stable_version,
    "GnuPG": software.fetch_gpg_stable_version,
    "BBC": news.bbc,
    "DW": news.dw,
    "CNN": news.cnn,
    "Irish Times": news.irishtimes,
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


async def fetch_by_selector(
    session, url: str, css_selector: str
) -> List[Dict[str, str]]:
    try:
        html = await fetch_with_retry(session, url)
        soup = BeautifulSoup(html, "html.parser")
        elements = soup.select(css_selector)[:MAX_HEADLINES]
        return [
            {"text": clean_text(el.text), "url": urljoin(url, el.get("href", "#"))}
            for el in elements
            if el.text.strip()
        ]
    except Exception as e:
        logging.error(f"Selector scraping failed for {url}: {e}")
        return []


async def get_updates() -> dict:
    sources = load_config()
    if not sources:
        logging.error("No sources found. Exiting.")
        return {}

    kyiv_tz = pytz.timezone("Europe/Kyiv")

    async with ClientSession(
        connector=TCPConnector(ssl=False), headers=HEADERS
    ) as session:
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
                logging.warning(
                    f"Skipping '{name}' — no CSS selector or valid mode provided."
                )

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        categorized_results = {}
        utc_now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        kyiv_now = utc_now.astimezone(kyiv_tz)
        formatted_kyiv_now = kyiv_now.strftime("%Y-%m-%d %H:%M")

        for name, result in zip(tasks.keys(), results):
            category = source_categories.get(name, "uncategorized")

            if category not in categorized_results:
                categorized_results[category] = {}

            if isinstance(result, Exception):
                logging.error(f"Scraping for '{name}' failed: {result}")
                categorized_results[category][name] = []
            else:
                items_with_timestamp = []
                for item in result:
                    new_item = item.copy()
                    new_item["fetched_at"] = utc_now.isoformat().replace("+00:00", "Z")

                    if "fetched_at" in item:
                        try:
                            dt_utc = datetime.datetime.fromisoformat(
                                item["fetched_at"].replace("Z", "+00:00")
                            ).replace(tzinfo=pytz.utc)
                        except Exception:
                            dt_utc = utc_now
                    else:
                        dt_utc = utc_now
                    dt_kyiv = dt_utc.astimezone(kyiv_tz)
                    new_item["fetched_at_kyiv"] = dt_kyiv.strftime("%Y-%m-%d %H:%M")

                    items_with_timestamp.append(new_item)

                categorized_results[category][name] = items_with_timestamp

        metadata = {
            "fetched_at": utc_now.isoformat().replace("+00:00", "Z"),
            "fetched_at_kyiv": formatted_kyiv_now,
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
