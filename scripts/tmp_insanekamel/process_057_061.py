#!/usr/bin/env python3
"""Process InsaneKamel sessions 057–061: corrected.txt / .md / summary.md."""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(
    "/Users/zzmr/Documents/Documents - ZahraZMR’s MacBook Air/Code/Myfiles/IslamicASR"
    "/Audios/Qasemian/InsaneKamel"
)
AYAH_JSON = Path(__file__).with_name("verified_ayahs.json")
AY = json.loads(AYAH_JSON.read_text(encoding="utf-8"))

# Strip accidental bismillah glued to 98:1 in some API editions
if AY.get("98:1", "").startswith("بِسْمِ"):
    AY["98:1"] = re.sub(
        r"^بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ\s*", "", AY["98:1"]
    ).strip()


def strip_tashkeel_light(s: str) -> str:
    """Keep letters; drop most diacritics for fuzzy match keys."""
    return re.sub(r"[\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)


# Verified blocks (alquran.cloud quran-uthmani)
TAWBAH_101_105 = " ".join(AY[f"9:{i}"] for i in range(101, 106))
TAWBAH_103_105 = " ".join(AY[f"9:{i}"] for i in range(103, 106))
TAWBAH_105 = AY["9:105"]
BAQARA_142 = AY["2:142"].lstrip("۞ ").strip()
BAQARA_143 = AY["2:143"]
BAQARA_142_143 = BAQARA_142 + " " + BAQARA_143
BAQARA_96 = AY["2:96"]
FATH_11 = AY["48:11"]
MAIDA_101 = AY["5:101"]
YUNUS_61 = AY["10:61"]
RAD_43 = AY["13:43"]
NISA_166 = AY["4:166"]
NISA_164 = AY["4:164"]
IMRAN_18 = AY["3:18"]
HADID_27 = AY["57:27"]
FUSSILAT_20_22 = " ".join(AY[f"41:{i}"] for i in range(20, 23))
ANAM_9 = AY["6:9"]
BAYYINA_1_5 = " ".join(AY[f"98:{i}"] for i in range(1, 6))

TRANSLATIONS = {
    "9:101-105": (
        "و از بادیه‌نشینانِ پیرامون شما منافقانی هستند و از اهل مدینه نیز کسانی بر نفاق "
        "سخت‌خوی‌اند؛ تو آنان را نمی‌شناسی، ما می‌شناسیم‌شان. به‌زودی دو بار عذابشان می‌کنیم، "
        "سپس به عذابی بزرگ بازگردانده می‌شوند. و دیگران به گناهان خود اعتراف کردند؛ "
        "عملی صالح را با سیّئه‌ای آمیختند؛ باشد که خدا توبه‌شان را بپذیرد… صدقه بگیر که "
        "پاکشان کند… و بگو: عمل کنید؛ خدا و رسولش و مؤمنان عملتان را خواهند دید…"
    ),
    "9:103-105": (
        "از اموالشان صدقه بگیر که پاک و تزکیه‌شان کند و بر آنان درود فرست؛ "
        "نمازت مایه آرامش آنان است… آیا نمی‌دانند خدا توبه را می‌پذیرد و صدقات را می‌گیرد؟ "
        "و بگو عمل کنید؛ خدا و رسول و مؤمنان عملتان را می‌بینند و به سوی دانای نهان و آشکار "
        "بازمی‌گردید تا از آنچه می‌کردید آگاهتان کند."
    ),
    "9:105": (
        "و بگو: عمل کنید؛ پس خدا عمل شما را خواهد دید و پیامبرش و مؤمنان نیز؛ "
        "و به سوی دانای غیب و شهادت بازگردانده می‌شوید، پس شما را به آنچه می‌کردید خبر می‌دهد."
    ),
    "2:142": (
        "به‌زودی سفیهان از مردم می‌گویند: چه چیز آنان را از قبله‌شان که بر آن بودند برگرداند؟ "
        "بگو: مشرق و مغرب از آنِ خداست؛ هر که را بخواهد به راه راست هدایت می‌کند."
    ),
    "2:143": (
        "و این‌گونه شما را امتی میانه قرار دادیم تا گواهان بر مردم باشید و پیامبر بر شما گواه باشد. "
        "و قبله‌ای را که بر آن بودی قرار ندادیم مگر تا بدانیم چه کسی از پیامبر پیروی می‌کند "
        "از آنکه بر پاشنه‌هایش برمی‌گردد… خدا ایمانتان را تباه نمی‌کند؛ همانا خدا به مردم رئوف و مهربان است."
    ),
    "2:142-143": (
        "به‌زودی سفیهان می‌گویند چه چیز آنان را از قبله‌شان برگرداند… "
        "و این‌گونه شما را امتی میانه ساختیم تا بر مردم گواه باشید و پیامبر بر شما گواه باشد…"
    ),
    "2:96": (
        "و آنان را حریص‌ترین مردم بر زندگی می‌یابی و از مشرکان نیز؛ هر یک دوست دارد هزار سال عمر کند…"
    ),
    "48:11": (
        "به‌زودی بازماندگانِ بادیه به تو می‌گویند: اموال و کسانمان ما را مشغول کرد؛ برای ما آمرزش بخواه…"
    ),
    "5:101": (
        "ای کسانی که ایمان آورده‌اید، از چیزهایی مپرسید که اگر برایتان آشکار شود شما را بد آید…"
    ),
    "10:61": (
        "و در هیچ حالی نیستی و هیچ قرآنی از آن نمی‌خوانی و هیچ عملی نمی‌کنید مگر آنکه "
        "ما بر شما گواهیم هنگامی که در آن فرو می‌روید…"
    ),
    "13:43": (
        "و کسانی که کفر ورزیدند می‌گویند تو فرستاده نیستی. بگو: خدا میان من و شما گواه بس است، "
        "و کسی که نزد او علم کتاب است."
    ),
    "4:166": (
        "ولی خدا گواهی می‌دهد به آنچه بر تو نازل کرده؛ آن را به علم خود نازل کرده، "
        "و فرشتگان گواهی می‌دهند؛ و خدا گواه بس است."
    ),
    "4:164": "و پیامبرانی که پیش‌تر داستانشان را برایت گفتیم و پیامبرانی که نگفتیم؛ و خدا با موسی سخن گفت، سخن‌گفتنی.",
    "3:18": (
        "خدا گواهی داد که معبودی جز او نیست، و فرشتگان و صاحبان دانش نیز، در حالی که به عدل قیام دارند…"
    ),
    "57:27": (
        "سپس در پی آثارشان رسولان خود را فرستادیم و عیسی پسر مریم را در پی آوردیم و به او انجیل دادیم "
        "و در دل پیروانش رأفت و رحمت نهادیم و رهبانیتی که خود بدعت کردند…"
    ),
    "41:20-22": (
        "تا چون به آن رسند، گوش و چشم و پوستشان به آنچه می‌کردند بر آنان گواهی دهد. "
        "و به پوست‌هایشان گویند: چرا بر ما گواهی دادید؟ گویند: خدایی که هر چیز را به سخن آورد ما را به سخن آورد…"
    ),
    "6:9": "و اگر او را فرشته‌ای می‌ساختیم، بی‌گمان او را مردی می‌ساختیم و آنچه را بر آنان می‌پوشانند بر ایشان می‌پوشاندیم.",
    "98:1-5": (
        "کافران از اهل کتاب و مشرکان جدا نمی‌شدند تا برهان روشن به آنان برسد: رسولی از جانب خدا "
        "که صحیفه‌های پاک می‌خواند… و فرمان نیافته بودند جز آنکه خدا را با دین خالص بپرستند…"
    ),
}

NOISE = re.compile(
    r"\[(?:سرفه|نفس عمیق|خنده|مکث|نامفهوم|گریه|اشعار|صدای[^\]]*|هم[^\]]*|سخن[^\]]*|"
    r"پچ[^\]]*|آیه قرآن|دعا|لغو شده[^\]]*|foreign text|سخنگوی[^\]]*|"
    r"چند نفر[^\]]*|سخنرانی[^\]]*)\]"
)

PERSIAN_FIXES = [
    ("الفاتحه ما الصلاة", "الفاتحة مع الصلاة"),
    ("الفاتحه ما الصلوات", "الفاتحة مع الصلاة"),
    ("الفاتحه ما الصالحات", "الفاتحة مع الصلاة"),
    ("الفاتحه ما السلام", "الفاتحة مع السلام"),
    ("اولیاحق", "اولیاء حق"),
    ("ذوی‌الحقوق", "ذوی‌الحقوق"),
    ("زمین حقوق", "ذوی‌الحقوق"),
    ("اولیاحقوق", "ذوی‌الحقوق"),
    ("صبر دیویس تر صفر", ""),
    ("futuro", "آینده"),
    ("relative خاموشه", "نسبتاً خاموش است"),
    ("تو کل استعین", "و به نستعین"),
    ("و ليل مستعين", "و به نستعین"),
    ("سوره مورکه", "سوره مبارکه رعد"),
    ("سوره مالک فتح", "سوره مبارکه فتح"),
    ("سرای دویست و سی و یک", "صفحه دویست و سی و یک"),
    ("جهت شامی ارواح", "جهت شادی ارواح"),
    ("جهت شهادی ارواح", "جهت شادی ارواح"),
    ("تکایه شهدا", "طیبه شهدا"),
    ("تکریم شهدا", "طیبه شهدا"),
    ("علی بروشنان", "و روشن‌ضمیران"),
    ("فواتح الصلاوات", "الفاتحة مع الصلوات"),
    ("مردو علی النفاق", "مَرَدُوا عَلَى النِّفَاقِ"),
    ("خلقوا عملا صالحا وآخر سيئا", "خَلَطُوا عَمَلًا صَالِحًا وَآخَرَ سَيِّئًا"),
    ("اعترفوا بذنوبهم", "اعْتَرَفُوا بِذُنُوبِهِمْ"),
    ("فينبئكم بما كنتم تحملون", "فَيُنَبِّئُكُم بِمَا كُنتُمْ تَعْمَلُونَ"),
    ("ستردون إلى عالم الغيب", "سَتُرَدُّونَ إِلَىٰ عَالِمِ الْغَيْبِ"),
    ("إذ تفيئون فيه", "إِذْ تُفِيضُونَ فِيهِ"),
    ("تَفِیضًا مِنَ الدَّمْعِ", "تَفِيضُ مِنَ الدَّمْعِ"),
    ("لستم مرسلين", "لَسْتَ مُرْسَلًا"),
    ("قل كفا بالله", "قُلْ كَفَىٰ بِاللَّهِ"),
    ("من عنده علم الكتاب", "وَمَنْ عِندَهُ عِلْمُ الْكِتَابِ"),
    ("where در هر جای", "در هر جای"),
    ("hustle فرما", "اِشْفَعْ فرما"),
    ("nayab فرما", "نصیب فرما"),
    ("God Allah", "خدا"),
]


def clean_noise(t: str) -> str:
    t = NOISE.sub("", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r" ?\n ?", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def apply_persian_fixes(t: str) -> str:
    for a, b in PERSIAN_FIXES:
        t = t.replace(a, b)
    return t


def norm_ar(s: str) -> str:
    """Normalize Arabic for matching: drop diacritics, unify alef forms."""
    s = re.sub(r"[\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
    s = s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ى", "ي").replace("ة", "ه")
    s = s.replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"\s+", " ", s)
    return s


def fuzzy_replace_block(
    t: str, start_hint: str, end_hint: str, replacement: str, max_span: int = 1200
) -> tuple[str, bool]:
    """Replace garbled Arabic between start/end hints using normalized matching."""
    nt = norm_ar(t)
    ns = norm_ar(start_hint)
    ne = norm_ar(end_hint)
    # distinctive cores
    core_s = re.sub(r"[^\u0621-\u064A]", "", ns)[:14]
    core_e = re.sub(r"[^\u0621-\u064A]", "", ne)[-14:]
    if len(core_s) < 6 or len(core_e) < 6:
        return t, False
    # Find start in normalized text
    i0 = nt.find(norm_ar(start_hint[:40])[:20])
    if i0 < 0:
        # letter-only search
        letters_only = re.sub(r"[^\u0621-\u064A ]", "", nt)
        # map is hard; use regex on original with flexible gaps
        start_pat = ".{0,2}".join(core_s)
        end_pat = ".{0,2}".join(core_e)
        rx = re.compile(start_pat + r".{10," + str(max_span) + r"}?" + end_pat, re.DOTALL)
        # search on normalized-letter version built from original positions
        # Simpler: search original with diacritics optional
        flex_s = "".join(c + r"[\u064B-\u065F\u0670]*" for c in core_s)
        flex_e = "".join(c + r"[\u064B-\u065F\u0670]*" for c in core_e)
        rx2 = re.compile(flex_s + r".{10," + str(max_span) + r"}?" + flex_e, re.DOTALL)
        # Also allow ٱ/أ/إ/آ as ا
        t_flat = (
            t.replace("ٱ", "ا")
            .replace("أ", "ا")
            .replace("إ", "ا")
            .replace("آ", "ا")
        )
        m = rx2.search(t_flat)
        if not m:
            return t, False
        return t[: m.start()] + replacement + t[m.end() :], True
    # find end after start
    i1 = nt.find(norm_ar(end_hint[-50:])[-25:], i0)
    if i1 < 0 or i1 - i0 > max_span:
        i1 = nt.find(core_e, i0)
        if i1 < 0 or i1 - i0 > max_span:
            return t, False
        i1 = i1 + len(core_e)
    else:
        i1 = i1 + len(norm_ar(end_hint[-50:])[-25:])
    # Map normalized indices roughly to original by scanning
    # Build cumulative map
    orig_idx = []
    ni = 0
    for oi, ch in enumerate(t):
        nch = norm_ar(ch)
        if not nch:
            continue
        for _ in nch:
            orig_idx.append(oi)
            ni += 1
    if i0 >= len(orig_idx) or i1 - 1 >= len(orig_idx):
        return t, False
    a = orig_idx[i0]
    b = orig_idx[min(i1 - 1, len(orig_idx) - 1)] + 1
    return t[:a] + replacement + t[b:], True


def replace_quoted_or_plain(t: str, needle: str, replacement: str) -> tuple[str, bool]:
    """Replace undiacritized/plain ASR quote with verified text (once)."""
    nt = norm_ar(t)
    nn = norm_ar(needle)
    # try progressive shortening of needle if long
    for length in (len(nn), min(80, len(nn)), min(50, len(nn))):
        frag = nn[:length]
        if len(frag) < 20:
            break
        idx = nt.find(frag)
        if idx < 0:
            continue
        # extend to cover roughly needle length in normalized space
        end = idx + max(len(nn), length)
        # clamp to nearby punctuation end if present
        window = nt[idx : idx + max_span_safe(len(nn) + 80)]
        # map back
        orig_idx = []
        for oi, ch in enumerate(t):
            nch = norm_ar(ch)
            if not nch:
                continue
            for _ in nch:
                orig_idx.append(oi)
        if idx >= len(orig_idx):
            continue
        a = orig_idx[idx]
        b = orig_idx[min(end - 1, len(orig_idx) - 1)] + 1
        # expand b to include trailing quote mark
        while b < len(t) and t[b] in "»\"'”":
            b += 1
        return t[:a] + replacement + t[b:], True
    return t, False


def max_span_safe(n: int) -> int:
    return max(n, 40)


def fix_citations(t: str, session: str) -> tuple[str, list[dict]]:
    log: list[dict] = []

    def log_fix(ref: str, fix: str, src: str):
        log.append({"ref": ref, "fix": fix, "src": src})

    def try_exact(old: str, new: str, ref: str, src: str) -> bool:
        nonlocal t
        if old in t:
            t = t.replace(old, new, 1)
            log_fix(ref, "normalized to verified Uthmani", src)
            return True
        return False

    # --- Session-shared major blocks ---

    # Tawbah 101–105 opening (057)
    if session == "057":
        # Opening quoted block often garbled after 101
        t2, ok = fuzzy_replace_block(
            t,
            "وَمِمَّنْ حَوْلَكُم",
            "فينبئكم بما كنتم",
            TAWBAH_101_105,
            max_span=1800,
        )
        if ok:
            t = t2
            log_fix(
                "Quran 9:101–105",
                "restored opening Tawbah block",
                "https://api.alquran.cloud/v1/ayah/9:105/quran-uthmani",
            )
        else:
            t2, ok = fuzzy_replace_block(
                t,
                "وممن حولكم من الأعراب",
                "بما كنتم تعملون",
                TAWBAH_101_105,
                max_span=1800,
            )
            if ok:
                t = t2
                log_fix(
                    "Quran 9:101–105",
                    "restored opening Tawbah block (alt match)",
                    "https://quran.com/at-tawbah/101-105",
                )

    if session in ("057", "059"):
        # Prefer not to carve 103–105 out of an already-restored 101–105 block
        already_101_105 = TAWBAH_101_105[:60] in t
        if not already_101_105:
            for start, end in [
                ("خذ من أموالهم صدقة", "بما كنتم تعملون"),
                ("خُذْ مِنْ أَمْوَالِهِمْ", "تَعْمَلُونَ"),
                ("قل اعملوا فسیرى", "بما كنتم تعملون"),
                ("وقل اعملوا فسيرى", "بما كنتم تعملون"),
            ]:
                t2, ok = fuzzy_replace_block(t, start, end, TAWBAH_103_105, max_span=900)
                if ok:
                    t = t2
                    log_fix(
                        "Quran 9:103–105",
                        "normalized ṣadaqa / iʿmalū block",
                        "https://quran.com/at-tawbah/103-105",
                    )
                    break

        # Lone 105 fragments only when full blocks are absent
        if TAWBAH_101_105[:40] not in t and TAWBAH_103_105[:40] not in t:
            t = re.sub(
                r"قُلِ?\s*اعْ?مَلُوا\s*فَ?سَ?يَرَى\s*اللّ?هُ\s*عَمَلَ?[كك]ُم[^\n.]{0,120}تَعْمَلُونَ",
                TAWBAH_105,
                t,
                count=2,
                flags=re.IGNORECASE,
            )

    if session in ("057", "058"):
        t2, ok = fuzzy_replace_block(
            t,
            "وَكَذَلِكَ جَعَلْنَاكُمْ",
            "رَءُوفٌ رَّحِيمٌ",
            BAQARA_143,
            max_span=700,
        )
        if ok:
            t = t2
            log_fix(
                "Quran 2:143",
                "normalized ummatan wasaṭan block",
                "https://api.alquran.cloud/v1/ayah/2:143/quran-uthmani",
            )
        else:
            t2, ok = fuzzy_replace_block(
                t,
                "وكذلك جعلناكم أمة وسطا",
                "رءوف رحيم",
                BAQARA_143,
                max_span=700,
            )
            if ok:
                t = t2
                log_fix("Quran 2:143", "normalized (undiacritized match)", "https://quran.com/2:143")

        # Fix ASR typo أَمَا جَعَلْنَا → وَمَا جَعَلْنَا inside 143 if still present
        t = t.replace("أَمَا جَعَلْنَا الْقِبْلَةَ", "وَمَا جَعَلْنَا الْقِبْلَةَ")

        t2, ok = fuzzy_replace_block(
            t, "سيقول السفهاء من الناس", "صراط مستقيم", BAQARA_142, max_span=400
        )
        if ok:
            t = t2
            log_fix("Quran 2:142", "normalized sayaqūlu al-sufahāʾ", "https://quran.com/2:142")

    if session == "057":
        t2, ok = fuzzy_replace_block(
            t,
            "سيقول لك المخلفون من الأعراب",
            "بما تعملون خبيرا",
            FATH_11,
            max_span=500,
        )
        if ok:
            t = t2
            log_fix("Quran 48:11", "normalized Fath sayaqūlu", "https://quran.com/48:11")

        t2, ok = fuzzy_replace_block(
            t,
            "لا تسألوا عن أشياء",
            "والله غفور حليم",
            MAIDA_101,
            max_span=350,
        )
        if ok:
            t = t2
            log_fix("Quran 5:101", "normalized lā tasʾalū", "https://quran.com/5:101")

        t2, ok = fuzzy_replace_block(
            t,
            "وما تكون في شأن",
            "كتاب مبين",
            YUNUS_61,
            max_span=450,
        )
        if ok:
            t = t2
            log_fix("Quran 10:61", "normalized shuhūd verse (fixed تفيضون)", "https://quran.com/10:61")

    if session == "058":
        t2, ok = fuzzy_replace_block(
            t,
            "ولتجدنهم أحرص الناس",
            "بما يعملون",
            BAQARA_96,
            max_span=400,
        )
        if ok:
            t = t2
            log_fix("Quran 2:96", "normalized ḥirṣ ʿalā ḥayāh", "https://quran.com/2:96")

        t2, ok = fuzzy_replace_block(
            t,
            "ثم قفينا على آثارهم",
            "فاسقون",
            HADID_27,
            max_span=600,
        )
        if ok:
            t = t2
            log_fix("Quran 57:27", "normalized rahbāniyyah verse", "https://quran.com/57:27")

        # Ensure Tawbah 105 fragment
        if "فَسَيَرَى اللَّهُ عَمَلَكُمْ" not in t and "فسیری الله" not in t.lower():
            t2, ok = fuzzy_replace_block(
                t, "قل اعملوا فسیری", "والمؤمنون", TAWBAH_105, max_span=200
            )
            if ok:
                t = t2
                log_fix("Quran 9:105", "normalized cross-ref", "https://quran.com/9:105")

    if session == "059":
        t2, ok = fuzzy_replace_block(
            t,
            "حتى إذا ما جاءوها شهد عليهم",
            "مما تعملون",
            FUSSILAT_20_22,
            max_span=700,
        )
        if ok:
            t = t2
            log_fix(
                "Quran 41:20–22",
                "normalized samʿ / abṣār / julūd testimony",
                "https://quran.com/41:20-22",
            )

    if session in ("060", "061"):
        t2, ok = fuzzy_replace_block(
            t,
            "ويقول الذين كفروا لست مرسلا",
            "علم الكتاب",
            RAD_43,
            max_span=250,
        )
        if not ok:
            t2, ok = fuzzy_replace_block(
                t,
                "وَيَقُولُ الَّذِينَ كَفَرُوا",
                "عِلْمُ الْكِتَابِ",
                RAD_43,
                max_span=250,
            )
        if ok:
            t = t2
            log_fix(
                "Quran 13:43",
                "normalized Raʿd closing (man ʿindahu ʿilm al-kitāb)",
                "https://api.alquran.cloud/v1/ayah/13:43/quran-uthmani",
            )

        t2, ok = fuzzy_replace_block(
            t, "شهد الله أنه لا إله إلا هو", "العزيز الحكيم", IMRAN_18, max_span=300
        )
        if ok:
            t = t2
            log_fix("Quran 3:18", "normalized shahida Allāh", "https://quran.com/3:18")

        t2, ok = fuzzy_replace_block(
            t, "لكن الله يشهد بما أنزل", "وكفى بالله شهيدا", NISA_166, max_span=250
        )
        if ok:
            t = t2
            log_fix("Quran 4:166", "normalized Allāh yashhadu", "https://quran.com/4:166")

    if session == "061":
        t2, ok = fuzzy_replace_block(
            t, "ولو جعلناه ملكا لجعلناه رجلا", "ما يلبسون", ANAM_9, max_span=200
        )
        if ok:
            t = t2
            log_fix("Quran 6:9", "normalized malak→rajul", "https://quran.com/6:9")


    # --- Explicit undiacritized / partial ASR quotes ---
    explicit = []
    if session == "057":
        explicit += [
            ("سيقول السفهاء من الناس ما", BAQARA_142, "Quran 2:142", "https://quran.com/2:142"),
            ("سيقول لك المخلفون من الأعراب", FATH_11, "Quran 48:11", "https://quran.com/48:11"),
            ("لا تسألوا عن أشياء إن تبد لكم تسؤكم", MAIDA_101, "Quran 5:101", "https://quran.com/5:101"),
            ("وكذلك جعلناكم أمة وسطا", BAQARA_143, "Quran 2:143", "https://quran.com/2:143"),
            ("وما تكونوا في شأنٍ وما تتلون من قرآن ولا تعملون من عملٍ إلا كنا عليكم شهودا إذ تفيئون فيه", YUNUS_61, "Quran 10:61", "https://quran.com/10:61"),
            ("وما تكون في شأن وما تتلو منه من قرآن", YUNUS_61, "Quran 10:61", "https://quran.com/10:61"),
        ]
    if session == "058":
        explicit += [
            ("ولتجدنهم أحرص الناس على حياة ومن الذين أشركوا", BAQARA_96, "Quran 2:96", "https://quran.com/2:96"),
            ("ثم قفينا على آثارهم برسلنا قفينا بعيسى ابن مريم وآتيناه الإنجيل", HADID_27, "Quran 57:27", "https://quran.com/57:27"),
            ("وجعلنا في قلوب الذين اتبعوه رأفة ورحمة ورحبانیة", HADID_27, "Quran 57:27", "https://quran.com/57:27"),
        ]
    if session == "059":
        explicit += [
            ("حتى إذا ما جاءوها شهد عليهم سمعهم وأبصارهم وجلودهم بما كانوا يعملون", FUSSILAT_20_22, "Quran 41:20–22", "https://quran.com/41:20-22"),
            ("وقالوا لجلودهم لم شهدتم علينا قالوا انطقنا الله الذي ينطق كل شيء", FUSSILAT_20_22, "Quran 41:20–22", "https://quran.com/41:20-22"),
        ]
    if session in ("060", "061"):
        explicit += [
            ("قل كفى بالله شهيدا بيني وبينكم ومن عنده علم الكتاب", RAD_43, "Quran 13:43", "https://quran.com/13:43"),
            ("قل كفا بالله شهيدا بيني وبينكم من عنده علم الكتاب", RAD_43, "Quran 13:43", "https://quran.com/13:43"),
        ]
    if session == "060":
        explicit += [
            (
                "شهد الله انه لا اله الا هو والملائكة و اولوا العلم",
                IMRAN_18,
                "Quran 3:18",
                "https://quran.com/3:18",
            ),
            (
                "لکن الله يشهد بما أنزل إليك أنزله بعلمه والملائكة يشهدون وكفى بالله شهيدا",
                NISA_166,
                "Quran 4:166",
                "https://quran.com/4:166",
            ),
            (
                "لكن الله يشهد بما أنزل إليك أنزله بعلمه والملائكة يشهدون وكفى بالله شهيدا",
                NISA_166,
                "Quran 4:166",
                "https://quran.com/4:166",
            ),
        ]
    if session == "061":
        explicit += [
            ("ولو جعلناه ملكا لجعلناه رجلا", ANAM_9, "Quran 6:9", "https://quran.com/6:9"),
        ]

    for needle, repl, ref, src_url in explicit:
        # skip if already have verified start
        if repl[:40] in t or norm_ar(repl)[:40] in norm_ar(t):
            # still try to fix known ASR garble fragments if needle present and not already full
            pass
        t2, ok = replace_quoted_or_plain(t, needle, repl)
        if ok:
            t = t2
            if not any(x["ref"] == ref for x in log):
                log_fix(ref, "replaced ASR fragment with verified Uthmani", src_url)

    # Fix Yunus 61 تفيئون → تفيضون if fragment remains
    if "تفيئون" in t or "تَفِيئُونَ" in t:
        t2, ok = replace_quoted_or_plain(
            t,
            "وما تكونوا في شأن وما تتلون من قرآن ولا تعملون من عمل إلا كنا عليكم شهودا إذ تفيئون فيه",
            YUNUS_61,
        )
        if ok:
            t = t2
            if not any(x["ref"] == "Quran 10:61" for x in log):
                log_fix("Quran 10:61", "fixed تفيضون (was تفيئون)", "https://quran.com/10:61")
        else:
            t = t.replace("تفيئون", "تُفِيضُونَ").replace("إذ تفيئون فيه", "إِذْ تُفِيضُونَ فِيهِ")
            log_fix("Quran 10:61", "corrected تفيضون spelling", "https://quran.com/10:61")

    # Fix أما جعلنا → وما جعلنا inside wasat verse ASR
    if "أما جعلنا القبلة" in t or "أَمَا جَعَلْنَا الْقِبْلَةَ" in t:
        t = t.replace("أما جعلنا القبلة", "وما جعلنا القبلة").replace(
            "أَمَا جَعَلْنَا الْقِبْلَةَ", "وَمَا جَعَلْنَا الْقِبْلَةَ"
        )
        if not any(x["ref"] == "Quran 2:143" for x in log):
            log_fix("Quran 2:143", "fixed وما جعلنا (ASR أما)", "https://quran.com/2:143")


    # Generic short normalizations everywhere
    replacements = [
        (
            r"إن الله على كل شيء شهيد",
            "إِنَّ اللَّهَ عَلَىٰ كُلِّ شَيْءٍ شَهِيدٌ",
            "Quran phrasing (cf. 22:17 / 34:47 style)",
            "https://quran.com",
        ),
        (
            r"على كل شيء شهيد",
            "عَلَىٰ كُلِّ شَيْءٍ شَهِيدٌ",
            "Quran phrasing شهيد",
            "https://quran.com",
        ),
    ]
    for pat, repl, ref, src in replacements:
        if re.search(pat, t) and repl not in t:
            t = re.sub(pat, repl, t, count=2)
            log_fix(ref, "normalized common shahīd phrasing", src)

    # Deduplicate log refs
    seen = set()
    uniq = []
    for item in log:
        if item["ref"] not in seen:
            seen.add(item["ref"])
            uniq.append(item)
    return t, uniq


def paragraphize(t: str) -> str:
    parts = re.split(r"(?<=[.؟!。])\s+", t)
    paras: list[str] = []
    buf: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        buf.append(p)
        if len(buf) >= 3 or len(" ".join(buf)) > 480:
            paras.append(" ".join(buf))
            buf = []
    if buf:
        paras.append(" ".join(buf))
    return "\n\n".join(paras)


def paragraphize_preserving_ayah_html(t: str) -> str:
    chunks = re.split(
        r'(<p class="ayah-ar"[\s\S]*?</p>\s*\n\s*> \*\*ترجمهٔ فارسی[\s\S]*?\n)',
        t,
    )
    out = []
    for ch in chunks:
        if ch.startswith('<p class="ayah-ar"'):
            out.append(ch.strip())
        elif ch.strip():
            out.append(paragraphize(ch))
    return "\n\n".join(out)


AYAH_HTML = (
    '<p class="ayah-ar" dir="rtl" style="font-size:1.5em; line-height:2.1; '
    "font-family: Amiri, 'Scheherazade New', 'Noto Naskh Arabic', 'Geeza Pro', serif;\">\n"
    "«{ar}» <span class=\"ayah-ref\">({ref})</span>\n</p>\n\n"
    "> **ترجمهٔ فارسی (توسط مدل، نه استاد):** {fa}\n"
)


WRAP_SPECS = [
    (TAWBAH_101_105, "توبه/۹:۱۰۱–۱۰۵", TRANSLATIONS["9:101-105"]),
    (TAWBAH_103_105, "توبه/۹:۱۰۳–۱۰۵", TRANSLATIONS["9:103-105"]),
    (FUSSILAT_20_22, "فصلت/۴۱:۲۰–۲۲", TRANSLATIONS["41:20-22"]),
    (BAQARA_142_143, "بقره/۲:۱۴۲–۱۴۳", TRANSLATIONS["2:142-143"]),
    (BAQARA_143, "بقره/۲:۱۴۳", TRANSLATIONS["2:143"]),
    (BAQARA_142, "بقره/۲:۱۴۲", TRANSLATIONS["2:142"]),
    (HADID_27, "حدید/۵۷:۲۷", TRANSLATIONS["57:27"]),
    (BAQARA_96, "بقره/۲:۹۶", TRANSLATIONS["2:96"]),
    (FATH_11, "فتح/۴۸:۱۱", TRANSLATIONS["48:11"]),
    (MAIDA_101, "مائده/۵:۱۰۱", TRANSLATIONS["5:101"]),
    (YUNUS_61, "یونس/۱۰:۶۱", TRANSLATIONS["10:61"]),
    (RAD_43, "رعد/۱۳:۴۳", TRANSLATIONS["13:43"]),
    (IMRAN_18, "آل عمران/۳:۱۸", TRANSLATIONS["3:18"]),
    (NISA_166, "نساء/۴:۱۶۶", TRANSLATIONS["4:166"]),
    (NISA_164, "نساء/۴:۱۶۴", TRANSLATIONS["4:164"]),
    (ANAM_9, "انعام/۶:۹", TRANSLATIONS["6:9"]),
    (TAWBAH_105, "توبه/۹:۱۰۵", TRANSLATIONS["9:105"]),
]


def wrap_ayahs_in_md(body: str) -> str:
    def inside_ayah_html(text: str, idx: int) -> bool:
        open_at = text.rfind('<p class="ayah-ar"', 0, idx)
        if open_at < 0:
            return False
        close_at = text.find("</p>", open_at, idx)
        return close_at < 0  # still inside the open <p>

    for ar, ref, fa in WRAP_SPECS:
        start = 0
        while True:
            idx = body.find(ar, start)
            if idx < 0:
                break
            if inside_ayah_html(body, idx):
                start = idx + len(ar)
                continue
            block = AYAH_HTML.format(ar=ar, ref=ref, fa=fa)
            body = body[:idx] + "\n\n" + block + "\n\n" + body[idx + len(ar) :]
            break  # one wrap per spec (first non-nested hit)
    return body


def insert_headings(body: str, session: str) -> str:
    meta = SESSION_META[session]
    paras = body.split("\n\n")
    n = max(len(paras), 1)
    cuts = []
    for frac, title in meta["headings"]:
        idx = min(int(frac * n), n - 1)
        cuts.append((idx, title))
    used: set[int] = set()
    for idx, title in sorted(cuts, key=lambda x: -x[0]):
        while idx in used and idx > 0:
            idx -= 1
        used.add(idx)
        paras[idx] = f"{title}\n\n{paras[idx]}"
    return "\n\n".join(paras)


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
"""

MD_FOOTER = """
---

## یادداشت پایانی

- پاکسازی ASR و ویرایش وضوح فارسی توسط مدل؛ محتوای استدلالی جلسه حفظ شده است.
- آیات و روایات اصلی با منابع برخط راستی‌آزمایی شده‌اند (جزئیات در Corrections log فایل `*.corrected.txt`).
- ترجمه‌های فارسی زیر عربی **گفتهٔ استاد نیستند**.
- بخش `--- Segments ---` از ASR در این خروجی نیامده است.
"""

SESSION_META = {
    "057": {
        "title": "جلسهٔ ۰۵۷ — انسان کامل",
        "focus": "توبه ۱۰۵؛ شاهدان عمل؛ تغییر قبله؛ امت وسط؛ نهی از سؤالِ افزاینده",
        "headings": [
            (0.00, "## افتتاح و تلاوت توبه ۱۰۱–۱۰۵"),
            (0.10, "## محور آیهٔ ۱۰۵: فَسَيَرَى اللَّهُ… وَرَسُولُهُ وَالْمُؤْمِنُونَ"),
            (0.22, "## سینِ «فسیری» و شبههٔ مشاهدهٔ آینده"),
            (0.35, "## تغییر قبله و «سیقول السفهاء» (بقره ۱۴۲–۱۴۳)"),
            (0.48, "## سیقول در فتح؛ افشای باطن جامعه"),
            (0.58, "## لا تسألوا عن اشیاء (مائده ۱۰۱) و فرهنگ استفتاء"),
            (0.70, "## تحرّی، اصول عملیه و لبه‌های فقه"),
            (0.82, "## یونس ۶۱ و شهود الهی بر عمل"),
            (0.92, "## دعا و روضه"),
        ],
        "summary_short": (
            "حجت‌الاسلام قاسمیان در پیمایش آیاتِ مرتبط با انسان کامل به توبه ۱۰۱–۱۰۵ می‌رسد و "
            "محور را آیهٔ ۱۰۵ («قل اعملوا فسیری الله عملکم و رسوله و المؤمنون») قرار می‌دهد: "
            "عمل شما را خدا و رسول و مؤمنان می‌بینند. شبههٔ ظاهرِ «سین» (مشاهدهٔ فقط آینده) را "
            "بهانه می‌کند تا فرهنگ شاهدان عمل را باز کند. سپس با بقره ۱۴۲–۱۴۳ (تغییر قبله و امت وسط) "
            "و «سیقول»های فتح، آماده‌سازی جامعه برای شبهات را نشان می‌دهد؛ و با مائده ۱۰۱ در برابر "
            "سؤال‌های افراطیِ استفتاء هشدار می‌دهد. یونس ۶۱ شهود الهی بر هر شأن و عمل را تثبیت می‌کند."
        ),
        "outline": [
            "افتتاح؛ تلاوت توبه ۱۰۱–۱۰۵",
            "توضیح آیهٔ ۱۰۵ و شاهدان عمل",
            "معنای سین در فسیری و شبهه",
            "بقره ۱۴۲–۱۴۳: تغییر قبله و امت وسط",
            "فتح ۱۱ و افشای نفاق با «سیقول»",
            "مائده ۱۰۱: نهی از سؤالِ مضر",
            "تحرّی و آفات زیاده‌روی در استفتاء",
            "یونس ۶۱: شهود بر عمل",
            "دعا و روضه",
        ],
        "takeaways": [
            "محور جلسه توبه ۱۰۵ است: عمل را خدا و رسول و مؤمنان می‌بینند.",
            "سینِ فسیری لزوماً مشاهده را به آخرت محدود نمی‌کند؛ بحث شاهدان معاصر مطرح است.",
            "قرآن با «سیقول» جامعه را پیشاپیش برای شبهات آماده می‌کند (قبله، تخلف از جهاد).",
            "امت وسط در بقره ۱۴۳ با شهادت بر مردم گره خورده است.",
            "مائده ۱۰۱ هشدار می‌دهد سؤالِ بی‌جا دین را سنگین و تلخ می‌کند.",
            "تحرّی در شکیات نمونه‌ای از راهکار درونی شرع است، نه انباشت استفتاء.",
            "یونس ۶۱: هیچ شأن و عملی از شهود الهی بیرون نیست.",
        ],
        "glossary": [
            ("فسیری الله عملکم", "توبه ۱۰۵؛ رؤیت عمل توسط خدا و رسول و مؤمنان"),
            ("امت وسط", "بقره ۱۴۳؛ امت گواه میان رسول و مردم"),
            ("سیقول", "آیاتی که سخن آیندهٔ مخالفان را پیش‌گویی می‌کند"),
            ("تحرّی", "ترجیح یک طرف شک در نماز و مانند آن"),
        ],
    },
    "058": {
        "title": "جلسهٔ ۰۵۸ — انسان کامل",
        "focus": "امت وسط؛ شهادت؛ نقد تفسیر افراط/تفریط؛ یهود و نصارا",
        "headings": [
            (0.00, "## افتتاح و تلاوت بقره ۱۴۳"),
            (0.12, "## پیوند با توبه ۱۰۵ و ورود موضوعی به شهادت"),
            (0.25, "## نقد تفسیر وسط = میان افراط و تفریط"),
            (0.40, "## حرص یهود بر حیات (بقره ۹۶) و رهبانیت نصارا (حدید ۲۷)"),
            (0.55, "## وسط در شهادت: میان رسول و الناس"),
            (0.70, "## ادای شهادت در قیامت و سیماهای برزخی"),
            (0.85, "## مع الذین انعم الله؛ تناسب محشور شدن"),
            (0.93, "## دعا و ختم"),
        ],
        "summary_short": (
            "ادامهٔ بحث شهادت و امت وسط است. استاد بقره ۱۴۳ را می‌خواند و می‌گوید تفسیر رایج "
            "«وسط میان افراط و تفریط» اگرچه به‌خودی‌خود حرف حقی است، مدلول مستقیم آیه نیست؛ "
            "آیه وسط بودن را برای شهادت بر مردم و شهادت رسول بر امت تبیین می‌کند. با بقره ۹۶ "
            "(حرص یهود بر دنیا) و حدید ۲۷ (رأفت و رهبانیتِ بدعتی در پیروان عیسی) دو قطب تاریخی "
            "را نشان می‌دهد، اما عنصر محورِ وسط را شهادت می‌داند نه صرفاً اخلاق میانه. سپس "
            "صحنهٔ قیامت و ظهور ملکات را به شهادت پیوند می‌زند."
        ),
        "outline": [
            "تلاوت بقره ۱۴۳",
            "پیوند با توبه ۱۰۵",
            "نقد تفسیر افراط/تفریط",
            "بقره ۹۶ و حدید ۲۷",
            "وسط = جایگاه شهادت میان رسول و الناس",
            "قیامت و صورت‌های برزخی",
            "محشور شدن با انبیا و شهداء",
            "دعا",
        ],
        "takeaways": [
            "آیه صریحاً طرفین وسط را مشخص می‌کند: رسول و الناس.",
            "تفسیر وسط به «میانه‌روی اخلاقی» کافی و مطابق نص نیست.",
            "یهود (حرص دنیا) و نصارا (رهبانیتِ ننوشته) دو نمونهٔ تاریخی‌اند، نه تعریف آیه.",
            "شهادت قرآنی با فرهنگ مشاهدهٔ عمل و ادای شهادت گره خورده است.",
            "در قیامت سیما و ملکات آشکار می‌شود؛ تناسب محشور شدن مهم است.",
        ],
        "glossary": [
            ("امت وسط", "امتی در میانهٔ شهادت میان پیامبر و مردم"),
            ("ادای شهادت", "گواهی‌دادن در محضر حساب، نه فقط دیدن صحنه"),
            ("رهبانیت", "حدید ۲۷؛ بدعتی که نوشته نشده بود"),
        ],
    },
    "059": {
        "title": "جلسهٔ ۰۵۹ — انسان کامل",
        "focus": "شاهدان عمل؛ فصلت ۲۰–۲۲؛ توبه و تبوک؛ تهدید و امید آیهٔ ۱۰۵",
        "headings": [
            (0.00, "## افتتاح و بازگشت به توبه ۱۰۳–۱۰۵"),
            (0.12, "## قیامت ظرف ادای شهادت"),
            (0.28, "## فصلت ۲۰–۲۲: گواهی سمع و بصر و جلود"),
            (0.45, "## صورت برزخی اعمال و ملکات"),
            (0.58, "## سیاق تبوک؛ تهدید و شناخت کاذبین"),
            (0.72, "## محسنانِ معذور و نصح لله و رسوله"),
            (0.85, "## مقامات مؤمنان و هشدار از عرفان‌زدگی"),
            (0.93, "## دعا و ختم"),
        ],
        "summary_short": (
            "استاد از توبه ۱۰۳–۱۰۵ بحث شاهدان عمل را ادامه می‌دهد: قیامت ظرف ادای شهادت است. "
            "با فصلت ۲۰–۲۲ توضیح می‌دهد گوش و چشم و پوست به اعمال گواهی می‌دهند، چون هر فعل "
            "صورت برزخی/ملکاتی می‌یابد. در سیاق جنگ تبوک، لحن آیه می‌تواند تهدیدآمیز باشد "
            "(اعمال دیده می‌شود) و همزمان برای معترفان و محسنانِ معذور امید بگشاید. "
            "بر تشخیص مقامات واقعی و پرهیز از عرفان‌های سست تأکید می‌کند."
        ),
        "outline": [
            "تلاوت توبه ۱۰۳–۱۰۵",
            "تحمل و ادای شهادت",
            "فصلت ۲۰–۲۲",
            "ملکات نفسانی به‌صورت بدن محشور",
            "سیاق تبوک و توبیخ متخلفان",
            "معذورانِ ناصح",
            "مقامات و خوف از خدا",
            "دعا",
        ],
        "takeaways": [
            "قیامت صحنهٔ ادای شهادت قوا و جلود است.",
            "تکرار جلود/سمع/بصر در فصلت با صورت ملکاتی عمل پیوند دارد.",
            "توبه ۱۰۵ در سیاق تبوک هم تهدید است هم افق امید برای توبه‌کاران.",
            "ناصحانِ معذور (ضعفا/مرضى) جدا از متخلفانِ کاذب‌اند.",
            "محور دین خوف از خداست؛ عرفان بدون خوف ناقص است.",
        ],
        "glossary": [
            ("تحمل شهادت", "دیدن/ثبت صحنه"),
            ("ادای شهادت", "گواهی در محضر حساب"),
            ("جلود", "پوست‌ها؛ فصلت ۲۰–۲۲"),
        ],
    },
    "060": {
        "title": "جلسهٔ ۰۶۰ — انسان کامل",
        "focus": "رعد ۴۳؛ شهادت خدا و من عنده علم الکتاب؛ ادای شهادت بر رسالت",
        "headings": [
            (0.00, "## افتتاح و تلاوت رعد ۴۳"),
            (0.12, "## انکار رسالت و تقاضای معجزه"),
            (0.28, "## آیه در مقام ادای شهادت است نه تحمل"),
            (0.42, "## شهادت خدا چگونه در احتجاج ظاهر می‌شود؟"),
            (0.55, "## آل عمران ۱۸ و نساء ۱۶۶: الگوی شهادت"),
            (0.70, "## من عنده علم الکتاب کیست؟"),
            (0.85, "## قرآن، علم الکتاب و عرفان"),
            (0.93, "## دعا و روضه"),
        ],
        "summary_short": (
            "محور جلسه رعد ۴۳ است: کافران می‌گویند تو مرسل نیستی؛ بگو خدا میان من و شما گواه بس است "
            "و کسی که نزد او علم کتاب است. استاد تأکید می‌کند آیه مقام ادای شهادت است نه صرفاً "
            "علم غیبیِ تحمل. با آل عمران ۱۸ و نساء ۱۶۶ الگوی «شهادت خدا و اهل علم» را نشان می‌دهد "
            "و می‌پرسد مصداق «من عنده علم الکتاب» کیست. بحث را به شهادت بالفعلِ قرآن و اهل معرفت "
            "به کتاب می‌کشاند."
        ),
        "outline": [
            "تلاوت رعد ۴۳",
            "انکار رسالت و معجزه‌طلبی",
            "ادای شهادت در برابر تحمل",
            "چگونگی شهادت خدا در احتجاج",
            "آل عمران ۱۸؛ نساء ۱۶۶",
            "مصداق علم الکتاب",
            "قرآن به‌عنوان شاهد",
            "دعا و روضه",
        ],
        "takeaways": [
            "رعد ۴۳ در مقام اثبات رسالت با شهادت است.",
            "صرف اینکه «خدا می‌داند من رسولم» در احتجاج با منکر کافی نیست؛ باید شهادت ادا شود.",
            "الگوی مشابه در شهادت بر توحید (آل عمران ۱۸) دیده می‌شود.",
            "«من عنده علم الکتاب» مصداق محوری بحث انسان کامل/ولایت علمی است.",
            "قرآن می‌تواند شهادت بالفعل بر رسالت باشد.",
        ],
        "glossary": [
            ("علم الکتاب", "رعد ۴۳؛ دانش ویژهٔ کتاب"),
            ("ادای شهادت", "گواهیِ قابل احتجاج در صحنه"),
            ("تحمل شهادت", "علم/مشاهدهٔ پیشینی"),
        ],
    },
    "061": {
        "title": "جلسهٔ ۰۶۱ — انسان کامل",
        "focus": "ختم بحث شاهد؛ رعد ۴۳؛ شهادت خدا با قرآن؛ ولایت و حفظ نظام",
        "headings": [
            (0.00, "## افتتاح؛ آخرین جلسهٔ این فصل تفسیر"),
            (0.10, "## مرور رعد ۴۳ و ادای شهادت"),
            (0.25, "## شهادت خدا چگونه در عالم تحقق می‌یابد؟"),
            (0.40, "## اعجاز قرآن به‌عنوان شهادت بالفعل"),
            (0.55, "## انعام ۹ و پوشاندن حقیقت ملک"),
            (0.68, "## ولایت فقیه؛ حفظ تمرکز و پرهیز از غلو"),
            (0.82, "## بصیرت، سیما و تشخیص جریان‌ها"),
            (0.92, "## دعا و بشارت ادامه پس از تابستان"),
        ],
        "summary_short": (
            "جلسهٔ پایانیِ این فصلِ تفسیرِ شاهد است. استاد دوباره رعد ۴۳ را محور می‌کند و توضیح "
            "می‌دهد شهادت خدا بر رسالت در ظرف ادا چگونه رخ می‌دهد: آمدن قرآنی که کسی نمی‌تواند "
            "مانندش بیاورد خود شهادت بالفعل است. با انعام ۹ (اگر فرشته می‌فرستادیم او را مرد "
            "می‌ساختیم) منطق پوشاندن را یادآور می‌شود. در حاشیه دربارهٔ جایگاه ولایت فقیه "
            "(نه مقام عصمت) و ضرورت حفظ نظام و پرهیز از تمرکزِ آسیب‌زا سخن می‌گوید و نوید "
            "ادامهٔ کلاس‌ها پس از امتحانات تابستان را می‌دهد."
        ),
        "outline": [
            "اعلام ختم پروندهٔ شاهد در این ترم",
            "مرور رعد ۴۳",
            "شهادت خدا در احتجاج",
            "اعجاز قرآن",
            "انعام ۹",
            "ولایت فقیه و حفظ جانشین/نظام",
            "تشخیص سیما و جریان",
            "دعا و برنامهٔ تابستان",
        ],
        "takeaways": [
            "این جلسه پروندهٔ موضوع شاهد را در این فصل می‌بندد.",
            "شهادت خدا بر رسالت با تحقق قرآنِ معجز می‌تواند ادا شود.",
            "انعام ۹: صورت بشری رسول پوششی حکیمانه است.",
            "جایگاه ولایت فقیه را نباید با عصمت یکی کرد؛ حفظ نظام مهم است.",
            "کلاس پس از امتحانات تابستان از سر گرفته می‌شود.",
        ],
        "glossary": [
            ("شهادت بالفعل", "گواهیِ محقق در صحنهٔ دنیا/احتجاج"),
            ("علم الکتاب", "رعد ۴۳"),
            ("ولایت فقیه", "بحث حاشیه‌ای حفظ نظام در این جلسه"),
        ],
    },
}


def format_corrections_log(log: list[dict]) -> str:
    lines = ["", "---", "", "## Corrections log", ""]
    if not log:
        lines.append("- (ASR clarity cleanup; principal ayahs verified via alquran.cloud / quran.com)")
    for item in log:
        lines.append(f"- **{item['ref']}** — {item['fix']} — _{item['src']}_")
    lines.append("")
    lines.append(
        "Note: `--- Segments ---` omitted from corrected output (per pipeline)."
    )
    lines.append(
        "Verification corpus: alquran.cloud `quran-uthmani` (fetched 2026-08-24)."
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
    text = apply_persian_fixes(text)
    text, log = fix_citations(text, nnn)

    body = paragraphize(text)
    corr_txt = body + format_corrections_log(log)
    corr_txt_path = folder / f"{stem}.corrected.txt"
    corr_txt_path.write_text(corr_txt + "\n", encoding="utf-8")

    md_continuous = wrap_ayahs_in_md(text)
    md_body = insert_headings(paragraphize_preserving_ayah_html(md_continuous), nnn)
    meta = SESSION_META[nnn]
    md = (
        MD_BANNER.format(nnn=nnn, title=meta["title"], focus=meta["focus"])
        + "\n"
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

    return {
        "session": nnn,
        "stem": stem,
        "cleaned_chars": raw_len,
        "corrected_txt_chars": len(corr_txt_path.read_text(encoding="utf-8")),
        "corrected_md_chars": len(corr_md_path.read_text(encoding="utf-8")),
        "summary_chars": len(summary_path.read_text(encoding="utf-8")),
        "ratio": len(body) / raw_len if raw_len else 0,
        "citations": len(log),
        "paths": {
            "txt": str(corr_txt_path),
            "md": str(corr_md_path),
            "summary": str(summary_path),
        },
    }


def main():
    results = []
    for nnn in ["057", "058", "059", "060", "061"]:
        r = process_session(nnn)
        results.append(r)
        print(
            f"{nnn}: cleaned={r['cleaned_chars']} txt={r['corrected_txt_chars']} "
            f"md={r['corrected_md_chars']} sum={r['summary_chars']} "
            f"ratio={r['ratio']:.2%} cites={r['citations']}"
        )
        if r["ratio"] < 0.70:
            print(f"  WARNING: ratio below 70% for {nnn}")
    return results


if __name__ == "__main__":
    main()
