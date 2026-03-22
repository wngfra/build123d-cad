#!/usr/bin/env python3
"""Execute a build123d script and export STEP/STL/SVG."""

import argparse
import traceback
from pathlib import Path

from helpers import exec_script, get_part, output_json, output_error, WORKSPACE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--format", choices=["step", "stl", "svg"], default="step")
    parser.add_argument("--filename", default=None)
    args = parser.parse_args()

    r = exec_script(args.script)
    if not r["ok"]:
        output_error(r["error"], r["stdout"])

    part = get_part(r["result"])
    fname = args.filename or f"model_{id(part) % 100000:05d}"
    out_path = WORKSPACE / f"{fname}.{args.format}"

    try:
        from build123d import export_step, export_stl, export_svg

        if args.format == "step":
            export_step(part, str(out_path))
        elif args.format == "stl":
            export_stl(part, str(out_path))
        elif args.format == "svg":
            export_svg(part, str(out_path))
    except Exception:
        output_error(traceback.format_exc(), r["stdout"])

    bb = part.bounding_box()
    output_json({
        "success": True,
        "artifact_path": str(out_path.resolve()),
        "format": args.format,
        "file_size_bytes": out_path.stat().st_size,
        "bounding_box_mm": {"x": round(bb.size.X, 2), "y": round(bb.size.Y, 2), "z": round(bb.size.Z, 2)},
        "stdout": r["stdout"],
    })


if __name__ == "__main__":
    main()
