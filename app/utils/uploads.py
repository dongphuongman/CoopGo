"""Upload an toàn: giới hạn dung lượng + chủng loại file, chống treo worker."""
from pathlib import Path

from fastapi import HTTPException, UploadFile

CHUNK = 1024 * 1024  # 1MB


async def save_upload_limited(
    upload: UploadFile,
    dest: Path,
    *,
    allowed_exts: tuple[str, ...],
    max_mb: float,
) -> Path:
    name = (upload.filename or "").lower()
    if not name.endswith(allowed_exts):
        raise HTTPException(400, f"Chỉ chấp nhận file {', '.join(allowed_exts)}")

    limit = int(max_mb * 1024 * 1024)
    size = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(dest, "wb") as out:
            while True:
                chunk = await upload.read(CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    raise HTTPException(
                        413, f"File quá lớn ({size // 1024 // 1024}MB). Tối đa {max_mb:g}MB.")
                out.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, f"Không lưu được file upload: {e}")
    finally:
        try:
            await upload.close()
        except Exception:
            pass
    return dest
