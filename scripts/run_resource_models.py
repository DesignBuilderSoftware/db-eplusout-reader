"""Run all IDF files in the resources folder using eppy + the bundled Chicago EPW.

The EnergyPlus installation is resolved from the ``Version`` object inside each IDF.
Output files are written to ``resources/output/<stem>/``.

Simulations are grouped by EnergyPlus version and run in parallel within each group
via eppy's ``runIDFs()`` (one worker per logical CPU).  Grouping is required because
eppy stores the active IDD as a class-level attribute; a single process can only hold
one IDD at a time.

Run both scripts to compare simulation times:
    uv run python scripts/run_resource_models.py
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

from eppy.modeleditor import IDF, IDDResetError
from eppy.runner.run_functions import EnergyPlusRunError, runIDFs

RESOURCES = Path(__file__).parent.parent / "resources"
WEATHER = RESOURCES / "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
OUTPUT_ROOT = RESOURCES / "output"
TEST_FILES = Path(__file__).parent.parent / "tests" / "test_files"

ENERGYPLUS_ROOT = Path("C:/")


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


def copy_outputs_to_test_files(idf_files: list[Path]) -> None:
    """Copy .eso and .sql outputs to tests/test_files/ using the IDF stem as name."""
    TEST_FILES.mkdir(parents=True, exist_ok=True)
    copied = 0
    for idf_path in idf_files:
        stem = idf_path.stem  # e.g. "231_1ZoneUncontrolled"
        out_dir = OUTPUT_ROOT / stem
        for ext in (".eso", ".sql"):
            src = out_dir / (stem + ext)
            if src.exists():
                shutil.copy2(src, TEST_FILES / src.name)
                copied += 1
    print(f"  Copied {copied} file(s) to {TEST_FILES}")


def reset_idd() -> None:
    """Reset eppy's class-level IDD state between version groups."""
    try:
        IDF.resetidd()
    except IDDResetError:
        pass  # resetidd() always raises this after clearing state


def main() -> None:  # pylint: disable=too-many-locals, too-many-statements
    """Run every IDF in resources/, grouped by EnergyPlus version, and report timings."""
    idf_files = sorted(RESOURCES.glob("*.idf"))
    if not idf_files:
        print("No IDF files found in resources/")
        sys.exit(1)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    # Group jobs by EnergyPlus directory (one IDD per group).
    groups: dict[Path, list[tuple[Path, dict]]] = defaultdict(list)
    skipped: list[str] = []

    for idf_path in idf_files:
        ep_dir = find_energyplus_dir(idf_path)
        if ep_dir is None:
            print(f"[SKIP] {idf_path.name}  (no EnergyPlus installation found)")
            skipped.append(idf_path.name)
            continue
        out_dir = OUTPUT_ROOT / idf_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        # Do NOT include 'weather' here: prepare_run() already passes idf.epw
        # as a positional argument to run(), so adding it again causes
        # "multiple values for argument 'weather'".
        kwargs = {
            "output_directory": str(out_dir),
            "output_prefix": idf_path.stem,
            "ep_version": ep_dir.name.replace("EnergyPlusV", ""),
            "verbose": "q",
        }
        groups[ep_dir].append((idf_path, kwargs))

    if not groups:
        print("Nothing to run.")
        sys.exit(1)

    total_jobs = sum(len(v) for v in groups.values())
    print(f"Running {total_jobs} simulations across {len(groups)} EnergyPlus version(s)")
    print(f"using {os.cpu_count()} CPUs …\n")

    # runIDFs creates/removes a 'multi_runs/' dir relative to cwd.
    original_cwd = os.getcwd()
    os.chdir(OUTPUT_ROOT)

    wall_start = time.perf_counter()
    try:
        for ep_dir, jobs_for_version in groups.items():
            reset_idd()
            IDF.setiddname(str(ep_dir / "Energy+.idd"), testing=True)

            ep_label = ep_dir.name
            print(f"[{ep_label}]  {len(jobs_for_version)} simulation(s)")

            idf_jobs: list[tuple[IDF, dict]] = []
            for idf_path, kwargs in jobs_for_version:
                idf_jobs.append((IDF(str(idf_path), str(WEATHER)), kwargs))

            t0 = time.perf_counter()
            try:
                runIDFs(idf_jobs, processors=0)  # processors=0 → use all CPUs
            except EnergyPlusRunError as exc:
                print(f"  WARNING: one or more simulations failed: {exc}")
            elapsed = time.perf_counter() - t0

            print(f"  done in {elapsed:.1f}s\n")
    finally:
        os.chdir(original_cwd)

    wall_elapsed = time.perf_counter() - wall_start

    ran_idf_files = [idf_path for jobs in groups.values() for idf_path, _ in jobs]
    print("Copying outputs to tests/test_files/ …")
    copy_outputs_to_test_files(ran_idf_files)

    print("=" * 50)
    print(f"  Simulations run : {total_jobs}")
    if skipped:
        print(f"  Skipped         : {len(skipped)}")
        for name in skipped:
            print(f"    - {name}")
    print(f"  Wall-clock time : {wall_elapsed:.1f}s")
    print("=" * 50)


if __name__ == "__main__":
    main()
