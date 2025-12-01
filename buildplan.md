# Steam Achievement Tracker - Build Plan

## Project Overview

A web-based Steam achievement tracking application that allows users to authenticate with their Steam account, view their recently played games, browse achievements in a structured format (locked first, then unlocked), and access guides for specific achievements.

## Technology Stack

- **Backend**: Python 3.x + Flask
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **CDNs/Libraries**:
  - Bootstrap 5 or Tailwind CSS (for UI components)
  - Font Awesome (icons)
  - Axios or Fetch API (HTTP requests)
  - Optional: GSAP (animations)
- **APIs**:
  - Steam Web API (authentication, games, achievements)
  - Steam OpenID 2.0 (authentication)
  - DuckDuckGo Search (DDGS) - for finding achievement guides
- **Search Integration**:
  - DuckDuckGo Search Python library (`duckduckgo-search`)
  - Automated guide discovery from public sources
- **Database**: SQLite (for caching user data, session management, and guide search results)

---

## Core Features & Requirements

### 1. User Authentication
- Implement Steam OpenID 2.0 login
- Store user session using Flask sessions
- Retrieve and cache Steam ID (64-bit) after authentication
- Display user profile info (avatar, username)

### 2. Game Library Display
- Fetch user's owned games via Steam Web API
- Retrieve recently played games sorted by last played date
- Display game list with:
  - Game cover art
  - Game name
  - Last played date
  - Total playtime
- Implement sorting/filtering options

### 3. Achievement Tracking
- Fetch all achievements for a selected game
- Separate achievements into:
  - **Locked** (not yet achieved) - displayed first
  - **Unlocked** (achieved) - displayed after locked
- Display achievement details:
  - Icon/image
  - Title
  - Description
  - Unlock percentage (global stats)
  - Unlock date (for unlocked achievements)
  - Progress indicator (if available)
- Add toggle to show/hide completed achievements

### 4. Achievement Guide Integration (Automated Search)
- Add "View Guide" button for each achievement
- Implement **automated guide discovery** using DuckDuckGo Search (DDGS):
  - **Primary**: Auto-search free public guides using DDGS
    - Search query format: `"[Game Name]" "[Achievement Name]" achievement guide walkthrough`
    - Target sources: Steam Community, Reddit, GameFAQs, IGN, YouTube, gaming wikis
    - Filter and rank results by relevance
  - **Secondary**: Cached search results stored in database
  - **Tertiary**: Manual guide entry/storage for custom guides
  - **Fallback**: Direct links to Steam Community guide search
- Display multiple guide options in modal or side panel
- Show guide preview snippets from search results
- Support multiple content types:
  - Text guides (web pages)
  - Video guides (YouTube embeds)
  - Forum discussions (Reddit, Steam Community)
  - Wiki pages
- Rate-limit and cache search results to optimize performance
- Support rich text formatting (Markdown or HTML)

---

## API Endpoints & Data Flow

### Steam Web API Endpoints Required

1. **Authentication**
   - OpenID 2.0: `https://steamcommunity.com/openid/login`

2. **User Profile**
   - `ISteamUser/GetPlayerSummaries/v2/`
   - Params: `steamids`, `key`

3. **Game Library**
   - `IPlayerService/GetOwnedGames/v1/`
   - Params: `steamid`, `key`, `include_appinfo=1`, `include_played_free_games=1`
   - `IPlayerService/GetRecentlyPlayedGames/v1/`

4. **Game Achievements**
   - `ISteamUserStats/GetPlayerAchievements/v1/`
   - Params: `steamid`, `appid`, `key`
   - `ISteamUserStats/GetSchemaForGame/v2/` (game achievement schema)
   - Params: `appid`, `key`

5. **Global Achievement Stats**
   - `ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/`
   - Params: `gameid`

### Flask Backend Routes

```
/                           # Home page (login or dashboard)
/auth/login                 # Initiate Steam OpenID login
/auth/callback              # Handle Steam OpenID callback
/auth/logout                # Logout user
/api/games                  # Get user's games (recently played)
/api/games/<appid>/achievements  # Get achievements for a game
/api/achievement/guide/search    # Search for guides using DDGS
/api/achievement/guide/cached    # Get cached guide results
/api/user/profile           # Get user profile data
```

---

## Database Schema (SQLite)

### Table: users
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT UNIQUE NOT NULL,
    persona_name TEXT,
    profile_url TEXT,
    avatar_url TEXT,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table: cached_games
```sql
CREATE TABLE cached_games (
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
    FOREIGN KEY (steam_id) REFERENCES users(steam_id)
);
```

### Table: achievement_guides
```sql
CREATE TABLE achievement_guides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER NOT NULL,
    achievement_name TEXT NOT NULL,
    guide_title TEXT,
    guide_content TEXT,
    guide_snippet TEXT,  -- Preview snippet from search
    guide_url TEXT,
    source TEXT,  -- 'ddgs', 'manual', 'steam', 'youtube', 'reddit', 'wiki'
    search_rank INTEGER DEFAULT 0,  -- Relevance ranking
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(app_id, achievement_name, guide_url)  -- Prevent duplicate URLs
);
```

### Table: guide_search_cache
```sql
CREATE TABLE guide_search_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_query TEXT UNIQUE NOT NULL,
    results_json TEXT,  -- JSON array of search results
    result_count INTEGER DEFAULT 0,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP  -- Cache expiration (7 days)
);
```

---

## Project Structure

```
SteamAchieve/
│
├── app.py                  # Main Flask application
├── config.py               # Configuration (API keys, secrets)
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (Steam API key)
├── database.py             # Database initialization and queries
├── steam_api.py            # Steam API wrapper functions
├── guide_search.py         # DuckDuckGo guide search functions
│
├── static/
│   ├── css/
│   │   └── style.css       # Custom styles
│   ├── js/
│   │   ├── main.js         # Main JavaScript logic
│   │   ├── games.js        # Game library functionality
│   │   └── achievements.js # Achievement display logic
│   └── images/
│       └── logo.png        # App logo/assets
│
├── templates/
│   ├── base.html           # Base template with navbar/footer
│   ├── index.html          # Landing/login page
│   ├── dashboard.html      # User dashboard with game library
│   ├── achievements.html   # Achievement viewer for selected game
│   └── components/
│       ├── game_card.html  # Game card component
│       └── achievement_card.html  # Achievement card component
│
└── utils/
    ├── auth.py             # Authentication helpers
    ├── cache.py            # Caching utilities
    └── search_helpers.py   # Guide search optimization utilities
```

---

## Implementation Phases

### Phase 1: Project Setup & Authentication
**Estimated Time: 2-3 hours**

1. **Environment Setup**
   - Create virtual environment
   - Install dependencies: Flask, requests, python-dotenv, pySteamSignIn
   - Set up `.env` file with Steam API key
   - Initialize SQLite database

2. **Steam Authentication**
   - Implement Steam OpenID 2.0 login flow
   - Create auth routes (`/auth/login`, `/auth/callback`, `/auth/logout`)
   - Store user session and Steam ID
   - Create user profile fetching function

3. **Basic UI**
   - Create base template with navigation
   - Design landing page with "Login with Steam" button
   - Style authentication flow

**Deliverables:**
- Working authentication system
- User can log in and see their Steam profile

---

### Phase 2: Game Library Implementation
**Estimated Time: 3-4 hours**

1. **Backend API Integration**
   - Create `steam_api.py` wrapper functions:
     - `get_owned_games(steam_id)`
     - `get_recently_played_games(steam_id)`
   - Implement caching mechanism in database
   - Create Flask route `/api/games`

2. **Frontend Display**
   - Create dashboard page
   - Design game card components
   - Implement game grid/list view
   - Add sorting options (recently played, playtime, alphabetical)
   - Add search/filter functionality

3. **UI/UX Polish**
   - Add loading states
   - Implement error handling
   - Add game cover image fallbacks

**Deliverables:**
- Dashboard displaying user's game library
- Games sorted by recently played
- Responsive grid layout

---

### Phase 3: Achievement System
**Estimated Time: 4-5 hours**

1. **Backend Achievement Fetching**
   - Create achievement fetching functions:
     - `get_player_achievements(steam_id, app_id)`
     - `get_achievement_schema(app_id)`
     - `get_global_achievement_stats(app_id)`
   - Merge player achievements with schema data
   - Sort achievements: locked first, then unlocked
   - Create `/api/games/<appid>/achievements` endpoint

2. **Achievement Display Page**
   - Create achievements.html template
   - Design achievement card components
   - Implement locked/unlocked sections
   - Display achievement metadata:
     - Icon, title, description
     - Unlock percentage
     - Unlock date (if unlocked)
   - Add progress indicators

3. **Frontend Logic**
   - Create achievements.js
   - Implement achievement loading
   - Add filtering (locked/unlocked/all)
   - Add toggle for showing/hiding unlocked achievements
   - Add search functionality
   - Implement statistics display (total, unlocked %, etc.)

**Deliverables:**
- Achievement viewer for each game
- Achievements displayed in locked-then-unlocked order
- Rich achievement details with stats

---

### Phase 4: Automated Achievement Guide System with DDGS
**Estimated Time: 5-6 hours**

1. **Guide Data Model & Caching**
   - Set up `achievement_guides` table for storing found guides
   - Set up `guide_search_cache` table for caching DDGS results
   - Create CRUD operations for guides
   - Implement cache expiration logic (7-day TTL)

2. **DuckDuckGo Search Integration**
   - Install and configure `duckduckgo-search` library
   - Create `guide_search.py` module with functions:
     - `search_achievement_guides(game_name, achievement_name, max_results=10)`
     - `build_search_query(game_name, achievement_name)` - construct optimized queries
     - `filter_results(results)` - rank by relevance and source quality
     - `categorize_source(url)` - identify source type (YouTube, Reddit, Steam, etc.)
   - Implement multi-query strategy:
     - Primary: `"[Game]" "[Achievement]" achievement guide`
     - Secondary: `"[Game]" "[Achievement]" how to unlock`
     - Tertiary: `"[Game]" "[Achievement]" walkthrough tips`
   - Extract and store result snippets for previews
   - Implement rate limiting (max 5 searches per minute)

3. **Backend API Endpoints**
   - Create `/api/achievement/guide/search` endpoint:
     - Accepts: `game_name`, `achievement_name`, `app_id`
     - Returns: Array of guide results with URLs, titles, snippets, sources
     - Checks cache first, then performs DDGS search if needed
     - Stores results in database for future use
   - Create `/api/achievement/guide/cached` endpoint:
     - Returns previously cached guides for an achievement
   - Implement error handling for search failures

4. **Guide Display UI**
   - Create enhanced guide modal/side panel component
   - Add "Find Guides" button to achievement cards
   - Display loading state during search
   - Show multiple guide options in categorized list:
     - Video Guides (YouTube icons)
     - Text Guides (article icons)
     - Community Discussions (forum icons)
     - Wiki Pages (book icons)
   - Display guide preview snippets
   - Add source badges (Steam, Reddit, YouTube, etc.)
   - Implement "Open in New Tab" functionality
   - Add YouTube video embedding for video guides
   - Show guide relevance ranking

5. **Search Optimization & Quality**
   - Implement result filtering:
     - Prioritize official sources (Steam, game wikis)
     - Boost Reddit threads with high upvotes
     - Filter out low-quality or spam results
   - Add source credibility scoring
   - Implement duplicate URL detection
   - Cache successful searches for 7 days
   - Handle "no results found" gracefully

6. **Manual Guide Management (Optional)**
   - Create simple admin interface for adding manual guides
   - Allow users to submit guide URLs
   - Implement guide voting/rating system
   - Add "Report Broken Link" functionality

**Deliverables:**
- Fully automated guide discovery using DDGS
- Categorized guide results from multiple public sources
- Intelligent caching system to minimize searches
- Rich guide display with previews and source attribution
- Video guide embedding support

---

### Phase 5: Polish & Optimization
**Estimated Time: 2-3 hours**

1. **Caching & Performance**
   - Implement intelligent caching strategy
   - Add cache invalidation rules
   - Optimize API calls (batch requests where possible)
   - Add loading states and skeleton screens

2. **Error Handling**
   - Handle API rate limits
   - Handle private profiles
   - Handle games without achievements
   - Add user-friendly error messages

3. **UI/UX Enhancements**
   - Add animations and transitions
   - Implement dark mode toggle
   - Add achievement unlock sound effects (optional)
   - Improve mobile responsiveness
   - Add keyboard navigation

4. **Testing**
   - Test with various Steam profiles
   - Test error scenarios
   - Cross-browser testing
   - Mobile device testing

**Deliverables:**
- Polished, production-ready application
- Responsive across all devices
- Comprehensive error handling

---

## Required Dependencies (requirements.txt)

```txt
Flask==3.0.0
python-dotenv==1.0.0
requests==2.31.0
pySteamSignIn==1.1.1
duckduckgo-search==4.1.1
beautifulsoup4==4.12.2  # Optional: for parsing guide snippets
```

## Environment Variables (.env)

```env
FLASK_SECRET_KEY=your-secret-key-here
STEAM_API_KEY=your-steam-api-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///steamachieve.db
```

---

## Design Guidelines

### Color Scheme
- **Background**: #171a21
- **Primary**: #1b2838
- **Secondary**: #66c0f4
- **Tertiary**: #2a475e
- **Text**: #c7d5e0

### UI Components
- **Game Cards**: Hover effects, cover art, overlay with details
- **Achievement Cards**: Icon, title, description, progress bar
- **Modals**: Smooth animations, backdrop blur
- **Buttons**: Steam-style with hover states
- **Navigation**: Sticky header with user profile dropdown

### Responsive Breakpoints
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

---

## API Rate Limits & Considerations

### Steam Web API
- ~100,000 calls per day per API key
- Implement caching to minimize API calls
- Cache game library for 1 hour
- Cache achievements for 30 minutes
- Handle rate limit errors gracefully

### DuckDuckGo Search (DDGS)
- No official rate limits, but implement courtesy delays
- Rate limit: Max 5 searches per minute to avoid being blocked
- Implement exponential backoff on errors
- Cache all search results for 7 days minimum
- Use search cache before making new requests
- Consider implementing queue system for batch searches
- Handle search failures gracefully with fallback options

---

## Security Considerations

1. **API Key Protection**: Store in `.env`, never commit to version control
2. **Session Management**: Use secure Flask sessions with secret key
3. **Input Validation**: Sanitize all user inputs
4. **HTTPS**: Use HTTPS in production (Let's Encrypt)
5. **CORS**: Configure properly if using separate frontend
6. **XSS Prevention**: Sanitize guide content if allowing user submissions
7. **External Links**: Validate and sanitize URLs from DDGS results
8. **Rate Limiting**: Implement per-user search rate limits to prevent abuse
9. **Content Filtering**: Filter inappropriate or malicious guide URLs

---

## Future Enhancements

1. **Achievement Statistics**: Personal stats, completion rates, rarest achievements
2. **Game Recommendations**: Suggest games based on achievement patterns
3. **Social Features**: Compare achievements with friends, leaderboards
4. **Notifications**: Alert when friends unlock achievements
5. **Achievement Hunt Mode**: Focus mode for completing specific games
6. **Export Feature**: Export achievement data to CSV/JSON
7. **PWA Support**: Offline functionality, installable app
8. **Multi-language Support**: Localization for different regions
9. **Achievement Difficulty Rating**: Community-driven difficulty ratings
10. **Integration with Other Platforms**: Xbox, PlayStation, Epic Games

---

## Testing Strategy

### Unit Tests
- Test Steam API wrapper functions
- Test database operations
- Test authentication flow

### Integration Tests
- Test complete user journey
- Test API endpoints

### Manual Testing Checklist
- [ ] User can log in with Steam
- [ ] Games load and display correctly
- [ ] Achievements load for all games
- [ ] Locked achievements appear first
- [ ] Automated guide search works correctly
- [ ] Guide results are categorized properly
- [ ] Search cache system functions correctly
- [ ] Multiple guide sources are displayed
- [ ] Video guides embed properly
- [ ] Error handling works for edge cases
- [ ] App is responsive on all devices
- [ ] Cache system works correctly

---

## Deployment Options

### Local Development
```bash
python app.py
```

### Production Deployment
- **Heroku**: Easy deployment with Heroku CLI
- **DigitalOcean**: App Platform or Droplet
- **AWS**: Elastic Beanstalk or EC2
- **Vercel/Netlify**: For frontend (if separating frontend/backend)
- **PythonAnywhere**: Quick Python web app hosting

### Docker Deployment (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

---

## Success Metrics

- Successfully authenticate Steam users
- Load and display game library in < 2 seconds
- Display achievements accurately with proper sorting
- Automated guide search returns relevant results for 80%+ of achievements
- Guide results cached efficiently to minimize duplicate searches
- Mobile-responsive design
- Zero critical bugs in core functionality

---

## Getting Started

1. **Obtain Steam Web API Key**: https://steamcommunity.com/dev/apikey
2. **Clone/Create Project**: Set up directory structure
3. **Install Dependencies**: `pip install -r requirements.txt`
4. **Configure Environment**: Create `.env` file with API key
5. **Initialize Database**: Run database setup script
6. **Start Development Server**: `flask run`
7. **Test Authentication**: Log in with Steam account
8. **Iterate**: Build features phase by phase

---

## Resources & Documentation

- **Steam Web API Documentation**: https://steamcommunity.com/dev
- **Steam Web API Methods**: https://developer.valvesoftware.com/wiki/Steam_Web_API
- **pySteamSignIn Library**: https://github.com/viperfx/pySteamSignIn
- **Flask Documentation**: https://flask.palletsprojects.com/
- **OpenID 2.0 Specification**: https://openid.net/specs/openid-authentication-2_0.html
- **DuckDuckGo Search Python**: https://github.com/deedy5/duckduckgo_search
- **DDGS Documentation**: https://duckduckgo-search.readthedocs.io/

---

## Notes & Tips

- **Private Profiles**: Some Steam profiles are private - handle this gracefully
- **Games Without Achievements**: Not all games have achievements - show appropriate message
- **Achievement Icons**: Use Steam CDN URLs for achievement images
- **Playtime Tracking**: Steam tracks playtime in minutes
- **Rate Limiting**: Implement exponential backoff for API requests
- **Automated Guide Discovery**: DDGS searches free public sources (Steam Community, Reddit, YouTube, wikis)
- **Search Optimization**: Construct precise queries to get best results: `"game" "achievement" guide walkthrough`
- **Source Diversity**: Results will come from multiple platforms (videos, forums, articles, wikis)
- **Cache-First Strategy**: Always check cache before performing new searches
- **Testing Steam ID**: Use your own Steam ID for initial testing

---

## Questions to Consider

1. **Search Results Limit**: How many guide results should be displayed per achievement (default: 10)?
2. **Caching Strategy**: How frequently should game/achievement data refresh?
3. **Public Access**: Should non-logged-in users be able to search for Steam profiles?
4. **Admin Panel**: Do you need an admin interface for managing guides?
5. **Analytics**: Should the app track which achievements users are viewing guides for?

---

**Total Estimated Development Time**: 16-22 hours (including automated guide search system)

This build plan provides a comprehensive roadmap for building your Steam achievement tracker. The phased approach allows you to build incrementally and test each component before moving to the next phase.
