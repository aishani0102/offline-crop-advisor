package app.cropadvisor

import android.graphics.Bitmap
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp



// Each language is shown in its own script, so the picker reads the same in any language.
val LANGUAGE_NAMES = mapOf(
    "en" to "English", "hi" to "हिन्दी", "bn" to "বাংলা", "mr" to "मराठी", "ta" to "தமிழ்", "te" to "తెలుగు",
)

// What the result card shows. Probabilities are over the chosen crop only.
// sevPct and band come from Severity.kt, only for disease and pest labels.
data class Diagnosis(
    val crop: String, val ranked: List<Pair<String, Float>>, val ms: Long,
    val sevPct: Double? = null, val band: String? = null,
    val quality: String = "ok",   // photo quality gate: ok, too_dark, too_blurry, no_leaf
) {
    val label get() = ranked[0].first
    val confidence get() = ranked[0].second
    val uncertain get() = confidence < UNCERTAIN_BELOW || quality != "ok"

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



@Composable
fun Header(subtitle: String) {
    Column(
        Modifier.fillMaxWidth().background(P.header).statusBarsPadding().padding(horizontal = 24.dp, vertical = 28.dp),
    ) {
        Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
            Text(
                stringResource(R.string.app_name), color = P.headerText, fontSize = 22.sp, fontWeight = FontWeight.SemiBold,
                modifier = Modifier.weight(1f),
            )
            LocalThemeSwitch.current?.let { ThemeSlider(it) }
        }
        Text(subtitle, color = P.headerText.copy(alpha = 0.85f), fontSize = 13.sp)
    }
}

@Composable
fun PrimaryButton(text: String, modifier: Modifier = Modifier, enabled: Boolean = true, onClick: () -> Unit) {
    Button(
        onClick = onClick, enabled = enabled, shape = RectangleShape, modifier = modifier.heightIn(min = 52.dp),
        colors = ButtonDefaults.buttonColors(containerColor = P.accent, contentColor = P.onAccent),
    ) { Text(text, fontWeight = FontWeight.SemiBold, textAlign = androidx.compose.ui.text.style.TextAlign.Center) }
}

@Composable
fun SecondaryButton(text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick, shape = RectangleShape, modifier = modifier.heightIn(min = 52.dp),
        border = BorderStroke(1.dp, P.outline),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = P.outlineText),
    ) { Text(text, textAlign = androidx.compose.ui.text.style.TextAlign.Center) }
}

@Composable
fun CropToggle(label: String, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    if (selected) PrimaryButton(label, modifier, onClick = onClick)
    else SecondaryButton(label, modifier, onClick = onClick)
}

@Composable
fun HomeScreen(
    crop: String, busy: Boolean, officer: String, lang: String, error: String, onLang: (String) -> Unit, onOfficer: (String) -> Unit,
    state: String, onState: (String) -> Unit,
    onCrop: (String) -> Unit, onCamera: () -> Unit, onGallery: () -> Unit,
) {
    Column(Modifier.fillMaxSize().background(P.bg).verticalScroll(rememberScrollState())) {
        Header(stringResource(R.string.subtitle))
        Column(Modifier.navigationBarsPadding().padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(stringResource(R.string.language), color = P.muted, fontSize = 13.sp)
            LANGUAGES.chunked(3).forEach { row ->
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    row.forEach { l -> CropToggle(LANGUAGE_NAMES.getValue(l), l == lang, Modifier.weight(1f)) { onLang(l) } }
                }
            }
            Spacer(Modifier.height(12.dp))
            Text(stringResource(R.string.crop), color = P.muted, fontSize = 13.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                CropToggle(stringResource(R.string.tomato), crop == "tomato", Modifier.weight(1f)) { onCrop("tomato") }
                CropToggle(stringResource(R.string.potato), crop == "potato", Modifier.weight(1f)) { onCrop("potato") }
            }
            Spacer(Modifier.height(12.dp))
            Text(stringResource(R.string.photo_hint), color = P.muted, fontSize = 13.sp)
            if (error.isNotEmpty()) Text(error, color = P.ink, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
            PrimaryButton(stringResource(if (busy) R.string.checking else R.string.take_photo), Modifier.fillMaxWidth(), enabled = !busy, onClick = onCamera)
            SecondaryButton(stringResource(R.string.gallery), Modifier.fillMaxWidth(), onClick = onGallery)
            Spacer(Modifier.height(12.dp))
            Text(stringResource(R.string.state), color = P.muted, fontSize = 13.sp)
            StatePicker(state, onState)
            Spacer(Modifier.height(4.dp))
            Text(stringResource(R.string.officer), color = P.muted, fontSize = 13.sp)
            androidx.compose.material3.OutlinedTextField(
                officer, onOfficer, singleLine = true, shape = RectangleShape, modifier = Modifier.fillMaxWidth(),
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                    keyboardType = androidx.compose.ui.text.input.KeyboardType.Phone,
                ),
                colors = androidx.compose.material3.OutlinedTextFieldDefaults.colors(
                    focusedTextColor = P.ink, unfocusedTextColor = P.ink,
                    focusedBorderColor = P.accent, unfocusedBorderColor = P.surfaceBorder, cursorColor = P.accent,
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
    Column(Modifier.fillMaxSize().background(P.bg).verticalScroll(scroll)) {
        Header(stringResource(if (d.crop == "potato") R.string.potato else R.string.tomato))
        Image(
            photo.asImageBitmap(), null, contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxWidth().aspectRatio(1.6f),
        )
        Column(Modifier.navigationBarsPadding().padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            if (d.uncertain) {
                Text(stringResource(R.string.not_sure), color = P.ink, fontSize = 26.sp, fontWeight = FontWeight.SemiBold)
                Text(
                    stringResource(
                        when (d.quality) {
                            "too_dark" -> R.string.q_too_dark
                            "too_blurry" -> R.string.q_too_blurry
                            "no_leaf" -> R.string.no_leaf_retake
                            else -> R.string.not_sure_body
                        },
                    ),
                    color = P.muted, fontSize = 14.sp,
                )
            } else {
                Text(condName(d.label), color = P.ink, fontSize = 26.sp, fontWeight = FontWeight.SemiBold)
                Text(stringResource(R.string.confidence, (d.confidence * 100).toInt()), color = P.accentText, fontSize = 14.sp)
                when (d.band) {
                    "mild", "moderate", "severe" -> Text(
                        stringResource(R.string.spread, stringResource(bandRes(d.band))),
                        color = P.ink, fontSize = 14.sp,
                    )
                    "no_leaf" -> Text(stringResource(R.string.no_leaf), color = P.muted, fontSize = 14.sp)
                }
            }
            Spacer(Modifier.height(4.dp))
            // No match list for a photo the quality gate rejected (dark, blurry, no leaf).
            if (d.quality == "ok") {
                Text(stringResource(R.string.top_matches), color = P.muted, fontSize = 13.sp)
                d.ranked.take(3).forEach { (label, p) -> ScoreBar(condName(label), p) }
            }
            Text(stringResource(R.string.checked_ms, d.ms.toInt()), color = P.muted, fontSize = 12.sp)
            if (advice.isNotEmpty()) {
                Spacer(Modifier.height(4.dp))
                Box(Modifier.fillMaxWidth().background(P.surface).border(1.dp, P.surfaceBorder).padding(16.dp)) {
                    Text(advice, color = P.ink, fontSize = 15.sp, lineHeight = 22.sp)
                }
                Text(adviceNote, color = P.muted, fontSize = 12.sp)
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
            Text(name, color = P.ink, fontSize = 14.sp, modifier = Modifier.weight(1f))
            Text("${(p * 100).toInt()}%", color = P.ink, fontSize = 14.sp)
        }
        Box(Modifier.fillMaxWidth().height(4.dp).background(P.track)) {
            Box(Modifier.fillMaxWidth(p.coerceIn(0.01f, 1f)).height(4.dp).background(P.barFill))
        }
    }
}

// One row of square options. Tapping the chosen one again clears it.
@Composable
fun OptionRow(options: List<Pair<String, Int>>, chosen: String?, onPick: (String?) -> Unit) {
    // same height for every option in the row, even when one label wraps
    Row(Modifier.height(androidx.compose.foundation.layout.IntrinsicSize.Min), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        options.forEach { (key, label) ->
            CropToggle(stringResource(label), key == chosen, Modifier.weight(1f).fillMaxHeight()) { onPick(if (key == chosen) null else key) }
        }
    }
}

// Asked after a confident disease or pest result. Every question can be left
// blank, and Skip goes straight to the advice.
@Composable
fun QuestionsScreen(crop: String, onDone: (rain: String?, stage: String?, sprayed: String?) -> Unit) {
    var rain by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf<String?>(null) }
    var stage by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf<String?>(null) }
    var sprayed by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf<String?>(null) }
    Column(Modifier.fillMaxSize().background(P.bg).verticalScroll(rememberScrollState())) {
        Header(stringResource(if (crop == "potato") R.string.potato else R.string.tomato))
        Column(Modifier.navigationBarsPadding().padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(stringResource(R.string.q_intro), color = P.ink, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(4.dp))
            Text(stringResource(R.string.q_rain), color = P.muted, fontSize = 14.sp)
            OptionRow(listOf("yes" to R.string.ans_yes, "no" to R.string.ans_no, "unsure" to R.string.ans_unsure), rain) { rain = it }
            Spacer(Modifier.height(4.dp))
            Text(stringResource(R.string.q_stage), color = P.muted, fontSize = 14.sp)
            OptionRow(listOf("seedling" to R.string.stage_seedling, "growing" to R.string.stage_growing), stage) { stage = it }
            OptionRow(listOf("flowering" to R.string.stage_flowering, "harvest" to R.string.stage_harvest), stage) { stage = it }
            Spacer(Modifier.height(4.dp))
            Text(stringResource(R.string.q_sprayed), color = P.muted, fontSize = 14.sp)
            OptionRow(listOf("yes" to R.string.ans_yes, "no" to R.string.ans_no), sprayed) { sprayed = it }
            Spacer(Modifier.height(12.dp))
            PrimaryButton(stringResource(R.string.show_advice), Modifier.fillMaxWidth()) { onDone(rain, stage, sprayed) }
            SecondaryButton(stringResource(R.string.skip), Modifier.fillMaxWidth()) { onDone(null, null, null) }
        }
    }
}

val STATES = listOf(
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Goa", "Gujarat",
    "Haryana", "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand", "Karnataka", "Kerala", "Ladakh",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Puducherry",
    "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal",
)

@Composable
fun StatePicker(state: String, onState: (String) -> Unit) {
    var open by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf(false) }
    Box {
        SecondaryButton(state.ifEmpty { stringResource(R.string.choose_state) }, Modifier.fillMaxWidth()) { open = true }
        androidx.compose.material3.DropdownMenu(
            open, { open = false }, shape = RectangleShape, containerColor = P.surface,
            modifier = Modifier.height(360.dp),
        ) {
            STATES.forEach { s ->
                androidx.compose.material3.DropdownMenuItem({ Text(s, color = P.ink) }, { onState(s); open = false })
            }
        }
    }
}