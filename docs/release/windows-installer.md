# Build and Publish a Windows Installer

This guide explains how to create a Windows installer that non-developers can download from GitHub Releases.

## What the Installer Includes

The release build includes:

- Tauri desktop app
- React frontend build
- PyInstaller-packaged FastAPI backend
- ComfyUI workflow templates
- app icons and bundled resources

The installer does not include user API keys or local generated images.

## Prerequisites for Release Maintainers

Install:

- Node.js 20+
- Python 3.12+
- Rust and Cargo
- Visual Studio Build Tools for Rust/Tauri
- Git

## Build

From the project root:

```powershell
.\scripts\build_windows_installer.ps1
```

If Windows blocks local PowerShell scripts, run the script with a one-time bypass:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_installer.ps1
```

The script does three things:

1. Builds `release/backend/cuddlekine-backend.exe` with PyInstaller.
2. Copies the backend exe and workflow templates into Tauri resources.
3. Runs `npm run tauri build`.

Installer artifacts are created under:

```text
desktop/src-tauri/target/release/bundle
```

## Test Before Publishing

Before uploading to GitHub Releases:

- install the generated package on a clean Windows machine or VM
- open CuddleKine
- confirm backend status is connected
- configure a test provider
- generate one mock image
- generate one real provider image if budget allows
- export customer board and factory PDF
- confirm no API key is bundled in the installer

## Publish on GitHub

1. Create a version tag, for example:

```powershell
git tag -a v1.2.0 -m "CuddleKine v1.2.0"
git push origin v1.2.0
```

2. Open GitHub Releases.
3. Draft a new release from the tag.
4. Upload the installer files from `desktop/src-tauri/target/release/bundle`.
5. Add release notes using [`github-release-template.md`](github-release-template.md).

## Important Security Rule

Do not upload:

- local `data/`
- local `outputs/`
- `provider_settings.json`
- `.env`
- screenshots showing full API keys
