"""Quran metadata: Surahs, page ranges (1-604), and Juz mappings."""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SurahInfo:
    number: int
    name_arabic: str
    name_english: str
    page_start: int
    page_end: int


# Standard Madinah Mushaf (604 Pages) Surah Mapping
SURAHS: List[SurahInfo] = [
    SurahInfo(1, "الفاتحة", "Al-Fatihah", 1, 1),
    SurahInfo(2, "البقرة", "Al-Baqarah", 2, 49),
    SurahInfo(3, "آل عمران", "Ali 'Imran", 50, 76),
    SurahInfo(4, "النساء", "An-Nisa", 77, 106),
    SurahInfo(5, "المائدة", "Al-Ma'idah", 106, 127),
    SurahInfo(6, "الأنعام", "Al-An'am", 128, 150),
    SurahInfo(7, "الأعراف", "Al-A'raf", 151, 176),
    SurahInfo(8, "الأنفال", "Al-Anfal", 177, 186),
    SurahInfo(9, "التوبة", "At-Tawbah", 187, 207),
    SurahInfo(10, "يونس", "Yunus", 208, 221),
    SurahInfo(11, "هود", "Hud", 221, 235),
    SurahInfo(12, "يوسف", "Yusuf", 235, 248),
    SurahInfo(13, "الرعد", "Ar-Ra'd", 249, 255),
    SurahInfo(14, "إبراهيم", "Ibrahim", 255, 261),
    SurahInfo(15, "الحجر", "Al-Hijr", 262, 267),
    SurahInfo(16, "النحل", "An-Nahl", 267, 281),
    SurahInfo(17, "الإسراء", "Al-Isra", 282, 293),
    SurahInfo(18, "الكهف", "Al-Kahf", 293, 304),
    SurahInfo(19, "مريم", "Maryam", 305, 312),
    SurahInfo(20, "طه", "Ta-Ha", 312, 321),
    SurahInfo(21, "الأنبياء", "Al-Anbiya", 322, 331),
    SurahInfo(22, "الحج", "Al-Hajj", 332, 341),
    SurahInfo(23, "المؤمنون", "Al-Mu'minun", 342, 349),
    SurahInfo(24, "النور", "An-Nur", 350, 359),
    SurahInfo(25, "الفرقان", "Al-Furqan", 359, 366),
    SurahInfo(26, "الشعراء", "Ash-Shu'ara", 367, 376),
    SurahInfo(27, "النمل", "An-Naml", 377, 385),
    SurahInfo(28, "القصص", "Al-Qasas", 385, 396),
    SurahInfo(29, "العنكبوت", "Al-'Ankabut", 396, 404),
    SurahInfo(30, "الروم", "Ar-Rum", 404, 410),
    SurahInfo(31, "لقمان", "Luqman", 411, 414),
    SurahInfo(32, "السجدة", "As-Sajdah", 415, 417),
    SurahInfo(33, "الأحزاب", "Al-Ahzab", 418, 427),
    SurahInfo(34, "سبأ", "Saba", 428, 434),
    SurahInfo(35, "فاطر", "Fatir", 434, 440),
    SurahInfo(36, "يس", "Ya-Sin", 440, 445),
    SurahInfo(37, "الصافات", "As-Saffat", 446, 452),
    SurahInfo(38, "ص", "Sad", 453, 458),
    SurahInfo(39, "الزمر", "Az-Zumar", 458, 467),
    SurahInfo(40, "غافر", "Ghafir", 467, 476),
    SurahInfo(41, "فصلت", "Fussilat", 477, 482),
    SurahInfo(42, "الشورى", "Ash-Shura", 483, 489),
    SurahInfo(43, "الزخرف", "Az-Zukhruf", 489, 495),
    SurahInfo(44, "الدخان", "Ad-Dukhan", 496, 498),
    SurahInfo(45, "الجاثية", "Al-Jathiyah", 499, 502),
    SurahInfo(46, "الأحقاف", "Al-Ahqaf", 502, 506),
    SurahInfo(47, "محمد", "Muhammad", 507, 510),
    SurahInfo(48, "الفتح", "Al-Fath", 511, 515),
    SurahInfo(49, "الحجرات", "Al-Hujurat", 515, 517),
    SurahInfo(50, "ق", "Qaf", 518, 520),
    SurahInfo(51, "الذاريات", "Adh-Dhariyat", 520, 523),
    SurahInfo(52, "الطور", "At-Tur", 523, 525),
    SurahInfo(53, "النجم", "An-Najm", 526, 528),
    SurahInfo(54, "القمر", "Al-Qamar", 528, 531),
    SurahInfo(55, "الرحمن", "Ar-Rahman", 531, 534),
    SurahInfo(56, "الواقعة", "Al-Waqi'ah", 534, 537),
    SurahInfo(57, "الحديد", "Al-Hadid", 537, 541),
    SurahInfo(58, "المجادلة", "Al-Mujadilah", 542, 545),
    SurahInfo(59, "الحشر", "Al-Hashr", 545, 548),
    SurahInfo(60, "الممتحنة", "Al-Mumtahanah", 549, 551),
    SurahInfo(61, "الصف", "As-Saff", 551, 552),
    SurahInfo(62, "الجمعة", "Al-Jumu'ah", 553, 554),
    SurahInfo(63, "المنافقون", "Al-Munafiqun", 554, 555),
    SurahInfo(64, "التغابن", "At-Taghabun", 556, 557),
    SurahInfo(65, "الطلاق", "At-Talaq", 558, 559),
    SurahInfo(66, "التحريم", "At-Tahrim", 560, 561),
    SurahInfo(67, "الملك", "Al-Mulk", 562, 564),
    SurahInfo(68, "القلم", "Al-Qalam", 564, 566),
    SurahInfo(69, "الحاقة", "Al-Haqqah", 566, 568),
    SurahInfo(70, "المعارج", "Al-Ma'arij", 568, 570),
    SurahInfo(71, "نوح", "Nuh", 570, 571),
    SurahInfo(72, "الجن", "Al-Jinn", 572, 573),
    SurahInfo(73, "المزمل", "Al-Muzzammil", 574, 575),
    SurahInfo(74, "المدثر", "Al-Muddaththir", 575, 577),
    SurahInfo(75, "القيامة", "Al-Qiyamah", 577, 578),
    SurahInfo(76, "الإنسان", "Al-Insan", 578, 580),
    SurahInfo(77, "المرسلات", "Al-Mursalat", 580, 581),
    SurahInfo(78, "النبأ", "An-Naba", 582, 583),
    SurahInfo(79, "النازعات", "An-Nazi'at", 583, 584),
    SurahInfo(80, "عبس", "'Abasa", 585, 586),
    SurahInfo(81, "التكوير", "At-Takwir", 586, 586),
    SurahInfo(82, "الانفطار", "Al-Infitar", 587, 587),
    SurahInfo(83, "المطففين", "Al-Mutaffifin", 587, 589),
    SurahInfo(84, "الانشقاق", "Al-Inshiqaq", 589, 590),
    SurahInfo(85, "البروج", "Al-Buruj", 590, 590),
    SurahInfo(86, "الطارق", "At-Tariq", 591, 591),
    SurahInfo(87, "الأعلى", "Al-A'la", 591, 592),
    SurahInfo(88, "الغاشية", "Al-Ghashiyah", 592, 593),
    SurahInfo(89, "الفجر", "Al-Fajr", 593, 594),
    SurahInfo(90, "البلد", "Al-Balad", 594, 595),
    SurahInfo(91, "الشمس", "Ash-Shams", 595, 595),
    SurahInfo(92, "الليل", "Al-Layl", 595, 596),
    SurahInfo(93, "الضحى", "Ad-Duha", 596, 596),
    SurahInfo(94, "الشرح", "Ash-Sharh", 596, 596),
    SurahInfo(95, "التين", "At-Tin", 597, 597),
    SurahInfo(96, "العلق", "Al-'Alaq", 597, 597),
    SurahInfo(97, "القدر", "Al-Qadr", 598, 598),
    SurahInfo(98, "البينة", "Al-Bayyinah", 598, 599),
    SurahInfo(99, "الزلزلة", "Az-Zalzalah", 599, 599),
    SurahInfo(100, "العاديات", "Al-'Adiyat", 599, 600),
    SurahInfo(101, "القارعة", "Al-Qari'ah", 600, 600),
    SurahInfo(102, "التكاثر", "At-Takathur", 600, 600),
    SurahInfo(103, "العصر", "Al-'Asr", 601, 601),
    SurahInfo(104, "الهمزة", "Al-Humazah", 601, 601),
    SurahInfo(105, "الفيل", "Al-Fil", 601, 601),
    SurahInfo(106, "قريش", "Quraysh", 602, 602),
    SurahInfo(107, "الماعون", "Al-Ma'un", 602, 602),
    SurahInfo(108, "الكوثر", "Al-Kawthar", 602, 602),
    SurahInfo(109, "الكافرون", "Al-Kafirun", 603, 603),
    SurahInfo(110, "النصر", "An-Nasr", 603, 603),
    SurahInfo(111, "المسد", "Al-Masad", 603, 603),
    SurahInfo(112, "الإخلاص", "Al-Ikhlas", 604, 604),
    SurahInfo(113, "الفلق", "Al-Falaq", 604, 604),
    SurahInfo(114, "الناس", "An-Nas", 604, 604),
]


def _normalize_name(name: str) -> str:
    """Normalizes Arabic/English name for flexible matching."""
    n = name.strip().lower()
    # Remove common prefixes in English (al-, an-, ash-, ar-, at-, az-, ad-)
    n = re.sub(r"^(al|an|ash|ar|at|az|ad|adh|as)[\-'\s]?", "", n)
    # Remove special punctuation
    n = re.sub(r"['\-\s_]", "", n)
    # Normalize Arabic prefixes (سورة، الـ)
    n = re.sub(r"^سورة\s*", "", n)
    n = re.sub(r"^ال", "", n)
    return n


def get_surahs_for_page_range(start_page: int, end_page: int) -> List[SurahInfo]:
    """Returns all Surahs that appear in the given page range."""
    return [
        s for s in SURAHS
        if not (s.page_end < start_page or s.page_start > end_page)
    ]


def get_juz_for_page(page: int) -> int:
    """Computes the Juz number (1 to 30) for a given page number."""
    if page < 1:
        return 1
    if page > 604:
        return 30
    juz = ((page - 2) // 20) + 1
    return max(1, min(30, juz))


def get_surah_by_name_or_number(identifier: str) -> Optional[SurahInfo]:
    """Looks up a Surah by name (Arabic/English) or number with flexible prefix matching."""
    identifier_clean = identifier.strip().lower()
    if identifier_clean.isdigit():
        num = int(identifier_clean)
        for s in SURAHS:
            if s.number == num:
                return s
        return None

    norm_query = _normalize_name(identifier)
    for s in SURAHS:
        if _normalize_name(s.name_english) == norm_query or _normalize_name(s.name_arabic) == norm_query:
            return s
        if s.name_english.lower() == identifier_clean or s.name_arabic == identifier.strip():
            return s

    return None
