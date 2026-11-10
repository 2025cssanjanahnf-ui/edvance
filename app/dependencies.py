import os
import uuid
import re
from pathlib import Path
from typing import Tuple
from fastapi import HTTPException, UploadFile, status
from app.database import get_db
from app.auth import (
    get_current_user,
    get_current_user_optional,
    get_current_student,
    get_current_faculty,
)

# Upload directory configuration
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "25"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".doc",
    ".zip",
    ".tar.gz",
    ".txt",
    ".py",
    ".json",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
}


def sanitize_filename(filename: str) -> str:
    """Sanitize original filename to prevent path traversal or unsafe characters."""
    clean = re.sub(r"[^\w\s\.-]", "_", filename).strip()
    return clean or "document"


def validate_and_save_upload(
    upload_file: UploadFile,
    subfolder: str
) -> Tuple[str, str, int, str]:
    """
    Validates file extension and size, saves file safely to disk.
    Returns: (saved_relative_path, safe_display_name, file_size_bytes, extension)
    """
    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload."
        )

    clean_name = sanitize_filename(upload_file.filename)
    extension = Path(clean_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{extension}' is not allowed. Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Prepare destination directory
    target_dir = Path(UPLOAD_DIR) / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)

    # Unique filename
    unique_prefix = uuid.uuid4().hex[:12]
    unique_filename = f"{unique_prefix}_{clean_name}"
    destination_path = target_dir / unique_filename

    # Read and validate size in chunks to prevent memory exhaustion
    total_size = 0
    try:
        with open(destination_path, "wb") as f:
            while chunk := upload_file.file.read(1024 * 64):  # 64KB chunks
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE_BYTES:
                    # Clean up partial file
                    f.close()
                    if destination_path.exists():
                        destination_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File size exceeds maximum permitted limit of {MAX_FILE_SIZE_MB}MB."
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Store relative path so it's portable
    relative_path = os.path.relpath(destination_path, BASE_DIR).replace("\\", "/")
    return relative_path, clean_name, total_size, extension

