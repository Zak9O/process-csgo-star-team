from datetime import datetime, timedelta
import pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event
from collections import defaultdict


def creatXes(
    rounds,
    ticks_per_sec: int = 64,
    # base_datetime: datetime = None,
    output_xes_file: str = "csgo_EventLog.xes",
):

    # Overall event log
    event_log = EventLog()
    event_log.attributes["concept:name"] = "csgo_demo_log"

    player_events = defaultdict(list)

    # Walk rounds like before, but instead of immediately appending to a Trace,
    # buffer them per player.
    for i, round_data in enumerate(rounds):
        round_idx = i + 1
        # Go through ticks in chronological order
        for tick in sorted(round_data.keys()):

            activities = round_data[tick]
            for activity in activities:
                playername, field_name, field_value = activity

                player_events[playername].append(
                    (round_idx, tick, field_name, field_value)
                )

    # Now build one Trace per player from player_events
    for playername, ev_list in player_events.items():
        ev_list_sorted = sorted(ev_list, key=lambda x: x[0])

        trace = Trace()

        # Trace (case) attributes
        trace.attributes["player"] = playername
        trace.attributes["concept:name"] = playername  # what RuM will show as case id

        # Add each recorded event for this player
        for (round_idx, tick, field_name, field_value) in ev_list_sorted:
            ev = Event()

            # Standard / required attributes
            # concept:name = the "activity label"
            # Here we keep your previous choice: use the observed value as the activity label.
            # Example: last_place_name == "LongA" becomes an activity named "LongA".
            ev["concept:name"] = field_value
            ev["concept:playername"] = playername

            # Extra context you might want during analysis
            ev["time:tick"] = tick          # raw demo tick
            ev["round"] = round_idx         # which round this happened in

            # If you also care about which "field" changed (e.g. last_place_name),
            # keep it as an attribute:
            ev["activity:type"] = field_name

            trace.append(ev)

        event_log.append(trace)

    # Finally, write the XES log to disk
    pm4py.write_xes(event_log, output_xes_file)

    return event_log
