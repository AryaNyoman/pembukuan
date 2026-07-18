from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class ParsedTransaction:
    amount: int
    kind: str
    description: str
    category_hint: str
    tags: list[str]
    occurred_at: datetime
    needs_confirmation: bool = False


_AMOUNT_RE = re.compile(
    r"(?P<sign>[+-])?\s*(?P<number>\d[\d.,]*)\s*(?P<suffix>juta|jt|ribu|rb|k)?\b",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"\b(?P<day>\d{1,2})[/-](?P<month>\d{1,2})(?:[/-](?P<year>\d{2,4}))?\b")
_TAG_RE = re.compile(r"#([\w-]+)", re.UNICODE)

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Makan & Minum": ("makan", "minum", "kopi", "teh", "resto", "warung", "gofood", "grabfood"),
    "Transportasi": (
        "bensin",
        "parkir",
        "tol",
        "grab",
        "gojek",
        "taxi",
        "transport",
        "bus",
        "ojek",
    ),
    "Rumah & Tagihan": ("listrik", "air", "internet", "wifi", "sewa", "kontrakan", "rumah"),
    "Belanja": ("belanja", "supermarket", "mall", "pakaian", "shopee", "tokopedia"),
    "Kesehatan": ("obat", "dokter", "rumah sakit", "kesehatan", "vitamin"),
    "Pendidikan": ("kursus", "buku", "sekolah", "kuliah", "pendidikan"),
    "Hiburan": ("film", "game", "hiburan", "netflix", "musik", "rekreasi"),
    "Pekerjaan": ("kantor", "pekerjaan", "bisnis", "client", "proyek"),
    "Hadiah/Donasi": ("hadiah", "donasi", "zakat", "sedekah"),
}


def _parse_number(raw: str, suffix: str | None) -> int:
    normalized = raw.strip()
    suffix = (suffix or "").lower()
    if "." in normalized and "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif suffix in {"jt", "juta", "rb", "ribu", "k"}:
        # With a unit suffix, comma/dot is a decimal separator unless it is
        # clearly a grouped integer such as 1.000rb.
        if normalized.count(".") == 1 and len(normalized.rsplit(".", 1)[1]) == 3:
            normalized = normalized.replace(".", "")
        elif normalized.count(",") == 1 and len(normalized.rsplit(",", 1)[1]) == 3:
            normalized = normalized.replace(",", "")
        else:
            normalized = normalized.replace(",", ".")
    elif "," in normalized:
        left, right = normalized.rsplit(",", 1)
        normalized = normalized.replace(",", "") if len(right) == 3 else f"{left}.{right}"
    elif "." in normalized:
        left, right = normalized.rsplit(".", 1)
        normalized = normalized.replace(".", "") if len(right) == 3 else f"{left}.{right}"
    try:
        value = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("Nominal tidak valid") from exc
    multiplier = {"k": 1_000, "rb": 1_000, "ribu": 1_000, "jt": 1_000_000, "juta": 1_000_000}.get(
        suffix, 1
    )
    result = (value * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if result <= 0 or result > 10_000_000_000_000:
        raise ValueError("Nominal harus lebih dari 0 dan tidak terlalu besar")
    return int(result)


def _parse_date(text: str, now: datetime) -> tuple[datetime, str]:
    lowered = text.lower()
    if "kemarin" in lowered:
        return now - timedelta(days=1), "kemarin"
    if "hari ini" in lowered or "hariini" in lowered:
        return now, "hari ini"
    match = _DATE_RE.search(text)
    if match:
        day = int(match.group("day"))
        month = int(match.group("month"))
        year_text = match.group("year")
        year = int(year_text) if year_text else now.year
        if year < 100:
            year += 2000
        try:
            parsed = now.replace(year=year, month=month, day=day)
        except ValueError as exc:
            raise ValueError("Tanggal tidak valid") from exc
        return parsed, match.group(0)
    weekdays = {"senin": 0, "selasa": 1, "rabu": 2, "kamis": 3, "jumat": 4, "sabtu": 5, "minggu": 6}
    for name, weekday in weekdays.items():
        if re.search(rf"\b{name}\b", lowered):
            delta = (now.weekday() - weekday) % 7
            return now - timedelta(days=delta), name
    return now, ""


def parse_message(
    text: str, now: datetime | None = None, timezone: str = "Asia/Makassar"
) -> ParsedTransaction:
    text = " ".join(text.strip().split())
    if not text or len(text) > 500:
        raise ValueError("Pesan transaksi kosong atau terlalu panjang")
    now = now or datetime.now(ZoneInfo(timezone))
    if re.search(r"\d\s*\*|\*\s*\d", text):
        raise ValueError("Nominal tidak valid; jangan gunakan nominal yang disamarkan")
    occurred_at, _date_token = _parse_date(text, now)
    # Remove calendar dates before amount matching so 12/08 is never read as Rp12.
    amount_text = _DATE_RE.sub(" ", text)
    amount_match = _AMOUNT_RE.search(amount_text)
    if not amount_match:
        raise ValueError("Nominal tidak ditemukan. Contoh: 25k makan siang")
    amount = _parse_number(amount_match.group("number"), amount_match.group("suffix"))
    prefix = amount_text[: amount_match.start()].strip()
    suffix_text = amount_text[amount_match.end() :].strip()
    context = f"{prefix} {suffix_text}".strip()
    kind = (
        "income"
        if amount_match.group("sign") == "+"
        or re.search(r"\b(masuk|pemasukan|income)\b", context, flags=re.I)
        else "expense"
    )
    if amount_match.group("sign") == "-" or re.search(
        r"\b(keluar|pengeluaran|expense)\b", context, flags=re.I
    ):
        kind = "expense"
    tags = [tag.lower() for tag in _TAG_RE.findall(text)]
    description = _TAG_RE.sub("", context)
    description = re.sub(
        r"\b(kemarin|hari\s+ini|hariini|senin|selasa|rabu|kamis|jumat|sabtu|minggu)\b",
        "",
        description,
        flags=re.I,
    )
    description = re.sub(
        r"\b(masuk|pemasukan|income|keluar|pengeluaran|expense)\b", "", description, flags=re.I
    )
    description = " ".join(description.split()).strip(" -:;") or "Transaksi"
    lower_description = description.lower()
    category_hint = "Pemasukan" if kind == "income" else "Lainnya"
    if kind == "expense":
        for category, words in _KEYWORDS.items():
            if any(word in lower_description for word in words):
                category_hint = category
                break
    needs_confirmation = description == "Transaksi"
    return ParsedTransaction(
        amount=amount,
        kind=kind,
        description=description,
        category_hint=category_hint,
        tags=tags,
        occurred_at=occurred_at,
        needs_confirmation=needs_confirmation,
    )


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + (month == 12), 1 if month == 12 else month + 1, 1) - timedelta(days=1)
    return start, end
