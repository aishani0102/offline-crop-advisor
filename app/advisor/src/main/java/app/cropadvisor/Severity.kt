package app.cropadvisor

import android.graphics.Bitmap
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sqrt

/**
 * Port of detection/severity.py (colour threshold method, no model).
 *
 * Steps, same order as segment() in severity.py:
 * 1. shrink so the longer side is at most 512
 * 2. 5x5 Gaussian blur, then RGB to HSV on OpenCV's scale (H 0..179, S and V 0..255)
 * 3. healthy = green (H 38..85, S >= 30, V >= 40)
 *    leafy   = H 10..90, S >= 40, V >= 30, or healthy
 * 4. leaf = close(healthy, 31x31 ellipse, 2 times), fill holes, drop parts under 1% of the
 *    image, keep only what is near leafy colour, open with a 5x5 ellipse
 * 5. lesion = leaf and not healthy, open with a 3x3 ellipse
 * 6. severity_pct = lesion pixels / leaf pixels * 100
 *
 * Integer maths copies OpenCV (blur kernel, HSV tables, ellipse shape) so the numbers match
 * the Python version. Check with severity_golden.json, see README.md.
 */
data class SeverityResult(
    val severityPct: Double?,   // null when no leaf was found
    val band: String,           // mild, moderate, severe or no_leaf
    val leafFraction: Double,   // share of the photo that is leaf
)

object Severity {
    const val WORK_SIZE = 512

    // PARAMS in detection/severity.py
    private const val H_LO = 38
    private const val H_HI = 85
    private const val S_MIN = 30
    private const val V_MIN = 40
    private const val CLOSE_K = 31

    // configs/thresholds.json: severity_bands_pct and quality_gate.min_leaf_share
    var mildBelowPct = 10.0
    var severeFromPct = 30.0
    var minLeafShare = 0.05

    fun estimate(photo: Bitmap): SeverityResult {
        val s = WORK_SIZE.toDouble() / max(photo.width, photo.height)
        val bmp = if (s < 1.0) {
            Bitmap.createScaledBitmap(
                photo, (photo.width * s).roundToInt(), (photo.height * s).roundToInt(), true)
        } else photo
        val w = bmp.width
        val h = bmp.height
        val px = IntArray(w * h)
        bmp.getPixels(px, 0, w, 0, 0, w, h)
        return estimate(px, w, h)
    }

    /** argb: packed pixels like Bitmap.getPixels gives, already at most 512 on the long side. */
    fun estimate(argb: IntArray, w: Int, h: Int): SeverityResult {
        val n = w * h
        val r = IntArray(n) { (argb[it] shr 16) and 255 }
        val g = IntArray(n) { (argb[it] shr 8) and 255 }
        val b = IntArray(n) { argb[it] and 255 }
        val rb = blur5(r, w, h)
        val gb = blur5(g, w, h)
        val bb = blur5(b, w, h)

        val healthy = BooleanArray(n)
        val leafy = BooleanArray(n)
        var leafyOnly = 0  // leafy colour without the healthy part, as the quality gate counts it
        for (i in 0 until n) {
            val hsv = toHsv(rb[i], gb[i], bb[i])
            val hu = hsv shr 16
            val sa = (hsv shr 8) and 255
            val va = hsv and 255
            healthy[i] = hu in H_LO..H_HI && sa >= S_MIN && va >= V_MIN
            val l = hu in 10..90 && sa >= 40 && va >= 30
            if (l) leafyOnly++
            leafy[i] = l || healthy[i]
        }
        if (leafyOnly.toDouble() / n < minLeafShare) {
            return SeverityResult(null, "no_leaf", 0.0)
        }

        val big = ellipse(CLOSE_K)
        var leaf = dilate(dilate(healthy, w, h, big), w, h, big)
        leaf = erode(erode(leaf, w, h, big), w, h, big)
        leaf = fillHoles(leaf, w, h)
        if (leaf.any { it }) {
            val near = dilate(leafy, w, h, big)
            for (i in 0 until n) leaf[i] = leaf[i] && near[i]
        }
        val k5 = ellipse(5)
        leaf = dilate(erode(leaf, w, h, k5), w, h, k5)

        var lesion = BooleanArray(n) { leaf[it] && !healthy[it] }
        val k3 = ellipse(3)
        lesion = dilate(erode(lesion, w, h, k3), w, h, k3)

        val leafPx = leaf.count { it }
        if (leafPx == 0) return SeverityResult(null, "no_leaf", 0.0)
        val pct = 100.0 * lesion.count { it } / leafPx
        val band = when {
            pct < mildBelowPct -> "mild"
            pct < severeFromPct -> "moderate"
            else -> "severe"
        }
        return SeverityResult(Math.round(pct * 10) / 10.0, band, leafPx.toDouble() / n)
    }

    // cv2.GaussianBlur(img, (5, 5), 0): kernel 1 4 6 4 1 / 16 each way, border reflect 101
    internal fun blur5(src: IntArray, w: Int, h: Int): IntArray {
        val k = intArrayOf(1, 4, 6, 4, 1)
        val tmp = IntArray(w * h)
        val out = IntArray(w * h)
        for (y in 0 until h) for (x in 0 until w) {
            var s = 0
            for (j in -2..2) s += k[j + 2] * src[y * w + reflect(x + j, w)]
            tmp[y * w + x] = s
        }
        for (y in 0 until h) for (x in 0 until w) {
            var s = 0
            for (j in -2..2) s += k[j + 2] * tmp[reflect(y + j, h) * w + x]
            out[y * w + x] = (s + 128) shr 8
        }
        return out
    }

    private fun reflect(i: Int, n: Int): Int {
        if (n == 1) return 0
        var p = i
        while (p < 0 || p >= n) p = if (p < 0) -p else 2 * n - 2 - p
        return p
    }

    private val sdiv = IntArray(256) { if (it == 0) 0 else Math.rint((255 shl 12) / it.toDouble()).toInt() }
    private val hdiv = IntArray(256) { if (it == 0) 0 else Math.rint((180 shl 12) / (6.0 * it)).toInt() }

    // cv2.COLOR_BGR2HSV for 8 bit images. Returns h shl 16 or s shl 8 or v.
    internal fun toHsv(r: Int, g: Int, b: Int): Int {
        val v = max(r, max(g, b))
        val diff = v - min(r, min(g, b))
        val s = (diff * sdiv[v] + (1 shl 11)) shr 12
        var hh = when (v) {
            r -> g - b
            g -> b - r + 2 * diff
            else -> r - g + 4 * diff
        }
        hh = (hh * hdiv[diff] + (1 shl 11)) shr 12
        if (hh < 0) hh += 180
        return (hh shl 16) or (s shl 8) or v
    }

    // cv2.getStructuringElement(MORPH_ELLIPSE, (k, k)) as a list of (dy, dxFrom, dxTo) rows
    private fun ellipse(k: Int): List<IntArray> {
        val rr = k / 2
        val c = k / 2
        val inv = if (rr > 0) 1.0 / (rr * rr) else 0.0
        val rows = ArrayList<IntArray>()
        for (i in 0 until k) {
            val dy = i - rr
            if (abs(dy) > rr) continue
            val dx = Math.rint(c * sqrt((rr * rr - dy * dy) * inv)).toInt()
            val j1 = max(c - dx, 0)
            val j2 = min(c + dx + 1, k)
            if (j2 > j1) rows.add(intArrayOf(dy, j1 - c, j2 - 1 - c))
        }
        return rows
    }

    private fun prefix(m: BooleanArray, w: Int, h: Int): IntArray {
        val p = IntArray(h * (w + 1))
        for (y in 0 until h) for (x in 0 until w) {
            p[y * (w + 1) + x + 1] = p[y * (w + 1) + x] + if (m[y * w + x]) 1 else 0
        }
        return p
    }

    // outside the image never counts, like OpenCV's default border for dilate and erode
    private fun dilate(m: BooleanArray, w: Int, h: Int, k: List<IntArray>): BooleanArray =
        morph(m, w, h, k, true)

    private fun erode(m: BooleanArray, w: Int, h: Int, k: List<IntArray>): BooleanArray =
        morph(m, w, h, k, false)

    private fun morph(m: BooleanArray, w: Int, h: Int, k: List<IntArray>, isDilate: Boolean): BooleanArray {
        val p = prefix(m, w, h)
        val out = BooleanArray(w * h)
        for (y in 0 until h) for (x in 0 until w) {
            var res = !isDilate
            for (row in k) {
                val yy = y + row[0]
                if (yy < 0 || yy >= h) continue
                val x0 = max(x + row[1], 0)
                val x1 = min(x + row[2], w - 1)
                if (x1 < x0) continue
                val cnt = p[yy * (w + 1) + x1 + 1] - p[yy * (w + 1) + x0]
                if (isDilate && cnt > 0) { res = true; break }
                if (!isDilate && cnt < x1 - x0 + 1) { res = false; break }
            }
            out[y * w + x] = res
        }
        return out
    }

    // _fill_holes: fill each outer shape and keep shapes of at least 1% of the image.
    // Python uses cv2.contourArea, here the filled pixel count is used (see README.md).
    private fun fillHoles(m: BooleanArray, w: Int, h: Int): BooleanArray {
        val n = w * h
        // background reachable from the border (4 neighbours) is outside; the rest are holes
        val outside = BooleanArray(n)
        val stack = IntArray(n)
        var sp = 0
        fun push(i: Int) { if (!m[i] && !outside[i]) { outside[i] = true; stack[sp++] = i } }
        for (x in 0 until w) { push(x); push((h - 1) * w + x) }
        for (y in 0 until h) { push(y * w); push(y * w + w - 1) }
        while (sp > 0) {
            val i = stack[--sp]
            val x = i % w
            val y = i / w
            if (x > 0) push(i - 1)
            if (x < w - 1) push(i + 1)
            if (y > 0) push(i - w)
            if (y < h - 1) push(i + w)
        }
        val filled = BooleanArray(n) { !outside[it] }
        // shapes are 8 connected, as cv2.findContours sees them
        val seen = BooleanArray(n)
        val out = BooleanArray(n)
        val minArea = 0.01 * n
        val part = IntArray(n)
        for (start in 0 until n) {
            if (!filled[start] || seen[start]) continue
            var cnt = 0
            sp = 0
            stack[sp++] = start
            seen[start] = true
            while (sp > 0) {
                val i = stack[--sp]
                part[cnt++] = i
                val x = i % w
                val y = i / w
                for (dy in -1..1) for (dx in -1..1) {
                    val nx = x + dx
                    val ny = y + dy
                    if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue
                    val j = ny * w + nx
                    if (filled[j] && !seen[j]) { seen[j] = true; stack[sp++] = j }
                }
            }
            if (cnt >= minArea) for (q in 0 until cnt) out[part[q]] = true
        }
        return out
    }
}
