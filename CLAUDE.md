# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SteamAchieve is a Flask web application for tracking Steam achievements. Users authenticate via Steam OpenID, view their game library, browse achievements (locked first, then unlocked), and discover achievement guides through DuckDuckGo search and AI-generated content via OpenRouter.

## Development Commands

```bash
# Run the application
python app.py

# Install dependencies
pip install -r requirements.txt

# Initialize/reset the database
python database.py
```

## Environment Setup

Create a `.env` file with:
```
FLASK_SECRET_KEY=your-secret-key-here
STEAM_API_KEY=your-steam-api-key-here
OPENROUTER_API_KEY=your-openrouter-api-key-here  # Optional, for AI guides
FLASK_ENV=development
DATABASE_URL=sqlite:///steamachieve.db
```

Get Steam API key from: https://steamcommunity.com/dev/apikey

## Architecture

### Core Modules

**app.py** - Flask routes and request handling
- Auth routes: `/auth/login`, `/auth/callback`, `/auth/logout`
- API routes: `/api/games`, `/api/games/<appid>/achievements`, `/api/achievement/guide/*`
- Uses `@require_login` decorator from `utils/auth.py` for protected routes

**steam_api.py** - Steam Web API wrapper (`SteamAPI` class)
- Fetches games, achievements, player data from Steam API
- `get_achievements_for_game()` merges player achievements with schema and global stats
- `sort_achievements_locked_first()` - core sorting logic (locked by rarity, unlocked by time)
- Global instance: `steam_api`

**database.py** - SQLite operations (`Database` class)
- Tables: `users`, `cached_games`, `achievement_guides`, `guide_search_cache`, `ai_generated_guides`, `user_guide_preferences`, `guide_bookmarks`
- Cache TTLs defined in `config.py`: games (1hr), achievements (30min), guides (7 days), AI guides (30 days)
- Global instance: `db`

**guide_search.py** - DuckDuckGo search (`GuideSearcher` class)
- Rate limited: 5 searches/minute with 2-second delays
- Uses `utils/search_helpers.py` for query building, filtering, ranking
- Global instance: `guide_searcher`

**ai_guide_generator.py** - AI guide generation (`AIGuideGenerator` class)
- Wraps `openrouter_api.py` for guide generation
- Caches AI guides in database
- Global instance: `ai_guide_generator`

**openrouter_api.py** - OpenRouter API client (`OpenRouterAPI` class)
- Uses model from `Config.OPENROUTER_MODEL` (currently `kwaipilot/kat-coder-pro:free`)
- Built-in rate limiting: 10/minute, 200/day
- Global instance: `openrouter_api`

**guide_aggregator.py** - Multi-source guide aggregation (`GuideAggregator` class)
- Combines: AI, DDGS search, Steam Community scraping, YouTube/Reddit search links
- Scores and ranks results by quality
- Global instance: `guide_aggregator`

**config.py** - Environment configuration (`Config` class)
- All settings from `.env` file
- Cache durations, rate limits, session config

### Data Flow

1. User authenticates via Steam OpenID (`utils/auth.py`)
2. Games fetched from Steam API, cached in `cached_games` table
3. Achievements fetched per-game, merged with schema and global stats
4. Guide searches check cache first, then query DDGS/AI, cache results

### Key Implementation Details

- **Achievement ordering**: Always locked first (sorted by rarity), then unlocked (sorted by unlock time)
- **Steam IDs**: 64-bit integers stored as strings
- **Achievement icons**: `http://cdn.steampowered.com/steamcommunity/public/images/apps/{appid}/{icon_hash}.jpg`
- **Game images**: Various formats from `https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/`

### Frontend

- Templates in `templates/`: `base.html`, `index.html`, `dashboard.html`, `achievements.html`, `locked_achievements.html`
- JavaScript in `static/js/`: `main.js`, `games.js`, `achievements.js`
- CSS: `static/css/style.css` (Steam-inspired theme: #171a21 background, #66c0f4 accent)

### Rate Limits

- Steam API: ~100,000 calls/day (use caching)
- DuckDuckGo: 5 searches/minute
- OpenRouter: 10 requests/minute, 200/day (free tier)
