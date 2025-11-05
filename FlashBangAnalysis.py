from demoparser2 import DemoParser
import pandas as pd
import time

# https://wiki.alliedmods.net/Counter-Strike:_Global_Offensive_Events?fbclid=IwY2xjawN3_7NleHRuA2FlbQIxMQBzcnRjBmFwcF9pZAEwAAEegomBVKlDgNMZ9bgs6M8jZJFAIFvuYmdXCELbQOoOpH1Za085B1eZWVszOjk_aem_NtddrD_Tlh-0fDGfgirgoA
#The purpose of this is to figure out when a player flashes 


start = time.time()

parser = DemoParser("../heroic-vs-3dmax-m1-dust2.dem")

round_start = parser.parse_event("round_start")["tick"].to_list()
round_end = parser.parse_event("round_end")["tick"].to_list()

class Activity:
    def __init__(self, field, isStartTickImportant):
        self.isStartTickImportant = isStartTickImportant
        self.field = field
    def getField(self):
        return self.field

startTickNotImportant = ["is_alive"]
startTickImportant = ["last_place_name"]
activities = [Activity(f, True) for f in startTickImportant] + [Activity(f, False) for f in startTickNotImportant]
activities_for_demoparser = startTickImportant + startTickNotImportant


print("Parsing all ticks once...")
all_ticks_df = parser.parse_ticks(activities_for_demoparser + ["team_name", "name", "tick"])
print("Done parsing ticks.")


def getActivityFromField(activity: Activity, df: pd.DataFrame) -> dict:
    field = activity.getField()
    df = df.sort_values(["name", "tick"])

    df["prev_value"] = df.groupby("name")[field].shift(1)
    changes = df[df[field] != df["prev_value"]].dropna(subset=[field])

    field_dict = (
    changes.groupby("name")
    .apply(lambda g: list(zip(
        g["team_name"] + "_" + g[field].astype(str),
        g["tick"],
        [field] * len(g)
    )))
    .to_dict()
    )

    return field_dict


def getActivityLog(activities: list[Activity], df: pd.DataFrame) -> dict:
    log_dict = {}
    for activity in activities:
        field_dict = getActivityFromField(activity, df)
        for player, activity_list in field_dict.items():
            for activity_label, tick, field_name in activity_list:
                if not activity.isStartTickImportant and tick in round_start:
                    continue
                log_dict.setdefault(tick, []).append((activity_label, field_name, player))

    return dict(sorted(log_dict.items()))


def getListOfActivitiesPerRound() -> list[dict]:
    round_dicts = []
    for i in range(len(round_start) - 1):
        start_tick = round_start[i]
        end_tick = round_end[i + 1]
        round_df = all_ticks_df.query("@start_tick <= tick <= @end_tick")
        activity_log = getActivityLog(activities, round_df)
        round_dicts.append(activity_log)
    return round_dicts


log = getListOfActivitiesPerRound()

for round_dict in log:
    for tick, data in round_dict.items():
        print(tick, data)

end = time.time()
time_ = end - start
print(time_)