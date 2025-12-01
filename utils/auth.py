import re
from urllib.parse import urlencode, parse_qs, urlparse
from flask import request, session, url_for
import requests
from config import Config


def get_steam_login_url(return_url):
    """Generate Steam OpenID login URL"""
    params = {
        'openid.ns': 'http://specs.openid.net/auth/2.0',
        'openid.mode': 'checkid_setup',
        'openid.return_to': return_url,
        'openid.realm': request.host_url,
        'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
        'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select',
    }

    query_string = urlencode(params)
    return f"{Config.STEAM_OPENID_URL}?{query_string}"


def validate_openid_response(params):
    """Validate OpenID response from Steam"""

    # Change mode to check_authentication
    validation_params = dict(params)
    validation_params['openid.mode'] = 'check_authentication'

    try:
        response = requests.post(Config.STEAM_OPENID_URL, data=validation_params, timeout=10)
        response.raise_for_status()

        # Check if validation was successful
        if 'is_valid:true' in response.text:
            return True

        return False

    except requests.RequestException as e:
        print(f"OpenID validation failed: {e}")
        return False


def extract_steam_id(claimed_id):
    """Extract Steam ID from OpenID claimed_id URL"""
    # claimed_id format: https://steamcommunity.com/openid/id/STEAM_ID_HERE
    match = re.search(r'https://steamcommunity\.com/openid/id/(\d+)', claimed_id)

    if match:
        return match.group(1)

    return None


def handle_steam_callback():
    """Handle Steam OpenID callback"""

    # Get all query parameters
    params = request.args.to_dict()

    # Check if user canceled login
    if params.get('openid.mode') == 'cancel':
        return None, 'Login canceled'

    # Validate the response
    if not validate_openid_response(params):
        return None, 'Invalid OpenID response'

    # Extract Steam ID
    claimed_id = params.get('openid.claimed_id')
    if not claimed_id:
        return None, 'No claimed_id in response'

    steam_id = extract_steam_id(claimed_id)
    if not steam_id:
        return None, 'Failed to extract Steam ID'

    return steam_id, None


def is_user_logged_in():
    """Check if user is logged in"""
    return 'steam_id' in session


def get_current_user():
    """Get current logged in user's Steam ID"""
    return session.get('steam_id')


def login_user(steam_id):
    """Log in a user by storing Steam ID in session"""
    session['steam_id'] = steam_id
    session.permanent = True


def logout_user():
    """Log out the current user"""
    session.pop('steam_id', None)
    session.clear()


def require_login(f):
    """Decorator to require login for routes"""
    from functools import wraps
    from flask import redirect, url_for

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_user_logged_in():
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function
