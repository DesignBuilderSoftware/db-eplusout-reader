"""Run all IDF files in the resources folder with the bundled Chicago EPW.

Each IDF runs with the EnergyPlus installation that matches the ``Version``
object inside it (``C:/EnergyPlusV<major>-<minor>-*``), by calling that
installation's ``energyplus`` executable directly. Output files are written to
``resources/output/<stem>/`` and the ``.eso`` and ``.sql`` results are then
copied to ``tests/test_files/<stem>.eso`` / ``.sql``.

Simulations run in parallel, one EnergyPlus process per logical CPU. Each
installation reads its own ``Energy+.idd``, so IDFs for different versions can
run side by side.

    uv run python scripts/run_resource_models.py
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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


def energyplus_command(ep_dir: Path, idf_path: Path, out_dir: Path) -> list[str]:
    """The command line that runs one IDF with one EnergyPlus installation."""
    command = [
        str(ep_dir / "energyplus"),
        "--weather",
        str(WEATHER),
        "--output-directory",
        str(out_dir),
        "--output-prefix",
        idf_path.stem,
    ]
    if "hvactemplate:" in idf_path.read_text(encoding="utf-8", errors="replace").lower():
        command.append("--expandobjects")
    command.append(str(idf_path))
    return command


def run_one(ep_dir: Path, idf_path: Path) -> tuple[Path, float, str | None]:
    """Run one simulation; return the IDF, its run time and an error or None."""
    out_dir = OUTPUT_ROOT / idf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    result = subprocess.run(
        energyplus_command(ep_dir, idf_path, out_dir),
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - t0
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        return idf_path, elapsed, f"exit code {result.returncode}: " + " | ".join(tail)
    return idf_path, elapsed, None


def copy_outputs_to_test_files(idf_files: list[Path]) -> None:
    """Copy .eso and .sql outputs to tests/test_files/ using the IDF stem as name."""
    TEST_FILES.mkdir(parents=True, exist_ok=True)
    copied = 0
    for idf_path in idf_files:
        stem = idf_path.stem  # e.g. "231_1ZoneUncontrolled"
        out_dir = OUTPUT_ROOT / stem
        for ext in (".eso", ".sql"):
            # The legacy suffix style names the files <prefix>out.eso / .sql.
            for src in (out_dir / (stem + ext), out_dir / (stem + "out" + ext)):
                if src.exists():
                    shutil.copy2(src, TEST_FILES / (stem + ext))
                    copied += 1
                    break
    print(f"  Copied {copied} file(s) to {TEST_FILES}")


def collect_jobs(idf_files: list[Path]) -> tuple[list[tuple[Path, Path]], list[str]]:
    """Pair each IDF with its EnergyPlus installation; list the IDFs with none."""
    jobs: list[tuple[Path, Path]] = []
    skipped: list[str] = []
    for idf_path in idf_files:
        ep_dir = find_energyplus_dir(idf_path)
        if ep_dir is None:
            print(f"[SKIP] {idf_path.name}  (no EnergyPlus installation found)")
            skipped.append(idf_path.name)
        else:
            jobs.append((ep_dir, idf_path))
    return jobs, skipped


def run_jobs(jobs: list[tuple[Path, Path]]) -> list[str]:
    """Run the simulations in parallel; return the names of the IDFs that failed."""
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as pool:
        for idf_path, elapsed, error in pool.map(lambda job: run_one(*job), jobs):
            if error is None:
                print(f"  [OK]   {idf_path.name}  {elapsed:.1f}s")
            else:
                print(f"  [FAIL] {idf_path.name}  {error}")
                failed.append(idf_path.name)
    return failed


def print_summary(run: int, failed: list[str], skipped: list[str], seconds: float) -> None:
    """Print how many simulations ran, failed and were skipped, and the wall time."""
    print("=" * 50)
    print(f"  Simulations run : {run}")
    for label, names in (("Failed", failed), ("Skipped", skipped)):
        if names:
            print(f"  {label:<16}: {len(names)}")
            for name in names:
                print(f"    - {name}")
    print(f"  Wall-clock time : {seconds:.1f}s")
    print("=" * 50)


def main() -> None:
    """Run every IDF in resources/ with its EnergyPlus version and report timings."""
    idf_files = sorted(RESOURCES.glob("*.idf"))
    if not idf_files:
        print("No IDF files found in resources/")
        sys.exit(1)

    jobs, skipped = collect_jobs(idf_files)
    if not jobs:
        print("Nothing to run.")
        sys.exit(1)

    versions = sorted({ep_dir.name for ep_dir, _ in jobs})
    print(f"Running {len(jobs)} simulations with {', '.join(versions)}")
    print(f"using {os.cpu_count()} CPUs …\n")

    wall_start = time.perf_counter()
    failed = run_jobs(jobs)
    wall_elapsed = time.perf_counter() - wall_start

    print("\nCopying outputs to tests/test_files/ …")
    copy_outputs_to_test_files([idf_path for _, idf_path in jobs])

    print_summary(len(jobs), failed, skipped, wall_elapsed)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
