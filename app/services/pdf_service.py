"""
PDF Service: Convert .docx → .pdf dùng LibreOffice headless.

Production considerations:
- LibreOffice có thể crash → dùng tenacity retry
- Timeout để tránh hung process
- Semaphore để limit concurrent conversions
"""
import asyncio
import shutil
import subprocess
import uuid
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

if not shutil.which(settings.LIBREOFFICE_BIN):
    logger.warning("libreoffice_missing",
                   hint="Cài LibreOffice để render PDF (apt install libreoffice). "
                        "Render DOCX vẫn hoạt động bình thường.")

# Semaphore giới hạn số conversion đồng thời (LibreOffice nặng memory)
_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_RENDERS)


async def convert_to_pdf(docx_path: str | Path, output_dir: str | Path) -> Path:
    """
    Convert file .docx sang .pdf dùng LibreOffice headless.

    Args:
        docx_path: Đường dẫn file .docx
        output_dir: Thư mục lưu file .pdf output

    Returns:
        Path của file .pdf
    """
    docx_path = Path(docx_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    async with _semaphore:
        loop = asyncio.get_event_loop()
        pdf_path = await loop.run_in_executor(
            None,
            _convert_sync,
            docx_path,
            output_dir,
        )

    logger.info("pdf_converted", source=str(docx_path), output=str(pdf_path))
    return pdf_path


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((subprocess.CalledProcessError, TimeoutError)),
    reraise=True,
)
def _convert_sync(docx_path: Path, output_dir: Path) -> Path:
    """
    Sync LibreOffice conversion với retry.
    LibreOffice dùng user profile riêng để tránh conflict khi chạy parallel.
    """
    # Tạo unique user profile dir để tránh LibreOffice conflict khi chạy song song
    unique_profile = settings.TEMP_DIR / f"lo_profile_{uuid.uuid4().hex}"
    unique_profile.mkdir(parents=True, exist_ok=True)

    if not shutil.which(settings.LIBREOFFICE_BIN):
        raise RuntimeError(
            "LibreOffice chưa được cài trên server nên không xuất được PDF. "
            "Hãy chọn output DOCX hoặc báo admin cài LibreOffice.")

    try:
        result = subprocess.run(
            [
                settings.LIBREOFFICE_BIN,
                "--headless",
                "--norestore",
                "--nofirststartwizard",
                f"-env:UserInstallation=file://{unique_profile}",
                "--convert-to", "pdf:writer_pdf_Export",
                str(docx_path),
                "--outdir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=settings.RENDER_TIMEOUT_SECONDS,
            check=True,
        )

        # LibreOffice output file cùng tên, đổi extension
        expected_pdf = output_dir / (docx_path.stem + ".pdf")
        if not expected_pdf.exists():
            raise FileNotFoundError(f"LibreOffice không tạo được PDF: {result.stderr}")

        return expected_pdf

    finally:
        # Cleanup profile temp
        shutil.rmtree(unique_profile, ignore_errors=True)
