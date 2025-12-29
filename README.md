# Qianwen Bilibili Notes

## One-time setup (Windows PowerShell)

```powershell
./scripts/setup.ps1
```

Or double-click:

```text
scripts/setup.cmd
```

This script:
- Installs Python + Node.js via winget (if missing)
- Downloads ffmpeg into `tools/ffmpeg`
- Creates backend venv and installs Python deps
- Installs frontend deps

## Start the app

```powershell
./scripts/start.ps1
```

Or double-click:

```text
scripts/start.cmd
```

## First run (setup + start)

```powershell
./scripts/first-run.ps1
```

Or double-click:

```text
scripts/first-run.cmd
```

## Notes
- If you already have ffmpeg, set `FFMPEG_LOCATION` to its path to override.
- DashScope base URL can be overridden with `DASHSCOPE_BASE_URL`.
