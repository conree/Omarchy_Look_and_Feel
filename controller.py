#!/usr/bin/env python3
"""Read-only source and application inventory for Omarchy Look & Feel."""

from __future__ import annotations

import json
import hashlib
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse
from pathlib import Path

from transaction import TransactionError, recover_pending, rollback_latest, transaction_status


HOME = Path.home()
CATALOG_ROOT = HOME / ".local/share/omarchy-look-and-feel/catalogs"
THEME_DIRS = (
    CATALOG_ROOT / "themes/omarchy-packaged",
    CATALOG_ROOT / "themes/omarchy-user",
)
ICON_DIRS = (Path("/usr/share/icons"), HOME / ".local/share/icons")
BACKGROUND_DIRS = (
    CATALOG_ROOT / "backgrounds/omarchy-packaged",
    CATALOG_ROOT / "backgrounds/omarchy-user",
    CATALOG_ROOT / "backgrounds/user-library",
)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

APPLICATIONS = (
    ("Hey", ("hey", "omarchy-webapp-handler-hey")),
    ("LibreOffice Fresh", ("libreoffice", "soffice")),
    ("OnlyOffice Desktop Editors", ("onlyoffice-desktopeditors",)),
    ("PCManFM", ("pcmanfm",)),
    ("Terminal: Alacritty", ("alacritty",)),
    ("Terminal: Foot", ("foot",)),
    ("Terminal: Ghostty", ("ghostty",)),
    ("Terminal: Kitty", ("kitty",)),
    ("Terminal: WezTerm", ("wezterm",)),
    ("Browser: Brave", ("brave", "brave-browser")),
)


def direct_dirs(paths: tuple[Path, ...]) -> list[str]:
    names: set[str] = set()
    for base in paths:
        if not base.is_dir():
            continue
        try:
            names.update(p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith("."))
        except OSError:
            continue
    return sorted(names, key=str.casefold)


def stable_id(kind: str, identity: str) -> str:
    """Build a readable, deterministic ID without depending on display order."""
    slug = re.sub(r"[^a-z0-9]+", "-", identity.casefold()).strip("-") or "item"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"{kind}:{slug[:48]}-{digest}"


def catalog_entry_eligible(entry: dict[str, object]) -> bool:
    """Require explicit review evidence before a discovered item is selectable."""
    license_name = entry.get("license")
    evidence = entry.get("licenseEvidence")
    parsed = urlparse(evidence) if isinstance(evidence, str) else None
    evidence_ok = bool(parsed and parsed.scheme in {"https", "file"} and parsed.path)
    compatibility = entry.get("compatibility")
    compatibility_ok = compatibility == "verified" if entry.get("kind") == "theme" else compatibility == "not-required"
    return bool(
        entry.get("review") == "verified"
        and entry.get("provenanceVerified") is True
        and isinstance(license_name, str) and license_name.strip()
        and evidence_ok
        and compatibility_ok
    )


def themes() -> list[str]:
    # A user overlay and its package theme share one selector entry.
    return direct_dirs(THEME_DIRS)


def theme_entries() -> list[dict[str, object]]:
    entries = []
    for name in themes():
        sources = [str(base / name) for base in THEME_DIRS if (base / name).is_dir()]
        entries.append({
            "id": stable_id("theme", name), "kind": "theme", "name": name,
            "source": sources, "license": None, "review": "needs-compatibility-and-license-review",
            "licenseEvidence": None, "provenanceVerified": False,
            "compatibility": "pending", "selectable": False,
        })
    return entries


def icon_themes() -> list[str]:
    names: set[str] = set()
    for base in ICON_DIRS:
        if not base.is_dir():
            continue
        try:
            for item in base.iterdir():
                if item.is_dir() and (item / "index.theme").is_file():
                    names.add(item.name)
        except OSError:
            continue
    return sorted(names, key=str.casefold)


def icon_entries() -> list[dict[str, object]]:
    entries = []
    for name in icon_themes():
        sources = [str(base / name) for base in ICON_DIRS if (base / name / "index.theme").is_file()]
        entries.append({
            "id": stable_id("icon", name), "kind": "icon", "name": name,
            "source": sources, "license": None, "review": "metadata-unverified",
            "licenseEvidence": None, "provenanceVerified": False,
            "compatibility": "not-required", "selectable": False,
        })
    return entries


def backgrounds() -> list[str]:
    found: set[str] = set()
    current = HOME / ".local/state/omarchy/current/background"
    try:
        resolved = current.resolve(strict=True)
        if resolved.is_file() and resolved.suffix.lower() in IMAGE_SUFFIXES:
            found.add(str(resolved))
    except OSError:
        pass
    for base in BACKGROUND_DIRS:
        if not base.is_dir():
            continue
        try:
            for path in base.rglob("*"):
                if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                    found.add(str(path.resolve()))
        except OSError:
            continue
    return sorted(found, key=str.casefold)


def background_entries() -> list[dict[str, object]]:
    entries = []
    for path_string in backgrounds():
        path = Path(path_string)
        try:
            identity = path.relative_to(CATALOG_ROOT).as_posix()
        except ValueError:
            identity = "external/" + path.as_posix()
        entries.append({
            "id": stable_id("background", identity), "kind": "background",
            "name": path.name, "source": str(path), "license": None,
            "review": "provenance-unverified", "licenseEvidence": None,
            "provenanceVerified": False,
            "compatibility": "not-required", "selectable": False,
        })
    return entries


def font_families() -> list[str]:
    if not shutil.which("fc-list"):
        return []
    try:
        result = subprocess.run(
            ["fc-list", "--format", "%{family}\n"],
            check=True,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    names = set()
    for line in result.stdout.splitlines():
        # Fontconfig can return aliases separated by commas.
        names.update(part.strip() for part in line.split(",") if part.strip())
    return sorted(names, key=str.casefold)


def font_entries() -> list[dict[str, object]]:
    return [{
        "id": stable_id("font", name), "kind": "font", "name": name,
        "source": "fontconfig; package/source not yet verified", "license": None,
        "review": "needs-provenance-and-license-review", "licenseEvidence": None,
        "provenanceVerified": False,
        "compatibility": "not-required", "selectable": False,
    } for name in font_families()]


def application_inventory() -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for name, commands in APPLICATIONS:
        path = next((shutil.which(command) for command in commands if shutil.which(command)), None)
        entries.append({"name": name, "available": path is not None, "path": path or ""})
    return entries


def inventory() -> dict[str, object]:
    entries = {
        "themes": theme_entries(),
        "fonts": font_entries(),
        "icons": icon_entries(),
        "backgrounds": background_entries(),
    }
    for records in entries.values():
        for record in records:
            record["selectable"] = catalog_entry_eligible(record)
    return {
        "read_only": True,
        "applications": application_inventory(),
        "catalogs": {
            "themes": themes(),
            "fonts": font_families(),
            "icons": icon_themes(),
            "backgrounds": backgrounds(),
        },
        "catalog_entries": entries,
        "catalog_review": {
            kind: {
                "total": len(records),
                "selectable": sum(1 for record in records if record["selectable"]),
                "pending_review": sum(1 for record in records if not record["selectable"]),
            }
            for kind, records in entries.items()
        },
        "catalog_sources": {
            "canonical_catalog_root": str(CATALOG_ROOT),
            "themes": [str(path) for path in THEME_DIRS],
            "fonts": ["fontconfig system and user font directories"],
            "icons": [str(path) for path in ICON_DIRS],
            "backgrounds": [str(path) for path in BACKGROUND_DIRS],
        },
    }


def main(argv: list[str]) -> int:
    if argv == ["inventory"]:
        json.dump(inventory(), sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 2 and argv[0] == "transaction":
        action = argv[1]
        try:
            if action == "status":
                result: object = {"transactions": transaction_status()}
            elif action == "recover":
                result = {"recovered": recover_pending()}
            elif action == "rollback":
                result = {"rolledBack": rollback_latest()}
            else:
                raise ValueError
        except ValueError:
            print("Usage: controller.py transaction {status|recover|rollback}", file=sys.stderr)
            return 2
        except TransactionError as exc:
            print(f"Transaction action failed: {exc}", file=sys.stderr)
            return 1
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    print("Usage: controller.py inventory | transaction {status|recover|rollback}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
