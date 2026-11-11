# Evaluation: Pipeline flags vs. DGM alert timeline

## Table 1 - Chronological timeline (DGM bulletins + pipeline rate-of-rise flags)

| Date | Source | Detail |
|---|---|---|
| 2026-01-16 | DGM bulletin | orange - Larache - forecast 20-40mm (valid 2026-01-16 18:00 to 2026-01-17 18:00) |
| 2026-01-21 | Pipeline flag (T-72h) | rate-of-rise flag for valid-date 2026-01-24 (inflow 52.8 m3/s, 3d lead) |
| 2026-01-22 | Pipeline flag (T-24h) | rate-of-rise flag for valid-date 2026-01-23 (inflow 20.5 m3/s, 1d lead) |
| 2026-01-22 | Pipeline flag (T-72h) | rate-of-rise flag for valid-date 2026-01-25 (inflow 115.8 m3/s, 3d lead) |
| 2026-01-23 | Pipeline flag (T-24h) | rate-of-rise flag for valid-date 2026-01-24 (inflow 46.9 m3/s, 1d lead) |
| 2026-01-23 | Pipeline flag (T-48h) | rate-of-rise flag for valid-date 2026-01-25 (inflow 78.1 m3/s, 2d lead) |
| 2026-01-24 | Pipeline flag (D0) | rate-of-rise flag for valid-date 2026-01-24 (inflow 131.8 m3/s, 0d lead) |
| 2026-01-29 | DGM bulletin | orange - Larache - forecast 60-90mm (valid 2026-01-29 11:00 to 2026-01-30 18:00) |
| 2026-01-30 | Pipeline flag (T-72h) | rate-of-rise flag for valid-date 2026-02-02 (inflow 60.4 m3/s, 3d lead) |
| 2026-01-31 | Pipeline flag (T-48h) | rate-of-rise flag for valid-date 2026-02-02 (inflow 77.4 m3/s, 2d lead) |
| 2026-01-31 | Pipeline flag (T-72h) | rate-of-rise flag for valid-date 2026-02-03 (inflow 294.4 m3/s, 3d lead) |
| 2026-02-01 | DGM bulletin | orange - Larache - forecast 50-80mm (valid 2026-02-02 06:00 to 2026-02-03 12:00) |
| 2026-02-01 | Pipeline flag (T-24h) | rate-of-rise flag for valid-date 2026-02-02 (inflow 53.3 m3/s, 1d lead) |
| 2026-02-01 | Pipeline flag (T-48h) | rate-of-rise flag for valid-date 2026-02-03 (inflow 111.3 m3/s, 2d lead) |
| 2026-02-01 | Pipeline flag (T-72h) | rate-of-rise flag for valid-date 2026-02-04 (inflow 358.0 m3/s, 3d lead) |
| 2026-02-02 | DGM bulletin | red - Larache - forecast 100-150mm (valid 2026-02-04 00:00 to 2026-02-04 23:00) |
| 2026-02-02 | Pipeline flag (T-24h) | rate-of-rise flag for valid-date 2026-02-03 (inflow 134.5 m3/s, 1d lead) |
| 2026-02-03 | DGM bulletin | orange - Larache - forecast 60-100mm (valid 2026-02-03 12:00 to 2026-02-04 23:00) |
| 2026-02-03 | Pipeline flag (D0) | rate-of-rise flag for valid-date 2026-02-03 (inflow 161.4 m3/s, 0d lead) |
| 2026-02-04 | DGM bulletin | orange - Larache - forecast 40-60mm (valid 2026-02-05 12:00 to 2026-02-06 12:00) |
| 2026-02-06 | DGM bulletin | orange - Larache - forecast 30-40; 40-70mm (valid 2026-02-06 12:00 to 2026-02-08 06:00) |

## Table 2 - Nearest pipeline flag per DGM bulletin, by lead time

Negative/'led by' = pipeline flag came before the DGM bulletin (earlier warning). Positive/'lagged by' = pipeline flag came after.

| DGM bulletin date | Level | D0 | T-24h | T-48h | T-72h |
|---|---|---|---|---|---|
| 2026-01-16 | orange | 2026-01-24 (lagged by 8d) | 2026-01-22 (lagged by 6d) | 2026-01-23 (lagged by 7d) | 2026-01-21 (lagged by 5d) |
| 2026-01-29 | orange | 2026-01-24 (led by 5d) | 2026-02-01 (lagged by 3d) | 2026-01-31 (lagged by 2d) | 2026-01-30 (lagged by 1d) |
| 2026-02-01 | orange | 2026-02-03 (lagged by 2d) | 2026-02-01 (matched) | 2026-02-01 (matched) | 2026-02-01 (matched) |
| 2026-02-02 | red | 2026-02-03 (lagged by 1d) | 2026-02-02 (matched) | 2026-02-01 (led by 1d) | 2026-02-01 (led by 1d) |
| 2026-02-03 | orange | 2026-02-03 (matched) | 2026-02-02 (led by 1d) | 2026-02-01 (led by 2d) | 2026-02-01 (led by 2d) |
| 2026-02-04 | orange | 2026-02-03 (led by 1d) | 2026-02-02 (led by 2d) | 2026-02-01 (led by 3d) | 2026-02-01 (led by 3d) |
| 2026-02-06 | orange | 2026-02-03 (led by 3d) | 2026-02-02 (led by 4d) | 2026-02-01 (led by 5d) | 2026-02-01 (led by 5d) |
