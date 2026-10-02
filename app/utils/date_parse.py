"""Parse ngày kiểu VN linh hoạt -> datetime.date | None.

Hỗ trợ: datetime/date, 'YYYY-MM-DD', 'DD/MM/YYYY', 'DD-MM-YYYY',
'DD.MM.YYYY', Excel serial, '2020.0' fallback.
Trả None nếu rỗng / không parse được (không throw).
"""
from __future__ import annotations

from datetime import date, datetime


def parse_vn_date(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, (int, float)):
        # Excel serial? 20000..60000 ~ 1954..2064
        try:
            if 20000 <= float(val) <= 60000:
                from datetime import timedelta
                base = date(1899, 12, 30)
                return base + timedelta(days=int(val))
            # Năm dạng 2020.0
            if 1900 <= int(val) <= 2100:
                return None  # năm SX, không phải ngày hết hạn
        except Exception:
            return None
        return None
    s = str(val).strip()
    if not s or s in {"-", "--", "N/A", "n/a", "Không", "không"}:
        return None
    # ISO trước
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y",
                "%d.%m.%Y", "%d/%m/%y", "%Y.%m.%d"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    # 'YYYY-MM-DD...' dài hơn (datetime iso)
    try:
        return datetime.fromisoformat(s[:19]).date()
    except Exception:
        return None


def days_until(d: date | None, today: date | None = None) -> int | None:
    if d is None:
        return None
    today = today or date.today()
    return (d - today).days


def expiry_level(days: int | None) -> str:
    """expired | critical(<=7) | warning(<=30) | notice(<=60) | ok | unknown"""
    if days is None:
        return "unknown"
    if days < 0:
        return "expired"
    if days <= 7:
        return "critical"
    if days <= 30:
        return "warning"
    if days <= 60:
        return "notice"
    return "ok"


def as_iso(d: date | None) -> str | None:
    return d.isoformat() if d else None
