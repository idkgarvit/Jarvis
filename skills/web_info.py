"""Web search, weather, news, and page summarization skills."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

NEWS_FEEDS = {
    "top": "https://news.ycombinator.com/",
    "tech": "https://news.ycombinator.com/",
    "world": "https://www.bbc.com/news/world",
    "business": "https://www.bbc.com/news/business",
    "science": "https://www.bbc.com/news/science_and_environment",
}


def search_web(query: str, num_results: int = 5) -> str:
    try:
        from httpx import Client
        from bs4 import BeautifulSoup

        with Client(follow_redirects=True, timeout=15) as client:
            url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            r = client.get(url)
            soup = BeautifulSoup(r.text, "html.parser")
            results = soup.select(".result__body") or []

            output = []
            for res in results[:num_results]:
                title = res.select_one(".result__title a") or res.select_one("a")
                snippet = res.select_one(".result__snippet") or res.select_one(".snippet")
                if title:
                    t = title.get_text(strip=True)
                    snip = snippet.get_text(strip=True)[:200] if snippet else ""
                    output.append(f"\u2022 {t}\n  {snip}")

            return f"Web search results for '{query}':\n" + "\n\n".join(output) if output else "No results."
    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return f"Search failed: {e}"


def get_weather(location: str = "") -> str:
    import httpx
    try:
        loc = location or "auto:ip"
        r = httpx.get(f"https://wttr.in/{loc}?format=%l:+%t+%C+%h+humidity+%w+wind", timeout=10)
        return r.text.strip() if r.status_code == 200 else f"Weather lookup failed ({r.status_code})"
    except Exception as e:
        return f"Weather error: {e}"


def get_news(topic: str = "top", count: int = 5) -> str:
    import httpx
    from bs4 import BeautifulSoup

    url = NEWS_FEEDS.get(topic.lower(), NEWS_FEEDS["top"])
    try:
        r = httpx.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        titles = soup.select(".titleline a") if "hacker" in url else soup.select("h3 a, h2 a, .gs-c-promo-heading")
        titles = [t for t in titles if t.get_text(strip=True)]
        if not titles:
            return "Couldn't fetch news."
        items = [f"\u2022 {t.get_text(strip=True)}" for t in titles[:count]]
        return f"News ({topic}):\n" + "\n".join(items)
    except Exception as e:
        return f"News fetch failed: {e}"


def summarize_page(url: str) -> str:
    import httpx
    from bs4 import BeautifulSoup
    try:
        r = httpx.get(url, follow_redirects=True, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ", strip=True).split())[:3000]
        return f"Summary of {url}:\n{text}"
    except Exception as e:
        return f"Failed to summarize: {e}"


def get_time() -> str:
    from datetime import datetime
    return datetime.now().strftime("%A, %B %d, %Y \u2014 %I:%M %p")
