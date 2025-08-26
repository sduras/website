import asyncio
import json
import logging
import os
import random
import re
from typing import Any, Callable, Dict, List
from urllib.parse import urljoin

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from bs4 import BeautifulSoup

# --- Configuration & Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

HEADERS = {
    "Accept": "text/html",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "uk-UA,uk;en;q=0.5",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
}

MAX_HEADLINES = 5
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_MIN = 1  # seconds
RETRY_BACKOFF_MAX = 3  # seconds


# --- Utility Functions ---
def clean_text(text: str, max_chars: int = 300) -> str:
    """Normalizes whitespace and truncates text."""
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "..."
    return cleaned


def load_config(config_path: str = None) -> List[Dict[str, Any]]:
    """Loads scraping sources from a JSON configuration file."""
    if config_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config.json")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("sources", [])
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return []


# --- Core Scraper Logic ---
class Scraper:
    def __init__(self, session: ClientSession):
        self.session = session
        self.scrapers = {
            "Vim": self.fetch_vim_version,
            "Debian": self.fetch_debian_stable_version,
            "GnuPG": self.fetch_gpg_stable_version,
            "cmus": self.fetch_cmus_stable_version,
            "aShell": self.fetch_aShell_stable_version,
            "picoopenpgp": self.fetch_pico_openpgp_stable_version,
        }

    async def _fetch_with_retry(self, url: str) -> str:
        """Fetches a URL with a simple retry mechanism and exponential backoff."""
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                timeout = ClientTimeout(total=10)
                async with self.session.get(url, timeout=timeout) as response:
                    response.raise_for_status()
                    return await response.text()
            except Exception as e:
                logging.warning(
                    f"[{attempt}/{RETRY_ATTEMPTS}] Error fetching {url}: {e}"
                )
                if attempt < RETRY_ATTEMPTS:
                    wait = random.uniform(RETRY_BACKOFF_MIN, RETRY_BACKOFF_MAX)
                    await asyncio.sleep(wait)
                else:
                    raise

    async def fetch_by_selector(
        self, url: str, css_selector: str
    ) -> List[Dict[str, str]]:
        """Scrapes a page for elements matching a CSS selector."""
        try:
            html = await self._fetch_with_retry(url)
            soup = BeautifulSoup(html, "html.parser")
            elements = soup.select(css_selector)[:MAX_HEADLINES]
            results = []
            for el in elements:
                if el and el.text.strip() and el.get("href"):
                    results.append(
                        {"text": el.text.strip(), "url": urljoin(url, el["href"])}
                    )
            return results
        except Exception as e:
            logging.error(f"Failed to scrape using selector from {url}: {e}")
            return []

    # --- Custom Scraper Implementations ---
    async def fetch_vim_version(self, url: str) -> List[Dict[str, str]]:
        try:
            html = await self._fetch_with_retry(url)
            soup = BeautifulSoup(html, "html.parser")
            version_heading = soup.find("h1", string="Version")
            if not version_heading:
                return []

            text_node = version_heading.find_next_sibling(string=True)
            if text_node:
                return [{"text": clean_text(text_node), "url": url}]
            return []
        except Exception as e:
            logging.error(f"Failed to scrape Vim page: {e}")
            return []

    async def fetch_debian_stable_version(self, url: str) -> List[Dict[str, str]]:
        try:
            html = await self._fetch_with_retry(url)
            soup = BeautifulSoup(html, "html.parser")
            target_p = soup.select_one(
                "#content > dl > dd:nth-of-type(1) > p:nth-of-type(3)"
            )
            if target_p:
                return [{"text": clean_text(target_p.get_text()), "url": url}]
            return []
        except Exception as e:
            logging.error(f"Failed to scrape Debian page: {e}")
            return []

    async def fetch_gpg_stable_version(self, url: str) -> List[Dict[str, str]]:
        try:
            html = await self._fetch_with_retry(url)
            soup = BeautifulSoup(html, "html.parser")
            target_p = soup.select_one("#text-1 > p:nth-of-type(3)")
            if target_p:
                return [{"text": clean_text(target_p.get_text()), "url": url}]
            return []
        except Exception as e:
            logging.error(f"Failed to scrape GnuPG page: {e}")
            return []

    async def fetch_cmus_stable_version(self, url: str) -> List[Dict[str, str]]:
        try:
            html = await self._fetch_with_retry(url)
            soup = BeautifulSoup(html, "html.parser")
            target_p = soup.select_one(
                "#content > div:nth-child(8) > ul > li:nth-child(1)"
            )
            if target_p:
                return [{"text": clean_text(target_p.get_text()), "url": url}]
            return []
        except Exception as e:
            logging.error(f"Failed to scrape cmus page: {e}")
            return []

    async def fetch_aShell_stable_version(self, url: str) -> List[Dict[str, str]]:
        try:
            html = await self._fetch_with_retry(url)
            soup = BeautifulSoup(html, "html.parser")
            version_heading = soup.select_one("article h1[id^='version']")
            if not version_heading:
                return []

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

            parts = [version_heading.get_text(strip=True)]
            if whats_new:
                parts.append("\nWhat’s New:")
                parts.extend([f"• {item}" for item in whats_new])
            if improvements:
                parts.append("\nImprovements:")
                parts.extend([f"• {item}" for item in improvements])

            return [{"text": "\n".join(parts), "url": url}]
        except Exception as e:
            logging.error(f"Failed to scrape a-Shell page: {e}")
            return []

    async def fetch_pico_openpgp_stable_version(self, url: str) -> List[Dict[str, str]]:
        try:
            html = await self._fetch_with_retry(url)
            soup = BeautifulSoup(html, "html.parser")

            latest_release_link = soup.select_one("a.Link span.Label--success")
            if not latest_release_link:
                logging.warning("Could not find 'Latest' release label")
                return []

            latest_url = urljoin(url, latest_release_link.parent["href"])
            release_html = await self._fetch_with_retry(latest_url)
            release_soup = BeautifulSoup(release_html, "html.parser")

            version = (
                release_soup.select_one("h1 strong") or release_soup.select_one("h1")
            ).get_text(strip=True)
            markdown_body = release_soup.select_one("div.markdown-body")

            whats_new, enhancements = [], []
            if markdown_body:
                for heading in markdown_body.find_all("h2"):
                    heading_text = heading.get_text(strip=True).lower()
                    next_sibling = heading.find_next_sibling("ul")
                    if next_sibling:
                        items = [
                            li.get_text(strip=True) for li in next_sibling.select("li")
                        ]
                        if "new" in heading_text:
                            whats_new = items
                        elif "enhancements" in heading_text:
                            enhancements = items

            text_parts = [f"Version {version}", ""]
            if whats_new:
                text_parts.append("New:")
                text_parts.extend([f"• {item}" for item in whats_new])
            if enhancements:
                text_parts.append("\nEnhancements:")
                text_parts.extend([f"• {item}" for item in enhancements])

            return [{"text": "\n".join(text_parts).strip(), "url": latest_url}]
        except Exception as e:
            logging.error(f"Failed to scrape pico-openpgp page: {e}")
            return []


# --- Main Execution Flow ---
async def get_news() -> Dict[str, List[Dict[str, str]]]:
    """Fetches news from all sources configured in config.json."""
    sources = load_config()
    if not sources:
        logging.error("No sources found. Exiting.")
        return {}

    async with ClientSession(
        connector=TCPConnector(ssl=False), headers=HEADERS
    ) as session:
        scraper = Scraper(session)
        tasks = {}

        for source in sources:
            name = source.get("name")
            url = source.get("url")
            selector = source.get("css_selector")
            mode = source.get("mode", "default")

            if not name or not url:
                logging.warning(f"Skipping malformed source entry: {source}")
                continue

            if mode == "custom":
                task_func = scraper.scrapers.get(name)
                if task_func:
                    tasks[name] = task_func(url)
                else:
                    logging.warning(f"Unknown custom source mode for '{name}'.")
            elif selector:
                tasks[name] = scraper.fetch_by_selector(url, selector)
            else:
                logging.warning(
                    f"Skipping '{name}' — no CSS selector or valid mode provided."
                )

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        all_news = {}
        for name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logging.error(f"Scraping for '{name}' failed: {result}")
                all_news[name] = []
            else:
                all_news[name] = result

    return all_news


def format_output(all_news: Dict[str, List[Dict[str, str]]]) -> str:
    """Formats the scraped news into a human-readable string."""
    output_parts = ["Updates\n"]
    for source, headlines in all_news.items():
        output_parts.append(f"**Updates from {source}**\n")
        if headlines:
            for article in headlines:
                output_parts.append(f"{article['text']}\n[URL]({article['url']})\n")
        else:
            output_parts.append("Failed to fetch info.\n")
        output_parts.append("-" * 20 + "\n")

    return "\n".join(output_parts).strip()


async def main():
    """Main entry point for the application."""
    logging.info("Starting news fetch operation...")
    news = await get_news()

    if news:
        formatted_message = format_output(news)
        print(formatted_message)
    else:
        print("No news could be fetched.")


if __name__ == "__main__":
    asyncio.run(main())
