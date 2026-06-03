# CuddleKine

CuddleKine is a desktop workbench for plush toy sampling. It helps small studios, toy designers, and factory teams turn customer briefs and reference images into plush toy sample images, revision versions, multi-view sheets, and exportable confirmation boards.

The project combines a local desktop UI, a FastAPI backend, and pluggable image providers such as ComfyUI, OpenAI image models, and Replicate.

## Highlights

- Order-based plush toy sampling workflow
- Reference image upload and material management
- Structured customer brief fields for character, colors, size, materials, accessories, and key features
- AI image generation with provider selection
- OpenAI / Replicate / local ComfyUI provider configuration
- Transparent-background-first sample output workflow
- Main view generation, local revision, front/side/back multi-view generation
- Customer confirmation board and factory package export
- Local desktop app powered by Tauri

## Tech Stack

- Frontend: React 19, Vite, TypeScript
- Desktop: Tauri 2
- Backend: FastAPI, SQLAlchemy, SQLite
- Image tooling: Pillow
- Local generation: ComfyUI workflows
- Cloud generation: OpenAI image API and Replicate API

## Project Structure

```text
backend/              FastAPI backend service
backend/app/routes/   API routes for orders, materials, generation, export, settings
backend/app/services/ Provider adapters and image processing services
comfyui/workflows/    ComfyUI workflow templates
desktop/              React + Tauri desktop app
docs/                 Product and implementation planning notes
```

## Requirements

- Node.js 20+
- Python 3.12+
- Rust and Cargo
- Optional: local ComfyUI installation
- Optional: OpenAI API key
- Optional: Replicate API token

## Quick Start

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

The Tauri app starts the local backend automatically when possible.

## Provider Setup

Open the CuddleKine desktop app and click **Settings** in the top status bar.

You can configure:

- Default provider
- Default model
- Default quality mode
- Transparent background preference
- OpenAI API key
- Replicate API token
- ComfyUI API URL
- ComfyUI input directory

API keys are stored locally in `data/provider_settings.json`. This file is ignored by Git.

## ComfyUI Notes

CuddleKine ships with basic workflow templates in `comfyui/workflows`.

For reference-image workflows, make sure the ComfyUI input directory in Settings points to the active ComfyUI `input` folder. Otherwise ComfyUI cannot load uploaded reference images.

## Security Notes

Never commit:

- `data/provider_settings.json`
- SQLite databases in `data/`
- generated images in `outputs/`
- API keys or tokens

If a token was pasted into a public issue, chat, or commit, revoke it from the provider dashboard and create a new one.

## Development Checks

Backend syntax check:

```powershell
python -m compileall backend\app
```

Frontend build:

```powershell
cd desktop
npm run build
```

Tauri Rust check:

```powershell
cd desktop\src-tauri
cargo check
```

## Roadmap

- Better prompt presets for different plush categories
- Provider-specific cost estimates
- Stronger reference-image preservation controls
- Model capability badges and provider health diagnostics
- Design board templates for customer review
- Factory-ready specification export

## License

No open-source license has been selected yet.
