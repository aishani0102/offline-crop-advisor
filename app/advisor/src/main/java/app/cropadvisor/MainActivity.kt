package app.cropadvisor

import android.graphics.Bitmap
import android.graphics.ImageDecoder
import android.net.Uri
import android.os.Bundle
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.FileProvider
import java.io.File
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
        officer = getSharedPreferences("settings", MODE_PRIVATE).getString("officer", "") ?: ""
        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(primary = Green, background = Black, surface = Charcoal),
                shapes = SquareShapes,
            ) {
                val camera = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
                    if (ok) photoUri?.let { classifyUri(it) }
                }
                val gallery = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
                    uri?.let { classifyUri(it) }
                }
                val d = diagnosis
                val p = photo
                if (d != null && p != null) {
                    BackHandler { diagnosis = null }
                    val c = case
                    ResultScreen(p, d, advice, adviceNote, if (c?.needsReferral == true) ({ sendSms(c) }) else null) {
                        diagnosis = null
                    }
                } else {
                    HomeScreen(
                        crop, busy, officer,
                        onOfficer = {
                            officer = it.filter { ch -> ch.isDigit() || ch == '+' }
                            getSharedPreferences("settings", MODE_PRIVATE).edit().putString("officer", officer).apply()
                        },
                        onCrop = { crop = it },
                        onCamera = { photoUri = newPhotoUri(); camera.launch(photoUri!!) },
                        onGallery = {
                            gallery.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                        },
                    )
                }
            }
        }
        // only on a fresh start, so a recreated activity does not run the test again
        if (savedInstanceState == null) {
            // debug: classify a file from the app folder without tapping, for screenshots
            intent.getStringExtra("classify")?.let { name ->
                intent.getStringExtra("crop")?.let { crop = it }
                classifyUri(android.net.Uri.fromFile(java.io.File(getExternalFilesDir(null), name)))
            }
            if (intent.getBooleanExtra("llmtest", false)) runLlmTest()
            if (intent.getBooleanExtra("visiontest", false)) runVisionTest()
        }
    }

    private var crop by mutableStateOf("tomato")
    private var photo by mutableStateOf<Bitmap?>(null)
    private var diagnosis by mutableStateOf<Diagnosis?>(null)
    private var photoUri: Uri? = null
    private var vision: Vision? = null

    private var officer by mutableStateOf("")
    private var case by mutableStateOf<Case?>(null)
    private var advice by mutableStateOf("")
    private var adviceNote by mutableStateOf("")
    private val advisor by lazy { Advisor(this) }
    private var llm: Llm? = null

    // Shows the template text at once, then tries the language model in the
    // background and swaps its text in only if it passes the safety check.
    // Called from the classify thread.
    private fun startAdvice(d: Diagnosis) {
        val c = Case.from(d)
        val tmpl = advisor.template(c)
        runOnUiThread { case = c; advice = tmpl; adviceNote = "From the crop guide" }
        if (c.uncertain) return
        val mem = android.app.ActivityManager.MemoryInfo()
        (getSystemService(ACTIVITY_SERVICE) as android.app.ActivityManager).getMemoryInfo(mem)
        val freeMb = mem.availMem / (1024 * 1024)
        val pte = ModelFiles.find(this, "llama.pte")
        val tok = ModelFiles.find(this, "tokenizer.model")
        if (freeMb < Advisor.LLAMA_NEEDS_MB || pte == null || tok == null) {
            Perf.log(this, "advice mode=template free_mb=$freeMb model=${pte != null}")
            return
        }
        runOnUiThread { adviceNote = "From the crop guide, writing simpler advice on the phone" }
        try {
            val m = llm ?: Llm(pte, tok).also { llm = it; it.load() }
            val (sys, user) = advisor.prompt(c)
            val r = m.generate(m.chatPrompt(sys, user), 768)
            val text = advisor.cleanOutput(r.text)
            val truncated = !text.trimEnd().let { it.endsWith(".") || it.endsWith("!") || it.endsWith("?") || it.endsWith("।") }
            val fails = advisor.check(text, c, truncated)
            Perf.log(this, "advice mode=llm free_mb=$freeMb load_ms=${m.loadMs} ttft_ms=${r.ttftMs} total_ms=${r.totalMs} tokens=${r.tokens} peak_rss_mb=${Perf.peakRssMb()} fails=$fails")
            if (diagnosis !== d) return
            runOnUiThread {
                if (fails.isEmpty()) { advice = text; adviceNote = "Written on this phone from the crop guide" }
                else adviceNote = "From the crop guide"
            }
        } catch (e: Throwable) {
            Perf.log(this, "advice_error=$e")
            runOnUiThread { adviceNote = "From the crop guide" }
        }
    }

    private fun sendSms(c: Case) {
        val number = getSharedPreferences("settings", MODE_PRIVATE).getString("officer", "") ?: ""
        val i = android.content.Intent(android.content.Intent.ACTION_SENDTO, Uri.parse("smsto:$number"))
        i.putExtra("sms_body", advisor.sms(c))
        startActivity(i)
    }

    private fun newPhotoUri(): Uri {
        val dir = File(cacheDir, "photos").apply { mkdirs() }
        return FileProvider.getUriForFile(this, "app.cropadvisor.photos", File(dir, "leaf.jpg"))
    }

    // Decodes the photo upright and runs the leaf model off the main thread.
    private fun classifyUri(uri: Uri) {
        if (busy) return
        busy = true
        val chosen = crop
        thread {
            try {
                val src = ImageDecoder.createSource(contentResolver, uri)
                val bmp = ImageDecoder.decodeBitmap(src) { dec, info, _ ->
                    dec.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
                    // big camera photos are shrunk on decode, the model only needs 256 px
                    val s = minOf(info.size.width, info.size.height)
                    if (s > 1024) dec.setTargetSampleSize(s / 1024)
                }
                val v = vision ?: Vision(ModelFiles.find(this, "vision.pte")!!.path).also { vision = it }
                val d = Diagnosis.from(chosen, v.classify(bmp))
                Perf.log(this, "classify crop=$chosen label=${d.label} conf=${"%.3f".format(d.confidence)} ms=${d.ms}")
                runOnUiThread { photo = bmp; diagnosis = d }
                startAdvice(d)
            } catch (e: Throwable) {
                Perf.log(this, "classify_error=$e")
            } finally {
                runOnUiThread { busy = false }
            }
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
