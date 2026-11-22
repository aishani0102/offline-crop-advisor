package app.cropadvisor

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathOperation
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import kotlin.math.cos
import kotlin.math.sin

// Light / Dark slider for the banner: sun on the left, moon on the right, the
// thumb slides to the chosen side. The only rounded control in the app (the
// user asked for a pill shape here); everything else stays square.
@Composable
fun ThemeSlider(sw: ThemeSwitch) {
    val cell = 44.dp
    val thumbX by animateDpAsState(if (sw.dark) cell else 0.dp, tween(150), label = "thumb")
    val pill = RoundedCornerShape(50)
    val on = P.sliderIcon
    val idle = P.sliderIdle
    val desc = stringResource(if (sw.dark) R.string.theme_dark else R.string.theme_light)
    // 48 dp tall touch area around the 40 dp track
    Box(
        Modifier.heightIn(min = 48.dp)
            .semantics { contentDescription = desc }
            .toggleable(value = sw.dark, role = Role.Switch) { sw.toggle() },
        contentAlignment = Alignment.Center,
    ) {
        Box(Modifier.size(cell * 2, 40.dp).clip(pill).background(P.sliderTrack)) {
            Box(Modifier.offset(x = thumbX).size(cell, 40.dp).clip(pill).background(P.sliderThumb))
            Row {
                Canvas(Modifier.size(cell, 40.dp)) { drawSun(if (sw.dark) idle else on) }
                Canvas(Modifier.size(cell, 40.dp)) { drawMoon(if (sw.dark) on else idle) }
            }
        }
    }
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawSun(c: Color) {
    val w = 1.5.dp.toPx()
    val r = 4.5.dp.toPx()
    drawCircle(c, r, center, style = Stroke(w))
    for (i in 0 until 8) {
        val a = Math.PI * i / 4
        val d = Offset(cos(a).toFloat(), sin(a).toFloat())
        drawLine(c, center + d * (r + 3.dp.toPx()), center + d * (r + 6.dp.toPx()), w, StrokeCap.Round)
    }
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawMoon(c: Color) {
    val r = 8.dp.toPx()
    val outer = Path().apply { addOval(androidx.compose.ui.geometry.Rect(center, r)) }
    val bite = Path().apply {
        addOval(androidx.compose.ui.geometry.Rect(center + Offset(r * 0.55f, -r * 0.35f), r * 0.85f))
    }
    drawPath(Path().apply { op(outer, bite, PathOperation.Difference) }, c, style = Stroke(1.5.dp.toPx()))
}
