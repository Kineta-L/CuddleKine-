# CuddleKine Release Distribution Design

## Goal

Make CuddleKine usable by non-developers through a downloadable Windows installer and clear GitHub documentation.

## Assumptions

- The first public target is Windows.
- Users should not need to install Node.js, Python, Rust, Cargo, or FastAPI.
- Users will provide their own model API keys and Tencent Cloud COS credentials.
- CuddleKine must not bundle or publish any local secrets.

## Approach

Use Tauri for the desktop installer and PyInstaller for the FastAPI backend. The Tauri app starts a bundled `cuddlekine-backend.exe` in release builds and falls back to the existing Python `backend/run.py` flow in development builds.

## Runtime Paths

Development mode keeps using project-local `data/`, `outputs/`, and `comfyui/workflows/`.

Release mode sets environment variables before starting the backend:

- `CUDDLEKINE_APP_ROOT`
- `CUDDLEKINE_RESOURCE_DIR`
- `CUDDLEKINE_DATA_DIR`
- `CUDDLEKINE_OUTPUT_DIR`

This keeps user data out of the installation directory.

## Documentation

GitHub should provide:

- a simple README product overview
- installation guide
- model provider configuration guide
- Tencent Cloud COS guide
- troubleshooting guide
- Windows installer build guide
- GitHub Release template

## Success Criteria

- A developer can run one PowerShell script to build a Windows installer.
- The installed app can start the bundled backend without Python being installed.
- New users can understand how to configure provider API keys and Tencent COS.
- Secrets and generated assets remain ignored by Git.
