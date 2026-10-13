# One-time setup of a Windows 11 PC with an NVIDIA GPU for this pipeline (WINDOWS.md has the same steps by hand).
# In PowerShell:
#   irm https://raw.githubusercontent.com/kondrat52/lada-analytics/main/setup_windows.ps1 | iex
# Safe to run again: each step skips what is already done. Windows asks once for admin rights (Developer Mode and a
# Defender exclusion for the work folder). The NVIDIA driver is only checked, not installed.

function Install-HockeyPC {
    $ErrorActionPreference = "Stop"
    $repoUrl = "https://github.com/kondrat52/lada-analytics.git"
    $repo = if ($env:HOCKEY_REPO) { $env:HOCKEY_REPO } else { Join-Path $HOME "lada-analytics" }
    $work = Join-Path $HOME "hockey-work"
    $problems = @()

    function Step($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }
    function Refresh-Path {
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                    [Environment]::GetEnvironmentVariable("Path", "User") + ";" + (Join-Path $HOME ".local\bin")
    }
    function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

    Step "NVIDIA driver"
    if (Have "nvidia-smi") {
        $gpu = (& nvidia-smi --query-gpu=name,driver_version --format=csv,noheader | Select-Object -First 1)
        Write-Host $gpu
        $ver = [double](($gpu -split ",")[-1].Trim() -replace "^(\d+\.\d+).*", '$1')
        if ($ver -lt 570) {
            $problems += "NVIDIA driver $ver is older than 570, which RTX 50-series cards need for CUDA 12.8: update it (NVIDIA app or nvidia.com)."
        }
    } else {
        $problems += "nvidia-smi not found: install the NVIDIA driver (NVIDIA app or nvidia.com), then run this again."
    }

    Step "Git for Windows"
    if (-not (Have "git")) {
        if (-not (Have "winget")) { throw "winget is missing: install 'App Installer' from the Microsoft Store, then run this again." }
        winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
        Refresh-Path
        if (-not (Have "git")) { throw "Git was installed but isn't on PATH yet: open a new PowerShell window and run this again." }
    }
    git --version

    Step "Claude Code"
    if (-not (Have "claude")) {
        # in a child PowerShell, so nothing the installer does can end this script
        & powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://claude.ai/install.ps1 | iex"
        Refresh-Path
    }
    if (Have "claude") { claude --version } else { $problems += "Claude Code didn't install: run 'irm https://claude.ai/install.ps1 | iex' by hand." }

    Step "Developer Mode (symlinks) and a Defender exclusion for $work"
    New-Item -ItemType Directory -Force -Path $work | Out-Null
    $key = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"
    $dev = (Get-ItemProperty -Path $key -Name AllowDevelopmentWithoutDevLicense -ErrorAction SilentlyContinue).AllowDevelopmentWithoutDevLicense
    if ($dev -eq 1) {
        Write-Host "Developer Mode is already on."
    } else {
        Write-Host "Windows will ask for admin rights to turn on Developer Mode and exclude $work from real-time scanning."
        $cmd = "if (-not (Test-Path '$key')) { New-Item -Path '$key' | Out-Null }; " +
               "Set-ItemProperty -Path '$key' -Name AllowDevelopmentWithoutDevLicense -Type DWord -Value 1; " +
               "try { Add-MpPreference -ExclusionPath '$work' } catch { }"
        $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($cmd))
        try {
            Start-Process powershell -Verb RunAs -Wait -ArgumentList "-NoProfile -EncodedCommand $enc"
        } catch {
            $problems += "Admin rights were declined: turn on Developer Mode by hand (search 'developer settings' in Start)."
        }
    }

    Step "Repository in $repo"
    if (Test-Path (Join-Path $repo ".git")) {
        git -C $repo remote set-url origin $repoUrl   # a clone from before the repo was renamed
        git -C $repo pull --ff-only
    } else {
        git clone $repoUrl $repo
    }
    if (-not (git config --global user.name)) { git config --global user.name "kondrat52" }
    if (-not (git config --global user.email)) { git config --global user.email "151690973+kondrat52@users.noreply.github.com" }

    Step "Python environment (PyTorch for CUDA, ~3-4 GB the first time)"
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "pipeline\setup_env.ps1")
    if ($LASTEXITCODE -ne 0) { $problems += "pipeline\setup_env.ps1 failed: see its output above." }

    Step "Done"
    if ($problems.Count) {
        Write-Host "Needs attention:" -ForegroundColor Yellow
        $problems | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    } else {
        Write-Host "Everything is set up." -ForegroundColor Green
    }
    Write-Host "`nNext: open a NEW PowerShell window, then"
    Write-Host "  cd $repo"
    Write-Host "  claude"
    Write-Host "log in, and paste the first-run test prompt from WINDOWS.md (step 7)."
}

Install-HockeyPC
