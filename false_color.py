#!/usr/bin/env python3
"""
Generate a false-color RGB visualization from a hyperspectral datacube.

Usage:
    # Default false-color using bands {70,53,19} from capture data
    python false_color.py 444

    # Custom band selection (R,G,B as 0-indexed band numbers)
    python false_color.py 444 --bands 100 70 30

    # Use reflectance data
    python false_color.py 444 --source results

    # Save to file
    python false_color.py 444 --save false_color_444.png

    # Use a pre-converted .mat file
    python false_color.py 444 --mat 444.mat

Environment setup:
    conda env create -f environment.yml
    conda activate hsi
"""

import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
from envi_to_mat import read_envi_cube, resolve_paths, parse_hdr
from spectral_signature import load_cube


def get_default_bands(capture_id, source="capture", prefix=None, basedir=None):
    """Read default bands from the HDR file (0-indexed)."""
    hdr, _ = resolve_paths(capture_id, source, prefix, basedir)
    meta = parse_hdr(hdr)
    db_str = meta.get("default bands", "")
    db_str = db_str.strip("{} ")
    if db_str:
        # HDR uses 1-indexed bands; convert to 0-indexed
        bands = [int(float(b.strip())) - 1 for b in db_str.split(",")]
        return bands
    return [69, 52, 18]  # fallback: bands 70,53,19 (0-indexed)


def false_color(cube, bands, percentile_stretch=(2, 98)):
    """
    Create a false-color RGB image from a datacube.
    bands: list of 3 band indices [R, G, B] (0-indexed)
    percentile_stretch: contrast stretch percentiles
    """
    rgb = np.stack([cube[:, :, b].astype(np.float64) for b in bands], axis=-1)

    # Per-channel percentile stretch for better contrast
    for i in range(3):
        ch = rgb[:, :, i]
        lo = np.percentile(ch, percentile_stretch[0])
        hi = np.percentile(ch, percentile_stretch[1])
        if hi > lo:
            rgb[:, :, i] = np.clip((ch - lo) / (hi - lo), 0, 1)
        else:
            rgb[:, :, i] = 0

    return rgb


def show_false_color(cube, bands, wavelengths=None, save_path=None, title=None):
    """Display or save a false-color image."""
    rgb = false_color(cube, bands)

    band_labels = []
    for b in bands:
        if wavelengths is not None and b < len(wavelengths):
            band_labels.append(f"band {b} ({wavelengths[b]:.0f} nm)")
        else:
            band_labels.append(f"band {b}")

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(rgb)
    ax.set_title(title or f"False Color: R={band_labels[0]}, G={band_labels[1]}, B={band_labels[2]}")
    ax.axis("off")
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved to {save_path}")
    else:
        plt.show()

    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="False-color visualization of hyperspectral data")
    parser.add_argument("capture_id", help="Capture ID (e.g. 444)")
    parser.add_argument("--bands", type=int, nargs=3, metavar=("R", "G", "B"),
                        help="Band indices for R, G, B channels (0-indexed). Default: from HDR file")
    parser.add_argument("--mat", help="Path to .mat file (skips ENVI reading)")
    parser.add_argument("--source", choices=["capture", "results"], default="capture",
                        help="Source: 'capture' or 'results' (default: capture)")
    parser.add_argument("--prefix", help="Calibration prefix: WHITEREF, DARKREF, or WHITEDARKREF")
    parser.add_argument("--save", help="Save image to file instead of displaying")
    args = parser.parse_args()

    basedir = os.path.dirname(os.path.abspath(__file__))
    cube, wavelengths = load_cube(args.capture_id, args.mat, args.source, args.prefix, basedir)

    if args.bands:
        bands = args.bands
    else:
        bands = get_default_bands(args.capture_id, args.source, args.prefix, basedir)

    title = f"False Color — Capture {args.capture_id} ({args.source})"
    show_false_color(cube, bands, wavelengths, args.save, title)


if __name__ == "__main__":
    main()
