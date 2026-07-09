# Project

This repository contains a small Flask browser project plus a helper script for running a remote Chromium session.

## Setup

1. Create and activate a virtual environment.
2. Install the Python dependencies:

```bash
pip install -r requirements.txt
```

3. On Linux, install the Playwright system libraries:

```bash
python -m playwright install-deps chromium
```

4. Install the Playwright browser binary used by the app:

```bash
python -m playwright install chromium
```

## Run

Start the app locally with:

```bash
python test.py
```

Run the tests with:

```bash
python -m unittest
```

## VS Code

Recommended extensions are listed in `.vscode/extensions.json`.

## Remote browser helper

The script in `scripts/launch_remote_browser.sh` expects a working Chromium binary plus system tools such as `Xvfb`, `x11vnc`, `websockify`, and noVNC to be available on the machine.
