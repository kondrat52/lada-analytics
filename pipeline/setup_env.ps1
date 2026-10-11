# One-time setup on a Windows PC with an NVIDIA GPU: a Python 3.12 environment at ~\.venvs\hockey with the
# pipeline's packages and a CUDA build of PyTorch, so detection runs on the GPU. setup_env.sh is the Mac version.
#   powershell -ExecutionPolicy Bypass -File pipeline\setup_env.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$envDir = if ($env:HOCKEY_ENV) { $env:HOCKEY_ENV } else { Join-Path $HOME ".venvs\hockey" }
$py = Join-Path $envDir "Scripts\python.exe"
if (Test-Path $py) {
    Write-Host "environment already exists: $envDir"
} else {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
        $env:Path = "$HOME\.local\bin;$env:Path"
    }
    uv venv -q --python 3.12 $envDir
    # torch first, from PyTorch's CUDA 12.8 wheels (RTX 50-series cards need 12.8 or later): installed after
    # ultralytics, pip would pick the CPU-only build
    uv pip install -q --python $py torch torchvision --index-url https://download.pytorch.org/whl/cu128
    uv pip install -q --python $py -r (Join-Path $here "requirements.txt")
}
# the pipeline reads and writes UTF-8 (the site, game.json); without this Windows Python uses the ANSI code page
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User"); $env:PYTHONUTF8 = "1"
& $py -c "import torch, ultralytics, rapidocr, yt_dlp; print('ok: torch', torch.__version__, '| cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
# run_period.py links each period's folder to the detections, and Windows allows symlinks only in Developer Mode
& $py -c "import os, tempfile; p = os.path.join(tempfile.gettempdir(), 'hockey-link-test'); os.path.lexists(p) and os.remove(p); os.symlink(r'$here\run_game.py', p); os.remove(p); print('ok: symlinks')"
if ($LASTEXITCODE -ne 0) { Write-Warning "Symlinks aren't allowed: turn on Developer Mode (Settings > System > For developers), then rerun this." }
