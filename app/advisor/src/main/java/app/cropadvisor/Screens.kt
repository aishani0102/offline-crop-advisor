package app.cropadvisor

import android.graphics.Bitmap
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

val Muted = Color(0xFF9A9A9A)

// Each language is shown in its own script, so the picker reads the same in any language.
val LANGUAGE_NAMES = mapOf(
    "en" to "English", "hi" to "हिन्दी", "bn" to "বাংলা", "mr" to "मराठी", "ta" to "தமிழ்", "te" to "తెలుగు",
)

// What the result card shows. Probabilities are over the chosen crop only.
// sevPct and band come from Severity.kt, only for disease and pest labels.
data class Diagnosis(
    val crop: String, val ranked: List<Pair<String, Float>>, val ms: Long,
    val sevPct: Double? = null, val band: String? = null,
) {
    val label get() = ranked[0].first
    val confidence get() = ranked[0].second
    val uncertain get() = confidence < UNCERTAIN_BELOW

    companion object {
        const val UNCERTAIN_BELOW = 0.6f

        fun from(crop: String, r: Vision.Result): Diagnosis {
            val idx = Vision.LABELS.indices.filter { Vision.LABELS[it].startsWith(crop + "_") }
            val sum = idx.sumOf { r.probs[it].toDouble() }.toFloat()
            val ranked = idx.map { Vision.LABELS[it] to r.probs[it] / sum }.sortedByDescending { it.second }
            return Diagnosis(crop, ranked, r.ms)
        }
    }
}

// Condition name in the chosen language, from the cond_* string resources.
@Composable
fun condName(label: String): String {
    val ctx = LocalContext.current
    return stringResource(ctx.resources.getIdentifier("cond_" + label.substringAfter('_'), "string", ctx.packageName))
}

fun bandRes(band: String) = when (band) {
    "mild" -> R.string.band_mild
    "moderate" -> R.string.band_moderate
    else -> R.string.band_severe
}

// English name for the SMS and the safety check: "tomato_septoria_leaf_spot" -> "Septoria leaf spot"
fun conditionName(label: String): String {
    val rest = label.substringAfter('_').replace('_', ' ')
    return when (rest) {
        "healthy" -> "Healthy"
        "yellow leaf curl virus" -> "Yellow leaf curl virus"
        "septoria leaf spot" -> "Septoria leaf spot"
        else -> rest.replaceFirstChar { it.uppercase() }
    }
}

private val headerBrush = Brush.linearGradient(listOf(Black, Charcoal, Green))

@Composable
fun Header(subtitle: String) {
    Column(
        Modifier.fillMaxWidth().background(headerBrush).statusBarsPadding().padding(horizontal = 24.dp, vertical = 28.dp),
    ) {
        Text(stringResource(R.string.app_name), color = Color.White, fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
        Text(subtitle, color = Color.White.copy(alpha = 0.75f), fontSize = 13.sp)
    }
}

@Composable
fun PrimaryButton(text: String, modifier: Modifier = Modifier, enabled: Boolean = true, onClick: () -> Unit) {
    Button(
        onClick = onClick, enabled = enabled, shape = RectangleShape, modifier = modifier.height(52.dp),
        colors = ButtonDefaults.buttonColors(containerColor = Green, contentColor = Black),
    ) { Text(text, fontWeight = FontWeight.SemiBold) }
}

@Composable
fun SecondaryButton(text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick, shape = RectangleShape, modifier = modifier.height(52.dp),
        border = BorderStroke(1.dp, Green),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = Green),
    ) { Text(text) }
}

@Composable
fun CropToggle(label: String, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    if (selected) PrimaryButton(label, modifier, onClick = onClick)
    else SecondaryButton(label, modifier, onClick = onClick)
}

@Composable
fun HomeScreen(
    crop: String, busy: Boolean, officer: String, lang: String, onLang: (String) -> Unit, onOfficer: (String) -> Unit,
    onCrop: (String) -> Unit, onCamera: () -> Unit, onGallery: () -> Unit,
) {
    Column(Modifier.fillMaxSize().background(Black)) {
        Header(stringResource(R.string.subtitle))
        Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(stringResource(R.string.language), color = Muted, fontSize = 13.sp)
            LANGUAGES.chunked(3).forEach { row ->
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    row.forEach { l -> CropToggle(LANGUAGE_NAMES.getValue(l), l == lang, Modifier.weight(1f)) { onLang(l) } }
                }
            }
            Spacer(Modifier.height(12.dp))
            Text(stringResource(R.string.crop), color = Muted, fontSize = 13.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                CropToggle(stringResource(R.string.tomato), crop == "tomato", Modifier.weight(1f)) { onCrop("tomato") }
                CropToggle(stringResource(R.string.potato), crop == "potato", Modifier.weight(1f)) { onCrop("potato") }
            }
            Spacer(Modifier.height(12.dp))
            Text(stringResource(R.string.photo_hint), color = Muted, fontSize = 13.sp)
            PrimaryButton(stringResource(if (busy) R.string.checking else R.string.take_photo), Modifier.fillMaxWidth(), enabled = !busy, onClick = onCamera)
            SecondaryButton(stringResource(R.string.gallery), Modifier.fillMaxWidth(), onClick = onGallery)
            Spacer(Modifier.height(12.dp))
            Text(stringResource(R.string.officer), color = Muted, fontSize = 13.sp)
            androidx.compose.material3.OutlinedTextField(
                officer, onOfficer, singleLine = true, shape = RectangleShape, modifier = Modifier.fillMaxWidth(),
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                    keyboardType = androidx.compose.ui.text.input.KeyboardType.Phone,
                ),
                colors = androidx.compose.material3.OutlinedTextFieldDefaults.colors(
                    focusedTextColor = Color.White, unfocusedTextColor = Color.White,
                    focusedBorderColor = Green, unfocusedBorderColor = Charcoal, cursorColor = Green,
                ),
            )
        }
    }
}

@Composable
fun ResultScreen(
    photo: Bitmap, d: Diagnosis, advice: String, adviceNote: String, onSms: (() -> Unit)?, onAgain: () -> Unit,
    scrollDown: Boolean = false,
) {
    val scroll = rememberScrollState()
    // debug only: jump to the advice so a screenshot can show it
    if (scrollDown) androidx.compose.runtime.LaunchedEffect(advice, scroll.maxValue) { scroll.scrollTo(scroll.maxValue) }
    Column(Modifier.fillMaxSize().background(Black).verticalScroll(scroll)) {
        Header(stringResource(if (d.crop == "potato") R.string.potato else R.string.tomato))
        Image(
            photo.asImageBitmap(), null, contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxWidth().aspectRatio(1.6f),
        )
        Column(Modifier.navigationBarsPadding().padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            if (d.uncertain) {
                Text(stringResource(R.string.not_sure), color = Color.White, fontSize = 26.sp, fontWeight = FontWeight.SemiBold)
                Text(
                    stringResource(R.string.not_sure_body),
                    color = Muted, fontSize = 14.sp,
                )
            } else {
                Text(condName(d.label), color = Color.White, fontSize = 26.sp, fontWeight = FontWeight.SemiBold)
                Text(stringResource(R.string.confidence, (d.confidence * 100).toInt()), color = Green, fontSize = 14.sp)
                when (d.band) {
                    "mild", "moderate", "severe" -> Text(
                        stringResource(R.string.spread, stringResource(bandRes(d.band))),
                        color = Color.White, fontSize = 14.sp,
                    )
                    "no_leaf" -> Text(stringResource(R.string.no_leaf), color = Muted, fontSize = 14.sp)
                }
            }
            Spacer(Modifier.height(4.dp))
            Text(stringResource(R.string.top_matches), color = Muted, fontSize = 13.sp)
            d.ranked.take(3).forEach { (label, p) -> ScoreBar(condName(label), p) }
            Text(stringResource(R.string.checked_ms, d.ms.toInt()), color = Muted, fontSize = 12.sp)
            if (advice.isNotEmpty()) {
                Spacer(Modifier.height(4.dp))
                Box(Modifier.fillMaxWidth().background(Charcoal).padding(16.dp)) {
                    Text(advice, color = Color.White, fontSize = 15.sp, lineHeight = 22.sp)
                }
                Text(adviceNote, color = Muted, fontSize = 12.sp)
            }
            Spacer(Modifier.height(8.dp))
            if (onSms != null) SecondaryButton(stringResource(R.string.send_officer), Modifier.fillMaxWidth(), onClick = onSms)
            PrimaryButton(stringResource(R.string.check_another), Modifier.fillMaxWidth(), onClick = onAgain)
        }
    }
}

@Composable
fun ScoreBar(name: String, p: Float) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row {
            Text(name, color = Color.White, fontSize = 14.sp, modifier = Modifier.weight(1f))
            Text("${(p * 100).toInt()}%", color = Color.White, fontSize = 14.sp)
        }
        Box(Modifier.fillMaxWidth().height(4.dp).background(Charcoal)) {
            Box(Modifier.fillMaxWidth(p.coerceIn(0.01f, 1f)).height(4.dp).background(Green))
        }
    }
}
