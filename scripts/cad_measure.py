#!/usr/bin/env python3
"""Execute a build123d script and return measurements."""

import argparse
import traceback

from helpers import exec_script, get_part, output_json, output_error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    args = parser.parse_args()

    r = exec_script(args.script)
    if not r["ok"]:
        output_error(r["error"], r["stdout"])

    part = get_part(r["result"])

    try:
        bb = part.bounding_box()
        com = part.center()
        output_json({
            "success": True,
            "bounding_box_mm": {"x": round(bb.size.X, 2), "y": round(bb.size.Y, 2), "z": round(bb.size.Z, 2)},
            "volume_mm3": round(part.volume, 2),
            "surface_area_mm2": round(part.area, 2),
            "center_of_mass_mm": {"x": round(com.X, 2), "y": round(com.Y, 2), "z": round(com.Z, 2)},
            "face_count": len(part.faces()),
            "edge_count": len(part.edges()),
            "stdout": r["stdout"],
        })
    except Exception:
        output_error(traceback.format_exc(), r["stdout"])


if __name__ == "__main__":
    main()
