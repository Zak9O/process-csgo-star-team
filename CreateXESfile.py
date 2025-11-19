import pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event

def CreateXES(rounds, output_xes_file: str = "csgo_EventLog.xes"):
    event_log = EventLog()
    event_log.attributes["concept:name"] = "csgo_demo_log"

    for i, round_data in enumerate(rounds):
        trace = Trace()
        trace.attributes["concept:name"] = f"round_{i + 1}"

        for tick in sorted(round_data.keys()):
            for activity in round_data[tick]:
                # support both 3-tuple and 4-tuple activity items
                if len(activity) == 3:
                    playername, field_name, field_value = activity
                    extra = None
                elif len(activity) == 4:
                    playername, field_name, field_value, extra = activity
                else:
                    # unexpected shape; try a graceful fallback
                    playername = activity[0] if len(activity) > 0 else None
                    field_name = activity[1] if len(activity) > 1 else "unknown"
                    field_value = activity[2] if len(activity) > 2 else str(activity)
                    extra = activity[3] if len(activity) > 3 else None

                ev = Event()
                ev["concept:name"] = field_value
                ev["tick"] = tick

                # handle extra metadata
                if extra is not None:
                    if isinstance(extra, dict):
                        for k, v in extra.items():
                            key = f"{k}"
                            try:
                                ev[key] = str(v)
                            except Exception:
                                ev[key] = str(v)
                    else:
                        # field-specific key selection
                        if field_name in ("weapon_damage", "utility_damage"):
                            try:
                                ev["damage_taken"] = str(extra)
                            except Exception:
                                ev["damage_taken"] = extra
                        elif field_name == "round_end":
                            # round_end keeps winner_spent
                            try:
                                ev["winner_spent"] = str(extra)
                            except Exception:
                                ev["winner_spent"] = extra
                        else:
                            # generic fallback
                            try:
                                ev["extra"] = str(extra)
                            except Exception:
                                ev["extra"] = extra

                trace.append(ev)

        event_log.append(trace)

    pm4py.write_xes(event_log, output_xes_file)
    return event_log
