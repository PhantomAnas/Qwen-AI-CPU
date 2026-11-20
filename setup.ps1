# One-time setup: installs Python packages, downloads the llama.cpp CPU engine into .\llama
# and (optionally) the Qwen3.6-35B-A3B GGUF model into .\models.
#   .\setup.ps1                 -> packages + engine
#   .\setup.ps1 -DownloadModel  -> also downloads the model (large, several GB)
param(
  [switch]$DownloadModel,
  [string]$Python = "python",
  [string]$LlamaBuild = "b12561",
  [string]$ModelFile = "Qwen3.6-35B-A3B-UD-IQ3_XXS.gguf"
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # makes Invoke-WebRequest much faster
Set-Location $PSScriptRoot

Write-Host "1/3 Installing Python packages..." -ForegroundColor Cyan
& $Python -m pip install -r requirements.txt

Write-Host "2/3 Downloading llama.cpp $LlamaBuild (Windows CPU x64)..." -ForegroundColor Cyan
if (Test-Path "llama\llama-server.exe") {
  Write-Host "    llama\llama-server.exe already exists, skipping."
} else {
  $zip = Join-Path $env:TEMP "llama-$LlamaBuild-bin-win-cpu-x64.zip"
  $url = "https://github.com/ggml-org/llama.cpp/releases/download/$LlamaBuild/llama-$LlamaBuild-bin-win-cpu-x64.zip"
  Invoke-WebRequest $url -OutFile $zip
  New-Item -ItemType Directory -Force "llama" | Out-Null
  Expand-Archive $zip -DestinationPath "llama" -Force
  # some releases nest files in a subfolder -> flatten
  $srv = Get-ChildItem "llama" -Recurse -Filter "llama-server.exe" | Select-Object -First 1
  if ($srv -and $srv.DirectoryName -ne (Resolve-Path "llama").Path) { Move-Item "$($srv.DirectoryName)\*" "llama\" -Force }
  Remove-Item $zip
}

if ($DownloadModel) {
  Write-Host "3/3 Downloading model $ModelFile (this is big, be patient)..." -ForegroundColor Cyan
  New-Item -ItemType Directory -Force "models" | Out-Null
  $out = "models\$ModelFile"
  if (Test-Path $out) { Write-Host "    $out already exists, skipping." }
  else { Invoke-WebRequest "https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/resolve/main/$ModelFile" -OutFile $out }
} else {
  Write-Host "3/3 Model download skipped. Re-run with -DownloadModel, or download it manually (see README)." -ForegroundColor Yellow
}
Write-Host "Done. Start the app with:  $Python qwen_launcher.py" -ForegroundColor Green
