# CuddleKine

CuddleKine is a desktop AI workbench for plush toy sampling. It helps plush toy designers and small studios turn customer briefs and reference images into plush sample images, local revision versions, front/side/back views, customer confirmation boards, and factory handoff PDFs.

## Download

The recommended way for non-developers is to download the Windows installer from GitHub Releases:

- Open the repository Releases page.
- Download `CuddleKine-Setup-x.x.x.exe` or the `.msi` installer.
- Install and open CuddleKine.
- Configure at least one image model provider in Settings.

Release packages are prepared with the scripts in [`scripts/`](scripts/). See [`docs/release/windows-installer.md`](docs/release/windows-installer.md) if you want to build an installer yourself.

## Screenshots

![CuddleKine home](docs/screenshots/01-cuddlekine-home.png)

![Project library](docs/screenshots/02-project-library.png)

![Brief workbench](docs/screenshots/03-brief-workbench.png)

![Generation workbench](docs/screenshots/04-generation-workbench.png)

## What It Does

- Order-based plush toy sampling workflow
- Reference image, sketch, screenshot, photo, and text material intake
- AI-assisted structured brief extraction and designer confirmation
- Provider selection with local and cloud image models
- OpenAI / Agnes / Replicate / local ComfyUI settings
- Tencent Cloud COS bridge for cloud image-to-image reference input
- Main plush sample generation with designer-led prompts
- Front / side / back multi-view generation
- Brush-mask local revision for a single view
- Customer confirmation image export
- Factory production PDF and ZIP export

## Quick Start for Users

1. Install CuddleKine from GitHub Releases.
2. Open the app and go to Settings.
3. Choose a provider, such as Agnes, OpenAI, Replicate, or ComfyUI.
4. Paste your provider API key.
5. If you use reference-image generation with Agnes, configure Tencent Cloud COS.
6. Create an order, upload references, confirm the brief, and generate a sample.

Detailed guides:

- [Install CuddleKine](docs/setup/install-cuddlekine.md)
- [Configure model providers](docs/setup/model-providers.md)
- [Configure Tencent Cloud COS](docs/setup/tencent-cos.md)
- [Common issues](docs/setup/troubleshooting.md)

## Tech Stack

- Frontend: React 19, Vite, TypeScript
- Desktop: Tauri 2
- Backend: FastAPI, SQLAlchemy, SQLite
- Image tooling: Pillow
- Local generation: ComfyUI workflows
- Cloud generation: OpenAI image API, Agnes API, Replicate API
- Cloud image bridge: Tencent Cloud COS signed URLs
- Packaging: Tauri bundler, PyInstaller

## Project Structure

```text
backend/              FastAPI backend service
backend/app/routes/   API routes for orders, materials, generation, export, settings
backend/app/services/ Provider adapters and image processing services
comfyui/workflows/    ComfyUI workflow templates
desktop/              React + Tauri desktop app
docs/                 Setup guides, release guides, screenshots, notes
scripts/              Release build scripts
```

## Development Setup

Install frontend dependencies:

```powershell
cd desktop
npm install
```

Install backend dependencies:

```powershell
cd ..
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend\requirements.txt
```

Run the desktop app:

```powershell
cd desktop
npm run tauri dev
```

During development, the backend API uses `http://127.0.0.1:8765`.

## Build a Windows Installer

```powershell
.\scripts\build_windows_installer.ps1
```

The script packages the FastAPI backend with PyInstaller, copies bundled resources for Tauri, and builds the desktop installer. Output files are under:

```text
desktop/src-tauri/target/release/bundle
```

## Security Notes

Never commit:

- `data/provider_settings.json`
- SQLite databases in `data/`
- generated images in `outputs/`
- API keys, COS SecretId, COS SecretKey, or provider tokens

If a token was pasted into a public issue, chat, screenshot, or commit, revoke it from the provider dashboard and create a new one.

## Development Checks

```powershell
python -m compileall backend\app
cd desktop
npm run build
cd src-tauri
cargo check
```

## License

No open-source license has been selected yet.
