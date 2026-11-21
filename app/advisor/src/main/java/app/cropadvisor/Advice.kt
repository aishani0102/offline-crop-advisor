package app.cropadvisor

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

// Port of the advisory stage (advisory/knowledge.py, prompt.py, template.py,
// safety.py, referral.py, memory.py). Everything said comes from kb.json.
//
// The phone does not estimate severity yet, so band is null for a disease or
// pest. Then we give the signs and the non chemical steps only, never a spray
// or dose, and always add the KVK referral line.

data class Case(
    val label: String, val crop: String, val condition: String, val type: String,
    val confidence: Float, val uncertain: Boolean, val band: String?, val pct: Float?, val lang: String = "en",
) {
    val needsReferral get() = uncertain || band == "severe" || (type != "healthy" && band == null)

    companion object {
        fun from(d: Diagnosis, lang: String = "en"): Case {
            val crop = d.label.substringBefore('_')
            val type = when {
                d.label.endsWith("_healthy") -> "healthy"
                d.label.endsWith("_leaf_miner") -> "pest"
                else -> "disease"
            }
            return Case(
                d.label, crop, conditionName(d.label), type, d.confidence, d.uncertain,
                if (type == "healthy") "none" else null, null, lang,
            )
        }
    }
}

class Facts(val lang: String, val kind: String) {
    var title = ""
    var summary = ""
    var signs = listOf<String>()
    var steps = listOf<String>()
    var severityNote = ""
    var chemicals = listOf<String>()
    var chemicalNote = ""
    var safety = listOf<String>()
    var noDose = ""
    var referral = ""
    var watch = ""

    // All fact text in one string, the allowed source for the safety check.
    fun text(): String = (listOf(title, summary, severityNote, chemicalNote, noDose, referral, watch) +
        signs + steps + chemicals + safety).filter { it.isNotEmpty() }.joinToString("\n")
}

// Languages the app offers. Llama only writes en and hi (the advisory eval only
// covered those). The others always get the translated template.
val LANGUAGES = listOf("en", "hi", "bn", "mr", "ta", "te")
val LLM_LANGUAGES = setOf("en", "hi")

// ctx should be the activity, so getString gives the chosen language.
class Advisor(private val ctx: Context) {
    val kb = JSONObject(readAsset("kb.json"))
    private val entries = kb.getJSONObject("entries")

    init {
        // kb_<lang>.json files have the same keys as kb.json with one language
        // each. Merge them in, so a missing text falls back to English below.
        for (l in LANGUAGES - setOf("en", "hi")) merge(kb, JSONObject(readAsset("kb_$l.json")))
    }

    private fun readAsset(name: String) = ctx.assets.open(name).bufferedReader(Charsets.UTF_8).readText()

    private fun merge(base: JSONObject, over: JSONObject) {
        for (k in over.keys()) {
            val b = base.opt(k)
            val o = over.get(k)
            if (b is JSONObject && o is JSONObject) merge(b, o) else if (b == null) base.put(k, o)
        }
    }

    private fun JSONArray.strings() = List(length()) { getString(it) }
    private fun JSONObject.lang(key: String, lang: String) = getJSONObject(key).let { it.optString(lang, "").ifEmpty { it.getString("en") } }
    private fun JSONObject.langList(key: String, lang: String) =
        getJSONObject(key).let { (it.optJSONArray(lang) ?: it.getJSONArray("en")).strings() }

    private fun res(name: String) = ctx.getString(ctx.resources.getIdentifier(name, "string", ctx.packageName))

    private fun chemLine(c: JSONObject, lang: String): String {
        val dose = c.lang("dose", lang)
        val days = c.optInt("waiting_days", 0)
        return if (lang == "hi") {
            val wait = if (days > 0) "तुड़ाई से $days दिन पहले तक छिड़काव न करें" else "प्रतीक्षा अवधि लेबल पर देखें"
            "${c.getString("name_hi")} (${c.getString("product")}): $dose, $wait"
        } else {
            val wait = if (days > 0) "do not spray in the last $days days before harvest" else "check the waiting period on the label"
            "${c.getString("product")}: $dose, $wait"
        }
    }

    fun title(c: Case): String {
        var t = if (c.lang == "en") "${c.crop.replaceFirstChar { it.uppercase() }}: ${c.condition.lowercase()}"
        else "${res(c.crop)}: ${res("cond_" + c.label.substringAfter('_'))}"
        if (c.band in listOf("mild", "moderate", "severe")) {
            t += ", ${c.band}"
            c.pct?.let { t += " (about ${Math.round(it)}% of the leaf)" }
        }
        return t
    }

    fun facts(c: Case, compact: Boolean = false): Facts {
        val lang = c.lang
        val entry = entries.optJSONObject(c.label)
        if (c.uncertain || entry == null) {
            return Facts(lang, "uncertain").apply {
                summary = kb.lang("uncertain", lang)
                referral = kb.lang("referral", lang)
            }
        }
        if (c.type == "healthy") {
            return Facts(lang, "healthy").apply {
                title = title(c)
                summary = entry.lang("description", lang)
                steps = entry.langList("cultural_ipm", lang).take(if (compact) 3 else 4)
                watch = entry.lang("call_kvk", lang)
            }
        }
        val band = c.band
        val f = Facts(lang, band ?: "unknown")
        f.title = title(c)
        f.summary = entry.lang("description", lang)
        f.signs = entry.langList("recognise", lang).take(if (compact) 1 else 2)
        f.steps = entry.langList("cultural_ipm", lang).take(if (compact) 2 else 3)
        if (band != null) f.severityNote = entry.getJSONObject("severity").lang(band, lang)
        if (band == "moderate" || band == "severe") {
            val all = entry.getJSONArray("chemicals")
            val n = if (compact) minOf(2, all.length()) else all.length()
            f.chemicals = List(n) { chemLine(all.getJSONObject(it), lang) }
            f.chemicalNote = entry.lang("chemical_note", lang)
            if (all.length() > 0) {
                val gs = kb.getJSONObject("general_safety").getJSONArray(lang).strings()
                f.safety = if (compact) gs.drop(1).take(1) else gs.take(2)
            } else {
                f.noDose = kb.lang("no_dose_text", lang)
            }
        }
        if (c.needsReferral) f.referral = kb.lang("referral", lang)
        return f
    }

    // template.py. Template text is KB text only, so it is safe by construction
    // and is not run through the safety check.
    fun template(c: Case): String {
        val f = facts(c)
        val lines = mutableListOf<String>()
        if (f.kind == "uncertain") return listOf(f.summary, f.referral).joinToString("\n")
        lines += f.title + if (c.lang == "en") "." else ""
        lines += f.summary
        if (f.kind == "healthy") {
            lines += res("keep_healthy") + ":"
            lines += f.steps.take(3).map { "- $it" }
            lines += f.watch
            return lines.joinToString("\n")
        }
        if (f.severityNote.isNotEmpty()) lines += f.severityNote
        if (f.signs.isNotEmpty()) {
            lines += res("signs") + ":"
            lines += f.signs.map { "- $it" }
        }
        lines += res("what_to_do") + ":"
        lines += f.steps.map { "- $it" }
        if (f.chemicals.isNotEmpty()) {
            lines += res("spray") + ":"
            lines += f.chemicals.map { "- $it" }
            lines += f.safety
        } else if (f.noDose.isNotEmpty()) {
            lines += f.noDose
        }
        if (f.referral.isNotEmpty()) lines += f.referral
        return lines.joinToString("\n")
    }

    // prompt.py
    fun prompt(c: Case): Pair<String, String> {
        val f = facts(c, compact = true)
        val langName = if (c.lang == "hi") "simple Hindi (Devanagari script)" else "English"
        val words = if (c.lang == "hi") 80 else 120
        val system = "You help small farmers in India. Rewrite the FACTS as short, simple advice for a farmer, " +
            "in $langName. Rules: use only the FACTS. Do not add any chemical, product, dose or number that is " +
            "not in the FACTS. Do not add new advice. Start by naming the crop and the problem. " +
            "Write $words words or less, in plain sentences, no headings."
        val lines = mutableListOf<String>()
        if (f.title.isNotEmpty()) lines += f.title
        lines += f.summary
        lines += f.signs
        if (f.severityNote.isNotEmpty()) lines += f.severityNote
        lines += f.steps
        if (f.watch.isNotEmpty()) lines += f.watch
        if (f.chemicals.isNotEmpty()) {
            lines += f.chemicalNote
            lines += f.chemicals
            lines += f.safety
        }
        if (f.noDose.isNotEmpty()) lines += f.noDose
        var user = "FACTS:\n" + lines.joinToString("\n") { "- $it" }
        if (f.kind == "healthy") user += "\n\nThe leaf is healthy. Give a short reassurance and two or three prevention tips."
        if (f.referral.isNotEmpty()) user += "\n\nEnd with this exact sentence: " + f.referral
        return system to user
    }

    fun cleanOutput(raw: String): String =
        raw.replace("<|eot_id|>", "").replace("<|end_of_text|>", "")
            .replaceFirst(Regex("^\\s*(here is|here's|sure|okay|ok,)[^\\n]*:\\s*\\n", RegexOption.IGNORE_CASE), "")
            .trim()

    // safety.py: returns the failed checks, empty means the text can be shown.
    fun check(text: String, c: Case, truncated: Boolean): List<String> {
        if (text.isBlank()) return listOf("empty")
        val source = facts(c).text()
        val fails = mutableListOf<String>()
        val allowed = Safety.chemicals(source, kb)
        val extra = Safety.chemicals(text, kb).filter { x -> allowed.none { x in it || it in x } }
        if (extra.isNotEmpty()) fails += "chemical_not_in_kb:" + extra.sorted().joinToString(",")
        var allowedNums = Safety.numbers(source)
        c.pct?.let { allowedNums = allowedNums + Safety.numbers(it.toString()) }
        val badNums = Safety.numbers(text) - allowedNums
        if (badNums.isNotEmpty()) fails += "number_not_in_kb:" + badNums.sorted().joinToString(",")
        val badPairs = Safety.dosePairs(text) - Safety.dosePairs(source)
        if (badPairs.isNotEmpty()) fails += "dose_not_in_kb"
        val wordDoses = Safety.WORD_DOSE.findAll(text).map { it.value }.filter { it.lowercase() !in source.lowercase() }.toList()
        if (wordDoses.isNotEmpty()) fails += "dose_in_words:" + wordDoses.joinToString(",")
        val mismatch = Safety.wrongNames(text, source)
        if (mismatch.isNotEmpty()) fails += "crop_or_condition_mismatch:" + mismatch.joinToString(",")
        if (c.needsReferral && !Safety.hasReferral(text)) fails += "missing_referral"
        if (!Safety.scriptOk(text, c.lang)) fails += "wrong_language"
        if (truncated) fails += "cut_off"
        if (text.split(Regex("\\s+")).size > (if (c.lang == "hi") 150 else 170)) fails += "too_long"
        return fails
    }

    // referral.py, plus the confidence. Plain ASCII so it fits in one SMS.
    fun sms(c: Case): String {
        val d = SimpleDateFormat("dd-MM-yyyy", Locale.US).format(Date())
        var cond = c.condition.lowercase()
        if (c.uncertain) cond = "possible $cond (unsure)"
        val sev = if (c.band in listOf("mild", "moderate", "severe")) ", ${c.band}" else ""
        val conf = Math.round(c.confidence * 100)
        return "KVK help: ${c.crop} $cond$sev, app confidence $conf%. Date $d, village ______. " +
            "Seen by offline crop app. Please advise."
    }

    companion object {
        // memory.py uses 2544 MB (2032 MB peak on the laptop plus 512 MB margin).
        // On the Redmi 12 the whole app peaked at 1559 MB RSS with Llama loaded,
        // so 1900 MB free leaves about 340 MB margin and lets Llama run there.
        const val LLAMA_NEEDS_MB = 1900L
    }
}

object Safety {
    private val EXTRA_EN = listOf(
        "chlorpyrifos", "monocrotophos", "carbendazim", "carbofuran", "phorate", "profenofos",
        "cypermethrin", "endosulfan", "dimethoate", "acephate", "metalaxyl", "propineb", "hexaconazole",
        "tebuconazole", "difenoconazole", "propiconazole", "copper sulphate", "copper sulfate", "copper",
        "sulphur", "sulfur", "bordeaux", "streptocycline", "streptomycin", "emamectin", "spinosad",
        "chlorantraniliprole", "flubendiamide", "thiram", "zineb", "ziram", "maneb", "iprodione", "kitazin",
        "malathion", "quinalphos", "glyphosate", "paraquat", "2,4-d", "ddt", "methyl parathion", "parathion",
        "triazophos", "fipronil", "lambda-cyhalothrin", "cyhalothrin", "deltamethrin", "bifenthrin",
        "abamectin", "neem", "nske", "azadirachtin", "trichoderma", "pseudomonas", "fluxapyroxad",
        "pyraclostrobin", "trifloxystrobin", "famoxadone", "fenamidone", "mandipropamid", "metiram",
        "oxydemeton", "methyl demeton", "spiromesifen", "fenazaquin", "novaluron", "indoxacarb",
        "thiacloprid", "acetamiprid", "clothianidin", "dinotefuran", "buprofezin", "diafenthiuron",
        "pymetrozine", "aureofungin", "validamycin", "tricyclazole", "benomyl", "chlorothalonil",
        "captan", "mancozeb", "azoxystrobin", "cymoxanil", "cyazofamid", "dimethomorph", "imidacloprid",
        "thiamethoxam", "cyantraniliprole", "copper oxychloride", "urea", "dap", "potash",
        "bavistin", "blitox", "dithane", "indofil", "ridomil", "curzate", "confidor", "actara", "coragen",
        "kavach", "saaf", "nativo", "amistar", "antracol", "kocide", "sulfex", "nuvan", "rogor",
    )
    // Hindi names, used when Llama writes in Hindi.
    private val EXTRA_HI = listOf(
        "क्लोरपायरीफॉस", "क्लोरपाइरीफॉस", "मोनोक्रोटोफॉस", "कार्बेन्डाजिम", "कार्बेंडाजिम", "कार्बोफ्यूरान",
        "फोरेट", "प्रोफेनोफॉस", "साइपरमेथ्रिन", "एंडोसल्फान", "डाइमेथोएट", "एसीफेट", "मेटालैक्सिल",
        "प्रोपिनेब", "हेक्साकोनाज़ोल", "हेक्साकोनाजोल", "टेबुकोनाज़ोल", "कॉपर", "तांबा", "गंधक", "सल्फर",
        "बोर्डो", "स्ट्रेप्टोसाइक्लिन", "इमामेक्टिन", "स्पिनोसैड", "क्लोरएन्ट्रानिलिप्रोल", "थीरम", "थायरम",
        "ज़िनेब", "जिनेब", "मैलाथियान", "क्विनालफॉस", "ग्लाइफोसेट", "पैराक्वाट", "फिप्रोनिल", "नीम",
        "ट्राइकोडर्मा", "क्लोरोथालोनिल", "कैप्टान", "मैंकोज़ेब", "मैन्कोज़ेब", "मैंकोजेब", "मेन्कोजेब",
        "एज़ोक्सीस्ट्रोबिन", "साइमोक्सानिल", "साइज़ोफ़ामिड", "डाइमेथोमॉर्फ", "इमिडाक्लोप्रिड",
        "थायामेथोक्साम", "थियामेथोक्सम", "साइएन्ट्रानिलिप्रोल", "यूरिया", "डीएपी", "पोटाश",
    )
    private val CHEM_SUFFIX = Regex(
        "\\b[a-z]{3,}(?:zole|zol|strobin|carb|phos|fos|thrin|mectin|cloprid|thoxam|thalonil|" +
            "ozeb|zeb|neb|sulfan|thion|oxanil|famid|morph|uron|prole)\\b",
    )
    private const val UNITS_EN = "(?:g|gm|gram|grams|kg|ml|millilitre|millilitres|milliliter|litre|litres|liter|liters|l|lit|percent|%|ppm|acre|ha|hectare)"
    private const val NUM_WORDS_EN = "(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|fifty|hundred|half|quarter)"
    private const val UNITS_HI = "(?:ग्राम|किलो|मिली|मिलीलीटर|लीटर|प्रतिशत|एकड़|हेक्टेयर)"
    private const val NUM_WORDS_HI = "(?:एक|दो|तीन|चार|पांच|पाँच|छह|सात|आठ|नौ|दस|बीस|पचास|सौ|आधा|आधी)"
    val WORD_DOSE = Regex("\\b$NUM_WORDS_EN\\s+$UNITS_EN\\b|(?<!\\S)$NUM_WORDS_HI\\s+$UNITS_HI", RegexOption.IGNORE_CASE)
    private val CROPS = listOf(
        "tomato", "potato", "wheat", "rice", "paddy", "maize", "corn", "cotton", "chilli", "chili",
        "brinjal", "eggplant", "onion", "soybean", "sugarcane", "mustard", "groundnut", "banana",
        "टमाटर", "आलू", "गेहूं", "गेहूँ", "धान", "चावल", "मक्का", "कपास", "मिर्च", "बैंगन", "प्याज",
        "सोयाबीन", "गन्ना", "सरसों", "मूंगफली", "केला",
    )
    private val CONDITIONS = listOf(
        "early blight", "late blight", "leaf mold", "leaf mould", "septoria", "leaf curl",
        "leaf miner", "powdery mildew", "downy mildew", "rust", "wilt", "mosaic", "bacterial spot",
        "anthracnose", "canker", "pest infestation", "nutrient deficiency", "root rot",
        "अगेती झुलसा", "पछेती झुलसा", "पत्ती फफूंद", "सेप्टोरिया", "पत्ती मोड़क", "पत्ती सुरंगक",
        "चूर्णिल आसिता", "रतुआ", "उकठा", "मोज़ेक", "विल्ट",
    )
    private val UNIT_MAP = mapOf(
        "g" to "g", "gm" to "g", "gram" to "g", "grams" to "g", "kg" to "kg", "kilo" to "kg",
        "kilogram" to "kg", "kilograms" to "kg", "ml" to "ml", "millilitre" to "ml", "millilitres" to "ml",
        "l" to "l", "lit" to "l", "litre" to "l", "litres" to "l", "liter" to "l", "liters" to "l",
        "%" to "%", "percent" to "%", "days" to "day", "day" to "day",
        "ग्राम" to "g", "किलो" to "kg", "मिली" to "ml", "लीटर" to "l", "प्रतिशत" to "%", "दिन" to "day",
    )
    private val DOSE_RE = Regex(
        "(\\d+(?:\\.\\d+)?)(?:\\s*(?:to|-|से)\\s*(\\d+(?:\\.\\d+)?))?\\s*" +
            "(kilograms|kilogram|millilitres|millilitre|grams|gram|litres|litre|liters|liter|" +
            "percent|days|day|kilo|lit|gm|kg|ml|g|l|%|ग्राम|किलो|मिली|लीटर|प्रतिशत|दिन)(?![a-z])",
        RegexOption.IGNORE_CASE,
    )

    private var lexicon: List<String>? = null

    private fun lexicon(kb: JSONObject): List<String> = lexicon ?: run {
        val names = (EXTRA_EN + EXTRA_HI).toMutableSet()
        val entries = kb.getJSONObject("entries")
        for (key in entries.keys()) {
            val chems = entries.getJSONObject(key).getJSONArray("chemicals")
            for (i in 0 until chems.length()) {
                chems.getJSONObject(i).getString("name").split("+").forEach { names += it.trim().lowercase() }
                chems.getJSONObject(i).getString("name_hi").split("+").forEach { names += it.trim() }
            }
        }
        names.sortedByDescending { it.length }.also { lexicon = it }
    }

    // Hindi names are matched as plain substrings, like safety.py does.
    private fun hasWord(low: String, name: String) = if (name.any { it in '\u0900'..'\u097F' }) name in low else
        Regex("(?<![a-z])" + Regex.escape(name) + "(?![a-z])").containsMatchIn(low)

    fun chemicals(text: String, kb: JSONObject): Set<String> {
        val low = text.lowercase()
        val found = mutableSetOf<String>()
        lexicon(kb).filterTo(found) { hasWord(low, it) }
        CHEM_SUFFIX.findAll(low).map { it.value }.filterTo(found) { it != "thion" }
        // "copper oxychloride" also matches "copper", keep only the longest
        return found.filter { f -> found.none { g -> f != g && f in g } }.toSet()
    }

    fun wrongNames(text: String, source: String): List<String> {
        val low = text.lowercase()
        val src = source.lowercase()
        return (CROPS + CONDITIONS).filter { hasWord(low, it) && it !in src }
    }

    private fun asciiDigits(s: String) = s.map { if (it in '\u0966'..'\u096F') '0' + (it - '\u0966') else it }.joinToString("")

    fun dosePairs(raw: String): Set<Pair<String, String>> {
        val text = asciiDigits(raw)
        val out = mutableSetOf<Pair<String, String>>()
        for (m in DOSE_RE.findAll(text)) {
            val u = UNIT_MAP[m.groupValues[3].lowercase()] ?: continue
            out += m.groupValues[1] to u
            if (m.groupValues[2].isNotEmpty()) out += m.groupValues[2] to u
        }
        return out
    }

    fun numbers(text: String): Set<String> {
        val t = asciiDigits(text).replace(Regex("(?m)^\\s*\\d+[.)]\\s+"), "").replace("1800-180-1551", " HELPLINE ")
        return Regex("\\d+(?:\\.\\d+)?").findAll(t).map { it.value }.toSet()
    }

    fun hasReferral(text: String): Boolean {
        val low = text.lowercase()
        val digits = asciiDigits(text).filter { it in '0'..'9' }
        return "18001801551" in digits || listOf(
            "kvk", "krishi vigyan kendra", "kisan call centre", "kisan call center",
            "कृषि विज्ञान केंद्र", "कृषि विज्ञान केन्द्र", "केवीके", "किसान कॉल सेंटर",
        )
            .any { it in low }
    }

    fun scriptOk(text: String, lang: String): Boolean {
        val letters = text.filter { it.isLetter() }
        if (letters.isEmpty()) return false
        val share = letters.count { it in 'ऀ'..'ॿ' }.toFloat() / letters.length
        return if (lang == "hi") share >= 0.6f else share <= 0.05f
    }
}
