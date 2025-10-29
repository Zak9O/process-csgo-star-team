from datetime import datetime, timedelta
import pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event


def creatXes(
    rounds,
    ticks_per_sec: int = 64,
    base_datetime: datetime = None,
    output_xes_file: str = "csgo_EventLog.xes",
):
    if base_datetime is None:
        base_datetime = datetime(2025, 1, 1, 0, 0, 0)

    # Create the event log
    event_log = EventLog()
    # Give the log a name so RuM is happy
    event_log.attributes["concept:name"] = "csgo_demo_log"

    # Go round by round
    for i, round_data in enumerate(rounds):
        round_idx = i + 1

        trace = Trace()
        # Trace attributes = case attributes in XES
        trace.attributes["round"] = round_idx
        trace.attributes["concept:name"] = f"round_{round_idx}"

        # Give each round its own base start time so timestamps aren't identical
        # e.g. round 1 starts at base_datetime + 0 min
        #      round 2 starts at base_datetime + 10 min
        #      round 3 starts at base_datetime + 20 min
        round_start_dt = base_datetime + timedelta(minutes=10 * i)

        # Go through ticks in order, so events are chronological
        for tick in sorted(round_data.keys()):
            # turn tick index into a timestamp
            # tick / ticks_per_sec = seconds since round start
            timestamp = round_start_dt + timedelta(seconds=tick / float(ticks_per_sec))

            activities = round_data[tick]
            for activity in activities:
                # unpack your tuple/list
                # activity[0] = player name (e.g. "bodyy")
                # activity[1] = field / activity type (e.g. "is_alive")
                # activity[2] = value (e.g. True)
                playername = activity[0]
                field_name = activity[1]      # this becomes concept:name
                field_value = activity[2]

                ev = Event()

                # REQUIRED / standard stuff RuM expects
                ev["concept:name"] = field_value                 # activity label
                ev["lifecycle:transition"] = "complete"         # generic lifecycle
                ev["time:timestamp"] = timestamp                # actual datetime

                # YOUR custom data
                ev["time:tick"] = tick                          # raw game tick
                ev["custom:value"] = field_value                # the value observed

                trace.append(ev)

        event_log.append(trace)

    # Write the log out as proper XES
    pm4py.write_xes(event_log, output_xes_file)

    return event_log
