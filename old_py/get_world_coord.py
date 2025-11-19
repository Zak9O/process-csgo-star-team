import numpy as np
import pandas as pd
from pathlib import Path

def get_world_min_max(origin, minBounds, maxBounds, centroid):
    origin = np.array(origin, dtype=float)
    minBounds = np.array(minBounds, dtype=float)
    maxBounds = np.array(maxBounds, dtype=float)
    centroid = np.array(centroid, dtype=float)
    world_min = origin + centroid + minBounds
    world_max = origin + centroid + maxBounds
    return world_min, world_max

def main(in_csv="csv_final.csv", out_csv="csv_final_with_world_with_centroid.csv"):
    p = Path(in_csv)
    if not p.exists():
        raise FileNotFoundError(f"Input CSV not found: {in_csv}")

    df = pd.read_csv(in_csv)

    # required columns for computation
    required = ["min_x","min_y","min_z","max_x","max_y","max_z","place_name"]
    for c in required:
        if c not in df.columns:
            raise KeyError(f"Missing required column: {c}")

    has_origin = all(c in df.columns for c in ("origin_x","origin_y","origin_z"))
    has_centroid = all(c in df.columns for c in ("cen_x","cen_y","cen_z"))

    out_rows = []
    for _, row in df.iterrows():
        if has_origin:
            origin = (row["origin_x"], row["origin_y"], row["origin_z"])
        elif has_centroid:
            origin = (row["cen_x"], row["cen_y"], row["cen_z"])
        else:
            origin = (0.0, 0.0, 0.0)

        centroid = (row["cen_x"], row["cen_y"], row["cen_z"]) if has_centroid else (0.0, 0.0, 0.0)

        minBounds = (row["min_x"], row["min_y"], row["min_z"])
        maxBounds = (row["max_x"], row["max_y"], row["max_z"])

        world_min, world_max = get_world_min_max(origin, minBounds, maxBounds, centroid)

        out_rows.append({
            "place_name": row["place_name"],
            "world_min_x": float(world_min[0]),
            "world_min_y": float(world_min[1]),
            "world_min_z": float(world_min[2]),
            "world_max_x": float(world_max[0]),
            "world_max_y": float(world_max[1]),
            "world_max_z": float(world_max[2]),
        })

    out_df = pd.DataFrame(out_rows, columns=[
        "place_name",
        "world_min_x","world_min_y","world_min_z",
        "world_max_x","world_max_y","world_max_z"
    ])

    out_df.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv} ({len(out_df)} rows).")

if __name__ == "__main__":
    main()
