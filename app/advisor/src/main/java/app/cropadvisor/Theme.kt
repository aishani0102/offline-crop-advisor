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
    val accentText: Color,  // confidence and other highlighted text
    val outline: Color,     // border of outlined buttons
    val outlineText: Color, // text of outlined buttons
    val surface: Color,     // advice box and menus
    val surfaceBorder: Color,
    val track: Color,       // empty part of a score bar, idle text field border
    val barFill: Color,
    val header: Brush,
    val headerText: Color,
    val sliderTrack: Color,  // Light / Dark slider in the banner
    val sliderThumb: Color,
    val sliderIcon: Color,   // icon on the thumb
    val sliderIdle: Color,   // the other icon
    val dark: Boolean,
)

// Dark mode, forest greens only (no #00C896). Contrast on #0A120F:
// #6C7D5E is about 4.2:1, too low for text, so text uses lighter tints of it:
// #8A9A7C (about 6:1) for muted text and #A9B79C (about 9:1) for highlights.
// Primary buttons: #6C7D5E with #0A120F text is also only 4.2:1, so the fill
// is the #8A9A7C tint, which gives about 6:1 with #0A120F text.
private val ChaosBlack = Color(0xFF0A120F)
private val DeepSlate = Color(0xFF12271C)
private val PalmGreen = Color(0xFF253E2D)
private val Catachan = Color(0xFF425940)
private val Emerald = Color(0xFF6C7D5E)
private val EmeraldTint = Color(0xFF8A9A7C)
private val EmeraldLight = Color(0xFFA9B79C)
private val NearWhite = Color(0xFFEDF0E9)

val DarkPalette = Palette(
    bg = ChaosBlack, ink = NearWhite, muted = EmeraldTint, accent = EmeraldTint, onAccent = ChaosBlack,
    accentText = EmeraldLight, outline = Emerald, outlineText = NearWhite,
    surface = DeepSlate, surfaceBorder = PalmGreen, track = PalmGreen, barFill = Emerald,
    header = Brush.linearGradient(listOf(ChaosBlack, PalmGreen, Catachan)), headerText = NearWhite,
    sliderTrack = DeepSlate, sliderThumb = Catachan, sliderIcon = NearWhite,
    sliderIdle = EmeraldTint, dark = true,
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
    accentText = Hunter, outline = Hunter, outlineText = Hunter,
    surface = Paper, surfaceBorder = Sage, track = Sage, barFill = Fern,
    header = Brush.linearGradient(listOf(Forest, Fern, Sage)), headerText = Paper, sliderTrack = Paper, sliderThumb = Sage, sliderIcon = Forest,
    sliderIdle = Hunter, dark = false,
)

val LocalPalette = staticCompositionLocalOf { DarkPalette }

val P: Palette
    @Composable @ReadOnlyComposable get() = LocalPalette.current

// The Light / Dark switch in the banner. null means no switch (for example in tests).
class ThemeSwitch(val dark: Boolean, val toggle: () -> Unit)

val LocalThemeSwitch = staticCompositionLocalOf<ThemeSwitch?> { null }
