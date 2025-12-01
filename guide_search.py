import time
from datetime import datetime
from duckduckgo_search import DDGS
from config import Config
from database import db
from utils.search_helpers import (
    build_search_query,
    build_fallback_queries,
    filter_and_rank_results,
    deduplicate_results
)


class GuideSearcher:
    """DuckDuckGo-based achievement guide search"""

    def __init__(self):
        self.last_search_time = 0
        self.search_count = 0
        self.search_times = []

    def _rate_limit_check(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()

        # Remove search times older than 1 minute
        self.search_times = [t for t in self.search_times if current_time - t < 60]

        # Check if we've exceeded the rate limit
        if len(self.search_times) >= Config.DDGS_MAX_SEARCHES_PER_MINUTE:
            # Calculate wait time
            oldest_search = self.search_times[0]
            wait_time = 60 - (current_time - oldest_search)

            if wait_time > 0:
                print(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)

                # Clear old times after waiting
                current_time = time.time()
                self.search_times = [t for t in self.search_times if current_time - t < 60]

        # Add courtesy delay between searches
        if self.last_search_time > 0:
            elapsed = current_time - self.last_search_time
            if elapsed < 2:  # Minimum 2 seconds between searches
                time.sleep(2 - elapsed)

    def search_guides(self, game_name, achievement_name, max_results=None):
        """Search for achievement guides using DuckDuckGo"""
        max_results = max_results or Config.DDGS_MAX_RESULTS

        # Check cache first
        query = build_search_query(game_name, achievement_name)
        cached = db.get_cached_search(query)

        if cached:
            print(f"Using cached search results for: {query}")
            return cached['results']

        # Rate limit check
        self._rate_limit_check()

        # Perform search
        try:
            print(f"Searching DuckDuckGo: {query}")

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results * 2))

            # Update rate limit tracking
            current_time = time.time()
            self.search_times.append(current_time)
            self.last_search_time = current_time

            # If no results, try fallback queries
            if not results:
                print("No results from primary query, trying fallbacks...")
                fallback_queries = build_fallback_queries(game_name, achievement_name)

                for fallback_query in fallback_queries:
                    self._rate_limit_check()

                    print(f"Trying fallback: {fallback_query}")
                    with DDGS() as ddgs:
                        results = list(ddgs.text(fallback_query, max_results=max_results * 2))

                    current_time = time.time()
                    self.search_times.append(current_time)
                    self.last_search_time = current_time

                    if results:
                        query = fallback_query  # Use fallback query for caching
                        break

            # Filter and rank results
            filtered = filter_and_rank_results(results, game_name, achievement_name)

            # Remove duplicates
            unique = deduplicate_results(filtered)

            # Limit to max_results
            final_results = unique[:max_results]

            # Cache the results
            db.cache_search_results(query, final_results)

            return final_results

        except Exception as e:
            print(f"Search failed: {e}")
            return []

    def search_achievement_guides(self, app_id, game_name, achievement_name):
        """Search and cache guides for a specific achievement"""

        # Check if we have cached guides
        cached_guides = db.get_cached_guides(app_id, achievement_name)

        if cached_guides:
            print(f"Using cached guides for {achievement_name}")
            return cached_guides

        # Perform search
        results = self.search_guides(game_name, achievement_name)

        if not results:
            # Fallback: return Steam Community search link
            steam_search_url = f"https://steamcommunity.com/app/{app_id}/guides/?searchText={achievement_name.replace(' ', '+')}"
            results = [{
                'title': f'Search Steam Community Guides for {achievement_name}',
                'url': steam_search_url,
                'snippet': 'No guides found. Click to search Steam Community.',
                'source': 'steam',
                'relevance_score': 0
            }]

        # Cache the guides
        db.cache_achievement_guides(app_id, achievement_name, results)

        return results

    def get_cached_guides(self, app_id, achievement_name):
        """Get cached guides without performing a search"""
        return db.get_cached_guides(app_id, achievement_name)


# Global searcher instance
guide_searcher = GuideSearcher()
