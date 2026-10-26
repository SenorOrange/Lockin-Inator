(function() {
    'use strict';
    if (window.__focuslens_edge_ig) return;
    window.__focuslens_edge_ig = true;

    var DIRECT_INBOX_URL = 'https://www.instagram.com/direct/inbox/';

    function isHomePage(url) {
        try {
            var parsed = new URL(url || window.location.href);
            if (!parsed.hostname.includes('instagram.com')) return false;
            var path = parsed.pathname;
            if (path.length > 1 && path.endsWith('/')) {
                path = path.slice(0, -1);
            }
            return path === '/' || path === '';
        } catch (e) {
            var p = window.location.pathname;
            return p === '/' || p === '';
        }
    }

    function isReelsPage(url) {
        var str = url || window.location.href;
        return str.includes('/reel/') || str.includes('/reels/');
    }

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

    function redirectToInbox() {
        try {
            window.location.replace(DIRECT_INBOX_URL);
        } catch (e) {
            window.location.href = DIRECT_INBOX_URL;
        }
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
                <h1 class="focuslens-title">Instagram Blocked During Study</h1>
                <p class="focuslens-subtitle">Instagram is completely locked by <strong>Lockin-Inator</strong> while your study session is active.</p>
                <div class="focuslens-study-timer-box">
                    <div class="focuslens-study-timer-label">Study Session Time Remaining</div>
                    <div id="focuslens-live-timer" class="focuslens-study-timer-digits">${initialTime}</div>
                </div>
                <div class="focuslens-info-box">
                    🚀 <strong>Prompts Executing in Background:</strong> Claude and Antigravity are autonomously working on your game builds. Stay in flow! Instagram will unlock during your scheduled 10-minute AI Review break.
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

    function showReelBlockOverlay() {
        killMedia();
        var existing = document.getElementById('focuslens-block-overlay');
        if (existing) {
            if (existing.getAttribute('data-overlay-type') === 'reel') {
                return;
            }
            existing.remove();
        }

        if (!document.body) {
            document.addEventListener('DOMContentLoaded', showReelBlockOverlay);
            return;
        }

        if (document.documentElement) document.documentElement.style.overflow = 'hidden';
        document.body.style.overflow = 'hidden';

        var overlay = document.createElement('div');
        overlay.id = 'focuslens-block-overlay';
        overlay.setAttribute('data-overlay-type', 'reel');

        overlay.innerHTML = `
            <div class="focuslens-card">
                <div class="focuslens-icon">🚫</div>
                <h1 class="focuslens-title">Instagram Reel Blocked</h1>
                <p class="focuslens-subtitle">Instagram Reels are blocked by <strong>Lockin-Inator</strong> to eliminate addictive short-form doomscrolling.</p>
                <div class="focuslens-info-box">
                    💬 <strong>Permitted Sub-URLs:</strong> Direct Messages, chat threads, search & explore, and account profiles remain 100% active.
                </div>
                <div class="focuslens-actions">
                    <a href="https://www.instagram.com/direct/inbox/" class="focuslens-btn-primary">💬 Open Direct Messages</a>
                    <a href="https://www.instagram.com/explore/" class="focuslens-btn-secondary">🔍 Search & Explore</a>
                    <button id="focuslens-ig-back-btn" class="focuslens-btn-secondary">⬅️ Go Back</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        var backBtn = document.getElementById('focuslens-ig-back-btn');
        if (backBtn) {
            backBtn.addEventListener('click', function(e) {
                e.preventDefault();
                if (window.history.length > 1) {
                    window.history.back();
                } else {
                    window.location.replace(DIRECT_INBOX_URL);
                }
            });
        }
    }

    function enforceBlockRules(url) {
        var currentUrl = url || window.location.href;

        // MODE 1: STUDY SESSION ACTIVE -> FULL DOMAIN LOCKOUT
        if (isStudyModeActive()) {
            showFullStudyOverlay();
            return;
        }

        // MODE 2: IDLE OR BREAK -> SELECTIVE BLOCKING (Only Reels)
        if (isReelsPage(currentUrl)) {
            showReelBlockOverlay();
        } else {
            removeBlockOverlay();
        }
    }

    function rewriteHomeLinks() {
        try {
            var links = document.querySelectorAll('a[href="/"]');
            for (var i = 0; i < links.length; i++) {
                links[i].href = DIRECT_INBOX_URL;
            }
        } catch (e) {}
    }

    // Intercept SPA navigation (pushState & replaceState)
    var origPush = history.pushState;
    var origReplace = history.replaceState;

    history.pushState = function(state, title, url) {
        var res = origPush.apply(this, arguments);
        enforceBlockRules(url ? String(url) : window.location.href);
        return res;
    };

    history.replaceState = function(state, title, url) {
        var res = origReplace.apply(this, arguments);
        enforceBlockRules(url ? String(url) : window.location.href);
        return res;
    };

    window.addEventListener('popstate', function() {
        enforceBlockRules();
    });

    // Intercept clicks on links pointing to Reels or outside overlay
    document.addEventListener('click', function(e) {
        // Never intercept clicks on or inside the block overlay
        if (e.target && e.target.closest && e.target.closest('#focuslens-block-overlay')) {
            return;
        }

        if (isStudyModeActive()) {
            e.preventDefault();
            e.stopPropagation();
            showFullStudyOverlay();
            return;
        }
        var link = e.target.closest('a');
        if (link && link.href) {
            if (isReelsPage(link.href)) {
                e.preventDefault();
                e.stopPropagation();
                showReelBlockOverlay();
                return;
            }
        }
    }, true);

    // Initial check right at document_start
    enforceBlockRules();

    // Listen to sync state changes
    if (window.LockinSync && typeof window.LockinSync.onStateChange === 'function') {
        window.LockinSync.onStateChange(function() {
            enforceBlockRules();
        });
    }

    window.addEventListener('lockin-sync-change', function() {
        enforceBlockRules();
    });

    // Observe DOM changes to kill media if blocked
    var observer = new MutationObserver(function() {
        if (isStudyModeActive()) {
            killMedia();
            if (!document.getElementById('focuslens-block-overlay')) {
                showFullStudyOverlay();
            }
        } else if (isReelsPage()) {
            killMedia();
        }
    });

    if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
    } else {
        document.addEventListener('DOMContentLoaded', function() {
            if (document.body) {
                observer.observe(document.body, { childList: true, subtree: true });
            }
            enforceBlockRules();
        });
    }
})();
