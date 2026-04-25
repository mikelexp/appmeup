# AppMeUp!

Desktop app for creating and editing Chromium-based web apps from `.desktop` launchers.

## Features

- Create user-level web app launchers in `~/.local/share/applications`
- Show AppMeUp-created web apps in the installed list
- Edit or uninstall installed AppMeUp web apps from the GUI
- Fetch site icons automatically when possible
- Refresh the desktop app menu and icon cache after changes

## Screenshots

![](screenshots/Screenshot_20260423_132155.png) 
![](screenshots/Screenshot_20260423_132222.png) 
![](screenshots/Screenshot_20260423_132239.png) 
![](screenshots/Screenshot_20260423_132300.png) 
![](screenshots/Screenshot_20260423_132317.png) 
![](screenshots/Screenshot_20260423_132336.png) 
![](screenshots/Screenshot_20260423_132410.png) 

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 appmeup.py
```

Open an existing launcher:

```bash
python3 appmeup.py ~/.local/share/applications/example.desktop
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
