import re
from urllib.parse import urlparse


def build_search_query(game_name, achievement_name):
    """Build optimized search query for achievement guides"""
    # Clean up the names
    game_clean = game_name.strip()
    achievement_clean = achievement_name.strip()

    # Primary query format
    query = f'"{game_clean}" "{achievement_clean}" achievement guide walkthrough'
    return query


def build_fallback_queries(game_name, achievement_name):
    """Build fallback queries if primary search fails"""
    game_clean = game_name.strip()
    achievement_clean = achievement_name.strip()

    queries = [
        f'"{game_clean}" "{achievement_clean}" how to unlock',
        f'"{game_clean}" "{achievement_clean}" tips walkthrough',
        f'{game_clean} {achievement_clean} achievement guide',
        f'{game_clean} {achievement_clean} steam guide'
    ]

    return queries


def categorize_source(url):
    """Categorize the source of a guide URL"""
    if not url:
        return 'unknown'

    domain = urlparse(url).netloc.lower()

    # YouTube
    if 'youtube.com' in domain or 'youtu.be' in domain:
        return 'youtube'

    # Reddit
    if 'reddit.com' in domain:
        return 'reddit'

    # Steam Community
    if 'steamcommunity.com' in domain:
        return 'steam'

    # Gaming wikis
    if any(wiki in domain for wiki in ['fandom.com', 'wikia.com', 'wiki.gg', 'gamepedia.com']):
        return 'wiki'

    # Gaming news/guide sites
    if any(site in domain for site in ['ign.com', 'gamespot.com', 'gamefaqs.com', 'polygon.com']):
        return 'gaming_site'

    # Blogs and other
    return 'article'


def get_source_priority(source):
    """Get priority score for source type (lower is better)"""
    priorities = {
        'steam': 1,
        'wiki': 2,
        'youtube': 3,
        'gaming_site': 4,
        'reddit': 5,
        'article': 6,
        'unknown': 7
    }
    return priorities.get(source, 10)


def is_url_valid(url):
    """Validate URL for security"""
    if not url:
        return False

    try:
        parsed = urlparse(url)

        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False

        # Only allow http/https
        if parsed.scheme not in ['http', 'https']:
            return False

        # Block suspicious patterns
        suspicious_patterns = [
            r'javascript:',
            r'data:',
            r'file:',
            r'ftp:',
        ]

        url_lower = url.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, url_lower):
                return False

        return True

    except Exception:
        return False


def sanitize_snippet(snippet, max_length=200):
    """Sanitize and truncate snippet text"""
    if not snippet:
        return ''

    # Remove excessive whitespace
    snippet = re.sub(r'\s+', ' ', snippet).strip()

    # Truncate if too long
    if len(snippet) > max_length:
        snippet = snippet[:max_length].rsplit(' ', 1)[0] + '...'

    return snippet


def filter_and_rank_results(results, game_name, achievement_name):
    """Filter and rank search results by relevance"""
    if not results:
        return []

    filtered = []

    for result in results:
        url = result.get('href') or result.get('url')

        # Skip invalid URLs
        if not is_url_valid(url):
            continue

        # Extract data
        title = result.get('title', '')
        snippet = sanitize_snippet(result.get('body') or result.get('snippet', ''))

        # Categorize source
        source = categorize_source(url)

        # Calculate relevance score
        relevance_score = calculate_relevance_score(
            title, snippet, url, game_name, achievement_name
        )

        filtered.append({
            'title': title,
            'url': url,
            'snippet': snippet,
            'source': source,
            'relevance_score': relevance_score
        })

    # Sort by relevance score (higher is better), then by source priority
    filtered.sort(key=lambda x: (x['relevance_score'], -get_source_priority(x['source'])), reverse=True)

    return filtered


def calculate_relevance_score(title, snippet, url, game_name, achievement_name):
    """Calculate relevance score based on keyword matches"""
    score = 0

    title_lower = title.lower()
    snippet_lower = snippet.lower()
    url_lower = url.lower()
    game_lower = game_name.lower()
    achievement_lower = achievement_name.lower()

    # Game name in title
    if game_lower in title_lower:
        score += 10

    # Achievement name in title
    if achievement_lower in title_lower:
        score += 10

    # Both in title
    if game_lower in title_lower and achievement_lower in title_lower:
        score += 5

    # Keywords in title
    guide_keywords = ['guide', 'walkthrough', 'how to', 'unlock', 'achievement', 'tutorial']
    for keyword in guide_keywords:
        if keyword in title_lower:
            score += 2

    # Game name in snippet
    if game_lower in snippet_lower:
        score += 3

    # Achievement name in snippet
    if achievement_lower in snippet_lower:
        score += 3

    # Game name in URL
    if game_lower.replace(' ', '') in url_lower.replace('-', '').replace('_', ''):
        score += 2

    return score


def deduplicate_results(results):
    """Remove duplicate URLs from results"""
    seen_urls = set()
    unique = []

    for result in results:
        url = result.get('url', '')

        # Normalize URL for comparison
        normalized = url.lower().rstrip('/')

        if normalized not in seen_urls:
            seen_urls.add(normalized)
            unique.append(result)

    return unique
