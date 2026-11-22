package app.cropadvisor

import android.graphics.Bitmap
import kotlin.math.roundToInt

// Photo preparation shared by the leaf model and the quality gate.
object Photo {
    // Shorter side to 256, like load_photo in detection/predict.py. A camera
    // photo is halved step by step first: one big bilinear jump skips most
    // pixels and gives a noisier picture than PIL's resize on the PC.
    var stepShrink = false  // debug switch: true = old step-by-step resize

    fun shortSide256(src: Bitmap): Bitmap {
        var b = src
        while (stepShrink && minOf(b.width, b.height) >= 512) {
            b = Bitmap.createScaledBitmap(b, b.width / 2, b.height / 2, true)
        }
        val s = 256f / minOf(b.width, b.height)
        if (minOf(b.width, b.height) == 256) return b
        return Bitmap.createScaledBitmap(b, (b.width * s).roundToInt(), (b.height * s).roundToInt(), true)
    }
}

// photo_quality from detection/predict.py, on the shorter-side-256 photo.
// Values from configs/thresholds.json (quality_gate).
object Quality {
    const val MIN_BRIGHTNESS = 40.0
    const val MIN_LAPLACIAN_VAR = 15.0
    const val MIN_LEAF_SHARE = 0.05

    // ok, too_dark, too_blurry or no_leaf
    fun check(src: Bitmap): String {
        val bmp = Photo.shortSide256(src)
        val w = bmp.width
        val h = bmp.height
        val n = w * h
        val px = IntArray(n)
        bmp.getPixels(px, 0, w, 0, 0, w, h)
        val r = IntArray(n) { (px[it] shr 16) and 255 }
        val g = IntArray(n) { (px[it] shr 8) and 255 }
        val b = IntArray(n) { px[it] and 255 }
        // cv2.COLOR_BGR2GRAY in fixed point, as OpenCV does it
        val grey = IntArray(n) { (r[it] * 4899 + g[it] * 9617 + b[it] * 1868 + 8192) shr 14 }
        if (grey.average() < MIN_BRIGHTNESS) return "too_dark"
        if (laplacianVar(grey, w, h) < MIN_LAPLACIAN_VAR) return "too_blurry"
        val rb = Severity.blur5(r, w, h)
        val gb = Severity.blur5(g, w, h)
        val bb = Severity.blur5(b, w, h)
        var leafy = 0
        for (i in 0 until n) {
            val hsv = Severity.toHsv(rb[i], gb[i], bb[i])
            val hu = hsv shr 16
            val sa = (hsv shr 8) and 255
            val va = hsv and 255
            if (hu in 10..90 && sa >= 40 && va >= 30) leafy++
        }
        return if (leafy.toDouble() / n < MIN_LEAF_SHARE) "no_leaf" else "ok"
    }

    // cv2.Laplacian(grey, CV_64F) with the default 3x3 kernel (0 1 0 / 1 -4 1 / 0 1 0)
    // and BORDER_REFLECT_101, then the variance over all pixels.
    private fun laplacianVar(g: IntArray, w: Int, h: Int): Double {
        fun at(x: Int, y: Int): Int {
            val xx = if (x < 0) 1 else if (x >= w) w - 2 else x
            val yy = if (y < 0) 1 else if (y >= h) h - 2 else y
            return g[yy * w + xx]
        }
        var sum = 0.0
        var sq = 0.0
        for (y in 0 until h) for (x in 0 until w) {
            val v = (at(x - 1, y) + at(x + 1, y) + at(x, y - 1) + at(x, y + 1) - 4 * at(x, y)).toDouble()
            sum += v
            sq += v * v
        }
        val n = (w * h).toDouble()
        val mean = sum / n
        return sq / n - mean * mean
    }
}
