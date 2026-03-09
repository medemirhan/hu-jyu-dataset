"""
Plot the spectral signature of a pixel from a hyperspectral .mat file.

Usage:
    # Plot spectral signature at pixel (row=100, col=200) for capture 444
    python spectral_signature.py 444 100 200

    # Use a pre-converted .mat file directly
    python spectral_signature.py 444 100 200 --mat 444.mat

    # Use reflectance data instead of raw capture
    python spectral_signature.py 444 100 200 --source results

    # Plot multiple pixels for comparison
    python spectral_signature.py 444 100 200 --also 150,250 200,300

    # Use a larger averaging window (default is 5x5)
    python spectral_signature.py 444 100 200 --window 11

    # Use a single pixel (no averaging)
    python spectral_signature.py 444 100 200 --window 1

    # Save to file instead of showing
    python spectral_signature.py 444 100 200 --save signature.png

Environment setup:
    conda env create -f environment.yml
    conda activate hsi
"""

import argparse
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import loadmat
from envi_to_mat import read_envi_cube, resolve_paths


def load_cube(capture_id, mat_path=None, source="capture", prefix=None, basedir=None):
    """Load hyperspectral cube and wavelengths, from .mat or raw ENVI."""
    if mat_path and os.path.isfile(mat_path):
        data = loadmat(mat_path)
        cube = data["cube"]
        wavelengths = data.get("wavelengths", None)
        if wavelengths is not None:
            wavelengths = wavelengths.flatten()
        return cube, wavelengths

    hdr, raw = resolve_paths(capture_id, source, prefix, basedir)
    cube, wavelengths, _ = read_envi_cube(hdr, raw)
    return cube, wavelengths


def extract_spectrum(cube, row, col, window=5):
    """
    Extract mean spectrum over a window centered at (row, col).
    Window is clamped to image boundaries.
    """
    h, w = cube.shape[:2]
    half = window // 2
    r0 = max(0, row - half)
    r1 = min(h, row + half + 1)
    c0 = max(0, col - half)
    c1 = min(w, col + half + 1)
    region = cube[r0:r1, c0:c1, :].astype(np.float64)
    return np.mean(region, axis=(0, 1))


def plot_spectral_signature(cube, wavelengths, pixels, window=5, save_path=None, title=None):
    """
    Plot spectral signatures for given pixel coordinates.
    pixels: list of (row, col) tuples
    window: size of the averaging window (e.g. 5 means 5x5)
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    for row, col in pixels:
        if row < 0 or row >= cube.shape[0] or col < 0 or col >= cube.shape[1]:
            print(f"Warning: pixel ({row}, {col}) out of bounds {cube.shape[:2]}, skipping.")
            continue

        spectrum = extract_spectrum(cube, row, col, window)
        label = f"({row}, {col})"
        if window > 1:
            label += f" [{window}x{window}]"
        if wavelengths is not None:
            ax.plot(wavelengths, spectrum, label=label)
        else:
            ax.plot(spectrum, label=label)

    ax.set_xlabel("Wavelength (nm)" if wavelengths is not None else "Band index")
    ax.set_ylabel("Value")
    ax.set_title(title or "Spectral Signature")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150)
        print(f"Saved plot to {save_path}")
    else:
        plt.show()

    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Plot spectral signature of a pixel")
    parser.add_argument("capture_id", help="Capture ID (e.g. 444)")
    parser.add_argument("row", type=int, help="Pixel row (0-indexed)")
    parser.add_argument("col", type=int, help="Pixel column (0-indexed)")
    parser.add_argument("--mat", help="Path to .mat file (skips ENVI reading)")
    parser.add_argument("--source", choices=["capture", "results"], default="capture",
                        help="Source: 'capture' or 'results' (default: capture)")
    parser.add_argument("--prefix", help="Calibration prefix: WHITEREF, DARKREF, or WHITEDARKREF")
    parser.add_argument("--window", type=int, default=5,
                        help="Averaging window size (default: 5, i.e. 5x5 neighborhood)")
    parser.add_argument("--also", nargs="+", metavar="ROW,COL",
                        help="Additional pixels to plot (e.g. --also 150,250 200,300)")
    parser.add_argument("--save", help="Save plot to file instead of displaying")
    args = parser.parse_args()

    basedir = os.path.dirname(os.path.abspath(__file__))
    cube, wavelengths = load_cube(args.capture_id, args.mat, args.source, args.prefix, basedir)

    pixels = [(args.row, args.col)]
    if args.also:
        for pair in args.also:
            r, c = pair.split(",")
            pixels.append((int(r), int(c)))

    source_label = args.source if not args.prefix else args.prefix
    title = f"Spectral Signature — Capture {args.capture_id} ({source_label})"
    plot_spectral_signature(cube, wavelengths, pixels, args.window, args.save, title)


if __name__ == "__main__":
    main()
