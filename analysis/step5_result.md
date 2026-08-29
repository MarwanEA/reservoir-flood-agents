# Step 5 result: basin-average rainfall forcing check (standalone, not part of evaluated pipeline)
Overlap window used (both series): 2026-01-14 to 2026-02-08, 23 days (Jan 29-31 excluded - not present in the 5-station file; see script docstring).
## Cumulative rainfall over the 23-day overlap window
- GFS D0 (dam point): 293.6 mm
- 5-station ABHL basin average: 919.3 mm (3.13x GFS)

## Peak simulated inflow (same SCS-CN + linear-reservoir transform, unchanged parameters)
- GFS D0 forcing (23-day window): 205.6 m3/s, on 2026-02-07
  (for reference, full 26-day pipeline window peak D0: 37.0 mm/day precip -> not directly comparable, different window length; the 358 m3/s figure quoted in the paper is the full-window T-72h peak, not D0 - see run_log.json)
- 5-station basin-average forcing (23-day window): 1628.8 m3/s, on 2026-01-28

## Magnitude gap vs. confirmed real peak inflow (3210 m3/s)
- GFS point forcing: 15.6x gap (205.6 -> 3210)
- Basin-average forcing: 2.0x gap (1628.8 -> 3210)

**Result: replacing point forcing with basin-average forcing alone, no other recalibration, narrows the magnitude gap by 87% (15.6x -> 2.0x).**

This uses the SAME uncalibrated CN=75/AMC/k=1.5d parameters throughout - it isolates the effect of forcing-data choice alone, exactly as asked. A full recalibration (fitting these parameters to the basin) was out of scope for this check.
