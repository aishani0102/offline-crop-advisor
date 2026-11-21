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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

val Muted = Color(0xFF9A9A9A)

// What the result card shows. Probabilities are over the chosen crop only.
data class Diagnosis(val crop: String, val ranked: List<Pair<String, Float>>, val ms: Long) {
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

// "tomato_septoria_leaf_spot" -> "Septoria leaf spot"
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
        Text("Crop Advisor", color = Color.White, fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
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
fun HomeScreen(crop: String, busy: Boolean, onCrop: (String) -> Unit, onCamera: () -> Unit, onGallery: () -> Unit) {
    Column(Modifier.fillMaxSize().background(Black)) {
        Header("Offline leaf check for tomato and potato")
        Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Crop", color = Muted, fontSize = 13.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                CropToggle("Tomato", crop == "tomato", Modifier.weight(1f)) { onCrop("tomato") }
                CropToggle("Potato", crop == "potato", Modifier.weight(1f)) { onCrop("potato") }
            }
            Spacer(Modifier.height(12.dp))
            Text("Photo of one leaf, close up, in daylight", color = Muted, fontSize = 13.sp)
            PrimaryButton(if (busy) "Checking" else "Take photo", Modifier.fillMaxWidth(), enabled = !busy, onClick = onCamera)
            SecondaryButton("Choose from gallery", Modifier.fillMaxWidth(), onClick = onGallery)
        }
    }
}

@Composable
fun ResultScreen(photo: Bitmap, d: Diagnosis, onAgain: () -> Unit) {
    Column(Modifier.fillMaxSize().background(Black).verticalScroll(rememberScrollState())) {
        Header(d.crop.replaceFirstChar { it.uppercase() })
        Image(
            photo.asImageBitmap(), null, contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxWidth().aspectRatio(1.6f),
        )
        Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            if (d.uncertain) {
                Text("Not sure", color = Color.White, fontSize = 26.sp, fontWeight = FontWeight.SemiBold)
                Text(
                    "The photo does not match any condition clearly. Take a closer photo of a single leaf " +
                        "in daylight, or show it to your extension officer.",
                    color = Muted, fontSize = 14.sp,
                )
            } else {
                Text(conditionName(d.label), color = Color.White, fontSize = 26.sp, fontWeight = FontWeight.SemiBold)
                Text("${(d.confidence * 100).toInt()}% confidence", color = Green, fontSize = 14.sp)
            }
            Spacer(Modifier.height(4.dp))
            Text("Top matches", color = Muted, fontSize = 13.sp)
            d.ranked.take(3).forEach { (label, p) -> ScoreBar(conditionName(label), p) }
            Text("Checked on this phone in ${d.ms} ms, no internet used", color = Muted, fontSize = 12.sp)
            Spacer(Modifier.height(8.dp))
            PrimaryButton("Check another leaf", Modifier.fillMaxWidth(), onClick = onAgain)
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
