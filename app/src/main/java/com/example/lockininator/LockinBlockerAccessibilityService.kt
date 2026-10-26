package com.example.lockininator

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.graphics.Path
import android.graphics.Rect
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.provider.Settings
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.Toast

class LockinBlockerAccessibilityService : AccessibilityService() {

    private val tag = "LockinShield"

    private val mainHandler = Handler(Looper.getMainLooper())

    private var lastToastTime = 0L
    private val toastCooldownMs = 2000L

    // Anti-spam cooldown for tab clicks / gesture taps
    private var lastActionTime = 0L
    private val actionCooldownMs = 350L

    // Study Mode Full Lockout State
    private var lastStudyLockoutTime = 0L
    private val blockedStudyPackages = setOf(
        "com.instagram.android",
        "com.google.android.youtube",
        "com.google.android.youtube.tv",
        "com.zhiliaoapp.musically",
        "com.ss.android.ugc.trill",
        "com.facebook.katana",
        "com.facebook.lite",
        "com.reddit.frontpage",
        "com.twitter.android",
        "com.snapchat.android",
        "tv.twitch.android.app",
        "com.netflix.mediaclient",
        "com.pinterest"
    )

    // State tracking for friend's reels and chat navigation
    private var lastInChatThreadTime = 0L
    private var lastReelsTabClickTime = 0L
    private var watchingFriendReel = false
    private var friendReelOpenedTime = 0L
    private var initialReelAuthor = ""
    private var redirectPending = false

    // Fast-response scroll accumulation for friend reel swipe
    private var accumulatedScrollY = 0
    private var lastScrollEventTime = 0L

    private val prefs: SharedPreferences by lazy {
        getSharedPreferences("lockin_prefs", Context.MODE_PRIVATE)
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.d(tag, "LockinBlockerAccessibilityService connected and ready!")
        try {
            if (prefs.getBoolean("sync_pc_enabled", true)) {
                SyncManager.getInstance(applicationContext).startSync()
            }
        } catch (e: Exception) {
            Log.e(tag, "Failed to start SyncManager from AccessibilityService", e)
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        try {
            if (event == null || event.packageName == null) return

            val pkg = event.packageName.toString()

            val blockAlways = prefs.getBoolean("block_always", true)
            val studyModeActive = prefs.getBoolean("study_mode_active", false)

            if (!blockAlways && !studyModeActive) return

            // 1. FULL STUDY MODE LOCKOUT
            // If Study Mode is active, distracting apps (Instagram, YouTube, TikTok, Facebook, Reddit, etc.)
            // are completely blocked and the user is routed right back to Lockin-Inator.
            if (studyModeActive && blockedStudyPackages.contains(pkg)) {
                handleStudyModeLockout(pkg)
                return
            }

            if (pkg == "com.instagram.android") {
                handleInstagram(event)
            } else if (pkg == "com.google.android.youtube" && prefs.getBoolean("block_shorts", true)) {
                handleYouTube()
            } else if (pkg == "com.facebook.katana" && prefs.getBoolean("block_facebook", true)) {
                handleFacebook()
            }
        } catch (t: Throwable) {
            Log.e(tag, "Unexpected error in onAccessibilityEvent", t)
        }
    }

    private fun handleStudyModeLockout(pkg: String) {
        val now = SystemClock.uptimeMillis()
        if (now - lastStudyLockoutTime < 800L) {
            return
        }
        lastStudyLockoutTime = now

        Log.w(tag, "Study Mode Active: Intercepted distracting app '$pkg'. Returning to Lockin-Inator.")

        // Kick out of distracting app immediately
        performGlobalAction(GLOBAL_ACTION_HOME)

        // Relaunch Lockin-Inator to foreground and pin
        mainHandler.postDelayed({
            try {
                val intent = Intent(this, MainActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
                    putExtra("EXTRA_START_LOCK_TASK", true)
                }
                startActivity(intent)
            } catch (e: Exception) {
                Log.e(tag, "Failed to launch MainActivity during study lockout", e)
            }
        }, 120L)

        if (now - lastToastTime > toastCooldownMs) {
            lastToastTime = now
            mainHandler.post {
                Toast.makeText(
                    applicationContext,
                    "🔒 Study Mode Active: Locked until timer ends.",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }

        recordIntercept("study_mode")
    }

    private fun recordIntercept(type: String) {
        val total = prefs.getInt("total_intercepts", 0) + 1
        val typeCount = prefs.getInt("${type}_intercepts", 0) + 1
        prefs.edit()
            .putInt("total_intercepts", total)
            .putInt("${type}_intercepts", typeCount)
            .putLong("last_intercept_time", System.currentTimeMillis())
            .apply()
    }

    private fun handleInstagram(event: AccessibilityEvent) {
        val rootNode = rootInActiveWindow
        if (rootNode == null) {
            Log.d(tag, "handleInstagram: rootInActiveWindow is null")
            return
        }
        val now = SystemClock.uptimeMillis()

        val redirectHomeToMessages = prefs.getBoolean("redirect_home_to_messages", true)
        val blockReels = prefs.getBoolean("block_reels", true)

        // 1. ARE WE INSIDE AN ACTIVE CHAT CONVERSATION?
        if (isInsideChatThread(rootNode)) {
            lastInChatThreadTime = now
            watchingFriendReel = false
            initialReelAuthor = ""
            accumulatedScrollY = 0
            return // Full unrestricted access in chat
        }

        // 2. ARE WE IN THE PHOTO / GALLERY PICKER OR CAMERA FROM CHAT?
        if (isInsideChatPhotoOrCamera(rootNode)) {
            lastInChatThreadTime = now // Keep chat session active while picking/capturing/previewing photos
            watchingFriendReel = false
            initialReelAuthor = ""
            accumulatedScrollY = 0
            return // Full unrestricted access to send photos in chat!
        }

        // 3. ARE WE IN A REELS / MEDIA VIEWER?
        val insideReels = isInsideReelsViewer(rootNode)
        val reelsTabSelected = isClipsTabSelected(rootNode)
        val hasBack = hasBackButton(rootNode)
        val insideHome = isInsideHomeFeed(rootNode)

        // A reel is a friend's reel if:
        // - We are already actively watching it, OR
        // - We were inside a CHAT THREAD within the last 15 seconds, bottom tabs (Home/Explore/Profile) are not selected,
        //   and the bottom Reels tab is not selected
        val cameFromChatThread = (now - lastInChatThreadTime < 15000L)
        val isFriendReel = (watchingFriendReel || (cameFromChatThread && (hasBack || insideReels))) &&
                !reelsTabSelected &&
                !insideHome &&
                (now - lastReelsTabClickTime > 3000L)

        if (insideReels && isFriendReel) {
            if (!watchingFriendReel) {
                watchingFriendReel = true
                friendReelOpenedTime = now
                accumulatedScrollY = 0
                initialReelAuthor = getVisibleReelAuthor(rootNode)
                Log.d(tag, "Friend's reel playback started. Author: '$initialReelAuthor'")
                return
            }

            // Lock in initial author as soon as the view renders
            if (initialReelAuthor.isEmpty()) {
                initialReelAuthor = getVisibleReelAuthor(rootNode)
                if (initialReelAuthor.isNotEmpty()) {
                    Log.d(tag, "Friend's reel author locked in: '$initialReelAuthor'")
                }
            }

            // Check for navigation to the NEXT reel (Swipe to next video / doomscroll)
            // Settle for 300ms after opening to let initial layout finish
            if (now - friendReelOpenedTime > 300L) {
                var swipeDetected = false

                // Signal 1: The visible author changed to a different creator
                val currentAuthor = getVisibleReelAuthor(rootNode)
                if (initialReelAuthor.isNotEmpty() && currentAuthor.isNotEmpty() &&
                    !currentAuthor.equals(initialReelAuthor, ignoreCase = true)
                ) {
                    Log.d(tag, "Reel author changed: '$initialReelAuthor' -> '$currentAuthor'. Returning to chat.")
                    swipeDetected = true
                }

                // Signal 2: Fast-response swipe detection via accumulated scroll distance
                // Intercepts the moment the user reaches 500px displacement mid-swipe
                if (!swipeDetected && event.eventType == AccessibilityEvent.TYPE_VIEW_SCROLLED) {
                    val className = event.className?.toString() ?: ""
                    val viewId = event.source?.viewIdResourceName ?: ""
                    val isPager = className.contains("RecyclerView") || className.contains("ViewPager")
                    val isComment = viewId.contains("comment", ignoreCase = true) || viewId.contains("sheet", ignoreCase = true)

                    if (isPager && !isComment) {
                        val deltaY = event.scrollDeltaY
                        // Reset accumulation if user paused scrolling (> 400ms gap)
                        if (now - lastScrollEventTime > 400L) {
                            accumulatedScrollY = 0
                        }
                        lastScrollEventTime = now
                        accumulatedScrollY += Math.abs(deltaY)

                        if (accumulatedScrollY >= 500 || Math.abs(deltaY) >= 500) {
                            Log.d(tag, "Instant swipe intercepted (accumulated=$accumulatedScrollY, deltaY=$deltaY). Returning to chat.")
                            swipeDetected = true
                        }
                    }
                }

                if (swipeDetected) {
                    watchingFriendReel = false
                    initialReelAuthor = ""
                    lastInChatThreadTime = 0L // Prevent exit animation frames from re-triggering friend reel
                    accumulatedScrollY = 0

                    // Ultra-fast exit: Click on-screen back button directly, with fallback to global BACK
                    if (!clickBackButton(rootNode)) {
                        performGlobalAction(GLOBAL_ACTION_BACK)
                    }
                    showToast("🚫 Endless Reels blocked - returned to chat")
                    recordIntercept("reels")
                    return
                }
            }

            // Unrestricted playback of this friend's reel
            return
        }

        // 4. ARE WE IN THE MESSAGES INBOX?
        if (isInsideInbox(rootNode)) {
            watchingFriendReel = false
            initialReelAuthor = ""
            accumulatedScrollY = 0
            return // Full unrestricted access in inbox
        }

        // 5. NON-FRIEND REELS VIEWER (Algorithmic Reels feed, Explore reel, or Reels tab)
        if (insideReels || reelsTabSelected) {
            Log.d(tag, "Non-friend Reels viewer -> Exiting back to Messages")
            watchingFriendReel = false
            initialReelAuthor = ""
            accumulatedScrollY = 0
            lastReelsTabClickTime = now
            if (redirectHomeToMessages) {
                val redirected = redirectToMessages(rootNode, allowBackFallback = true)
                if (!redirected) scheduleRedirectRetry()
            } else {
                performGlobalAction(GLOBAL_ACTION_BACK)
            }
            recordIntercept("reels")
            return
        }

        // 6. INTERCEPT TAPS ON REELS TAB IN BOTTOM BAR
        if (isClipsTabEvent(event, rootNode)) {
            lastReelsTabClickTime = now
            watchingFriendReel = false
            initialReelAuthor = ""
            accumulatedScrollY = 0
            Log.d(tag, "Reels tab tap intercepted -> redirecting to Messages")
            val redirected = redirectToMessages(rootNode, allowBackFallback = false)
            if (!redirected) scheduleRedirectRetry()
            recordIntercept("reels")
            return
        }

        // 7. DISMISS SHARE SHEET FROM REELS FEED
        if (isInsideShareSheet(rootNode) && !watchingFriendReel) {
            val recentlyClickedReels = (now - lastReelsTabClickTime) < 3000L
            if (recentlyClickedReels || reelsTabSelected) {
                Log.d(tag, "Reels feed share sheet detected -> Dismissing")
                performGlobalAction(GLOBAL_ACTION_BACK)
                recordIntercept("reels")
                return
            }
        }

        // 8. AUTO-SWITCH TO MESSAGES:
        // User is outside Messages/Chat and not watching a friend's reel
        // (Swiped to Home feed, Search/Explore, Profile, or cold launch)
        if (redirectHomeToMessages) {
            watchingFriendReel = false
            initialReelAuthor = ""
            accumulatedScrollY = 0
            Log.d(tag, "Non-messages screen/tab detected -> redirecting to Messages")
            val redirected = redirectToMessages(rootNode, allowBackFallback = false)
            if (!redirected) {
                scheduleRedirectRetry()
            }
            recordIntercept("instagram")
            return
        }

        // 9. FALLBACK: If only Reels blocking is enabled and Reels tab is selected
        if (blockReels && reelsTabSelected) {
            lastReelsTabClickTime = now
            watchingFriendReel = false
            initialReelAuthor = ""
            accumulatedScrollY = 0
            val redirected = redirectToMessages(rootNode, allowBackFallback = false)
            if (!redirected) scheduleRedirectRetry()
            recordIntercept("reels")
            return
        }
    }

    private fun scheduleRedirectRetry(attempt: Int = 1) {
        if (redirectPending || attempt > 5) return
        redirectPending = true
        mainHandler.postDelayed({
            redirectPending = false
            val root = rootInActiveWindow ?: return@postDelayed
            if (isInsideChatThread(root) || isInsideChatPhotoOrCamera(root) || isInsideInbox(root) || watchingFriendReel) return@postDelayed

            val redirected = redirectToMessages(root, allowBackFallback = false)
            if (!redirected && attempt < 5) {
                scheduleRedirectRetry(attempt + 1)
            }
        }, 150L * attempt)
    }

    private fun handleFacebook() {
        val rootNode = rootInActiveWindow ?: return
        val now = SystemClock.uptimeMillis()
        if (now - lastActionTime < actionCooldownMs) return

        if (isInsideFacebookReels(rootNode)) {
            lastActionTime = now
            Log.d(tag, "Facebook Reels detected -> performing Back action")
            performGlobalAction(GLOBAL_ACTION_BACK)
            showToast("🚫 Facebook Reels blocked by Lockin-Inator!")
            recordIntercept("facebook")
        }
    }

    private fun isInsideFacebookReels(root: AccessibilityNodeInfo): Boolean {
        val fbReelsIds = listOf(
            "fb_shorts_container",
            "fb_shorts_viewer_fragment",
            "reels_viewer_fragment",
            "reel_viewer",
            "reels_tray",
            "unified_reels_tray",
            "fb_shorts_video_container",
            "fb_shorts_unified_toaster"
        )
        for (id in fbReelsIds) {
            val nodes = root.findAccessibilityNodeInfosByViewId("com.facebook.katana:id/$id")
            if (nodes.isNotEmpty()) return true
        }

        val reelsTabs = root.findAccessibilityNodeInfosByText("Reels")
        if (reelsTabs.any { it.isSelected || it.isFocused }) return true

        return false
    }

    private fun getVisibleReelAuthor(root: AccessibilityNodeInfo): String {
        val displayMetrics = resources.displayMetrics
        val screenHeight = displayMetrics.heightPixels.takeIf { it > 0 } ?: 2340
        val authorIds = listOf(
            "com.instagram.android:id/clips_author_name",
            "com.instagram.android:id/clips_user_name",
            "com.instagram.android:id/row_feed_photo_profile_name",
            "com.instagram.android:id/reel_viewer_user_name",
            "com.instagram.android:id/author_name"
        )
        for (id in authorIds) {
            val nodes = root.findAccessibilityNodeInfosByViewId(id)
            for (node in nodes) {
                val bounds = Rect()
                node.getBoundsInScreen(bounds)
                // Ensure the node is visible in viewport (ignore off-screen prebuffered nodes)
                if (bounds.bottom > 100 && bounds.top < screenHeight - 100 && bounds.width() > 0 && bounds.height() > 0) {
                    val text = node.text?.toString()?.trim()
                    if (!text.isNullOrEmpty()) return text
                }
            }
        }
        return ""
    }

    private fun isInsideChatThread(root: AccessibilityNodeInfo): Boolean {
        val chatIds = listOf(
            "com.instagram.android:id/thread_fragment_container",
            "com.instagram.android:id/direct_thread_header",
            "com.instagram.android:id/message_thread_container",
            "com.instagram.android:id/row_thread_composer_container",
            "com.instagram.android:id/row_thread_composer_edittext",
            "com.instagram.android:id/thread_view_root",
            "com.instagram.android:id/message_list",
            "com.instagram.android:id/direct_conversation_container",
            "com.instagram.android:id/direct_thread_content_below_action_bar"
        )
        for (id in chatIds) {
            if (root.findAccessibilityNodeInfosByViewId(id).isNotEmpty()) return true
        }
        return false
    }

    private fun isInsideChatPhotoOrCamera(root: AccessibilityNodeInfo): Boolean {
        val now = SystemClock.uptimeMillis()
        // Must have been in a chat thread recently (within 60s)
        if (now - lastInChatThreadTime > 60000L) return false

        // Never treat Home feed, Reels tab, Search, or Profile tab as photo picking
        if (isInsideHomeFeed(root) || isNonDirectTabSelected(root) || isClipsTabSelected(root)) {
            return false
        }

        // 1. Check known photo / gallery / camera IDs in Instagram chat
        val photoCameraIds = listOf(
            "gallery_container",
            "gallery_recycler_view",
            "gallery_grid",
            "gallery_media_grid",
            "gallery_scroller",
            "gallery_folder_menu_btn",
            "gallery_header",
            "gallery_title",
            "direct_private_media_picker",
            "direct_composer_gallery",
            "direct_gallery_container",
            "camera_container",
            "quick_camera_fragment",
            "cam_dest_direct",
            "direct_camera",
            "camera_shutter_button",
            "camera_stub",
            "capture_controls",
            "direct_media_composer",
            "crop_image_view",
            "direct_expiring_media_composer",
            "photo_picker",
            "media_picker",
            "media_picker_view",
            "album_picker",
            "direct_visual_timeline",
            "direct_composer_camera_container",
            "modal_container",
            "creation_main_actions",
            "direct_send_button",
            "send_button",
            "bottom_sheet_container"
        )
        for (idSub in photoCameraIds) {
            if (root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/$idSub").isNotEmpty()) {
                return true
            }
        }

        // 2. Specific keywords in photo picker / camera / send screen
        val keywords = listOf(
            "Recents",
            "Gallery",
            "Camera roll",
            "Allow replay",
            "Keep in chat",
            "View once",
            "Send separately",
            "Send to",
            "Manage photos"
        )
        for (kw in keywords) {
            if (root.findAccessibilityNodeInfosByText(kw).isNotEmpty()) return true
        }

        // 3. Modal / overlay subscreen with Back / Close button and NO bottom tab bar
        val tabBars = root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/tab_bar")
        if (tabBars.isEmpty() && hasBackButton(root)) {
            return true
        }

        return false
    }

    private fun isInsideInbox(root: AccessibilityNodeInfo): Boolean {
        // If a non-direct tab (Home, Reels, Search, Profile) is selected, we are definitely NOT in Inbox!
        if (isNonDirectTabSelected(root)) return false

        val directTabs = root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/direct_tab")
        for (tab in directTabs) {
            if (tab.isSelected || tab.isFocused) return true
            for (i in 0 until tab.childCount) {
                val child = tab.getChild(i)
                if (child != null && (child.isSelected || child.isFocused)) return true
            }
        }

        val tabBars = root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/tab_bar")
        for (tabBar in tabBars) {
            if (tabBar.childCount >= 3) {
                val directTab = tabBar.getChild(2)
                if (directTab != null) {
                    if (directTab.isSelected || directTab.isFocused) return true
                    for (i in 0 until directTab.childCount) {
                        val child = directTab.getChild(i)
                        if (child != null && (child.isSelected || child.isFocused)) return true
                    }
                }
            }
        }

        // Layouts where direct_inbox_action_bar or message recyclerview is present
        if (root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/direct_inbox_action_bar").isNotEmpty()) return true
        if (root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/inbox_refreshable_thread_list_recyclerview").isNotEmpty()) return true

        return false
    }

    private fun isNonDirectTabSelected(root: AccessibilityNodeInfo): Boolean {
        val nonDirectTabIds = listOf(
            "com.instagram.android:id/feed_tab",
            "com.instagram.android:id/clips_tab",
            "com.instagram.android:id/search_tab",
            "com.instagram.android:id/profile_tab"
        )
        for (id in nonDirectTabIds) {
            val tabs = root.findAccessibilityNodeInfosByViewId(id)
            for (tab in tabs) {
                if (tab.isSelected || tab.isFocused) return true
                for (i in 0 until tab.childCount) {
                    val child = tab.getChild(i)
                    if (child != null && (child.isSelected || child.isFocused)) return true
                }
            }
        }

        val tabBars = root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/tab_bar")
        for (tabBar in tabBars) {
            for (i in 0 until tabBar.childCount) {
                if (i == 2) continue // index 2 is direct_tab
                val child = tabBar.getChild(i) ?: continue
                if (child.isSelected || child.isFocused) return true
                for (j in 0 until child.childCount) {
                    val sub = child.getChild(j)
                    if (sub != null && (sub.isSelected || sub.isFocused)) return true
                }
            }
        }

        return false
    }

    private fun isInsideHomeFeed(root: AccessibilityNodeInfo): Boolean {
        val feedTabs = root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/feed_tab")
        for (tab in feedTabs) {
            if (tab.isSelected || tab.isFocused) return true
            for (i in 0 until tab.childCount) {
                val child = tab.getChild(i)
                if (child != null && (child.isSelected || child.isFocused)) return true
            }
        }
        if (root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/main_feed_action_bar").isNotEmpty()) return true
        return false
    }

    private fun hasBackButton(root: AccessibilityNodeInfo): Boolean {
        val backIds = listOf(
            "com.instagram.android:id/action_bar_button_back",
            "com.instagram.android:id/action_bar_back_button",
            "com.instagram.android:id/back_button",
            "com.instagram.android:id/close_button",
            "com.instagram.android:id/action_bar_button_close"
        )
        for (id in backIds) {
            if (root.findAccessibilityNodeInfosByViewId(id).isNotEmpty()) return true
        }
        val backNodes = root.findAccessibilityNodeInfosByText("Back")
        for (node in backNodes) {
            if (node.isClickable) return true
        }
        return false
    }

    private fun clickBackButton(root: AccessibilityNodeInfo): Boolean {
        val backIds = listOf(
            "com.instagram.android:id/action_bar_button_back",
            "com.instagram.android:id/action_bar_back_button",
            "com.instagram.android:id/back_button",
            "com.instagram.android:id/close_button",
            "com.instagram.android:id/action_bar_button_close"
        )
        for (id in backIds) {
            val nodes = root.findAccessibilityNodeInfosByViewId(id)
            for (node in nodes) {
                if (clickNodeOrPerformTap(node)) return true
            }
        }
        val backNodes = root.findAccessibilityNodeInfosByText("Back")
        for (node in backNodes) {
            if (node.isClickable && clickNodeOrPerformTap(node)) return true
        }
        return false
    }

    private fun clickNodeOrPerformTap(node: AccessibilityNodeInfo): Boolean {
        var current: AccessibilityNodeInfo? = node
        var depth = 0
        while (current != null && depth < 5) {
            if (current.isClickable) {
                if (current.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                    return true
                }
            }
            current = current.parent
            depth++
        }

        // Fallback: Dispatch gesture tap on node bounds
        val bounds = Rect()
        node.getBoundsInScreen(bounds)
        if (bounds.width() > 0 && bounds.height() > 0) {
            return dispatchTap(bounds.centerX().toFloat(), bounds.centerY().toFloat())
        }

        return false
    }

    private fun isClipsTabEvent(event: AccessibilityEvent, root: AccessibilityNodeInfo): Boolean {
        if (event.eventType != AccessibilityEvent.TYPE_VIEW_CLICKED) return false
        // Never intercept taps inside chat, during photo picking, or during friend reel playback
        if (watchingFriendReel || isInsideChatThread(root) || isInsideChatPhotoOrCamera(root) || isInsideReelsViewer(root)) return false

        val viewId = event.source?.viewIdResourceName ?: ""
        if (viewId == "com.instagram.android:id/clips_tab" || viewId.endsWith(":id/clips_tab")) {
            return true
        }

        val desc = event.contentDescription?.toString() ?: ""
        if (desc.equals("Reels", ignoreCase = true)) {
            val source = event.source ?: return false
            var current: AccessibilityNodeInfo? = source.parent
            var depth = 0
            while (current != null && depth < 4) {
                val parentId = current.viewIdResourceName ?: ""
                if (parentId.contains("tab_bar")) return true
                current = current.parent
                depth++
            }
            val bounds = Rect()
            source.getBoundsInScreen(bounds)
            val screenHeight = resources.displayMetrics.heightPixels
            if (screenHeight > 0 && bounds.bottom >= screenHeight - 250 && bounds.top >= screenHeight - 350) {
                return true
            }
        }
        return false
    }

    private fun isClipsTabSelected(root: AccessibilityNodeInfo): Boolean {
        val clipsTabs = root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/clips_tab")
        for (tab in clipsTabs) {
            if (tab.isSelected || tab.isFocused) return true
            for (i in 0 until tab.childCount) {
                val child = tab.getChild(i)
                if (child != null && (child.isSelected || child.isFocused)) return true
            }
        }
        return false
    }

    private fun isInsideShareSheet(root: AccessibilityNodeInfo): Boolean {
        val shareSheetIds = listOf(
            "direct_share_sheet",
            "direct_private_share_fragment",
            "direct_share_sheet_recyclerview",
            "share_sheet_container",
            "share_container"
        )
        for (id in shareSheetIds) {
            if (root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/$id").isNotEmpty()) {
                return true
            }
        }
        return false
    }

    private fun redirectToMessages(rootNode: AccessibilityNodeInfo, allowBackFallback: Boolean = false): Boolean {
        val now = SystemClock.uptimeMillis()
        if (now - lastActionTime < actionCooldownMs) return false

        // 1. Primary: Click the direct_tab (Message tab) in the bottom navigation bar
        if (clickDirectTab(rootNode)) {
            lastActionTime = now
            Log.d(tag, "Successfully clicked direct_tab to switch to Messages")
            showToast("💬 Switched to Messages")
            return true
        }

        // 2. Secondary: Top-right action bar direct inbox button
        if (clickActionBarInboxButton(rootNode)) {
            lastActionTime = now
            Log.d(tag, "Successfully clicked action bar inbox button")
            showToast("💬 Switched to Messages")
            return true
        }

        // 3. Tertiary: Dispatch tap gesture on the center bottom tab (only if tab_bar exists)
        if (tapCenterBottomTab(rootNode)) {
            lastActionTime = now
            Log.d(tag, "Dispatched gesture tap to center bottom tab")
            showToast("💬 Switched to Messages")
            return true
        }

        // 4. Fallback: If on an overlay/sub-view, press BACK to return
        if (allowBackFallback) {
            lastActionTime = now
            performGlobalAction(GLOBAL_ACTION_BACK)
            return true
        }

        return false
    }

    private fun clickDirectTab(root: AccessibilityNodeInfo): Boolean {
        // 1. Direct tab by ID
        val directTabs = root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/direct_tab")
        for (tab in directTabs) {
            if (clickNodeOrPerformTap(tab)) return true
            for (i in 0 until tab.childCount) {
                val child = tab.getChild(i) ?: continue
                if (clickNodeOrPerformTap(child)) return true
            }
        }

        // 2. Center tab (index 2) of tab_bar
        val tabBars = root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/tab_bar")
        for (tabBar in tabBars) {
            if (tabBar.childCount >= 3) {
                val centerTab = tabBar.getChild(2)
                if (centerTab != null && clickNodeOrPerformTap(centerTab)) return true
            }
            for (i in 0 until tabBar.childCount) {
                val child = tabBar.getChild(i) ?: continue
                val desc = child.contentDescription?.toString() ?: ""
                val id = child.viewIdResourceName ?: ""
                if (id.contains("direct") || desc.equals("Message", ignoreCase = true) || desc.equals("Direct", ignoreCase = true)) {
                    if (clickNodeOrPerformTap(child)) return true
                }
            }
        }

        // 3. Any node with text "Message" or desc "Message"
        val messageNodes = root.findAccessibilityNodeInfosByText("Message")
        for (node in messageNodes) {
            val resId = node.viewIdResourceName ?: ""
            val cDesc = node.contentDescription?.toString() ?: ""
            if (resId.contains("tab") || resId.contains("direct") || resId.contains("inbox") ||
                cDesc.contains("Message", ignoreCase = true) || cDesc.contains("Direct", ignoreCase = true)) {
                if (clickNodeOrPerformTap(node)) return true
            }
        }

        return false
    }

    private fun clickActionBarInboxButton(root: AccessibilityNodeInfo): Boolean {
        val inboxIds = listOf(
            "com.instagram.android:id/action_bar_inbox_button",
            "com.instagram.android:id/action_bar_button_inbox",
            "com.instagram.android:id/inbox_button"
        )
        for (id in inboxIds) {
            val nodes = root.findAccessibilityNodeInfosByViewId(id)
            for (node in nodes) {
                if (clickNodeOrPerformTap(node)) return true
            }
        }
        return false
    }

    private fun tapCenterBottomTab(root: AccessibilityNodeInfo): Boolean {
        val tabBars = root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/tab_bar")
        if (tabBars.isNotEmpty()) {
            val barBounds = Rect()
            tabBars[0].getBoundsInScreen(barBounds)
            if (barBounds.width() > 0 && barBounds.height() > 0) {
                return dispatchTap(barBounds.centerX().toFloat(), barBounds.centerY().toFloat())
            }
        }
        return false
    }

    private fun dispatchTap(x: Float, y: Float): Boolean {
        val path = Path().apply { moveTo(x, y) }
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, 50))
            .build()
        return dispatchGesture(gesture, null, null)
    }

    private fun isInsideReelsViewer(root: AccessibilityNodeInfo): Boolean {
        val reelsIds = listOf(
            "clips_viewer_container",
            "clips_media_item",
            "reel_viewer",
            "reel_recycler_view",
            "clips_swipe_refresh_layout",
            "clips_video_container",
            "clips_viewer_view_pager",
            "clips_author_name",
            "direct_thread_media_viewer",
            "media_viewer_container",
            "video_container"
        )
        for (id in reelsIds) {
            if (root.findAccessibilityNodeInfosByViewId("com.instagram.android:id/$id").isNotEmpty()) {
                return true
            }
        }
        return false
    }

    private fun handleYouTube() {
        val rootNode = rootInActiveWindow ?: return

        if (isInsideShorts(rootNode)) {
            Log.d(tag, "YouTube Shorts detected -> performing Back action")
            performGlobalAction(GLOBAL_ACTION_BACK)
            showToast("🚫 YouTube Shorts blocked by Lockin-Inator!")
            recordIntercept("shorts")
        }
    }

    private fun isInsideShorts(root: AccessibilityNodeInfo): Boolean {
        val shortsIds = listOf(
            "shorts_player",
            "reel_player_fragment",
            "reel_recycler_view",
            "reel_player_page_container",
            "shorts_container",
            "reel_watch_fragment"
        )
        for (id in shortsIds) {
            val nodes = root.findAccessibilityNodeInfosByViewId("com.google.android.youtube:id/$id")
            if (nodes.isNotEmpty()) return true
        }

        val shortsText = root.findAccessibilityNodeInfosByText("Shorts")
        if (shortsText.any { it.isSelected || it.isFocused }) return true

        return false
    }

    private fun showToast(message: String) {
        val now = SystemClock.uptimeMillis()
        if (now - lastToastTime > toastCooldownMs) {
            lastToastTime = now
            Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
        }
    }

    override fun onInterrupt() {}

    companion object {
        fun isServiceEnabled(context: Context): Boolean {
            val expectedId = ComponentName(context, LockinBlockerAccessibilityService::class.java).flattenToString()
            val enabledServices = Settings.Secure.getString(
                context.contentResolver,
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
            ) ?: return false
            return enabledServices.split(":").any { it.equals(expectedId, ignoreCase = true) }
        }
    }
}
