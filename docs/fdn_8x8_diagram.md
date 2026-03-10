# 8x8 FDN Reverb Structure

```
                         Feedback (from FWHT output)
                         ┌──────────────────────────────────────────────┐
                         │                                              │
                         v                                              │
Input ──>──┬──> [+ sum] ──> [ Delay  341 smp ] ──> [ 3-band EQ ] ──>──┤
           │                                                            │
           ├──> [+ sum] ──> [ Delay  613 smp ] ──> [ 3-band EQ ] ──>──┤
           │                                                            │
           ├──> [+ sum] ──> [ Delay  919 smp ] ──> [ 3-band EQ ] ──>──┤
           │                                                            │
           ├──> [+ sum] ──> [ Delay 1153 smp ] ──> [ 3-band EQ ] ──>──┤
           │                                                            │
           ├──> [+ sum] ──> [ Delay 1523 smp ] ──> [ 3-band EQ ] ──>──┤
           │                                                            │
           ├──> [+ sum] ──> [ Delay 1867 smp ] ──> [ 3-band EQ ] ──>──┤
           │                                                            │
           ├──> [+ sum] ──> [ Delay 2311 smp ] ──> [ 3-band EQ ] ──>──┤
           │                                                            │
           └──> [+ sum] ──> [ Delay 2791 smp ] ──> [ 3-band EQ ] ──>──┤
                                                                        │
                     ┌──────────────────────────────────────────────────┘
                     │
                     v
              ┌─────────────┐
              │  8x8 FWHT   │    All 8 outputs mixed into all 8 inputs
              │  (Hadamard)  │    using only add/sub butterflies
              └──────┬──────┘
                     │
          ┌──────────┼──────────┐
          v          v          v
      Tap L/R    Feedback    Modulation
      outputs    (to sums)   (per-line LFO)
```

## FWHT Butterfly Detail (8 channels, 3 stages)

```
 x0 ──┬──[+]──┬────[+]────┬────[+]──── y0
      │       │           │
 x1 ──┴──[-]──┤    ┌──[+]─┤    ┌─[+]── y1
               │    │      │    │
 x2 ──┬──[+]──┴──[-]──────┤    │
      │              │     │    │
 x3 ──┴──[-]─────────┴──[-]┤   │
                            │   │
 x4 ──┬──[+]──┬────[+]─────┴──[-]──── y4
      │       │           │
 x5 ──┴──[-]──┤    ┌──[+]─┤    ┌─[-]── y5
               │    │      │    │
 x6 ──┬──[+]──┴──[-]──────┤    │
      │              │     │    │
 x7 ──┴──[-]─────────┴──[-]┴───┘


  Stage 1        Stage 2        Stage 3
  stride=1       stride=2       stride=4

  8 add/sub      8 add/sub      8 add/sub  =  24 total
```

## Hadamard Matrix (what the FWHT computes)

```
         1/sqrt(8) *

     [ +1  +1  +1  +1  +1  +1  +1  +1 ]     y0
     [ +1  -1  +1  -1  +1  -1  +1  -1 ]     y1
     [ +1  +1  -1  -1  +1  +1  -1  -1 ]     y2
     [ +1  -1  -1  +1  +1  -1  -1  +1 ]     y3
     [ +1  +1  +1  +1  -1  -1  -1  -1 ]     y4
     [ +1  -1  +1  -1  -1  +1  -1  +1 ]     y5
     [ +1  +1  -1  -1  -1  -1  +1  +1 ]     y6
     [ +1  -1  -1  +1  -1  +1  +1  -1 ]     y7

Every row is orthogonal to every other row.
Every entry is +1 or -1 (no multiplies needed).
Energy in = energy out (unitary when normalized).
```

## Signal Flow Per Sample

```
1. Read 8 delay outputs ──> d[0..7]

2. Apply 3-band decay EQ to each ──> f[0..7]
   (low shelf, mid, high shelf — independent decay rates)

3. FWHT(f) ──> m[0..7]
   (all 8 channels mixed into all 8 — 24 add/subs)

4. Scale by feedback gain (decay / sqrt(8))

5. Add input to each: m[i] += input * distribution[i]

6. Write to delay lines: delay[i].write(m[i])

7. Tap multiple delay lines for L/R stereo output
```
