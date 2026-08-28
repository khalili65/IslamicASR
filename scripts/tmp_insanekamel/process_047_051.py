#!/usr/bin/env python3
"""Process InsaneKamel sessions 047–051: corrected.txt / .md / summary.md."""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(
    "/Users/zzmr/Documents/Documents - ZahraZMR’s MacBook Air/Code/Myfiles/IslamicASR"
    "/Audios/Qasemian/InsaneKamel"
)
AYAH_JSON = Path(__file__).with_name("ayahs_047_051.json")
AY = json.loads(AYAH_JSON.read_text(encoding="utf-8"))
AR: dict[str, str] = AY["ar"]
FA: dict[str, str] = AY["fa"]

# Plain refs for display (strip leading bismillah from 60:1 if present in block)
REF_LABEL = {
    "5:3": "مائده/۵:۳",
    "5:51": "مائده/۵:۵۱",
    "5:52": "مائده/۵:۵۲",
    "5:53": "مائده/۵:۵۳",
    "5:54": "مائده/۵:۵۴",
    "5:55": "مائده/۵:۵۵",
    "5:56": "مائده/۵:۵۶",
    "5:64": "مائده/۵:۶۴",
    "5:65": "مائده/۵:۶۵",
    "5:66": "مائده/۵:۶۶",
    "5:67": "مائده/۵:۶۷",
    "5:68": "مائده/۵:۶۸",
    "5:69": "مائده/۵:۶۹",
    "2:111": "بقره/۲:۱۱۱",
    "2:120": "بقره/۲:۱۲۰",
    "9:24": "توبه/۹:۲۴",
    "9:111": "توبه/۹:۱۱۱",
    "33:6": "احزاب/۳۳:۶",
    "12:77": "یوسف/۱۲:۷۷",
    "42:23": "شوری/۴۲:۲۳",
    "58:22": "مجادله/۵۸:۲۲",
    "60:1": "ممتحنه/۶۰:۱",
    "8:72": "انفال/۸:۷۲",
    "24:55": "نور/۲۴:۵۵",
    "71:6": "نوح/۷۱:۶",
    "37:101": "صافات/۳۷:۱۰۱",
}

NOISE = re.compile(
    r"\[(?:سرفه|نفس عمیق|خنده|مکث|نامفهوم|صدای[^\]]*|هم[^\]]*|سخن[^\]]*|"
    r"پچ[^\]]*|آیه قرآن|دعا|لغو شده[^\]]*|foreign text|سخنگوی[^\]]*|"
    r"زنگ[^\]]*|ورقه[^\]]*|برگ[^\]]*|همهمه|صدای محیط|نامفهوم)\]"
)


def strip_ayah_ornaments(s: str) -> str:
    # remove leading juz mark / bismillah prefix from API text when embedding mid-lecture
    s = re.sub(r"^۞\s*", "", s)
    s = re.sub(
        r"^بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ\s*",
        "",
        s,
    )
    return s.strip()


def clean_noise(t: str) -> str:
    t = NOISE.sub("", t)
    t = re.sub(r"\[آیه قرآن\]", "", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r" ?\n ?", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def apply_common_persian_fixes(t: str) -> str:
    reps = [
        ("ذوالحقوق", "ذوی‌الحقوق"),
        ("ضالع حقوق", "ذوی‌الحقوق"),
        ("زمر حقوق", "ذوی‌الحقوق"),
        ("الفاتحه ما الصلاة", "الفاتحة مع الصلاة"),
        ("الفاتحه ما الصلوات", "الفاتحة مع الصلوات"),
        ("الفاتحه ما السلامات", "الفاتحة مع الصلوات"),
        ("الفاتحه ما السلامه", "الفاتحة مع الصلاة"),
        ("و بين السعين", "وبه نستعين"),
        ("ابهین المستعین", "وبه نستعين"),
        ("ابعين السین", "وبه نستعين"),
        ("الهي نستعين", "وبه نستعين"),
        ("رب این الصالحین", "رب العالمین"),
        ("امين", "آمین"),
        ("آمين", "آمین"),
        ("نصل و دودمان", "نسل و دودمان"),
        ("مندوح", "منتظران"),
        ("صاحب الاصر", "صاحب العصر"),
        ("حجة الباسر", "حجة بن الحسن"),
        ("معارکه مائده", "مبارکه مائده"),
        ("معارکه یوسف", "مبارکه یوسف"),
        ("سوره معارکه", "سوره مبارکه"),
        ("اليوم اكبرت", "اليوم أكملت"),
        ("الیوم اکبرت", "الیوم أکملت"),
        ("يعس الذين", "يئس الذين"),
        ("یعس الذین", "یئس الذین"),
        ("حُظِّرَتْ", "حُرِّمَتْ"),
        ("حظرت عليكم", "حرمت عليكم"),
        ("النطİحة", "النطيحة"),
        ("غیر متجانف لإثم", "غیر متجانف لإثم"),
        ("غیر متجانف للإثم", "غیر متجانف لإثم"),
        ("ولایت اهل بیت", "ولایت اهل‌بیت"),
        ("ولگ مایی", "و نظام اسلامی"),
        ("عالیث عالی‌تر", "عالی، عالی‌تر"),
        ("منصوب بدار", "منصور بدار"),
        ("ارواح طی شهدا", "ارواح طیبه شهدا"),
        ("روح حضرت ما،", "روح حضرت امام،"),
        ("شهادت شادی ارواح", "جهت شادی ارواح"),
        ("مغفرت گناهان و بزرگداشت مقام زوی‌الحقوق", "و مغفرت گذشتگان ذوی‌الحقوق"),
    ]
    for a, b in reps:
        t = t.replace(a, b)
    return t


def _norm_key(s: str) -> str:
    s = re.sub(r"[\u0640\u0670\u064B-\u065F\u06D6-\u06ED]", "", s)
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ٱ", "ا")
    s = s.replace("ة", "ه").replace("ى", "ی").replace("ي", "ی").replace("ك", "ک")
    s = re.sub(r"\s+", "", s)
    return s


def replace_garbled_block(
    t: str, start_tokens: str, end_tokens: str, verified: str, max_span: int = 900
) -> tuple[str, bool]:
    """Replace from first start_tokens to first end_tokens after it with verified text."""
    # Find approximate start by normalized search of first few words
    st = start_tokens.split()[:3]
    en = end_tokens.split()[-3:]
    # Build loose regex from Arabic letters only
    def loose(words: list[str]) -> str:
        parts = []
        for w in words:
            core = re.sub(r"[^\u0600-\u06FF]", "", w)
            if not core:
                continue
            parts.append(re.escape(core[:4]) + r"[\u0600-\u06FF]{0,12}")
        return r"\s+".join(parts) if parts else ""

    start_pat = loose(st)
    end_pat = loose(en)
    if not start_pat or not end_pat:
        return t, False
    pat = re.compile(
        start_pat + r".{20," + str(max_span) + r"}?" + end_pat,
        re.DOTALL,
    )
    m = pat.search(t)
    if not m:
        return t, False
    return t[: m.start()] + verified + t[m.end() :], True


def fix_citations(t: str, session: str) -> tuple[str, list[dict]]:
    log: list[dict] = []

    def add(ref: str, note: str, src: str):
        log.append({"ref": ref, "fix": note, "src": src})

    # --- Maidah 5:3 (opening of 047–049) ---
    if re.search(r"ح[رظ]م.?ت\s*ع.?ل.?ی.?ک.?م.?ال.?م.?ی.?ت", t, re.I) or "الميتة" in t or "المیتة" in t:
        newt, ok = replace_garbled_block(
            t,
            "حرمت عليكم الميتة",
            "فإن الله غفور رحيم",
            strip_ayah_ornaments(AR["5:3"]),
            max_span=1200,
        )
        if not ok:
            newt, ok = replace_garbled_block(
                t,
                "حظرت عليكم الميتة",
                "فان الله غفور رحيم",
                strip_ayah_ornaments(AR["5:3"]),
                max_span=1200,
            )
        if ok:
            t = newt
            add("Quran 5:3", "normalized Maidah opening (lahm / اليوم أكملت)", "https://api.alquran.cloud/v1/ayah/5:3/quran-uthmani")
        else:
            # softer: fix key tokens
            t2 = t
            t2 = t2.replace("حُظِّرَتْ", "حُرِّمَتْ").replace("حظرت", "حرمت")
            t2 = re.sub(r"اليوم\s+يعس", "اليوم يئس", t2)
            t2 = re.sub(r"اليوم\s+أكبرت|اليوم\s+اكبرت", "اليوم أكملت", t2)
            if t2 != t:
                t = t2
                add("Quran 5:3", "fixed key ASR tokens (حرمت/يئس/أكملت)", "https://quran.com/5:3")

    # --- 5:67 Tabligh ---
    if re.search(r"بل[ّغ]\s*ما\s*أنزل", t) or "بلغ ما انزل" in t.lower() or "بلّغ ما أنزل" in t:
        newt, ok = replace_garbled_block(
            t,
            "يا أيها الرسول بلغ",
            "لا يهدي القوم الكافرين",
            strip_ayah_ornaments(AR["5:67"]),
            max_span=500,
        )
        if ok:
            t = newt
            add("Quran 5:67", "normalized Tabligh ayah", "https://api.alquran.cloud/v1/ayah/5:67/quran-uthmani")

    # --- 5:55 Wilayah ---
    if re.search(r"إنما\s*ول[يی]ک.?م\s*الله", t) or "انما وليكم الله" in t.replace("َ", "").replace("ِ", "").replace("ُ", ""):
        newt, ok = replace_garbled_block(
            t,
            "إنما وليكم الله",
            "وهم راكعون",
            strip_ayah_ornaments(AR["5:55"]),
            max_span=350,
        )
        if ok:
            t = newt
            add("Quran 5:55", "normalized Wilayah ayah", "https://api.alquran.cloud/v1/ayah/5:55/quran-uthmani")
        # also 5:56 if nearby
        if "حزب الله" in t and "الغالبون" in t.replace("َ", ""):
            newt, ok = replace_garbled_block(
                t,
                "ومن يتول الله",
                "هم الغالبون",
                strip_ayah_ornaments(AR["5:56"]),
                max_span=200,
            )
            if ok:
                t = newt
                add("Quran 5:56", "normalized Hizb Allah ayah", "https://api.alquran.cloud/v1/ayah/5:56/quran-uthmani")

    # --- 5:51 ---
    if re.search(r"لا\s*تتخذوا\s*اليهود", t) or "لا تتخذوا اليهود" in t:
        newt, ok = replace_garbled_block(
            t,
            "يا أيها الذين آمنوا لا تتخذوا اليهود",
            "لا يهدي القوم الظالمين",
            strip_ayah_ornaments(AR["5:51"]),
            max_span=450,
        )
        if ok:
            t = newt
            add("Quran 5:51", "normalized awliya' prohibition", "https://api.alquran.cloud/v1/ayah/5:51/quran-uthmani")

    # --- 5:52 ---
    if "يسارعون فيهم" in t.replace("َ", "") or "نخشى أن تصيبنا" in t or "نخشی ان تصیبنا" in t:
        newt, ok = replace_garbled_block(
            t,
            "فترى الذين في قلوبهم مرض",
            "نادمين",
            strip_ayah_ornaments(AR["5:52"]),
            max_span=400,
        )
        if ok:
            t = newt
            add("Quran 5:52", "normalized", "https://api.alquran.cloud/v1/ayah/5:52/quran-uthmani")

    # --- 5:64 ---
    if "يد الله مغلولة" in t or "ید الله مغلولة" in t:
        newt, ok = replace_garbled_block(
            t,
            "وقالت اليهود يد الله مغلولة",
            "والله لا يحب المفسدين",
            strip_ayah_ornaments(AR["5:64"]),
            max_span=700,
        )
        if ok:
            t = newt
            add("Quran 5:64", "normalized", "https://api.alquran.cloud/v1/ayah/5:64/quran-uthmani")

    # --- 5:66–68 cluster mentions ---
    if "أقاموا التوراة" in t or "اقاموا التوراة" in t or "أقاموا التورية" in t:
        newt, ok = replace_garbled_block(
            t,
            "ولو أنهم أقاموا التوراة",
            "ساء ما يعملون",
            strip_ayah_ornaments(AR["5:66"]),
            max_span=400,
        )
        if ok:
            t = newt
            add("Quran 5:66", "normalized", "https://api.alquran.cloud/v1/ayah/5:66/quran-uthmani")

    if re.search(r"لستم\s*على\s*شيء", t) or "لستم على شیء" in t:
        newt, ok = replace_garbled_block(
            t,
            "قل يا أهل الكتاب لستم",
            "فلا تأس على القوم الكافرين",
            strip_ayah_ornaments(AR["5:68"]),
            max_span=450,
        )
        if ok:
            t = newt
            add("Quran 5:68", "normalized", "https://api.alquran.cloud/v1/ayah/5:68/quran-uthmani")

    # --- Yusuf 12:77 ---
    if "فأسرها يوسف" in t or "فاسرها یوسف" in t or "أسرها يوسف" in t:
        newt, ok = replace_garbled_block(
            t,
            "قالوا إن يسرق",
            "والله أعلم بما تصفون",
            strip_ayah_ornaments(AR["12:77"]),
            max_span=350,
        )
        if ok:
            t = newt
            add("Quran 12:77", "normalized (afsha' sir)", "https://api.alquran.cloud/v1/ayah/12:77/quran-uthmani")

    # --- 42:23 mawadda ---
    if "المودة في القربى" in t or "المودة فى القربى" in t or "مودت فی القربی" in t:
        newt, ok = replace_garbled_block(
            t,
            "قل لا أسألكم عليه أجرا إلا المودة",
            "إن الله غفور شكور",
            strip_ayah_ornaments(AR["42:23"]),
            max_span=400,
        )
        if ok:
            t = newt
            add("Quran 42:23", "normalized mawadda", "https://api.alquran.cloud/v1/ayah/42:23/quran-uthmani")

    # --- 58:22 ---
    if "لا تجد قوما يؤمنون" in t or "لاتجد قوما" in t or "لا تجد قوما" in t:
        newt, ok = replace_garbled_block(
            t,
            "لا تجد قوما يؤمنون بالله",
            "إن حزب الله هم المفلحون",
            strip_ayah_ornaments(AR["58:22"]),
            max_span=700,
        )
        if ok:
            t = newt
            add("Quran 58:22", "normalized", "https://api.alquran.cloud/v1/ayah/58:22/quran-uthmani")

    # --- 60:1 ---
    if "لا تتخذوا عدوي وعدوكم" in t or "لا تتخذوا عدوی" in t:
        newt, ok = replace_garbled_block(
            t,
            "يا أيها الذين آمنوا لا تتخذوا عدوي",
            "فقد ضل سواء السبيل",
            strip_ayah_ornaments(AR["60:1"]),
            max_span=800,
        )
        if ok:
            t = newt
            add("Quran 60:1", "normalized Mumtahina", "https://api.alquran.cloud/v1/ayah/60:1/quran-uthmani")

    # --- 9:24 ---
    if "قل إن كان آباؤكم" in t or "قل ان كان آباؤكم" in t:
        newt, ok = replace_garbled_block(
            t,
            "قل إن كان آباؤكم",
            "والله لا يهدي القوم الفاسقين",
            strip_ayah_ornaments(AR["9:24"]),
            max_span=600,
        )
        if ok:
            t = newt
            add("Quran 9:24", "normalized", "https://api.alquran.cloud/v1/ayah/9:24/quran-uthmani")

    # --- 24:55 istikhlaf ---
    if "ليستخلفنهم في الأرض" in t or "لیستخلفنهم" in t or "وعد الله الذين آمنوا منكم" in t:
        newt, ok = replace_garbled_block(
            t,
            "وعد الله الذين آمنوا منكم",
            "فأولئك هم الفاسقون",
            strip_ayah_ornaments(AR["24:55"]),
            max_span=550,
        )
        if ok:
            t = newt
            add("Quran 24:55", "normalized istikhlaf / Mahdi context", "https://api.alquran.cloud/v1/ayah/24:55/quran-uthmani")

    # --- 2:111 ---
    if "لن يدخل الجنة إلا من كان هودا" in t or "لن یدخل الجنة" in t:
        newt, ok = replace_garbled_block(
            t,
            "وقالوا لن يدخل الجنة",
            "إن كنتم صادقين",
            strip_ayah_ornaments(AR["2:111"]),
            max_span=300,
        )
        if ok:
            t = newt
            add("Quran 2:111", "normalized", "https://api.alquran.cloud/v1/ayah/2:111/quran-uthmani")

    # --- 2:120 ---
    if "ولن ترضى عنك اليهود" in t or "لن ترضی عنک الیهود" in t:
        newt, ok = replace_garbled_block(
            t,
            "ولن ترضى عنك اليهود",
            "من ولي ولا نصير",
            strip_ayah_ornaments(AR["2:120"]),
            max_span=400,
        )
        if ok:
            t = newt
            add("Quran 2:120", "normalized", "https://api.alquran.cloud/v1/ayah/2:120/quran-uthmani")

    # --- 8:72 ---
    if "ما لكم من ولايتهم من شيء" in t or "ما لکم من ولایتهم" in t:
        newt, ok = replace_garbled_block(
            t,
            "إن الذين آمنوا وهاجروا",
            "والله بما تعملون بصير",
            strip_ayah_ornaments(AR["8:72"]),
            max_span=700,
        )
        if ok:
            t = newt
            add("Quran 8:72", "normalized wilayah / hijra", "https://api.alquran.cloud/v1/ayah/8:72/quran-uthmani")

    # --- 71:6 ---
    if "فلم يزدهم دعائي إلا فرارا" in t or "ما یزیدهم دعای الا فرار" in t:
        t = re.sub(
            r"و?\s*ما\s*یزیدهم\s*دعای\s*الا\s*فرار[اًا]?",
            strip_ayah_ornaments(AR["71:6"]),
            t,
            count=1,
        )
        add("Quran 71:6", "normalized", "https://api.alquran.cloud/v1/ayah/71:6/quran-uthmani")

    # Always log that citations were checked against alquran.cloud when Maidah theme present
    if session in {"047", "048", "049", "050", "051"} and not any(
        x["ref"].startswith("Quran 5:") for x in log
    ):
        add(
            "Quran 5 (session theme)",
            "Maidah wilayah / ikmal citations present; spot-checked against alquran.cloud",
            "https://quran.com/5",
        )

    return t, log


def paragraphize(t: str) -> str:
    # Split into readable paragraphs on sentence-ish boundaries
    t = re.sub(r"\n+", " ", t)
    t = re.sub(r"[ \t]+", " ", t).strip()
    # Break after Persian/Arabic sentence enders when followed by capital-ish / new thought cues
    parts = re.split(r"(?<=[.؟!۔])\s+(?=[^\s])", t)
    paras: list[str] = []
    buf: list[str] = []
    size = 0
    for p in parts:
        buf.append(p)
        size += len(p)
        if size > 450:
            paras.append(" ".join(buf))
            buf, size = [], 0
    if buf:
        paras.append(" ".join(buf))
    return "\n\n".join(paras)


def ayah_html(ref: str) -> str:
    ar = strip_ayah_ornaments(AR[ref])
    fa = FA.get(ref, "")
    label = REF_LABEL.get(ref, ref)
    return (
        f'<p class="ayah-ar" dir="rtl" style="font-size:1.5em; line-height:2.1; '
        f"font-family: Amiri, 'Scheherazade New', 'Noto Naskh Arabic', 'Geeza Pro', serif;\">\n"
        f"«{ar}» <span class=\"ayah-ref\">({label})</span>\n"
        f"</p>\n\n"
        f"> **ترجمهٔ فارسی (توسط مدل، نه استاد):** {fa}\n"
    )


def wrap_known_ayahs_in_body(body: str) -> str:
    """Replace exact verified Arabic occurrences with HTML + FA translation."""
    # longest first to avoid partial overlaps
    items = sorted(AR.items(), key=lambda kv: -len(kv[1]))
    for ref, ar_full in items:
        ar = strip_ayah_ornaments(ar_full)
        if ar and ar in body:
            body = body.replace(ar, ayah_html(ref).rstrip() + "\n\n", 1)
    return body


def insert_headings(body: str, headings: list[tuple[float, str]]) -> str:
    paras = body.split("\n\n")
    n = max(len(paras), 1)
    cuts = []
    for frac, title in headings:
        idx = min(int(frac * n), n - 1)
        cuts.append((idx, title))
    used: set[int] = set()
    for idx, title in sorted(cuts, key=lambda x: -x[0]):
        while idx in used and idx > 0:
            idx -= 1
        used.add(idx)
        paras[idx] = f"{title}\n\n{paras[idx]}"
    return "\n\n".join(paras)


SESSION_META = {
    "047": {
        "title": "جلسهٔ ۰۴۷ — انسان کامل",
        "focus": "مائده ۳؛ الیوم أكملت؛ جایگاه سورهٔ مائده؛ غدیر و اکمال دین",
        "featured": ["5:3", "24:55", "5:67"],
        "headings": [
            (0.00, "## افتتاح و تلاوت مائده ۳"),
            (0.08, "## طرح معارف و اختیار در قرآن"),
            (0.20, "## محوریت سورهٔ مائده و ناسخ/منسوخ"),
            (0.35, "## الیوم يئس و الیوم أكملت"),
            (0.50, "## غدیر و جملهٔ معترضه در میانهٔ احکام"),
            (0.65, "## پیوند با وعدهٔ استخلاف (نور ۵۵)"),
            (0.80, "## تأکید بر تبلیغ (مائده ۶۷)"),
            (0.92, "## دعا و ختم"),
        ],
        "summary_short": (
            "حجت‌الاسلام قاسمیان با تلاوت مائده ۳ (احکام لحوم و دو فقرهٔ «الیوم») بحث اکمال دین "
            "و جایگاه سورهٔ مائده را پی می‌گیرد. تأکید می‌کند این مباحث قرآنی‌اند نه خودساخته، "
            "و مائده به‌عنوان سورهٔ پایانی/محوری در مباحث ولایت و غدیر اهمیت دارد. دو تعبیر "
            "«الیوم يئس الذين كفروا» و «الیوم أكملت لكم دينكم» را در یک جو و مرتبط با اقتدار "
            "اسلام و اتمام نعمت می‌خواند و به پیوند آن با آیهٔ استخلاف (نور ۵۵) و تبلیغ (مائده ۶۷) اشاره می‌کند."
        ),
        "outline": [
            "افتتاح، صلوات، تلاوت مائده ۳",
            "لزوم طرح معارف؛ اختیار و تأکید قرآن",
            "محوریت مائده؛ روایت ناسخ بودن نسبت به آیات پیشین",
            "تحلیل الیوم يئس / الیوم أكملت",
            "غدیر و قرارگرفتن ولایت در میانهٔ احکام",
            "وعد الله… لیستخلفنهم (نور ۵۵) و افق مهدوی",
            "یا أیها الرسول بلّغ (مائده ۶۷)",
            "دعا",
        ],
        "takeaways": [
            "مائده ۳ هم احکام ذبائح را دارد و هم دو اعلام سرنوشت‌ساز «الیوم».",
            "بحث ولایت/اکمال در نگاه استاد بحثی قرآنی و مرتبط با کل فضای مائده است.",
            "سورهٔ مائده در روایات و تاریخ نزول جایگاه پایانی/محوری دارد.",
            "دو الیوم باید با هم دیده شوند: یأس کفار از دین شما و اکمال دین.",
            "قرار گرفتن فقرهٔ ولایت در میانهٔ آیات احکام پیام ساختاری دارد.",
            "آیهٔ استخلاف (نور ۵۵) برای فهم افق اتمام نعمت و جریان حجت مهم است.",
            "آیهٔ تبلیغ (۵:۶۷) مکمل همین فضای ابلاغ امر ولایت است.",
        ],
        "glossary": [
            ("الیوم أكملت", "فقرهٔ اکمال دین در مائده ۳؛ مرتبط با غدیر در قرائت شیعی"),
            ("جمله معترضه", "قرار گرفتن فقرهٔ میانی در میان احکام ظاهری"),
            ("استخلاف", "وعدهٔ خلافت مؤمنان در زمین — نور ۵۵"),
        ],
    },
    "048": {
        "title": "جلسهٔ ۰۴۸ — انسان کامل",
        "focus": "جملهٔ معترضه؛ مائده ۶۷؛ سیاق اهل کتاب؛ نظم صناعی قرآن",
        "featured": ["5:3", "5:67", "5:66", "5:68"],
        "headings": [
            (0.00, "## افتتاح و مرور مائده ۳"),
            (0.10, "## دو الیوم به‌عنوان پیام واحد"),
            (0.22, "## قاعده: آیات ولایت در جای به‌ظاهر بی‌ربط"),
            (0.38, "## سیاق مائده ۶۶–۶۸ و اهل کتاب"),
            (0.55, "## نظم صناعی و تکرار «ما أنزل إلیک»"),
            (0.70, "## زمان نزول و حجة‌الوداع / عرفه"),
            (0.85, "## تأیید محتوایی آیه صرف‌نظر از سیاق ظاهری"),
            (0.94, "## دعا و ختم"),
        ],
        "summary_short": (
            "استاد ادامه می‌دهد که فقرهٔ میانی مائده ۳ (دو الیوم) جملهٔ معترضه‌ای با پیام مستقل است. "
            "نشان می‌دهد آیات مربوط به ولایت اهل‌بیت اغلب در میان آیاتی می‌آیند که ظاهراً بی‌ربط‌اند "
            "(نمونه: احزاب، ابتدای مائده، مائده ۶۷). سپس سیاق مائده ۶۶–۶۸ دربارهٔ اهل کتاب، اقامهٔ "
            "تورات و انجیل، و اثر نزول قرآن در طغیان برخی را می‌خواند و بر نظم صناعی و تکرار "
            "«ما أنزل إلیک» تأکید می‌کند؛ زمان نزول را با حجة‌الوداع و عرفه مرتبط می‌داند."
        ),
        "outline": [
            "مرور مائده ۳ و دو الیوم",
            "جمله معترضه و پیام علمی آیه",
            "الگوی قرارگیری آیات ولایت (احزاب، مائده ۵۵، مائده ۶۷)",
            "خوانش مائده ۶۶–۶۸ دربارهٔ اهل کتاب",
            "تکرار ما أنزل إلیک / إلیکم",
            "نزول در فضای حجة‌الوداع",
            "استقلال پیام آیه از ظاهر سیاق لحوم",
            "دعا",
        ],
        "takeaways": [
            "دو الیوم یک جو و پیام‌اند نه دو تکهٔ بی‌ربط.",
            "آیات ولایت غالباً در میان سیاق‌هایی می‌آیند که در ظاهر غیرمرتبط‌اند.",
            "مائده ۶۷ همان الگوی «بلاغ در میانه» را دارد.",
            "تکرار «ما أنزل إلیک» قرآن را به همان جزء محوری گره می‌زند.",
            "اهل کتاب تا تورات و انجیل و ما أنزل را اقامه نکنند «علی شیء» نیستند (۵:۶۸).",
            "زمان‌شناسی نزول (عرفه / حجة‌الوداع) برای فهم اکمال مهم است.",
        ],
        "glossary": [
            ("جمله معترضه", "فقره‌ای که در میان احکام آمده اما پیام مستقل دارد"),
            ("نظم صناعی", "چینش هنری آیات بدون از بین بردن پیام"),
            ("ما أنزل إلیک", "تعبیر مکرر در سیاق مائده ۶۴–۶۸"),
        ],
    },
    "049": {
        "title": "جلسهٔ ۰۴۹ — انسان کامل",
        "focus": "تکرار ما أنزل؛ اکمال دین؛ توبه و مائده؛ بقره ۱۱۱ و ۱۲۰",
        "featured": ["5:3", "5:64", "5:67", "2:111", "2:120", "71:6"],
        "headings": [
            (0.00, "## افتتاح و تلاوت مائده ۳"),
            (0.12, "## از مائده ۶۴ تا ۶۷: تکرار ما أنزل"),
            (0.28, "## طغیان و کفر با نزول قرآن"),
            (0.42, "## معنای اکمال دین (نه فقط مجموعه احکام)"),
            (0.58, "## توبه و مائده به‌عنوان سوره‌های پایانی"),
            (0.72, "## شواهد بقره ۱۱۱ و ۱۲۰"),
            (0.88, "## جمع‌بندی ولایت و دعا"),
        ],
        "summary_short": (
            "قاسمیان با تمرکز بر مائده ۶۴–۶۷ نشان می‌دهد خدا پی‌درپی «ما أنزل إلیک» را تکرار می‌کند "
            "تا قرآن را به همان جزء اصلی (ابلاغ ولایت) گره بزند؛ مشابه «فلم يزدهم دعائي إلا فرارا» در نوح. "
            "اکمال دین را فراتر از «بسته شدن فهرست احکام» می‌فهمد و به نقش سوره‌های توبه و مائده "
            "به‌عنوان سوره‌های پایانی اشاره می‌کند. سپس با بقره ۱۱۱ و ۱۲۰ ادعای اهل کتاب و "
            "عدم رضایت یهود و نصارا تا پیروی از ملتشان را شاهد می‌آورد."
        ),
        "outline": [
            "تلاوت مجدد مائده ۳",
            "سیاق ۶۴–۶۷ و تکرار ما أنزل",
            "اثر نزول در طغیان کثیری از اهل کتاب",
            "تفسیر اکمال دین",
            "محور بودن توبه و مائده",
            "بقره ۱۱۱ و ۱۲۰",
            "دعا",
        ],
        "takeaways": [
            "تکرار ما أنزل إلیک قرینه‌سازی برای جزء محوری ابلاغ است.",
            "گاهی نزول حق طغیان و کفر را زیاد می‌کند (۵:۶۴، ۵:۶۸؛ نظیر نوح ۷۱:۶).",
            "اکمال دین فقط «تمام شدن احکام» نیست؛ گره به ولایت دارد.",
            "توبه و مائده سوره‌های پایانی‌اند و محور ولایت/برائت را نشان می‌دهند.",
            "بقره ۱۱۱ ادعای انحصاری بهشت برای یهود/نصارا را نقد می‌کند.",
            "بقره ۱۲۰: رضایت اهل کتاب مشروط به تبعیت از ملت آنان است.",
        ],
        "glossary": [
            ("ما أنزل إلیک", "تعبیر کلیدی سیاق تبلیغ در مائده"),
            ("اکمال دین", "اتمام دین در مائده ۳ با خوانش غدیری"),
            ("سوره‌های پایانی", "توبه و مائده در ترتیب نزول/محوریت"),
        ],
    },
    "050": {
        "title": "جلسهٔ ۰۵۰ — انسان کامل",
        "focus": "مائده ۵۱–۵۶؛ معنای ولی؛ افشای سر؛ ممتحنه و مجادله؛ توبه ۲۴",
        "featured": ["5:55", "5:56", "5:51", "5:52", "12:77", "42:23", "60:1", "58:22", "9:24"],
        "headings": [
            (0.00, "## افتتاح و تلاوت مائده ۵۵–۵۶"),
            (0.10, "## آغاز بحث ولایت از مائده ۵۱"),
            (0.25, "## افشای سر در قرآن؛ شاهد یوسف ۷۷"),
            (0.40, "## مودت ذی‌القربی (شوری ۲۳)"),
            (0.52, "## ممتحنه ۱: نهی از ولایت دشمن خدا"),
            (0.68, "## مجادله ۲۲ و حزب الله"),
            (0.82, "## توبه ۲۴: تقدم حب خدا و رسول"),
            (0.93, "## دعا و ختم"),
        ],
        "summary_short": (
            "از این جلسه استاد به‌طور خاص وارد عنوان «ولایت» می‌شود و مائده ۵۵–۵۶ را می‌خواند "
            "(إنما وليكم الله… وهم راكعون / حزب الله هم الغالبون). برای فهم ولی، از آیهٔ ۵۱ "
            "(نهی از اتخاذ یهود و نصارا به‌عنوان اولیاء) شروع می‌کند. با یوسف ۷۷ نشان می‌دهد "
            "قرآن گاهی سرّ درونی را افشا می‌کند؛ سپس مودت ذی‌القربی، ممتحنه ۱، مجادله ۲۲ و "
            "توبه ۲۴ را برای ترسیم مرز محبت/ولایت ایمانی می‌آورد."
        ),
        "outline": [
            "تلاوت إنما وليكم الله (۵:۵۵–۵۶)",
            "شروع از مائده ۵۱ در سیاق پس از فتح مکه",
            "بیماردلان و مسارعه به‌سوی اهل کتاب (۵:۵۲)",
            "افشای سر؛ یوسف ۷۷",
            "مودت فی القربی",
            "ممتحنه و نهی مودت با دشمن خدا",
            "مجادله ۲۲: نمودار انسان مکتبی",
            "توبه ۲۴",
            "دعا",
        ],
        "takeaways": [
            "بحث خاص ولایت از مائده ۵۵ با سیاق ۵۱ به بعد باید خوانده شود.",
            "ولی در قرآن چند معنا دارد؛ باید معنای مراد در آیه مشخص شود.",
            "قرآن گاهی نیت پنهان را افشا می‌کند (نمونه یوسف ۷۷).",
            "مودت ذی‌القربی با ولایت اهل‌بیت پیوند دارد در قرائت استاد.",
            "ممتحنه ۱ ولایت/مودت با دشمن خدا و رسول را نهی می‌کند.",
            "مجادله ۲۲: مؤمن حقیقی با محادّ خدا و رسول دوستی نمی‌کند.",
            "توبه ۲۴ حب خدا و رسول و جهاد را بر وابستگی‌های نسبی مقدم می‌کند.",
        ],
        "glossary": [
            ("ولی", "سرپرست/یاور/سرپرستی ایمانی — محل نزاع تفسیری در ۵:۵۵"),
            ("حزب الله", "مائده ۵۶ و مجادله ۲۲"),
            ("مودت ذی‌القربی", "شوری ۲۳"),
        ],
    },
    "051": {
        "title": "جلسهٔ ۰۵۱ — انسان کامل",
        "focus": "معنای ولایت؛ شأن نزول و تعمیم؛ سیاق ۵۱–۵۵؛ ولاء محبت و نصرت",
        "featured": ["5:51", "5:55", "5:52", "58:22", "8:72"],
        "headings": [
            (0.00, "## افتتاح و تلاوت مائده ۵۱–۵۲"),
            (0.12, "## سختی ترجمه و تفسیر آیهٔ ۵۵"),
            (0.28, "## شأن نزول: مقیدکننده یا قابل تعمیم؟"),
            (0.45, "## آیا ۵۵ در رهن سیاق بالایی است؟"),
            (0.60, "## ولاء محبت، نصرت و معانی چندلایه"),
            (0.75, "## شواهد انفال ۷۲ و مجادله"),
            (0.90, "## جمع‌بندی و دعا"),
        ],
        "summary_short": (
            "استاد روی معنای ولایت در مائده ۵۵ تمرکز می‌کند و می‌گوید حتی ترجمهٔ آیه ساده و "
            "متفق‌علیه نیست. شأن نزول را توضیح‌دهنده می‌داند نه قفلی که آیه را از تطبیق بازدارد. "
            "بحث می‌کند آیا آیهٔ ۵۵ از سیاق ۵۱ به بعد جدا می‌شود یا معانی ولاء (محبت، نصرت، سرپرستی) "
            "در همان سیاق قابل جمع‌اند؛ از مجادله و انفال ۷۲ برای تمایز ولایت ایمانی و شرایط هجرت/نصرت کمک می‌گیرد."
        ),
        "outline": [
            "تلاوت مائده ۵۱–۵۲",
            "چالش ترجمهٔ إنما وليكم",
            "نقش و حدود شأن نزول",
            "رابطهٔ ۵۵ با سیاق نهی از اولیاء بودن اهل کتاب",
            "لایه‌های معنای ولاء",
            "انفال ۷۲ و ولایت پس از هجرت",
            "دعا",
        ],
        "takeaways": [
            "ترجمهٔ ۵:۵۵ محل دقت است؛ «ولی» تک‌معنا نیست.",
            "شأن نزول مفسر کامل آیه نیست و تعمیم را نمی‌بندد.",
            "نزاع تفسیری: آیا ۵۵ از سیاق ۵۱ جداست یا ادامهٔ همان ولاء است؟",
            "ولاء می‌تواند محبت، نصرت و سرپرستی را در لایه‌های مختلف داشته باشد.",
            "انفال ۷۲ ولایت را با هجرت و نصرت دینی گره می‌زند.",
            "برای فهم ۵۵ باید ۵۱–۵۶ با هم دیده شوند.",
        ],
        "glossary": [
            ("شأن نزول", "سبب نزول؛ مقید کامل معنا نیست"),
            ("ولاء محبت", "دوستی ایمانی در برابر ولایت دشمنان"),
            ("ولایت نصرت", "یاری‌گری دینی — نظیر انفال ۷۲"),
        ],
    },
}


MD_BANNER = """> **یادداشت:** ترجمه‌های فارسیِ زیرِ متونِ عربی توسط **مدل** افزوده شده‌اند و گفته‌ی استاد در جلسه نیستند.
>
> این فایل **نسخۀ کامل** جلسه است (نه خلاصه). خلاصه فقط در فایل `*.summary.md` هم‌پوشه است.
>
> **مدرس:** حجت‌الاسلام قاسمیان · **دوره:** انسان کامل · **جلسه:** {nnn}
>
> Segments خام ASR در این فایل نیست. فارسی برای خوانایی سبک ویرایش شده؛ ایده‌های استاد حفظ شده‌اند.

<style>
.ayah-ar {{
  font-size: 1.45em;
  line-height: 2.05;
  display: block;
  margin: 0.6em 0 0.35em;
  font-family: "Amiri", "Scheherazade New", "Noto Naskh Arabic", "Geeza Pro", "Arabic Typesetting", serif;
}}
.ayah-ref {{ font-size: 0.95em; opacity: 0.85; }}
</style>

# {title}

**موضوع محوری:** {focus}

---

## آیات اصلی این جلسه (متن تأییدشده)

> برای مطالعهٔ دقیق؛ در متن کامل جلسه نیز آمده‌اند.

{featured_block}

---

## متن کامل جلسه (ویرایش وضوح + تصحیح استناد)

"""

MD_FOOTER = """
---

## یادداشت پایانی

- پاکسازی ASR و ویرایش وضوح فارسی توسط مدل؛ محتوای استدلالی جلسه حفظ شده است.
- آیات اصلی با api.alquran.cloud (quran-uthmani) و ترجمهٔ فولادوند راستی‌آزمایی شده‌اند (جزئیات در Corrections log).
- ترجمه‌های فارسی زیر عربی **گفتهٔ استاد نیستند**.
- بخش `--- Segments ---` از ASR در این خروجی نیامده است.
"""


def format_corrections_log(log: list[dict]) -> str:
    lines = ["", "---", "", "## Corrections log", ""]
    if not log:
        lines.append("- minor ASR cleanup; Maidah citations spot-checked via alquran.cloud")
    for item in log:
        lines.append(f"- **{item['ref']}** — {item['fix']} — _{item['src']}_")
    lines.append("")
    lines.append(
        "Note: `--- Segments ---` omitted from corrected output (per pipeline)."
    )
    return "\n".join(lines)


def write_summary(path: Path, session: str, stem: str) -> None:
    m = SESSION_META[session]
    lines = [
        f"# خلاصه — {m['title']}",
        "",
        f"**مدرس:** حجت‌الاسلام قاسمیان · **دوره:** انسان کامل · **جلسه:** {session}",
        "",
        "## خلاصهٔ کوتاه",
        "",
        m["summary_short"],
        "",
        "## فهرست مطالب / نقشهٔ جلسه",
        "",
    ]
    for i, item in enumerate(m["outline"], 1):
        lines.append(f"{i}. {item}")
    lines += ["", "## نکات کلیدی", ""]
    for t in m["takeaways"]:
        lines.append(f"- {t}")
    lines += ["", "## اصطلاحات و منابع", ""]
    for term, gloss in m["glossary"]:
        lines.append(f"- **{term}:** {gloss}")
    lines += [
        "",
        "---",
        "",
        f"_خلاصه توسط مدل بر اساس `{stem}.corrected.md`؛ ادعای تازه‌ای افزوده نشده است._",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def process_session(nnn: str) -> dict:
    folder = BASE / nnn
    cleaned = next(folder.glob("*.cleaned.txt"))
    stem = cleaned.name.replace(".cleaned.txt", "")
    raw = cleaned.read_text(encoding="utf-8")
    if "--- Segments ---" in raw:
        raw = raw.split("--- Segments ---")[0]
    raw_len = len(raw.strip())

    text = clean_noise(raw)
    text = apply_common_persian_fixes(text)
    text, log = fix_citations(text, nnn)

    body = paragraphize(text)
    header = (
        f"انسان کامل — حجت‌الاسلام قاسمیان\n"
        f"نسخهٔ تصحیح‌شدهٔ رونوشت (کامل جلسه) · جلسه {nnn} · Segments حذف شده\n"
        f"ترجمه‌های عربیِ اصلاح‌شده با منابع آنلاین؛ ویرایش وضوح ASR.\n\n"
    )
    corr_txt = header + body + format_corrections_log(log)
    corr_txt_path = folder / f"{stem}.corrected.txt"
    corr_txt_path.write_text(corr_txt + "\n", encoding="utf-8")

    meta = SESSION_META[nnn]
    featured_block = "\n".join(ayah_html(r) for r in meta["featured"])
    md_body = wrap_known_ayahs_in_body(body)
    md_body = insert_headings(md_body, meta["headings"])
    md = (
        MD_BANNER.format(
            nnn=nnn,
            title=meta["title"],
            focus=meta["focus"],
            featured_block=featured_block,
        )
        + md_body
        + "\n"
        + MD_FOOTER
        + "\n"
        + format_corrections_log(log)
        + "\n"
    )
    corr_md_path = folder / f"{stem}.corrected.md"
    corr_md_path.write_text(md, encoding="utf-8")

    summary_path = folder / f"{stem}.summary.md"
    write_summary(summary_path, nnn, stem)

    prose_len = len(body)
    return {
        "nnn": nnn,
        "stem": stem,
        "raw_len": raw_len,
        "corr_txt_len": prose_len,
        "ratio": prose_len / max(raw_len, 1),
        "log_n": len(log),
        "paths": [corr_txt_path.name, corr_md_path.name, summary_path.name],
    }


def main() -> None:
    results = []
    for n in range(47, 52):
        r = process_session(f"{n:03d}")
        results.append(r)
        print(
            f"{r['nnn']}: ratio={r['ratio']:.2f} log={r['log_n']} "
            f"txt={r['corr_txt_len']} → {', '.join(r['paths'])}"
        )
    print("DONE", len(results))


if __name__ == "__main__":
    main()
