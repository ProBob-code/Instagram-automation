/**
 * IG Growth Hub - Frontend Application
 * Main JavaScript for Login & Core Functionality
 */

// API Configuration - uses relative path for deployment flexibility
const API_BASE = '/api';

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${getToastIcon(type)}</span>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Auto remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function getToastIcon(type) {
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    return icons[type] || icons.info;
}

/**
 * Format large numbers (e.g., 1500 -> 1.5K)
 */
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

/**
 * Store data in session storage
 */
function storeSession(key, value) {
    sessionStorage.setItem(key, JSON.stringify(value));
}

/**
 * Get data from session storage
 */
function getSession(key) {
    const data = sessionStorage.getItem(key);
    return data ? JSON.parse(data) : null;
}

/**
 * Clear session
 */
function clearSession() {
    sessionStorage.clear();
}

// ============================================
// LOGIN PAGE FUNCTIONALITY
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on login page
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        initLoginPage();
    }
});

function initLoginPage() {
    const loginForm = document.getElementById('loginForm');
    const togglePassword = document.getElementById('togglePassword');
    const passwordField = document.getElementById('password');
    const submitBtn = document.getElementById('submitBtn');
    const errorMessage = document.getElementById('errorMessage');

    // Toggle password visibility
    if (togglePassword && passwordField) {
        togglePassword.addEventListener('click', () => {
            const type = passwordField.type === 'password' ? 'text' : 'password';
            passwordField.type = type;
            togglePassword.textContent = type === 'password' ? '👁️' : '🙈';
        });
    }

    // Handle form submission
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;

            // Validate inputs
            if (!username || !password) {
                showError('Please enter both username and password');
                return;
            }

            // Show loading state with progress
            setLoading(true, 'Connecting to Instagram... (0%)');
            hideError();

            // Progress simulation for user feedback
            const tasks = [
                { msg: 'Connecting to Instagram...', pct: 10 },
                { msg: 'Starting secure browser...', pct: 20 },
                { msg: 'Navigating to login page...', pct: 30 },
                { msg: 'Authenticating...', pct: 50 },
                { msg: 'Verifying credentials...', pct: 60 },
                { msg: 'Analyzing your profile...', pct: 75 },
                { msg: 'Extracting profile data...', pct: 85 },
                { msg: 'Calculating SEO score...', pct: 95 }
            ];

            let taskIndex = 0;
            const progressInterval = setInterval(() => {
                if (taskIndex < tasks.length) {
                    setLoading(true, `${tasks[taskIndex].msg} (${tasks[taskIndex].pct}%)`);
                    taskIndex++;
                }
            }, 2500);

            try {
                // Call login API
                const response = await fetch(`${API_BASE}/login`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ username, password })
                });

                clearInterval(progressInterval);
                const data = await response.json();

                if (data.requires_2fa) {
                    // Show 2FA modal
                    setLoading(false);
                    show2FAModal(username);
                } else if (response.ok && data.success) {
                    // Store session data
                    storeSession('user', {
                        username: username,
                        loggedIn: true,
                        loginTime: new Date().toISOString()
                    });

                    // Store profile data if available
                    if (data.profile) {
                        storeSession('profile', data.profile);
                    }
                    if (data.score) {
                        storeSession('score', data.score);
                    }
                    if (data.suggestions) {
                        storeSession('suggestions', data.suggestions);
                    }

                    // Redirect to dashboard
                    window.location.href = 'dashboard.html';
                } else {
                    showError(data.error || 'Login failed. Please check your credentials.');
                }
            } catch (error) {
                clearInterval(progressInterval);
                console.error('Login error:', error);

                // For demo/development: allow login without backend
                if (error.message.includes('Failed to fetch')) {
                    showError('Cannot connect to server. Make sure the Flask server is running.');
                } else {
                    showError('Connection error. Please try again.');
                }
            } finally {
                setLoading(false);
            }
        });
    }

    // 2FA Modal functionality
    function show2FAModal(username) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('twoFaModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'twoFaModal';
            modal.className = 'modal-overlay';
            modal.innerHTML = `
                <div class="modal-content glass-card">
                    <h3>🔐 Two-Factor Authentication</h3>
                    <p>Enter the verification code sent to your device</p>
                    <input type="text" id="twoFaCode" class="input-field" 
                           placeholder="Enter 6-digit code" maxlength="8" autocomplete="one-time-code">
                    <div class="modal-buttons">
                        <button type="button" id="cancelTwoFa" class="btn btn-secondary">Cancel</button>
                        <button type="button" id="submitTwoFa" class="btn btn-primary">Verify</button>
                    </div>
                    <p id="twoFaError" class="error-text" style="display: none;"></p>
                </div>
            `;
            document.body.appendChild(modal);

            // Add modal styles if not present
            if (!document.getElementById('modalStyles')) {
                const styles = document.createElement('style');
                styles.id = 'modalStyles';
                styles.textContent = `
                    .modal-overlay {
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.7);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        z-index: 1000;
                        backdrop-filter: blur(5px);
                    }
                    .modal-content {
                        padding: 2rem;
                        border-radius: 16px;
                        max-width: 400px;
                        text-align: center;
                    }
                    .modal-content h3 {
                        margin-bottom: 0.5rem;
                        font-size: 1.5rem;
                    }
                    .modal-content p {
                        color: rgba(255, 255, 255, 0.7);
                        margin-bottom: 1.5rem;
                    }
                    .modal-content .input-field {
                        width: 100%;
                        padding: 1rem;
                        font-size: 1.5rem;
                        text-align: center;
                        letter-spacing: 0.5rem;
                        margin-bottom: 1rem;
                    }
                    .modal-buttons {
                        display: flex;
                        gap: 1rem;
                    }
                    .modal-buttons .btn {
                        flex: 1;
                        padding: 0.8rem;
                    }
                    .btn-secondary {
                        background: rgba(255, 255, 255, 0.1);
                        border: 1px solid rgba(255, 255, 255, 0.2);
                    }
                    .error-text {
                        color: #ff6b6b;
                        margin-top: 1rem;
                    }
                `;
                document.head.appendChild(styles);
            }
        }

        modal.style.display = 'flex';
        const codeInput = document.getElementById('twoFaCode');
        codeInput.value = '';
        codeInput.focus();

        // Handle cancel
        document.getElementById('cancelTwoFa').onclick = () => {
            modal.style.display = 'none';
        };

        // Handle submit
        document.getElementById('submitTwoFa').onclick = () => submit2FA(username);

        // Handle enter key
        codeInput.onkeypress = (e) => {
            if (e.key === 'Enter') {
                submit2FA(username);
            }
        };
    }

    async function submit2FA(username) {
        const code = document.getElementById('twoFaCode').value.trim();
        const errorEl = document.getElementById('twoFaError');

        if (!code || code.length < 6) {
            errorEl.textContent = 'Please enter a valid verification code';
            errorEl.style.display = 'block';
            return;
        }

        const submitBtn = document.getElementById('submitTwoFa');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Verifying...';
        errorEl.style.display = 'none';

        try {
            const response = await fetch(`${API_BASE}/submit-2fa`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, code })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // Store session data
                storeSession('user', {
                    username: username,
                    loggedIn: true,
                    loginTime: new Date().toISOString()
                });

                if (data.profile) storeSession('profile', data.profile);
                if (data.score) storeSession('score', data.score);
                if (data.suggestions) storeSession('suggestions', data.suggestions);

                // Redirect to dashboard
                window.location.href = 'dashboard.html';
            } else {
                errorEl.textContent = data.error || '2FA verification failed';
                errorEl.style.display = 'block';
            }
        } catch (error) {
            errorEl.textContent = 'Connection error. Please try again.';
            errorEl.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Verify';
        }
    }

    function setLoading(loading, message = 'Analyzing...') {
        if (submitBtn) {
            submitBtn.disabled = loading;
            if (loading) {
                submitBtn.innerHTML = `<span class="spinner"></span>${message}`;
            } else {
                submitBtn.innerHTML = '<span class="btn-text">Analyze My Profile</span>';
            }
        }
    }

    function showError(message) {
        if (errorMessage) {
            errorMessage.textContent = message;
            errorMessage.style.display = 'block';
        }
    }

    function hideError() {
        if (errorMessage) {
            errorMessage.style.display = 'none';
        }
    }
}

// ============================================
// DEMO DATA GENERATORS
// ============================================

function generateDemoProfile(username) {
    return {
        username: username,
        name: username.charAt(0).toUpperCase() + username.slice(1),
        bio: 'Content creator | DM for collabs',
        posts: Math.floor(Math.random() * 200) + 50,
        followers: Math.floor(Math.random() * 5000) + 1000,
        following: Math.floor(Math.random() * 500) + 200,
        profilePic: null,
        isPrivate: false
    };
}

function generateDemoScore() {
    const bioScore = Math.floor(Math.random() * 10) + 10; // 10-20 out of 25
    const nameScore = Math.floor(Math.random() * 8) + 5; // 5-13 out of 15
    const contentScore = Math.floor(Math.random() * 10) + 8; // 8-18 out of 20
    const hashtagScore = Math.floor(Math.random() * 8) + 5; // 5-13 out of 15
    const engagementScore = Math.floor(Math.random() * 8) + 5; // 5-13 out of 15
    const completenessScore = Math.floor(Math.random() * 5) + 4; // 4-9 out of 10

    const total = bioScore + nameScore + contentScore + hashtagScore + engagementScore + completenessScore;

    return {
        total: total,
        breakdown: {
            bio: { score: bioScore, max: 25, status: bioScore >= 18 ? 'pass' : bioScore >= 12 ? 'warn' : 'fail' },
            name: { score: nameScore, max: 15, status: nameScore >= 10 ? 'pass' : nameScore >= 7 ? 'warn' : 'fail' },
            content: { score: contentScore, max: 20, status: contentScore >= 15 ? 'pass' : contentScore >= 10 ? 'warn' : 'fail' },
            hashtags: { score: hashtagScore, max: 15, status: hashtagScore >= 10 ? 'pass' : hashtagScore >= 7 ? 'warn' : 'fail' },
            engagement: { score: engagementScore, max: 15, status: engagementScore >= 10 ? 'pass' : engagementScore >= 7 ? 'warn' : 'fail' },
            completeness: { score: completenessScore, max: 10, status: completenessScore >= 8 ? 'pass' : completenessScore >= 5 ? 'warn' : 'fail' }
        }
    };
}

function generateDemoSuggestions() {
    return [
        {
            category: 'BIO',
            priority: 'high',
            text: 'Add niche-specific keywords to your bio',
            example: 'Instead of "Content creator", try "Fitness & lifestyle content | Helping men stay lean"'
        },
        {
            category: 'NAME FIELD',
            priority: 'medium',
            text: 'Optimize your name field for search',
            example: 'Add your niche: "Tushar | Fitness Creator"'
        },
        {
            category: 'HASHTAGS',
            priority: 'high',
            text: 'Use the 3-2-1 hashtag formula',
            example: '3 niche (#fitnesscreator), 2 broad (#reels), 1 location (#chennai)'
        },
        {
            category: 'CAPTIONS',
            priority: 'medium',
            text: 'Write SEO-friendly captions',
            example: 'Start with a searchable hook, not just emojis or quotes'
        },
        {
            category: 'EMAIL',
            priority: 'low',
            text: 'Add a contact email to your bio',
            example: 'Brands filter for creators with visible contact info'
        }
    ];
}

// Export for use in other scripts
window.IGGrowthHub = {
    showToast,
    formatNumber,
    storeSession,
    getSession,
    clearSession,
    API_BASE
};
