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

        # Convert to list of dicts for JSON response
        games_list = []
        for game in games:
            games_list.append({
                'app_id': game.get('appid'),
                'name': game.get('name'),
                'img_icon_url': game.get('img_icon_url'),
                'img_logo_url': game.get('img_logo_url'),
                'playtime_forever': game.get('playtime_forever', 0),
                'playtime_2weeks': game.get('playtime_2weeks', 0),
                'last_played': game.get('rtime_last_played', 0)
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
