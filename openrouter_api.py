"""
OpenRouter API wrapper for AI-powered achievement guide generation
Uses x-ai/grok-beta model (free tier)
"""

import requests
import time
from collections import deque
from datetime import datetime, timedelta
from config import Config


class RateLimiter:
    """Simple rate limiter for API calls"""

    def __init__(self, max_per_minute=10, max_per_day=200):
        self.max_per_minute = max_per_minute
        self.max_per_day = max_per_day
        self.minute_calls = deque()
        self.daily_calls = deque()

    def can_make_request(self):
        """Check if we can make a request without exceeding limits"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)

        # Clean old entries
        while self.minute_calls and self.minute_calls[0] < minute_ago:
            self.minute_calls.popleft()
        while self.daily_calls and self.daily_calls[0] < day_ago:
            self.daily_calls.popleft()

        return (len(self.minute_calls) < self.max_per_minute and
                len(self.daily_calls) < self.max_per_day)

    def record_request(self):
        """Record a new request"""
        now = datetime.now()
        self.minute_calls.append(now)
        self.daily_calls.append(now)

    def wait_time(self):
        """Get seconds to wait before next request"""
        if not self.can_make_request():
            if len(self.minute_calls) >= self.max_per_minute:
                oldest = self.minute_calls[0]
                return max(0, 61 - (datetime.now() - oldest).seconds)
            return 0
        return 0


class OpenRouterAPI:
    """OpenRouter AI API client"""

    def __init__(self, api_key=None):
        self.api_key = api_key or Config.OPENROUTER_API_KEY
        self.base_url = Config.OPENROUTER_BASE_URL
        self.model = Config.OPENROUTER_MODEL
        self.max_tokens = Config.OPENROUTER_MAX_TOKENS
        self.temperature = Config.OPENROUTER_TEMPERATURE
        self.rate_limiter = RateLimiter(
            max_per_minute=Config.AI_REQUESTS_PER_MINUTE,
            max_per_day=Config.AI_REQUESTS_PER_DAY
        )

    def _wait_for_rate_limit(self):
        """Wait if rate limit is exceeded"""
        wait_time = self.rate_limiter.wait_time()
        if wait_time > 0:
            print(f"Rate limit reached, waiting {wait_time} seconds...")
            time.sleep(wait_time)

    def _make_request(self, messages, max_tokens=None, temperature=None):
        """Make a request to OpenRouter API"""
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")

        # Check and wait for rate limit
        self._wait_for_rate_limit()

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://steamachieve.app',  # Optional: your site URL
            'X-Title': 'SteamAchieve'  # Optional: your app name
        }

        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': max_tokens or self.max_tokens,
            'temperature': temperature or self.temperature
        }

        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            self.rate_limiter.record_request()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"OpenRouter API request failed: {e}")
            return None

    def generate_achievement_guide(self, game_name, achievement_name,
                                   achievement_description, global_percent=None):
        """
        Generate a comprehensive achievement guide using AI

        Args:
            game_name: Name of the game
            achievement_name: Name of the achievement
            achievement_description: Description from Steam
            global_percent: Global unlock percentage (optional)

        Returns:
            dict: Generated guide with strategies, tips, difficulty, etc.
        """
        rarity = "rare" if global_percent and global_percent < 10 else "common"
        rarity_info = f"(Only {global_percent:.1f}% of players have unlocked this)" if global_percent else ""

        system_prompt = """You are an expert gaming guide writer specializing in achievement hunting.
Your guides are clear, concise, and actionable. Focus on practical strategies and specific steps.
Format your response as structured JSON with the following fields:
- difficulty_rating: Integer 1-10 (1=very easy, 10=extremely hard)
- estimated_time: String like "5-10 minutes", "2-3 hours", "20+ hours"
- strategies: Array of strings, each a different approach to unlock the achievement
- tips: Array of helpful tips and warnings
- summary: Brief 2-3 sentence overview of what the achievement requires"""

        user_prompt = f"""Generate a comprehensive achievement guide for:

Game: {game_name}
Achievement: {achievement_name}
Description: {achievement_description}
Rarity: {rarity} {rarity_info}

Provide specific, actionable strategies to unlock this achievement. Include any tips about timing, difficulty, or prerequisites."""

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]

        response = self._make_request(messages, max_tokens=1500)

        if not response or 'choices' not in response:
            return None

        try:
            content = response['choices'][0]['message']['content']

            # Try to parse as JSON first
            import json
            try:
                guide_data = json.loads(content)
            except json.JSONDecodeError:
                # If not JSON, structure the text response
                guide_data = {
                    'difficulty_rating': self._estimate_difficulty(global_percent),
                    'estimated_time': 'Varies',
                    'strategies': [content],
                    'tips': [],
                    'summary': content[:200] + '...' if len(content) > 200 else content
                }

            # Ensure all required fields exist
            guide_data.setdefault('difficulty_rating', self._estimate_difficulty(global_percent))
            guide_data.setdefault('estimated_time', 'Varies')
            guide_data.setdefault('strategies', [])
            guide_data.setdefault('tips', [])
            guide_data.setdefault('summary', '')

            return guide_data

        except Exception as e:
            print(f"Error parsing AI response: {e}")
            return None

    def _estimate_difficulty(self, global_percent):
        """Estimate difficulty based on global percentage"""
        if not global_percent:
            return 5

        if global_percent >= 75:
            return 1  # Very easy
        elif global_percent >= 50:
            return 3  # Easy
        elif global_percent >= 25:
            return 5  # Medium
        elif global_percent >= 10:
            return 7  # Hard
        elif global_percent >= 1:
            return 9  # Very hard
        else:
            return 10  # Extremely rare

    def batch_generate_guides(self, achievements, game_name, max_count=5):
        """
        Generate guides for multiple achievements (rate-limited)

        Args:
            achievements: List of achievement dicts
            game_name: Name of the game
            max_count: Maximum number to generate in one batch

        Returns:
            list: Generated guides
        """
        guides = []
        count = 0

        for ach in achievements:
            if count >= max_count:
                break

            if not self.rate_limiter.can_make_request():
                print(f"Rate limit reached after {count} guides, stopping batch generation")
                break

            guide = self.generate_achievement_guide(
                game_name=game_name,
                achievement_name=ach.get('name'),
                achievement_description=ach.get('description', ''),
                global_percent=ach.get('global_percent')
            )

            if guide:
                guides.append({
                    'achievement_name': ach.get('name'),
                    'guide': guide
                })
                count += 1

        return guides

    def get_rate_limit_status(self):
        """Get current rate limit status"""
        return {
            'can_make_request': self.rate_limiter.can_make_request(),
            'wait_time': self.rate_limiter.wait_time(),
            'minute_calls_remaining': self.rate_limiter.max_per_minute - len(self.rate_limiter.minute_calls),
            'daily_calls_remaining': self.rate_limiter.max_per_day - len(self.rate_limiter.daily_calls)
        }


# Global OpenRouter API instance
openrouter_api = OpenRouterAPI()
