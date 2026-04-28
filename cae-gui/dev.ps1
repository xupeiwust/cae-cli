$ErrorActionPreference = "Stop"

$ProjectDir = "E:\cae-cli\cae-gui"
$RustBin = "E:\C_Drive_Migration\Users\yd576\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin"
$MsVcBin = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64"
$MsVcLib = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\lib\x64"
$SdkLib = "C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0\um\x64"
$SdkUcrt = "C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0\ucrt\x64"
$MsVcInc = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\include"
$SdkIncUm = "C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\um"
$SdkIncUcrt = "C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\ucrt"
$SdkIncShared = "C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\shared"

Write-Host "=== cae-gui Dev Launcher ===" -ForegroundColor Cyan

$env:PATH = "$MsVcBin;$RustBin;" + $env:PATH
$env:CARGO_HOME = "E:\C_Drive_Migration\Users\yd576\.rustup"
$env:RUSTUP_HOME = "E:\C_Drive_Migration\Users\yd576\.rustup"
$env:LIB = "$MsVcLib;$SdkLib;$SdkUcrt"
$env:INCLUDE = "$MsVcInc;$SdkIncUm;$SdkIncUcrt;$SdkIncShared"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[OK] Env vars set" -ForegroundColor Green
Write-Host "  Rust: $RustBin"
Write-Host "  MSVC: $MsVcBin"
Write-Host "  LIB : $env:LIB"
Write-Host ""

Set-Location $ProjectDir
Write-Host "[OK] CD: $ProjectDir"
Write-Host ""

Write-Host ">>> Starting tauri dev ..." -ForegroundColor Yellow
npm run tauri dev
