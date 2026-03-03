"""Run all IDF files in the resources folder using eppy + the bundled Chicago EPW.

The EnergyPlus installation is resolved from the ``Version`` object inside each IDF.
Output files are written to ``resources/output/<stem>/``.

Run both scripts to compare simulation times:
    uv run python scripts/run_resource_models.py       # idfkit
    uv run python scripts/run_resource_models_eppy.py  # eppy
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from eppy.modeleditor import IDF

RESOURCES = Path(__file__).parent.parent / "resources"
WEATHER = RESOURCES / "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
OUTPUT_ROOT = RESOURCES / "output"

ENERGYPLUS_ROOT = Path("C:/")

_idd_set_for: str | None = None


def find_energyplus_dir(idf_path: Path) -> Path | None:
    """Return the EnergyPlus install dir matching the Version object in the IDF."""
    text = idf_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"(?i)\bVersion\s*,\s*([\d.]+)\s*;", text)
    if m is None:
        return None
    version_str = m.group(1)
    parts = version_str.split(".")
    major, minor = parts[0], parts[1] if len(parts) > 1 else "0"
    candidates = sorted(
        ENERGYPLUS_ROOT.glob(f"EnergyPlusV{major}-{minor}-*"),
        reverse=True,
    )
    return candidates[0] if candidates else None


def set_idd(ep_dir: Path) -> None:
    """Point eppy at the IDD for this EnergyPlus installation (once per dir)."""
    global _idd_set_for
    idd_path = str(ep_dir / "Energy+.idd")
    if _idd_set_for != idd_path:
        IDF.setiddname(idd_path, testing=True)
        _idd_set_for = idd_path


def main() -> None:
    idf_files = sorted(RESOURCES.glob("*.idf"))
    if not idf_files:
        print("No IDF files found in resources/")
        sys.exit(1)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    for idf_path in idf_files:
        print(f"[RUN ] {idf_path.name}")
        try:
            ep_dir = find_energyplus_dir(idf_path)
            if ep_dir is None:
                print("       SKIP  (no EnergyPlus installation found)")
                continue

            set_idd(ep_dir)

            out_dir = OUTPUT_ROOT / idf_path.stem
            out_dir.mkdir(parents=True, exist_ok=True)

            idf = IDF(str(idf_path), str(WEATHER))

            t0 = time.perf_counter()
            idf.run(
                weather=str(WEATHER),
                output_directory=str(out_dir),
                output_prefix=idf_path.stem,
                ep_version=ep_dir.name.replace("EnergyPlusV", "").replace("-", "."),
                verbose="q",
            )
            elapsed = time.perf_counter() - t0

            print(f"       OK  ({elapsed:.1f}s)  [{ep_dir.name}]")
        except Exception as exc:
            print(f"       ERROR: {exc}")


if __name__ == "__main__":
    main()
