"""All telemetry retrieved from the SPIKE Prime hub during this exercise.

Every number here was read back off the hub via get_telemetry. Nothing is
synthetic. Times in the *_PROFILE tables are milliseconds from the start of
that dash; distances are raw sensor-A readings in mm (2000 / None = no echo).
"""

# ----------------------------------------------------------------------
# Characterisation run 3: stepped stationary calibration to touch-off
# theta = encoder degrees from the start line, r1/r2 = sensor A/B readings
# ----------------------------------------------------------------------
THETA_CONTACT = 1945.5          # encoder deg at which the rover touched the wall

CAL = [
    # theta,    r1,     r2
    (   0.0, 1014.5,  880.0),
    ( 272.5,  889.5,  733.0),
    ( 540.0,  807.8,  629.5),
    ( 811.5,  587.0,  453.3),
    (1082.0,  434.0,  292.0),
    (1243.5,  351.5,  211.0),
    (1406.5,  285.0,  178.0),
    (1490.5,  240.0,  176.3),
    (1574.5,  191.0,   56.0),
    (1611.0,  175.5,   43.3),
    (1647.5,  163.8,  180.0),
    (1731.5,  114.0,   40.0),
    (1768.0,   95.0, 2000.0),
    (1803.0,   78.0, 2000.0),
    (1840.5,   62.0, 2000.0),
]

CREEP_LAST_A = 40.0             # last valid sensor-A reading at contact
CREEP_LAST_B = 94.0
K_CRUISE = 0.492                # mm per encoder degree, measured at constant speed
K_STEPPED = 0.5214              # mm per encoder degree from the stepped fit (inflated)

# ----------------------------------------------------------------------
# Characterisation run 3: three full-speed dashes (blended A+B estimator)
# ----------------------------------------------------------------------
CHAR3_DASHES = [
    dict(tag=0, trig=260.0,  g0=985.00,  wall=1008.83, nfix=46, vbrk_dps=891,
         vmms=445.94, brake_enc=12.26, hend=-7.55, afin=289.0),
    dict(tag=1, trig=260.0,  g0=987.58,  wall=1010.48, nfix=45, vbrk_dps=919,
         vmms=452.15, brake_enc=12.26, hend=-4.89, afin=289.0),
    dict(tag=2, trig=108.42, g0=984.66,  wall=1011.58, nfix=60, vbrk_dps=930,
         vmms=457.56, brake_enc=12.01, hend=2.30,  afin=110.0),
]

# ----------------------------------------------------------------------
# Characterisation run 4: validation trigger sweep
# ----------------------------------------------------------------------
VALIDATION = [
    dict(dash=1, trig=150.0, g0=1016.88, wall=1042.66, lag=25.79, nfix=64,
         vmms=439.11, brake_enc=11.56, lastfix_g=203.0, afin=117.0,
         gfin_sensor=114.00, gfin_dr=114.98, hmax=1.34, hend=-2.40),
    dict(dash=2, trig=100.0, g0=1011.13, wall=1034.94, lag=23.81, nfix=74,
         vmms=441.32, brake_enc=12.79, lastfix_g=139.0, afin=58.0,
         gfin_sensor=55.00,  gfin_dr=58.61,  hmax=0.91, hend=-3.54),
    dict(dash=3, trig=78.70, g0=1014.13, wall=1035.36, lag=21.24, nfix=77,
         vmms=442.55, brake_enc=12.30, lastfix_g=130.0, afin=40.0,
         gfin_sensor=37.00,  gfin_dr=45.30,  hmax=0.77, hend=-2.30),
]

VALIDATION_PROFILES = {
    1: [(0,1024),(120,1017),(240,966),(361,922),(481,875),(601,827),(721,911),
        (841,721),(962,665),(1082,608),(1203,557),(1324,495),(1446,442),
        (1566,388),(1687,330),(1807,289),(1927,289),(2120,159),(2204,126),
        (2289,121),(2373,117),(2541,117),(2709,117),(2877,117)],
    2: [(0,1012),(121,999),(241,954),(361,903),(481,852),(601,801),(721,757),
        (841,705),(961,648),(1081,586),(1202,549),(1323,483),(1444,424),
        (1564,367),(1695,313),(1816,290),(1936,219),(2057,171),(2243,85),
        (2327,63),(2411,58),(2579,58),(2747,58),(2915,58)],
    3: [(0,1019),(120,1000),(240,946),(360,898),(480,854),(600,801),(721,748),
        (843,690),(964,641),(1084,588),(1204,527),(1324,467),(1445,418),
        (1565,360),(1685,306),(1805,291),(1925,207),(2045,155),(2232,66),
        (2316,50),(2400,40),(2568,40),(2736,40),(2904,40)],
}

# ----------------------------------------------------------------------
# Phase 2: the five locked operation runs
# measured_gap = operator ground truth, supplied only after all five were run
# ----------------------------------------------------------------------
OPERATION = [
    dict(run=1, start_a=1020.88, g0=1018.25, wall=1047.09, lag=28.84, nfix=66,
         vmms=458.79, brake_enc=13.28, lastfix_g=113.0, afin=40.0,
         gfin_dr=18.97, hmax=1.25, hend=-1.28, vbat=7256, measured_gap=3.0),
    dict(run=2, start_a=1018.13, g0=1015.13, wall=1045.04, lag=29.91, nfix=76,
         vmms=432.96, brake_enc=14.02, lastfix_g=103.0, afin=40.0,
         gfin_dr=13.56, hmax=1.11, hend=-3.71, vbat=7253, measured_gap=5.0),
    dict(run=3, start_a=1016.63, g0=1013.13, wall=1043.32, lag=30.20, nfix=74,
         vmms=457.56, brake_enc=13.04, lastfix_g=99.0,  afin=40.0,
         gfin_dr=11.24, hmax=0.78, hend=-6.27, vbat=7248, measured_gap=8.0),
    dict(run=4, start_a=1017.88, g0=1015.25, wall=1054.94, lag=39.69, nfix=75,
         vmms=454.61, brake_enc=12.55, lastfix_g=107.0, afin=40.0,
         gfin_dr=7.04,  hmax=1.25, hend=-4.25, vbat=7243, measured_gap=9.0),
    dict(run=5, start_a=1015.63, g0=1011.63, wall=1047.88, lag=36.25, nfix=72,
         vmms=446.74, brake_enc=11.81, lastfix_g=113.0, afin=40.0,
         gfin_dr=15.49, hmax=1.87, hend=-3.03, vbat=7239, measured_gap=1.0),
]

OPERATION_PROFILES = {
    1: [(0,1024),(120,1010),(240,968),(360,928),(480,873),(601,839),(721,None),
        (841,722),(964,660),(1084,606),(1204,555),(1324,486),(1446,428),
        (1566,381),(1686,324),(1809,290),(1929,215),(2049,172),(2169,116),
        (2341,44),(2425,67),(2509,40),(2761,40),(3013,40)],
    2: [(0,1018),(120,1003),(240,964),(360,914),(482,862),(603,812),(723,763),
        (843,713),(963,652),(1083,593),(1205,551),(1325,484),(1446,426),
        (1567,371),(1688,322),(1809,290),(1929,220),(2050,169),(2171,106),
        (2343,40),(2595,40),(2763,40),(3015,40)],
    3: [(0,1016),(122,1004),(242,962),(362,910),(483,866),(603,812),(723,763),
        (843,704),(964,655),(1084,592),(1204,537),(1325,472),(1446,422),
        (1566,368),(1688,313),(1809,294),(1929,210),(2049,158),(2250,59),
        (2334,40),(2418,40),(2586,40),(2754,40),(3007,40)],
    4: [(0,1018),(120,989),(241,960),(361,928),(481,877),(601,833),(721,None),
        (843,726),(963,668),(1083,615),(1204,568),(1325,498),(1446,439),
        (1567,384),(1688,337),(1808,286),(1929,244),(2050,177),(2170,131),
        (2359,47),(2443,40),(2611,40),(2780,40),(3032,40)],
    5: [(0,1012),(120,997),(241,959),(361,922),(482,868),(602,823),(724,771),
        (844,None),(964,665),(1084,603),(1205,552),(1326,498),(1447,436),
        (1567,383),(1687,325),(1807,291),(1927,291),(2048,175),(2169,124),
        (2358,41),(2442,40),(2526,61),(2778,40),(3030,40)],
}

# ----------------------------------------------------------------------
# Aborted / interrupted attempts during the operation phase (no dash occurred)
# ----------------------------------------------------------------------
OPERATION_REFUSALS = [
    dict(event="flash timeout", detail="deployed=False, nothing written to hub"),
    dict(event="abort_code 7", start_a=817.63, rear=2000.0,
         detail="start position gate: expected ~1016mm, rover did not move"),
    dict(event="abort_code 7", start_a=833.38, rear=555.0,
         detail="start position gate: rear sensor also changed, rover did not move"),
]

PORT_MAP = {0: "ultrasonic (forward, primary)", 1: "ultrasonic (forward, unused)",
            2: "motor", 3: "motor", 4: "ultrasonic (rear)", 5: "colour sensor"}
