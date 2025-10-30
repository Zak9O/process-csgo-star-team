from demoparser2 import DemoParser
parser = DemoParser("heroic-vs-3dmax-m1-dust2.dem")
ticks = parser.parse_ticks(["tick", "name", "is_alive", "team_name","bomb_exploded"])

list_of_activities = ["last_place_name"]

def getActivityFromField(field:str, df):

    field_dict = dict()

    for _, row in df.iterrows():
        name = row["name"]
        field_value = row[field]
        # We found some anomalies, where no zone was given, we are disregarding these
        if field_value == "":
            continue 
        tick = row["tick"]

        if name not in field_dict:
            field_dict[name] = [(field, field_value, tick)]

        else:
            _, previous_field_value,_ = field_dict[name][-1]
            if previous_field_value != field_value:
                field_dict[name].append((field, field_value, tick))

    return field_dict


def getActivityLog(activities:list[str], df):
    # this function itterates over the list of activities given, for example
    # ["is_alive", "last_place_name"]. And then makes a new dictionary
    # where each tick maps to a list of (player, field, field_value)
    log_dict = dict()
    for activity in activities:
        field_dict = getActivityFromField(activity, df)
        for player in field_dict:
            player_activities = field_dict[player]
            for activity in player_activities:
                field, field_value, tick = activity
                if tick not in log_dict:
                    log_dict[tick] = [(player, field, field_value)]
                else:
                    log_dict[tick].append((player, field, field_value))

    return dict(sorted(log_dict.items()))


def getListOfActivitiesPerRound(round_numbers: list[int]):
    """
    Build activity logs for the specific (1-based) rounds you pass in.
    Example: [4] returns only round 4; [4, 5] returns rounds 4 and 5.
    Returns a list of activity-log dicts in the same order as round_numbers.
    """
    # pull full round_start / round_end events so we get ticks AND metadata
    round_start_df = parser.parse_event("round_start")
    round_end_df = parser.parse_event("round_end")

    round_start = list(round_start_df["tick"])
    round_end = list(round_end_df["tick"])

    # get full death event data once
    deaths_df = parser.parse_event("player_death")

    # normalize the requested rounds: keep order, remove duplicates, keep only positive ints
    seen = set()
    requested_rounds = []
    for rn in round_numbers:
        if isinstance(rn, int) and rn > 0 and rn not in seen:
            requested_rounds.append(rn)
            seen.add(rn)

    # build (round_number, start_tick, end_tick) tuples
    round_intervals = []
    for rn in requested_rounds:
        i = rn - 1  # 1-based -> 0-based index for lists
        if i >= len(round_start):
            # skip if outside available starts
            continue

        # keep original behavior: pair start[i] with end[i+1] if possible, else fall back to end[i]
        if i + 1 < len(round_end):
            start_tick, end_tick = round_start[i], round_end[i + 1]
        elif i < len(round_end):
            start_tick, end_tick = round_start[i], round_end[i]
        else:
            # no valid end tick
            continue

        # sanity: ensure end >= start; if not, try to pick the first end after start
        if end_tick < start_tick:
            later_ends = [t for t in round_end if t >= start_tick]
            if later_ends:
                end_tick = later_ends[0]
            else:
                continue

        round_intervals.append((rn, start_tick, end_tick))

    list_of_dict = []

    for rn, start_tick, end_tick in round_intervals:
        # all ticks belonging to this round span
        list_of_ticks_for_round = list(range(start_tick, end_tick + 1))

        # slice per-tick data for this round
        round_df = parser.parse_ticks(list_of_activities, ticks=list_of_ticks_for_round)

        # build the normal activity log for this round
        activity_log = getActivityLog(list_of_activities, round_df)

        # figure out which players were active in this round
        players_in_round = list(round_df["name"].unique())

        # inject round_start for EACH PLAYER at start_tick
        if start_tick not in activity_log:
            activity_log[start_tick] = []
        for pname in players_in_round:
            activity_log[start_tick].insert(0, (pname, "round_start", "round_start"))

        # add deaths that happened in this round window (per player)
        if deaths_df is not None and len(deaths_df) > 0:
            round_deaths = deaths_df[
                (deaths_df["tick"] >= start_tick) & (deaths_df["tick"] <= end_tick)
            ]
            for _, row in round_deaths.iterrows():
                death_tick = row["tick"]
                victim_name = row["user_name"]
                if death_tick not in activity_log:
                    activity_log[death_tick] = [(victim_name, "player_death", "Died")]
                else:
                    activity_log[death_tick].append((victim_name, "player_death", "Died"))

        # inject round_end for EACH PLAYER at end_tick with winner/why
        matching_end_rows = round_end_df[round_end_df["tick"] == end_tick]
        winner_value = "winner_UNKNOWN_reason_UNKNOWN"
        if len(matching_end_rows) > 0:
            end_row = matching_end_rows.iloc[0]

            winner_team_code = "UNKNOWN"
            if "winner" in end_row:
                try:
                    w_int = int(end_row["winner"])
                    if w_int == 2:
                        winner_team_code = "T"
                    elif w_int == 3:
                        winner_team_code = "CT"
                    else:
                        winner_team_code = str(w_int)
                except:
                    winner_team_code = str(end_row["winner"])

            reason_code = "UNKNOWN"
            if "reason" in end_row:
                reason_code = str(end_row["reason"])

            winner_value = f"winner_{winner_team_code}_reason_{reason_code}"

        if end_tick not in activity_log:
            activity_log[end_tick] = []
        for pname in players_in_round:
            activity_log[end_tick].append((pname, "round_end", winner_value))

        # final cleanup: keep ticks sorted
        activity_log = dict(sorted(activity_log.items()))
        list_of_dict.append(activity_log)

    return list_of_dict
