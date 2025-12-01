from functools import wraps
from datetime import datetime, timedelta


def cache_result(cache_func, get_cache_func, cache_time_seconds):
    """
    Decorator factory for caching function results

    Args:
        cache_func: Function to cache the result (e.g., db.cache_games)
        get_cache_func: Function to retrieve cached result (e.g., db.get_cached_games)
        cache_time_seconds: Cache duration in seconds
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Try to get cached result
            cached = get_cache_func(*args, max_age_seconds=cache_time_seconds)

            if cached is not None:
                return cached

            # No cache, call original function
            result = f(*args, **kwargs)

            # Cache the result
            if result is not None:
                cache_func(*args, result)

            return result

        return wrapped
    return decorator


def format_playtime(minutes):
    """Format playtime in minutes to readable string"""
    if minutes < 60:
        return f"{minutes}m"

    hours = minutes / 60
    if hours < 100:
        return f"{hours:.1f}h"

    return f"{int(hours)}h"


def format_timestamp(timestamp):
    """Format Unix timestamp to readable date"""
    if not timestamp:
        return "Never"

    try:
        dt = datetime.fromtimestamp(timestamp)
        now = datetime.now()

        # If today
        if dt.date() == now.date():
            return f"Today at {dt.strftime('%H:%M')}"

        # If yesterday
        if dt.date() == (now - timedelta(days=1)).date():
            return f"Yesterday at {dt.strftime('%H:%M')}"

        # If within a week
        if (now - dt).days < 7:
            return dt.strftime('%A at %H:%M')

        # Otherwise
        return dt.strftime('%b %d, %Y')

    except Exception:
        return "Unknown"


def is_cache_expired(cached_at, max_age_seconds):
    """Check if cache entry is expired"""
    if not cached_at:
        return True

    try:
        if isinstance(cached_at, str):
            cached_at = datetime.fromisoformat(cached_at)

        age = (datetime.now() - cached_at).total_seconds()
        return age > max_age_seconds

    except Exception:
        return True


def get_cache_age_string(cached_at):
    """Get human-readable cache age"""
    if not cached_at:
        return "Unknown"

    try:
        if isinstance(cached_at, str):
            cached_at = datetime.fromisoformat(cached_at)

        age = (datetime.now() - cached_at).total_seconds()

        if age < 60:
            return f"{int(age)} seconds ago"
        elif age < 3600:
            return f"{int(age / 60)} minutes ago"
        elif age < 86400:
            return f"{int(age / 3600)} hours ago"
        else:
            return f"{int(age / 86400)} days ago"

    except Exception:
        return "Unknown"
