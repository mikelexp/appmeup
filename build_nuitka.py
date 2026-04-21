#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_SCRIPT = PROJECT_ROOT / "mkwebapp_generator.py"
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"

def build_command(onefile: bool) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--assume-yes-for-downloads",
        "--standalone",
        "--enable-plugin=pyside6",
        "--include-qt-plugins=platforms,platformthemes,iconengines,imageformats,wayland-shell-integration,wayland-decoration-client,wayland-graphics-integration-client,xcbglintegrations",
        "--output-dir=" + str(DIST_DIR),
        "--remove-output",
        "--show-progress",
        "--show-scons",
        "--follow-imports",
        "--python-flag=no_site",
        "--warn-unusual-code",
        "--company-name=MK",
        "--product-name=MK Web App Generator",
        "--file-description=Create and edit Chromium web apps from .desktop files",
        "--file-version=1.0.0",
        "--product-version=1.0.0",
        "--nofollow-import-to=tkinter,test,unittest,pydoc",
        str(MAIN_SCRIPT),
    ]

    if onefile:
        command.append("--onefile")

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
        PROJECT_ROOT / "mkwebapp_generator.build",
        PROJECT_ROOT / "mkwebapp_generator.dist",
        PROJECT_ROOT / "mkwebapp_generator.onefile-build",
    ]
    for target in targets:
        if target.is_dir():
            shutil.rmtree(target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build MK Web App Generator with Nuitka.")
    parser.add_argument("--onefile", action="store_true", help="Build a onefile binary instead of standalone.")
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
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
