# Project

This repository contains a helper script for running a remote Chromium session.

## Setup

1. Start the remote browser helper.

## Run

In Codespaces, run the remote browser helper:

```bash
bash scripts/launch_remote_browser.sh
```

The port you want is:

1. `6080` for the remote browser / noVNC session.

If you are using VS Code, run the task named `Start browser environment` from the Command Palette or the Run Task menu.

## VS Code

Recommended extensions are listed in `.vscode/extensions.json`.

## Remote browser helper

The script in `scripts/launch_remote_browser.sh` prefers a real Google Chrome install first, then falls back to Chromium, plus system tools such as `Xvfb`, `x11vnc`, `websockify`, and noVNC.

## Downloads and file transfer

Files downloaded from the remote browser should go into the workspace `downloads/` folder. That keeps large files out of the repo while making them persistent across Codespaces reconnects.

Suggested flow:

1. Download the file in Chrome.
2. Move or save it into `downloads/` if it is not already there.
3. Transfer it out of the codespace with a direct download, `gh codespace cp`, or an external sync tool like `rclone` if you want Google Drive support.

For very large files, avoid putting them in git. Use the `downloads/` folder as the handoff point instead.
