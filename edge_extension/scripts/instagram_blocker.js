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

    function showBlockOverlay() {
        killMedia();
        if (document.getElementById('focuslens-block-overlay')) return;
        if (!document.body) {
            document.addEventListener('DOMContentLoaded', showBlockOverlay);
            return;
        }

        if (document.documentElement) document.documentElement.style.overflow = 'hidden';
        document.body.style.overflow = 'hidden';

        var overlay = document.createElement('div');
        overlay.id = 'focuslens-block-overlay';

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

        // 1. Block Main Home Page -> Auto-redirect to Messages
        if (isHomePage(currentUrl)) {
            redirectToInbox();
            return;
        }

        // 2. Block Reels -> Show Focus Shield
        if (isReelsPage(currentUrl)) {
            showBlockOverlay();
        } else {
            removeBlockOverlay();
        }

        // 3. Rewrite any logo / Home navigation links to point to Messages
        rewriteHomeLinks();
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
        if (url && isHomePage(String(url))) {
            redirectToInbox();
            return;
        }
        var res = origPush.apply(this, arguments);
        if (url) enforceBlockRules(String(url));
        return res;
    };

    history.replaceState = function(state, title, url) {
        if (url && isHomePage(String(url))) {
            redirectToInbox();
            return;
        }
        var res = origReplace.apply(this, arguments);
        if (url) enforceBlockRules(String(url));
        return res;
    };

    window.addEventListener('popstate', function() {
        enforceBlockRules();
    });

    // Intercept clicks on links pointing to the Home page or Reels
    document.addEventListener('click', function(e) {
        var link = e.target.closest('a');
        if (link && link.href) {
            if (isHomePage(link.href)) {
                e.preventDefault();
                e.stopPropagation();
                redirectToInbox();
                return;
            }
            if (isReelsPage(link.href)) {
                e.preventDefault();
                e.stopPropagation();
                showBlockOverlay();
                return;
            }
        }
    }, true);

    // Initial check right at document_start
    enforceBlockRules();

    // Observe DOM changes to maintain link rewrites and kill media if on Reels
    var observer = new MutationObserver(function() {
        if (isHomePage()) {
            redirectToInbox();
        } else if (isReelsPage()) {
            killMedia();
        } else {
            rewriteHomeLinks();
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
