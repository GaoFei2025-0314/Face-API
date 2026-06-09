"""Admin, maintenance, backup, and restore helpers for face_api."""
from pathlib import Path
import shutil
import time

from api_errors import raise_api_error


def is_maintenance_mode(maintenance_mode_file: Path) -> bool:
    return maintenance_mode_file.exists()


def set_maintenance_mode(enabled: bool, maintenance_mode_file: Path) -> None:
    if enabled:
        maintenance_mode_file.write_text(str(round(time.time(), 3)), encoding="utf-8")
    elif maintenance_mode_file.exists():
        maintenance_mode_file.unlink()


def ensure_not_maintenance(maintenance_mode_file: Path) -> None:
    if is_maintenance_mode(maintenance_mode_file):
        raise_api_error(503, "MAINTENANCE_MODE_ACTIVE")


def require_confirm(confirm: bool) -> None:
    if not confirm:
        raise_api_error(400, "MAINTENANCE_CONFIRM_REQUIRED")


def ensure_backup_subdir(backup_dir: Path, *, project_root: Path | None = None) -> Path:
    root = (project_root or Path.cwd()).resolve()
    backup_root = (root / "backups").resolve()
    resolved = backup_dir.resolve()
    try:
        is_allowed = resolved.is_relative_to(backup_root)
    except AttributeError:
        is_allowed = str(resolved).startswith(str(backup_root) + "\\")
    if resolved == backup_root or not is_allowed:
        raise_api_error(400, "BACKUP_PATH_INVALID")
    return resolved


def copy_existing_db_files(target_dir: Path, *, db_path: str, db) -> list[str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    backup_file = target_dir / Path(db_path).name
    return [db.backup_to(backup_file)]


def restore_db_files(backup_dir: Path, *, db_path: str, project_root: Path | None = None) -> list[str]:
    backup_dir = ensure_backup_subdir(backup_dir, project_root=project_root)
    if not backup_dir.exists():
        raise_api_error(404, "BACKUP_NOT_FOUND")
    restored = []
    base_name = Path(db_path).name
    if not (backup_dir / base_name).exists():
        raise_api_error(404, "BACKUP_NOT_FOUND")
    for suffix in ("", "-wal", "-shm"):
        src = backup_dir / f"{base_name}{suffix}"
        dst = Path(f"{db_path}{suffix}")
        if src.exists():
            shutil.copy2(src, dst)
            restored.append(str(dst))
        elif suffix and dst.exists():
            dst.unlink()
    return restored
