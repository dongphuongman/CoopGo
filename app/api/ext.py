"""Ext API — Bulk render + Verify QR + Audit + Roles.

- POST /bulk/render-fleet — chọn N xe -> render N văn bản từ 1 template
- GET /verify/{code} + POST /render/{tid}/with-verify — ký số/QR verify
- GET /audit/logs — truy vết ai làm gì
- GET /roles/matrix + PATCH /users/{id}/role — phân quyền đơn giản
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, Template, RenderJob, RenderStatus
from app.core.config import get_settings
from app.models.coop_models import VanBanVerify, AuditLog, LenhVanChuyen
from app.models.fleet_models import PhuongTien, LaiXe
from app.services.qr_verify_service import new_verify_code, verify_url
from app.services.audit_service import log_audit
from app.api.auth import require_roles
from app.api.render import _do_render
from app.models.schema import RenderJobResponse, RenderJobStatus

router = APIRouter(tags=["Ext - Bulk, Verify, Audit, Roles"])
public_router = APIRouter(tags=["Public - Tra cứu công khai"])

OPS_WRITE = require_roles("admin", "dieu_hanh", "van_phong")
AUDIT_READ = require_roles("admin", "dieu_hanh")
settings = get_settings()


# ─── Bulk render ──────────────────────────────────────────────────
class BulkFleetIn(BaseModel):
    template_id: str
    bien_so_list: list[str] = []
    phuong_tien_ids: list[str] = []
    output_format: str = "pdf"
    extra_data: dict = {}
    gan_verify: bool = True


@router.post("/bulk/render-fleet", summary="Render hàng loạt từ danh sách xe",
             dependencies=[Depends(OPS_WRITE)])
async def bulk_render_fleet(payload: BulkFleetIn, background_tasks: BackgroundTasks,
                            db: AsyncSession = Depends(get_db)):
    tpl = (await db.execute(select(Template).where(Template.id == payload.template_id))).scalar_one_or_none()
    if not tpl:
        raise HTTPException(404, "Template không tồn tại")
    # Lấy xe theo ids hoặc biển số
    pts: list[PhuongTien] = []
    if payload.phuong_tien_ids:
        pts = (await db.execute(select(PhuongTien).where(PhuongTien.id.in_(payload.phuong_tien_ids)))).scalars().all()
    elif payload.bien_so_list:
        pts = (await db.execute(select(PhuongTien).where(PhuongTien.bien_so.in_(payload.bien_so_list)))).scalars().all()
    else:
        raise HTTPException(400, "Cần bien_so_list hoặc phuong_tien_ids")
    if not pts:
        raise HTTPException(404, "Không tìm thấy xe nào")

    jobs = []
    for pt in pts:
        job_id = str(uuid.uuid4())
        data = {"bien_so": pt.bien_so, "hang_xe": pt.hang_xe, "so_cho": pt.so_cho,
                "tuyen_khai_thac": pt.tuyen_khai_thac, "han_dang_kiem": pt.han_dang_kiem,
                "han_phu_hieu": pt.han_phu_hieu, "han_bao_hiem": pt.han_bao_hiem,
                **(payload.extra_data or {})}
        code = new_verify_code(job_id, tpl.id) if payload.gan_verify else None
        if code:
            data["verify_code"] = code
            data["verify_url"] = verify_url(code)
            data["qr_text"] = data["verify_url"]
        job = RenderJob(id=job_id, template_id=tpl.id, status=RenderStatus.PENDING,
                        input_data={"data": data, "output_format": payload.output_format,
                                    "bien_so": pt.bien_so, "verify_code": code})
        db.add(job)
        jobs.append((job_id, pt.bien_so, code))
        background_tasks.add_task(_bulk_one, job_id, tpl.id, data, payload.output_format, code,
                                  tpl.name, pt.bien_so)
    await db.flush()
    await log_audit(db, action="bulk_render", entity="template", entity_id=tpl.id,
                    detail=f"{len(jobs)} xe")
    return {"template": tpl.name, "total": len(jobs),
            "jobs": [{"job_id": j, "bien_so": b,
                      "download_url": f"/render/jobs/{j}/download",
                      "verify_code": c,
                      "verify_url": verify_url(c) if c else None} for j, b, c in jobs]}


async def _bulk_one(job_id: str, template_id: str, data: dict, fmt: str,
                    code: Optional[str], tpl_name: str, bien_so: str):
    from app.core.database import AsyncSessionLocal
    from app.api.render import RenderRequest
    async with AsyncSessionLocal() as db:
        try:
            r = await db.execute(select(RenderJob).where(RenderJob.id == job_id))
            job = r.scalar_one()
            job.status = RenderStatus.PROCESSING
            t = (await db.execute(select(Template).where(Template.id == template_id))).scalar_one()
            out = await _do_render(t, RenderRequest(data=data, output_format=fmt))
            job.status = RenderStatus.DONE
            job.output_path = str(out)
            job.completed_at = datetime.now(timezone.utc)
            if code:
                db.add(VanBanVerify(verify_code=code, render_job_id=job_id,
                                    template_id=template_id, template_name=tpl_name,
                                    bien_so=bien_so,
                                    payload_summary=json.dumps({"bien_so": bien_so}, ensure_ascii=False)))
            await db.commit()
        except Exception as e:
            r = await db.execute(select(RenderJob).where(RenderJob.id == job_id))
            job = r.scalar_one_or_none()
            if job:
                job.status = RenderStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()


# ─── Render kèm verify (đơn lẻ) ───────────────────────────────────
@router.post("/render/{template_id}/with-verify", summary="Render 1 văn bản kèm mã QR verify",
             dependencies=[Depends(OPS_WRITE)])
async def render_with_verify(template_id: str, payload: dict, background_tasks: BackgroundTasks,
                              db: AsyncSession = Depends(get_db)):
    from app.api.render import RenderRequest
    tpl = (await db.execute(select(Template).where(Template.id == template_id))).scalar_one_or_none()
    if not tpl:
        raise HTTPException(404, "Template không tồn tại")
    data = dict(payload.get("data") or {})
    fmt = payload.get("output_format", "pdf")
    job_id = str(uuid.uuid4())
    code = new_verify_code(job_id, template_id)
    data.update({"verify_code": code, "verify_url": verify_url(code), "qr_text": verify_url(code)})
    job = RenderJob(id=job_id, template_id=template_id, status=RenderStatus.PENDING,
                    input_data={"data": data, "output_format": fmt,
                                "verify_code": code,
                                "bien_so": data.get("bien_so")})
    db.add(job)
    await db.flush()
    background_tasks.add_task(_bulk_one, job_id, template_id, data, fmt, code, tpl.name,
                              str(data.get("bien_so") or ""))
    return {"job_id": job_id, "status": "pending", "verify_code": code,
            "verify_url": verify_url(code),
            "download_url": f"/render/jobs/{job_id}/download"}


@public_router.get("/verify/{code}", summary="Tra cứu văn bản bằng mã QR (công khai, không cần đăng nhập)")
async def verify_doc(code: str, db: AsyncSession = Depends(get_db)):
    code = code.upper()
    v = (await db.execute(select(VanBanVerify).where(VanBanVerify.verify_code == code))).scalar_one_or_none()
    if v:
        job = (await db.execute(select(RenderJob).where(RenderJob.id == v.render_job_id))).scalar_one_or_none()
        return {"hop_le": True, "verify_code": v.verify_code, "template": v.template_name,
                "bien_so": v.bien_so, "created_at": v.created_at,
                "download_url": f"/render/jobs/{v.render_job_id}/download" if job and job.status == RenderStatus.DONE else None}
    # Lệnh vận chuyển (có verify_code riêng, không qua render)
    lenh = (await db.execute(select(LenhVanChuyen).where(LenhVanChuyen.verify_code == code))).scalar_one_or_none()
    if lenh:
        return {"hop_le": True, "verify_code": lenh.verify_code,
                "template": "Lệnh vận chuyển",
                "so_lenh": lenh.so_lenh, "bien_so": lenh.bien_so,
                "created_at": lenh.created_at, "download_url": None}
    # fallback: tìm trong render job input (job cũ chưa có VanBanVerify)
    jobs = (await db.execute(select(RenderJob).where(RenderJob.status == RenderStatus.DONE)
                             .order_by(RenderJob.created_at.desc()).limit(200))).scalars().all()
    for j in jobs:
        if (j.input_data or {}).get("verify_code") == code:
            return {"hop_le": True, "verify_code": code,
                    "template": None, "bien_so": (j.input_data or {}).get("bien_so"),
                    "created_at": j.created_at, "download_url": f"/render/jobs/{j.id}/download"}
    raise HTTPException(404, "Mã xác thực không tồn tại (văn bản giả?)")


@public_router.get("/lenh-qr/{code}", summary="Ảnh QR tra cứu lệnh (PNG, công khai)")
async def lenh_qr(code: str):
    """QR trỏ tới trang xác thực công khai /verify/{code} trên web."""
    import io
    import qrcode
    from fastapi.responses import StreamingResponse
    url = f"{settings.PUBLIC_WEB_URL.rstrip('/')}/verify/{code.upper()}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


# ─── Audit ────────────────────────────────────────────────────────
@router.get("/audit/logs", summary="Nhật ký ai làm gì",
             dependencies=[Depends(AUDIT_READ)])
async def list_audit(entity: Optional[str] = None, action: Optional[str] = None,
                     limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = (await db.execute(stmt)).scalars().all()
    return [{"id": r.id, "actor": r.actor_name, "action": r.action, "entity": r.entity,
             "entity_id": r.entity_id, "detail": r.detail,
             "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


# ─── Roles (đơn giản trên User.is_admin + role string) ───────────
@router.get("/roles/matrix", summary="Ma trận phân quyền chuẩn HTX (đồng bộ menu frontend)")
async def roles_matrix():
    all_roles = ["admin", "dieu_hanh", "ke_toan", "van_phong", "lai_xe"]
    office = ["admin", "dieu_hanh", "van_phong"]
    return {
        "roles": all_roles,
        "role_labels": {
            "admin": "Quản trị", "dieu_hanh": "Điều hành", "ke_toan": "Kế toán",
            "van_phong": "Văn phòng", "lai_xe": "Lái xe",
        },
        "menus": {
            "/": all_roles,
            "/canh-bao": ["admin", "dieu_hanh", "ke_toan", "van_phong"],
            "/templates": office,
            "/render": office,
            "/bulk": office,
            "/jobs": office,
            "/phuong-tien": all_roles,
            "/lai-xe": all_roles,
            "/dieu-hanh": ["admin", "dieu_hanh"],
            "/bao-tri": ["admin", "dieu_hanh", "ke_toan"],
            "/xa-vien": ["admin", "dieu_hanh", "ke_toan"],
            "/settings": ["admin"],
        },
        "matrix": {
            "fleet.xem": all_roles,
            "fleet.sua": ["admin", "dieu_hanh"],
            "fleet.import": ["admin", "dieu_hanh"],
            "lenh.cap": ["admin", "dieu_hanh"],
            "taichinh.xem": ["admin", "dieu_hanh", "ke_toan"],
            "taichinh.sua": ["admin", "ke_toan"],
            "template.render": office,
            "cautruc.xem": all_roles,
            "config.sua": ["admin"],
        },
        "luu_y": "Admin luôn có mọi quyền. Menu frontend ẩn theo ma trận này; API chặn bằng require_roles.",
    }


@router.patch("/users/{user_id}/role", summary="Gán role cho user (admin)",
             dependencies=[Depends(require_roles("admin"))])
async def set_role(user_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    from app.core.database import User
    role = str(payload.get("role") or "").strip()
    if role not in ("admin", "dieu_hanh", "ke_toan", "van_phong", "lai_xe"):
        raise HTTPException(400, "role không hợp lệ")
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User không tồn tại")
    if hasattr(u, "role"):
        u.role = role
    u.is_admin = (role == "admin")
    await log_audit(db, action="set_role", entity="user", entity_id=user_id, detail=role)
    return {"ok": True, "role": role}
