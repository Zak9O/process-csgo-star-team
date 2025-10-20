from demoparser2 import DemoParser

def sample_positions_every_second(demo_path: str, ticks_per_sec: int = 64):
    parser = DemoParser(demo_path)

    # Ask demoparser2 for the place name prop directly
    ticks = parser.parse_ticks(["X", "Y", "Z", "tick", "name", "is_alive", "last_place_name"])

    rounds = parser.parse_event("round_start")
    round_ends = parser.parse_event("round_end")

    valid_round_starts = rounds.sort_values("tick").reset_index(drop=True)
    valid_round_ends = round_ends.sort_values("tick").reset_index(drop=True)

    first_start = valid_round_starts["tick"].iloc[0]
    first_end = valid_round_ends[valid_round_ends["tick"] > first_start]["tick"].iloc[0]
    print(f"First round range: {first_start} → {first_end}")

    # Slice to round 1 and make a copy
    round1 = ticks.loc[(ticks["tick"] >= first_start) & (ticks["tick"] <= first_end)].copy()
    print("Round 1 ticks count:", len(round1))

    # Relative time and 1 Hz sampling
    round1["relative_tick"] = round1["tick"] - round1["tick"].min()
    sampled = round1[round1["relative_tick"] % ticks_per_sec == 0].copy()
    sampled["time_sec"] = sampled["relative_tick"] / float(ticks_per_sec)

    # Order rows nicely
    sampled = sampled.sort_values(["name", "relative_tick"]).reset_index(drop=True)

    print("Sampled positions:", len(sampled))
    return sampled


if __name__ == "__main__":
    demo_path = "./heroic-vs-3dmax-m1-dust2.dem"
    df = sample_positions_every_second(demo_path, ticks_per_sec=64)

    # Choose the columns you want in the CSV
    cols = ["name", "time_sec", "X", "Y", "Z", "is_alive", "last_place_name"]
    cols = [c for c in cols if c in df.columns]  # keep only present columns
    df[cols].to_csv("round1_positions_with_place.csv", index=False)
    print("✅ Saved round1_positions_with_place.csv")