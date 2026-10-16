#!/usr/bin/env bash
# PRHAAR C5 training watchdog -- detects and kills HUNG trainers, and since
# 2026-10-16 also SUPERVISES the sweep chain.
#
# Why this exists (measured): after a long system sleep, the trainer process
# can survive but hang forever on a dead CUDA context while its python
# process keeps existing. The sweep chain (and autoresume) treat "process
# exists" as "training alive" and would wait indefinitely. A healthy trainer
# writes to its canonical log every few seconds (unbuffered -u; progress bar
# updates); a log untouched for STALE_MIN minutes means hung.
#
# Behavior: every POLL seconds, for each python process running
# train_detector.py, check its experiment log's mtime. Stale > STALE_MIN ->
# taskkill the tree (the sweep chain then resumes from last.pt via its normal
# crash path; no resume logic lives here -- single responsibility).
#
# Supervisor addition (2026-10-16, measured gap): the sweep chain crashed at
# 03:05 (run_eval local-expansion bug) and the watchdog itself died to a
# cygwin fork failure shortly after -- GPU sat idle ~6 h until morning.
# Chain death must be visible HERE, not only at next logon. While the
# completion sentinel (logs/.sweep_chain_complete) is absent and
# NO_AUTORESUME is not set, a dead chain is restarted. If the watchdog
# itself dies, the 30-min Task Scheduler task (PRHAAR_C5_autoresume_loop)
# re-runs autoresume_c5.sh, which restarts it.
#
# Evidence: operations recorded in logs/watchdog.log.

set -u
cd "$(dirname "$0")/.." || exit 1

STALE_MIN=30
POLL=300
LOG="logs/watchdog.log"

note() { echo "[watchdog $(date '+%F %T')] $*" >> "$LOG"; }

probe_trainers() { # "pid<TAB>experiment_id" per python train_detector process
  powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "train_detector" } | ForEach-Object { $eid = ""; if ($_.CommandLine -match "--experiment-id\s+(\S+)") { $eid = $Matches[1] }; "$($_.ProcessId)`t$eid" }' 2>/dev/null | tr -d '\r'
}

chain_alive() {
  local n
  n=$(powershell -NoProfile -Command '(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "bash.exe" -and $_.CommandLine -match "run_sweep_302" -and $_.CommandLine -notmatch "qoder|snapshot" } | Measure-Object).Count' 2>/dev/null | tr -d '\r\n ')
  [ "${n:-0}" -ge 1 ] 2>/dev/null
}

note "watchdog start (stale=${STALE_MIN}min poll=${POLL}s)"
while :; do
  while IFS=$'\t' read -r pid eid; do
    [ -z "${pid:-}" ] && continue
    [ -z "${eid:-}" ] && eid="unknown"
    tlog="logs/train_${eid}.log"
    if [ ! -f "$tlog" ]; then
      # wrapper log should exist within seconds of launch; else skip this poll
      continue
    fi
    if [ -z "$(find "$tlog" -mmin "-$STALE_MIN" 2>/dev/null)" ]; then
      age=$(( $(date +%s) - $(stat -c %Y "$tlog" 2>/dev/null || echo 0) ))
      note "HUNG: pid=$pid eid=$eid log=$tlog stale ${age}s (> $((STALE_MIN*60))s) -> taskkill tree"
      taskkill //F //T //PID "$pid" >> "$LOG" 2>&1 || note "taskkill failed pid=$pid (already gone?)"
    fi
  done < <(probe_trainers)
  # supervisor: keep the sweep chain alive until it writes its completion
  # sentinel (restart loop guard). Gated by the same NO_AUTORESUME flag.
  if [ ! -f NO_AUTORESUME ] && [ ! -f logs/.sweep_chain_complete ]; then
    if chain_alive; then :; else
      note "supervisor: sweep chain dead and sweep incomplete -> restarting"
      nohup bash scripts/run_sweep_302.sh >> logs/sweep_chain.log 2>&1 &
    fi
  fi
  sleep $POLL
done
