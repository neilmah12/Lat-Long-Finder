#!/usr/bin/env python3
"""Geocode a spreadsheet of addresses to latitude/longitude using the Esri ArcGIS geocoder.

Input file must contain a "Full Address" column (or a column whose name
contains both "full" and "address"), formatted at minimum as:
"Number Street, City, Province".

Usage:
    python geocode_addresses.py input.xlsx
    python geocode_addresses.py input.csv --address-column "Full Address" --country CAN
"""

import argparse
import sys
import time

import pandas as pd
import requests
from tqdm import tqdm

GEOCODE_URL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"

RESULT_COLUMNS = [
    "latitude",
    "longitude",
    "geocode_score",
    "matched_address",
    "address_type",
]


def geocode_arcgis(full_address, country_code=None, timeout=10):
    params = {
        "f": "json",
        "singleLine": full_address,
        "outFields": "Match_addr,Addr_type,Score",
        "maxLocations": 1,
    }
    if country_code:
        params["countryCode"] = country_code

    try:
        response = requests.get(GEOCODE_URL, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates") or []
        if candidates:
            best = candidates[0]
            return {
                "latitude": best["location"]["y"],
                "longitude": best["location"]["x"],
                "geocode_score": best["attributes"]["Score"],
                "matched_address": best["attributes"]["Match_addr"],
                "address_type": best["attributes"]["Addr_type"],
            }
    except Exception as e:
        print(f"Error geocoding '{full_address}': {e}")

    return {
        "latitude": None,
        "longitude": None,
        "geocode_score": None,
        "matched_address": None,
        "address_type": None,
    }


def find_address_column(df, override=None):
    if override:
        if override not in df.columns:
            sys.exit(f"Column '{override}' not found. Available columns: {df.columns.tolist()}")
        return override

    for col in df.columns:
        if "full" in col.lower() and "address" in col.lower():
            return col

    print("No 'Full Address' column found automatically. Available columns:")
    for i, col in enumerate(df.columns):
        print(f"{i}: {col}")
    col_index = int(input("\nEnter the column number for Full Address: "))
    return df.columns[col_index]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_file", help="Path to the .csv, .xls, or .xlsx file to geocode")
    parser.add_argument("--address-column", help="Name of the column containing the full address")
    parser.add_argument("--country", default="CAN", help="ISO country code to bias results (default: CAN, use '' for none)")
    parser.add_argument("--delay", type=float, default=0.05, help="Seconds to sleep between requests (default: 0.05)")
    parser.add_argument("--output-prefix", help="Prefix for output files (default: <input>_geocoded)")
    args = parser.parse_args()

    input_file = args.input_file
    if input_file.lower().endswith(".csv"):
        df = pd.read_csv(input_file)
    else:
        df = pd.read_excel(input_file)

    print(f"Total records: {len(df)}")
    print(f"Columns found: {df.columns.tolist()}\n")

    address_col = find_address_column(df, args.address_column)
    print(f"Using column: '{address_col}' for geocoding\n")

    # Drop any stale geocode result columns from a previous run so the new
    # results aren't concatenated alongside duplicate column names (which
    # turns df_final['latitude'] into a multi-column DataFrame downstream).
    df = df.drop(columns=[c for c in RESULT_COLUMNS if c in df.columns])

    results = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Geocoding"):
        full_address = str(row[address_col])
        results.append(geocode_arcgis(full_address, country_code=args.country or None))
        time.sleep(args.delay)

    df_geo = pd.DataFrame(results, columns=RESULT_COLUMNS)
    df_final = pd.concat([df.reset_index(drop=True), df_geo], axis=1)

    success_count = int(df_final["latitude"].notna().sum())
    unique_coords = df_final[["latitude", "longitude"]].drop_duplicates()

    print("\nGeocoding complete!")
    print(f"Successful: {success_count}/{len(df_final)} ({success_count / len(df_final) * 100:.1f}%)")
    print(f"Unique locations: {len(unique_coords)}")

    high_quality = df_final[df_final["geocode_score"] >= 90]
    print(f"High quality matches (score >= 90): {len(high_quality)}")

    output_prefix = args.output_prefix or input_file.rsplit(".", 1)[0] + "_geocoded"
    df_final.to_csv(f"{output_prefix}.csv", index=False)
    df_final.to_excel(f"{output_prefix}.xlsx", index=False)

    print("\nFiles saved:")
    print(f"- {output_prefix}.csv")
    print(f"- {output_prefix}.xlsx")

    print("\nSample of geocoded data:")
    print(df_final[[address_col, "latitude", "longitude", "geocode_score"]].head(10))


if __name__ == "__main__":
    main()
