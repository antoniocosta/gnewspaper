# GNewspaper

A GNews-compatible Python client for Google News using the batchexecute protocol instead of RSS feeds. Drop-in replacement for the [GNews](https://github.com/ranahaani/GNews) library with more features and reliability.

If you like ❤️ this or find it useful 🌟, support the project by buying me a coffee ☕.

<a href="https://www.buymeacoffee.com/antoniocosta" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 40px !important;width: 140px !important;" ></a>

## Why GNewspaper?

| Feature | GNews (RSS) | GNewspaper (batchexecute) |
|---------|-------------|---------------------------|
| Article title | ✅ | ✅ |
| Article URL | ✅ | ✅ |
| Publisher | ✅ | ✅ |
| Publish date | ✅ | ✅ |
| **Article image** | ❌ | ✅ |
| **Exact timestamp** | ❌ | ✅ |
| **Authors** | ❌ | ✅ |
| **Article clustering** | ❌ | ✅ |
| **More results** | ~100 | 200+ |
| Date filtering | ✅ | ✅ |
| Topic filtering | ✅ | ✅ |
| Search | ✅ | ✅ |

## Installation

```bash
pip install requests

# Optional: for get_full_article()
pip install newspaper4k
```

## Quick Start

```python
from gnewspaper import GNews

# Initialize (same as GNews)
google_news = GNews(language='en', country='us')

# Get top news
top_news = google_news.get_top_news()

# Search for news
ai_news = google_news.get_news('artificial intelligence')

# Get news by topic
tech_news = google_news.get_news_by_topic('TECHNOLOGY')

# Print results
for article in tech_news[:5]:
    print(article['title'])
    print(article['publisher']['title'])
    print(article['published_date'])
    print(article['url'])
    if article['authors']:
        print(f"By: {', '.join(article['authors'])}")
    print()

# Get clustered results (articles grouped by story)
clusters = google_news.get_top_news(clustered=True)
for cluster in clusters:
    main = cluster['articles'][0]  # First article has is_main=True
    print(f"Story: {main['title']}")
    print(f"  Related: {len(cluster['articles']) - 1} articles")
```

## API Reference

### Constructor

```python
GNews(
    language='en',      # Language code (lowercase)
    country='us',       # Country code (lowercase)
    max_results=100,    # Maximum results to return
    period=None,        # Time period: '1h', '1d', '7d', '1m', '1y'
    start_date=None,    # Filter: articles after this date
    end_date=None,      # Filter: articles before this date
    exclude_websites=None,  # List of domains to exclude
    proxy=None          # Proxy configuration dict
)
```

### Methods

All methods support an optional `clustered` parameter. When `clustered=True`, returns articles grouped by story instead of a flat list.

#### `get_news(key: str, clustered: bool = False) -> List[Dict]`

Search for news articles.

```python
news = google_news.get_news('climate change')
clusters = google_news.get_news('climate change', clustered=True)
```

#### `get_top_news(clustered: bool = False) -> List[Dict]`

Get top/headline news for the configured region.

```python
headlines = google_news.get_top_news()
clusters = google_news.get_top_news(clustered=True)
```

#### `get_news_by_topic(topic: str, clustered: bool = False) -> List[Dict]`

Get news by topic category.

```python
# Available topics: WORLD, NATION, BUSINESS, TECHNOLOGY,
#                   ENTERTAINMENT, SPORTS, SCIENCE, HEALTH
tech = google_news.get_news_by_topic('TECHNOLOGY')
```

#### `get_news_by_location(location: str, clustered: bool = False) -> List[Dict]`

Get news filtered by location.

```python
nyc_news = google_news.get_news_by_location('New York')
```

#### `get_news_by_site(site: str, clustered: bool = False) -> List[Dict]`

Get news from a specific website.

```python
cnn_news = google_news.get_news_by_site('cnn.com')
```

#### `get_full_article(url: str) -> Dict`

Get full article content (requires newspaper4k).

```python
article = google_news.get_full_article('https://example.com/article')
print(article['text'])
```

### Properties

All properties have getters and setters:

```python
google_news.language = 'de'
google_news.country = 'de'
google_news.max_results = 50
google_news.period = '7d'
google_news.start_date = (2024, 1, 1)  # or datetime.date
google_news.end_date = (2024, 12, 31)
google_news.exclude_websites = ['example.com']
```

## Article Format

### Flat Format (default)

```python
{
    'title': 'Article headline',
    'url': 'https://example.com/article',
    'published_date': 'Thu, 22 Jan 2026 00:42:13 GMT',
    'published_timestamp': 1769047920,
    'publisher': {
        'title': 'Publisher Name',
        'favicon': 'https://favicon-url...'
    },
    'image': 'https://image-url...',
    'authors': ['Author Name']
}
```

### Clustered Format

When `clustered=True`, returns a list of clusters:

```python
{
    'articles': [
        {
            'title': 'Main article headline',
            'url': 'https://example.com/article',
            'published_date': 'Thu, 22 Jan 2026 00:42:13 GMT',
            'published_timestamp': 1769047920,
            'publisher': {
                'title': 'Publisher Name',
                'favicon': '...'
            },
            'image': 'https://image-url...',
            'authors': ['Author Name'],
            'is_main': True
        },
        {
            'title': 'Related article',
            ...
            'is_main': False
        }
    ]
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Article headline |
| `url` | string | Direct publisher URL |
| `published_date` | string | RFC 2822 format ("Thu, 22 Jan 2026 00:42:13 GMT") |
| `published_timestamp` | int | Unix timestamp (seconds since epoch) |
| `publisher.title` | string | Publisher name |
| `publisher.favicon` | string | Publisher favicon URL |
| `image` | string | Article thumbnail URL |
| `authors` | list | Author names (may be empty) |
| `is_main` | bool | Main article in cluster (clustered mode only) |

## Date Filtering

Filter articles by date using multiple methods:

```python
from datetime import date

# Using period (relative)
google_news.period = '7d'   # Last 7 days
google_news.period = '1h'   # Last hour
google_news.period = '1m'   # Last month
google_news.period = '1y'   # Last year

# Using absolute dates
google_news.start_date = date(2024, 1, 1)
google_news.end_date = date(2024, 12, 31)

# Using tuples
google_news.start_date = (2024, 1, 1)
google_news.end_date = (2024, 12, 31)
```

## Available Topics

| Topic | Description |
|-------|-------------|
| `WORLD` | International news |
| `NATION` | Country-specific news |
| `BUSINESS` | Business and finance |
| `TECHNOLOGY` | Tech news |
| `ENTERTAINMENT` | Entertainment news |
| `SPORTS` | Sports news |
| `SCIENCE` | Science news |
| `HEALTH` | Health news |

## Supported Locales

Use lowercase codes:

```python
# Languages
'en', 'es', 'fr', 'de', 'pt', 'it', 'ja', 'ko', 'zh', 'ar', 'ru', ...

# Countries
'us', 'gb', 'ca', 'au', 'in', 'de', 'fr', 'es', 'br', 'mx', 'jp', ...
```

## Command-Line Interface

```bash
# Search
python gnewspaper.py "artificial intelligence"

# By topic
python gnewspaper.py --topic technology

# Different locale
python gnewspaper.py --language pt --country br

# With date filter
python gnewspaper.py --topic technology --period 7d

# JSON output
python gnewspaper.py --topic technology --json

# Clustered output
python gnewspaper.py --topic technology --clustered --json
```

### CLI Options

```
query               Search query (optional)
--topic, -t         Topic (world, nation, business, technology, etc.)
--language, -l      Language code (default: en)
--country, -c       Country code (default: us)
--max, -m           Max results (default: 10)
--period, -p        Time period (e.g., 7d, 1h)
--json, -j          Output as JSON
--clustered         Group articles by story
```

## Migration from GNews

Replace your import:

```python
# Before
from gnews import GNews

# After
from gnewspaper import GNews
```

The API methods are compatible. Article schema differences:

| GNews | GNewspaper |
|-------|------------|
| `published date` | `published_date` |
| `description` | (removed - always empty) |
| `publisher.href` | `publisher.favicon` |

Additional fields in GNewspaper:
- `published_timestamp` - Unix timestamp
- `authors` - List of author names
- `image` - Article thumbnail URL
- `clustered=True` parameter for story grouping

## Technical Details

### How It Works

GNewspaper uses Google's batchexecute protocol instead of RSS:

1. Fetches Google News HTML pages
2. Extracts embedded JSON data from `<script class="ds:N">` blocks
3. Parses protobuf-like JSON structures to extract articles
4. Encodes topic IDs using Freebase MIDs

### Topic ID Encoding

Topic IDs are base64-encoded protobuf messages containing:
- Freebase MID (e.g., `/m/07c1v` for Technology)
- Language code
- Country code

### Response Types

| Type | Source |
|------|--------|
| `gbres` | Homepage briefing |
| `gtsres` | Topic pages |
| `gsrres` | Search results |

## Files

```
gnewspaper.py   # Main library (single file)
README.md       # Documentation
tmp/            # Development files (not needed for distribution)
```

## Rate Limiting

Be respectful of Google's servers:
- Add delays between requests for bulk fetching
- Cache responses when possible
- The library respects `max_results` limits

## License

MIT License

## Disclaimer

For educational and research purposes. Respect Google's Terms of Service.
