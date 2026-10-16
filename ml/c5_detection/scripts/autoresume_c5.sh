#!/usr/bin/env bash
# PRHAAR C5 logon auto-resume -- restores the training pipeline after any
# reboot / power-off (measured need: user power-offs on 2026-10-14 10:54 and
# 13:12 killed trainer+chain; boot on 2026-10-15 found nothing running).
#
# Triggered at user logon via Startup\PRHAAR_C5_autoresume.bat. Steps
# (all idempotent, safe to run any time):
#   1. if exp001 incomplete and no trainer alive: resume from last.pt
#   2. start watchdog_c5.sh if not running
#   3. start run_sweep_302.sh if not running
#
# Disable: create an empty file named NO_AUTORESUME in ml/c5_detection/
# (or delete the Startup .bat). Operations recorded in logs/autoresume.log.

set -u
cd "$(dirname "$0")/.." || exit 1

PY="C:/Users/harsh/AppData/Local/Programs/Python/Python311/python.exe"
DATA="datasets/PRHAAR-C5-DETECTION/data.yaml"
LOG="logs/autoresume.log"

note() { echo "[autoresume $(date '+%F %T')] $*" >> "$LOG"; }

experiment_done() { [ -f "training/runs/$1/run_manifest.json" ]; }

proc_count() { # PowerShell Where-Object script fragment -> integer (0 on error)
  local n
  n=$(powershell -NoProfile -Command "($1 | Measure-Object).Count" 2>/dev/null | tr -d '\r\n ')
  echo "${n:-0}"
}

trainer_alive() {
  proc_count '(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "train_detector" })' | grep -qE "^[1-9]"
}

watchdog_alive() {
  # exclude Qoder wrapper shells (they contain the script name in cmdline)
  proc_count '(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "bash.exe" -and $_.CommandLine -match "watchdog_c5" -and $_.CommandLine -notmatch "qoder|snapshot" })' | grep -qE "^[1-9]"
}

chain_alive() {
  proc_count '(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "bash.exe" -and $_.CommandLine -match "run_sweep_302" -and $_.CommandLine -notmatch "qoder|snapshot" })' | grep -qE "^[1-9]"
}

if [ -f NO_AUTORESUME ]; then
  note "NO_AUTORESUME flag present -- standing down"
  exit 0
fi

note "logon hook fired"

# 1) trainer: resume exp001 only if its lineage is incomplete and nothing runs
if ! experiment_done exp001_yolo26s_640; then
  if trainer_alive; then
    note "trainer already alive -- leaving it"
  elif [ -f "training/runs/exp001_yolo26s_640/weights/last.pt" ]; then
    note "resume exp001 from last.pt"
    nohup "$PY" -u scripts/train_detector.py --data "$DATA" --model yolo26s.pt \
      --experiment-id exp001_yolo26s_640 --imgsz 640 --batch 8 --epochs 80 \
      --patience 25 --seed 0 --workers 4 --no-pin-memory --resume \
      >> logs/train_exp001_yolo26s_640.log 2>&1 &
    sleep 15   # let the python process exist before anything else probes
  else
    note "exp001 incomplete but no last.pt -- leaving it to the chain (fresh start)"
  fi
fi

# 2) watchdog
if watchdog_alive; then
  note "watchdog already alive"
else
  note "starting watchdog"
  nohup bash scripts/watchdog_c5.sh >> logs/watchdog.log 2>&1 &
  sleep 2
fi

# 3) sweep chain (waits for external exp001 by design)
if chain_alive; then
  note "chain already alive"
else
  note "starting sweep chain"
  nohup bash scripts/run_sweep_302.sh >> logs/sweep_chain.log 2>&1 &
fi

# 4) epoch cap watcher -- user-directed hard cap for exp001 (2026-10-15:
# "train within 3-4 hours"). Restarts it after a reboot too, while the run
# is incomplete and below the cap. No-op once the manifest exists.
cap_watcher_alive() {
  proc_count '(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "bash.exe" -and $_.CommandLine -match "epoch_cap_watcher" -and $_.CommandLine -notmatch "qoder|snapshot" })' | grep -qE "^[1-9]"
}
CAP_EPOCH=50
if [ -f NO_EPOCH_CAP ]; then
  note "NO_EPOCH_CAP flag present -- watcher not started"
elif experiment_done exp001_yolo26s_640; then
  note "exp001 manifest exists -- cap watcher not needed"
else
  CAP_ROWS=0
  [ -f training/runs/exp001_yolo26s_640/results.csv ] && \
    CAP_ROWS=$(( $(wc -l < training/runs/exp001_yolo26s_640/results.csv) - 1 ))
  if [ "$CAP_ROWS" -ge "$CAP_EPOCH" ]; then
    note "results.csv rows $CAP_ROWS >= cap $CAP_EPOCH but no manifest -- chain/finalize will handle it; watcher not started"
  elif cap_watcher_alive; then
    note "cap watcher already alive"
  else
    note "starting epoch cap watcher (cap=$CAP_EPOCH, rows=$CAP_ROWS)"
    nohup bash scripts/epoch_cap_watcher.sh exp001_yolo26s_640 "$CAP_EPOCH" yolo26s.pt \
      >> logs/epoch_cap_exp001_yolo26s_640.log 2>&1 &
  fi
fi

note "done"
