(function() {
    'use strict';
    if (window.__focuslens_edge_yt) return;
    window.__focuslens_edge_yt = true;

    function isStudyModeActive() {
        if (window.LockinSync && typeof window.LockinSync.isStudyMode === 'function') {
            return window.LockinSync.isStudyMode();
        }
        return false;
    }

    function getFormattedRemainingTime() {
        if (window.LockinSync && typeof window.LockinSync.getRemainingSeconds === 'function') {
            return window.LockinSync.formatTime(window.LockinSync.getRemainingSeconds());
        }
        return '--:--';
    }

    function killMedia() {
        try {
            var mediaElements = document.querySelectorAll('video, audio');
            for (var i = 0; i < mediaElements.length; i++) {
                mediaElements[i].pause();
                mediaElements[i].muted = true;
                mediaElements[i].currentTime = 0;
            }
        } catch (e) {}
    }

    function removeBlockOverlay() {
        var existing = document.getElementById('focuslens-block-overlay');
        if (existing) existing.remove();
        if (document.documentElement) document.documentElement.style.overflow = '';
        if (document.body) document.body.style.overflow = '';
    }

    function showFullStudyOverlay() {
        killMedia();
        var existing = document.getElementById('focuslens-block-overlay');
        if (existing) {
            if (existing.getAttribute('data-overlay-type') === 'full-study') {
                return;
            }
            existing.remove();
        }

        if (!document.body) {
            document.addEventListener('DOMContentLoaded', showFullStudyOverlay);
            return;
        }

        if (document.documentElement) document.documentElement.style.overflow = 'hidden';
        document.body.style.overflow = 'hidden';

        var overlay = document.createElement('div');
        overlay.id = 'focuslens-block-overlay';
        overlay.setAttribute('data-overlay-type', 'full-study');

        var initialTime = getFormattedRemainingTime();

        overlay.innerHTML = `
            <div class="focuslens-card study-lockout">
                <div class="focuslens-icon study">🔒</div>
                <h1 class="focuslens-title">YouTube Blocked During Study</h1>
                <p class="focuslens-subtitle">YouTube is completely locked by <strong>Lockin-Inator</strong> while your study session is active.</p>
                <div class="focuslens-study-timer-box">
                    <div class="focuslens-study-timer-label">Study Session Time Remaining</div>
                    <div id="focuslens-live-timer" class="focuslens-study-timer-digits">${initialTime}</div>
                </div>
                <div class="focuslens-info-box">
                    🚀 <strong>Prompts Executing in Background:</strong> Claude and Antigravity are autonomously working on your game builds. Stay in flow! YouTube will unlock during your scheduled 10-minute AI Review break.
                </div>
                <div class="focuslens-actions">
                    <button id="focuslens-close-tab-btn" class="focuslens-btn-primary">⬅️ Close Tab & Return to Studying</button>
                    <button id="focuslens-end-session-btn" class="focuslens-btn-secondary" style="margin-top: 6px; color: #f87171; border-color: rgba(239, 68, 68, 0.4);">🛑 End Study Session Early</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        var closeBtn = document.getElementById('focuslens-close-tab-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                try {
                    window.close();
                } catch (err) {}
                if (window.history.length > 1) {
                    window.history.back();
                } else {
                    window.location.replace('about:blank');
                }
            });
        }

        var endSessionBtn = document.getElementById('focuslens-end-session-btn');
        if (endSessionBtn) {
            endSessionBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                if (confirm('End study session early? This will unlock PC, phone, and browser.')) {
                    if (window.LockinSync && typeof window.LockinSync.sendAction === 'function') {
                        window.LockinSync.sendAction('RESET');
                    } else {
                        fetch('http://127.0.0.1:8765/api/action', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ action: 'RESET' })
                        }).catch(function() {});
                    }
                    removeBlockOverlay();
                }
            });
        }
    }

    function showShortsBlockOverlay(vidId) {
        killMedia();
        var existing = document.getElementById('focuslens-block-overlay');
        if (existing) {
            if (existing.getAttribute('data-overlay-type') === 'shorts') {
                return;
            }
            existing.remove();
        }

        if (!document.body) {
            document.addEventListener('DOMContentLoaded', function() {
                showShortsBlockOverlay(vidId);
            });
            return;
        }

        if (document.documentElement) document.documentElement.style.overflow = 'hidden';
        document.body.style.overflow = 'hidden';

        var overlay = document.createElement('div');
        overlay.id = 'focuslens-block-overlay';
        overlay.setAttribute('data-overlay-type', 'shorts');

        var watchUrl = vidId ? ('https://www.youtube.com/watch?v=' + vidId) : 'https://www.youtube.com/';

        overlay.innerHTML = `
            <div class="focuslens-card">
                <div class="focuslens-icon">🚫</div>
                <h1 class="focuslens-title">YouTube Short Blocked</h1>
                <p class="focuslens-subtitle">Short-form algorithmic video loops are blocked by <strong>Lockin-Inator</strong> to protect your attention.</p>
                <div class="focuslens-info-box">
                    💡 <strong>Core Feature Preserved:</strong> You can watch this individual video in the standard long-form player without the infinite-scroll dopamine loop.
                </div>
                <div class="focuslens-actions">
                    ${vidId ? `<a href="${watchUrl}" class="focuslens-btn-primary">▶️ Watch as Standard YouTube Video</a>` : ''}
                    <a href="https://www.youtube.com/" class="focuslens-btn-secondary">🏠 Return to YouTube Home</a>
                    <button id="focuslens-back-btn" class="focuslens-btn-secondary">⬅️ Go Back</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        var backBtn = document.getElementById('focuslens-back-btn');
        if (backBtn) {
            backBtn.addEventListener('click', function(e) {
                e.preventDefault();
                if (window.history.length > 1) {
                    window.history.back();
                } else {
                    window.location.href = 'https://www.youtube.com/';
                }
            });
        }
    }

    function enforceYouTubeRules(url) {
        var currentUrl = url || window.location.href;

        // MODE 1: STUDY SESSION ACTIVE -> FULL DOMAIN LOCKOUT
        if (isStudyModeActive()) {
            showFullStudyOverlay();
            return;
        }

        // MODE 2: IDLE OR BREAK -> SELECTIVE BLOCKING (Only Shorts)
        if (currentUrl.includes('/shorts/')) {
            var parts = currentUrl.split('/shorts/');
            var vidId = '';
            if (parts.length > 1) {
                vidId = parts[1].split('?')[0].split('/')[0];
            }
            showShortsBlockOverlay(vidId);
        } else {
            removeBlockOverlay();
        }
    }

    // Intercept SPA navigation
    var origPush = history.pushState;
    var origReplace = history.replaceState;

    history.pushState = function(state, title, url) {
        var res = origPush.apply(this, arguments);
        enforceYouTubeRules(url ? String(url) : window.location.href);
        return res;
    };

    history.replaceState = function(state, title, url) {
        var res = origReplace.apply(this, arguments);
        enforceYouTubeRules(url ? String(url) : window.location.href);
        return res;
    };

    window.addEventListener('popstate', function() {
        enforceYouTubeRules();
    });

    window.addEventListener('yt-navigate-start', function(e) {
        if (e && e.detail && e.detail.url) {
            enforceYouTubeRules(e.detail.url);
        }
    });

    // Eradicate dynamically loaded Shorts shelves
    var observer = new MutationObserver(function() {
        if (isStudyModeActive()) {
            killMedia();
            if (!document.getElementById('focuslens-block-overlay')) {
                showFullStudyOverlay();
            }
        } else {
            if (window.location.href.includes('/shorts/')) {
                killMedia();
            }
            var shelves = document.querySelectorAll('ytd-rich-shelf-renderer[is-shorts], ytd-reel-shelf-renderer');
            for (var i = 0; i < shelves.length; i++) {
                shelves[i].remove();
            }
        }
    });

    if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
    } else {
        document.addEventListener('DOMContentLoaded', function() {
            if (document.body) {
                observer.observe(document.body, { childList: true, subtree: true });
            }
            enforceYouTubeRules();
        });
    }

    // Initial check
    enforceYouTubeRules();

    // Listen to sync state changes
    if (window.LockinSync && typeof window.LockinSync.onStateChange === 'function') {
        window.LockinSync.onStateChange(function() {
            enforceYouTubeRules();
        });
    }

    window.addEventListener('lockin-sync-change', function() {
        enforceYouTubeRules();
    });
})();
