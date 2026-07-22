# Lat-Long Finder

Geocodes a spreadsheet of addresses (CSV/XLS/XLSX) to latitude/longitude using
the free Esri ArcGIS `findAddressCandidates` REST endpoint.

## Requirements

Input file must have a "Full Address" column (or a column whose name contains
both "full" and "address"), formatted at minimum as `Number Street, City,
Province`.

## Usage

```bash
pip install -r requirements.txt
python geocode_addresses.py path/to/input.xlsx
```

Optional flags:

- `--address-column "Full Address"` — force which column to geocode instead of auto-detecting
- `--country CAN` — ISO country code to bias matches (default `CAN`; pass `--country ""` to disable)
- `--delay 0.05` — seconds to sleep between requests
- `--output-prefix out` — base name for the output `.csv`/`.xlsx` files (default: `<input>_geocoded`)

Output columns added: `latitude`, `longitude`, `geocode_score`,
`matched_address`, `address_type`.

## Bug fix note

The original script crashed with
`TypeError: unsupported format string passed to Series.__format__` when run
on a file that already had `latitude`/`longitude`/etc. columns from a
previous geocoding pass (e.g. re-running on an already-geocoded export).
`pd.concat` produced duplicate column names, so `df_final['latitude']`
returned a multi-column DataFrame instead of a Series, and `.sum()` on that
returned a per-column Series rather than a single number, which can't be
used in an f-string `{:.1f}` format spec. This version drops any pre-existing
geocode result columns before merging in the new results.
