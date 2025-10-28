from datetime import datetime, timedelta
import pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event
from xml.dom import minidom


def _pretty_format_xes_file(path: str):
    # Read what pm4py wrote
    with open(path, "r", encoding="utf-8") as f:
        raw_xml = f.read()

    # Pretty-print with indentation
    dom = minidom.parseString(raw_xml)
    pretty_xml = dom.toprettyxml(indent="  ")

    # Remove blank lines that minidom sometimes inserts
    pretty_xml_lines = [line for line in pretty_xml.splitlines() if line.strip()]
    pretty_xml = "\n".join(pretty_xml_lines)

    # Force xes.version to "1.0" instead of "2.0" for tool compatibility
    pretty_xml = pretty_xml.replace('xes.version="2.0"', 'xes.version="1.0"')

    # Write back
    with open(path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)


def creatXes(
    rounds,
    ticks_per_sec: int = 64,
    base_datetime: datetime = None,
    output_xes_file: str = "csgo_EventLog.xes",
):
    """
    rounds is a list of rounds.
    Each round is a dict:
        {
          tick_1: [(playername, field_name, value), ...],
          tick_2: [...],
          ...
        }
    """

    if base_datetime is None:
        base_datetime = datetime(2025, 1, 1, 0, 0, 0)

    event_log = EventLog()
    event_log.attributes["concept:name"] = "csgo_demo_log"

    for i, round_data in enumerate(rounds):
        round_idx = i + 1

        trace = Trace()
        trace.attributes["round"] = round_idx
        trace.attributes["concept:name"] = f"round_{round_idx}"

        round_start_dt = base_datetime + timedelta(minutes=10 * i)

        for tick in sorted(round_data.keys()):
            timestamp = round_start_dt + timedelta(seconds=tick / float(ticks_per_sec))

            activities = round_data[tick]
            for activity in activities:
                playername = activity[0]
                field_name = activity[1]      # e.g. "is_alive", "bomb_planted", etc.
                field_value = activity[2]     # True/False/"A"/"CT"/etc.

                ev = Event()
                ev["concept:name"] = field_name
                ev["lifecycle:transition"] = "complete"
                ev["time:timestamp"] = timestamp

                ev["time:tick"] = tick
                ev["user:playername"] = playername
                ev["custom:value"] = str(field_value)  # always string to avoid polars bool issue

                trace.append(ev)

        event_log.append(trace)

    # Write raw XES
    pm4py.write_xes(event_log, output_xes_file)

    # Re-open and pretty format (indent + newlines + xes.version fix)
    _pretty_format_xes_file(output_xes_file)

    return event_log
