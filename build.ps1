# Build Local Chat Launcher into a standalone Windows app with PyInstaller.
# Output: dist\LocalChatLauncher\  (exe + _internal + llama\ engine).
# Run setup.ps1 first so the llama\ engine folder exists. The model file is NOT copied (chosen in the app).
param([string]$Python = "python")
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path "llama\llama-server.exe")) { throw "llama\llama-server.exe not found. Run .\setup.ps1 first." }
& $Python -m PyInstaller --noconfirm --clean --onedir --windowed --name LocalChatLauncher --distpath dist --workpath build --specpath build `
  --exclude-module PyQt5 --exclude-module PySide6 --exclude-module PyQt6.QtWebEngineWidgets --exclude-module PyQt6.QtWebEngineCore `
  --exclude-module tkinter --exclude-module matplotlib --exclude-module numpy --exclude-module pandas qwen_launcher.py
$d = "dist\LocalChatLauncher"
New-Item -ItemType Directory -Force "$d\llama" | Out-Null
Copy-Item "llama\*" "$d\llama\" -Recurse -Force
Copy-Item "README.md" $d -Force
"Built: $((Resolve-Path $d).Path)"
