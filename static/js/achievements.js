// Achievement display and guide search functionality for SteamAchieve

let allAchievements = [];
let currentGameName = '';
let currentAppId = null;
let guideModal = null;

async function loadAchievements(appId) {
    currentAppId = appId;

    const loadingEl = document.getElementById('loadingAchievements');
    const errorEl = document.getElementById('errorMessage');
    const container = document.getElementById('achievementsContainer');
    const statsEl = document.getElementById('achievementStats');

    try {
        hideError('errorMessage');
        showElement('loadingAchievements');
        hideElement('noAchievements');

        const data = await fetchAPI(`/api/games/${appId}/achievements`);

        if (!data.success) {
            throw new Error(data.error || 'Failed to load achievements');
        }

        allAchievements = data.achievements || [];
        currentGameName = data.game_name || 'Game';

        // Update page title
        document.getElementById('gameName').innerHTML = `<i class="fas fa-trophy"></i> ${currentGameName}`;

        // Update stats
        if (data.stats) {
            document.getElementById('totalAchievements').textContent = data.stats.total;
            document.getElementById('unlockedAchievements').textContent = data.stats.unlocked;
            document.getElementById('lockedAchievements').textContent = data.stats.locked;
            document.getElementById('completionPercent').textContent = `${data.stats.completion_percent}%`;

            const progressBar = document.getElementById('progressBar');
            progressBar.style.width = `${data.stats.completion_percent}%`;
            progressBar.textContent = `${data.stats.completion_percent}%`;

            showElement('achievementStats');
        }

        displayAchievements();

        hideElement('loadingAchievements');

        if (allAchievements.length === 0) {
            showElement('noAchievements');
        }

    } catch (error) {
        console.error('Error loading achievements:', error);
        hideElement('loadingAchievements');
        showError('errorMessage', error.message);
    }
}

function displayAchievements() {
    const container = document.getElementById('achievementsContainer');
    container.innerHTML = '';

    const filtered = getFilteredAchievements();

    if (filtered.length === 0) {
        showElement('noAchievements');
        return;
    }

    hideElement('noAchievements');

    filtered.forEach(achievement => {
        const achievementCard = createAchievementCard(achievement);
        container.appendChild(achievementCard);
    });
}

function createAchievementCard(achievement) {
    const card = document.createElement('div');
    card.className = `achievement-card ${achievement.achieved ? 'unlocked' : 'locked'}`;
    card.setAttribute('data-achieved', achievement.achieved);
    card.setAttribute('data-name', achievement.name.toLowerCase());

    const icon = achievement.achieved ? achievement.icon : achievement.icongray || achievement.icon;
    const iconUrl = icon || 'https://via.placeholder.com/64/1b2838/66c0f4?text=?';

    const unlockDateHtml = achievement.achieved && achievement.unlocktime > 0
        ? `<span class="unlock-date"><i class="fas fa-check-circle"></i> Unlocked: ${formatUnlockDate(achievement.unlocktime)}</span>`
        : '';

    const globalPercent = achievement.global_percent || 0;
    const rarity = getRarityLabel(globalPercent);

    card.innerHTML = `
        <img src="${iconUrl}" alt="${achievement.name}" class="achievement-icon ${!achievement.achieved ? 'grayscale' : ''}">
        <div class="achievement-content">
            <div class="achievement-title">${achievement.name}</div>
            <div class="achievement-description">${achievement.description || 'No description'}</div>
            <div class="achievement-meta">
                <span class="global-percent">
                    <i class="fas fa-users"></i> ${globalPercent.toFixed(1)}% ${rarity}
                </span>
                ${unlockDateHtml}
            </div>
        </div>
        <div class="ms-auto">
            <button class="btn btn-outline-primary btn-sm" onclick="showGuides('${escapeHtml(achievement.name)}')">
                <i class="fas fa-book"></i> Find Guides
            </button>
        </div>
    `;

    return card;
}

function getRarityLabel(percent) {
    if (percent >= 75) return '(Common)';
    if (percent >= 50) return '(Uncommon)';
    if (percent >= 25) return '(Rare)';
    if (percent >= 10) return '(Very Rare)';
    if (percent >= 1) return '(Ultra Rare)';
    return '(Legendary)';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function showGuides(achievementName) {
    if (!guideModal) {
        guideModal = new bootstrap.Modal(document.getElementById('guideModal'));
    }

    const modalTitle = document.getElementById('guideModalLabel');
    const guideResults = document.getElementById('guideResults');
    const guideLoading = document.getElementById('guideLoading');
    const guideError = document.getElementById('guideError');
    const noGuides = document.getElementById('noGuides');

    modalTitle.textContent = `Guides for: ${achievementName}`;

    showElement('guideLoading');
    hideElement('guideError');
    hideElement('noGuides');
    guideResults.innerHTML = '';

    guideModal.show();

    try {
        const response = await fetch('/api/achievement/guide/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                app_id: currentAppId,
                game_name: currentGameName,
                achievement_name: achievementName
            })
        });

        const data = await response.json();

        hideElement('guideLoading');

        if (!data.success) {
            throw new Error(data.error || 'Failed to search guides');
        }

        const guides = data.guides || [];

        if (guides.length === 0) {
            showElement('noGuides');
            return;
        }

        guides.forEach(guide => {
            const guideItem = createGuideItem(guide);
            guideResults.appendChild(guideItem);
        });

    } catch (error) {
        console.error('Error loading guides:', error);
        hideElement('guideLoading');
        guideError.textContent = error.message;
        showElement('guideError');
    }
}

function createGuideItem(guide) {
    const item = document.createElement('a');
    item.href = guide.url || guide.guide_url;
    item.target = '_blank';
    item.className = 'list-group-item list-group-item-action guide-item';

    const sourceClass = `source-${guide.source || 'article'}`;
    const sourceIcon = getSourceIcon(guide.source);

    item.innerHTML = `
        <div class="d-flex w-100 justify-content-between align-items-start">
            <div class="flex-grow-1">
                <span class="guide-source-badge ${sourceClass}">
                    ${sourceIcon} ${(guide.source || 'article').toUpperCase()}
                </span>
                <h6 class="mb-1">${guide.title || guide.guide_title || 'Guide'}</h6>
                ${guide.snippet || guide.guide_snippet ? `<p class="mb-1 small text-muted">${guide.snippet || guide.guide_snippet}</p>` : ''}
            </div>
            <i class="fas fa-external-link-alt ms-2"></i>
        </div>
    `;

    return item;
}

function getSourceIcon(source) {
    const icons = {
        'steam': '<i class="fab fa-steam"></i>',
        'youtube': '<i class="fab fa-youtube"></i>',
        'reddit': '<i class="fab fa-reddit"></i>',
        'wiki': '<i class="fas fa-book"></i>',
        'gaming_site': '<i class="fas fa-gamepad"></i>',
        'article': '<i class="fas fa-file-alt"></i>'
    };
    return icons[source] || icons['article'];
}

function getFilteredAchievements() {
    const filterValue = document.querySelector('input[name="filterAchievements"]:checked')?.value || 'all';
    const searchTerm = document.getElementById('searchAchievements')?.value.toLowerCase().trim() || '';

    let filtered = [...allAchievements];

    // Apply achievement status filter
    if (filterValue === 'locked') {
        filtered = filtered.filter(ach => !ach.achieved);
    } else if (filterValue === 'unlocked') {
        filtered = filtered.filter(ach => ach.achieved);
    }

    // Apply search filter
    if (searchTerm) {
        filtered = filtered.filter(ach => {
            const name = (ach.name || '').toLowerCase();
            const desc = (ach.description || '').toLowerCase();
            return name.includes(searchTerm) || desc.includes(searchTerm);
        });
    }

    return filtered;
}

function filterAchievements() {
    displayAchievements();
}
