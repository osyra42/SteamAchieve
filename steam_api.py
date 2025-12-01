import requests
from config import Config


class SteamAPI:
    """Steam Web API wrapper"""

    BASE_URL = 'https://api.steampowered.com'
    CDN_URL = 'http://cdn.steampowered.com/steamcommunity/public/images/apps'
    STORE_CDN = 'https://cdn.cloudflare.steamstatic.com/steam/apps'

    def __init__(self, api_key=None):
        self.api_key = api_key or Config.STEAM_API_KEY
        if not self.api_key:
            raise ValueError("Steam API key is required")

    def _make_request(self, endpoint, params=None):
        """Make a request to Steam API"""
        if params is None:
            params = {}

        params['key'] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Steam API request failed: {e}")
            return None

    def get_player_summaries(self, steam_ids):
        """Get player profile information"""
        if isinstance(steam_ids, list):
            steam_ids = ','.join(str(sid) for sid in steam_ids)

        endpoint = 'ISteamUser/GetPlayerSummaries/v2/'
        params = {'steamids': steam_ids}

        data = self._make_request(endpoint, params)
        if data and 'response' in data and 'players' in data['response']:
            return data['response']['players']
        return None

    def get_owned_games(self, steam_id, include_appinfo=True, include_played_free_games=True):
        """Get user's owned games"""
        endpoint = 'IPlayerService/GetOwnedGames/v1/'
        params = {
            'steamid': steam_id,
            'include_appinfo': 1 if include_appinfo else 0,
            'include_played_free_games': 1 if include_played_free_games else 0
        }

        data = self._make_request(endpoint, params)
        if data and 'response' in data and 'games' in data['response']:
            return data['response']['games']
        return None

    def get_recently_played_games(self, steam_id, count=0):
        """Get recently played games (count=0 returns all)"""
        endpoint = 'IPlayerService/GetRecentlyPlayedGames/v1/'
        params = {
            'steamid': steam_id,
            'count': count
        }

        data = self._make_request(endpoint, params)
        if data and 'response' in data and 'games' in data['response']:
            return data['response']['games']
        return None

    def get_player_achievements(self, steam_id, app_id):
        """Get player's achievements for a specific game"""
        endpoint = 'ISteamUserStats/GetPlayerAchievements/v1/'
        params = {
            'steamid': steam_id,
            'appid': app_id
        }

        data = self._make_request(endpoint, params)
        if data and 'playerstats' in data:
            playerstats = data['playerstats']
            if playerstats.get('success'):
                return playerstats.get('achievements', [])
        return None

    def get_schema_for_game(self, app_id):
        """Get achievement schema (metadata) for a game"""
        endpoint = 'ISteamUserStats/GetSchemaForGame/v2/'
        params = {'appid': app_id}

        data = self._make_request(endpoint, params)
        if data and 'game' in data:
            game_data = data['game']
            return {
                'game_name': game_data.get('gameName'),
                'game_version': game_data.get('gameVersion'),
                'achievements': game_data.get('availableGameStats', {}).get('achievements', [])
            }
        return None

    def get_global_achievement_percentages(self, app_id):
        """Get global achievement unlock percentages"""
        endpoint = 'ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/'
        params = {'gameid': app_id}

        data = self._make_request(endpoint, params)
        if data and 'achievementpercentages' in data:
            return data['achievementpercentages'].get('achievements', [])
        return None

    def get_achievement_icon_url(self, app_id, icon_hash):
        """Construct achievement icon URL"""
        if not icon_hash:
            return None
        return f"{self.CDN_URL}/{app_id}/{icon_hash}.jpg"

    def get_game_header_image(self, app_id):
        """Get game header image (460x215) - used in library"""
        return f"{self.STORE_CDN}/{app_id}/header.jpg"

    def get_game_capsule_image(self, app_id, size='231x87'):
        """Get game capsule image - available sizes: 231x87, 184x69, 467x181"""
        return f"{self.STORE_CDN}/{app_id}/capsule_{size}.jpg"

    def get_game_hero_image(self, app_id):
        """Get game hero/banner image (1920x620)"""
        return f"{self.STORE_CDN}/{app_id}/library_hero.jpg"

    def get_game_logo(self, app_id):
        """Get game logo (transparent PNG)"""
        return f"{self.STORE_CDN}/{app_id}/logo.png"

    def get_game_library_capsule(self, app_id):
        """Get library capsule image (600x900) - vertical poster"""
        return f"{self.STORE_CDN}/{app_id}/library_600x900.jpg"

    def enrich_game_with_images(self, game):
        """Add image URLs to game data"""
        app_id = game.get('appid')
        if not app_id:
            return game

        game['images'] = {
            'header': self.get_game_header_image(app_id),
            'capsule': self.get_game_capsule_image(app_id),
            'capsule_small': self.get_game_capsule_image(app_id, '184x69'),
            'capsule_large': self.get_game_capsule_image(app_id, '467x181'),
            'hero': self.get_game_hero_image(app_id),
            'logo': self.get_game_logo(app_id),
            'library_capsule': self.get_game_library_capsule(app_id)
        }

        return game

    def merge_achievement_data(self, player_achievements, schema_achievements, global_percentages):
        """Merge player achievements with schema and global data"""
        if not player_achievements or not schema_achievements:
            return []

        # Create lookup dictionaries
        schema_dict = {ach['name']: ach for ach in schema_achievements}
        global_dict = {ach['name']: ach['percent'] for ach in (global_percentages or [])}

        merged = []
        for player_ach in player_achievements:
            name = player_ach['apiname']
            schema = schema_dict.get(name, {})

            # Ensure global_percent is always a float
            raw_percent = global_dict.get(name, 0)
            try:
                global_percent = float(raw_percent) if raw_percent is not None else 0.0
            except (ValueError, TypeError):
                global_percent = 0.0

            achievement = {
                'apiname': name,
                'achieved': player_ach.get('achieved', 0) == 1,
                'unlocktime': player_ach.get('unlocktime', 0),
                'name': player_ach.get('name', schema.get('displayName', name)),
                'description': schema.get('description', ''),
                'icon': schema.get('icon', ''),
                'icongray': schema.get('icongray', ''),
                'hidden': schema.get('hidden', 0) == 1,
                'global_percent': global_percent
            }

            merged.append(achievement)

        return merged

    def sort_achievements_locked_first(self, achievements):
        """Sort achievements: locked first, then unlocked"""
        locked = [ach for ach in achievements if not ach['achieved']]
        unlocked = [ach for ach in achievements if ach['achieved']]

        # Sort locked by global percentage (rarest first)
        locked.sort(key=lambda x: x.get('global_percent', 100))

        # Sort unlocked by unlock time (most recent first)
        unlocked.sort(key=lambda x: x.get('unlocktime', 0), reverse=True)

        return locked + unlocked

    def get_achievements_for_game(self, steam_id, app_id):
        """Get complete achievement data for a game (player + schema + global)"""
        player_achievements = self.get_player_achievements(steam_id, app_id)

        if player_achievements is None:
            return {
                'success': False,
                'error': 'Failed to fetch player achievements. Profile may be private or game has no achievements.'
            }

        schema = self.get_schema_for_game(app_id)
        global_percentages = self.get_global_achievement_percentages(app_id)

        if not schema:
            return {
                'success': False,
                'error': 'Failed to fetch achievement schema.'
            }

        merged = self.merge_achievement_data(
            player_achievements,
            schema['achievements'],
            global_percentages
        )

        sorted_achievements = self.sort_achievements_locked_first(merged)

        # Calculate statistics
        total = len(sorted_achievements)
        unlocked = sum(1 for ach in sorted_achievements if ach['achieved'])
        completion_percent = (unlocked / total * 100) if total > 0 else 0

        return {
            'success': True,
            'game_name': schema.get('game_name', ''),
            'achievements': sorted_achievements,
            'stats': {
                'total': total,
                'unlocked': unlocked,
                'locked': total - unlocked,
                'completion_percent': round(completion_percent, 1)
            }
        }


# Global Steam API instance
steam_api = SteamAPI()
