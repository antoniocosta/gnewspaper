#!/usr/bin/env python3
"""
GNewspaper - Google News client using batchexecute protocol

A Python client for Google News that uses the batchexecute protocol instead
of RSS feeds. Provides more metadata than RSS-based libraries.

Example:
    from gnewspaper import GNews

    google_news = GNews(language='en', country='us')
    news = google_news.get_news('technology')

    for article in news:
        print(article['title'])
        print(article['url'])
        print(article['image'])
        print(article['authors'])
"""

import base64
import json
import re
import requests
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode


# =============================================================================
# CONSTANTS
# =============================================================================

GOOGLE_NEWS_URL = "https://news.google.com"

# Topic name to Freebase MID mapping
TOPIC_MIDS = {
    # Main topics
    "world": "/m/09nm_",
    "nation": "/m/09c7w0",
    "business": "/m/09s1f",
    "technology": "/m/07c1v",
    "entertainment": "/m/02jjt",
    "sports": "/m/06ntj",
    "science": "/m/06mq7",
    "health": "/m/0kt51",
    # Politics & Culture
    "politics": "/m/05qt0",
    "celebrities": "/m/026t6",
    "tv": "/m/01lj9",
    "music": "/m/05qjt",
    "movies": "/m/02vxn",
    "theater": "/m/01c2_0",
    # Sports
    "soccer": "/m/02vx4",
    "cycling": "/m/03c7kzv",
    "motor sports": "/m/083_h",
    "tennis": "/m/07bs0",
    "combat sports": "/m/01bvx",
    "basketball": "/m/018w8",
    "baseball": "/m/018jz",
    "football": "/m/079cl",
    "sports betting": "/m/05v1x6",
    "water sports": "/m/0194d",
    "hockey": "/m/05xnv",
    "golf": "/m/06vbd",
    "cricket": "/m/0jm_",
    "rugby": "/m/04y7b",
    # Business & Finance
    "economy": "/m/02j62",
    "personal finance": "/m/0gnwz4",
    "finance": "/m/01v9724",
    "digital currencies": "/m/01d9ll",
    # Technology
    "mobile": "/m/03_d0",
    "energy": "/m/0glt670",
    "gaming": "/m/01mw1",
    "internet security": "/m/0dyc2c",
    "gadgets": "/m/063km",
    "virtual reality": "/m/03qbcv",
    "robotics": "/m/02_h0",
    # Health & Science
    "nutrition": "/m/05qjc",
    "public health": "/m/0g71qc",
    "mental health": "/m/039jq",
    "medicine": "/m/04zrq",
    "space": "/m/01lyb",
    "wildlife": "/m/05t4q",
    "environment": "/m/01cbzq",
    "neuroscience": "/m/07ygz",
    "physics": "/m/0hkf",
    "geology": "/m/036hv",
    "paleontology": "/m/0263lr1",
    "social sciences": "/m/0gl9p",
    # Lifestyle
    "education": "/m/01h6rj",
    "jobs": "/m/0158vt",
    "online education": "/m/01rzcn",
    "higher education": "/m/03r8gp",
    "vehicles": "/m/03w6kx",
    "arts-design": "/m/0c7hdf",
    "beauty": "/m/07khblk",
    "food": "/m/0c2wf",
    "travel": "/m/0mkz",
    "shopping": "/m/01q4y",
    "home": "/m/0f15k",
    "outdoors": "/m/07h26",
    "fashion": "/m/0d8wb",
}

# GNews-compatible topic names (uppercase)
TOPICS = list(k.upper() for k in TOPIC_MIDS.keys())


# =============================================================================
# TOPIC ID ENCODING
# =============================================================================

def _encode_topic_id(topic: str, language: str, country: str) -> str:
    """Encode a topic ID for Google News."""
    mid = TOPIC_MIDS.get(topic.lower())
    if not mid:
        raise ValueError(f"Unknown topic: {topic}. Available: {list(TOPIC_MIDS.keys())}")

    def encode_varint(n: int) -> bytes:
        result = []
        while n > 127:
            result.append((n & 0x7F) | 0x80)
            n >>= 7
        result.append(n)
        return bytes(result)

    def encode_string(field_num: int, s: str) -> bytes:
        data = s.encode("utf-8")
        header = (field_num << 3) | 2
        return bytes([header]) + encode_varint(len(data)) + data

    inner_msg = encode_string(1, mid)
    inner_msg += encode_string(2, language.lower())
    inner_msg += encode_string(3, country.upper())

    inner = bytes([0x08, 0x10])
    inner += bytes([0x12, len(inner_msg)]) + inner_msg
    inner += bytes([0x28, 0x00])

    inner_b64 = base64.b64encode(inner).decode("ascii").rstrip("=")

    middle = bytes([0x08, 0x0a])
    middle += encode_string(4, inner_b64)
    middle += bytes([0x50, 0x01])

    outer = bytes([0x08, 0x00])
    outer += bytes([0x2a, len(middle)]) + middle

    return base64.b64encode(outer).decode("ascii").rstrip("=")


# =============================================================================
# MAIN CLIENT
# =============================================================================

class GNews:
    """
    GNews-compatible client using batchexecute protocol.

    This is a drop-in replacement for the GNews library that provides:
    - Same API as GNews (get_news, get_top_news, get_news_by_topic, etc.)
    - More metadata (images, exact timestamps)
    - Direct publisher URLs (no decoding needed)
    - Better reliability (uses batchexecute instead of RSS)

    Args:
        language: Language code (default: "en"). Use lowercase.
        country: Country code (default: "us"). Use lowercase.
        max_results: Maximum number of results (default: 100)
        period: Time period filter (e.g., "7d", "1h", "1y")
        start_date: Filter articles after this date (datetime.date or tuple)
        end_date: Filter articles before this date (datetime.date or tuple)
        exclude_websites: List of domains to exclude
        proxy: Proxy configuration (dict)

    Example:
        >>> google_news = GNews(language='en', country='us')
        >>> news = google_news.get_news('artificial intelligence')
        >>> for article in news:
        ...     print(article['title'])
        ...     print(article['url'])      # Direct publisher URL
        ...     print(article['image'])    # Thumbnail URL
    """

    def __init__(
        self,
        language: str = "en",
        country: str = "us",
        max_results: int = 100,
        period: Optional[str] = None,
        start_date: Optional[Union[date, tuple]] = None,
        end_date: Optional[Union[date, tuple]] = None,
        exclude_websites: Optional[List[str]] = None,
        proxy: Optional[Dict] = None,
    ):
        self._language = language.lower()
        self._country = country.lower()
        self._max_results = max_results
        self._period = period
        self._start_date = self._parse_date(start_date)
        self._end_date = self._parse_date(end_date)
        self._exclude_websites = exclude_websites or []
        self._proxy = proxy

        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        if proxy:
            self._session.proxies.update(proxy)

    # =========================================================================
    # Properties (GNews compatible)
    # =========================================================================

    @property
    def language(self) -> str:
        return self._language

    @language.setter
    def language(self, value: str):
        self._language = value.lower()

    @property
    def country(self) -> str:
        return self._country

    @country.setter
    def country(self, value: str):
        self._country = value.lower()

    @property
    def max_results(self) -> int:
        return self._max_results

    @max_results.setter
    def max_results(self, value: int):
        self._max_results = value

    @property
    def period(self) -> Optional[str]:
        return self._period

    @period.setter
    def period(self, value: Optional[str]):
        self._period = value

    @property
    def start_date(self) -> Optional[date]:
        return self._start_date

    @start_date.setter
    def start_date(self, value: Optional[Union[date, tuple]]):
        self._start_date = self._parse_date(value)

    @property
    def end_date(self) -> Optional[date]:
        return self._end_date

    @end_date.setter
    def end_date(self, value: Optional[Union[date, tuple]]):
        self._end_date = self._parse_date(value)

    @property
    def exclude_websites(self) -> List[str]:
        return self._exclude_websites

    @exclude_websites.setter
    def exclude_websites(self, value: List[str]):
        self._exclude_websites = value or []

    # =========================================================================
    # Internal Methods
    # =========================================================================

    @staticmethod
    def _parse_date(value: Optional[Union[date, tuple]]) -> Optional[date]:
        """Parse date from various formats."""
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, tuple) and len(value) == 3:
            return date(value[0], value[1], value[2])
        return None

    def _build_url(self, path: str, params: Optional[Dict] = None) -> str:
        """Build URL with locale parameters."""
        hl = f"{self._language}-{self._country.upper()}"
        url_params = {
            "hl": hl,
            "gl": self._country.upper(),
            "ceid": f"{self._country.upper()}:{self._language}",
        }
        if params:
            url_params.update(params)
        return f"{GOOGLE_NEWS_URL}{path}?{urlencode(url_params)}"

    def _build_search_query(self, query: str) -> str:
        """Build search query with date filters."""
        parts = [query]

        if self._period:
            parts.append(f"when:{self._period}")

        if self._start_date:
            parts.append(f"after:{self._start_date.isoformat()}")

        if self._end_date:
            parts.append(f"before:{self._end_date.isoformat()}")

        for site in self._exclude_websites:
            parts.append(f"-site:{site}")

        return " ".join(parts)

    def _fetch(self, url: str) -> str:
        """Fetch page HTML."""
        resp = self._session.get(url)
        resp.raise_for_status()
        return resp.text

    def _extract_data(self, html: str) -> Dict[str, Any]:
        """Extract data blocks from HTML."""
        result = {}
        pattern = r'<script class="ds:(\d+)"[^>]*>[\s\S]*?data:([\s\S]*?),\s*sideChannel:[\s\S]*?</script>'
        for match in re.finditer(pattern, html):
            try:
                result[f"ds:{match.group(1)}"] = json.loads(match.group(2).strip())
            except json.JSONDecodeError:
                pass
        return result

    def _parse_article(self, data: list) -> Optional[Dict[str, Any]]:
        """Parse article from raw data into GNews-compatible dict."""
        try:
            if not (isinstance(data, list) and len(data) > 10 and
                    data[0] == 13 and isinstance(data[1], list) and
                    len(data[1]) >= 2 and isinstance(data[1][1], str) and
                    data[1][1].startswith("CBMi")):
                return None

            article_id = data[1][1]
            title = data[2] if len(data) > 2 else None
            url = data[6] if len(data) > 6 else None

            if not (article_id and title and url):
                return None

            # Timestamp
            published = None
            published_date = ""
            if len(data) > 4 and isinstance(data[4], list) and data[4]:
                published = data[4][0]
                if published:
                    dt = datetime.fromtimestamp(published)
                    published_date = dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

            # Image
            image = None
            if len(data) > 8 and isinstance(data[8], list) and data[8]:
                img_data = data[8][0]
                if isinstance(img_data, list) and len(img_data) > 13:
                    image = img_data[13]

            # Source/Publisher
            source = "Unknown"
            favicon = None
            if len(data) > 10 and isinstance(data[10], list) and len(data[10]) > 2:
                pub_data = data[10]
                source = pub_data[2] if len(pub_data) > 2 else "Unknown"
                if len(pub_data) > 3 and isinstance(pub_data[3], list) and pub_data[3]:
                    favicon = pub_data[3][0]

            # Authors - found at end of article array as [["Author Name"]]
            authors = []
            for i in range(len(data) - 1, max(len(data) - 10, 10), -1):
                item = data[i]
                if (isinstance(item, list) and len(item) == 1 and
                    isinstance(item[0], list) and len(item[0]) >= 1 and
                    isinstance(item[0][0], str) and
                    not item[0][0].startswith("http") and
                    not item[0][0].startswith("CAA")):
                    authors = item[0]
                    break

            return {
                "title": title,
                "url": url,
                "published_date": published_date,
                "published_timestamp": published,
                "publisher": {
                    "title": source,
                    "favicon": favicon,
                },
                "image": image,
                "authors": authors,
            }
        except Exception:
            return None

    def _extract_articles(self, data: Any, articles: Optional[List[Dict]] = None) -> List[Dict]:
        """Recursively extract articles from nested data."""
        if articles is None:
            articles = []

        if not isinstance(data, list):
            return articles

        article = self._parse_article(data)
        if article:
            articles.append(article)
        else:
            for item in data:
                if isinstance(item, list):
                    self._extract_articles(item, articles)

        return articles

    def _extract_clusters(self, data: Any) -> List[Dict]:
        """Extract article clusters from data."""
        clusters = []

        if not isinstance(data, list):
            return clusters

        # Find cluster container (usually at data[1][3][1] for gbres)
        try:
            if data[0] == "gbres" and len(data) > 1:
                section = data[1]
                if isinstance(section, list) and len(section) > 3:
                    cluster_container = section[3]
                    if isinstance(cluster_container, list) and len(cluster_container) > 1:
                        cluster_items = cluster_container[1]
                        if isinstance(cluster_items, list):
                            for cluster_data in cluster_items:
                                articles = self._extract_articles(cluster_data, [])
                                if articles:
                                    # Mark main article
                                    articles[0]["is_main"] = True
                                    for a in articles[1:]:
                                        a["is_main"] = False
                                    clusters.append({
                                        "articles": articles,
                                    })
        except (IndexError, TypeError):
            pass

        # Fallback: treat all articles as individual clusters
        if not clusters:
            articles = self._extract_articles(data, [])
            for article in articles:
                article["is_main"] = True
                clusters.append({"articles": [article]})

        return clusters

    def _filter_articles(self, articles: List[Dict]) -> List[Dict]:
        """Apply filters and limits to articles."""
        result = articles

        # Filter by exclude_websites
        if self._exclude_websites:
            result = [
                a for a in result
                if not any(site.lower() in a["url"].lower() for site in self._exclude_websites)
            ]

        # Filter by date range (if we have timestamps)
        if self._start_date:
            start_ts = datetime.combine(self._start_date, datetime.min.time()).timestamp()
            result = [a for a in result if a.get("published_timestamp") and a["published_timestamp"] >= start_ts]

        if self._end_date:
            end_ts = datetime.combine(self._end_date, datetime.max.time()).timestamp()
            result = [a for a in result if a.get("published_timestamp") and a["published_timestamp"] <= end_ts]

        # Apply max_results
        return result[:self._max_results]

    def _filter_clusters(self, clusters: List[Dict]) -> List[Dict]:
        """Apply filters and limits to clusters."""
        result = []
        total = 0

        for cluster in clusters:
            if total >= self._max_results:
                break

            filtered_articles = []
            for article in cluster["articles"]:
                if total >= self._max_results:
                    break

                # Filter by exclude_websites
                if self._exclude_websites:
                    if any(site.lower() in article["url"].lower() for site in self._exclude_websites):
                        continue

                # Filter by date range
                if self._start_date:
                    start_ts = datetime.combine(self._start_date, datetime.min.time()).timestamp()
                    if not article.get("published_timestamp") or article["published_timestamp"] < start_ts:
                        continue

                if self._end_date:
                    end_ts = datetime.combine(self._end_date, datetime.max.time()).timestamp()
                    if not article.get("published_timestamp") or article["published_timestamp"] > end_ts:
                        continue

                filtered_articles.append(article)
                total += 1

            if filtered_articles:
                result.append({"articles": filtered_articles})

        return result

    # =========================================================================
    # Public API (GNews compatible)
    # =========================================================================

    def get_news(self, key: str, clustered: bool = False) -> List[Dict[str, Any]]:
        """
        Search for news articles by keyword.

        Args:
            key: Search keyword/query
            clustered: If True, returns articles grouped in clusters

        Returns:
            List of article dictionaries (or cluster dicts if clustered=True)

        Example:
            >>> news = google_news.get_news('artificial intelligence')
            >>> clustered = google_news.get_news('AI', clustered=True)
        """
        if not key or not key.strip():
            raise ValueError("Search key cannot be empty")

        query = self._build_search_query(key)
        url = self._build_url("/search", {"q": query})
        html = self._fetch(url)
        ds_data = self._extract_data(html)

        if clustered:
            clusters = []
            for data in ds_data.values():
                if isinstance(data, list) and data and data[0] == "gsrres":
                    clusters.extend(self._extract_clusters(data))
            return self._filter_clusters(clusters)
        else:
            articles = []
            for data in ds_data.values():
                if isinstance(data, list) and data and data[0] == "gsrres":
                    articles.extend(self._extract_articles(data))
            return self._filter_articles(articles)

    def get_top_news(self, clustered: bool = False) -> List[Dict[str, Any]]:
        """
        Get top/headline news for the configured region.

        Args:
            clustered: If True, returns articles grouped in clusters

        Returns:
            List of article dictionaries (or cluster dicts if clustered=True)

        Example:
            >>> top_news = google_news.get_top_news()
            >>> clustered = google_news.get_top_news(clustered=True)
        """
        url = self._build_url("/home")
        html = self._fetch(url)
        ds_data = self._extract_data(html)

        if clustered:
            clusters = []
            for data in ds_data.values():
                if isinstance(data, list) and data and data[0] in ("gbres", "gfres"):
                    clusters.extend(self._extract_clusters(data))
            return self._filter_clusters(clusters)
        else:
            articles = []
            for data in ds_data.values():
                if isinstance(data, list) and data and data[0] in ("gbres", "gfres"):
                    articles.extend(self._extract_articles(data))
            return self._filter_articles(articles)

    def get_news_by_topic(self, topic: str, clustered: bool = False) -> List[Dict[str, Any]]:
        """
        Get news by topic category.

        Args:
            topic: Topic name (case-insensitive). See TOPICS for available options.
                   Examples: WORLD, NATION, BUSINESS, TECHNOLOGY, ENTERTAINMENT,
                   SPORTS, SCIENCE, HEALTH, POLITICS, SOCCER, GAMING, etc.
            clustered: If True, returns articles grouped in clusters

        Returns:
            List of article dictionaries (or cluster dicts if clustered=True)

        Example:
            >>> tech_news = google_news.get_news_by_topic('TECHNOLOGY')
            >>> clustered = google_news.get_news_by_topic('TECHNOLOGY', clustered=True)
        """
        topic_lower = topic.lower()
        if topic_lower not in TOPIC_MIDS:
            raise ValueError(f"Invalid topic: {topic}. Available: {TOPICS}")

        topic_id = _encode_topic_id(topic_lower, self._language, self._country)
        url = self._build_url(f"/topics/{topic_id}")
        html = self._fetch(url)
        ds_data = self._extract_data(html)

        if clustered:
            clusters = []
            for data in ds_data.values():
                if isinstance(data, list) and data and data[0] == "gtsres":
                    clusters.extend(self._extract_clusters(data))
            return self._filter_clusters(clusters)
        else:
            articles = []
            for data in ds_data.values():
                if isinstance(data, list) and data and data[0] == "gtsres":
                    articles.extend(self._extract_articles(data))
            return self._filter_articles(articles)

    def get_news_by_location(self, location: str, clustered: bool = False) -> List[Dict[str, Any]]:
        """
        Get news filtered by location.

        Args:
            location: Location name (e.g., "New York", "California")
            clustered: If True, returns articles grouped in clusters

        Returns:
            List of article dictionaries (or cluster dicts if clustered=True)

        Example:
            >>> nyc_news = google_news.get_news_by_location('New York')
        """
        if not location or not location.strip():
            raise ValueError("Location cannot be empty")

        return self.get_news(location, clustered=clustered)

    def get_news_by_site(self, site: str, clustered: bool = False) -> List[Dict[str, Any]]:
        """
        Get news from a specific website/domain.

        Args:
            site: Domain name (e.g., "cnn.com", "bbc.com")
            clustered: If True, returns articles grouped in clusters

        Returns:
            List of article dictionaries (or cluster dicts if clustered=True)

        Example:
            >>> cnn_news = google_news.get_news_by_site('cnn.com')
        """
        if not site or not site.strip():
            raise ValueError("Site cannot be empty")

        return self.get_news(f"site:{site}", clustered=clustered)

    def get_full_article(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get full article content using newspaper4k.

        Args:
            url: Article URL

        Returns:
            Dictionary with full article data (title, text, authors, etc.)

        Note:
            Requires newspaper4k: pip install newspaper4k
        """
        try:
            from newspaper import Article
        except ImportError:
            raise ImportError(
                "newspaper4k is required for get_full_article(). "
                "Install with: pip install newspaper4k"
            )

        try:
            article = Article(url)
            article.download()
            article.parse()

            return {
                "title": article.title,
                "text": article.text,
                "authors": article.authors,
                "publish_date": article.publish_date,
                "top_image": article.top_image,
                "images": list(article.images),
                "movies": article.movies,
            }
        except Exception:
            return None


# =============================================================================
# CLI
# =============================================================================

def main():
    """Command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(
        description="GNewspaper - Fetch news from Google News",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--topic", "-t", choices=list(TOPIC_MIDS.keys()), help="Topic")
    parser.add_argument("--language", "-l", default="en", help="Language (default: en)")
    parser.add_argument("--country", "-c", default="us", help="Country (default: us)")
    parser.add_argument("--max", "-m", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--period", "-p", help="Time period (e.g., 7d, 1h)")
    parser.add_argument("--clustered", action="store_true", help="Group articles in clusters")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--output", "-o", help="Save to file")

    args = parser.parse_args()

    gn = GNews(
        language=args.language,
        country=args.country,
        max_results=args.max,
        period=args.period,
    )

    if args.topic:
        result = gn.get_news_by_topic(args.topic, clustered=args.clustered)
    elif args.query:
        result = gn.get_news(args.query, clustered=args.clustered)
    else:
        result = gn.get_top_news(clustered=args.clustered)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Saved to {args.output}")
    elif args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if args.clustered:
            for i, cluster in enumerate(result, 1):
                print(f"\n=== Cluster {i} ({len(cluster['articles'])} articles) ===")
                for article in cluster["articles"]:
                    main_marker = "[MAIN] " if article.get("is_main") else "       "
                    print(f"{main_marker}{article['title'][:60]}...")
                    print(f"       {article['publisher']['title']}")
        else:
            for i, article in enumerate(result, 1):
                print(f"\n{i}. {article['title']}")
                print(f"   {article['publisher']['title']}")
                print(f"   {article['published_date']}")
                print(f"   {article['url'][:60]}...")


if __name__ == "__main__":
    main()
