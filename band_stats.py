#!/usr/bin/env python3
"""
Print per-band statistics (min, max, mean, std) of a hyperspectral datacube.

Usage:
    # Quick QA summary for a capture
    python band_stats.py 444

    # From reflectance data
    python band_stats.py 444 --source results

    # Save stats to CSV
    python band_stats.py 444 --csv stats_444.csv

Environment setup:
    conda env create -f environment.yml
    conda activate hsi
"""

import argparse
import os
import numpy as np
from spectral_signature import load_cube


def compute_band_stats(cube, wavelengths=None):
    """Compute per-band statistics. Returns a list of dicts."""
    stats = []
    for b in range(cube.shape[2]):
        band_data = cube[:, :, b].astype(np.float64)
        entry = {
            "band": b,
            "min": np.min(band_data),
            "max": np.max(band_data),
            "mean": np.mean(band_data),
            "std": np.std(band_data),
        }
        if wavelengths is not None and b < len(wavelengths):
            entry["wavelength_nm"] = wavelengths[b]
        stats.append(entry)
    return stats


def print_band_stats(stats):
    """Print stats as a formatted table."""
    has_wl = "wavelength_nm" in stats[0]
    if has_wl:
        header = f"{'Band':>5} {'Wavelength':>11} {'Min':>12} {'Max':>12} {'Mean':>12} {'Std':>12}"
    else:
        header = f"{'Band':>5} {'Min':>12} {'Max':>12} {'Mean':>12} {'Std':>12}"

    print(header)
    print("-" * len(header))

    for s in stats:
        if has_wl:
            print(f"{s['band']:>5d} {s['wavelength_nm']:>10.2f}nm {s['min']:>12.4f} {s['max']:>12.4f} {s['mean']:>12.4f} {s['std']:>12.4f}")
        else:
            print(f"{s['band']:>5d} {s['min']:>12.4f} {s['max']:>12.4f} {s['mean']:>12.4f} {s['std']:>12.4f}")


def save_stats_csv(stats, csv_path):
    """Save stats to CSV."""
    import csv
    keys = stats[0].keys()
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(stats)
    print(f"Saved stats to {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="Band statistics for hyperspectral data")
    parser.add_argument("capture_id", help="Capture ID (e.g. 444)")
    parser.add_argument("--mat", help="Path to .mat file")
    parser.add_argument("--source", choices=["capture", "results"], default="capture")
    parser.add_argument("--prefix", help="Calibration prefix: WHITEREF, DARKREF, or WHITEDARKREF")
    parser.add_argument("--csv", help="Save stats to CSV file")
    args = parser.parse_args()

    basedir = os.path.dirname(os.path.abspath(__file__))
    cube, wavelengths = load_cube(args.capture_id, args.mat, args.source, args.prefix, basedir)

    stats = compute_band_stats(cube, wavelengths)
    print_band_stats(stats)

    if args.csv:
        save_stats_csv(stats, args.csv)


if __name__ == "__main__":
    main()
