# api/scrap/news.py

from urllib.parse import urljoin

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from bs4 import BeautifulSoup


async def fetch_news(session, url, class_name, max_words=15, ellipsis="..."):
    timeout = ClientTimeout(total=10)
    async with session.get(url, timeout=timeout) as response:
        response.raise_for_status()
        html = await response.text()
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.find_all("div", class_=class_name)

        headlines = []
        for article in articles[:5]:
            title = article.find("a")
            if title:
                words = title.text.strip().split()[:max_words]
                headline = " ".join(words)
                if len(words) < len(title.text.strip().split()):
                    headline += ellipsis
                link = urljoin(url, title.get("href", "#"))
                headlines.append({"text": headline, "url": link})

        return headlines


async def bbc(session, url):
    return await fetch_news(session, url, class_name="bbc-14zb6im")


async def dw(session, url):
    return await fetch_news(session, url, class_name="news-title")


async def cnn(session, url):
    return await fetch_news(
        session, url, class_name="container_lead-plus-headlines__item"
    )


async def irishtimes(session, url):
    return await fetch_news(session, url, class_name="b-flex-promo-card__text")
