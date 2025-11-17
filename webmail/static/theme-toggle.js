/**
 * Privra Mail - Multi-Level Theme System
 * 7 modes: light-1, light-2, light-3, dark-1, dark-2, dark-3, auto
 */

class ThemeManager {
    constructor() {
        this.themes = [
            'auto',      // System default
            'light-1',   // Bright
            'light-2',   // Dim
            'light-3',   // Dimmer
            'dark-1',    // Dim dark
            'dark-2',    // Dimmer dark
            'dark-3'     // Full black
        ];

        this.themeIcons = {
            'auto': '🌓',
            'light-1': '☀️',
            'light-2': '🌤️',
            'light-3': '⛅',
            'dark-1': '🌙',
            'dark-2': '🌑',
            'dark-3': '⚫'
        };

        this.themeNames = {
            'auto': 'Auto',
            'light-1': 'Light',
            'light-2': 'Dim',
            'light-3': 'Dimmer',
            'dark-1': 'Dark',
            'dark-2': 'Darker',
            'dark-3': 'Black'
        };

        this.currentThemeIndex = 0;
        this.init();
    }

    init() {
        // Load saved theme or default to auto
        const savedTheme = localStorage.getItem('privra-theme') || 'auto';
        this.currentThemeIndex = this.themes.indexOf(savedTheme);
        if (this.currentThemeIndex === -1) this.currentThemeIndex = 0;

        this.applyTheme(this.themes[this.currentThemeIndex]);

        // Listen for system theme changes
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (this.themes[this.currentThemeIndex] === 'auto') {
                    this.applyTheme('auto');
                }
            });
        }
    }

    applyTheme(theme) {
        const body = document.body;

        if (theme === 'auto') {
            // Detect system preference
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            const actualTheme = prefersDark ? 'dark-1' : 'light-1';
            body.setAttribute('data-theme', actualTheme);
        } else {
            body.setAttribute('data-theme', theme);
        }

        // Save preference
        localStorage.setItem('privra-theme', theme);

        // Update UI
        this.updateToggleButton();
    }

    cycleTheme() {
        // Move to next theme
        this.currentThemeIndex = (this.currentThemeIndex + 1) % this.themes.length;
        const nextTheme = this.themes[this.currentThemeIndex];

        this.applyTheme(nextTheme);

        // Show notification
        this.showThemeNotification(nextTheme);
    }

    updateToggleButton() {
        const currentTheme = this.themes[this.currentThemeIndex];
        const button = document.getElementById('theme-toggle-btn');
        const indicator = document.getElementById('theme-indicator');

        if (button) {
            button.innerHTML = this.themeIcons[currentTheme];
        }

        if (indicator) {
            indicator.textContent = this.themeNames[currentTheme];
        }
    }

    showThemeNotification(theme) {
        // Create floating notification
        const notification = document.createElement('div');
        notification.className = 'theme-notification';
        notification.innerHTML = `
            <div style="
                position: fixed;
                top: 80px;
                right: 20px;
                background: var(--glass-bg);
                backdrop-filter: blur(10px);
                border: 1px solid var(--glass-border);
                padding: 1rem 1.5rem;
                border-radius: 12px;
                box-shadow: 0 10px 30px var(--shadow);
                z-index: 9999;
                animation: slideInRight 0.3s ease-out;
                display: flex;
                align-items: center;
                gap: 1rem;
                color: var(--text-primary);
            ">
                <span style="font-size: 2rem;">${this.themeIcons[theme]}</span>
                <div>
                    <div style="font-weight: 600;">Theme Changed</div>
                    <div style="font-size: 0.85rem; opacity: 0.8;">${this.themeNames[theme]} Mode</div>
                </div>
            </div>
        `;

        document.body.appendChild(notification);

        // Add slide in animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideInRight {
                from {
                    opacity: 0;
                    transform: translateX(100px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
            @keyframes slideOutRight {
                from {
                    opacity: 1;
                    transform: translateX(0);
                }
                to {
                    opacity: 0;
                    transform: translateX(100px);
                }
            }
        `;
        document.head.appendChild(style);

        // Remove after 2 seconds
        setTimeout(() => {
            notification.firstElementChild.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => {
                notification.remove();
                style.remove();
            }, 300);
        }, 2000);
    }

    getCurrentTheme() {
        return this.themes[this.currentThemeIndex];
    }

    getActualTheme() {
        const theme = this.getCurrentTheme();
        if (theme === 'auto') {
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            return prefersDark ? 'dark-1' : 'light-1';
        }
        return theme;
    }
}

// Initialize theme manager
const themeManager = new ThemeManager();

// Expose global function for button
function toggleTheme() {
    themeManager.cycleTheme();
}
