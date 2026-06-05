"""
Export and validate face_api bulk manifests.

This script intentionally does not call InsightFace or register faces. It gives
operators a repeatable manifest workflow before they run batch registration.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from storage import FaceDB  # noqa: E402


EXPORT_FIELDS = ["id", "user_id", "username", "metadata", "created_at"]
IMPORT_REQUIRED_FIELDS = ["image_path", "username"]
IMPORT_OPTIONAL_FIELDS = ["user_id", "terminal_id", "metadata"]


def parse_metadata(raw):
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)


def export_manifest(args):
    db = FaceDB(args.db_path)
    rows = db.list_all()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "jsonl":
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            for row in rows:
                item = {field: row.get(field) for field in EXPORT_FIELDS}
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    else:
        with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=EXPORT_FIELDS)
            writer.writeheader()
            for row in rows:
                item = {field: row.get(field) for field in EXPORT_FIELDS}
                item["metadata"] = json.dumps(item["metadata"], ensure_ascii=False)
                writer.writerow(item)

    report = {
        "ok": True,
        "mode": "export",
        "count": len(rows),
        "output": str(output_path),
        "fields": EXPORT_FIELDS,
        "contains_embedding": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def read_import_rows(path):
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if line.strip():
                    try:
                        yield line_number, json.loads(line)
                    except json.JSONDecodeError as exc:
                        yield line_number, {"__parse_errors__": [f"invalid_json:{exc.msg}"]}
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                yield 1, {"__parse_errors__": ["empty_or_invalid_csv"]}
                return
            for line_number, row in enumerate(reader, 2):
                yield line_number, row


def validate_import_manifest(args):
    manifest_path = Path(args.manifest)
    success = []
    failed = []
    skipped = []
    seen_user_ids = set()

    if not manifest_path.exists():
        report = {
            "ok": False,
            "mode": "validate-import",
            "manifest": str(manifest_path),
            "success_count": 0,
            "failure_count": 1,
            "skipped_count": 0,
            "success": [],
            "failed": [{"line": None, "username": None, "user_id": None, "reasons": ["manifest_not_found"]}],
            "skipped": [],
            "required_fields": IMPORT_REQUIRED_FIELDS,
            "optional_fields": IMPORT_OPTIONAL_FIELDS,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    try:
        rows = list(read_import_rows(manifest_path))
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        rows = [(None, {"__parse_errors__": [f"manifest_read_error:{exc.__class__.__name__}"]})]

    for line_number, row in rows:
        errors = list(row.get("__parse_errors__", []))
        for field in IMPORT_REQUIRED_FIELDS:
            if not str(row.get(field, "")).strip():
                errors.append(f"missing_{field}")

        image_path = Path(str(row.get("image_path", "")).strip())
        if image_path and not image_path.is_absolute():
            image_path = (manifest_path.parent / image_path).resolve()
        if row.get("image_path") and not image_path.exists():
            errors.append("image_not_found")

        user_id = str(row.get("user_id", "")).strip()
        if user_id:
            if user_id in seen_user_ids:
                skipped.append({"line": line_number, "reason": "duplicate_user_id", "user_id": user_id})
                continue
            seen_user_ids.add(user_id)

        try:
            parse_metadata(row.get("metadata"))
        except Exception:
            errors.append("invalid_metadata_json")

        item = {"line": line_number, "username": row.get("username"), "user_id": row.get("user_id")}
        if errors:
            failed.append({**item, "reasons": errors})
        else:
            success.append(item)

    report = {
        "ok": not failed,
        "mode": "validate-import",
        "manifest": str(manifest_path),
        "success_count": len(success),
        "failure_count": len(failed),
        "skipped_count": len(skipped),
        "success": success[:20],
        "failed": failed,
        "skipped": skipped,
        "required_fields": IMPORT_REQUIRED_FIELDS,
        "optional_fields": IMPORT_OPTIONAL_FIELDS,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
    print(output)
    if failed:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description="face_api batch manifest workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="export current face manifest")
    export_parser.add_argument("--db-path", default="faces.db")
    export_parser.add_argument("--output", default="exports/faces-manifest.jsonl")
    export_parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    export_parser.set_defaults(func=export_manifest)

    validate_parser = subparsers.add_parser("validate-import", help="validate an import manifest")
    validate_parser.add_argument("manifest")
    validate_parser.add_argument("--output")
    validate_parser.set_defaults(func=validate_import_manifest)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
