#!/usr/bin/env bash
# PRHAAR C5 #32 -- limited-sweep chain (spec sections 23-25).
#
# Sequence (serial, one GPU):
#   1. wait for exp001_yolo26s_640 (launched before this chain -- external run)
#   2. eval exp001: val@640 + test@640 + per-box error analysis test@640
#   3. exp004 rtdetr-l 640 | eval
#
# 2026-10-15 TRIM (user directive "hnn krde", quality-over-quantity):
#   exp002 yolo26m / exp003 yolo26l REMOVED from this sweep. Rationale:
#   (a) 4 GB edge GPU makes m/l latency+VRAM deployment-impractical;
#   (b) rtdetr-l covers the license-diverse (Apache-2.0) fallback while the
#       Ultralytics AGPL/RUP decision stays open -- strategically the one
#       alternative that matters;
#   (c) measured epoch budget on this machine. Deviation from spec 24 is
#   recorded in reports/evidence/incidents/20261014_exp001_incident.md and
#   project memory. Deferred models remain ADDABLE later as append-only 63
#   log rows if the measured results warrant a bigger YOLO.
#
# Crash resilience (measured need 2026-10-14: WDDM pin-memory crash; then
# commit-exhaustion crash; then a chain-race data-loss incident):
#   * RACE GUARD: every crash path re-checks training_alive() before launching
#     anything -- if another train_detector process is running (e.g. a manual
#     relaunch), the chain WAITS for it instead of racing it. Incident
#     2026-10-14: this chain's crash path relaunched a duplicate next to a
#     manual run -> VRAM duel -> false OOM -> rm -rf wiped exp001 ep1-3 lineage.
#   * OOM fresh-halving is allowed ONLY for chain-owned (non-external) runs.
#   * chain children: rc!=0 without manifest -> OOM signature in log -> halve
#     batch and restart fresh (max 2 halvings); otherwise resume from
#     weights/last.pt (max 3), else give up loudly.
#   * external exp001: poll; launch only when NO python process running
#     train_detector.py (checked via Get-CimInstance command lines, never
#     guessed); resume-only -- never batch-halved, never rm -rf'ed.
# Every --no-pin-memory (WDDM workaround). Metrics are still written ONLY by
# eval_detector.py from measurement; this chain changes no numbers.

set -u
cd "$(dirname "$0")/.." || exit 1

PY="C:/Users/harsh/AppData/Local/Programs/Python/Python311/python.exe"
DATA="datasets/PRHAAR-C5-DETECTION/data.yaml"
POLL=300

note() { echo "[chain $(date '+%F %T')] $*"; }

experiment_done() { [ -f "training/runs/$1/run_manifest.json" ]; }

log_stale() { [ -f "$1" ] && [ -n "$(find "$1" -mmin +15 2>/dev/null)" ]; }

ooms_in_log() {
  [ -f "$1" ] && tail -c 300000 "$1" 2>/dev/null | grep -qi "out of memory"
}

training_alive() { # any python running scripts/train_detector.py (cmdline match)
  local n
  n=$(powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \"name='python.exe'\").CommandLine | Where-Object { \$_ -match 'train_detector' } | Measure-Object | Select-Object -ExpandProperty Count" 2>/dev/null | tr -d '\r\n ')
  [ -n "$n" ] && [ "$n" -ge 1 ] 2>/dev/null
}

launch_train() { # id model epochs patience batch resume_flag(0|1)
  local id="$1" model="$2" epochs="$3" patience="$4" batch="$5" resume="$6"
  local tlog="logs/train_${id}.log"
  local -a cmd=("$PY" -u scripts/train_detector.py --data "$DATA" --model "$model"
                --experiment-id "$id" --imgsz 640 --batch "$batch" --epochs "$epochs"
                --patience "$patience" --seed 0 --workers 4 --no-pin-memory)
  if [ "$resume" = "1" ]; then
    cmd+=(--resume)
  else
    case "$id" in
      exp0*) rm -rf "training/runs/$id" ;;
      *) note "REFUSING rm for unexpected id '$id'"; return 9 ;;
    esac
  fi
  note "train launch id=$id model=$model batch=$batch epochs=$epochs resume=$resume"
  "${cmd[@]}" >> "$tlog" 2>&1
}

run_experiment() { # id model epochs patience batch [external]
  local id="$1" model="$2" epochs="$3" patience="$4" batch="$5" external="${6:-0}"
  local tlog="logs/train_${id}.log"
  local resumes=0 ooms=0 fresh_left=1 first=1
  while :; do
    if experiment_done "$id"; then note "$id DONE"; return 0; fi
    if [ "$first" = "1" ] && [ "$external" = "1" ]; then
      if training_alive; then
        note "$id external run in progress -- waiting"
        sleep $POLL
        continue
      fi
      note "$id external run is gone without a manifest"
    fi
    if [ "$first" = "0" ]; then
      # our own child exited without producing a manifest -> crash path
      # RACE GUARD (incident 2026-10-14): never relaunch while ANY other
      # train_detector process is alive -- wait instead of dueling.
      if training_alive; then
        note "$id another train_detector run is active -- waiting for it"
        sleep $POLL
        continue
      fi
      # OOM fresh-halving only for chain-owned runs; external runs are
      # resume-only (an rm -rf + batch-halve here once destroyed exp001 ep1-3)
      if [ "$external" != "1" ] && ooms_in_log "$tlog" && [ "$ooms" -lt 2 ]; then
        ooms=$((ooms + 1)); batch=$((batch / 2)); [ "$batch" -lt 1 ] && batch=1
        note "$id OOM crash -> fresh run at batch=$batch (halving $ooms/2)"
        launch_train "$id" "$model" "$epochs" "$patience" "$batch" 0 || true
        continue
      fi
      if [ -f "training/runs/$id/weights/last.pt" ] && [ "$resumes" -lt 3 ]; then
        resumes=$((resumes + 1))
        note "$id crashed -> resume $resumes/3 from last.pt"
        launch_train "$id" "$model" "$epochs" "$patience" "$batch" 1 || true
        continue
      fi
      note "$id GIVE UP (resumes=$resumes ooms=$ooms) -- see $tlog"
      return 1
    fi
    # first iteration, not external (or external already gone): start from scratch
    if training_alive; then
      # supervisor-restart guard (2026-10-16): an orphan trainer from a
      # crashed previous chain instance must never be duelled -- wait for it
      note "$id another trainer already alive at start -- waiting"
      sleep $POLL
      continue
    fi
    if [ -f "training/runs/$id/weights/last.pt" ] && [ "$resumes" -lt 3 ]; then
      resumes=$((resumes + 1))
      note "$id found checkpoint without manifest -> resume $resumes/3"
      launch_train "$id" "$model" "$epochs" "$patience" "$batch" 1
    elif [ "$fresh_left" = "1" ]; then
      fresh_left=0
      note "$id fresh start"
      launch_train "$id" "$model" "$epochs" "$patience" "$batch" 0
    else
      note "$id GIVE UP before start"
      return 1
    fi
    first=0
  done
}

run_eval() { # id
  # NOTE (incident 2026-10-16 03:05): the previous single-line form
  #   local id="$1" best="training/runs/$id/..." elog="logs/eval_${id}.log"
  # crashed with "id: unbound variable" on its FIRST real execution: bash
  # expands ALL arguments of one `local` command BEFORE executing it, so $id
  # was still unset when best/elog were expanded (set -u made it fatal).
  # Split the declaration; never self-reference a variable inside the same
  # local statement.
  local id="$1"
  local best="training/runs/$id/weights/best.pt" elog="logs/eval_${id}.log"
  if [ ! -f "$best" ]; then note "eval $id: no best.pt -- skipped"; return 1; fi
  if grep -q "^${id}," C5_EXPERIMENT_LOG.csv 2>/dev/null; then
    note "eval $id already logged -- skip"; return 0
  fi
  note "eval $id val@640"
  "$PY" -u scripts/eval_detector.py --weights "$best" --data "$DATA" --split val \
        --imgsz 640 --batch 4 --experiment-id "$id" \
        --run-dir "training/runs/$id" --append-log >> "$elog" 2>&1 \
    || note "eval $id val failed -- see $elog"
  note "eval $id test@640"
  "$PY" -u scripts/eval_detector.py --weights "$best" --data "$DATA" --split test \
        --imgsz 640 --batch 4 --experiment-id "${id}_test640" \
        --run-dir "training/runs/$id" --append-log >> "$elog" 2>&1 \
    || note "eval $id test failed -- see $elog"
  note "errors $id test@640"
  "$PY" -u scripts/analyze_errors.py --weights "$best" --data "$DATA" --split test \
        --imgsz 640 --batch 4 --experiment-id "$id" >> "$elog" 2>&1 \
    || note "errors $id failed -- see $elog"
  return 0
}

note "sweep chain start (exp001 external; then rtdetr-l + evals)"

run_experiment exp001_yolo26s_640  yolo26s.pt  80 25 8   1
run_eval exp001_yolo26s_640

run_experiment exp004_rtdetr_l_640 rtdetr-l.pt 50 12 4
run_eval exp004_rtdetr_l_640

# completion sentinel: the watchdog supervisor restarts the chain only while
# this file is absent (prevents a restart loop after the sweep finishes).
touch logs/.sweep_chain_complete
note "sweep chain complete"

note "sweep chain complete"
note "experiment log rows so far:"
grep -c "^exp" C5_EXPERIMENT_LOG.csv 2>/dev/null || echo 0
