# Datasheet: IMD / Open-Meteo Weather Telemetry (D2)

**Dataset:** Hourly temp (C), humidity (%), UV index, monsoon alerts — Punjab grid
**Version:** v1.0.0-P1  **DOI:** pending Zenodo
**BibTeX:** `[@imd2024; @openmeteo2024]`
**Path:** `data/raw/weather/YYYYMMDD.json` → `data/gold/weather_hourly.parquet`

## 1. Motivation

Feeds `Φ_env(T,H)` (`spec §2.2:104`) and forecaster weather feature (`spec §4.1`). Punjab Loo (44°C) and monsoon H>70% are first-class hazards (`mockData.js:10-12`).

## 2. Composition

Fields: `timestamp_utc, lat, lon, temp_c, humidity_pct, uv_index, precipitation_mm, source (IMD|open-meteo)`. Coverage: Punjab bounding box 29.5-32.7N, 73.5-77N, hourly. Missingness: IMD gridded 3-hour; gap-filled via Open-Meteo linear interp, flag `is_interpolated`.

## 3. Collection

IMD gridded 0.25° via `data/ingestion/imd.py` (manual download where API restricted); Open-Meteo `https://api.open-meteo.com/v1/forecast?latitude=30.9&longitude=75.85&hourly=temperature_2m,relative_humidity_2m&past_days=90` hourly pull. Rate 1 req/s.

## 4. Preprocessing

- Bias correction: IMD minus Open-Meteo mean bias +0.3°C Ludhiana summer (computed L1.2).
- GE: `expect_temp_c_between_-10_55`, `humidity_0_100`.
- Provenance: source column retained.

## 5. Uses & Limitations

Humidity threshold `H_threshold=70%` per spec; tail >85% rare (<2% hours) — model may underperform. Monsoon alerts not yet in Φ (future ADR).

## 9. Citation

`@imd2024`, `@openmeteo2024` (CC-BY-4.0).

## Real Fetch Log

<!-- real-fetch-log -->

| window | source | points | rows | peak | retrieved |
|---|---|---|---|---|---|
| 2026-05-01..2026-06-30 | open-meteo-archive | 5 points | 7320 rows | max 43.6C | retrieved 2026-08-25T12:24:07.892590 |
