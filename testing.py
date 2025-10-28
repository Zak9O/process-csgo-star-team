from demoparser2 import DemoParser
import pandas as pd


def extract_flashbang_throwers(demo_path: str) -> pd.DataFrame:
    """
    One row per flashbang detonation.

    Columns you'll get (if available in your demo):
      - tick
      - flash_thrower_id           (ID from the event)
      - flash_thrower_name         (name string from the event, if provided)
      - thrower_name               (name we matched at that tick via parse_ticks)
      - flash_x / flash_y / flash_z  (detonation coords)
      - thrower_team_name / thrower_team_num / thrower_team
      - thrower_pos_X / _Y / _Z      (thrower location at that tick)
      - thrower_is_alive
      - thrower_place                (map area / callout)
    """

    parser = DemoParser(demo_path)

    # 1. All flashbang detonation events
    try:
        fb_events = parser.parse_event("flashbang_detonate").copy()
    except Exception:
        return pd.DataFrame()  # event not available / parser doesn't know it

    if fb_events.empty:
        return pd.DataFrame()

    fb_events = fb_events.sort_values("tick").reset_index(drop=True)

    # --- identify the thrower (ID AND name if present in the event row) ---
    thrower_id_candidates = [
        "userid",
        "user",
        "player",
        "player_entindex",
        "entityid",
        "player_steamid",
        "steamid",
    ]
    thrower_name_candidates = [
        "player_name",
        "attacker_name",
        "name",
    ]

    # choose ID column
    chosen_thrower_id_col = None
    for c in thrower_id_candidates + thrower_name_candidates:
        # (include name-like columns at the end just in case userid isn't there,
        #  so we always get *something*)
        if c in fb_events.columns:
            chosen_thrower_id_col = c
            break

    if chosen_thrower_id_col is not None:
        fb_events["flash_thrower_id"] = fb_events[chosen_thrower_id_col].astype(str)
    else:
        fb_events["flash_thrower_id"] = "UNKNOWN"

    # choose "flash_thrower_name" from the event row, if available
    chosen_thrower_name_col = None
    for c in thrower_name_candidates:
        if c in fb_events.columns:
            chosen_thrower_name_col = c
            break
    if chosen_thrower_name_col is not None:
        fb_events["flash_thrower_name"] = fb_events[chosen_thrower_name_col].astype(str)
    else:
        fb_events["flash_thrower_name"] = None

    # grab detonation coords if present
    keep_cols = ["tick", "flash_thrower_id", "flash_thrower_name"]
    coord_map = {}
    if "x" in fb_events.columns:
        keep_cols.append("x")
        coord_map["x"] = "flash_x"
    if "y" in fb_events.columns:
        keep_cols.append("y")
        coord_map["y"] = "flash_y"
    if "z" in fb_events.columns:
        keep_cols.append("z")
        coord_map["z"] = "flash_z"

    fb_events_trimmed = fb_events[keep_cols].rename(columns=coord_map)

    # 2. For those ticks, grab player snapshots
    flash_ticks = sorted(fb_events_trimmed["tick"].unique().tolist())

    player_cols_base = [
        "tick",
        "name",
        "X", "Y", "Z",
        "is_alive",
        "last_place_name",
        "team_name",
        "team_num",
        "team",
    ]

    # possible ID columns we can use to link players to flash_thrower_id
    candidate_id_cols = [
        "userid",
        "user",
        "player_entindex",
        "entityid",
        "player_steamid",
        "steamid",
    ]

    parser_cols = player_cols_base + candidate_id_cols
    players_df = parser.parse_ticks(parser_cols, ticks=flash_ticks).copy()

    # normalize per-player ID -> "user_id"
    chosen_player_id_col = None
    for c in candidate_id_cols:
        if c in players_df.columns:
            chosen_player_id_col = c
            break
    if chosen_player_id_col is not None:
        players_df["user_id"] = players_df[chosen_player_id_col].astype(str)
    else:
        players_df["user_id"] = players_df["name"].astype(str)

    # keep only what we need from each player row, then rename for clarity
    snap_cols = [
        "tick",
        "user_id",
        "name",
        "team_name",
        "team_num",
        "team",
        "X", "Y", "Z",
        "is_alive",
        "last_place_name",
    ]
    snap_cols = [c for c in snap_cols if c in players_df.columns]
    thrower_snapshots = players_df[snap_cols].rename(columns={
        "name": "thrower_name",
        "team_name": "thrower_team_name",
        "team_num": "thrower_team_num",
        "team": "thrower_team",
        "X": "thrower_pos_X",
        "Y": "thrower_pos_Y",
        "Z": "thrower_pos_Z",
        "is_alive": "thrower_is_alive",
        "last_place_name": "thrower_place",
    })

    # 3. Join flash events ↔ thrower snapshot using tick + ID
    merged = fb_events_trimmed.merge(
        thrower_snapshots,
        how="left",
        left_on=["tick", "flash_thrower_id"],
        right_on=["tick", "user_id"],
        suffixes=("", "_player"),
    )

    # we don't need the technical join key user_id anymore
    if "user_id" in merged.columns:
        merged = merged.drop(columns=["user_id"])

    # final nice column order
    nice_cols = [
        "tick",
        "flash_thrower_id",
        "flash_thrower_name",        # <- raw name from event (if stored there)
        "thrower_name",              # <- resolved name from snapshot
        "flash_x", "flash_y", "flash_z",
        "thrower_team_name",
        "thrower_team_num",
        "thrower_team",
        "thrower_pos_X", "thrower_pos_Y", "thrower_pos_Z",
        "thrower_is_alive",
        "thrower_place",
    ]
    nice_cols = [c for c in nice_cols if c in merged.columns]

    merged = merged[nice_cols].sort_values(["tick"]).reset_index(drop=True)

    return merged


# EXAMPLE USAGE
if __name__ == "__main__":
    demo_path = "heroic-vs-3dmax-m1-dust2.dem"
    df_flash_throwers = extract_flashbang_throwers(demo_path)

    df_flash_throwers.to_csv("flashbang_throwers.csv", index=False)
    print("✅ Saved flashbang_throwers.csv")
