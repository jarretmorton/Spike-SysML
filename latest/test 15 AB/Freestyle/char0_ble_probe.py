# char0 — BLE deploy probe
#
# Purpose: after four consecutive flash_program TimeoutErrors with hub_id: null,
# bisect "program too large to transfer" against "cannot connect to hub at all".
# Flashed only; never executed, so it consumes no characterization run.
#
# Result: this ~250-byte program timed out identically to the ~10 KB one,
# ruling out program size and isolating the fault to the BLE link.

from pybricks.hubs import PrimeHub
from pybricks.tools import StopWatch
from usys import stdout

hub = PrimeHub()
clock = StopWatch()
stdout.write('{"timestamp_ms":%d,"sensor":"probe","value":1.00}\n' % clock.time())
stdout.write('{"event":"end"}\n')
