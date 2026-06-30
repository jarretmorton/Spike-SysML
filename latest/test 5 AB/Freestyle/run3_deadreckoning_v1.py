# Run 3 — Dead-reckoning stop v1 + active heading-hold (first encoder-stop attempt).
# Measures d0 stationary, sprints at full speed holding IMU heading at 0, and brakes
# on wheel-degrees (not the laggy live distance). Targets a ~60 mm final sensor reading.
#
# KNOWN ISSUE (fixed in Run 4): telemetry is emitted INSIDE the control loop. The
# stdout-over-BLE writes block the loop (up to ~64 ms/iteration as the BLE buffer fills),
# so the brake fired ~31 mm late. Heading-hold itself worked (held within +/-1.4 deg).

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()
def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), s, v))

mC = Motor(Port.C); mD = Motor(Port.D)
usA = UltrasonicSensor(Port.A); usB = UltrasonicSensor(Port.B)

MMPD=0.489; BRAKE_MM=74.0; REACT_MM=6.0; G_SENSOR=60.0
MAXSPD=1000; DIRC=-1; ACCEL=3000; KP=14.0; GCAP=320.0

mC.control.limits(acceleration=ACCEL)
mD.control.limits(acceleration=ACCEL)

def dmin():
    a=usA.distance(); b=usB.distance()
    return a,b,(a if a<b else b)

try:
    mC.reset_angle(0); mD.reset_angle(0)
    vals=[]
    for i in range(7):
        a,b,m=dmin(); vals.append(m); wait(20)
    vals.sort(); d0=vals[3]
    if d0<700 or d0>1300: d0=905.0
    emit("d0", d0)

    final_fdeg=(d0-G_SENSOR)/MMPD
    trig_fdeg=final_fdeg-(BRAKE_MM+REACT_MM)/MMPD
    emit("trig_fdeg", trig_fdeg); emit("pred_final_fdeg", final_fdeg)

    baseC=DIRC*MAXSPD; baseD=-DIRC*MAXSPD
    def fdeg(): return DIRC*0.5*(mC.angle()-mD.angle())

    mC.run(baseC); mD.run(baseD)
    n=0; t0=clock.time()
    while True:
        t=clock.time(); fd=fdeg(); h=hub.imu.heading()
        g=KP*h
        if g>GCAP: g=GCAP
        if g<-GCAP: g=-GCAP
        mC.run(baseC+g); mD.run(baseD+g)
        if (n%4)==0:
            emit("fdeg",fd); emit("heading",h)
            emit("est_dist", d0-fd*MMPD); emit("fspd", DIRC*0.5*(mC.speed()-mD.speed()))
        if fd>=trig_fdeg:
            emit("brake_fdeg",fd); emit("brake_heading",h)
            mC.brake(); mD.brake(); break
        if fd>final_fdeg+40:
            mC.brake(); mD.brake(); break
        if (t-t0)>3500:
            mC.brake(); mD.brake(); break
        n+=1; wait(5)

    wait(400)
    a,b,m=dmin(); a2,b2,m2=dmin()
    emit("fdeg_final", fdeg())
    emit("d_final_A",(a+a2)/2.0); emit("d_final_B",(b+b2)/2.0); emit("d_final_min",(m+m2)/2.0)
    emit("heading_final", hub.imu.heading())
finally:
    mC.brake(); mD.brake()
    stdout.write('{"event":"end"}\n')
