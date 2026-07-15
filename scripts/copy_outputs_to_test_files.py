"""Copy .eso and .sql simulation outputs to tests/test_files/.

For every sub-directory under ``resources/output/`` that contains an .eso or
.sql file whose name matches the directory stem, the file is copied to
``tests/test_files/`` (overwriting any existing copy).

Usage:
    uv run python scripts/copy_outputs_to_test_files.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

OUTPUT_ROOT = Path(__file__).parent.parent / "resources" / "output"
TEST_FILES = Path(__file__).parent.parent / "tests" / "test_files"


def main() -> None:
    """Copy matching .eso/.sql outputs from resources/output/ into tests/test_files/."""
    TEST_FILES.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    missing: list[str] = []

    for out_dir in sorted(OUTPUT_ROOT.iterdir()):
        if not out_dir.is_dir():
            continue
        stem = out_dir.name
        for ext in (".eso", ".sql"):
            # eppy may append 'out' to the prefix (legacy suffix style)
            src = out_dir / (stem + ext)
            if not src.exists():
                src = out_dir / (stem + "out" + ext)
            if src.exists():
                dst_name = stem + ext  # always store without the 'out' infix
                shutil.copy2(src, TEST_FILES / dst_name)
                copied.append(dst_name)
            else:
                missing.append(stem + ext)

    print(f"Copied {len(copied)} file(s) to {TEST_FILES}:")
    for name in copied:
        print(f"  {name}")

    if missing:
        print(f"\nNot found ({len(missing)}):")
        for name in missing:
            print(f"  {name}")


if __name__ == "__main__":
    main()
