package com.example.lockininator

import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Handler
import android.os.Looper
import android.util.Log
import kotlinx.coroutines.*
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.HttpURLConnection
import java.net.InetSocketAddress
import java.net.URL
import java.util.concurrent.CopyOnWriteArrayList

class SyncManager(private val context: Context) {

    companion object {
        @Volatile
        private var instance: SyncManager? = null

        fun getInstance(context: Context): SyncManager {
            return instance ?: synchronized(this) {
                instance ?: SyncManager(context.applicationContext).also { instance = it }
            }
        }
    }

    private val prefs: SharedPreferences = context.getSharedPreferences("lockin_prefs", Context.MODE_PRIVATE)
    private var syncJob: Job? = null
    private var udpJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    var isConnected: Boolean = false
        private set
    var currentServerIp: String = prefs.getString("sync_pc_ip", "192.168.2.17") ?: "192.168.2.17"
        private set

    private val listeners = CopyOnWriteArrayList<(Boolean, String, Long) -> Unit>()

    fun addSyncListener(listener: (Boolean, String, Long) -> Unit) {
        if (!listeners.contains(listener)) {
            listeners.add(listener)
        }
    }

    fun removeSyncListener(listener: (Boolean, String, Long) -> Unit) {
        listeners.remove(listener)
    }

    var onSyncStatusChanged: ((Boolean, String, Long) -> Unit)? = null

    fun startSync() {
        stopSync()

        // 1. Start UDP Discovery Listener in background
        udpJob = scope.launch {
            listenForUdpBeacon()
        }

        // 2. Start polling / state sync loop
        syncJob = scope.launch {
            while (isActive) {
                pollPcStatus()
                delay(2000)
            }
        }
    }

    fun stopSync() {
        udpJob?.cancel()
        syncJob?.cancel()
        udpJob = null
        syncJob = null
        isConnected = false
    }

    private suspend fun listenForUdpBeacon() {
        var socket: DatagramSocket? = null
        try {
            socket = DatagramSocket(null).apply {
                reuseAddress = true
                bind(InetSocketAddress(8766))
            }
            socket.broadcast = true
            val buffer = ByteArray(1024)

            while (scope.isActive) {
                val packet = DatagramPacket(buffer, buffer.size)
                socket.receive(packet)
                val msg = String(packet.data, 0, packet.length)
                try {
                    val json = JSONObject(msg)
                    if (json.optString("service") == "lockin-inator-sync") {
                        val ip = json.optString("ip")
                        if (ip.isNotEmpty() && ip != currentServerIp) {
                            currentServerIp = ip
                            prefs.edit().putString("sync_pc_ip", ip).apply()
                            Log.d("LockinSync", "Discovered PC IP via UDP: $ip")
                        }
                    }
                } catch (e: Exception) {
                    Log.w("LockinSync", "Failed to parse UDP beacon: ${e.message}")
                }
            }
        } catch (e: Exception) {
            Log.w("LockinSync", "UDP beacon listener stopped: ${e.message}")
        } finally {
            socket?.close()
        }
    }

    private fun pollPcStatus() {
        try {
            val url = URL("http://$currentServerIp:8765/api/status")
            val conn = url.openConnection() as HttpURLConnection
            conn.connectTimeout = 1500
            conn.readTimeout = 1500
            conn.requestMethod = "GET"

            if (conn.responseCode == 200) {
                val reader = BufferedReader(InputStreamReader(conn.inputStream))
                val response = reader.readText()
                reader.close()

                val json = JSONObject(response)
                val state = json.optString("state", "IDLE")
                val remainingSeconds = json.optLong("remaining_seconds", 0L)
                isConnected = true

                Handler(Looper.getMainLooper()).post {
                    handleStateFromPc(state, remainingSeconds)
                }
            } else {
                if (isConnected) {
                    isConnected = false
                    notifyListeners(false, "IDLE", 0L)
                }
            }
            conn.disconnect()
        } catch (e: Exception) {
            if (isConnected) {
                isConnected = false
                notifyListeners(false, "IDLE", 0L)
            }
        }
    }

    private fun handleStateFromPc(state: String, remainingSeconds: Long) {
        val currentStudyActive = prefs.getBoolean("study_mode_active", false)

        if (state == "STUDY") {
            if (!currentStudyActive) {
                prefs.edit().putBoolean("study_mode_active", true).apply()
                Log.d("LockinSync", "Enabling study mode synced from PC ($remainingSeconds s left)")

                // Silence notifications with DND
                try {
                    val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                    if (notificationManager.isNotificationPolicyAccessGranted) {
                        notificationManager.setInterruptionFilter(NotificationManager.INTERRUPTION_FILTER_NONE)
                    }
                } catch (e: Exception) {
                    Log.w("LockinSync", "DND silence error: ${e.message}")
                }

                // Bring MainActivity to the front so screen pinning can lock
                try {
                    val intent = Intent(context, MainActivity::class.java).apply {
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
                        putExtra("EXTRA_START_LOCK_TASK", true)
                    }
                    context.startActivity(intent)
                } catch (e: Exception) {
                    Log.e("LockinSync", "Failed to bring MainActivity to front: ${e.message}")
                }
            }
            notifyListeners(true, state, remainingSeconds)
        } else if (state == "BREAK") {
            if (currentStudyActive) {
                prefs.edit().putBoolean("study_mode_active", false).apply()
                try {
                    val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                    if (notificationManager.isNotificationPolicyAccessGranted) {
                        notificationManager.setInterruptionFilter(NotificationManager.INTERRUPTION_FILTER_ALL)
                    }
                } catch (e: Exception) {
                    Log.w("LockinSync", "DND restore error: ${e.message}")
                }
            }
            notifyListeners(true, state, remainingSeconds)
        } else {
            if (currentStudyActive) {
                prefs.edit().putBoolean("study_mode_active", false).apply()
                try {
                    val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                    if (notificationManager.isNotificationPolicyAccessGranted) {
                        notificationManager.setInterruptionFilter(NotificationManager.INTERRUPTION_FILTER_ALL)
                    }
                } catch (e: Exception) {
                    Log.w("LockinSync", "DND restore error: ${e.message}")
                }
            }
            notifyListeners(true, "IDLE", 0L)
        }
    }

    private fun notifyListeners(connected: Boolean, state: String, remainingSeconds: Long) {
        Handler(Looper.getMainLooper()).post {
            onSyncStatusChanged?.invoke(connected, state, remainingSeconds)
            for (listener in listeners) {
                try {
                    listener(connected, state, remainingSeconds)
                } catch (e: Exception) {
                    Log.e("LockinSync", "Listener error: ${e.message}")
                }
            }
        }
    }

    fun sendActionToPc(action: String, durationMinutes: Int = 50) {
        scope.launch {
            try {
                val url = URL("http://$currentServerIp:8765/api/action")
                val conn = url.openConnection() as HttpURLConnection
                conn.connectTimeout = 2000
                conn.readTimeout = 2000
                conn.requestMethod = "POST"
                conn.setRequestProperty("Content-Type", "application/json")
                conn.doOutput = true

                val payload = JSONObject().apply {
                    put("action", action)
                    put("duration_minutes", durationMinutes)
                }

                val writer = OutputStreamWriter(conn.outputStream)
                writer.write(payload.toString())
                writer.flush()
                writer.close()

                val code = conn.responseCode
                Log.d("LockinSync", "Sent $action to PC, response code: $code")
                conn.disconnect()
            } catch (e: Exception) {
                Log.e("LockinSync", "Failed to send action to PC: ${e.message}")
            }
        }
    }
}
