# Database Reset Instructions

## Issue Fixed
The database schema was outdated and didn't include the new image columns. The database has been reset with the correct schema.

## What Was Done
1. Removed old `steamachieve.db` file
2. Recreated database with new schema including:
   - Image columns in `cached_games` table
   - New `ai_generated_guides` table
   - New `user_guide_preferences` table
   - New `guide_bookmarks` table

## If You Need to Reset Again

Run these commands:
```bash
# Remove old database
python -c "import os; os.remove('steamachieve.db') if os.path.exists('steamachieve.db') else None"

# Create new database
python database.py
```

Or use this single command:
```bash
python -c "import os; os.remove('steamachieve.db') if os.path.exists('steamachieve.db') else None" && python database.py
```

## Database Schema

### Tables Created
1. **users** - Steam user profiles
2. **cached_games** - Game library with image URLs (NEW COLUMNS)
3. **achievement_guides** - Cached guides from web search
4. **guide_search_cache** - DuckDuckGo search cache
5. **ai_generated_guides** - AI-generated achievement guides (NEW)
6. **user_guide_preferences** - User preferences for guide types (NEW)
7. **guide_bookmarks** - Bookmarked guides (NEW)

### cached_games Columns
- id
- steam_id
- app_id
- name
- img_icon_url
- img_logo_url
- **header_image** ← NEW
- **capsule_image** ← NEW
- **hero_image** ← NEW
- **logo_image** ← NEW
- **library_capsule** ← NEW
- playtime_forever
- playtime_2weeks
- last_played
- cached_at

## Note
After reset, users will need to:
1. Log in again with Steam
2. Game library will be cached on first load
3. Achievement data will be fetched fresh

The reset does NOT affect:
- Steam authentication (uses sessions)
- Any code or configuration
- Just clears the local cache

## Verification
Run to verify schema:
```bash
python -c "import sqlite3; conn = sqlite3.connect('steamachieve.db'); cursor = conn.cursor(); cursor.execute('PRAGMA table_info(cached_games)'); [print(row[1]) for row in cursor.fetchall()]"
```

Should show all columns including the new image columns.
