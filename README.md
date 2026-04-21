# MK Web App Generator

A Python + PySide6 desktop app for creating and editing Chromium web apps from user-level `.desktop` files.

## Features

- Creates `.desktop` files in `~/.local/share/applications`
- Uses Chromium already installed on the system
- Can edit existing web apps if they are Chromium web apps
- Rejects `.desktop` files that do not look like web apps
- Tries to download the icon automatically from the website
- Runs `kbuildsycoca6` or an equivalent command to refresh Plasma

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 mkwebapp_generator.py
```

You can also open a `.desktop` file directly:

```bash
python3 mkwebapp_generator.py ~/.local/share/applications/mi-app.desktop
```

## Build with Nuitka

The generated binary includes the Python dependencies. Two build modes are provided:

- `standalone`: produces a self-contained directory in `dist/`
- `onefile`: produces a single executable that self-extracts at runtime

Install build dependencies:

```bash
./scripts/install-build-deps.sh
```

Build standalone:

```bash
./scripts/build-standalone.sh
```

Build onefile:

```bash
./scripts/build-onefile.sh
```

Clean build outputs:

```bash
./scripts/clean-build.sh
```

Expected outputs:

- `dist/mkwebapp_generator.dist/` for standalone
- `dist/mkwebapp_generator.dist/mkwebapp_generator.bin` as the standalone executable
- `dist/` will contain the Nuitka-generated onefile executable when using onefile mode
