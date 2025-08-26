# api/scrap/utils.py

import re
import asyncio
import random
from aiohttp import ClientSession, ClientTimeout
import datetime
from typing import Optional
from bs4 import BeautifulSoup
    
import logging
logging.basicConfig(level=logging.DEBUG)
logging.debug("utils.py loaded")

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_MIN = 1
RETRY_BACKOFF_MAX = 3

def clean_text(text: str, max_chars: int = 300) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "..."
    return cleaned

async def fetch_with_retry(session: ClientSession, url: str) -> str:
    for attempt in range(RETRY_ATTEMPTS):
        try:
            timeout = ClientTimeout(total=10)
            async with session.get(url, timeout=timeout) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(random.uniform(RETRY_BACKOFF_MIN, RETRY_BACKOFF_MAX))
            else:
                logging.error(f"Failed to fetch {url}: {e}")
                raise


def utc_now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def extract_version(text: str, pattern: str, default="Unknown") -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1) if match else default


def extract_first_sentence(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return sentences[0] if sentences else text


async def get_html_soup(session: ClientSession, url: str) -> Optional[BeautifulSoup]:
    try:
        html = await fetch_with_retry(session, url)
        return BeautifulSoup(html, "html.parser")
    except Exception as e:
        logging.error(f"Failed to fetch or parse {url}: {e}", exc_info=True)
        return None