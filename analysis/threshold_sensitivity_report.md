# Threshold sensitivity check: rate-of-rise multiplier and naive baseline
Standalone check, not part of the evaluated pipeline. Reads outputs/run_log.json only.

## 1. Rate-of-rise multiplier sensitivity, full DGM comparison

Days led (negative)/lagged (positive) vs. each DGM bulletin, by lead time. 'match' = 0d. 3.0x is the value used in the paper.

### Multiplier 2.0x
| DGM bulletin | Level | D0 | T-24h | T-48h | T-72h |
|---|---|---|---|---|---|
| 2026-01-16 | informational | lag 8d | lag 6d | lag 6d | lag 5d |
| 2026-01-29 | red (Chefchaouen), o | lag 1d | lag 3d | lag 2d | lag 1d |
| 2026-02-01 | orange | lag 1d | match | match | match |
| 2026-02-02 | red | match | match | match | led 1d |
| 2026-02-03 | red | match | led 1d | led 1d | led 2d |
| 2026-02-05 | orange | led 2d | lag 1d | led 3d | led 4d |
| 2026-02-07 | orange | match | led 1d | led 5d | led 6d |

### Multiplier 2.5x
| DGM bulletin | Level | D0 | T-24h | T-48h | T-72h |
|---|---|---|---|---|---|
| 2026-01-16 | informational | lag 8d | lag 6d | lag 7d | lag 5d |
| 2026-01-29 | red (Chefchaouen), o | lag 1d | lag 3d | lag 2d | lag 1d |
| 2026-02-01 | orange | lag 1d | match | match | match |
| 2026-02-02 | red | match | match | match | led 1d |
| 2026-02-03 | red | match | led 1d | led 1d | led 2d |
| 2026-02-05 | orange | led 2d | lag 1d | led 3d | led 4d |
| 2026-02-07 | orange | led 4d | led 1d | led 5d | led 6d |

### Multiplier 3.0x
| DGM bulletin | Level | D0 | T-24h | T-48h | T-72h |
|---|---|---|---|---|---|
| 2026-01-16 | informational | lag 8d | lag 6d | lag 7d | lag 5d |
| 2026-01-29 | red (Chefchaouen), o | led 5d | lag 3d | lag 2d | lag 1d |
| 2026-02-01 | orange | lag 2d | match | match | match |
| 2026-02-02 | red | lag 1d | match | led 1d | led 1d |
| 2026-02-03 | red | match | led 1d | led 2d | led 2d |
| 2026-02-05 | orange | led 2d | led 3d | led 4d | led 4d |
| 2026-02-07 | orange | led 4d | led 5d | led 6d | led 6d |

### Multiplier 3.5x
| DGM bulletin | Level | D0 | T-24h | T-48h | T-72h |
|---|---|---|---|---|---|
| 2026-01-16 | informational | lag 8d | lag 6d | lag 7d | lag 5d |
| 2026-01-29 | red (Chefchaouen), o | led 5d | lag 3d | lag 2d | lag 1d |
| 2026-02-01 | orange | lag 2d | match | match | led 1d |
| 2026-02-02 | red | lag 1d | match | led 1d | led 2d |
| 2026-02-03 | red | match | led 1d | led 2d | led 3d |
| 2026-02-05 | orange | led 2d | led 3d | led 4d | led 5d |
| 2026-02-07 | orange | led 4d | led 5d | led 6d | led 7d |

### Multiplier 4.0x
| DGM bulletin | Level | D0 | T-24h | T-48h | T-72h |
|---|---|---|---|---|---|
| 2026-01-16 | informational | lag 8d | lag 6d | lag 7d | lag 5d |
| 2026-01-29 | red (Chefchaouen), o | led 5d | lag 3d | lag 2d | lag 1d |
| 2026-02-01 | orange | led 8d | match | match | led 1d |
| 2026-02-02 | red | led 9d | match | led 1d | led 2d |
| 2026-02-03 | red | led 10d | led 1d | led 2d | led 3d |
| 2026-02-05 | orange | led 12d | led 3d | led 4d | led 5d |
| 2026-02-07 | orange | led 14d | led 5d | led 6d | led 7d |

### Multiplier 5.0x
| DGM bulletin | Level | D0 | T-24h | T-48h | T-72h |
|---|---|---|---|---|---|
| 2026-01-16 | informational | lag 8d | lag 6d | lag 15d | lag 5d |
| 2026-01-29 | red (Chefchaouen), o | led 5d | lag 3d | lag 2d | lag 1d |
| 2026-02-01 | orange | led 8d | match | led 1d | led 1d |
| 2026-02-02 | red | led 9d | match | led 2d | led 2d |
| 2026-02-03 | red | led 10d | led 1d | led 3d | led 3d |
| 2026-02-05 | orange | led 12d | led 3d | led 5d | led 5d |
| 2026-02-07 | orange | led 14d | led 5d | led 7d | led 7d |

## 2. Naive fixed-precipitation-threshold baseline, full DGM comparison

### Threshold 20mm
| DGM bulletin | Level | D0 | T-24h | T-48h | T-72h |
|---|---|---|---|---|---|
| 2026-01-16 | informational | match | lag 6d | lag 5d | led 2d |
| 2026-01-29 | red (Chefchaouen), o | lag 4d | lag 3d | lag 2d | lag 1d |
| 2026-02-01 | orange | lag 1d | match | match | match |
| 2026-02-02 | red | match | match | match | led 1d |
| 2026-02-03 | red | match | led 1d | led 1d | lag 1d |
| 2026-02-05 | orange | led 1d | lag 1d | match | led 1d |
| 2026-02-07 | orange | match | led 1d | led 2d | led 3d |

### Threshold 30mm
| DGM bulletin | Level | D0 | T-24h | T-48h | T-72h |
|---|---|---|---|---|---|
| 2026-01-16 | informational | lag 8d | lag 21d | lag 17d | lag 15d |
| 2026-01-29 | red (Chefchaouen), o | led 5d | lag 8d | lag 4d | lag 2d |
| 2026-02-01 | orange | lag 6d | lag 5d | lag 1d | match |
| 2026-02-02 | red | lag 5d | lag 4d | match | led 1d |
| 2026-02-03 | red | lag 4d | lag 3d | led 1d | led 2d |
| 2026-02-05 | orange | lag 2d | lag 1d | match | led 4d |
| 2026-02-07 | orange | match | led 1d | led 2d | led 6d |

## 3. Focused comparison: the Feb 1-3 cluster (the paper's headline claim)

Does 'matched or led by up to 2 days' hold at other multipliers, and how does the naive baseline do on the same three bulletins?

| Method | Param | DGM bulletin | D0 | T-24h | T-48h | T-72h |
|---|---|---|---|---|---|---|
| rate_of_rise | 2.0x | 2026-02-01 | lag 1d | match | match | match |
| rate_of_rise | 2.0x | 2026-02-02 | match | match | match | led 1d |
| rate_of_rise | 2.0x | 2026-02-03 | match | led 1d | led 1d | led 2d |
| rate_of_rise | 2.5x | 2026-02-01 | lag 1d | match | match | match |
| rate_of_rise | 2.5x | 2026-02-02 | match | match | match | led 1d |
| rate_of_rise | 2.5x | 2026-02-03 | match | led 1d | led 1d | led 2d |
| rate_of_rise | 3.0x | 2026-02-01 | lag 2d | match | match | match |
| rate_of_rise | 3.0x | 2026-02-02 | lag 1d | match | led 1d | led 1d |
| rate_of_rise | 3.0x | 2026-02-03 | match | led 1d | led 2d | led 2d |
| rate_of_rise | 3.5x | 2026-02-01 | lag 2d | match | match | led 1d |
| rate_of_rise | 3.5x | 2026-02-02 | lag 1d | match | led 1d | led 2d |
| rate_of_rise | 3.5x | 2026-02-03 | match | led 1d | led 2d | led 3d |
| rate_of_rise | 4.0x | 2026-02-01 | led 8d | match | match | led 1d |
| rate_of_rise | 4.0x | 2026-02-02 | led 9d | match | led 1d | led 2d |
| rate_of_rise | 4.0x | 2026-02-03 | led 10d | led 1d | led 2d | led 3d |
| rate_of_rise | 5.0x | 2026-02-01 | led 8d | match | led 1d | led 1d |
| rate_of_rise | 5.0x | 2026-02-02 | led 9d | match | led 2d | led 2d |
| rate_of_rise | 5.0x | 2026-02-03 | led 10d | led 1d | led 3d | led 3d |
| naive_precip_threshold | 20mm | 2026-02-01 | lag 1d | match | match | match |
| naive_precip_threshold | 20mm | 2026-02-02 | match | match | match | led 1d |
| naive_precip_threshold | 20mm | 2026-02-03 | match | led 1d | led 1d | lag 1d |
| naive_precip_threshold | 30mm | 2026-02-01 | lag 6d | lag 5d | lag 1d | match |
| naive_precip_threshold | 30mm | 2026-02-02 | lag 5d | lag 4d | match | led 1d |
| naive_precip_threshold | 30mm | 2026-02-03 | lag 4d | lag 3d | led 1d | led 2d |
