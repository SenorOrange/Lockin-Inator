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
        if (document.body) {
            document.body.style.overflow = '';
            document.body.classList.remove('focuslens-study-locked');
        }
    }

    function showFullStudyOverlay() {
        killMedia();
        var existing = document.getElementById('focuslens-block-overlay');
        if (existing) {
            if (existing.getAttribute('data-overlay-type') === 'full-study') {
                if (document.body && existing.parentNode !== document.body) {
                    document.body.appendChild(existing);
                    document.body.classList.add('focuslens-study-locked');
                }
                return;
            }
            existing.remove();
        }

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

        if (document.body) {
            document.body.appendChild(overlay);
            document.body.classList.add('focuslens-study-locked');
            document.body.style.overflow = 'hidden';
        } else if (document.documentElement) {
            document.documentElement.appendChild(overlay);
            var bodyWatcher = new MutationObserver(function() {
                if (document.body) {
                    bodyWatcher.disconnect();
                    document.body.appendChild(overlay);
                    document.body.classList.add('focuslens-study-locked');
                    document.body.style.overflow = 'hidden';
                }
            });
            bodyWatcher.observe(document.documentElement, { childList: true });
        }

        if (document.documentElement) document.documentElement.style.overflow = 'hidden';

        // Dedicated live ticker on this overlay: guarantees smooth decrement every 1000ms
        var currentRemaining = (window.LockinSync && window.LockinSync.getRemainingSeconds() > 0)
            ? window.LockinSync.getRemainingSeconds()
            : 3000;

        var localOverlayTimer = setInterval(function() {
            var activeOverlay = document.getElementById('focuslens-block-overlay');
            if (!activeOverlay) {
                clearInterval(localOverlayTimer);
                return;
            }
            if (window.LockinSync && typeof window.LockinSync.getRemainingSeconds === 'function') {
                var syncRem = window.LockinSync.getRemainingSeconds();
                if (syncRem > 0 && Math.abs(syncRem - currentRemaining) > 1) {
                    currentRemaining = syncRem;
                }
            }
            if (currentRemaining > 0) {
                currentRemaining--;
            }
            var el = document.getElementById('focuslens-live-timer');
            if (el && window.LockinSync) {
                el.textContent = window.LockinSync.formatTime(currentRemaining);
            }
        }, 1000);

        var closeBtn = document.getElementById('focuslens-close-tab-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                if (window.LockinSync && typeof window.LockinSync.closeTab === 'function') {
                    window.LockinSync.closeTab();
                } else {
                    if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage) {
                        chrome.runtime.sendMessage({ type: 'CLOSE_CURRENT_TAB' });
                    }
                    try { window.close(); } catch (err) {}
                    if (window.history.length > 1) {
                        window.history.back();
                    } else {
                        window.location.replace('about:blank');
                    }
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
                if (document.body && existing.parentNode !== document.body) {
                    document.body.appendChild(existing);
                }
                return;
            }
            existing.remove();
        }

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

        if (document.body) {
            document.body.appendChild(overlay);
        } else if (document.documentElement) {
            document.documentElement.appendChild(overlay);
            var bodyWatcher = new MutationObserver(function() {
                if (document.body) {
                    bodyWatcher.disconnect();
                    document.body.appendChild(overlay);
                }
            });
            bodyWatcher.observe(document.documentElement, { childList: true });
        }

        if (document.documentElement) document.documentElement.style.overflow = 'hidden';
        if (document.body) document.body.style.overflow = 'hidden';

        var backBtn = document.getElementById('focuslens-back-btn');
        if (backBtn) {
            backBtn.addEventListener('click', function(e) {
                e.preventDefault();
                if (window.history.length > 1) {
                    window.history.back();
                } else {
                    window.location.replace('https://www.youtube.com/');
                }
            });
        }
    }

    function extractVideoId(url) {
        var str = url || window.location.href;
        var match = str.match(/\/shorts\/([a-zA-Z0-9_-]+)/);
        return match ? match[1] : null;
    }

    function enforceYouTubeRules(url) {
        var currentUrl = url || window.location.href;

        // MODE 1: STUDY SESSION ACTIVE -> FULL DOMAIN LOCKOUT
        if (isStudyModeActive()) {
            showFullStudyOverlay();
            return;
        }

        // MODE 2: IDLE OR BREAK -> SHIELDS SHORTS ONLY
        if (currentUrl.includes('/shorts/')) {
            var vidId = extractVideoId(currentUrl);
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

    window.addEventListener('yt-navigate-start', function() {
        if (isStudyModeActive()) {
            killMedia();
            showFullStudyOverlay();
        }
    });

    window.addEventListener('yt-navigate-finish', function() {
        enforceYouTubeRules();
    });

    // Observer to kill media and remove Shorts shelves
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
