# Run 4 — Loop-stall fix: buffer telemetry in RAM, dump only after the rover stops.
# The control loop no longer touches stdout, so it stays fast (~2 ms/iter) and the brake
# fires within ~1 mm of the trigger point. Everything else matches Run 3, brake budget
# refined to the measured 67 mm. Target ~50 mm final sensor reading.
#
# KNOWN ISSUE (fixed in Run 5): the end-of-run dump writes 3 lines per buffered sample
# and the loop ran faster than expected (~456 samples -> ~1368 lines), so the dump
# overran the 12 s host timeout. The stop itself was clean (85 mm, no contact); only the
# logging tail was truncated.

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

MMPD=0.489; BRAKE_MM=67.0; REACT_MM=6.0; G_SENSOR=50.0
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

    bt=[]; bf=[]; bh=[]
    brake_fd=0.0; brake_h=0.0
    mC.run(baseC); mD.run(baseD)
    n=0; t0=clock.time()
    while True:
        t=clock.time(); fd=fdeg(); h=hub.imu.heading()
        g=KP*h
        if g>GCAP: g=GCAP
        elif g<-GCAP: g=-GCAP
        mC.run(baseC+g); mD.run(baseD+g)
        if (n & 1)==0:
            bt.append(t); bf.append(fd); bh.append(h)
        if fd>=trig_fdeg:
            brake_fd=fd; brake_h=h; mC.brake(); mD.brake(); break
        if fd>final_fdeg+40 or (t-t0)>3500:
            brake_fd=fd; brake_h=h; mC.brake(); mD.brake(); break
        n+=1; wait(2)

    last=fdeg(); stable=0; tcap=clock.time()
    while (clock.time()-tcap)<800:
        wait(10); cur=fdeg()
        bt.append(clock.time()); bf.append(cur); bh.append(hub.imu.heading())
        if abs(cur-last)<1:
            stable+=1
            if stable>=5: break
        else: stable=0
        last=cur

    emit("brake_fdeg", brake_fd); emit("brake_heading", brake_h)
    emit("fdeg_final", fdeg())
    wait(300)
    a,b,m=dmin(); a2,b2,m2=dmin()
    emit("d_final_A",(a+a2)/2.0); emit("d_final_B",(b+b2)/2.0); emit("d_final_min",(m+m2)/2.0)
    emit("heading_final", hub.imu.heading())

    k=len(bt); emit("n_samples", float(k)); i=0
    while i<k:
        stdout.write('{"timestamp_ms":%d,"sensor":"fdeg","value":%f}\n' % (bt[i], bf[i]))
        stdout.write('{"timestamp_ms":%d,"sensor":"heading","value":%f}\n' % (bt[i], bh[i]))
        stdout.write('{"timestamp_ms":%d,"sensor":"est_dist","value":%f}\n' % (bt[i], d0 - bf[i]*MMPD))
        i+=1
finally:
    mC.brake(); mD.brake()
    stdout.write('{"event":"end"}\n')
