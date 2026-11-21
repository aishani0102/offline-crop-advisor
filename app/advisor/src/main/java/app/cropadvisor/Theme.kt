package app.cropadvisor

import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

// Colours by role, so the screens do not care which mode is on.
class Palette(
    val bg: Color,          // screen background
    val ink: Color,         // body text
    val muted: Color,       // labels and small notes
    val accent: Color,      // primary buttons, outlines, confidence text
    val onAccent: Color,    // text on a primary button
    val surface: Color,     // advice box and menus
    val surfaceBorder: Color,
    val track: Color,       // empty part of a score bar, idle text field border
    val barFill: Color,
    val header: Brush,
    val headerText: Color,
    val dark: Boolean,
)

val DarkPalette = Palette(
    bg = Black, ink = Color.White, muted = Color(0xFF9A9A9A), accent = Green, onAccent = Black,
    surface = Charcoal, surfaceBorder = Color.Transparent, track = Charcoal, barFill = Green,
    header = Brush.linearGradient(listOf(Black, Charcoal, Green)), headerText = Color.White, dark = true,
)

// Light mode from the user's palette. Contrast on #DAD7CD: body #344E41 about 6.3:1,
// #3A5A40 about 5.4:1, so muted text uses #3A5A40 at full strength. Sage #A3B18A is only
// used for lines and bars, never behind text (4.0:1 with #344E41 is too low).
private val Paper = Color(0xFFDAD7CD)
private val Sage = Color(0xFFA3B18A)
private val Fern = Color(0xFF588157)
private val Hunter = Color(0xFF3A5A40)
private val Forest = Color(0xFF344E41)

val LightPalette = Palette(
    bg = Paper, ink = Forest, muted = Hunter, accent = Hunter, onAccent = Paper,
    surface = Paper, surfaceBorder = Sage, track = Sage, barFill = Fern,
    header = Brush.linearGradient(listOf(Forest, Fern, Sage)), headerText = Paper, dark = false,
)

val LocalPalette = staticCompositionLocalOf { DarkPalette }

val P: Palette
    @Composable @ReadOnlyComposable get() = LocalPalette.current
