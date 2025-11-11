import pm4py
from demoparser2.demoparser2 import DemoParser
from pandas import DataFrame
from pm4py.objects.log.obj import EventLog, Trace, Event

def dfToEventLog(
        data: DataFrame,
        trace_identifier: str,
        time_identifier: str,
        activityList: list[str]) -> dict:
    log_dict = {}
    identifiers = data[trace_identifier].unique()
    for identifier in identifiers:
        trace_data = data[data[trace_identifier] == identifier]
        # build merged activity dict per tick (unsorted)
        temp_tick_map: dict = {}
        for _, row in trace_data.iterrows():
            tick = row[time_identifier]
            for activity in activityList:
                activity_value = row[activity]
                if activity_value == "":
                    continue
                if tick not in temp_tick_map:
                    temp_tick_map[tick] = {activity: activity_value}
                else:
                    temp_tick_map[tick][activity] = activity_value
        # iterate ticks in order and only add if different from last added
        trace_dict: dict = {}
        last_added: dict | None = None
        for tick in sorted(temp_tick_map):
            curr = temp_tick_map[tick]
            if last_added is None or curr != last_added:
                trace_dict[tick] = curr
                last_added = curr
        key = identifier if trace_identifier == "name" else f"{trace_identifier}_{identifier}"
        log_dict[key] = trace_dict  # already ordered by tick keys
    return log_dict


def createXesFileFromEventLog(event_log: dict, file_path: str) -> bool:
    pm4py_event_log = EventLog()
    pm4py_event_log.attributes["concept:name"] = "csgo_demo_log"
    for trace_id in event_log:
        trace = Trace()
        trace.attributes["concept:name"] = trace_id
        for tick in event_log[trace_id]:
            activities = event_log[trace_id][tick]
            for activity_name in activities:
                activity_value = activities[activity_name]
                event = Event()
                event['concept:name'] = activity_value
                event['concept:activity'] = activity_name
                event['time:tick'] = tick
                trace.append(event)
        pm4py_event_log.append(trace)
    pm4py.write_xes(pm4py_event_log, file_path)
    return True