from datetime import datetime, timedelta
import pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event
from CreateLog import getListOfActivitiesPerRound
from demoparser2 import DemoParser
from tqdm.auto import tqdm


def creatXes(rounds):
    event_log = EventLog()
    # implement way to split into rounds, where each round is a trace, currently everything is just one large trace
    event_log.attributes["concept:name"] = "csgo_demo_log"
    for i, round in enumerate(rounds):
        trace = Trace()
        trace.attributes["round"] = i + 1
        trace.attributes["concept:name"] = f"round_{i + 1}"

        for tick in round:
            for activity in round[tick]:
                event = Event()
                event['concept:name'] = activity[2]
                event['concept:activity'] = activity[1]
                event['time:tick'] = tick
                event['custom:value'] = activity[0]
                trace.append(event)

        event_log.append(trace)

    # Specify the path to your output XES file
    output_xes_file = 'csgo_EventLog.xes'

    # Write the event log to the XES file
    pm4py.write_xes(event_log, output_xes_file)


def createXesOld(
    rounds: list[dict],
    ticks_per_sec: int = 64,
    base_datetime: datetime = None,
    output_xes_file: str = "csgo_EventLog.xes",
    show_progress: bool = True,
    ):
    """
    Convert rounds data to a PM4Py XES event log and write it to output_xes_file.
    :param rounds:
    :param ticks_per_sec:
    :param base_datetime:
    :param output_xes_file:
    :param show_progress:
    :return:
    """
    if base_datetime is None:
        base_datetime = datetime(2025, 1, 1, 0, 0, 0)

    event_log = EventLog()
    event_log.attributes["concept:name"] = "csgo_demo_log"

    for i, round_data in enumerate(tqdm(rounds, desc="Rounds", disable=not show_progress)):
        round_idx = i + 1
        trace = Trace()
        trace.attributes["round"] = round_idx
        trace.attributes["concept:name"] = f"round_{round_idx}"

        round_start_dt = base_datetime + timedelta(minutes=10 * i)

        ticks_iter = sorted(round_data.keys())
        for tick in tqdm(ticks_iter, desc=f"Round {round_idx} ticks", leave=False, disable=not show_progress):
            timestamp = round_start_dt + timedelta(seconds=tick / float(ticks_per_sec))
            activities = round_data[tick]
            for activity in activities:
                playername = activity[0]
                field_name = activity[1]
                field_value = activity[2]

                event = Event()
                event["concept:name"] = field_value
                event["lifecycle:transition"] = "complete"
                event["time:timestamp"] = timestamp
                event["time:tick"] = tick
                event["custom:value"] = field_value

                trace.append(event)

        event_log.append(trace)

    pm4py.write_xes(event_log, output_xes_file)
    return event_log



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


def getEventLog(parser: DemoParser):
    print("Creating log...")
    rounds = getListOfActivitiesPerRound(parser, max_rounds=3)
    creatXes(rounds)
    print("Done. Log created and saved succesfully")

