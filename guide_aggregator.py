"""
Guide aggregator - combines guides from multiple sources
- DuckDuckGo search results
- AI-generated guides
- Steam Community guides
- PCGamingWiki
- TrueAchievements
- Reddit
- YouTube
"""

import re
import requests
from bs4 import BeautifulSoup
from guide_search import guide_searcher
from ai_guide_generator import ai_guide_generator
from database import db


class GuideAggregator:
    """Aggregate achievement guides from multiple sources"""

    def __init__(self):
        self.sources = {
            'ai': self._get_ai_guide,
            'ddgs': self._get_ddgs_results,
            'steam_community': self._scrape_steam_community,
            'pcgamingwiki': self._scrape_pcgamingwiki,
            'youtube': self._search_youtube,
            'reddit': self._search_reddit
        }

    def aggregate_guides(self, app_id, game_name, achievement_name,
                        achievement_description='', global_percent=None,
                        sources=None, max_results=15):
        """
        Aggregate guides from multiple sources

        Args:
            app_id: Steam app ID
            game_name: Game name
            achievement_name: Achievement name
            achievement_description: Achievement description
            global_percent: Global unlock percentage
            sources: List of source names to use (None = all)
            max_results: Maximum total results to return

        Returns:
            dict: Aggregated guides with metadata
        """
        if sources is None:
            sources = ['ai', 'ddgs', 'steam_community', 'youtube']

        all_guides = []
        source_counts = {}

        for source in sources:
            if source in self.sources:
                try:
                    guides = self.sources[source](
                        app_id, game_name, achievement_name,
                        achievement_description, global_percent
                    )
                    if guides:
                        all_guides.extend(guides)
                        source_counts[source] = len(guides)
                except Exception as e:
                    print(f"Error fetching from {source}: {e}")
                    source_counts[source] = 0

        # Rank and score guides
        scored_guides = self._score_and_rank_guides(all_guides)

        # Limit results
        top_guides = scored_guides[:max_results]

        return {
            'success': True,
            'guides': top_guides,
            'total_found': len(all_guides),
            'sources_used': source_counts,
            'filtered_count': len(top_guides)
        }

    def _get_ai_guide(self, app_id, game_name, achievement_name,
                     achievement_description, global_percent):
        """Get AI-generated guide"""
        result = ai_guide_generator.generate_guide(
            app_id=app_id,
            achievement_name=achievement_name,
            game_name=game_name,
            achievement_description=achievement_description,
            global_percent=global_percent
        )

        if result.get('success'):
            guide_data = result['guide']
            return [{
                'source': 'ai_generated',
                'type': 'ai',
                'title': f'AI Guide: {achievement_name}',
                'content': guide_data.get('summary', ''),
                'url': None,  # AI guides are local
                'difficulty': guide_data.get('difficulty_rating'),
                'estimated_time': guide_data.get('estimated_time'),
                'strategies': guide_data.get('strategies', []),
                'tips': guide_data.get('tips', []),
                'quality_score': 85,  # AI guides get high base score
                'from_cache': result.get('from_cache', False)
            }]

        return []

    def _get_ddgs_results(self, app_id, game_name, achievement_name,
                         achievement_description, global_percent):
        """Get DuckDuckGo search results"""
        # Check cache first
        cached_guides = db.get_cached_guides(app_id, achievement_name)
        if cached_guides:
            return [{
                'source': guide.get('source', 'ddgs'),
                'type': 'external',
                'title': guide.get('guide_title'),
                'snippet': guide.get('guide_snippet'),
                'url': guide.get('guide_url'),
                'quality_score': 70 - guide.get('search_rank', 0) * 5,
                'from_cache': True
            } for guide in cached_guides]

        # Perform new search
        try:
            results = guide_searcher.search_guides(game_name, achievement_name, max_results=10)
            if results:
                # Cache the results
                db.cache_achievement_guides(app_id, achievement_name, results)

                return [{
                    'source': result.get('source', 'ddgs'),
                    'type': 'external',
                    'title': result.get('title'),
                    'snippet': result.get('snippet'),
                    'url': result.get('url'),
                    'quality_score': 70 - idx * 5,
                    'from_cache': False
                } for idx, result in enumerate(results)]
        except Exception as e:
            print(f"DDGS search failed: {e}")

        return []

    def _scrape_steam_community(self, app_id, game_name, achievement_name,
                                achievement_description, global_percent):
        """Scrape Steam Community guides (public, no API key needed)"""
        guides = []
        try:
            # Search Steam Community guides
            search_url = f"https://steamcommunity.com/app/{app_id}/guides/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find guide links
                guide_links = soup.find_all('a', class_='workshopItemTitle')[:5]

                for link in guide_links:
                    title = link.get_text(strip=True)
                    url = link.get('href')

                    # Filter by achievement name relevance
                    if achievement_name.lower() in title.lower() or 'achievement' in title.lower():
                        guides.append({
                            'source': 'steam_community',
                            'type': 'steam_guide',
                            'title': title,
                            'url': url,
                            'snippet': 'Steam Community Guide',
                            'quality_score': 80,  # Steam guides are usually high quality
                            'from_cache': False
                        })

        except Exception as e:
            print(f"Error scraping Steam Community: {e}")

        return guides

    def _scrape_pcgamingwiki(self, app_id, game_name, achievement_name,
                            achievement_description, global_percent):
        """Scrape PCGamingWiki for achievement info"""
        guides = []
        try:
            # PCGamingWiki search
            search_term = game_name.replace(' ', '_')
            wiki_url = f"https://www.pcgamingwiki.com/wiki/{search_term}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(wiki_url, headers=headers, timeout=10)
            if response.status_code == 200:
                # Simple check if page has achievement section
                if 'achievement' in response.text.lower():
                    guides.append({
                        'source': 'pcgamingwiki',
                        'type': 'wiki',
                        'title': f'{game_name} - PCGamingWiki',
                        'url': wiki_url,
                        'snippet': 'Technical and achievement information on PCGamingWiki',
                        'quality_score': 75,
                        'from_cache': False
                    })

        except Exception as e:
            print(f"Error scraping PCGamingWiki: {e}")

        return guides

    def _search_youtube(self, app_id, game_name, achievement_name,
                       achievement_description, global_percent):
        """Generate YouTube search URLs (no API key needed)"""
        # Create YouTube search URL
        query = f"{game_name} {achievement_name} achievement guide"
        safe_query = requests.utils.quote(query)
        youtube_url = f"https://www.youtube.com/results?search_query={safe_query}"

        return [{
            'source': 'youtube',
            'type': 'video',
            'title': f'YouTube: {achievement_name} Guide',
            'url': youtube_url,
            'snippet': 'Video guides and walkthroughs on YouTube',
            'quality_score': 65,
            'from_cache': False
        }]

    def _search_reddit(self, app_id, game_name, achievement_name,
                      achievement_description, global_percent):
        """Generate Reddit search URLs"""
        query = f"{game_name} {achievement_name}"
        safe_query = requests.utils.quote(query)
        reddit_url = f"https://www.reddit.com/search/?q={safe_query}"

        return [{
            'source': 'reddit',
            'type': 'community',
            'title': f'Reddit Discussions: {achievement_name}',
            'url': reddit_url,
            'snippet': 'Community discussions and tips on Reddit',
            'quality_score': 60,
            'from_cache': False
        }]

    def _score_and_rank_guides(self, guides):
        """
        Score and rank guides by quality

        Quality factors:
        - Source type (AI, Steam Community, etc.)
        - Relevance (title/content matching)
        - Freshness (not implemented yet)
        - User ratings (not implemented yet)
        """
        # Sort by quality score (already assigned per source)
        guides.sort(key=lambda x: x.get('quality_score', 0), reverse=True)

        # Add rank
        for idx, guide in enumerate(guides):
            guide['rank'] = idx + 1

        return guides


# Global guide aggregator instance
guide_aggregator = GuideAggregator()
