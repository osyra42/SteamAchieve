/**
 * Game Cache Module - Manages localStorage caching for game achievement data
 */

const GameCache = {
    CACHE_KEY: 'steamachieve_games_cache',
    CACHE_TIMESTAMP_KEY: 'steamachieve_cache_timestamp',
    CACHE_DURATION: 24 * 60 * 60 * 1000, // 24 hours in milliseconds

    /**
     * Get cached games data
     * @returns {Array|null} Cached games array or null if not found/expired
     */
    getGames: function() {
        try {
            const timestamp = localStorage.getItem(this.CACHE_TIMESTAMP_KEY);
            if (!timestamp) return null;

            // Check if cache is expired
            const age = Date.now() - parseInt(timestamp);
            if (age > this.CACHE_DURATION) {
                this.clear();
                return null;
            }

            const data = localStorage.getItem(this.CACHE_KEY);
            return data ? JSON.parse(data) : null;
        } catch (e) {
            console.error('Error reading game cache:', e);
            return null;
        }
    },

    /**
     * Save games data to cache
     * @param {Array} games - Array of game objects
     */
    saveGames: function(games) {
        try {
            localStorage.setItem(this.CACHE_KEY, JSON.stringify(games));
            localStorage.setItem(this.CACHE_TIMESTAMP_KEY, Date.now().toString());
        } catch (e) {
            console.error('Error saving game cache:', e);
        }
    },

    /**
     * Update a single game in the cache
     * @param {Object} gameData - Game object with app_id and stats
     */
    updateGame: function(gameData) {
        try {
            const games = this.getGames() || [];
            const index = games.findIndex(g => g.app_id === gameData.app_id);

            if (index >= 0) {
                games[index] = gameData;
            } else {
                games.push(gameData);
            }

            this.saveGames(games);
        } catch (e) {
            console.error('Error updating game cache:', e);
        }
    },

    /**
     * Clear the cache
     */
    clear: function() {
        localStorage.removeItem(this.CACHE_KEY);
        localStorage.removeItem(this.CACHE_TIMESTAMP_KEY);
    },

    /**
     * Check if cache exists and is valid
     * @returns {boolean}
     */
    isValid: function() {
        const timestamp = localStorage.getItem(this.CACHE_TIMESTAMP_KEY);
        if (!timestamp) return false;

        const age = Date.now() - parseInt(timestamp);
        return age <= this.CACHE_DURATION;
    },

    /**
     * Get cache age in human readable format
     * @returns {string}
     */
    getCacheAge: function() {
        const timestamp = localStorage.getItem(this.CACHE_TIMESTAMP_KEY);
        if (!timestamp) return 'Never';

        const age = Date.now() - parseInt(timestamp);
        const minutes = Math.floor(age / 60000);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) {
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else if (minutes > 0) {
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else {
            return 'Just now';
        }
    },

    /**
     * Get incomplete games (games with locked > 0)
     * @returns {Array}
     */
    getIncompleteGames: function() {
        const games = this.getGames() || [];
        return games.filter(g => g.locked > 0);
    },

    /**
     * Get completed games (games with locked === 0)
     * @returns {Array}
     */
    getCompletedGames: function() {
        const games = this.getGames() || [];
        return games.filter(g => g.locked === 0 && g.total > 0);
    },

    /**
     * Get stats summary
     * @returns {Object}
     */
    getStats: function() {
        const games = this.getGames() || [];
        const incomplete = games.filter(g => g.locked > 0);
        const completed = games.filter(g => g.locked === 0 && g.total > 0);
        const totalLocked = games.reduce((sum, g) => sum + g.locked, 0);
        const totalUnlocked = games.reduce((sum, g) => sum + g.unlocked, 0);
        const totalAchievements = games.reduce((sum, g) => sum + g.total, 0);

        return {
            totalGames: games.length,
            incompleteGames: incomplete.length,
            completedGames: completed.length,
            totalLocked: totalLocked,
            totalUnlocked: totalUnlocked,
            totalAchievements: totalAchievements,
            completionRate: totalAchievements > 0
                ? ((totalUnlocked / totalAchievements) * 100).toFixed(1)
                : 0
        };
    }
};

/**
 * Scan games with progress tracking
 * @param {Function} onProgress - Callback for progress updates (scanned, total, percent)
 * @param {Function} onComplete - Callback when scan completes (games array)
 * @param {Function} onError - Callback for errors
 */
function scanGamesWithProgress(onProgress, onComplete, onError) {
    const eventSource = new EventSource('/api/games-with-progress-stream');

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.type === 'start') {
            onProgress(0, data.total, 0);
        } else if (data.type === 'progress') {
            onProgress(data.scanned, data.total, data.percent);
        } else if (data.type === 'complete') {
            eventSource.close();
            // Save to cache
            GameCache.saveGames(data.games);
            onComplete(data.games);
        } else if (data.type === 'error') {
            eventSource.close();
            onError(data.error || 'Failed to scan games');
        }
    };

    eventSource.onerror = function() {
        eventSource.close();
        onError('Failed to connect to server');
    };

    return eventSource;
}

/**
 * Rescan a single game
 * @param {number} appId - Steam app ID
 * @returns {Promise}
 */
async function rescanSingleGame(appId) {
    const response = await fetch(`/api/games/${appId}/achievements`);
    const data = await response.json();

    if (data.success) {
        // Update cache with new game data
        const gameData = {
            app_id: appId,
            name: data.game_name,
            total: data.stats.total,
            unlocked: data.stats.unlocked,
            locked: data.stats.locked,
            completion_percent: data.stats.completion_percent,
            header_image: `https://cdn.cloudflare.steamstatic.com/steam/apps/${appId}/header.jpg`,
            playtime_forever: 0
        };
        GameCache.updateGame(gameData);
        return gameData;
    } else {
        throw new Error(data.error || 'Failed to rescan game');
    }
}
