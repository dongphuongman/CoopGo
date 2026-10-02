# 🚌 CoopGo — Nền tảng quản trị HTX vận tải

Hệ thống điều hành hợp tác xã vận tải: quản lý **phương tiện, lái xe, tuyến, lệnh xuất bến**,
**sinh hợp đồng/văn bản từ Word template** (kèm QR xác thực), **cảnh báo hết hạn** đăng kiểm /
phù hiệu / bảo hiểm / GPLX, và **quản lý xã viên – vốn góp – doanh thu**.

- Backend: **FastAPI** (`app/`) — MySQL + SQLAlchemy async, JWT auth + phân quyền role
- Frontend: **React + Vite + shadcn-ui** (`e-coopgov-vision-admin/`) — port 3000

---

## ✨ Tính năng

### 🚍 Fleet — Phương tiện & Lái xe (`/fleet`)
- Import Excel danh sách xe / lái xe (preview trước, upsert hoặc bỏ qua trùng, tải file các dòng lỗi)
- Tìm kiếm + filter linh hoạt, xuất Excel theo filter, thống kê tổng hợp
- Cập nhật có validate (ngày sai định dạng / số chỗ âm / hạng GPLX lạ → 422)
- Kiểm tra GPLX có đủ lái xe bao nhiêu chỗ (`/fleet/lai-xe/{id}/gplx-check`)

### 🗓️ Điều hành vận tải (Ops)
- **Tuyến** (`/tuyen`): CRUD tuyến khai thác
- **Phân công** (`/phan-cong`): gán xe ↔ lái xe theo ngày, tự check hạng GPLX vs số chỗ + trùng lịch
- **Lệnh vận chuyển** (`/lenh`): cấp số lệnh tự động + mã QR xác thực
- **Bảo trì** (`/bao-tri`): sửa chữa / bảo dưỡng / nhiên liệu + tổng chi phí theo xe
- **Hồ sơ pháp lý** (`/ho-so`): lưu từng kỳ đăng kiểm / phù hiệu / bảo hiểm, tự sync hạn mới nhất về xe

### 📄 Tạo hợp đồng từ Word template (`/templates`, `/render`)
- Upload `.docx` (cú pháp Jinja2) → tự parse placeholder (xử lý lỗi Word tách run)
- **Nhãn tiếng Việt có dấu tự động** (từ điển ~100 cụm từ HTX + AI Ollama cho key lạ),
  viết tắt giữ in hoa kèm hint giải thích (CCCD, GPLX, MST…)
- `POST /templates/{id}/relabel` — chuẩn hóa lại nhãn template cũ (giữ nhãn đã sửa tay)
- Render sync (tải ngay) / async (job + poll), xuất **PDF** (LibreOffice) hoặc DOCX,
  render hàng loạt từ danh sách xe (`/bulk/render-fleet`)

### ✅ Xác thực công khai bằng QR
- Mỗi lệnh/văn bản có `verify_code` + ảnh QR (`GET /lenh-qr/{code}` — công khai)
- Trang công khai `/verify/{mã}` (không cần đăng nhập): CSGT/khách quét → thấy tính hợp lệ,
  loại văn bản, biển số, nút tải bản gốc / in

### 🔔 Cảnh báo hết hạn (`/alerts`)
- Quét hạn đăng kiểm / phù hiệu / bảo hiểm / GPLX / KSK, xếp mức `expired / critical / warning / notice`
- `POST /alerts/notify` gửi nhắc qua **log / email SMTP / Zalo OA** (chống gửi trùng trong ngày)
- Job tự động **7h sáng hằng ngày** (bật/tắt trên màn hình Cấu hình, không cần restart)

### 📊 Chỉ huy & Tài chính HTX
- `GET /dashboard/summary` — xe, lái xe, lệnh hôm nay, hết hạn gấp, doanh thu tháng
- Xã viên (`/xa-vien`), vốn góp (`/von-gop`), doanh thu tháng tự tính lợi nhuận (`/doanh-thu`)
- Nhật ký audit (`/audit/logs`) — ai làm gì, bản ghi nào, khi nào

### 🔐 Bảo mật & Cấu hình
- JWT auth bắt buộc toàn bộ API nghiệp vụ; phân quyền role:
  `admin > dieu_hanh > ke_toan > van_phong > lai_xe`
- Upload giới hạn dung lượng (`MAX_UPLOAD_MB`, mặc định 20MB)
- Màn hình **Cấu hình** (chỉ admin): sửa SMTP, Zalo, AI, upload… **lưu vào database**,
  không cần đụng file `.env`, không mất khi restart

---

## 🚀 Quick Start

### 1. Cấu hình

```bash
cp .env.example .env
# Tối thiểu: DATABASE_URL, API_SECRET_KEY
# Scheduler/notify/email/Zalo sửa sau trên màn hình Cấu hình (không bắt buộc)
```

### 2. Chạy bằng Docker

```bash
docker compose up --build
```

| Dịch vụ | Địa chỉ |
|---|---|
| Web admin | http://localhost:3000 |
| API + Swagger | http://localhost:8001 / `/docs` |
| phpMyAdmin | http://localhost:8080 |
| Nginx (profile production) | http://localhost:80 |

```bash
docker compose --profile production up --build
```

### 3. Chạy local (dev)

```bash
python3.11 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/uvicorn app.main:app --reload --port 8001
```

```bash
cd e-coopgov-vision-admin && npm install && npm run dev
# Mở http://localhost:3000 — proxy /api trỏ qua VITE_API_TARGET (mặc định API production)
```

### 4. Tài khoản đầu tiên

```bash
# Đăng ký qua API (mặc định role van_phong), rồi nâng lên admin trong DB:
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@htx.vn","username":"admin","password":"admin123"}'
# UPDATE users SET role='admin', is_admin=1 WHERE username='admin';
```

---

## 📡 API chính (đều cần `Authorization: Bearer <token>`, trừ `/verify/*`)

```bash
# Fleet
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8001/fleet/phuong-tien?q=29B"
curl -X POST http://localhost:8001/fleet/lai-xe/import -H "Authorization: Bearer $TOKEN" \
  -F "file=@Phu_luc_2_Danh_sach_lai_xe.xlsx" -F "header_row=4" -F "data_start_row=6"

# Điều hành
curl -X POST http://localhost:8001/lenh -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"bien_so":"29B-12345"}'
curl "http://localhost:8001/alerts/expiry?within_days=30" -H "Authorization: Bearer $TOKEN"

# Tạo hợp đồng
curl -X POST http://localhost:8001/templates/ -H "Authorization: Bearer $TOKEN" \
  -F "file=@hop_dong.docx" -F "name=HD thuê xe 50 chỗ"
curl -X POST http://localhost:8001/render/{template_id} -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data": {"bien_so_xe": "29B-12345"}, "output_format": "pdf"}' -o hop_dong.pdf

# Xác thực công khai (không cần token)
curl http://localhost:8001/verify/{ma_qr}
```

## 📝 Template Syntax (Jinja2)

```
{{ bien_so_xe }}              ← scalar field
{{ ngay_ky }}                 ← date field

{% for item in danh_sach %}
{{ item.ten }} | {{ item.so_tien }}
{% endfor %}

{% if co_phu_luc %}
Phụ lục: {{ ten_phu_luc }}
{% endif %}

{{ qr_text }}                 ← nhúng link xác thực / QR vào văn bản
```

Xem ví dụ đầy đủ trong `templates/TEMPLATE_GUIDE.txt`. File mẫu trong `documents/Files/`.

---

## 🏗️ Kiến trúc

```
Browser :3000 (Vite, proxy /api)
  ↓
Nginx :80 (profile production)
  ↓
FastAPI :8000 (2 workers, LibreOffice cho PDF)
  ├── /auth, /config (admin)          → users, app_settings
  ├── /templates, /render, /bulk     → templates, render_jobs, van_ban_verify
  ├── /fleet                         → phuong_tien, lai_xe, import_jobs
  ├── /tuyen, /phan-cong, /lenh,     → tuyen, phan_cong, lenh_van_chuyen,
  │   /bao-tri, /ho-so                  bao_tri, ho_so_phap_ly
  ├── /alerts (+scheduler 7h sáng)   → thong_bao (gửi log/email/Zalo)
  ├── /dashboard                      → tổng hợp chỉ huy
  ├── /xa-vien, /von-gop, /doanh-thu → xa_vien, von_gop, doanh_thu
  ├── /audit, /roles                 → audit_logs
  └── /verify/{code}, /lenh-qr/{code} (công khai, không cần đăng nhập)

MySQL 8 (docgen) + phpMyAdmin :8080
Storage/  ├── uploads/ (template .docx, file import)
          ├── outputs/ (PDF/DOCX đã render)
          └── temp/    (file tạm + LibreOffice profiles)
```

## ⚙️ Biến môi trường (`.env`)

| Key | Mặc định | Sửa trên UI được? |
|---|---|---|
| `DATABASE_URL` | `mysql+aiomysql://docgen:docgenpassword@db:3306/docgen` | ❌ |
| `API_SECRET_KEY` | `changeme-in-production` | ❌ |
| `PUBLIC_WEB_URL` | `http://localhost:3000` | ✅ (QR trỏ đúng domain khi deploy) |
| `AI_ENABLED` / `OLLAMA_API_KEY` | `true` / — | ✅ |
| `MAX_UPLOAD_MB` | `20` | ✅ |
| `SCHEDULER_ENABLED` / `NOTIFY_WITHIN_DAYS` | `false` / `30` | ✅ |
| `SMTP_HOST/PORT/USER/PASS/FROM`, `NOTIFY_EMAILS` | — | ✅ |
| `ZALO_OA_TOKEN`, `ZALO_USER_IDS` | — | ✅ |
| `MAX_CONCURRENT_RENDERS`, `RENDER_TIMEOUT_SECONDS` | `10` / `60` | ✅ (cần restart API) |

Mọi key nhóm 2–5 sửa trên màn hình **Cấu hình** (lưu DB, thắng `.env`).
