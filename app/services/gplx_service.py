"""Validate hạng GPLX vs số chỗ — theo quy định VN rút gọn.

B2: <=9 chỗ | C: <=9 chỗ (tải) | D: <=30 chỗ | E: >30 chỗ
Trả (ok: bool, message: str).
"""
from __future__ import annotations

_HANG_ORDER = {"B1": 1, "B2": 2, "C": 3, "D": 4, "E": 5, "F": 6}
_MAX_CHO = {"B1": 9, "B2": 9, "C": 9, "D": 30, "E": 99, "F": 99}


def normalize_hang(hang: str | None) -> str | None:
    if not hang:
        return None
    s = str(hang).strip().upper().replace(".", "").replace(" ", "")
    # 'D ', 'E ' etc
    for k in _HANG_ORDER:
        if s.startswith(k):
            return k
    return s or None


def validate_gplx_for_so_cho(hang: str | None, so_cho: int | None) -> tuple[bool, str]:
    h = normalize_hang(hang)
    if not h:
        return False, "Thiếu hạng GPLX"
    if h not in _HANG_ORDER:
        return False, f"Hạng GPLX lạ: {hang}"
    if not so_cho:
        return True, "OK (không rõ số chỗ, bỏ qua)"
    max_cho = _MAX_CHO.get(h, 9)
    if so_cho <= max_cho:
        return True, "OK"
    need = "D" if so_cho <= 30 else "E"
    return False, f"Hạng {h} chỉ lái tối đa {max_cho} chỗ; xe {so_cho} chỗ cần hạng {need} trở lên"


def min_hang_for_so_cho(so_cho: int | None) -> str:
    if not so_cho:
        return "B2"
    if so_cho <= 9:
        return "B2"
    if so_cho <= 30:
        return "D"
    return "E"
