"""Shim tương thích: re-export models đã tách sang ops/coop/system.

Code mới nên import trực tiếp:
  from app.models.ops import Tuyen, PhanCong, LenhVanChuyen, HoSoPhapLy, BaoTri
  from app.models.coop import XaVien, VonGop, DoanhThu
  from app.models.system import VanBanVerify, AuditLog, ThongBao, AppSetting
"""
from app.models.ops import Tuyen, PhanCong, LenhVanChuyen, HoSoPhapLy, BaoTri
from app.models.coop import XaVien, VonGop, DoanhThu
from app.models.system import VanBanVerify, AuditLog, ThongBao, AppSetting

__all__ = [
    "Tuyen", "PhanCong", "LenhVanChuyen", "HoSoPhapLy", "BaoTri",
    "XaVien", "VonGop", "DoanhThu",
    "VanBanVerify", "AuditLog", "ThongBao", "AppSetting",
]
