import pm4py
from demoparser2.demoparser2 import DemoParser
from pandas import DataFrame
from pm4py.objects.log.obj import EventLog, Trace, Event


def eventLogDictToPm4py(event_log_dict):
    import pandas as pd
    from pm4py.objects.log.util import dataframe_utils
    from pm4py.objects.conversion.log import converter as log_converter

    # Create list to hold all events
    all_events = []

    for case_id, case_data in event_log_dict.items():
        for event in case_data["events"]:
            event_row = {
                "case:concept:name": case_id,  # Changed from concept:name
                "concept:name": event["concept:name"],
                "time:timestamp": pd.Timestamp(event["time:tick"], unit='s')  # Convert tick to timestamp
            }
            # Add any other attributes from the case
            for key, value in case_data["attributes"].items():
                if key != "concept:name":  # Skip concept:name as it's case-specific
                    event_row[f"case:{key}"] = value

            all_events.append(event_row)

    # Create DataFrame
    df = pd.DataFrame(all_events)

    # Sort by case and timestamp
    df = df.sort_values(["case:concept:name", "time:timestamp"])

    # Convert to event log
    event_log = log_converter.apply(df, variant=log_converter.Variants.TO_EVENT_LOG)

    return event_log


def getFirstBloods(parser: DemoParser) -> DataFrame:
    fb_events = parser.parse_event("player_death", other=["total_rounds_played", "attacker_name"])
    # remove all columns except attacker_name, assister_name,
    # assistedflash, distance, headshot, total_rounds_played, weapon
    fb_events = fb_events[[
        "tick",
        "attacker_name",
        "assister_name",
        "assistedflash",
        "distance",
        "headshot",
        "total_rounds_played",
        "weapon"
    ]]
    # remove entries with weapon C4
    fb_events = fb_events[fb_events["weapon"] != "planted_c4"]

    # now take only the first death per round
    fb_events = fb_events.sort_values(by=["tick"])
    fb_events = fb_events.drop_duplicates(subset=["total_rounds_played"], keep="first")

    return fb_events


def getActionListForFirstBloods(data: DataFrame, first_bloods: DataFrame) -> list[DataFrame]:
    # for each killer in first_bloods, get each row from data where name == attacker_name, total_rounds_played matches
    # And tick is less than or equal to the tick of the first blood
    # add to a new dataframe
    action_list = []
    for _, fb_row in first_bloods.iterrows():
        attacker_name = fb_row["attacker_name"]
        round_number = fb_row["total_rounds_played"]
        fb_tick = fb_row["tick"]

        player_actions = data[
            (data["name"] == attacker_name) &
            (data["total_rounds_played"] == round_number) &
            (data["tick"] <= fb_tick)
        ]
        # remove entries where all entries except tick and name haven't changed
        filtered_actions = player_actions.sort_values(by=["tick"])
        filtered_actions = filtered_actions.drop_duplicates(
            subset=[col for col in filtered_actions.columns
                    if col not in ["tick" , "name"]], keep="first")

        # remove all entries before empty last_place_name including the empty one
        if "last_place_name" in filtered_actions.columns:
            empty_place_indices = filtered_actions[filtered_actions["last_place_name"] == ""].index
            if not empty_place_indices.empty:
                first_empty_index = empty_place_indices[0]
                filtered_actions = filtered_actions.loc[first_empty_index + 1:]


        action_list.append(filtered_actions)

    return action_list


def eventLogFromActionList(action_list_for_first_bloods: list[DataFrame], first_bloods: DataFrame, game_name: str = "") :
    event_log = {}
    for i, action_df in enumerate(action_list_for_first_bloods):

        if action_df.empty:
            print(f"Empty action dataframe for first blood index {i}, on game {game_name}, skipping.")
            continue

        player_name = action_df["name"].iloc[0]


        if player_name != first_bloods["attacker_name"].iloc[i]:
            raise ValueError("Player name mismatch between action list and first bloods")
        if len(action_list_for_first_bloods) != len(first_bloods["weapon"]):
            print("no match")

        weapon = first_bloods["weapon"].iloc[i]
        # find team_name from action_df where round number matches
        round_number = first_bloods["total_rounds_played"].iloc[i]
        round_rows = action_df[action_df["total_rounds_played"] == round_number]
        if round_rows.empty:
            team_name = "Unknown"
        else:
            team_name = round_rows["team_name"].iloc[0]


        att = {"player": player_name, "weapon": weapon, "team_name": team_name}
        event_list = []
        i = 0

        # first append spawn event
        first_tick = action_df["tick"].iloc[0]
        event_list.append({
            "concept:name": "spawned",
            "time:tick": first_tick
        })

        # loop through action_df and create event list, if last_place_name changes add moved_to_place event
        # if armor goes up add bought_armor event
        # if armor or health goes down add took_damage event
        indices = action_df.index.tolist()
        while i < len(indices) - 1:
            current_row = action_df.loc[indices[i]]
            next_row = action_df.loc[indices[i + 1]]

            tick = next_row["tick"]

            # Check for last_place_name change
            if current_row["last_place_name"] != next_row["last_place_name"]:
                event_list.append({
                    "concept:name": "moved_to_place",
                    "place_name": next_row["last_place_name"],
                    "time:tick": tick
                })

            # Check for armor increase
            if next_row["armor_value"] > current_row["armor_value"]:
                event_list.append({
                    "concept:name": "bought_armor",
                    "new_armor": next_row["armor_value"],
                    "time:tick": tick
                })

            # Check for health or armor decrease
            if next_row["health"] < current_row["health"] or next_row["armor_value"] < current_row["armor_value"]:
                event_list.append({
                    "concept:name": "took_damage",
                    "change": (current_row["health"] + current_row["armor_value"]) -
                              (next_row["health"] + next_row["armor_value"]) ,
                    "time:tick": tick
                })

            i += 1

        # add first blood event
        event_list.append({
            "concept:name": "first_blood",
            "time:tick": action_df.loc[indices[-1]]["tick"],
        })


        event_log[f"{game_name}_{player_name}_{round_number}"] = {"attributes": att, "events": event_list}
    return event_log
