// Locked Achievements Hunter functionality

let allLockedAchievements = [];
let filteredAchievements = [];
let currentAchievement = null;
let guideModal = null;

// Load locked achievements from API
async function loadLockedAchievements() {
    const loadingEl = document.getElementById('loadingAchievements');
    const errorEl = document.getElementById('errorMessage');
    const statsSection = document.getElementById('statsSection');
    const filtersSection = document.getElementById('filtersSection');
    const achievementsList = document.getElementById('achievementsList');
    const noAchievements = document.getElementById('noAchievements');

    try {
        showElement('loadingAchievements');
        hideError('errorMessage');
        hideElement('statsSection');
        hideElement('filtersSection');
        hideElement('noAchievements');

        const data = await fetchAPI('/api/locked-achievements?max_games=20');

        if (!data.success) {
            throw new Error(data.error || 'Failed to load locked achievements');
        }

        allLockedAchievements = data.locked_achievements || [];
        filteredAchievements = [...allLockedAchievements];

        // Update stats
        updateStats(data);

        // Populate game filter
        populateGameFilter();

        // Display achievements
        displayAchievements();

        hideElement('loadingAchievements');
        showElement('statsSection');
        showElement('filtersSection');

        if (allLockedAchievements.length === 0) {
            showElement('noAchievements');
        }

    } catch (error) {
        console.error('Error loading locked achievements:', error);
        hideElement('loadingAchievements');
        showError('errorMessage', error.message);
    }
}

function updateStats(data) {
    document.getElementById('totalLocked').textContent = data.total_locked || 0;
    document.getElementById('gamesScanned').textContent = data.games_scanned || 0;

    // Count ultra rare achievements (<1%)
    const ultraRare = allLockedAchievements.filter(ach =>
        (ach.global_percent || 100) < 1
    ).length;
    document.getElementById('ultraRareCount').textContent = ultraRare;

    // AI guides count (placeholder - would be from cache)
    document.getElementById('aiGuidesAvailable').textContent = '0';
}

function populateGameFilter() {
    const gameFilter = document.getElementById('gameFilter');

    // Get unique games
    const games = {};
    allLockedAchievements.forEach(ach => {
        if (ach.game_name && !games[ach.game_name]) {
            games[ach.game_name] = true;
        }
    });

    // Sort games alphabetically
    const sortedGames = Object.keys(games).sort();

    // Clear and populate filter
    gameFilter.innerHTML = '<option value="">All Games</option>';
    sortedGames.forEach(game => {
        const option = document.createElement('option');
        option.value = game;
        option.textContent = game;
        gameFilter.appendChild(option);
    });
}

function displayAchievements() {
    const container = document.getElementById('achievementsList');
    container.innerHTML = '';

    if (filteredAchievements.length === 0) {
        showElement('noAchievements');
        return;
    }

    hideElement('noAchievements');

    filteredAchievements.forEach(achievement => {
        const card = createLockedAchievementCard(achievement);
        container.appendChild(card);
    });
}

function createLockedAchievementCard(achievement) {
    const card = document.createElement('div');
    card.className = 'locked-achievement-card';

    const globalPercent = parseFloat(achievement.global_percent) || 0;
    const rarity = getRarityInfo(globalPercent);
    const difficulty = estimateDifficulty(globalPercent);

    const iconUrl = achievement.icongray || achievement.icon ||
        'https://via.placeholder.com/64/1b2838/66c0f4?text=?';

    card.innerHTML = `
        <div class="d-flex align-items-start">
            <img src="${iconUrl}" alt="${achievement.name}"
                 class="achievement-icon grayscale me-3"
                 style="width: 64px; height: 64px; border-radius: 8px;">
            <div class="flex-grow-1">
                <div class="achievement-game-badge">
                    <i class="fas fa-gamepad"></i> ${achievement.game_name}
                </div>
                <h5 class="text-light mb-2">${achievement.name}</h5>
                <p class="text-muted mb-2">${achievement.description || 'No description'}</p>

                <div class="d-flex align-items-center gap-2 flex-wrap">
                    <span class="achievement-rarity rarity-${rarity.class}">
                        <i class="fas fa-users"></i> ${globalPercent.toFixed(1)}% ${rarity.label}
                    </span>

                    <span class="difficulty-badge diff-${difficulty}">
                        <i class="fas fa-signal"></i> Difficulty: ${difficulty}/10
                    </span>

                    <button class="btn btn-sm btn-primary" onclick="showGuides(${achievement.app_id}, '${escapeHtml(achievement.game_name)}', '${escapeHtml(achievement.name)}', '${escapeHtml(achievement.description || '')}', ${globalPercent})">
                        <i class="fas fa-book"></i> Find Guides
                    </button>

                    <button class="btn btn-sm btn-outline-info" onclick="viewGameAchievements(${achievement.app_id})">
                        <i class="fas fa-trophy"></i> View All Achievements
                    </button>
                </div>
            </div>
        </div>
    `;

    return card;
}

function getRarityInfo(percent) {
    if (percent < 1) return { class: 'legendary', label: 'Legendary' };
    if (percent < 10) return { class: 'ultra-rare', label: 'Ultra Rare' };
    if (percent < 25) return { class: 'very-rare', label: 'Very Rare' };
    if (percent < 50) return { class: 'rare', label: 'Rare' };
    if (percent < 75) return { class: 'uncommon', label: 'Uncommon' };
    return { class: 'common', label: 'Common' };
}

function estimateDifficulty(globalPercent) {
    if (globalPercent >= 75) return 1;
    if (globalPercent >= 50) return 3;
    if (globalPercent >= 25) return 5;
    if (globalPercent >= 10) return 7;
    if (globalPercent >= 1) return 9;
    return 10;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/'/g, '\\\'');
}

// Show guides modal
async function showGuides(appId, gameName, achievementName, achievementDescription, globalPercent) {
    if (!guideModal) {
        guideModal = new bootstrap.Modal(document.getElementById('guideModal'));
    }

    currentAchievement = { appId, gameName, achievementName, achievementDescription, globalPercent };

    document.getElementById('guideModalLabel').textContent = `Guides for: ${achievementName}`;

    showElement('guideLoading');
    hideElement('guideError');
    hideElement('guideTabs');
    document.getElementById('aiGuideContent').innerHTML = '';
    document.getElementById('communityGuidesContent').innerHTML = '';

    guideModal.show();

    try {
        // Fetch guides from all sources
        const response = await fetch('/api/achievement/guide/multi-search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                app_id: appId,
                game_name: gameName,
                achievement_name: achievementName,
                achievement_description: achievementDescription,
                global_percent: globalPercent,
                sources: ['ai', 'ddgs', 'steam_community', 'youtube'],
                max_results: 15
            })
        });

        const data = await response.json();

        hideElement('guideLoading');

        if (!data.success) {
            throw new Error(data.error || 'Failed to load guides');
        }

        const guides = data.guides || [];

        // Separate AI guide from other guides
        const aiGuide = guides.find(g => g.source === 'ai_generated');
        const communityGuides = guides.filter(g => g.source !== 'ai_generated');

        // Display guides
        if (aiGuide) {
            displayAIGuide(aiGuide);
        } else {
            document.getElementById('aiGuideContent').innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-robot"></i> AI guide is being generated...
                    <button class="btn btn-sm btn-primary ms-2" onclick="generateAIGuide()">
                        <i class="fas fa-magic"></i> Generate Now
                    </button>
                </div>
            `;
        }

        if (communityGuides.length > 0) {
            displayCommunityGuides(communityGuides);
        } else {
            document.getElementById('communityGuidesContent').innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i> No community guides found yet.
                </div>
            `;
        }

        showElement('guideTabs');

    } catch (error) {
        console.error('Error loading guides:', error);
        hideElement('guideLoading');
        document.getElementById('guideErrorText').textContent = error.message;
        showElement('guideError');
    }
}

function displayAIGuide(aiGuide) {
    const container = document.getElementById('aiGuideContent');

    const strategies = aiGuide.strategies || [];
    const tips = aiGuide.tips || [];

    const strategiesHtml = strategies.length > 0 ? `
        <h6 class="text-light mb-3"><i class="fas fa-lightbulb"></i> Strategies</h6>
        ${strategies.map((strategy, idx) => `
            <div class="strategy-item">
                <strong>${idx + 1}.</strong> ${strategy}
            </div>
        `).join('')}
    ` : '';

    const tipsHtml = tips.length > 0 ? `
        <h6 class="text-light mb-3 mt-4"><i class="fas fa-star"></i> Tips</h6>
        ${tips.map(tip => `
            <div class="tip-item">
                <i class="fas fa-angle-right"></i> ${tip}
            </div>
        `).join('')}
    ` : '';

    const difficulty = aiGuide.difficulty || 5;
    const estimatedTime = aiGuide.estimated_time || 'Varies';

    container.innerHTML = `
        <div class="ai-guide-content">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="text-light mb-0">
                    <i class="fas fa-robot"></i> AI-Generated Guide
                </h5>
                <div>
                    <span class="difficulty-badge diff-${difficulty}">
                        Difficulty: ${difficulty}/10
                    </span>
                    <span class="badge bg-info text-dark ms-2">
                        <i class="fas fa-clock"></i> ${estimatedTime}
                    </span>
                </div>
            </div>

            <p class="text-light">${aiGuide.content || aiGuide.summary || 'Guide content'}</p>

            ${strategiesHtml}
            ${tipsHtml}

            <div class="mt-4 text-muted">
                <small>
                    <i class="fas fa-info-circle"></i> Generated by ${aiGuide.model_used || 'Grok AI'}
                    ${aiGuide.from_cache ? ' (Cached)' : ''}
                </small>
            </div>
        </div>
    `;
}

function displayCommunityGuides(guides) {
    const container = document.getElementById('communityGuidesContent');

    const guidesHtml = guides.map(guide => {
        const sourceIcon = getSourceIcon(guide.source);
        const sourceBadge = `guide-source-badge source-${guide.source}`;

        return `
            <a href="${guide.url}" target="_blank" class="list-group-item list-group-item-action guide-item bg-dark border-secondary mb-2">
                <div class="d-flex w-100 justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <span class="${sourceBadge}">
                            ${sourceIcon} ${(guide.source || 'external').toUpperCase()}
                        </span>
                        <h6 class="mb-1 text-light">${guide.title}</h6>
                        ${guide.snippet ? `<p class="mb-1 small text-muted">${guide.snippet}</p>` : ''}
                        <small class="text-muted">Quality Score: ${guide.quality_score || 0}/100</small>
                    </div>
                    <i class="fas fa-external-link-alt ms-2 text-muted"></i>
                </div>
            </a>
        `;
    }).join('');

    container.innerHTML = `
        <div class="list-group">
            ${guidesHtml}
        </div>
    `;
}

async function generateAIGuide() {
    if (!currentAchievement) return;

    const { appId, gameName, achievementName, achievementDescription, globalPercent } = currentAchievement;

    showElement('guideLoading');

    try {
        const response = await fetch('/api/achievement/guide/ai-generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                app_id: appId,
                game_name: gameName,
                achievement_name: achievementName,
                achievement_description: achievementDescription,
                global_percent: globalPercent,
                force_regenerate: true
            })
        });

        const data = await response.json();

        hideElement('guideLoading');

        if (!data.success) {
            throw new Error(data.error || 'Failed to generate AI guide');
        }

        displayAIGuide({
            ...data.guide,
            source: 'ai_generated',
            from_cache: false
        });

    } catch (error) {
        console.error('Error generating AI guide:', error);
        hideElement('guideLoading');
        alert('Failed to generate AI guide: ' + error.message);
    }
}

function getSourceIcon(source) {
    const icons = {
        'ai_generated': '<i class="fas fa-robot"></i>',
        'steam_community': '<i class="fab fa-steam"></i>',
        'steam': '<i class="fab fa-steam"></i>',
        'youtube': '<i class="fab fa-youtube"></i>',
        'reddit': '<i class="fab fa-reddit"></i>',
        'wiki': '<i class="fas fa-book"></i>',
        'pcgamingwiki': '<i class="fas fa-book"></i>',
        'ddgs': '<i class="fas fa-search"></i>'
    };
    return icons[source] || '<i class="fas fa-link"></i>';
}

function viewGameAchievements(appId) {
    window.location.href = `/achievements/${appId}`;
}

// Filter and search functions
function filterAchievements() {
    const gameFilter = document.getElementById('gameFilter').value;
    const rarityFilter = document.getElementById('rarityFilter').value;
    const sortBy = document.getElementById('sortBy').value;
    const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();

    filteredAchievements = [...allLockedAchievements];

    // Filter by game
    if (gameFilter) {
        filteredAchievements = filteredAchievements.filter(ach =>
            ach.game_name === gameFilter
        );
    }

    // Filter by rarity
    if (rarityFilter) {
        filteredAchievements = filteredAchievements.filter(ach => {
            const percent = ach.global_percent || 100;
            const rarity = getRarityInfo(percent);
            return rarity.class === rarityFilter;
        });
    }

    // Filter by search term
    if (searchTerm) {
        filteredAchievements = filteredAchievements.filter(ach => {
            const name = (ach.name || '').toLowerCase();
            const desc = (ach.description || '').toLowerCase();
            const game = (ach.game_name || '').toLowerCase();
            return name.includes(searchTerm) || desc.includes(searchTerm) || game.includes(searchTerm);
        });
    }

    // Sort
    if (sortBy === 'rarity') {
        filteredAchievements.sort((a, b) => (a.global_percent || 100) - (b.global_percent || 100));
    } else if (sortBy === 'common') {
        filteredAchievements.sort((a, b) => (b.global_percent || 0) - (a.global_percent || 0));
    } else if (sortBy === 'game') {
        filteredAchievements.sort((a, b) => (a.game_name || '').localeCompare(b.game_name || ''));
    }

    displayAchievements();
}

// Set up event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Filter listeners
    const gameFilter = document.getElementById('gameFilter');
    const rarityFilter = document.getElementById('rarityFilter');
    const sortBy = document.getElementById('sortBy');
    const searchInput = document.getElementById('searchInput');

    if (gameFilter) gameFilter.addEventListener('change', filterAchievements);
    if (rarityFilter) rarityFilter.addEventListener('change', filterAchievements);
    if (sortBy) sortBy.addEventListener('change', filterAchievements);
    if (searchInput) searchInput.addEventListener('input', filterAchievements);
});
