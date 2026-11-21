package app.cropadvisor

import android.graphics.Bitmap
import org.pytorch.executorch.EValue
import org.pytorch.executorch.Module
import org.pytorch.executorch.Tensor
import kotlin.math.exp
import kotlin.math.roundToInt

// Leaf classifier. Preprocessing matches detection/common.py: shorter side to
// 256, centre crop 224, ImageNet mean and std. Temperature from training.
class Vision(path: String) {
    private val module = Module.load(path)

    data class Result(val probs: FloatArray, val ms: Long) {
        fun top(k: Int) = probs.indices.sortedByDescending { probs[it] }.take(k)
    }

    fun classify(src: Bitmap): Result {
        val t0 = System.currentTimeMillis()
        val input = Tensor.fromBlob(toChw(src), longArrayOf(1, 3, SIZE.toLong(), SIZE.toLong()))
        val logits = module.forward(EValue.from(input))[0].toTensor().dataAsFloatArray
        return Result(softmax(logits), System.currentTimeMillis() - t0)
    }

    fun close() = module.destroy()

    companion object {
        const val SIZE = 224
        const val TEMPERATURE = 0.7087f
        val LABELS = listOf(
            "potato_early_blight", "potato_healthy", "potato_late_blight",
            "tomato_early_blight", "tomato_healthy", "tomato_late_blight",
            "tomato_leaf_miner", "tomato_leaf_mold", "tomato_septoria_leaf_spot",
            "tomato_yellow_leaf_curl_virus",
        )
        private val MEAN = floatArrayOf(0.485f, 0.456f, 0.406f)
        private val STD = floatArrayOf(0.229f, 0.224f, 0.225f)

        fun toChw(src: Bitmap): FloatArray {
            val resized = Photo.shortSide256(src)
            val w = resized.width
            val h = resized.height
            val crop = Bitmap.createBitmap(resized, (w - SIZE) / 2, (h - SIZE) / 2, SIZE, SIZE)
            val px = IntArray(SIZE * SIZE)
            crop.getPixels(px, 0, SIZE, 0, 0, SIZE, SIZE)
            val n = SIZE * SIZE
            val out = FloatArray(3 * n)
            for (i in 0 until n) {
                val p = px[i]
                out[i] = (((p shr 16) and 0xFF) / 255f - MEAN[0]) / STD[0]
                out[n + i] = (((p shr 8) and 0xFF) / 255f - MEAN[1]) / STD[1]
                out[2 * n + i] = ((p and 0xFF) / 255f - MEAN[2]) / STD[2]
            }
            return out
        }

        fun softmax(logits: FloatArray): FloatArray {
            val z = logits.map { it / TEMPERATURE }
            val m = z.max()
            val e = z.map { exp(it - m) }
            val s = e.sum()
            return e.map { it / s }.toFloatArray()
        }
    }
}
