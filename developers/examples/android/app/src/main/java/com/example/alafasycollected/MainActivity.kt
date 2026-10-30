package com.example.alafasycollected

import android.app.Activity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.NumberPicker
import android.widget.TextView
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import org.json.JSONArray
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

private const val BASE = "https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/download/v1.0.0"
private data class Timing(val ayah: Int, val start: Long, val end: Long)
private fun name(n: Int) = n.toString().padStart(3, '0')

class MainActivity : Activity() {
    private lateinit var player: ExoPlayer
    private lateinit var ayahLabel: TextView
    private lateinit var status: TextView
    private lateinit var pick: NumberPicker
    private val main = Handler(Looper.getMainLooper())
    private val executor = Executors.newSingleThreadExecutor()
    private var timings: List<Timing> = emptyList()
    private var generation = 0
    private var closed = false

    private val ticker = object : Runnable {
        override fun run() {
            if (closed) return
            val ms = player.currentPosition
            val ayah = timings.firstOrNull { ms >= it.start && ms < it.end }?.ayah
            ayahLabel.text = "الآية الحالية: ${ayah ?: "—"}"
            main.postDelayed(this, 150)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        player = ExoPlayer.Builder(this).build()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 48, 32, 24)
            gravity = Gravity.CENTER_HORIZONTAL
        }
        val title = TextView(this).apply {
            text = "مشاري العفاسي — مصحف مجمع"
            textSize = 23f
        }
        pick = NumberPicker(this).apply { minValue = 1; maxValue = 114; value = 1 }
        val play = Button(this).apply { text = "تشغيل السورة" }
        val pause = Button(this).apply { text = "إيقاف مؤقت / متابعة" }
        ayahLabel = TextView(this).apply { text = "الآية الحالية: —"; textSize = 24f }
        status = TextView(this).apply { text = "هذا المثال يعرض رقم الآية فقط" }
        listOf<View>(title, pick, play, pause, ayahLabel, status).forEach { root.addView(it) }
        setContentView(root)

        play.setOnClickListener { load(pick.value) }
        pause.setOnClickListener {
            if (player.isPlaying) player.pause() else if (player.playbackState != Player.STATE_IDLE) player.play()
        }
        player.addListener(object : Player.Listener {
            override fun onPlayerError(error: PlaybackException) {
                status.text = "تعذّر تشغيل ملف الصوت: ${error.errorCodeName}"
            }
        })
        main.post(ticker)
    }

    private fun load(surah: Int) {
        val requestId = ++generation
        player.stop()
        player.clearMediaItems()
        timings = emptyList()
        status.text = "تحميل توقيتات السورة $surah..."
        executor.execute {
            try {
                val url = URL("$BASE/timings-${name(surah)}.json")
                val connection = (url.openConnection() as HttpURLConnection).apply {
                    connectTimeout = 15000
                    readTimeout = 15000
                    instanceFollowRedirects = true
                }
                val body: String
                try {
                    if (connection.responseCode != 200) error("JSON HTTP ${connection.responseCode}")
                    if (connection.contentLengthLong > 500_000) error("Timing file too large")
                    body = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
                    if (body.length > 500_000) error("Timing file too large")
                } finally { connection.disconnect() }
                val items = JSONArray(body)
                require(items.length() in 1..286) { "Invalid timing count" }
                val rows = (0 until items.length()).map { index ->
                    val row = items.getJSONObject(index)
                    val ayah = row.getInt("ayah")
                    val start = row.getLong("start_time")
                    val end = row.getLong("end_time")
                    require(ayah == index + 1 && start >= 0 && end > start) { "Invalid timing row" }
                    Timing(ayah, start, end)
                }
                require(rows.zipWithNext().all { (a, b) -> b.start >= a.start }) { "Out-of-order timings" }
                main.post {
                    if (closed || requestId != generation) return@post
                    timings = rows
                    status.text = "التوقيتات جاهزة — تشغيل الصوت"
                    player.setMediaItem(MediaItem.fromUri("$BASE/${name(surah)}.mp3"))
                    player.prepare()
                    player.play()
                }
            } catch (error: Exception) {
                main.post {
                    if (!closed && requestId == generation) status.text = "تعذّر التحميل: ${error.message}"
                }
            }
        }
    }

    override fun onDestroy() {
        closed = true
        generation++
        main.removeCallbacks(ticker)
        player.release()
        executor.shutdownNow()
        super.onDestroy()
    }
}
