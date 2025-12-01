// Main JavaScript utilities for SteamAchieve

// Utility functions
function formatPlaytime(minutes) {
    if (!minutes || minutes === 0) return '0h';

    if (minutes < 60) {
        return `${minutes}m`;
    }

    const hours = Math.floor(minutes / 60);
    if (hours < 100) {
        return `${(minutes / 60).toFixed(1)}h`;
    }

    return `${hours}h`;
}

function formatTimestamp(timestamp) {
    if (!timestamp) return 'Never';

    const date = new Date(timestamp * 1000);
    const now = new Date();

    // If today
    if (date.toDateString() === now.toDateString()) {
        return `Today at ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
    }

    // If yesterday
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) {
        return `Yesterday at ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
    }

    // If within a week
    const daysDiff = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    if (daysDiff < 7) {
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        return `${days[date.getDay()]} at ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
    }

    // Otherwise
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatUnlockDate(timestamp) {
    if (!timestamp || timestamp === 0) return null;

    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.classList.remove('d-none');
    }
}

function hideError(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.add('d-none');
    }
}

function showElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.remove('d-none');
    }
}

function hideElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.add('d-none');
    }
}

function getSteamGameImageUrl(appId, imgHash) {
    if (!imgHash) return null;
    return `http://cdn.steampowered.com/steamcommunity/public/images/apps/${appId}/${imgHash}.jpg`;
}

async function fetchAPI(url, options = {}) {
    try {
        const response = await fetch(url, options);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'API request failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Global error handler
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
});

// Console welcome message
console.log('%cSteamAchieve', 'font-size: 24px; font-weight: bold; color: #66c0f4;');
console.log('%cTrack your Steam achievements!', 'font-size: 14px; color: #c7d5e0;');
