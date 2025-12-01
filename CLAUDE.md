# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SteamAchieve is a Flask web application for tracking Steam achievements. Users authenticate with Steam OpenID, view their game library sorted by recently played, browse achievements (locked first, then unlocked), and access automated achievement guides discovered via DuckDuckGo search.

## Development Commands

### Running the Application
```bash
python app.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Environment Setup
Create a `.env` file with:
```
FLASK_SECRET_KEY=your-secret-key-here
STEAM_API_KEY=your-steam-api-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///steamachieve.db
```

Obtain Steam Web API key from: https://steamcommunity.com/dev/apikey

## Architecture

### Core Module Responsibilities

**app.py** - Main Flask application with routes and request handling
- Authentication routes: `/auth/login`, `/auth/callback`, `/auth/logout`
- API routes: `/api/games`, `/api/games/<appid>/achievements`
- Guide search routes: `/api/achievement/guide/search`, `/api/achievement/guide/cached`
- Session management and user profile display

**steam_api.py** - Steam Web API wrapper
- `get_owned_games(steam_id)` - Fetch user's game library
- `get_recently_played_games(steam_id)` - Get recently played games
- `get_player_achievements(steam_id, app_id)` - Fetch player achievements
- `get_achievement_schema(app_id)` - Get achievement metadata
- `get_global_achievement_stats(app_id)` - Fetch global unlock percentages
- Merges player data with schema data for complete achievement details

**guide_search.py** - DuckDuckGo-based guide discovery
- `search_achievement_guides(game_name, achievement_name, max_results=10)` - Automated guide search
- `build_search_query(game_name, achievement_name)` - Construct optimized search queries
- `filter_results(results)` - Rank results by relevance and source quality
- `categorize_source(url)` - Identify source type (YouTube, Reddit, Steam, Wiki)
- Multi-query strategy with fallback options
- Rate limiting: max 5 searches per minute

**database.py** - SQLite database operations
- Initialize and create tables: `users`, `cached_games`, `achievement_guides`, `guide_search_cache`
- CRUD operations for caching game data and guide search results
- Cache expiration logic (guides: 7 days, games: 1 hour, achievements: 30 minutes)

**utils/auth.py** - Steam OpenID 2.0 authentication helpers
**utils/cache.py** - Caching strategies for API responses
**utils/search_helpers.py** - Search query optimization and result filtering

### Database Schema

**users** - Steam user profiles (steam_id, persona_name, avatar_url, last_login)

**cached_games** - Cached game library data with playtime and last played timestamps

**achievement_guides** - Discovered guides with URL, title, snippet, source type, and search rank

**guide_search_cache** - DDGS search results cache with 7-day TTL to minimize duplicate searches

### Frontend Structure

**Templates** (templates/)
- `base.html` - Base template with navbar and Steam-themed UI
- `index.html` - Landing/login page
- `dashboard.html` - Game library display
- `achievements.html` - Achievement viewer with locked/unlocked sections
- Components: `game_card.html`, `achievement_card.html`

**JavaScript** (static/js/)
- `main.js` - Core application logic and initialization
- `games.js` - Game library loading, sorting, filtering
- `achievements.js` - Achievement display, filtering, guide search UI

**Styling** (static/css/style.css)
- Steam-inspired color scheme: #171a21 background, #66c0f4 primary accent
- Responsive design with breakpoints: mobile (<768px), tablet (768-1024px), desktop (>1024px)

## Key Implementation Details

### Achievement Ordering
Achievements are **always displayed locked first, then unlocked**. This is core functionality implemented in the achievement fetching and display logic.

### Guide Discovery System
Uses DuckDuckGo Search (DDGS) for automated guide discovery:
1. Check cache first (`guide_search_cache` table)
2. If cache miss, construct optimized query: `"[Game]" "[Achievement]" achievement guide walkthrough`
3. Execute DDGS search with multiple query variations as fallback
4. Categorize results by source (YouTube, Reddit, Steam Community, Wiki)
5. Store results in `achievement_guides` table
6. Cache search for 7 days to avoid duplicate searches
7. Display multiple guide options with preview snippets and source badges

Rate limiting is critical - max 5 searches/minute to avoid DDGS blocking.

### Steam Web API Usage
Key endpoints:
- `ISteamUser/GetPlayerSummaries/v2/` - User profile
- `IPlayerService/GetOwnedGames/v1/` - Game library with `include_appinfo=1`
- `IPlayerService/GetRecentlyPlayedGames/v1/` - Recent games
- `ISteamUserStats/GetPlayerAchievements/v1/` - Player achievement status
- `ISteamUserStats/GetSchemaForGame/v2/` - Achievement metadata (icons, descriptions)
- `ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/` - Global unlock stats

Rate limit: ~100,000 calls/day. Caching is essential.

### Caching Strategy
- Game library: 1 hour
- Achievements: 30 minutes
- Guide search results: 7 days
- Search cache prevents duplicate DDGS queries for same achievement

### Error Handling Requirements
- Private Steam profiles (return appropriate message)
- Games without achievements (show notification)
- API rate limits (exponential backoff)
- DDGS search failures (fallback to Steam Community links)
- Missing guide results (graceful "no guides found" message)

## Special Considerations

- All user inputs must be sanitized, especially for DDGS queries and guide URLs
- External links from DDGS must be validated to prevent XSS
- Session security requires proper Flask secret key in production
- Achievement icons use Steam CDN URLs: `http://cdn.steampowered.com/steamcommunity/public/images/apps/{appid}/{icon_hash}.jpg`
- Playtime is tracked in minutes by Steam API
- Steam uses 64-bit Steam IDs throughout

## Security

- Never commit `.env` file with API keys
- Use secure session cookies in production (HTTPS required)
- Sanitize all DDGS results before displaying
- Validate external URLs from guide searches
- Implement per-user rate limiting on guide searches to prevent abuse
- Filter inappropriate or malicious guide URLs from search results
