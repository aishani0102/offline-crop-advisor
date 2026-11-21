package app.cropadvisor

import android.content.Context
import android.os.SystemClock
import org.pytorch.executorch.extension.llm.LlmCallback
import org.pytorch.executorch.extension.llm.LlmModule
import java.io.File

// Model files are pushed with adb, they are not part of the APK.
// First look in the app's external files dir, then /data/local/tmp/cropadv.
object ModelFiles {
    fun find(ctx: Context, name: String): File? {
        val dirs = listOfNotNull(ctx.getExternalFilesDir(null), File("/data/local/tmp/cropadv"))
        return dirs.map { File(it, name) }.firstOrNull { it.canRead() }
    }
}

class Llm(private val pte: File, private val tokenizer: File) {
    private var module: LlmModule? = null
    var loadMs = 0L
        private set

    fun load() {
        if (module != null) return
        val t0 = SystemClock.elapsedRealtime()
        module = LlmModule(pte.absolutePath, tokenizer.absolutePath, 0.0f).also { it.load() }
        loadMs = SystemClock.elapsedRealtime() - t0
    }

    // Llama 3 chat format, same as the advisory prompt builder on the PC side.
    fun chatPrompt(system: String, user: String): String =
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n$system<|eot_id|>" +
            "<|start_header_id|>user<|end_header_id|>\n\n$user<|eot_id|>" +
            "<|start_header_id|>assistant<|end_header_id|>\n\n"

    class Result(val text: String, val ttftMs: Long, val totalMs: Long, val tokens: Int, val stats: String)

    fun generate(prompt: String, maxLen: Int, onToken: (String) -> Unit = {}): Result {
        load()
        val sb = StringBuilder()
        var first = -1L
        var n = 0
        var stats = ""
        val t0 = SystemClock.elapsedRealtime()
        module!!.generate(prompt, maxLen, object : LlmCallback {
            override fun onResult(result: String) {
                if (first < 0) first = SystemClock.elapsedRealtime() - t0
                n++
                sb.append(result)
                onToken(result)
            }
            override fun onStats(s: String) { stats = s }
        }, false)
        return Result(sb.toString(), first, SystemClock.elapsedRealtime() - t0, n, stats)
    }

    fun close() {
        module?.resetNative()
        module = null
    }
}

object Perf {
    // Peak resident memory of this process in MB, from /proc/self/status (VmHWM).
    fun peakRssMb(): Long {
        val line = File("/proc/self/status").readLines().firstOrNull { it.startsWith("VmHWM") } ?: return -1
        return line.filter { it.isDigit() }.toLong() / 1024
    }

    fun log(ctx: Context, line: String) {
        val f = File(ctx.getExternalFilesDir(null), "timings.log")
        f.appendText("${System.currentTimeMillis()} $line\n")
        android.util.Log.i("CropAdvisor", line)
    }
}
