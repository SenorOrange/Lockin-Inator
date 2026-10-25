(function() {
    'use strict';
    if (window.__lockin_general_blocker) return;
    window.__lockin_general_blocker = true;

    function getSiteDisplayName(host) {
        var h = (host || window.location.hostname).toLowerCase();
        if (h.includes('reddit')) return 'Reddit';
        if (h.includes('tiktok')) return 'TikTok';
        if (h.includes('twitter') || h.includes('x.com')) return 'Twitter / X';
        if (h.includes('twitch')) return 'Twitch';
        if (h.includes('facebook')) return 'Facebook';
        if (h.includes('netflix')) return 'Netflix';
        if (h.includes('discord')) return 'Discord';
        if (h.includes('threads')) return 'Threads';
        return window.location.hostname;
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

    function showStudyBlockOverlay() {
        killMedia();
        var existing = document.getElementById('focuslens-block-overlay');
        if (existing) {
            return;
        }

        if (!document.body) {
            document.addEventListener('DOMContentLoaded', showStudyBlockOverlay);
            return;
        }

        if (document.documentElement) document.documentElement.style.overflow = 'hidden';
        document.body.style.overflow = 'hidden';

        var overlay = document.createElement('div');
        overlay.id = 'focuslens-block-overlay';
        overlay.setAttribute('data-overlay-type', 'full-study');

        var siteName = getSiteDisplayName();
        var initialTime = getFormattedRemainingTime();

        overlay.innerHTML = `
            <div class="focuslens-card study-lockout">
                <div class="focuslens-icon study">🔒</div>
                <h1 class="focuslens-title">${siteName} Blocked During Study</h1>
                <p class="focuslens-subtitle"><strong>${siteName}</strong> is completely locked by <strong>Lockin-Inator</strong> while your study session is active.</p>
                <div class="focuslens-study-timer-box">
                    <div class="focuslens-study-timer-label">Study Session Time Remaining</div>
                    <div id="focuslens-live-timer" class="focuslens-study-timer-digits">${initialTime}</div>
                </div>
                <div class="focuslens-info-box">
                    🚀 <strong>Prompts Executing in Background:</strong> Claude and Antigravity are autonomously working on your game builds. Stay in flow! Distracting sites will unlock during your scheduled 10-minute AI Review break.
                </div>
                <div class="focuslens-actions">
                    <button id="focuslens-close-tab-btn" class="focuslens-btn-primary">⬅️ Close Tab & Return to Studying</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        var closeBtn = document.getElementById('focuslens-close-tab-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', function(e) {
                e.preventDefault();
                try {
                    window.close();
                } catch (err) {}
                if (window.history.length > 1) {
                    window.history.back();
                } else {
                    window.location.href = 'about:blank';
                }
            });
        }
    }

    function checkSiteBlock() {
        if (isStudyModeActive()) {
            showStudyBlockOverlay();
        } else {
            removeBlockOverlay();
        }
    }

    // Intercept SPA navigation
    var origPush = history.pushState;
    var origReplace = history.replaceState;

    history.pushState = function(state, title, url) {
        var res = origPush.apply(this, arguments);
        checkSiteBlock();
        return res;
    };

    history.replaceState = function(state, title, url) {
        var res = origReplace.apply(this, arguments);
        checkSiteBlock();
        return res;
    };

    window.addEventListener('popstate', function() {
        checkSiteBlock();
    });

    // Observer to kill media and ensure overlay stays on DOM mutations
    var observer = new MutationObserver(function() {
        if (isStudyModeActive()) {
            killMedia();
            if (!document.getElementById('focuslens-block-overlay')) {
                showStudyBlockOverlay();
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
            checkSiteBlock();
        });
    }

    // Initial run
    checkSiteBlock();

    // Listen to sync changes
    if (window.LockinSync && typeof window.LockinSync.onStateChange === 'function') {
        window.LockinSync.onStateChange(function() {
            checkSiteBlock();
        });
    }

    window.addEventListener('lockin-sync-change', function() {
        checkSiteBlock();
    });
})();
