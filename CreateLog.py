from demoparser2 import DemoParser
import pandas as pd  # NEW


# === EDIT THIS LIST ONLY ====================================
list_of_activities = [
    # "is_alive",
    # "last_place_name",
    "bomb_planted",
    "bomb_exploded",
    "bomb_defused",
    "flashbang_detonate",
    "molotov_detonate",
    "smokegrenade_detonate",
    "round_winner",
]
# ============================================================


def classify_activities(parser, wanted):
    """
    Split requested activities into:
      - tick_fields  (pulled with parse_ticks per player/per tick)
      - special_events (pulled via parse_event)
    Always include 'tick' and 'name' in tick_fields so we know WHEN and WHO.
    """
    try:
        game_events = set(parser.list_game_events())
    except Exception:
        game_events = set()

    tick_fields = []
    special_events = []

    for a in wanted:
        if a == "round_winner" or a in game_events:
            if a not in special_events:
                special_events.append(a)
        else:
            if a not in tick_fields:
                tick_fields.append(a)

    for base_col in ["tick", "name"]:
        if base_col not in tick_fields:
            tick_fields.insert(0, base_col)

    return tick_fields, special_events


def get_tick_change_events(tick_fields, df):
    """
    For each player and each tick-field, log an event WHEN the value changes.
    Output for a round:
        { tick: [(player_name, activity, value), ...], ... }
    """
    round_log = {}
    last_seen = {}  # (player_name, field) -> last_value

    # chronological order
    for _, row in df.sort_values("tick").iterrows():
        tick = int(row["tick"])
        player = row["name"]

        for field in tick_fields:
            if field in ("tick", "name"):
                continue
            if field not in row:
                continue

            value = row[field]
            if value in ["", None]:
                continue

            key = (player, field)
            if key not in last_seen or last_seen[key] != value:
                round_log.setdefault(tick, []).append(
                    (player, field, str(value))
                )
                last_seen[key] = value

    return round_log


def _safe_parse_event(parser, ev_name):
    """
    Returns a pandas DataFrame for the given event name, or an empty DataFrame.
    Handles cases where demoparser2 returns [] instead of a DataFrame.
    """
    try:
        raw = parser.parse_event(ev_name)
    except Exception:
        return pd.DataFrame()  # nothing

    # if it's already a DataFrame-like (has iterrows), just return it
    if hasattr(raw, "iterrows"):
        return raw

    # if it's e.g. [] or [ { .. }, { .. } ], turn it into a DataFrame
    try:
        return pd.DataFrame(raw)
    except Exception:
        return pd.DataFrame()


def _build_userid_to_name_map(parser):
    """
    Build a map: userid (short game ID like 217) -> playername ("Alkaren").
    We look at common player info events that usually have both userid and name.
    Robust against parse_event returning [].
    """
    userid_to_name = {}

    for ev_name in ["player_connect_full", "player_spawn", "player_team"]:
        df = _safe_parse_event(parser, ev_name)
        if df.empty:
            continue

        for _, row in df.iterrows():
            uid = row.get("userid", None)
            pname = row.get("name", None)
            if uid not in [None, ""] and pname not in [None, ""]:
                userid_to_name[str(uid)] = str(pname)

    return userid_to_name


def add_special_events(round_log, parser, start_tick, end_tick, special_events):
    """
    Add one-shot events (flashbang_detonate, bomb_planted, round_winner, ...).

    We ALWAYS emit tuples like:
      (playername, activity, value)

    playername:
      1. row["name"] if available
      2. if not, row["userid"] -> look up real player name
      3. fallback: event name in caps
    """
    userid_to_name = _build_userid_to_name_map(parser)

    # --- round_winner is derived from round_end, not a direct event ---
    if "round_winner" in special_events:
        end_df = _safe_parse_event(parser, "round_end").sort_values("tick")
        end_df = end_df[
            (end_df["tick"] > start_tick) &
            (end_df["tick"] <= end_tick)
        ]
        if not end_df.empty:
            row = end_df.iloc[-1]
            tick = int(row["tick"])

            winner_side = row.get("winner", None)   # "T"/"CT"/etc.
            reason      = row.get("reason", None)   # why they won
            msg         = row.get("message", "")    # text like "Terrorists win"

            parts = []
            if winner_side not in [None, ""]:
                parts.append(str(winner_side))
            if reason not in [None, ""]:
                parts.append(f"reason={reason}")
            if msg:
                parts.append(msg)
            if not parts:
                parts.append("round_winner")

            value_text = " | ".join(parts)

            round_log.setdefault(tick, []).append(
                ("ROUND", "round_winner", value_text)
            )

    # --- all real in-game events the user asked for (bomb_planted, flashbang_detonate, etc.) ---
    for ev_name in special_events:
        if ev_name == "round_winner":
            continue

        ev_df = _safe_parse_event(parser, ev_name)
        if ev_df.empty:
            continue

        # keep only events in this round's tick window
        ev_df = ev_df[
            (ev_df["tick"] >= start_tick) &
            (ev_df["tick"] <= end_tick)
        ]
        if ev_df.empty:
            continue

        for _, row in ev_df.iterrows():
            tick = int(row["tick"])

            # PLAYERNAME RESOLUTION
            pname = row.get("name", None)

            if (pname in [None, ""]) and ("userid" in row):
                uid_str = str(row["userid"])
                if uid_str in userid_to_name:
                    pname = userid_to_name[uid_str]

            if pname in [None, ""]:
                pname = ev_name.upper()

            # VALUE RESOLUTION (bomb site, etc.)
            value_out = True
            for cand in ["site", "bombsite", "winner", "message"]:
                if cand in row and row[cand] not in [None, ""]:
                    value_out = row[cand]
                    break

            round_log.setdefault(tick, []).append(
                (str(pname), ev_name, str(value_out))
            )

    # return ticks sorted
    return dict(sorted(round_log.items()))


def get_round_intervals(parser):
    """
    Returns list of (start_tick, end_tick) for each round.
    We match round_start[i] with round_end[i+1] like before.
    """
    starts = list(parser.parse_event("round_start")["tick"])
    ends   = list(parser.parse_event("round_end")["tick"])

    out = []
    for i in range(min(len(starts), len(ends) - 1)):
        out.append((starts[i], ends[i + 1]))
    return out


def getListOfActivitiesPerRound(max_rounds=5):
    """
    Returns:
      [
        { tick: [(player, activity, value), ...], ... },  # round 1
        { ... },                                         # round 2
        ...
      ]
    Only first max_rounds rounds are returned.
    """
    parser = DemoParser("heroic-vs-3dmax-m1-dust2.dem")

    tick_fields, special_events = classify_activities(parser, list_of_activities)

    intervals = get_round_intervals(parser)[:max_rounds]

    rounds_output = []

    for (start_tick, end_tick) in intervals:
        # all ticks in this round
        tick_range = list(range(start_tick, end_tick + 1))

        # pull per-tick data
        round_df = parser.parse_ticks(tick_fields, ticks=tick_range)

        # 1) per-player state-change events (if you enabled any tick fields like is_alive)
        log_this_round = get_tick_change_events(tick_fields, round_df)

        # 2) grenade/bomb/round_winner events with resolved player names
        log_this_round = add_special_events(
            log_this_round,
            parser,
            start_tick,
            end_tick,
            special_events
        )

        rounds_output.append(log_this_round)

    return rounds_output
