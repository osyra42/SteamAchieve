// Game library functionality for SteamAchieve

let allGames = [];
let filteredGames = [];

async function loadGames() {
    const loadingEl = document.getElementById('loadingGames');
    const errorEl = document.getElementById('errorMessage');
    const gamesGrid = document.getElementById('gamesGrid');
    const noGames = document.getElementById('noGames');

    try {
        hideError('errorMessage');
        showElement('loadingGames');
        hideElement('noGames');

        const data = await fetchAPI('/api/games');

        if (!data.success) {
            throw new Error(data.error || 'Failed to load games');
        }

        allGames = data.games || [];
        filteredGames = [...allGames];

        // Sort by last played (most recent first)
        filteredGames.sort((a, b) => {
            const aTime = a.last_played || 0;
            const bTime = b.last_played || 0;
            return bTime - aTime;
        });

        displayGames();

        hideElement('loadingGames');

        if (allGames.length === 0) {
            showElement('noGames');
        }

    } catch (error) {
        console.error('Error loading games:', error);
        hideElement('loadingGames');
        showError('errorMessage', error.message);
    }
}

function displayGames() {
    const gamesGrid = document.getElementById('gamesGrid');
    gamesGrid.innerHTML = '';

    if (filteredGames.length === 0) {
        showElement('noGames');
        return;
    }

    hideElement('noGames');

    filteredGames.forEach(game => {
        const gameCard = createGameCard(game);
        gamesGrid.appendChild(gameCard);
    });
}

function createGameCard(game) {
    const col = document.createElement('div');
    col.className = 'col';

    const appId = game.app_id || game.appid;
    const gameName = game.name || 'Unknown Game';
    const playtimeForever = game.playtime_forever || 0;
    const playtime2Weeks = game.playtime_2weeks || 0;
    const lastPlayed = game.last_played || 0;

    // Use new CDN image URLs with fallbacks
    let gameImageUrl;
    if (game.images && game.images.header) {
        gameImageUrl = game.images.header;
    } else if (game.header_image) {
        gameImageUrl = game.header_image;
    } else {
        // Fallback to Steam CDN header image
        gameImageUrl = `https://cdn.cloudflare.steamstatic.com/steam/apps/${appId}/header.jpg`;
    }

    const card = document.createElement('div');
    card.className = 'game-card';
    card.onclick = () => viewAchievements(appId);

    card.innerHTML = `
        <img src="${gameImageUrl}" alt="${gameName}" onerror="this.src='https://via.placeholder.com/460x215/1b2838/66c0f4?text=${encodeURIComponent(gameName)}'">
        <div class="card-body">
            <h5 class="card-title" title="${gameName}">${gameName}</h5>
            <div class="game-playtime">
                <i class="fas fa-clock"></i> ${formatPlaytime(playtimeForever)}
                ${playtime2Weeks > 0 ? `<span class="text-success">(+${formatPlaytime(playtime2Weeks)} recently)</span>` : ''}
            </div>
            ${lastPlayed > 0 ? `<div class="game-playtime mt-1"><i class="fas fa-calendar"></i> Last played: ${formatTimestamp(lastPlayed)}</div>` : ''}
        </div>
    `;

    col.appendChild(card);
    return col;
}

function viewAchievements(appId) {
    window.location.href = `/achievements/${appId}`;
}

function searchGames() {
    const searchInput = document.getElementById('searchGames');
    const searchTerm = searchInput.value.toLowerCase().trim();

    if (!searchTerm) {
        filteredGames = [...allGames];
    } else {
        filteredGames = allGames.filter(game => {
            const gameName = (game.name || '').toLowerCase();
            return gameName.includes(searchTerm);
        });
    }

    displayGames();
}

// Set up search event listener
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchGames');
    if (searchInput) {
        searchInput.addEventListener('input', searchGames);
    }
});
