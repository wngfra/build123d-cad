#!/usr/bin/env python3
"""Generate a 2D cross-section SVG at a given plane and offset."""

import argparse
import traceback

from helpers import exec_script, get_part, output_json, output_error, WORKSPACE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--plane", choices=["XY", "XZ", "YZ"], default="XY")
    parser.add_argument("--offset", type=float, default=0.0)
    parser.add_argument("--filename", default=None)
    args = parser.parse_args()

    r = exec_script(args.script)
    if not r["ok"]:
        output_error(r["error"], r["stdout"])

    part = get_part(r["result"])
    fname = args.filename or f"section_{args.plane}_{args.offset}"
    out_path = WORKSPACE / f"{fname}.svg"

    try:
        from build123d import Plane, export_svg

        planes = {"XY": Plane.XY, "XZ": Plane.XZ, "YZ": Plane.YZ}
        section_plane = planes[args.plane].offset(args.offset)
        section = part.section(plane=section_plane)
        export_svg(section, str(out_path))

        output_json({
            "success": True,
            "artifact_path": str(out_path.resolve()),
            "plane": args.plane,
            "offset_mm": args.offset,
            "section_edge_count": len(section.edges()) if hasattr(section, "edges") else 0,
            "stdout": r["stdout"],
        })
    except Exception:
        output_error(traceback.format_exc(), r["stdout"])


if __name__ == "__main__":
    main()
