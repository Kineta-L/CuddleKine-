# Install CuddleKine

This guide is for designers and studio users who want to use CuddleKine without setting up a development environment.

## Recommended Install Method

1. Open the CuddleKine GitHub Releases page.
2. Download the latest Windows installer:
   - `CuddleKine-Setup-x.x.x.exe`, or
   - `CuddleKine_x.x.x_x64_en-US.msi`
3. Double-click the installer.
4. Open CuddleKine from the Start menu or desktop shortcut.
5. Go to Settings and configure a model provider.

You do not need to install Node.js, Python, Rust, Cargo, or FastAPI when using the release installer.

## First Launch Checklist

- Open Settings.
- Select the default provider.
- Enter the provider API key.
- Configure Tencent Cloud COS if you want cloud models to read local reference images.
- Click the connection test buttons where available.
- Create a test order and generate one sample image.

## Where Local Data Is Stored

The release build stores user data in the system application data directory, not in the installation directory.

Typical content includes:

- local SQLite database
- uploaded reference materials
- generated images
- provider settings

Do not share the local settings file publicly because it may contain API keys.

## Development Install

Developers can still run from source:

```powershell
cd desktop
npm install
npm run tauri dev
```

See the README for backend dependency setup.
