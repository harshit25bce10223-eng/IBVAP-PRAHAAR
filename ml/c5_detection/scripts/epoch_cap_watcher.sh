#!/usr/bin/env bash
# epoch_cap_watcher.sh -- user-directed HARD EPOCH CAP for a training run.
#
# Why (2026-10-15): user directive "smart + quality approach... train within
# 3-4 hours". On this RTX 2050 4GB an epoch measures 14-20 min, so the
# remaining exp001 schedule (40 epochs of 80) cannot fit 3-4 h. The cap is
# the quality/time compromise: checkpoint selection (best.pt by ultralytics
# fitness) is preserved, mAP50 is decelerating (+~0.004/epoch late-run), and
# the final retrain after error analysis (#33, spec section 64) gets the full
# budget anyway. Labeled deviation from spec section 23's schedule -- written
# into the run manifest's termination block, the incident record, and memory.
# NEVER a silent stop.
#
# Contract with run_sweep_302.sh: the chain treats run_manifest.json as
# experiment-done. Order of operations below is deliberate:
#   1. results.csv rows reach CAP (cap epoch's validation is complete)
#   2. wait for the trainer to finish writing last.pt/best.pt (mtime-stable)
#   3. write the manifest FIRST (finalize_capped_run.py) -- a chain poll in
#      this window then sees experiment_done and goes to eval instead of
#      resuming the run to the full schedule
#   4. only then taskkill the trainer (cmdline-verified, //F //T)
# If finalize fails the trainer is LEFT RUNNING (safe default: training
# continues normally; the cap is best-effort and never destroys a run).
#
# Exit conditions: manifest appears (natural finish / early stop) -> 0;
# cap applied -> finalize's rc; trainer dies early -> keep watching (chain
# or autoresume will bring it back).
#
# usage: epoch_cap_watcher.sh EXPERIMENT_ID CAP_EPOCH MODEL [REQUESTED_BY]
set -u
cd "$(dirname "$0")/.." || exit 1

EXP_ID="${1:?usage: epoch_cap_watcher.sh EXPERIMENT_ID CAP_EPOCH MODEL [REQUESTED_BY]}"
CAP="${2:?CAP_EPOCH required}"
MODEL="${3:?MODEL required (e.g. yolo26s.pt) -- recorded in manifest model.requested}"
REQUESTED_BY="${4:-user time budget 2026-10-15 ('smart + quality... within 3-4 hours')}"

PY="C:/Users/harsh/AppData/Local/Programs/Python/Python311/python.exe"
RUN_DIR="training/runs/$EXP_ID"
CSV="$RUN_DIR/results.csv"
MANIFEST="$RUN_DIR/run_manifest.json"
LOG="logs/epoch_cap_${EXP_ID}.log"

note() { echo "[cap $(date '+%F %T')] $*" | tee -a "$LOG"; }

rows() { [ -f "$CSV" ] && echo $(( $(wc -l < "$CSV") - 1 )) || echo 0; }

trainer_pids() { # cmdline-verified: train_detector.py AND this experiment id
  powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | Where-Object { \$_.CommandLine -match 'train_detector' -and \$_.CommandLine -match '$EXP_ID' } | Select-Object -ExpandProperty ProcessId" 2>/dev/null \
    | tr -d '\r' | grep -E '^[0-9]+$' || true
}

note "watcher start exp=$EXP_ID cap=$CAP model=$MODEL rows_now=$(rows)"

while :; do
  if [ -f "$MANIFEST" ]; then
    note "manifest already exists -- run finished naturally before cap; nothing to do"
    exit 0
  fi
  R=$(rows)
  [ "$R" -ge "$CAP" ] && break
  sleep 60
done
note "results.csv rows=$R >= cap=$CAP; stabilizing checkpoints before finalize"

# wait for last.pt write to finish: fresh AND mtime-stable across two samples
for attempt in 1 2 3; do
  [ -f "$RUN_DIR/weights/last.pt" ] || { note "last.pt missing -- waiting 60s"; sleep 60; continue; }
  AGE=$(( $(date +%s) - $(stat -c %Y "$RUN_DIR/weights/last.pt") ))
  if [ "$AGE" -lt 300 ]; then
    M1=$(stat -c %Y "$RUN_DIR/weights/last.pt"); B1=$(stat -c %Y "$RUN_DIR/weights/best.pt" 2>/dev/null || echo 0)
    sleep 12
    M2=$(stat -c %Y "$RUN_DIR/weights/last.pt"); B2=$(stat -c %Y "$RUN_DIR/weights/best.pt" 2>/dev/null || echo 0)
    if [ "$M1" = "$M2" ] && [ "$B1" = "$B2" ]; then
      note "checkpoints stable (last.pt age ${AGE}s) -- finalizing"
      break
    fi
    note "checkpoint mtimes still moving (attempt $attempt) -- waiting"
  else
    note "last.pt age ${AGE}s > 300s -- save not finished yet (attempt $attempt)"
  fi
  sleep 45
done

if "$PY" scripts/finalize_capped_run.py --experiment-id "$EXP_ID" --model "$MODEL" \
      --cap-epoch "$CAP" --requested-by "$REQUESTED_BY" --no-pin-memory \
      --optimizer-resolved "MuSGD" 2>&1 | tee -a "$LOG"; then
  note "manifest written -- stopping trainer"
else
  note "FINALIZE FAILED (rc=$?) -- trainer left running; cap abandoned safely"
  exit 1
fi

PIDS=$(trainer_pids)
if [ -z "$PIDS" ]; then
  note "no train_detector process for $EXP_ID found (exited on its own) -- done"
  exit 0
fi
for P in $PIDS; do
  note "taskkill //F //T //PID $P"
  taskkill //F //T //PID "$P" 2>&1 | tr -d '\r' | tee -a "$LOG" || true
done
sleep 8
REM=$(trainer_pids)
if [ -n "$REM" ]; then
  note "WARNING: still alive after kill: $REM -- chain will still not resume (manifest exists)"
else
  note "trainer stopped -- cap applied at epoch $CAP"
fi
exit 0
