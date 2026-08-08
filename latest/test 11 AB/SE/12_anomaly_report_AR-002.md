# 12 — ANOMALY REPORT AR-002 — v1.0

**Anomaly:** R-CAL v1.1 run-20260712-233644 hit the 90 s host timeout during
telemetry dump. Lost: segment-4 and creep full-resolution series windows,
the dump's own diagnostics (`rcal.emit_lines`, `rcal.dump_ms`), and the
**end sentinel** (SYS-10 violated for this run). All 105 summary values,
all S1 events, and the seg2/seg3 series windows arrived intact — the
calibration payload was complete.

**Timeline / root cause.** Motion ended ≈ 19.1 s; dump ran ≈ 71 s and
emitted only 464 lines ≈ 26 kB → **BLE throughput ≈ 0.37 kB/s**, a ~6×
collapse versus run 1 (≈ 2.2 kB/s, same firmware, same program family).
Session-to-session BLE variability was not in the dump budget. The dump was
sized (~1 100–1 400 lines) for ≥ 1.5 kB/s.

**Secondary finding (folded into the Calibration Report §2/§3.3):** two of
the three brake triggers fired 95–150 mm early on single low-glitch readings
from sensor B at speed. Safe direction, fatal to closeness — drove the
OP-WAR trigger design (trend gate + median-of-3 + confirm).

**Corrective actions (bound into Gate B artifacts):**
1. OP-WAR v1.0 dump sized to ~100–140 lines ≈ 5–6 kB → ≤ 18 s even at
   0.3 kB/s (CMP-H2 budget 20 s, verified at R-VER).
2. Host run timeout for R-VER and all operation runs: **45 s**
   (motion ≈ 5 s + worst-case dump + margin).
3. Verification criterion 7 (doc 11) makes sentinel + emission duration an
   explicit R-VER pass item.
4. BLE-start retry procedure (AR-001 disposition) unchanged: one retry on
   failed start, counted as the same run attempt.

**Severity:** minor — no data essential to calibration was lost; sentinel
loss was host-timeout-induced, not a program fault (the finally-block would
have emitted it).

**Status:** CLOSED at Gate B (corrective actions embedded in docs 11/13).
