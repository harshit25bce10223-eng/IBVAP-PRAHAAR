' PRHAAR C5 scheduler kick -- runs the idempotent autoresume_c5.sh invisibly.
' Created 2026-10-16: measured gap -- the sweep chain crashed 03:05 and the
' watchdog died to a cygwin fork failure the same night; nothing restarted
' them until logon (GPU idle ~6 h). This task fires every 30 min via Task
' Scheduler (PRHAAR_C5_autoresume_loop). autoresume_c5.sh is idempotent and
' gated by the NO_AUTORESUME flag file, so extra firings are cheap no-ops.
' Remove: schtasks /delete /tn PRHAAR_C5_autoresume_loop /f (or NO_AUTORESUME).
CreateObject("Wscript.Shell").Run """C:\Program Files\Git\bin\bash.exe"" -c ""nohup bash /c/SIH/ml/c5_detection/scripts/autoresume_c5.sh >/dev/null 2>&1 &""", 0, False
