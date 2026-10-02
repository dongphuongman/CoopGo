"""App factory — dựng FastAPI app (dùng cho chạy thật và tests)."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import setup_logging, logger
from app.api import template, render, config, auth, alerts, ops, coop, bulk, verify, access, dashboard
from app.api import fleet_common, fleet_import, fleet_vehicles, fleet_drivers
from app.api.auth import get_current_user
from app.core.scheduler import start_scheduler, stop_scheduler

settings = get_settings()

# Mọi router nghiệp vụ đều yêu cầu đăng nhập (trừ auth, health, verify công khai)
Authed = [Depends(get_current_user)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    setup_logging()
    settings.ensure_dirs()
    await init_db()
    start_scheduler()  # job nhắc hết hạn 7h sáng (nếu SCHEDULER_ENABLED=true)
    logger.info("app_started", version=settings.APP_VERSION, debug=settings.DEBUG)
    yield
    stop_scheduler()
    logger.info("app_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
## 📄 CoopGo API – Word Template → PDF

### Tính năng
- **Upload template** `.docx` (Jinja2 syntax)
- **AI auto-label** tiếng Việt cho từng field
- **Fill dữ liệu** động, bao gồm bảng lặp
- **Export PDF** giữ nguyên layout (LibreOffice)
- **Async render** cho batch processing

### Template syntax
```
{{ ho_ten }}          → scalar field
{{ ngay_sinh }}       → date field

{% for item in danh_sach %}
{{ item.ten }} | {{ item.so_tien }}
{% endfor %}
```
    """,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Thu hẹp lại trong production
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers (auth.router tự quản lý: login/register public, /me cần token)
    app.include_router(auth.router)
    app.include_router(template.router, dependencies=Authed)
    app.include_router(render.router, dependencies=Authed)
    app.include_router(config.router, dependencies=Authed)
    app.include_router(fleet_common.router, dependencies=Authed)
    app.include_router(fleet_import.router, dependencies=Authed)
    app.include_router(fleet_vehicles.router, dependencies=Authed)
    app.include_router(fleet_drivers.router, dependencies=Authed)
    app.include_router(alerts.router, dependencies=Authed)
    app.include_router(ops.router, dependencies=Authed)
    app.include_router(coop.router, dependencies=Authed)
    app.include_router(bulk.router, dependencies=Authed)
    app.include_router(access.router, dependencies=Authed)
    app.include_router(verify.public_router)  # /verify/{code}, /lenh-qr/{code} công khai cho CSGT quét QR
    app.include_router(dashboard.router, dependencies=Authed)

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "version": settings.APP_VERSION}

    return app
