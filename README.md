# SteamAchieve

A web-based Steam achievement tracking application that allows users to authenticate with their Steam account, view their game library, browse achievements (locked first, then unlocked), and discover guides for specific achievements using automated DuckDuckGo search.

## Features

- **Steam Authentication**: Secure login using Steam OpenID 2.0
- **Game Library**: View your recently played games with playtime statistics
- **Achievement Tracking**: Browse all achievements for your games
- **Smart Sorting**: Achievements are displayed locked first, then unlocked
- **Automated Guide Discovery**: Find achievement guides from multiple sources:
  - Steam Community
  - YouTube tutorials
  - Reddit discussions
  - Gaming wikis (Fandom, Wiki.gg, etc.)
  - Gaming sites (IGN, GameFAQs, etc.)
- **Intelligent Caching**:
  - Game library cached for 1 hour
  - Achievements cached for 30 minutes
  - Guide search results cached for 7 days
- **Rich Statistics**: View completion percentages, global unlock rates, and rarity labels

## Technology Stack

- **Backend**: Python 3.x + Flask
- **Frontend**: HTML5, CSS3, Bootstrap 5, Vanilla JavaScript
- **Database**: SQLite
- **APIs**:
  - Steam Web API
  - Steam OpenID 2.0
  - DuckDuckGo Search (DDGS)

## Installation

### Prerequisites

- Python 3.12 or higher
- pip package manager
- Steam Web API key ([Get one here](https://steamcommunity.com/dev/apikey))

### Setup

1. **Clone or download the repository**

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Copy `.env.example` to `.env` and fill in your Steam API key:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your Steam API key:
   ```
   FLASK_SECRET_KEY=your-secret-key-here
   STEAM_API_KEY=your-steam-api-key-here
   FLASK_ENV=development
   ```

5. **Initialize the database**
   ```bash
   python database.py
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Open your browser**

   Navigate to `http://localhost:5000`

## Usage

1. Click "Sign in with Steam" on the home page
2. Authorize the application through Steam
3. Browse your game library on the dashboard
4. Click on any game to view its achievements
5. Use the "Find Guides" button to discover guides for specific achievements
6. Filter achievements by status (All/Locked/Unlocked)
7. Search for specific achievements using the search bar

## Project Structure

```
SteamAchieve/
├── app.py                  # Main Flask application
├── config.py               # Configuration and environment variables
├── database.py             # Database setup and operations
├── steam_api.py            # Steam Web API wrapper
├── guide_search.py         # DuckDuckGo guide search integration
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment variables
├── utils/
│   ├── auth.py             # Steam OpenID authentication
│   ├── cache.py            # Caching utilities
│   └── search_helpers.py   # Search optimization helpers
├── templates/
│   ├── base.html           # Base template
│   ├── index.html          # Landing/login page
│   ├── dashboard.html      # Game library page
│   └── achievements.html   # Achievement viewer page
└── static/
    ├── css/
    │   └── style.css       # Custom Steam-themed styles
    └── js/
        ├── main.js         # Global utilities
        ├── games.js        # Game library functionality
        └── achievements.js # Achievement display and guide search
```

## Key Features

### Achievement Sorting

Achievements are **always displayed locked first, then unlocked**. Within each category:
- Locked achievements are sorted by rarity (rarest first based on global unlock %)
- Unlocked achievements are sorted by unlock time (most recent first)

### Guide Discovery System

The application uses DuckDuckGo Search to automatically find guides:
1. Checks cache first (7-day expiration)
2. Constructs optimized search query: `"[Game]" "[Achievement]" achievement guide walkthrough`
3. Searches multiple sources and categorizes results
4. Ranks by relevance score
5. Caches results for future use

Rate limiting: Maximum 5 searches per minute with 2-second courtesy delays

### Caching Strategy

- **Game Library**: 1 hour cache
- **Achievements**: 30 minutes cache
- **Guide Search**: 7 days cache
- Prevents duplicate API calls and improves performance

## API Endpoints

### Authentication
- `GET /auth/login` - Initiate Steam login
- `GET /auth/callback` - Handle Steam callback
- `GET /auth/logout` - Logout user

### Pages
- `GET /` - Home page
- `GET /dashboard` - Game library
- `GET /achievements/<app_id>` - Achievement viewer

### API
- `GET /api/games` - Get user's game library
- `GET /api/games/<app_id>/achievements` - Get achievements for a game
- `POST /api/achievement/guide/search` - Search for guides
- `GET /api/achievement/guide/cached` - Get cached guides

## Security Considerations

- Steam API keys stored in environment variables (never commit `.env`)
- Secure session management with Flask sessions
- Input validation and sanitization
- URL validation for guide search results
- HTTPS required in production
- XSS prevention for user-generated content

## Development

### Running in Development Mode

```bash
# Set environment
export FLASK_ENV=development  # On Windows: set FLASK_ENV=development

# Run with debug mode
python app.py
```

### Database Management

Initialize or reset database:
```bash
python database.py
```

Clean expired cache entries:
```python
from database import db
db.cleanup_expired_cache()
```

## Troubleshooting

### "STEAM_API_KEY must be set"
Make sure you've created a `.env` file and added your Steam API key.

### "Failed to fetch games. Profile may be private."
Ensure your Steam profile and game details are set to public in Steam privacy settings.

### "No guides found"
The DuckDuckGo search may not have found relevant results. Try clicking the fallback Steam Community search link.

### Rate limit errors
Wait 60 seconds before performing more guide searches. The app limits to 5 searches per minute.

## Contributing

This is a personal project built for learning purposes. Feel free to fork and modify for your own use.

## License

This project is provided as-is for educational purposes. Steam and the Steam logo are trademarks of Valve Corporation.

## Acknowledgments

- Steam Web API for game and achievement data
- DuckDuckGo for guide search functionality
- Bootstrap for UI components
- Font Awesome for icons
