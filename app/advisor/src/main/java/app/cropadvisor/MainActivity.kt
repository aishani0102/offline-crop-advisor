package app.cropadvisor

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import kotlin.concurrent.thread

val Black = Color(0xFF040404)
val Charcoal = Color(0xFF1F1F1F)
val Green = Color(0xFF00C896)

// Square corners everywhere.
private val square = RectangleShape
// Theme shapes need a corner based shape, so use zero radius corners there.
private val zero = RoundedCornerShape(0.dp)
val SquareShapes = Shapes(zero, zero, zero, zero, zero)

class MainActivity : ComponentActivity() {
    private var out by mutableStateOf("")
    private var busy by mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(primary = Green, background = Black, surface = Charcoal),
                shapes = SquareShapes,
            ) {
                Column(
                    Modifier.fillMaxSize().background(Black).padding(24.dp).verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    Button(
                        onClick = { runLlmTest() },
                        enabled = !busy,
                        shape = square,
                        colors = ButtonDefaults.buttonColors(containerColor = Green, contentColor = Black),
                    ) { Text("Run language model test") }
                    Text(out, color = Color.White)
                }
            }
        }
        // only on a fresh start, so a recreated activity does not run the test again
        if (savedInstanceState == null) {
            if (intent.getBooleanExtra("llmtest", false)) runLlmTest()
            if (intent.getBooleanExtra("visiontest", false)) runVisionTest()
        }
    }

    // Classifies every test_*.jpg in the app's files folder and logs top 3.
    private fun runVisionTest() {
        thread {
            try {
                val dir = getExternalFilesDir(null)!!
                val pte = ModelFiles.find(this, "vision.pte") ?: error("vision.pte not found")
                val t0 = System.currentTimeMillis()
                val vision = Vision(pte.path)
                Perf.log(this, "vision_load_ms=${System.currentTimeMillis() - t0}")
                val images = dir.listFiles { f -> f.name.startsWith("test_") && f.name.endsWith(".jpg") }!!.sorted()
                for (f in images) {
                    val bmp = android.graphics.BitmapFactory.decodeFile(f.path)
                    vision.classify(bmp) // warm up
                    val r = vision.classify(bmp)
                    val top = r.top(3).joinToString(" ") { "${Vision.LABELS[it]}:${"%.3f".format(r.probs[it])}" }
                    Perf.log(this, "vision ${f.name} ms=${r.ms} top3=$top")
                }
                Perf.log(this, "vision_done peak_rss_mb=${Perf.peakRssMb()}")
                vision.close()
            } catch (e: Throwable) {
                Perf.log(this, "vision_error=$e")
            }
        }
    }

    private fun runLlmTest() {
        if (busy) return
        busy = true
        out = "Loading model"
        thread {
            try {
                val pte = ModelFiles.find(this, "llama.pte") ?: error("llama.pte not found")
                val tok = ModelFiles.find(this, "tokenizer.model") ?: error("tokenizer.model not found")
                val llm = Llm(pte, tok)
                llm.load()
                Perf.log(this, "llm_load_ms=${llm.loadMs} rss_mb=${Perf.peakRssMb()}")
                val prompt = llm.chatPrompt(
                    "You are a farm advisor. Answer in two short sentences.",
                    "How do I stop early blight spreading on my tomato plants?",
                )
                val sb = StringBuilder()
                val r = llm.generate(prompt, 256) { tok -> sb.append(tok); runOnUiThread { out = sb.toString() } }
                val secs = (r.totalMs - r.ttftMs).coerceAtLeast(1) / 1000.0
                val line = "llm ttft_ms=${r.ttftMs} total_ms=${r.totalMs} tokens=${r.tokens} " +
                    "tok_per_s=${"%.2f".format((r.tokens - 1) / secs)} peak_rss_mb=${Perf.peakRssMb()} stats=${r.stats}"
                Perf.log(this, line)
                Perf.log(this, "llm_text=" + r.text.replace("\n", " "))
                llm.close()
            } catch (e: Throwable) {
                Perf.log(this, "llm_error=$e")
                runOnUiThread { out = "Error: $e" }
            } finally {
                runOnUiThread { busy = false }
            }
        }
    }
}
