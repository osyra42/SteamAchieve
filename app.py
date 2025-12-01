from flask import Flask, render_template, redirect, url_for, jsonify, request, session
from datetime import timedelta
from config import Config
from database import db
from steam_api import steam_api
from guide_search import guide_searcher
from utils.auth import (
    get_steam_login_url,
    handle_steam_callback,
    is_user_logged_in,
    get_current_user,
    login_user,
    logout_user,
    require_login
)

app = Flask(__name__)
app.config.from_object(Config)
app.permanent_session_lifetime = timedelta(seconds=Config.PERMANENT_SESSION_LIFETIME)

# Initialize database on startup
db.initialize()


# Routes
@app.route('/')
def index():
    """Home page - login or redirect to dashboard"""
    if is_user_logged_in():
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/auth/login')
def auth_login():
    """Initiate Steam OpenID login"""
    return_url = url_for('auth_callback', _external=True)
    steam_login_url = get_steam_login_url(return_url)
    return redirect(steam_login_url)


@app.route('/auth/callback')
def auth_callback():
    """Handle Steam OpenID callback"""
    steam_id, error = handle_steam_callback()

    if error:
        return render_template('index.html', error=error)

    # Login user
    login_user(steam_id)

    # Fetch and store user profile
    try:
        players = steam_api.get_player_summaries(steam_id)
        if players and len(players) > 0:
            player = players[0]
            db.upsert_user(
                steam_id=steam_id,
                persona_name=player.get('personaname'),
                profile_url=player.get('profileurl'),
                avatar_url=player.get('avatarfull')
            )
    except Exception as e:
        print(f"Failed to fetch user profile: {e}")

    return redirect(url_for('dashboard'))


@app.route('/auth/logout')
def auth_logout():
    """Logout user"""
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@require_login
def dashboard():
    """User dashboard with game library"""
    steam_id = get_current_user()
    user = db.get_user(steam_id)
    return render_template('dashboard.html', user=user)


@app.route('/achievements/<int:app_id>')
@require_login
def achievements(app_id):
    """Achievement viewer for a specific game"""
    steam_id = get_current_user()
    user = db.get_user(steam_id)
    return render_template('achievements.html', user=user, app_id=app_id)


@app.route('/achievement-hunter')
@require_login
def locked_achievements_page():
    """Achievement hunter page - discover locked achievements with guides"""
    steam_id = get_current_user()
    user = db.get_user(steam_id)
    return render_template('locked_achievements.html', user=user)


# API Routes
@app.route('/api/user/profile')
@require_login
def api_user_profile():
    """Get current user profile"""
    steam_id = get_current_user()
    user = db.get_user(steam_id)

    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    return jsonify({
        'success': True,
        'user': user
    })


@app.route('/api/games')
@require_login
def api_games():
    """Get user's game library"""
    steam_id = get_current_user()

    # Check cache first
    cached_games = db.get_cached_games(steam_id)

    if cached_games:
        return jsonify({
            'success': True,
            'games': cached_games,
            'from_cache': True
        })

    # Fetch from Steam API
    try:
        games = steam_api.get_owned_games(steam_id)

        if games is None:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch games. Profile may be private.'
            }), 400

        # Cache the games
        db.cache_games(steam_id, games)

        # Convert to list of dicts for JSON response with image URLs
        games_list = []
        for game in games:
            enriched_game = steam_api.enrich_game_with_images(game)
            games_list.append({
                'app_id': game.get('appid'),
                'name': game.get('name'),
                'img_icon_url': game.get('img_icon_url'),
                'img_logo_url': game.get('img_logo_url'),
                'playtime_forever': game.get('playtime_forever', 0),
                'playtime_2weeks': game.get('playtime_2weeks', 0),
                'last_played': game.get('rtime_last_played', 0),
                'images': enriched_game.get('images', {})
            })

        return jsonify({
            'success': True,
            'games': games_list,
            'from_cache': False
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/games/<int:app_id>/achievements')
@require_login
def api_achievements(app_id):
    """Get achievements for a specific game"""
    steam_id = get_current_user()

    try:
        result = steam_api.get_achievements_for_game(steam_id, app_id)

        if not result['success']:
            return jsonify(result), 400

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/achievement/guide/search', methods=['POST'])
@require_login
def api_guide_search():
    """Search for achievement guides"""
    data = request.get_json()

    app_id = data.get('app_id')
    game_name = data.get('game_name')
    achievement_name = data.get('achievement_name')

    if not all([app_id, game_name, achievement_name]):
        return jsonify({
            'success': False,
            'error': 'Missing required parameters'
        }), 400

    try:
        guides = guide_searcher.search_achievement_guides(
            app_id,
            game_name,
            achievement_name
        )

        return jsonify({
            'success': True,
            'guides': guides
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/achievement/guide/cached')
@require_login
def api_cached_guides():
    """Get cached guides for an achievement"""
    app_id = request.args.get('app_id', type=int)
    achievement_name = request.args.get('achievement_name')

    if not app_id or not achievement_name:
        return jsonify({
            'success': False,
            'error': 'Missing required parameters'
        }), 400

    try:
        guides = guide_searcher.get_cached_guides(app_id, achievement_name)

        return jsonify({
            'success': True,
            'guides': guides or []
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/locked-achievements')
@require_login
def api_locked_achievements():
    """Get all locked achievements across all games"""
    steam_id = get_current_user()

    try:
        # Get user's games
        games = steam_api.get_owned_games(steam_id)

        if not games:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch games'
            }), 400

        locked_achievements = []
        games_with_achievements = 0

        # Limit to first 20 games to avoid long response times
        max_games = request.args.get('max_games', 20, type=int)

        for game in games[:max_games]:
            app_id = game.get('appid')
            game_name = game.get('name')

            # Fetch achievements for this game
            result = steam_api.get_achievements_for_game(steam_id, app_id)

            if result.get('success'):
                games_with_achievements += 1
                achievements = result.get('achievements', [])

                # Filter locked achievements
                locked = [ach for ach in achievements if not ach.get('achieved')]

                # Add game info to each achievement
                for ach in locked:
                    ach['game_name'] = game_name
                    ach['app_id'] = app_id

                locked_achievements.extend(locked)

        # Sort by rarity (rarest first)
        locked_achievements.sort(key=lambda x: x.get('global_percent', 100))

        return jsonify({
            'success': True,
            'locked_achievements': locked_achievements,
            'total_locked': len(locked_achievements),
            'games_scanned': games_with_achievements,
            'total_games': len(games)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/achievement/guide/ai-generate', methods=['POST'])
@require_login
def api_ai_generate_guide():
    """Generate AI-powered guide for an achievement"""
    from ai_guide_generator import ai_guide_generator

    data = request.get_json()
    app_id = data.get('app_id')
    game_name = data.get('game_name')
    achievement_name = data.get('achievement_name')
    achievement_description = data.get('achievement_description', '')
    global_percent = data.get('global_percent')
    force_regenerate = data.get('force_regenerate', False)

    if not all([app_id, game_name, achievement_name]):
        return jsonify({
            'success': False,
            'error': 'Missing required parameters'
        }), 400

    try:
        result = ai_guide_generator.generate_guide(
            app_id=app_id,
            achievement_name=achievement_name,
            game_name=game_name,
            achievement_description=achievement_description,
            global_percent=global_percent,
            force_regenerate=force_regenerate
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/achievement/guide/multi-search', methods=['POST'])
@require_login
def api_multi_search_guides():
    """Search for guides from multiple sources"""
    from guide_aggregator import guide_aggregator

    data = request.get_json()
    app_id = data.get('app_id')
    game_name = data.get('game_name')
    achievement_name = data.get('achievement_name')
    achievement_description = data.get('achievement_description', '')
    global_percent = data.get('global_percent')
    sources = data.get('sources')  # None = all sources
    max_results = data.get('max_results', 15)

    if not all([app_id, game_name, achievement_name]):
        return jsonify({
            'success': False,
            'error': 'Missing required parameters'
        }), 400

    try:
        result = guide_aggregator.aggregate_guides(
            app_id=app_id,
            game_name=game_name,
            achievement_name=achievement_name,
            achievement_description=achievement_description,
            global_percent=global_percent,
            sources=sources,
            max_results=max_results
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/rate-limit-status')
@require_login
def api_ai_rate_limit():
    """Get current AI API rate limit status"""
    from ai_guide_generator import ai_guide_generator

    try:
        status = ai_guide_generator.get_rate_limit_status()
        return jsonify({
            'success': True,
            'rate_limit': status
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error='Internal server error'), 500


if __name__ == '__main__':
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please set STEAM_API_KEY in your .env file")
        exit(1)

    # Run the app
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000)
