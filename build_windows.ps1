$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$requiredFiles = @(
    "main.py", "app_webview.py", "app_support.py", "optimizations.py", "gaming.py",
    "game_preparation.py", "hardware_telemetry.py", "history.py", "network_lab.py",
    "performance_lab.py", "ui_settings.py", "window_lifecycle.py",
    "requirements.txt", "requirements-build.txt", "test_ui.cjs",
    "test_improvements.py", "test_window_lifecycle.py", "test_compatibility.py",
    "ui/index.html", "ui/app.js", "ui/style.css"
)
foreach ($requiredFile in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Arquivo ausente: $requiredFile. Use o conteúdo completo da pasta SHADOW OPTIMIZER."
    }
}

# Confirma a versão do Python no PATH; usa o launcher 3.12 como alternativa.
$env:PYTHONUTF8 = "1"
$buildEnv = Join-Path $PSScriptRoot ".venv-build-win"
$python = Join-Path $buildEnv "Scripts\python.exe"
$pythonReady = $false
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python -c "import sys; sys.exit(0 if (3,12) <= sys.version_info[:2] < (3,15) else 1)"
    $pythonReady = ($LASTEXITCODE -eq 0)
}
if ($pythonReady) {
    & python -m venv --clear $buildEnv
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.12 -m venv --clear $buildEnv
} else {
    throw "Instale Python 3.12 com o launcher py ou adicione-o ao PATH."
}

if ($LASTEXITCODE -ne 0) { throw "Não foi possível criar o ambiente de compilação." }
& $python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "Não foi possível instalar as dependências de compilação." }

& $python -m unittest discover -p "test_*.py" -v
if ($LASTEXITCODE -ne 0) { throw "Testes falharam; a compilação foi interrompida." }

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name Shadow `
    --add-data "ui;ui" `
    --collect-data webview `
    --hidden-import webview.platforms.winforms `
    --hidden-import webview.platforms.win32 `
    --hidden-import webview.platforms.edgechromium `
    --collect-all pythonnet `
    --collect-all clr_loader `
    --collect-all psutil `
    --exclude-module webview.platforms.gtk `
    --exclude-module webview.platforms.qt `
    --exclude-module webview.platforms.android `
    --exclude-module webview.platforms.cef `
    --exclude-module webview.platforms.cocoa `
    --exclude-module PyQt5 `
    --exclude-module PyQt6 `
    --exclude-module PySide2 `
    --exclude-module PySide6 `
    --exclude-module gi `
    main.py

if ($LASTEXITCODE -ne 0) {
    throw "A compilação falhou. Veja as mensagens acima."
}

$exePath = Join-Path $PSScriptRoot "dist\Shadow.exe"
$sizeMb = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
Write-Host "Shadow compilado: $exePath ($sizeMb MB)"
Write-Host "O Microsoft Edge WebView2 Runtime é necessário no Windows de destino e não é incluído para manter o pacote menor."
