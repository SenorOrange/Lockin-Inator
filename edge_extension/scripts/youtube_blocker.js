(function() {
    'use strict';
    if (window.__focuslens_edge_yt) return;
    window.__focuslens_edge_yt = true;

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

    function showBlockOverlay(vidId) {
        killMedia();
        if (document.getElementById('focuslens-block-overlay')) return;
        if (!document.body) {
            document.addEventListener('DOMContentLoaded', function() {
                showBlockOverlay(vidId);
            });
            return;
        }

        if (document.documentElement) document.documentElement.style.overflow = 'hidden';
        document.body.style.overflow = 'hidden';

        var overlay = document.createElement('div');
        overlay.id = 'focuslens-block-overlay';

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

    function checkShorts(url) {
        if (!url) url = window.location.href;
        if (url.includes('/shorts/')) {
            var parts = url.split('/shorts/');
            var vidId = '';
            if (parts.length > 1) {
                vidId = parts[1].split('?')[0].split('/')[0];
            }
            showBlockOverlay(vidId);
        } else {
            removeBlockOverlay();
        }
    }

    // Intercept SPA navigation
    var origPush = history.pushState;
    var origReplace = history.replaceState;

    history.pushState = function(state, title, url) {
        var res = origPush.apply(this, arguments);
        if (url) checkShorts(String(url));
        return res;
    };

    history.replaceState = function(state, title, url) {
        var res = origReplace.apply(this, arguments);
        if (url) checkShorts(String(url));
        return res;
    };

    window.addEventListener('popstate', function() {
        checkShorts();
    });

    window.addEventListener('yt-navigate-start', function(e) {
        if (e && e.detail && e.detail.url) {
            checkShorts(e.detail.url);
        }
    });

    // Eradicate dynamically loaded Shorts shelves
    var observer = new MutationObserver(function() {
        if (window.location.href.includes('/shorts/')) {
            killMedia();
        }
        var shelves = document.querySelectorAll('ytd-rich-shelf-renderer[is-shorts], ytd-reel-shelf-renderer');
        for (var i = 0; i < shelves.length; i++) {
            shelves[i].remove();
        }
    });

    if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
    } else {
        document.addEventListener('DOMContentLoaded', function() {
            observer.observe(document.body, { childList: true, subtree: true });
        });
    }

    checkShorts();
})();
