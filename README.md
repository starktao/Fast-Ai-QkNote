# Qianwen Bilibili Notes

## One-time setup (Windows)

```text
scripts\setup.cmd
```

This script:
- Installs Python + Node.js via winget (if missing)
- Downloads ffmpeg into `tools/ffmpeg`
- Creates backend venv and installs Python deps
- Installs frontend deps

## Start the app

```text
scripts\start.cmd
```

## First run (setup + start)

```text
scripts\first-run.cmd
```

## Notes
- If you already have ffmpeg, set `FFMPEG_LOCATION` to its path to override.
- DashScope base URL can be overridden with `DASHSCOPE_BASE_URL`.
