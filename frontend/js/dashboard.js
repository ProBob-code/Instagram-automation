/**
 * IG Growth Hub - Dashboard JavaScript
 * Handles dashboard functionality, score display, and boost controls
 */

// Global state
let selectedPlatform = 'instagram';
let selectedActions = ['likes'];
let intensity = 1;
let isBoostRunning = false;
let currentTaskId = null;
let progressPollInterval = null;
let targetKeywords = []; // Store user keywords

document.addEventListener('DOMContentLoaded', () => {
    // Check if user is logged in
    const user = IGGrowthHub.getSession('user');
    if (!user || !user.loggedIn) {
        window.location.href = 'index.html';
        return;
    }

    initDashboard();
});

async function initDashboard() {
    // Load cached data
    const profile = IGGrowthHub.getSession('profile');
    const score = IGGrowthHub.getSession('score');
    const suggestions = IGGrowthHub.getSession('suggestions');

    // Initialize UI
    if (profile) {
        renderProfile(profile);
    }
    if (score) {
        renderScore(score);
    }
    if (suggestions) {
        renderSuggestions(suggestions);
    }

    // Initialize controls
    initNavigation(); // New Navigation
    initPlatformControls();
    initActionCheckboxes();
    initKeywordControls();
    initBoostControls();
    initLogout();
    initModal(); // Keep for detail view


    // Fetch initial rate limits
    fetchRateLimits();

    // Show welcome toast
    IGGrowthHub.showToast('Profile analysis complete!', 'success');
}

async function fetchRateLimits() {
    try {
        const response = await fetch(`${IGGrowthHub.API_BASE}/rate-limits/${selectedPlatform}`);
        const data = await response.json();

        if (response.ok) {
            updateDailyLimitsUI(data);
        }
    } catch (error) {
        console.error('Error fetching rate limits:', error);
    }
}

function updateDailyLimitsUI(limits) {
    const types = {
        'likes': 'likesRemaining',
        'follows': 'followsRemaining',
        'comments': 'commentsRemaining',
        'views': 'viewsRemaining'
    };

    for (const [type, elementId] of Object.entries(types)) {
        const el = document.getElementById(elementId);
        if (el && limits[type]) {
            const used = limits[type].used.daily || 0;
            const limit = limits[type].limits.per_day || 300;
            el.textContent = `${used} / ${limit}`;
        }
    }
}

// ============================================
// PROFILE RENDERING
// ============================================

function renderProfile(profile) {
    const username = profile.username;
    // Normalize profile pic URL
    const profilePicUrl = profile.profile_pic_local || (username ? `/api/profile-pic/${username}` : profile.profile_pic_url);

    // Update Header Avatar
    const avatarImg = document.getElementById('userAvatarImg');
    const avatarInitial = document.getElementById('userAvatarInitial');

    if (username) {
        if (avatarInitial) avatarInitial.textContent = username.charAt(0).toUpperCase();

        if (profilePicUrl && avatarImg) {
            avatarImg.src = profilePicUrl;
            avatarImg.style.display = 'block';
            if (avatarInitial) avatarInitial.style.display = 'none';
        }
    }

    // Update Profile Card Pic (Sidebar)
    const cardImg = document.getElementById('profilePicImg');
    const cardEmoji = document.getElementById('profilePicEmoji');

    if (profilePicUrl && cardImg) {
        cardImg.src = profilePicUrl;
        cardImg.style.display = 'block';
        if (cardEmoji) cardEmoji.style.display = 'none';
    }

    // Update profile text info
    const profileName = document.getElementById('profileName');
    const profileUsername = document.getElementById('profileUsername');

    if (profileName) profileName.textContent = profile.name || username;
    if (profileUsername) profileUsername.textContent = '@' + username;

    // Update stats
    if (document.getElementById('postsCount')) document.getElementById('postsCount').textContent = IGGrowthHub.formatNumber(profile.posts || 0);
    if (document.getElementById('followersCount')) document.getElementById('followersCount').textContent = IGGrowthHub.formatNumber(profile.followers || 0);
    if (document.getElementById('followingCount')) document.getElementById('followingCount').textContent = IGGrowthHub.formatNumber(profile.following || 0);
}

// ============================================
// SCORE RENDERING
// ============================================

function renderScore(scoreData) {
    const total = scoreData.total;
    const breakdown = scoreData.breakdown;

    animateScoreNumber(total);
    updateScoreRing(total);
    updateScoreBadge(total);
    renderBreakdown(breakdown);
}

function animateScoreNumber(targetScore) {
    const scoreElement = document.getElementById('scoreNumber');
    let currentScore = 0;
    const duration = 1500;
    const startTime = performance.now();

    function animate(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        currentScore = Math.round(eased * targetScore);
        scoreElement.textContent = currentScore;

        if (progress < 1) {
            requestAnimationFrame(animate);
        }
    }

    requestAnimationFrame(animate);
}

function updateScoreRing(score) {
    const ring = document.getElementById('scoreRing');
    if (!ring) return;

    const circumference = 502;
    const offset = circumference - (score / 100) * circumference;

    setTimeout(() => {
        ring.style.strokeDashoffset = offset;
    }, 100);
}

function updateScoreBadge(score) {
    const badge = document.getElementById('scoreBadge');
    if (!badge) return;

    badge.classList.remove('excellent', 'good', 'needs-work');

    if (score >= 71) {
        badge.textContent = 'Excellent';
        badge.classList.add('excellent');
    } else if (score >= 41) {
        badge.textContent = 'Good';
        badge.classList.add('good');
    } else {
        badge.textContent = 'Needs Work';
        badge.classList.add('needs-work');
    }
}

function renderBreakdown(breakdown) {
    const container = document.getElementById('scoreBreakdown');
    if (!container) return;

    const labels = {
        bio: 'Bio Optimization',
        name: 'Name Field SEO',
        content: 'Content Consistency',
        hashtags: 'Hashtag Strategy',
        engagement: 'Engagement Rate',
        completeness: 'Profile Completeness'
    };

    const icons = { pass: '✓', warn: '!', fail: '✗' };

    container.innerHTML = Object.entries(breakdown).map(([key, data]) => `
        <div class="breakdown-item">
            <div class="breakdown-icon ${data.status}">${icons[data.status]}</div>
            <span class="breakdown-text">${labels[key]}</span>
            <span class="breakdown-score">${data.score}/${data.max}</span>
        </div>
    `).join('');
}

// ============================================
// SUGGESTIONS RENDERING
// ============================================

function renderSuggestions(suggestions) {
    const container = document.getElementById('suggestionsContainer');
    if (!container) return;

    // Add AI generation buttons at the top
    let html = `
        <div class="ai-generate-section">
            <h4>🤖 AI-Powered Suggestions</h4>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1rem;">
                Generate copy-paste ready content optimized for Instagram SEO
            </p>
            <div class="ai-buttons">
                <button class="ai-btn" onclick="generateAISuggestions('bio')">
                    ✨ Generate Bio Ideas
                </button>
                <button class="ai-btn" onclick="generateAISuggestions('caption')">
                    📝 Generate Captions
                </button>
                <button class="ai-btn" onclick="generateAISuggestions('hashtag')">
                    # Hashtag Strategy
                </button>
            </div>
            <div id="aiSuggestionsResult" class="ai-results"></div>
        </div>
        <hr style="border-color: var(--glass-border); margin: 1.5rem 0;">
    `;

    if (suggestions && suggestions.length) {
        // Priority badges and colors
        const priorityConfig = {
            high: { badge: '🔴 CRITICAL', class: 'priority-high' },
            medium: { badge: '🟡 RECOMMENDED', class: 'priority-medium' },
            low: { badge: '🟢 NICE TO HAVE', class: 'priority-low' }
        };

        // Sort by priority
        const sorted = [...suggestions].sort((a, b) => {
            const order = { high: 0, medium: 1, low: 2 };
            return (order[a.priority] || 2) - (order[b.priority] || 2);
        });

        html += sorted.map(suggestion => {
            const priority = priorityConfig[suggestion.priority] || priorityConfig.medium;
            return `
                <div class="suggestion-item ${priority.class}">
                    <div class="suggestion-header">
                        <span class="suggestion-category">${suggestion.category}</span>
                        <span class="suggestion-priority">${priority.badge}</span>
                    </div>
                    <div class="suggestion-text">${suggestion.text}</div>
                    <div class="suggestion-example">
                        💡 <strong>Example:</strong> ${suggestion.example}
                    </div>
                </div>
            `;
        }).join('');
    }

    container.innerHTML = html;
}

async function generateAISuggestions(type) {
    const resultContainer = document.getElementById('aiSuggestionsResult');
    const user = IGGrowthHub.getSession('user');

    if (!user) return;

    resultContainer.innerHTML = '<div class="loading-ai">🔄 Generating suggestions with AI...</div>';

    try {
        const response = await fetch(
            `${IGGrowthHub.API_BASE}/ai/suggestions?username=${encodeURIComponent(user.username)}&type=${type}`
        );
        const data = await response.json();

        if (data.error) {
            resultContainer.innerHTML = `<div class="ai-error">❌ ${data.error}</div>`;
            return;
        }

        if (type === 'bio') {
            resultContainer.innerHTML = renderBioSuggestions(data.suggestions);
        } else if (type === 'caption') {
            resultContainer.innerHTML = renderCaptionSuggestions(data.suggestions);
        } else if (type === 'hashtag') {
            resultContainer.innerHTML = renderHashtagStrategy(data.strategy);
        }

    } catch (error) {
        console.error('AI error:', error);
        resultContainer.innerHTML = '<div class="ai-error">❌ Failed to generate suggestions</div>';
    }
}

function renderBioSuggestions(suggestions) {
    if (!suggestions || !suggestions.length) {
        return '<div class="ai-empty">No suggestions generated</div>';
    }

    return `
        <h4>📄 Bio Suggestions (Click to copy)</h4>
        ${suggestions.map((s, i) => `
            <div class="ai-suggestion-card" onclick="copyToClipboard(this, '${escapeForAttr(s.suggested)}')">
                <div class="ai-suggestion-num">#${i + 1}</div>
                <div class="ai-suggestion-content">
                    <pre class="ai-copyable">${s.suggested}</pre>
                    <span class="ai-reason">💡 ${s.reason}</span>
                </div>
                <span class="copy-badge">📋 Click to copy</span>
            </div>
        `).join('')}
    `;
}

function renderCaptionSuggestions(suggestions) {
    if (!suggestions || !suggestions.length) {
        return '<div class="ai-empty">No suggestions generated</div>';
    }

    return `
        <h4>📝 Caption Templates (Click to copy)</h4>
        ${suggestions.map((s, i) => `
            <div class="ai-suggestion-card" onclick="copyToClipboard(this, '${escapeForAttr(s.caption)}')">
                <div class="ai-suggestion-num">#${i + 1}</div>
                <div class="ai-suggestion-content">
                    <pre class="ai-copyable">${s.caption}</pre>
                    <span class="ai-reason">💡 ${s.reason}</span>
                </div>
                <span class="copy-badge">📋 Click to copy</span>
            </div>
        `).join('')}
    `;
}

function renderHashtagStrategy(strategy) {
    if (!strategy || !Object.keys(strategy).length) {
        return '<div class="ai-empty">No strategy generated</div>';
    }

    return `
        <h4># Hashtag Strategy (Click each section to copy)</h4>
        
        <div class="ai-suggestion-card" onclick="copyToClipboard(this, '${(strategy.niche || []).join(' ')}')">
            <div class="hashtag-category">🎯 Niche (Under 100K)</div>
            <pre class="ai-copyable">${(strategy.niche || []).join(' ')}</pre>
            <span class="copy-badge">📋 Copy</span>
        </div>
        
        <div class="ai-suggestion-card" onclick="copyToClipboard(this, '${(strategy.medium || []).join(' ')}')">
            <div class="hashtag-category">📊 Medium (100K-500K)</div>
            <pre class="ai-copyable">${(strategy.medium || []).join(' ')}</pre>
            <span class="copy-badge">📋 Copy</span>
        </div>
        
        <div class="ai-suggestion-card" onclick="copyToClipboard(this, '${(strategy.broad || []).join(' ')}')">
            <div class="hashtag-category">🌍 Broad (500K+)</div>
            <pre class="ai-copyable">${(strategy.broad || []).join(' ')}</pre>
            <span class="copy-badge">📋 Copy</span>
        </div>
        
        <div class="ai-suggestion-card" onclick="copyToClipboard(this, '${strategy.branded || ''}')">
            <div class="hashtag-category">⭐ Branded</div>
            <pre class="ai-copyable">${strategy.branded || 'N/A'}</pre>
            <span class="copy-badge">📋 Copy</span>
        </div>
    `;
}

function escapeForAttr(str) {
    return (str || '').replace(/'/g, "\\'").replace(/"/g, "&quot;").replace(/\n/g, "\\n");
}

function copyToClipboard(element, text) {
    // Replace escaped newlines
    const cleanText = text.replace(/\\n/g, '\n').replace(/&quot;/g, '"');

    navigator.clipboard.writeText(cleanText).then(() => {
        const badge = element.querySelector('.copy-badge');
        if (badge) {
            badge.textContent = '✅ Copied!';
            badge.classList.add('copied');
            setTimeout(() => {
                badge.textContent = '📋 Click to copy';
                badge.classList.remove('copied');
            }, 2000);
        }
        IGGrowthHub.showToast('Copied to clipboard!', 'success');
    }).catch(() => {
        IGGrowthHub.showToast('Failed to copy', 'error');
    });
}

// ============================================
// PLATFORM & ACTION CONTROLS
// ============================================

function initPlatformControls() {
    // Platform selection
    document.querySelectorAll('[data-platform]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('[data-platform]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedPlatform = btn.dataset.platform;
        });
    });

    // Intensity slider
    const slider = document.getElementById('intensitySlider');
    if (slider) {
        slider.addEventListener('input', (e) => {
            intensity = parseInt(e.target.value);
        });
    }
}

// ============================================
// KEYWORD MANAGEMENT
// ============================================

function initKeywordControls() {
    const keywordInput = document.getElementById('keywordInput');
    const addKeywordBtn = document.getElementById('addKeywordBtn');

    if (addKeywordBtn && keywordInput) {
        addKeywordBtn.addEventListener('click', addKeyword);
        keywordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') addKeyword();
        });
    }
}

function addKeyword() {
    const input = document.getElementById('keywordInput');
    const value = input.value.trim();

    if (!value) return;

    if (targetKeywords.length >= 10) {
        IGGrowthHub.showToast('Maximum 10 keywords allowed', 'error');
        return;
    }

    // Allow duplicates if user really wants, or block them? Let's block exact dupes
    if (targetKeywords.includes(value)) {
        IGGrowthHub.showToast('Keyword already added', 'warning');
        return;
    }

    targetKeywords.push(value);
    input.value = '';
    renderKeywords();
}

function removeKeyword(keyword) {
    targetKeywords = targetKeywords.filter(k => k !== keyword);
    renderKeywords();
}

function renderKeywords() {
    const list = document.getElementById('keywordsList');
    if (!list) return;

    list.innerHTML = targetKeywords.map(keyword => `
        <span class="keyword-tag">
            ${keyword}
            <span class="remove-keyword" onclick="removeKeyword('${keyword}')">&times;</span>
        </span>
    `).join('');
}

function initActionCheckboxes() {
    // New chip-based action selection
    const chips = document.querySelectorAll('.action-chip');
    const commentGroup = document.getElementById('commentTemplatesGroup');
    const intensitySlider = document.getElementById('intensitySlider');
    const intensityValue = document.getElementById('intensityValue');

    // Intensity value labels
    const intensityLabels = { 1: 'Conservative', 2: 'Moderate', 3: 'Aggressive' };

    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            chip.classList.toggle('active');

            // Update selected actions
            selectedActions = Array.from(document.querySelectorAll('.action-chip.active'))
                .map(c => c.dataset.action);

            // Show/hide comment templates
            if (selectedActions.includes('comments')) {
                commentGroup.style.display = 'block';
            } else {
                commentGroup.style.display = 'none';
            }
        });
    });

    // Update intensity label when slider changes
    if (intensitySlider && intensityValue) {
        intensitySlider.addEventListener('input', (e) => {
            intensity = parseInt(e.target.value);
            intensityValue.textContent = intensityLabels[intensity] || 'Conservative';
        });
    }
}

// ============================================
// BOOST CONTROLS
// ============================================

function initBoostControls() {
    const boostBtn = document.getElementById('boostBtn');
    const stopBtn = document.getElementById('stopBtn');

    if (boostBtn) {
        boostBtn.addEventListener('click', startBoost);
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', stopBoost);
    }
}

async function startBoost() {
    // Validations
    if (selectedActions.length === 0) {
        IGGrowthHub.showToast('Please select at least one action type', 'error');
        return;
    }

    if (!targetKeywords || targetKeywords.length === 0) {
        IGGrowthHub.showToast('Please add at least one keyword or hashtag', 'error');
        return;
    }

    const statusBadge = document.getElementById('statusBadge');
    const statusText = document.getElementById('statusText');
    const boostBtn = document.getElementById('boostBtn');
    const stopBtn = document.getElementById('stopBtn');
    const progressPanel = document.getElementById('progressPanel');

    // Get comment templates if comments selected
    let commentTemplates = [];
    if (selectedActions.includes('comments')) {
        const textarea = document.getElementById('commentTemplates');
        if (textarea && textarea.value.trim()) {
            commentTemplates = textarea.value.trim().split('\n').filter(c => c.trim());
        }
        if (commentTemplates.length === 0) {
            IGGrowthHub.showToast('Please add comment templates', 'error');
            return;
        }
    }

    isBoostRunning = true;

    // Update UI
    if (statusBadge) statusBadge.classList.add('running');
    if (statusText) statusText.textContent = 'Running...';
    boostBtn.style.display = 'none';
    stopBtn.style.display = 'flex';
    if (progressPanel) progressPanel.style.display = 'block';

    IGGrowthHub.showToast(`Starting boost on ${selectedPlatform}...`, 'info');

    try {
        const user = IGGrowthHub.getSession('user');
        const response = await fetch(`${IGGrowthHub.API_BASE}/boost/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: user.username,
                platform: selectedPlatform,
                action_types: selectedActions,
                intensity: intensity,
                comment_templates: commentTemplates,
                target_hashtags: targetKeywords // Send frontend keywords
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            currentTaskId = data.task_id;

            // Display task ID in UI
            const taskIdEl = document.getElementById('taskIdDisplay');
            if (taskIdEl) taskIdEl.textContent = data.task_id;

            document.getElementById('progressTotal').textContent = data.target_count || '...';
            IGGrowthHub.showToast('Boost started!', 'success');
            startProgressPolling();
        } else {
            throw new Error(data.error || 'Failed to start boost');
        }
    } catch (error) {
        console.error('Boost error:', error);
        IGGrowthHub.showToast(error.message || 'Failed to start boost', 'error');
        resetBoostUI();
    }
}

async function stopBoost() {
    if (currentTaskId) {
        try {
            await fetch(`${IGGrowthHub.API_BASE}/boost/stop`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task_id: currentTaskId
                })
            });
        } catch (error) {
            console.error('Stop error:', error);
        }
    }

    isBoostRunning = false;
    if (progressPollInterval) {
        clearInterval(progressPollInterval);
        progressPollInterval = null;
    }

    IGGrowthHub.showToast('Boost stopped - showing report', 'info');

    // Show report of what was done
    await showReport();

    resetBoostUI();
}

function resetBoostUI() {
    const statusBadge = document.getElementById('statusBadge');
    const statusText = document.getElementById('statusText');
    const boostBtn = document.getElementById('boostBtn');
    const stopBtn = document.getElementById('stopBtn');
    const progressPanel = document.getElementById('progressPanel');

    isBoostRunning = false;
    if (statusBadge) statusBadge.classList.remove('running');
    if (statusText) statusText.textContent = 'Ready';
    boostBtn.style.display = 'flex';
    stopBtn.style.display = 'none';
    if (progressPanel) progressPanel.style.display = 'none';
}

// ============================================
// PROGRESS POLLING
// ============================================

function startProgressPolling() {
    if (progressPollInterval) {
        clearInterval(progressPollInterval);
    }

    progressPollInterval = setInterval(async () => {
        if (!currentTaskId || !isBoostRunning) {
            clearInterval(progressPollInterval);
            return;
        }

        try {
            const response = await fetch(`${IGGrowthHub.API_BASE}/boost/progress/${currentTaskId}`);
            const data = await response.json();

            if (response.ok) {
                updateProgressUI(data);

                // Check if completed
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(progressPollInterval);
                    progressPollInterval = null;

                    if (data.status === 'completed') {
                        IGGrowthHub.showToast('Boost completed!', 'success');
                        showReport();
                    } else {
                        IGGrowthHub.showToast('Boost failed', 'error');
                    }

                    resetBoostUI();
                }
            }
        } catch (error) {
            console.error('Progress poll error:', error);
        }
    }, 2000); // Poll every 2 seconds
}

function updateProgressUI(progress) {
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressCompleted = document.getElementById('progressCompleted');
    const progressTotal = document.getElementById('progressTotal');
    const statusText = document.getElementById('statusText');
    const feedItems = document.getElementById('feedItems');

    // Check if still in extraction phase
    const isExtracting = progress.extraction_phase === true;
    const extractionPercent = progress.extraction_progress || 0;

    if (isExtracting) {
        // Show extraction progress
        if (progressBar) progressBar.style.width = `${extractionPercent}%`;
        if (progressPercent) progressPercent.textContent = `${extractionPercent}%`;
        if (progressCompleted) progressCompleted.textContent = '0';
        if (progressTotal) progressTotal.textContent = '—';
        if (statusText) statusText.textContent = `Collecting... ${extractionPercent}%`;
    } else {
        // Show action progress
        if (progressBar) progressBar.style.width = `${progress.percentage}%`;
        if (progressPercent) progressPercent.textContent = `${progress.percentage}%`;
        if (progressCompleted) progressCompleted.textContent = progress.completed;
        if (progressTotal) progressTotal.textContent = progress.total;
        if (statusText) statusText.textContent = `${progress.completed}/${progress.total} actions`;
    }

    // Update live status message
    const statusMessageText = document.getElementById('statusMessageText');
    if (statusMessageText && progress.status_message) {
        statusMessageText.textContent = progress.status_message;
    }

    // Update daily limits from backend data
    if (progress.limits) {
        const types = {
            'likes': 'likesRemaining',
            'follows': 'followsRemaining',
            'comments': 'commentsRemaining',
            'views': 'viewsRemaining'
        };

        for (const [type, elementId] of Object.entries(types)) {
            const el = document.getElementById(elementId);
            if (el && progress.limits[type]) {
                const used = progress.limits[type].used.daily || 0;
                const limit = progress.limits[type].limits.per_day || 300;
                el.textContent = `${used} / ${limit}`;
            }
        }
    }

    // Update action feed with recent actions
    if (progress.recent_actions && progress.recent_actions.length > 0 && feedItems) {
        const actionIcons = {
            'likes': '❤️',
            'follows': '➕',
            'comments': '💬',
            'views': '👁️'
        };

        feedItems.innerHTML = progress.recent_actions.reverse().map(action => {
            const time = new Date(action.timestamp).toLocaleTimeString();
            return `
                <div class="feed-item">
                    <span class="feed-item-icon">${actionIcons[action.action_type] || '✓'}</span>
                    <span class="feed-item-text">${action.action_type} → @${action.target_username}</span>
                    <span class="feed-item-time">${time}</span>
                </div>
            `;
        }).join('');
    }
}

// ============================================
// REPORT MODAL
// ============================================

function initModal() {
    const closeBtn = document.getElementById('closeReportModal');
    const modal = document.getElementById('reportModal');

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    // Close on backdrop click
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
}

// ============================================
// NAVIGATION & VIEWS
// ============================================

function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-item[data-view]');
    const views = document.querySelectorAll('.view-section');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update buttons
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update views
            const viewId = `view-${btn.dataset.view}`;
            views.forEach(view => {
                if (view.id === viewId) {
                    view.classList.add('active');
                    view.style.display = 'block'; // Explicitly show
                } else {
                    view.classList.remove('active');
                    view.style.display = 'none'; // Explicitly hide
                }
            });

            // Load specific data
            if (btn.dataset.view === 'analytics') {
                loadAnalytics();
            } else if (btn.dataset.view === 'reports') {
                loadReportsView();
            }
        });
    });
}

// ============================================
// ANALYTICS
// ============================================

let activityChart = null;
let impactChart = null;

async function loadAnalytics() {
    const user = IGGrowthHub.getSession('user');
    if (!user) return;

    try {
        const response = await fetch(`${IGGrowthHub.API_BASE}/analytics?username=${user.username}`);
        const data = await response.json();

        if (data.error) throw new Error(data.error);

        renderPredictions(data);
        renderCharts(data);
        renderGrowthTips(data);

    } catch (error) {
        console.error('Analytics error:', error);
        // Don't show toast on simple empty state, but log it
    }
}

function renderPredictions(data) {
    // Populate stat cards with new analytics data
    if (document.getElementById('totalActionsVal')) {
        document.getElementById('totalActionsVal').textContent = data.total_actions || 0;
    }
    if (document.getElementById('totalSuccessVal')) {
        document.getElementById('totalSuccessVal').textContent = data.total_success || 0;
    }

    // Backend provides pre-calculated predictions
    if (data.predictions) {
        if (document.getElementById('futureScopeText')) {
            document.getElementById('futureScopeText').textContent = data.predictions.future_scope;
        }
        if (document.getElementById('estGainVal')) {
            document.getElementById('estGainVal').textContent = `+${data.predictions.est_followers_gained}`;
        }
        if (document.getElementById('successRateVal')) {
            document.getElementById('successRateVal').textContent = data.predictions.success_rate || '--';
        }
        if (document.getElementById('daysActiveVal')) {
            document.getElementById('daysActiveVal').textContent = data.predictions.days_active || '--';
        }
        if (document.getElementById('dailyAvgVal')) {
            document.getElementById('dailyAvgVal').textContent = data.predictions.daily_avg_success || '--';
        }
        if (document.getElementById('predInsight')) {
            document.getElementById('predInsight').textContent = data.predictions.insight || 'Based on 3% follow-back rate';
        }
    }
}

function renderGrowthTips(data) {
    const container = document.getElementById('growthTips');
    if (!container) return;

    const tips = data.growth_tips || [];

    if (tips.length === 0) {
        container.innerHTML = '<div class="tip-card">🚀 Start boosting to unlock personalized tips!</div>';
        return;
    }

    container.innerHTML = tips.map(t => `
        <div class="tip-card ${t.type}">
            <span class="tip-icon">${t.icon}</span>
            <span class="tip-text">${t.tip}</span>
        </div>
    `).join('');
}

function renderCharts(data) {
    const ctxActivity = document.getElementById('activityChart').getContext('2d');
    const ctxImpact = document.getElementById('impactChart').getContext('2d');

    // Prepare Daily Activity Data from Backend Format
    // Backend returns: activity_chart: { labels: [], success: [], skipped: [] }
    const chartData = data.activity_chart || { labels: [], success: [], skipped: [] };

    // Format dates
    const activityLabels = (chartData.labels || []).map(dateStr => {
        const d = new Date(dateStr);
        return isNaN(d) ? dateStr : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    });

    const activityValues = chartData.success || [];

    // Prepare Impact Data (Success vs Skip) - Top level keys
    const successCount = data.total_success || 0;
    const skipCount = data.total_skipped || 0;

    // Destroy old charts if exist
    if (activityChart) activityChart.destroy();
    if (impactChart) impactChart.destroy();

    // Create Activity Chart
    activityChart = new Chart(ctxActivity, {
        type: 'line',
        data: {
            labels: activityLabels,
            datasets: [{
                label: 'Successful Actions',
                data: activityValues,
                borderColor: '#14b8a6',
                backgroundColor: 'rgba(20, 184, 166, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });

    // Create Impact Chart
    impactChart = new Chart(ctxImpact, {
        type: 'doughnut',
        data: {
            labels: ['Success', 'Skipped'],
            datasets: [{
                data: [successCount, skipCount],
                backgroundColor: ['#22c55e', '#ef4444'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#94a3b8' } }
            }
        }
    });
}

// ============================================
// REPORTS VIEW
// ============================================

async function loadReportsView() {
    const container = document.getElementById('fullReportsList');
    container.innerHTML = '<div class="loading-spinner">Loading reports...</div>';

    try {
        const response = await fetch(`${IGGrowthHub.API_BASE}/reports`);
        const data = await response.json();

        if (data.reports && data.reports.length > 0) {
            // Compact row-based layout
            let html = '<div class="reports-compact-list">';
            html += data.reports.map(report => renderReportRow(report)).join('');
            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="text-center text-muted">No reports found. Start a boost!</div>';
        }
    } catch (error) {
        console.error("Reports Load Error", error);
        container.innerHTML = '<div class="error-msg">Failed to load reports</div>';
    }
}

function renderReportRow(report) {
    const date = new Date(report.created_at || report.completed_at).toLocaleDateString();
    const time = new Date(report.created_at || report.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const statusClass = report.status ? report.status.toLowerCase() : 'unknown';
    const successCount = report.successful_actions || 0;
    const skippedCount = report.skipped_actions || 0;
    const totalActions = report.total_actions || 0;

    // Compact row style - click opens in NEW TAB
    return `
        <div class="report-row-compact" onclick="openReportInNewTab('${report.task_id}')">
            <div class="report-row-left">
                <span class="report-row-date">${date} ${time}</span>
                <span class="status-badge-sm ${statusClass}">${report.status || '?'}</span>
            </div>
            <div class="report-row-stats">
                <span class="stat-mini">${totalActions} <small>total</small></span>
                <span class="stat-mini success">${successCount} <small>✓</small></span>
                <span class="stat-mini warn">${skippedCount} <small>⏭</small></span>
            </div>
            <div class="report-row-action">
                <span class="view-link">View →</span>
            </div>
        </div>
    `;
}

// Open report detail in NEW TAB
function openReportInNewTab(taskId) {
    // Create a new window with the report details
    const url = `report_detail.html?task_id=${taskId}`;
    window.open(url, '_blank');
}

// Fallback: Show in modal if report_detail.html doesn't exist
async function showReportDetail(taskId) {
    try {
        const response = await fetch(`${IGGrowthHub.API_BASE}/boost/report/${taskId}`);
        const report = await response.json();

        if (!response.ok) throw new Error(report.error);

        renderReportDetailContent(report);
        document.getElementById('reportModal').style.display = 'flex';
    } catch (error) {
        IGGrowthHub.showToast('Could not load details', 'error');
    }
}

function renderReportDetailContent(report) {
    const content = document.getElementById('reportContent');
    const actions = report.actions || [];

    const skips = actions.filter(a => a.status === 'skipped');
    const success = actions.filter(a => a.status === 'success');

    let durationText = 'N/A';
    if (report.summary && report.summary.duration_seconds) {
        const secs = Math.round(report.summary.duration_seconds);
        const mins = Math.floor(secs / 60);
        const remSecs = secs % 60;
        durationText = mins > 0 ? `${mins}m ${remSecs}s` : `${secs}s`;
    }

    // TABLE format with columns: Username, Post URL, Action, Status, Reason
    content.innerHTML = `
        <div class="report-summary-stats" style="display: flex; justify-content: space-between; margin-bottom: 1rem; color: var(--text-muted); font-size: 0.9rem;">
            <span>⏱️ Duration: <strong>${durationText}</strong></span>
            <span>📅 ${new Date(report.created_at).toLocaleString()}</span>
        </div>
        <div class="report-summary-grid">
             <div class="stat-box"><h3>${actions.length}</h3><small>Total</small></div>
             <div class="stat-box success"><h3>${success.length}</h3><small>Success</small></div>
             <div class="stat-box warn"><h3>${skips.length}</h3><small>Skipped</small></div>
        </div>

        <h4 class="mt-4">📋 Activity Log (Table)</h4>
        <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
            <table class="report-detail-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Username</th>
                        <th>Post URL</th>
                        <th>Action</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${actions.map(action => {
        const isSkip = action.status === 'skipped';
        const statusClass = isSkip ? 'text-warn' : 'text-success';
        const statusText = isSkip ? `Skipped: ${action.reason || 'N/A'}` : 'Success';
        const postUrl = action.target_url || '#';
        const shortUrl = postUrl.replace('https://www.instagram.com', '');
        return `
                            <tr class="${isSkip ? 'row-skipped' : ''}">
                                <td>${new Date(action.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                                <td><strong>@${action.target_username || 'unknown'}</strong></td>
                                <td><a href="${postUrl}" target="_blank" class="post-link">${shortUrl}</a></td>
                                <td>${action.action_type}</td>
                                <td class="${statusClass}">${statusText}</td>
                            </tr>
                        `;
    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// ============================================
// MODAL & LOGOUT (Existing adapted)
// ============================================

function initModal() {
    const modal = document.getElementById('reportModal');
    const closeBtn = document.getElementById('closeReportModal');

    if (closeBtn) closeBtn.onclick = () => modal.style.display = 'none';
    if (modal) modal.onclick = (e) => { if (e.target === modal) modal.style.display = 'none'; };
}

function initLogout() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            // ... existing logout logic ...
            IGGrowthHub.clearSession();
            window.location.href = 'index.html';
        });
    }
}

// Ensure global access for onclick events
window.showReportDetail = showReportDetail;

// Helper to show report for current task
async function showReport() {
    if (currentTaskId) {
        await showReportDetail(currentTaskId);
    }
}
window.showReport = showReport;
