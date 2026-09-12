#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_SCRIPT = PROJECT_ROOT / "appmeup.py"
ICON_FILE = PROJECT_ROOT / "icon.png"
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"

def build_command(onefile: bool) -> list[str]:
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.constants import APP_VERSION
    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--assume-yes-for-downloads",
        "--mode=accelerated",
        "--output-filename=appmeup.bin",
        "--output-dir=" + str(DIST_DIR),
        "--remove-output",
        "--show-progress",
        "--show-scons",
        "--python-flag=site",
        "--warn-unusual-code",
        "--company-name=Mikele",
        "--product-name=App Me Up",
        "--file-description=Create and edit Chromium web apps from .desktop files",
        f"--file-version={APP_VERSION}.0",
        f"--product-version={APP_VERSION}.0",
        "--nofollow-import-to=tkinter,test,unittest,pydoc,PySide6,shiboken6,src",
        f"--include-data-files={ICON_FILE}=icon.png",
        f"--include-data-dir={PROJECT_ROOT / 'src'}=src",
        str(MAIN_SCRIPT),
    ]

    return command


def ensure_dirs() -> None:
    BUILD_DIR.mkdir(exist_ok=True)
    DIST_DIR.mkdir(exist_ok=True)
    (BUILD_DIR / ".cache").mkdir(exist_ok=True)


def clean() -> None:
    targets = [
        BUILD_DIR,
        DIST_DIR,
        PROJECT_ROOT / "__pycache__",
        PROJECT_ROOT / "appmeup.build",
        PROJECT_ROOT / "appmeup.dist",
        PROJECT_ROOT / "appmeup.onefile-build",
        PROJECT_ROOT / "appmeup.bin",
    ]
    for target in targets:
        if target.is_dir():
            shutil.rmtree(target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build App Me Up with Nuitka.")
    parser.add_argument("--onefile", action="store_true", help="Legacy compatibility option; builds accelerated mode.")
    parser.add_argument("--clean", action="store_true", help="Remove build artifacts before building.")
    parser.add_argument("--clean-only", action="store_true", help="Only remove build artifacts.")
    args = parser.parse_args()

    if args.clean or args.clean_only:
        clean()
    if args.clean_only:
        return 0

    ensure_dirs()
    command = build_command(onefile=args.onefile)
    print("Running:", " ".join(command))
    env = os.environ.copy()
    env["XDG_CACHE_HOME"] = str(BUILD_DIR / ".cache")
    completed = subprocess.run(command, cwd=PROJECT_ROOT, env=env)
    if completed.returncode == 0:
        shutil.copytree(
            PROJECT_ROOT / "src",
            DIST_DIR / "src",
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        shutil.copy2(ICON_FILE, DIST_DIR / "icon.png")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
