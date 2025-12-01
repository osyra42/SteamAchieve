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

    const globalPercent = parseFloat(achievement.global_percent) || 0;
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

    // Find the achievement data
    const achievement = allAchievements.find(a => a.name === achievementName);
    if (!achievement) {
        console.error('Achievement not found:', achievementName);
        return;
    }

    const modalTitle = document.getElementById('guideModalLabel');
    const aiGuideSection = document.getElementById('aiGuideSection');
    const communityGuideSection = document.getElementById('communityGuideSection');
    const guideLoading = document.getElementById('guideLoading');
    const guideError = document.getElementById('guideError');

    modalTitle.textContent = `Guides for: ${achievementName}`;

    showElement('guideLoading');
    hideElement('guideError');
    aiGuideSection.innerHTML = '';
    communityGuideSection.innerHTML = '';

    guideModal.show();

    try {
        // Fetch guides from all sources using multi-search
        const response = await fetch('/api/achievement/guide/multi-search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                app_id: currentAppId,
                game_name: currentGameName,
                achievement_name: achievementName,
                achievement_description: achievement.description || '',
                global_percent: achievement.global_percent,
                sources: ['ai', 'ddgs', 'steam_community', 'youtube'],
                max_results: 15
            })
        });

        const data = await response.json();

        hideElement('guideLoading');

        if (!data.success) {
            throw new Error(data.error || 'Failed to search guides');
        }

        const guides = data.guides || [];

        // Separate AI guide from community guides
        const aiGuide = guides.find(g => g.source === 'ai_generated' || g.type === 'ai');
        const communityGuides = guides.filter(g => g.source !== 'ai_generated' && g.type !== 'ai');

        // Display AI Guide
        if (aiGuide) {
            displayAIGuideInModal(aiGuide, achievement);
        } else {
            displayGenerateAIButton(achievement);
        }

        // Display Community Guides
        if (communityGuides.length > 0) {
            displayCommunityGuidesInModal(communityGuides);
        } else {
            communityGuideSection.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i> No community guides found. Try generating an AI guide!
                </div>
            `;
        }

    } catch (error) {
        console.error('Error loading guides:', error);
        hideElement('guideLoading');
        guideError.textContent = error.message;
        showElement('guideError');
    }
}

function displayAIGuideInModal(aiGuide, achievement) {
    const container = document.getElementById('aiGuideSection');

    const strategies = aiGuide.strategies || [];
    const tips = aiGuide.tips || [];
    const difficulty = aiGuide.difficulty || aiGuide.difficulty_rating || 5;
    const estimatedTime = aiGuide.estimated_time || 'Varies';
    const content = aiGuide.content || aiGuide.summary || aiGuide.guide_content || '';

    const strategiesHtml = strategies.length > 0 ? `
        <div class="mt-3">
            <h6 class="text-primary"><i class="fas fa-lightbulb"></i> Strategies</h6>
            ${strategies.map((strategy, idx) => `
                <div class="bg-dark p-3 rounded mb-2 border-start border-primary border-3">
                    <strong class="text-light">${idx + 1}.</strong> <span class="text-light">${strategy}</span>
                </div>
            `).join('')}
        </div>
    ` : '';

    const tipsHtml = tips.length > 0 ? `
        <div class="mt-3">
            <h6 class="text-warning"><i class="fas fa-star"></i> Pro Tips</h6>
            ${tips.map(tip => `
                <div class="bg-dark p-2 rounded mb-2 border-start border-warning border-2">
                    <i class="fas fa-angle-right text-warning"></i> <span class="text-light">${tip}</span>
                </div>
            `).join('')}
        </div>
    ` : '';

    container.innerHTML = `
        <div class="card bg-gradient text-light border-primary mb-4" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="mb-0">
                        <i class="fas fa-robot"></i> AI-Generated Guide
                    </h5>
                    <div>
                        <span class="badge bg-dark">
                            <i class="fas fa-signal"></i> Difficulty: ${difficulty}/10
                        </span>
                        <span class="badge bg-dark ms-1">
                            <i class="fas fa-clock"></i> ${estimatedTime}
                        </span>
                    </div>
                </div>

                <div class="alert alert-light mb-3">
                    <p class="mb-0" style="color: #1a1a1a; line-height: 1.6; white-space: pre-wrap;">${content || 'Generating comprehensive guide...'}</p>
                </div>

                ${strategiesHtml}
                ${tipsHtml}

                <div class="mt-3">
                    <small class="text-light opacity-75">
                        <i class="fas fa-info-circle"></i> Generated by ${aiGuide.model_used || 'Grok AI'}
                        ${aiGuide.from_cache ? ' • Cached' : ' • Fresh'}
                    </small>
                </div>
            </div>
        </div>
    `;
}

function displayGenerateAIButton(achievement) {
    const container = document.getElementById('aiGuideSection');

    container.innerHTML = `
        <div class="card bg-dark border-primary text-center p-4 mb-4">
            <div class="card-body">
                <i class="fas fa-robot fa-3x text-primary mb-3"></i>
                <h5 class="text-light mb-3">No AI Guide Yet</h5>
                <p class="text-muted mb-4">Generate a comprehensive AI-powered walkthrough with strategies, tips, and difficulty analysis.</p>
                <button class="btn btn-primary btn-lg" onclick="generateAIGuideInline('${escapeHtml(achievement.name)}', '${escapeHtml(achievement.description || '')}', ${achievement.global_percent || 0})">
                    <i class="fas fa-magic"></i> Generate AI Guide Now
                </button>
                <div id="aiGenerationProgress" class="mt-3" style="display: none;">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">Generating...</span>
                    </div>
                    <p class="text-light mt-2 mb-0">AI is analyzing the achievement...</p>
                </div>
            </div>
        </div>
    `;
}

async function generateAIGuideInline(achievementName, achievementDescription, globalPercent) {
    const progressEl = document.getElementById('aiGenerationProgress');
    showElement('aiGenerationProgress');

    try {
        const response = await fetch('/api/achievement/guide/ai-generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                app_id: currentAppId,
                game_name: currentGameName,
                achievement_name: achievementName,
                achievement_description: achievementDescription,
                global_percent: globalPercent,
                force_regenerate: true
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to generate AI guide');
        }

        // Find achievement and display the guide
        const achievement = allAchievements.find(a => a.name === achievementName);
        displayAIGuideInModal(data.guide, achievement);

    } catch (error) {
        console.error('Error generating AI guide:', error);
        alert('Failed to generate AI guide: ' + error.message + '\n\nMake sure you have set OPENROUTER_API_KEY in your .env file.');
        hideElement('aiGenerationProgress');
    }
}

function displayCommunityGuidesInModal(guides) {
    const container = document.getElementById('communityGuideSection');

    const guidesHtml = guides.map(guide => {
        const sourceIcon = getSourceIcon(guide.source);

        return `
            <a href="${guide.url}" target="_blank" class="list-group-item list-group-item-action bg-dark border-secondary text-light mb-2 rounded">
                <div class="d-flex w-100 justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <span class="badge bg-secondary mb-2">
                            ${sourceIcon} ${(guide.source || 'external').toUpperCase()}
                        </span>
                        <h6 class="mb-1">${guide.title || 'Guide'}</h6>
                        ${guide.snippet ? `<p class="mb-1 small text-muted">${guide.snippet}</p>` : ''}
                        ${guide.quality_score ? `<small class="text-muted">Quality: ${guide.quality_score}/100</small>` : ''}
                    </div>
                    <i class="fas fa-external-link-alt ms-2 text-muted"></i>
                </div>
            </a>
        `;
    }).join('');

    container.innerHTML = `
        <h6 class="text-light mb-3"><i class="fas fa-users"></i> Community Guides</h6>
        <div class="list-group">
            ${guidesHtml}
        </div>
    `;
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
        'gaming_site': '<i class="fas fa-gamepad"></i>',
        'ddgs': '<i class="fas fa-search"></i>',
        'article': '<i class="fas fa-file-alt"></i>'
    };
    return icons[source] || '<i class="fas fa-link"></i>';
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
