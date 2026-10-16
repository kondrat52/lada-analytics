# Setting up a Windows PC

Detection, the slow step of `/process-game` (~2 h on the Mac's GPU), runs on CUDA on a Windows PC with an NVIDIA
GPU (RTX 5090 here): about 10 to 25 minutes per game, and fetch as a whole about 30. Everything else works the same
as on the Mac. `RUNBOOK.md` and the process-game skill cover the pipeline itself; this page is the one-time setup.
Every game since October 2026 has been processed this way.

## Quick setup: one script

In PowerShell (no need to run it as administrator):

```powershell
irm https://raw.githubusercontent.com/kondrat52/lada-analytics/main/setup_windows.ps1 | iex
```

`setup_windows.ps1` does steps 1–6 below: it checks the NVIDIA driver, installs Git and Claude Code, turns on
Developer Mode and adds the Defender exclusion (Windows asks once for admin rights), clones the repo to
`~\lada-analytics`, sets the git identity and builds the Python environment. It ends with a list of anything
that needs attention, and it is safe to run again. Then go on with step 7.

The steps by hand:

## 1. NVIDIA driver

In PowerShell:

```powershell
nvidia-smi
```

It should list the RTX 5090, a driver version of 570 or newer, and "CUDA Version: 12.8" or higher. If not, update
the driver (NVIDIA app or nvidia.com; Game Ready or Studio).

## 2. Git for Windows

Claude Code runs its shell commands in Git's bash, and the pipeline's commands are written for it.

```powershell
winget install --id Git.Git -e
```

## 3. Claude Code

```powershell
irm https://claude.ai/install.ps1 | iex
```

Open a **new** PowerShell window, then check with `claude --version` (`claude doctor` for a fuller check).

## 4. Developer Mode

The pipeline links each period's folder to the detections, and Windows allows symlinks only in Developer Mode.
Search "developer settings" in Start and turn **Developer Mode** on.

## 5. Clone the repo and set the git identity

```powershell
cd $HOME
git clone https://github.com/kondrat52/lada-analytics.git
cd lada-analytics
git config --global user.name "kondrat52"
git config --global user.email "151690973+kondrat52@users.noreply.github.com"
```

The first `git push` opens a browser window to sign in to GitHub.

## 6. Python environment

About 3–4 GB to download, mostly PyTorch:

```powershell
powershell -ExecutionPolicy Bypass -File pipeline\setup_env.ps1
```

It should end with:

```
ok: torch 2.x+cu128 | cuda True NVIDIA GeForce RTX 5090
ok: symlinks
```

`cuda False` means the driver (step 1); a symlink warning means Developer Mode is off (step 4). The script also
sets `PYTHONUTF8=1` for your user, since the pipeline reads and writes UTF-8.

Optional but recommended: in Windows Security, Virus & threat protection, add `C:\Users\<you>\hockey-work` as an
exclusion. A game writes about 250k small crop files there, and real-time scanning can slow that down a lot.

## 7. First run

Start Claude Code in the repo folder (`claude`), log in through the browser, and test before a real game by
pasting:

> Test the pipeline on this Windows PC before a real game. Check that `~/.venvs/hockey/Scripts/python.exe` sees
> CUDA. Then run `run_game.py fetch https://youtu.be/406X511W3gg ~/hockey-work/test --rink snoqualmie2 --jersey
> white --bench left --limit 120` (Oct 10 vs TTT, already published from the Mac). Tell me the detection rate in
> fps from `full/log.txt`. The Mac does about 4.4 fps. If anything Windows-specific breaks (paths, symlinks,
> encoding, ffmpeg), fix it in the pipeline and tell me what you changed. Don't publish anything, and delete
> `~/hockey-work/test` when done.

That downloads the 2.7 GB video and detects 2 minutes of it, which gives a real speed number. After that,
`/process-game <link>` works as on the Mac, with `PY=~/.venvs/hockey/Scripts/python.exe` and no `caffeinate`
(`run_game.py` keeps Windows awake while it runs).

Claude Code's memory lives per machine (`%USERPROFILE%\.claude`), so notes from the Mac don't carry over; the
rules that matter for processing a game are in the skill.
