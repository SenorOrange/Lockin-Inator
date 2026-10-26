package com.example.lockininator

import android.annotation.SuppressLint
import android.app.Activity
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.os.Bundle
import android.os.CountDownTimer
import android.provider.Settings
import android.view.View
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import kotlinx.coroutines.delay
import kotlin.math.abs
import kotlin.math.roundToInt

@Suppress("DEPRECATION")
class MainActivity : ComponentActivity() {

    private val prefs: SharedPreferences by lazy {
        getSharedPreferences("lockin_prefs", Context.MODE_PRIVATE)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            android.util.Log.e("LockinApp", "Uncaught exception in thread ${thread.name}", throwable)
        }
        setContent {
            val notificationManager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
            if (!notificationManager.isNotificationPolicyAccessGranted && !prefs.getBoolean("dnd_prompted", false)) {
                prefs.edit().putBoolean("dnd_prompted", true).apply()
                try {
                    val intent = Intent(Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS)
                    startActivity(intent)
                } catch (e: Exception) {
                    android.util.Log.e("LockinApp", "Error launching DND settings", e)
                }
            }
            val activity = this
            var showSplash by remember { mutableStateOf(true) }

            LaunchedEffect(Unit) {
                delay(1200)
                showSplash = false
            }

            MaterialTheme(
                colorScheme = darkColorScheme(
                    primary = Color(0xFF6A0DAD),
                    surface = Color.Black,
                    onBackground = Color.White,
                    onSurface = Color.White
                )
            ) {
                if (showSplash) {
                    SplashScreen()
                } else {
                    LockininatorApp(activity)
                }
            }
        }
    }

    @SuppressLint("GestureBackNavigation")
    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        super.onBackPressed()
    }

    override fun onResume() {
        super.onResume()
        if (prefs.getBoolean("study_mode_active", false)) {
            try {
                startLockTask()
            } catch (e: Exception) {
                android.util.Log.w("LockinApp", "startLockTask failed in onResume: ${e.message}")
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (intent.getBooleanExtra("EXTRA_START_LOCK_TASK", false) ||
            prefs.getBoolean("study_mode_active", false)) {
            try {
                startLockTask()
            } catch (e: Exception) {
                android.util.Log.w("LockinApp", "startLockTask failed in onNewIntent: ${e.message}")
            }
        }
    }

    @Composable
    fun SplashScreen() {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                CircularProgressIndicator(
                    color = Color(0xFF6A0DAD),
                    strokeWidth = 4.dp,
                    modifier = Modifier.size(60.dp)
                )
                Spacer(modifier = Modifier.height(24.dp))
                Text(
                    text = "Lockin-Inator",
                    color = Color.White,
                    fontSize = 32.sp,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Focus Timer + Reels/Shorts Shield",
                    color = Color.Gray,
                    fontSize = 14.sp
                )
            }
        }
    }

    @Composable
    fun LockininatorApp(activity: Activity) {
        val context = LocalContext.current
        var timeSeconds by remember { mutableFloatStateOf(60f) }
        var timeRemaining by remember { mutableLongStateOf(0L) }
        var timerRunning by remember { mutableStateOf(false) }
        var inExtraTime by remember { mutableStateOf(false) }
        var extraTime by remember { mutableLongStateOf(0L) }
        var userSetTime by remember { mutableLongStateOf(0L) }

        var countDownTimer: CountDownTimer? by remember { mutableStateOf(null) }
        var extraTimer: CountDownTimer? by remember { mutableStateOf(null) }
        var showSummary by remember { mutableStateOf(false) }

        // State for Pop-Open Settings Screen
        var showSettingsDialog by remember { mutableStateOf(false) }

        // State for 60-Second Urge-Breaker Friction Dialog
        var showUrgeBreakerDialog by remember { mutableStateOf(false) }
        var urgeBreakerSecondsRemaining by remember { mutableIntStateOf(60) }
        var pendingDisableAction by remember { mutableStateOf<(() -> Unit)?>(null) }
        var pendingSettingName by remember { mutableStateOf("") }

        // Live Doomscroll & Shield Stats
        var totalIntercepts by remember { mutableIntStateOf(prefs.getInt("total_intercepts", 0)) }
        var reelsIntercepts by remember { mutableIntStateOf(prefs.getInt("reels_intercepts", 0)) }
        var shortsIntercepts by remember { mutableIntStateOf(prefs.getInt("shorts_intercepts", 0)) }
        var fbIntercepts by remember { mutableIntStateOf(prefs.getInt("facebook_intercepts", 0)) }

        // Social Lock-in Shield Settings
        var isAccessibilityOn by remember { mutableStateOf(LockinBlockerAccessibilityService.isServiceEnabled(context)) }
        var blockReels by remember { mutableStateOf(prefs.getBoolean("block_reels", true)) }
        var redirectHomeToMessages by remember { mutableStateOf(prefs.getBoolean("redirect_home_to_messages", false)) }
        var blockShorts by remember { mutableStateOf(prefs.getBoolean("block_shorts", true)) }
        var blockFacebook by remember { mutableStateOf(prefs.getBoolean("block_facebook", true)) }
        var blockAlways by remember { mutableStateOf(prefs.getBoolean("block_always", true)) }

        // Local Wi-Fi Sync across PC, Browser, and Phone
        val syncManager = remember { SyncManager.getInstance(context) }
        var syncPcEnabled by remember { mutableStateOf(prefs.getBoolean("sync_pc_enabled", true)) }
        var isSyncConnected by remember { mutableStateOf(false) }

        DisposableEffect(syncPcEnabled) {
            val listener: (Boolean, String, Long) -> Unit = { connected, state, remainingSec ->
                isSyncConnected = connected
                if (state == "STUDY") {
                    if (!timerRunning) {
                        prefs.edit().putBoolean("study_mode_active", true).apply()
                        try {
                            activity.startLockTask()
                        } catch (e: Exception) {
                            android.util.Log.w("LockinApp", "startLockTask failed in sync: ${e.message}")
                        }
                        try {
                            val notificationManager = activity.getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                            if (notificationManager.isNotificationPolicyAccessGranted) {
                                notificationManager.setInterruptionFilter(NotificationManager.INTERRUPTION_FILTER_NONE)
                            }
                        } catch (e: SecurityException) {
                            android.util.Log.e("LockinApp", "DND access denied in sync", e)
                        }

                        timerRunning = true
                        inExtraTime = false
                        timeRemaining = remainingSec * 1000L
                        userSetTime = timeRemaining
                        countDownTimer?.cancel()
                        countDownTimer = object : CountDownTimer(timeRemaining, 1000) {
                            override fun onTick(millisUntilFinished: Long) {
                                timeRemaining = millisUntilFinished
                            }
                            override fun onFinish() {
                                try {
                                    activity.stopLockTask()
                                } catch (e: Exception) {
                                    android.util.Log.w("LockinApp", "stopLockTask failed onFinish: ${e.message}")
                                }
                                try {
                                    val notificationManager = activity.getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                                    if (notificationManager.isNotificationPolicyAccessGranted) {
                                        notificationManager.setInterruptionFilter(NotificationManager.INTERRUPTION_FILTER_ALL)
                                    }
                                } catch (e: SecurityException) {
                                    android.util.Log.e("LockinApp", "DND access denied onFinish", e)
                                }
                                timerRunning = false
                                inExtraTime = true
                                extraTime = 0L
                                extraTimer = object : CountDownTimer(60_000_000, 1000) {
                                    override fun onTick(millisUntilFinished: Long) {
                                        extraTime += 1000
                                    }
                                    override fun onFinish() {}
                                }.start()
                            }
                        }.start()
                    } else {
                        // Drift correction: if phone timer is more than 3s off PC timer, sync it
                        val diff = abs(timeRemaining - (remainingSec * 1000L))
                        if (diff > 3000) {
                            timeRemaining = remainingSec * 1000L
                        }
                    }
                } else if (state == "BREAK" || state == "IDLE") {
                    prefs.edit().putBoolean("study_mode_active", false).apply()
                    try {
                        activity.stopLockTask()
                    } catch (e: Exception) {
                        android.util.Log.w("LockinApp", "stopLockTask failed on idle/break: ${e.message}")
                    }
                    try {
                        val notificationManager = activity.getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                        if (notificationManager.isNotificationPolicyAccessGranted) {
                            notificationManager.setInterruptionFilter(NotificationManager.INTERRUPTION_FILTER_ALL)
                        }
                    } catch (e: SecurityException) {
                        android.util.Log.e("LockinApp", "DND access denied on idle/break", e)
                    }
                    if (timerRunning) {
                        countDownTimer?.cancel()
                        timerRunning = false
                    }
                    if (inExtraTime) {
                        extraTimer?.cancel()
                        inExtraTime = false
                    }
                }
            }

            if (syncPcEnabled) {
                syncManager.addSyncListener(listener)
                syncManager.startSync()
            } else {
                syncManager.removeSyncListener(listener)
                isSyncConnected = false
            }
            onDispose {
                syncManager.removeSyncListener(listener)
            }
        }

        val lifecycleOwner = LocalLifecycleOwner.current
        DisposableEffect(lifecycleOwner) {
            val observer = LifecycleEventObserver { _, event ->
                if (event == Lifecycle.Event.ON_RESUME) {
                    isAccessibilityOn = LockinBlockerAccessibilityService.isServiceEnabled(context)
                    totalIntercepts = prefs.getInt("total_intercepts", 0)
                    reelsIntercepts = prefs.getInt("reels_intercepts", 0)
                    shortsIntercepts = prefs.getInt("shorts_intercepts", 0)
                    fbIntercepts = prefs.getInt("facebook_intercepts", 0)
                }
            }
            lifecycleOwner.lifecycle.addObserver(observer)
            onDispose {
                lifecycleOwner.lifecycle.removeObserver(observer)
            }
        }

        LaunchedEffect(timerRunning) {
            if (timerRunning) {
                window.decorView.systemUiVisibility =
                    (View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                            or View.SYSTEM_UI_FLAG_FULLSCREEN
                            or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION)
            } else {
                window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_VISIBLE
            }
        }

        @SuppressLint("DefaultLocale")
        fun formatTime(ms: Long): String {
            val totalSec = ms / 1000
            val hours = totalSec / 3600
            val minutes = (totalSec % 3600) / 60
            val seconds = totalSec % 60
            return String.format("%02d:%02d:%02d", hours, minutes, seconds)
        }

        fun snapTime(raw: Float): Float {
            val clamped = raw.coerceIn(1f, 7200f)
            val base = if (clamped < 60f) {
                clamped.roundToInt().toFloat()
            } else {
                (clamped / 60f).roundToInt() * 60f
            }
            val milestonesSec = (15..120 step 15).map { it * 60 }
            val tolerance = 120f
            var snapped = base
            var bestDelta = Float.MAX_VALUE
            for (m in milestonesSec) {
                val delta = abs(base - m)
                if (delta < bestDelta) {
                    bestDelta = delta
                    snapped = m.toFloat()
                }
            }
            return if (bestDelta <= tolerance) snapped else base
        }

        // Helper for 60-Second Urge-Breaker Friction
        fun requestDisableWithFriction(settingName: String, onConfirm: () -> Unit) {
            pendingSettingName = settingName
            pendingDisableAction = onConfirm
            urgeBreakerSecondsRemaining = 60
            showUrgeBreakerDialog = true
        }

        if (showSummary) {
            SessionSummaryScreen(totalMillis = userSetTime - timeRemaining + extraTime)
            LaunchedEffect(Unit) {
                delay(10000)
                activity.finishAffinity()
            }
        } else {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black)
                    .padding(horizontal = 24.dp, vertical = 20.dp)
            ) {
                // Top Section: Header + Intercept Stats Bar directly below
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .align(Alignment.TopCenter)
                ) {
                    // Top Header Row with App Title + Single Sleek Pop-Open Settings Button
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 12.dp, bottom = 12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "Lockin-Inator",
                                color = Color.White,
                                fontSize = 24.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = if (isAccessibilityOn) "🟢 Shield Active" else "🟡 Setup Required",
                                color = if (isAccessibilityOn) Color(0xFF34D399) else Color(0xFFFBBF24),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Medium
                            )
                        }

                        // Single Sleek Button to Pop Open Main Settings
                        Box(
                            modifier = Modifier
                                .background(Color(0xFF1E1E2E), RoundedCornerShape(12.dp))
                                .clickable { showSettingsDialog = true }
                                .padding(horizontal = 14.dp, vertical = 9.dp)
                        ) {
                            Text(
                                text = "⚙️ Settings",
                                color = Color(0xFFC084FC),
                                fontSize = 13.sp,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }

                    // COMPACT DOOMSCROLL STATS BAR
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF13131D)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 14.dp, vertical = 9.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = "🛡️ Intercepts: $totalIntercepts",
                                    color = Color.White,
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                                Spacer(modifier = Modifier.height(2.dp))
                                Text(
                                    text = "IG: $reelsIntercepts • YT: $shortsIntercepts • FB: $fbIntercepts",
                                    color = Color.Gray,
                                    fontSize = 11.sp
                                )
                            }
                        }
                    }
                }

                // Center Section: Study Timer centered in the middle of the display
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .align(Alignment.Center),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    if (!timerRunning && !inExtraTime) {
                        val displayMinutes = (timeSeconds.toInt() / 60)
                        val displaySeconds = (timeSeconds.toInt() % 60)

                        Text(
                            text = "Study Timer",
                            color = Color.Gray,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Medium
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "${displayMinutes}m ${displaySeconds}s",
                            color = Color.White,
                            fontSize = 42.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(bottom = 20.dp)
                        )

                        Slider(
                            value = timeSeconds,
                            onValueChange = { timeSeconds = snapTime(it) },
                            valueRange = 1f..7200f,
                            modifier = Modifier.padding(bottom = 28.dp)
                        )

                        Button(
                            onClick = {
                                if (syncPcEnabled) {
                                    syncManager.sendActionToPc("START_STUDY", (timeSeconds / 60).roundToInt())
                                }
                                prefs.edit().putBoolean("study_mode_active", true).apply()
                                try {
                                    activity.startLockTask()
                                } catch (e: Exception) {
                                    android.util.Log.w("LockinApp", "startLockTask failed: ${e.message}")
                                }
                                try {
                                    val notificationManager = activity.getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                                    if (notificationManager.isNotificationPolicyAccessGranted) {
                                        notificationManager.setInterruptionFilter(NotificationManager.INTERRUPTION_FILTER_NONE)
                                        Toast.makeText(activity, "Lockin-Inator active — notifications silenced", Toast.LENGTH_SHORT).show()
                                    } else {
                                        Toast.makeText(activity, "Lockin-Inator active", Toast.LENGTH_SHORT).show()
                                    }
                                } catch (e: SecurityException) {
                                    android.util.Log.e("LockinApp", "DND access denied", e)
                                    Toast.makeText(activity, "Lockin-Inator active", Toast.LENGTH_SHORT).show()
                                }

                                timerRunning = true
                                inExtraTime = false
                                userSetTime = timeSeconds.toLong() * 1000
                                timeRemaining = userSetTime
                                countDownTimer = object : CountDownTimer(timeRemaining, 1000) {
                                    override fun onTick(millisUntilFinished: Long) {
                                        timeRemaining = millisUntilFinished
                                    }
                                    override fun onFinish() {
                                        prefs.edit().putBoolean("study_mode_active", false).apply()
                                        try {
                                            activity.stopLockTask()
                                        } catch (e: Exception) {
                                            android.util.Log.w("LockinApp", "stopLockTask failed: ${e.message}")
                                        }
                                        try {
                                            val notificationManager = activity.getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                                            if (notificationManager.isNotificationPolicyAccessGranted) {
                                                notificationManager.setInterruptionFilter(NotificationManager.INTERRUPTION_FILTER_ALL)
                                            }
                                        } catch (e: SecurityException) {
                                            android.util.Log.e("LockinApp", "DND access denied onFinish", e)
                                        }
                                        timerRunning = false
                                        inExtraTime = true
                                        extraTime = 0L
                                        extraTimer = object : CountDownTimer(60_000_000, 1000) {
                                            override fun onTick(millisUntilFinished: Long) {
                                                extraTime += 1000
                                            }
                                            override fun onFinish() {}
                                        }.start()
                                    }
                                }.start()
                            },
                            modifier = Modifier
                                .fillMaxWidth(0.9f)
                                .height(54.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6A0DAD)),
                            shape = RoundedCornerShape(14.dp)
                        ) {
                            Text(
                                "Activate Study Mode",
                                color = Color.White,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }

                    // Countdown view
                    if (timerRunning) {
                        Spacer(modifier = Modifier.height(32.dp))
                        Text(
                            text = "Time Remaining:",
                            color = Color.White,
                            fontSize = 22.sp,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        Text(
                            text = formatTime(timeRemaining),
                            color = Color.White,
                            fontSize = 46.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }

                    // Extra time view
                    if (inExtraTime) {
                        Spacer(modifier = Modifier.height(32.dp))
                        Text(
                            text = "You have been locking in for:",
                            color = Color.White,
                            fontSize = 22.sp,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        Text(
                            text = formatTime(userSetTime + extraTime),
                            color = Color.White,
                            fontSize = 46.sp,
                            fontWeight = FontWeight.Bold
                        )

                        Button(
                            onClick = {
                                if (syncPcEnabled) {
                                    syncManager.sendActionToPc("RESET")
                                }
                                prefs.edit().putBoolean("study_mode_active", false).apply()
                                try {
                                    val notificationManager = activity.getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                                    if (notificationManager.isNotificationPolicyAccessGranted) {
                                        notificationManager.setInterruptionFilter(NotificationManager.INTERRUPTION_FILTER_ALL)
                                    }
                                } catch (e: SecurityException) {
                                    android.util.Log.e("LockinApp", "DND access denied on reset", e)
                                }
                                try {
                                    activity.stopLockTask()
                                } catch (e: Exception) {
                                    android.util.Log.w("LockinApp", "stopLockTask failed: ${e.message}")
                                }
                                showSummary = true

                                countDownTimer?.cancel()
                                extraTimer?.cancel()
                            },
                            modifier = Modifier.padding(top = 24.dp)
                        ) {
                            Text(
                                "Stop Study Mode",
                                color = Color.White
                            )
                        }
                    }
                }
            }
        }

        // ====================================================================
        // POP-OPEN SETTINGS SCREEN (Modal Dialog)
        // ====================================================================
        if (showSettingsDialog) {
            Dialog(
                onDismissRequest = { showSettingsDialog = false },
                properties = DialogProperties(usePlatformDefaultWidth = false)
            ) {
                Card(
                    modifier = Modifier
                        .fillMaxWidth(0.92f)
                        .padding(vertical = 24.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF14141E)),
                    shape = RoundedCornerShape(22.dp)
                ) {
                    Column(
                        modifier = Modifier
                            .padding(22.dp)
                            .verticalScroll(rememberScrollState())
                    ) {
                        // Header with Title + Close button
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "🛡️ Main Settings",
                                color = Color.White,
                                fontSize = 19.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Box(
                                modifier = Modifier
                                    .size(32.dp)
                                    .background(Color(0xFF262636), RoundedCornerShape(16.dp))
                                    .clickable { showSettingsDialog = false },
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = "✕",
                                    color = Color.White,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(18.dp))

                        // Accessibility Status Card
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(
                                    if (isAccessibilityOn) Color(0xFF1E3A2F) else Color(0xFF3E2D1E),
                                    RoundedCornerShape(12.dp)
                                )
                                .clickable {
                                    val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                                    context.startActivity(intent)
                                    Toast.makeText(context, "Turn on Lockin-Inator in Accessibility", Toast.LENGTH_LONG).show()
                                }
                                .padding(horizontal = 14.dp, vertical = 12.dp)
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column {
                                    Text(
                                        text = "Accessibility Service",
                                        color = Color.White,
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.SemiBold
                                    )
                                    Text(
                                        text = if (isAccessibilityOn) "Running & protecting in background" else "Tap here to turn on in settings",
                                        color = if (isAccessibilityOn) Color(0xFF34D399) else Color(0xFFFBBF24),
                                        fontSize = 11.sp
                                    )
                                }
                                Text(
                                    text = if (isAccessibilityOn) "🟢 Active" else "🔴 Off",
                                    color = if (isAccessibilityOn) Color(0xFF34D399) else Color(0xFFEF4444),
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(18.dp))

                        // Instagram Reels Tab Toggle (With 60s Urge-Breaker on disable)
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text("Block Instagram Reels Tab", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                                Text("Redirects Reels tab to Messages; DMs stay functional", color = Color.Gray, fontSize = 11.sp)
                            }
                            Switch(
                                checked = blockReels,
                                onCheckedChange = { targetState ->
                                    if (!targetState) {
                                        requestDisableWithFriction("Instagram Reels Blocker") {
                                            blockReels = false
                                            prefs.edit().putBoolean("block_reels", false).apply()
                                        }
                                    } else {
                                        blockReels = true
                                        prefs.edit().putBoolean("block_reels", true).apply()
                                    }
                                },
                                colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Color(0xFF6A0DAD))
                            )
                        }

                        HorizontalDivider(modifier = Modifier.padding(vertical = 10.dp), color = Color(0xFF262636))

                        // YouTube Shorts Toggle (With 60s Urge-Breaker on disable)
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text("Block YouTube Shorts", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                                Text("Closes Shorts player; long-form videos stay active", color = Color.Gray, fontSize = 11.sp)
                            }
                            Switch(
                                checked = blockShorts,
                                onCheckedChange = { targetState ->
                                    if (!targetState) {
                                        requestDisableWithFriction("YouTube Shorts Blocker") {
                                            blockShorts = false
                                            prefs.edit().putBoolean("block_shorts", false).apply()
                                        }
                                    } else {
                                        blockShorts = true
                                        prefs.edit().putBoolean("block_shorts", true).apply()
                                    }
                                },
                                colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Color(0xFF6A0DAD))
                            )
                        }

                        HorizontalDivider(modifier = Modifier.padding(vertical = 10.dp), color = Color(0xFF262636))

                        // FEATURE 1: Facebook Reels Toggle (With 60s Urge-Breaker on disable)
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text("Block Facebook Reels", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                                Text("Closes Facebook reels player; feed & Messenger work", color = Color.Gray, fontSize = 11.sp)
                            }
                            Switch(
                                checked = blockFacebook,
                                onCheckedChange = { targetState ->
                                    if (!targetState) {
                                        requestDisableWithFriction("Facebook Reels Blocker") {
                                            blockFacebook = false
                                            prefs.edit().putBoolean("block_facebook", false).apply()
                                        }
                                    } else {
                                        blockFacebook = true
                                        prefs.edit().putBoolean("block_facebook", true).apply()
                                    }
                                },
                                colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Color(0xFF6A0DAD))
                            )
                        }

                        HorizontalDivider(modifier = Modifier.padding(vertical = 10.dp), color = Color(0xFF262636))

                        // Redirect Home to Messages Toggle
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text("Redirect Home to Messages", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                                Text("Keeps Instagram purely in the Messages tab", color = Color.Gray, fontSize = 11.sp)
                            }
                            Switch(
                                checked = redirectHomeToMessages,
                                onCheckedChange = {
                                    redirectHomeToMessages = it
                                    prefs.edit().putBoolean("redirect_home_to_messages", it).apply()
                                },
                                colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Color(0xFF6A0DAD))
                            )
                        }

                        HorizontalDivider(modifier = Modifier.padding(vertical = 10.dp), color = Color(0xFF262636))

                        // 24/7 Always Active vs Study Session Only (With 60s Urge-Breaker on disable)
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text("Always Active (24/7 Shield)", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                                Text(
                                    if (blockAlways) "Protects continuously in background" else "Protects only during study timer",
                                    color = Color.Gray,
                                    fontSize = 11.sp
                                )
                            }
                            Switch(
                                checked = blockAlways,
                                onCheckedChange = { targetState ->
                                    if (!targetState) {
                                        requestDisableWithFriction("Always Active Shield") {
                                            blockAlways = false
                                            prefs.edit().putBoolean("block_always", false).apply()
                                        }
                                    } else {
                                        blockAlways = true
                                        prefs.edit().putBoolean("block_always", true).apply()
                                    }
                                },
                                colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Color(0xFF6A0DAD))
                            )
                        }

                        HorizontalDivider(modifier = Modifier.padding(vertical = 10.dp), color = Color(0xFF262636))

                        // FEATURE: PC & Browser Wi-Fi Sync
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text("PC & Browser Wi-Fi Sync", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                                Text(
                                    if (isSyncConnected) "Connected to PC (${syncManager.currentServerIp})" else "Searching for PC on local Wi-Fi...",
                                    color = if (isSyncConnected) Color(0xFF10B981) else Color.Gray,
                                    fontSize = 11.sp
                                )
                            }
                            Switch(
                                checked = syncPcEnabled,
                                onCheckedChange = {
                                    syncPcEnabled = it
                                    prefs.edit().putBoolean("sync_pc_enabled", it).apply()
                                },
                                colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Color(0xFF6A0DAD))
                            )
                        }

                        Spacer(modifier = Modifier.height(18.dp))

                        // One-Tap Direct Messages Shortcut Button
                        Button(
                            onClick = {
                                try {
                                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://instagram.com/direct/inbox/"))
                                    intent.setPackage("com.instagram.android")
                                    intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
                                    context.startActivity(intent)
                                } catch (e: Exception) {
                                    Toast.makeText(context, "Instagram app not found", Toast.LENGTH_SHORT).show()
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF241E38)),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("💬 Open Instagram DMs Directly", color = Color(0xFFC084FC), fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                        }

                        Spacer(modifier = Modifier.height(14.dp))

                        // Done / Close Button
                        Button(
                            onClick = { showSettingsDialog = false },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(46.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6A0DAD)),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("Done", color = Color.White, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }

        // ====================================================================
        // FEATURE 2: 60-SECOND URGE-BREAKER FRICTION MODAL
        // ====================================================================
        if (showUrgeBreakerDialog) {
            LaunchedEffect(showUrgeBreakerDialog) {
                while (urgeBreakerSecondsRemaining > 0) {
                    delay(1000)
                    urgeBreakerSecondsRemaining--
                }
            }

            Dialog(
                onDismissRequest = {
                    showUrgeBreakerDialog = false
                    pendingDisableAction = null
                },
                properties = DialogProperties(dismissOnBackPress = true, dismissOnClickOutside = false)
            ) {
                Card(
                    modifier = Modifier
                        .fillMaxWidth(0.92f)
                        .padding(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF14141E)),
                    shape = RoundedCornerShape(22.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center
                    ) {
                        Text(
                            text = "⏸️ Urge-Breaker Pause",
                            color = Color.White,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            textAlign = TextAlign.Center
                        )

                        Spacer(modifier = Modifier.height(10.dp))

                        Text(
                            text = "Take a slow, deep breath. 90% of doomscrolling impulses completely fade away within 60 seconds.",
                            color = Color(0xFFD1D5DB),
                            fontSize = 13.sp,
                            textAlign = TextAlign.Center,
                            lineHeight = 18.sp
                        )

                        Spacer(modifier = Modifier.height(24.dp))

                        // Live 60-Second Countdown Circle
                        Box(
                            contentAlignment = Alignment.Center,
                            modifier = Modifier.size(110.dp)
                        ) {
                            CircularProgressIndicator(
                                progress = { (urgeBreakerSecondsRemaining / 60f) },
                                color = if (urgeBreakerSecondsRemaining > 0) Color(0xFFC084FC) else Color(0xFFEF4444),
                                trackColor = Color(0xFF262636),
                                strokeWidth = 6.dp,
                                modifier = Modifier.fillMaxSize()
                            )
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text(
                                    text = "${urgeBreakerSecondsRemaining}s",
                                    color = Color.White,
                                    fontSize = 28.sp,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    text = if (urgeBreakerSecondsRemaining > 0) "breathe" else "unlocked",
                                    color = Color.Gray,
                                    fontSize = 11.sp
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(24.dp))

                        Text(
                            text = "Are you sure you want to turn off $pendingSettingName?",
                            color = Color(0xFF9CA3AF),
                            fontSize = 12.sp,
                            textAlign = TextAlign.Center
                        )

                        Spacer(modifier = Modifier.height(18.dp))

                        // 1. Stay Locked In Button (Always available, encouraged)
                        Button(
                            onClick = {
                                showUrgeBreakerDialog = false
                                pendingDisableAction = null
                            },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(48.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6A0DAD)),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text(
                                "🛡️ Stay Locked In (Cancel)",
                                color = Color.White,
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        // 2. Turn Off Button (Disabled until full 60 seconds elapses)
                        Button(
                            onClick = {
                                if (urgeBreakerSecondsRemaining == 0) {
                                    pendingDisableAction?.invoke()
                                    showUrgeBreakerDialog = false
                                    pendingDisableAction = null
                                }
                            },
                            enabled = (urgeBreakerSecondsRemaining == 0),
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(44.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color(0xFF3F1D1D),
                                disabledContainerColor = Color(0xFF1E1E26)
                            ),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text(
                                text = if (urgeBreakerSecondsRemaining > 0) "Wait ${urgeBreakerSecondsRemaining}s to Unlock" else "Yes, Turn Off Protection",
                                color = if (urgeBreakerSecondsRemaining == 0) Color(0xFFEF4444) else Color(0xFF6B7280),
                                fontSize = 13.sp,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }
                }
            }
        }
    }

    @SuppressLint("DefaultLocale")
    @Composable
    fun SessionSummaryScreen(totalMillis: Long) {
        val hours = totalMillis / 3_600_000
        val minutes = (totalMillis % 3_600_000) / 60_000
        val seconds = (totalMillis % 60_000) / 1000

        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "Session Complete!",
                    color = Color.White,
                    fontSize = 36.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = String.format("You studied for %02d:%02d:%02d", hours, minutes, seconds),
                    color = Color.White,
                    fontSize = 22.sp
                )
            }
        }
    }
}
