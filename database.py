import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager
import json
from config import Config


class Database:
    """SQLite database manager for SteamAchieve"""

    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DATABASE_PATH

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def initialize(self):
        """Create all database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    steam_id TEXT UNIQUE NOT NULL,
                    persona_name TEXT,
                    profile_url TEXT,
                    avatar_url TEXT,
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Cached games table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cached_games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    steam_id TEXT NOT NULL,
                    app_id INTEGER NOT NULL,
                    name TEXT,
                    img_icon_url TEXT,
                    img_logo_url TEXT,
                    playtime_forever INTEGER,
                    playtime_2weeks INTEGER,
                    last_played TIMESTAMP,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (steam_id) REFERENCES users(steam_id),
                    UNIQUE(steam_id, app_id)
                )
            ''')

            # Achievement guides table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS achievement_guides (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id INTEGER NOT NULL,
                    achievement_name TEXT NOT NULL,
                    guide_title TEXT,
                    guide_content TEXT,
                    guide_snippet TEXT,
                    guide_url TEXT,
                    source TEXT,
                    search_rank INTEGER DEFAULT 0,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(app_id, achievement_name, guide_url)
                )
            ''')

            # Guide search cache table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS guide_search_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_query TEXT UNIQUE NOT NULL,
                    results_json TEXT,
                    result_count INTEGER DEFAULT 0,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            ''')

            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cached_games_steam_id ON cached_games(steam_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_achievement_guides_app_id ON achievement_guides(app_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_guide_search_cache_query ON guide_search_cache(search_query)')

    # User operations
    def upsert_user(self, steam_id, persona_name=None, profile_url=None, avatar_url=None):
        """Insert or update user information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (steam_id, persona_name, profile_url, avatar_url, last_login)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(steam_id) DO UPDATE SET
                    persona_name = excluded.persona_name,
                    profile_url = excluded.profile_url,
                    avatar_url = excluded.avatar_url,
                    last_login = excluded.last_login
            ''', (steam_id, persona_name, profile_url, avatar_url, datetime.now()))

    def get_user(self, steam_id):
        """Get user by steam_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE steam_id = ?', (steam_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # Game cache operations
    def cache_games(self, steam_id, games):
        """Cache user's game library"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Delete old cached games for this user
            cursor.execute('DELETE FROM cached_games WHERE steam_id = ?', (steam_id,))

            # Insert new games
            for game in games:
                cursor.execute('''
                    INSERT INTO cached_games
                    (steam_id, app_id, name, img_icon_url, img_logo_url,
                     playtime_forever, playtime_2weeks, last_played, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    steam_id,
                    game.get('appid'),
                    game.get('name'),
                    game.get('img_icon_url'),
                    game.get('img_logo_url'),
                    game.get('playtime_forever', 0),
                    game.get('playtime_2weeks', 0),
                    datetime.fromtimestamp(game['rtime_last_played']) if game.get('rtime_last_played') else None,
                    datetime.now()
                ))

    def get_cached_games(self, steam_id, max_age_seconds=None):
        """Get cached games for a user"""
        max_age_seconds = max_age_seconds or Config.CACHE_GAME_LIBRARY

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_time = datetime.now() - timedelta(seconds=max_age_seconds)

            cursor.execute('''
                SELECT * FROM cached_games
                WHERE steam_id = ? AND cached_at > ?
                ORDER BY last_played DESC
            ''', (steam_id, cutoff_time))

            rows = cursor.fetchall()
            return [dict(row) for row in rows] if rows else None

    # Achievement guide operations
    def cache_achievement_guides(self, app_id, achievement_name, guides):
        """Cache achievement guides"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            for rank, guide in enumerate(guides):
                cursor.execute('''
                    INSERT INTO achievement_guides
                    (app_id, achievement_name, guide_title, guide_snippet,
                     guide_url, source, search_rank, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(app_id, achievement_name, guide_url) DO UPDATE SET
                        guide_title = excluded.guide_title,
                        guide_snippet = excluded.guide_snippet,
                        search_rank = excluded.search_rank,
                        cached_at = excluded.cached_at,
                        updated_at = CURRENT_TIMESTAMP
                ''', (
                    app_id,
                    achievement_name,
                    guide.get('title'),
                    guide.get('snippet'),
                    guide.get('url'),
                    guide.get('source'),
                    rank,
                    datetime.now()
                ))

    def get_cached_guides(self, app_id, achievement_name, max_age_seconds=None):
        """Get cached guides for an achievement"""
        max_age_seconds = max_age_seconds or Config.CACHE_GUIDE_SEARCH

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_time = datetime.now() - timedelta(seconds=max_age_seconds)

            cursor.execute('''
                SELECT * FROM achievement_guides
                WHERE app_id = ? AND achievement_name = ? AND cached_at > ?
                ORDER BY search_rank ASC
            ''', (app_id, achievement_name, cutoff_time))

            rows = cursor.fetchall()
            return [dict(row) for row in rows] if rows else None

    # Search cache operations
    def cache_search_results(self, query, results):
        """Cache DuckDuckGo search results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            expires_at = datetime.now() + timedelta(seconds=Config.CACHE_GUIDE_SEARCH)
            results_json = json.dumps(results)

            cursor.execute('''
                INSERT INTO guide_search_cache (search_query, results_json, result_count, searched_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(search_query) DO UPDATE SET
                    results_json = excluded.results_json,
                    result_count = excluded.result_count,
                    searched_at = excluded.searched_at,
                    expires_at = excluded.expires_at
            ''', (query, results_json, len(results), datetime.now(), expires_at))

    def get_cached_search(self, query):
        """Get cached search results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM guide_search_cache
                WHERE search_query = ? AND expires_at > ?
            ''', (query, datetime.now()))

            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['results'] = json.loads(result['results_json'])
                return result
            return None

    def cleanup_expired_cache(self):
        """Remove expired cache entries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM guide_search_cache WHERE expires_at < ?', (datetime.now(),))
            deleted = cursor.rowcount
            return deleted


# Global database instance
db = Database()


def init_db():
    """Initialize the database"""
    db.initialize()
    print(f"Database initialized at {db.db_path}")


if __name__ == '__main__':
    init_db()
