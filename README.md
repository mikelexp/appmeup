# AppMeUp!

A desktop app for creating and editing Chromium-based web apps in Linux.

## Features

- Create user-level web app launchers in `~/.local/share/applications`
- Show AppMeUp-created web apps in the installed list
- Edit or uninstall installed AppMeUp web apps from the GUI
- Use `New WebApp` and `Save WebApp` actions in the app UI
- Fetch site icons automatically when possible
- Refresh the desktop app menu and icon cache after changes
- Read XDG menu locations through `pyxdg` so category discovery follows the active DE
- Filter Chromium parameters by name or description in the options tab

## Screenshots

![](screenshots/Screenshot_20260423_132155.png) 
![](screenshots/Screenshot_20260423_132222.png) 
![](screenshots/Screenshot_20260423_132239.png) 
![](screenshots/Screenshot_20260423_132300.png) 
![](screenshots/Screenshot_20260423_132317.png) 
![](screenshots/Screenshot_20260423_132336.png) 
![](screenshots/Screenshot_20260423_132410.png) 

## Requirements

- Python 3.13

## Run

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python appmeup.py
```

## Build

```bash
./scripts/install-build-deps.sh
./scripts/build-standalone.sh
# or
./scripts/build-onefile.sh
```

Install a built binary locally:

```bash
./scripts/install.sh
```
