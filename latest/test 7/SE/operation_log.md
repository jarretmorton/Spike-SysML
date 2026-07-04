# Operation Phase Log — Wall-Approach Rover (prog_v4 locked)

Onboard gap estimate method (frozen before any ground truth):
- **Primary: sensor-A near-range fit** `gap_est = 0.643*rest_A + 1.03` mm
  (fit to near-range truth points V1 42->28 and V1' 70->46; validated on V1':
  predicted 46, operator 46).
- Cross-check: **trigger geometry** `(true_start - travel_trig) - D_stop_eff(58)`.

No operator measurements taken during the 5 runs (per task rules); requested together at close-out.

| Run | run_id | trig | emerg | a_start | target_travel | travel_trig | trig true pos | rest_A | rest_B | D_stop_enc | heading | omega | **onboard gap est (mm)** | contact? |
|:--:|---|:--:|:--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|:--:|
| 1 | run-20260702-130444 | 1 | 0 | 945 | 825 | 828 | 110 | 66 | 60 | 4.8 | -5.2 | 1050 | **43** (xcheck 52) | none |
| 2 | run-20260702-130717 | 1 | 0 | 939 | 819 | 820 | 112 | 59 | 60 | 10.3 | -3.5 | 1046 | **39** (xcheck 54) | none |
| 3 | run-20260702-130917 | 1 | 0 | 950 | 830 | 832 | 111 | 56 | 49 | 7.0 | -4.0 | 1067 | **37** (xcheck 53) | none |
| 4 | run-20260702-131121 | 1 | 0 | 942 | 822 | 823 | 112 | 66 | 71 | 3.6 | -4.7 | 1053 | **43** (xcheck 54) | none |
| 5 | run-20260702-131402 | 1 | 0 | 939 | 819 | 821 | 111 | 67 | 60 | 7.2 | -6.8 | 1038 | **44** (xcheck 53) | none |

**All 5 onboard estimates FROZEN before ground truth: 43, 39, 37, 43, 44 mm (A-fit); trigger-geometry cross-check 52, 54, 53, 54, 53 mm. No contact on any run (5/5).**

Run 1 estimate: A-fit 0.643*66+1.03 = 43.5 -> **43 mm**; trigger-geometry (938-828)-58 = 52 mm.
