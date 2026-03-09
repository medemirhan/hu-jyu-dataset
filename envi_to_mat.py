#!/usr/bin/env python3
"""
Convert ENVI raw+hdr hyperspectral data to a MATLAB .mat file.

Usage:
    # Convert a raw capture (default: looks for <ID>.raw in capture/ folder)
    python envi_to_mat.py 444

    # Convert a specific file pair
    python envi_to_mat.py 444 --hdr data/444/capture/444.hdr --raw data/444/capture/444.raw

    # Convert reflectance data from results/ folder
    python envi_to_mat.py 444 --source results

    # Convert a calibration file
    python envi_to_mat.py 444 --source capture --prefix WHITEREF

    # Specify output path
    python envi_to_mat.py 444 -o my_output.mat

Environment setup:
    conda env create -f environment.yml
    conda activate hsi
"""

import argparse
import os
import sys
import numpy as np
from scipy.io import savemat
import spectral.io.envi as envi


def parse_hdr(hdr_path):
    """Parse ENVI header file and return metadata dict."""
    with open(hdr_path, "r") as f:
        text = f.read()

    meta = {}
    # Collapse multi-line values (lines inside { })
    import re
    text = re.sub(r"\{([^}]*)\}", lambda m: "{" + m.group(1).replace("\n", "") + "}", text)

    for line in text.splitlines():
        if "=" in line:
            key, val = line.split("=", 1)
            meta[key.strip().lower()] = val.strip()

    return meta


def read_envi_cube(hdr_path, raw_path):
    """Read an ENVI datacube and return (cube_array, wavelengths, metadata)."""
    meta = parse_hdr(hdr_path)

    samples = int(meta["samples"])
    lines = int(meta["lines"])
    bands = int(meta["bands"])
    dtype_code = int(meta["data type"])
    interleave = meta["interleave"].strip().lower()
    header_offset = int(meta.get("header offset", 0))
    byte_order = int(meta.get("byte order", 0))

    # ENVI data type mapping
    envi_dtype = {
        1: np.uint8, 2: np.int16, 3: np.int32,
        4: np.float32, 5: np.float64,
        12: np.uint16, 13: np.uint32, 14: np.int64, 15: np.uint64,
    }
    if dtype_code not in envi_dtype:
        raise ValueError(f"Unsupported ENVI data type code: {dtype_code}")

    dt = envi_dtype[dtype_code]
    if byte_order == 1:
        dt = dt.newbyteorder(">")

    # Read raw binary
    with open(raw_path, "rb") as f:
        f.seek(header_offset)
        raw = np.fromfile(f, dtype=dt)

    # Reshape according to interleave
    if interleave == "bil":
        cube = raw.reshape((lines, bands, samples)).transpose(0, 2, 1)
    elif interleave == "bip":
        cube = raw.reshape((lines, samples, bands))
    elif interleave == "bsq":
        cube = raw.reshape((bands, lines, samples)).transpose(1, 2, 0)
    else:
        raise ValueError(f"Unknown interleave: {interleave}")

    # cube shape: (lines, samples, bands) i.e. (rows, cols, bands)

    # Parse wavelengths
    wavelengths = None
    wl_str = meta.get("wavelength", "")
    if wl_str:
        wl_str = wl_str.strip("{} ")
        if wl_str:
            wavelengths = np.array([float(w) for w in wl_str.split(",") if w.strip()])

    return cube, wavelengths, meta


def envi_to_mat(hdr_path, raw_path, output_path):
    """Convert ENVI raw+hdr to .mat file with key 'cube' and 'wavelengths'."""
    cube, wavelengths, meta = read_envi_cube(hdr_path, raw_path)

    mat_dict = {"cube": cube}
    if wavelengths is not None:
        mat_dict["wavelengths"] = wavelengths

    savemat(output_path, mat_dict, do_compression=True)
    print(f"Saved {output_path}  shape={cube.shape}  dtype={cube.dtype}")
    return output_path


def resolve_paths(capture_id, source="capture", prefix=None, basedir=None):
    """Resolve hdr/raw paths from a capture ID."""
    if basedir is None:
        basedir = os.path.dirname(os.path.abspath(__file__))

    capture_dir = os.path.join(basedir, "data", str(capture_id))
    if not os.path.isdir(capture_dir):
        raise FileNotFoundError(f"Capture directory not found: {capture_dir}")

    if source == "capture":
        folder = os.path.join(capture_dir, "capture")
        if prefix:
            name = f"{prefix}_{capture_id}"
        else:
            name = str(capture_id)
        hdr = os.path.join(folder, f"{name}.hdr")
        raw = os.path.join(folder, f"{name}.raw")
    elif source == "results":
        folder = os.path.join(capture_dir, "results")
        name = f"REFLECTANCE_{capture_id}"
        hdr = os.path.join(folder, f"{name}.hdr")
        raw = os.path.join(folder, f"{name}.dat")
    else:
        raise ValueError(f"Unknown source: {source}. Use 'capture' or 'results'.")

    if not os.path.isfile(hdr):
        raise FileNotFoundError(f"HDR file not found: {hdr}")
    if not os.path.isfile(raw):
        raise FileNotFoundError(f"Raw file not found: {raw}")

    return hdr, raw


def main():
    parser = argparse.ArgumentParser(description="Convert ENVI hyperspectral data to .mat")
    parser.add_argument("capture_id", help="Capture ID (e.g. 444)")
    parser.add_argument("--hdr", help="Path to .hdr file (overrides auto-detection)")
    parser.add_argument("--raw", help="Path to .raw/.dat file (overrides auto-detection)")
    parser.add_argument("--source", choices=["capture", "results"], default="capture",
                        help="Source folder: 'capture' for raw data, 'results' for reflectance (default: capture)")
    parser.add_argument("--prefix", help="Calibration prefix: WHITEREF, DARKREF, or WHITEDARKREF")
    parser.add_argument("-o", "--output", help="Output .mat file path")
    args = parser.parse_args()

    basedir = os.path.dirname(os.path.abspath(__file__))

    if args.hdr and args.raw:
        hdr, raw = args.hdr, args.raw
    else:
        hdr, raw = resolve_paths(args.capture_id, args.source, args.prefix, basedir)

    if args.output:
        out = args.output
    else:
        out = os.path.join(basedir, f"{args.capture_id}.mat")

    envi_to_mat(hdr, raw, out)


if __name__ == "__main__":
    main()
