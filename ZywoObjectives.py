import os
import pandas as pd
from typing import Dict, List, Any
from demoparser2 import DemoParser
import numpy as np
import matplotlib.pyplot as plt
import pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event


def ensure_plotdata(plotData: dict, dfEventsRound: pd.DataFrame = None, tick_rate: float = 64.0) -> dict:
    """Ensure the plotData dict contains all keys needed by the plotting functions.

    This function will fill missing keys with sensible defaults so callers may
    call the plot functions with only a dictionary.
    """
    if plotData is None:
        plotData = {}

    # sensible defaults
    plotData.setdefault("half_life_seconds", plotData.get("half_life_seconds", 3))

    # Derive first/last ticks from provided DataFrame if available
    if dfEventsRound is not None and not dfEventsRound.empty:
        plotData.setdefault("firstTickInRound", int(dfEventsRound["tick"].min()))
        plotData.setdefault("lastTickInRound", int(dfEventsRound["tick"].max()))
    else:
        plotData.setdefault("firstTickInRound", int(plotData.get("firstTickInRound", plotData.get("first_tick", 0) or 0)))
        plotData.setdefault("lastTickInRound", int(plotData.get("lastTickInRound", plotData.get("last_tick", 0) or 0)))

    # activityOverTime can populate ticks/activities/events
    activity_over_time = plotData.get("activityOverTime", plotData.get("activity_over_time", [])) or []
    if activity_over_time and (not plotData.get("ticks") or not plotData.get("activities_plot") or not plotData.get("events_plot")):
        try:
            ticks_plot, activities_plot, events_plot = zip(*activity_over_time)
            plotData.setdefault("ticks", list(ticks_plot))
            plotData.setdefault("activities_plot", list(activities_plot))
            plotData.setdefault("events_plot", list(events_plot))
        except Exception:
            plotData.setdefault("ticks", [])
            plotData.setdefault("activities_plot", [])
            plotData.setdefault("events_plot", [])
    else:
        plotData.setdefault("ticks", list(plotData.get("ticks", [])))
        plotData.setdefault("activities_plot", list(plotData.get("activities_plot", [])))
        plotData.setdefault("events_plot", list(plotData.get("events_plot", [])))

    plotData.setdefault("peak_tick", plotData.get("peak_tick", None))
    plotData.setdefault("peak_activity", float(plotData.get("peak_activity", 0)))
    plotData.setdefault("upper_threshold", float(plotData.get("upper_threshold", 10)))
    plotData.setdefault("lower_threshold", float(plotData.get("lower_threshold", 0.75 * plotData.get("upper_threshold", 10))))

    # Build activityOverTime if missing
    if not plotData.get("activityOverTime"):
        if plotData.get("ticks") and plotData.get("activities_plot"):
            aet = []
            evs = plotData.get("events_plot") or [None] * len(plotData.get("ticks"))
            for tk, act, ev in zip(plotData["ticks"], plotData["activities_plot"], evs):
                aet.append((int(tk), float(act), ev))
            plotData["activityOverTime"] = aet
        else:
            plotData["activityOverTime"] = []

    return plotData
def plot_activity_with_decay(plotData: dict, tick_rate: float = 64.0, ax=None, show: bool = False, show_legend: bool = True, line_color=None, line_label=None):
    import numpy as np
    import matplotlib.pyplot as plt

    plotData = ensure_plotdata(plotData, tick_rate=tick_rate)

    ticks = np.asarray(plotData.get("ticks", []), dtype=int)
    activity_points = np.asarray(plotData.get("activities_plot", []), dtype=float)
    event_types = np.asarray(plotData.get("events_plot", []), dtype=object)

    first_tick = int(plotData.get("firstTickInRound", 0) or 0)
    last_tick = int(plotData.get("lastTickInRound", 0) or 0)
    half_life_seconds = float(plotData.get("half_life_seconds", 3))
    peak_tick = plotData.get("peak_tick", None)
    peak_activity = plotData.get("peak_activity", None)
    upper_threshold = plotData.get("upper_threshold", None)
    lower_threshold = plotData.get("lower_threshold", None)

    # decay parameter
    lambda_decay = np.log(2) / (half_life_seconds * tick_rate)

    # Construct timeline t and compute decayed activity y
    if last_tick < first_tick:
        last_tick = first_tick
    t = np.arange(first_tick, last_tick + 1)
    total_ticks = len(t)
    y = np.zeros(total_ticks, dtype=float)

    activity = 0.0
    last_event_tick = first_tick

    # If activityOverTime exists we treat the activity values as totals (already decayed)
    activity_over_time = plotData.get("activityOverTime", []) or []
    if activity_over_time:
        # map tick -> total activity (decayed) at that tick
        total_map = {int(tk): float(act) for (tk, act, _) in activity_over_time}
        for i, current_tick in enumerate(t):
            dt = current_tick - last_event_tick
            # decay from previous tick
            activity *= np.exp(-lambda_decay * dt)
            if current_tick in total_map:
                # set activity to the recorded total (not add)
                activity = float(total_map[current_tick])
            y[i] = activity
            last_event_tick = current_tick
    else:
        # fallback: activities_plot are per-event contributions (deltas)
        event_dict = dict(zip(ticks, activity_points)) if len(ticks) else {}
        for i, current_tick in enumerate(t):
            dt = current_tick - last_event_tick
            activity *= np.exp(-lambda_decay * dt)
            if current_tick in event_dict:
                activity += float(event_dict[current_tick])
            y[i] = activity
            last_event_tick = current_tick

    # Convert to seconds for x-axis
    t_seconds = t / tick_rate
    ticks_seconds = ticks / tick_rate if len(ticks) else np.array([])

    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 4))

    line_col = line_color or 'blue'
    line_lbl = line_label or 'Decayed Activity'
    ax.plot(t_seconds, y, color=line_col, label=line_lbl)

    # Scatter events colored by type
    color_map = {
        'weapon_fire': 'red',
        'player_hurt': 'green',
        'player_death': 'black',
        'grenade_thrown': 'orange',
        None: 'gray'
    }

    if len(ticks) > 0:
        unique_events = []
        seen = set()
        for ev in event_types:
            if ev not in seen:
                unique_events.append(ev)
                seen.add(ev)

        plotted_any = False
        for ev in unique_events:
            mask = (event_types == ev)
            if not mask.any():
                continue
            ev_color = color_map.get(ev, 'purple')
            ax.scatter(ticks_seconds[mask], activity_points[mask], color=ev_color, label=str(ev))
            plotted_any = True

        if not plotted_any:
            ax.scatter(ticks_seconds, activity_points, color='red', label='Events')

    # Thresholds
    if upper_threshold is not None:
        ax.axhline(upper_threshold, color='orange', linestyle='--', label=f'Upper Threshold ({upper_threshold})')
    if lower_threshold is not None:
        ax.axhline(lower_threshold, color='purple', linestyle='--', label=f'Lower Threshold ({lower_threshold})')

    # Peak
    if peak_tick is not None and peak_activity is not None:
        peak_tick_seconds = peak_tick / tick_rate
        ax.text(peak_tick_seconds, peak_activity, f'Peak: {peak_activity:.2f}', color='green', fontsize=10, va='bottom')

    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Activity')
    # Optional title info
    rn = plotData.get('round_number') or plotData.get('round')
    zn = plotData.get('zone_name') or plotData.get('zone')
    title = 'Activity Over Time'
    if rn is not None or zn is not None:
        pieces = []
        if rn is not None:
            pieces.append(f'Round {rn}')
        if zn is not None:
            pieces.append(f"Zone: {zn}")
        title += ' | ' + ', '.join(pieces)
    ax.set_title(title)
    ax.grid(True)
    if show_legend:
        ax.legend()
    if show:
        plt.show()
def plot_round_objectives(plottingDataPerRound: List[Any], zones: List[str], tick_rate: float = 64.0, round_number: int = None, save_path: str = None, show_debug: bool = False):
    """Plot all objectives for a round on a single figure.

    plottingDataPerRound: list of tuples (zone, objectives_list, plotData)
    `zones` is the ordered list of zone names to map to grid slots.
    """
    n_slots = 6
    ncols = 3
    nrows = 2
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(18, 8), sharex=True)
    axes = list(axes.flatten())

    def _norm(s):
        return str(s).strip().lower()

    entries_by_zone = {}
    if plottingDataPerRound:
        entries_by_zone = { _norm(zone): (objectives, plotData, zone) for (zone, objectives, plotData) in plottingDataPerRound }

    for slot_idx in range(n_slots):
        if slot_idx < len(zones):
            zone = zones[slot_idx]
        else:
            zone = f"Slot {slot_idx+1}"

        ax = axes[slot_idx]
        key = _norm(zone)

        if key in entries_by_zone:
            objectives, plotData, original_zone = entries_by_zone[key]
            if show_debug:
                print(f"Slot {slot_idx} -> zone '{zone}' matched entry '{original_zone}'")

            # ensure plotData has everything
            plotData = ensure_plotdata(plotData)

            # include round and zone for titles
            pd_copy = dict(plotData)
            pd_copy.setdefault('round_number', round_number)
            pd_copy.setdefault('zone_name', zone)

            plot_activity_with_decay(pd_copy, tick_rate=tick_rate, ax=ax, show=False, show_legend=False)
            ax.set_title(f"Zone: {zone}")
        else:
            ax.set_title(f"Zone: {zone}")
            ax.set_xticks([])
            ax.set_yticks([])

    # Collect legend entries from all axes and create a single figure-level legend
    handles = []
    labels = []
    for ax in axes:
        h, l = ax.get_legend_handles_labels()
        for hh, ll in zip(h, l):
            if ll not in labels:
                handles.append(hh)
                labels.append(ll)

    if labels:
        fig.legend(handles, labels, loc='upper center', ncol=min(8, len(labels)), bbox_to_anchor=(0.5, 0.99))

    title = f"Round {round_number} Objectives" if round_number is not None else "Round Objectives"
    fig.suptitle(title)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    if save_path:
        plt.savefig(save_path)
        plt.close(fig)
        print(f"Saved round plot to {save_path}")
    else:
        plt.show()
def getRoundWinnerDict(parser:DemoParser) -> Dict[int, str]:
    df = parser.parse_event("round_freeze_end", other=["team_rounds_total", "total_rounds_played"])
    winners: Dict[int, str] = {}
    tWinLastRound = 0
    for _, row in df.iterrows():
        round_num = int(row["total_rounds_played"])
        tWinThisRound = row["t_team_rounds_total"]
        isCTwin = tWinLastRound == tWinThisRound
        if isCTwin:
            winners[round_num] = 0 #CT WIN
        else:
            winners[round_num] = 1 #TERROIST WIN
            tWinLastRound = tWinThisRound
    return winners
class WorkflowLog:
    def __init__(self):

        #Misc
        self.folder_path = r"C:\Users\felim\Desktop\School\PM\matches"
        try:
            self.matches = os.listdir(self.folder_path)
        except Exception:
            raise KeyError("change self.folder_path variable, to match matches folder")
        self.parser = None
        self.caseID = 0 #increments for each trace
        self.TICK_RATE = 64.0 #server tick rate
        self.PLOTTING = False
        self.matchNumber = 0
        self.roundNumber = 0

        #Events & Activity points
        self.GAME_EVENTS = ['grenade_thrown', 'weapon_fire', 'player_hurt', 'player_death']
        self.activityPoints = {
                    "grenade_thrown": 3,
                    "weapon_fire": 1,
                    "player_hurt": (1,10), #at least 1, at most 10, scaling with damage
                    "player_death": 5
                }
        
       
        

        #Objective mapping
        self.zones = ['BombsiteA', 'Catwalk', 'BombsiteBZone', 'Middle', 'Side', 'Tunnels']
        self.ZONE_MAP: Dict[str, str] = {
            "BombsiteA": "BombsiteA", 
            "ARamp": "BombsiteA", 
            "UnderA": "BombsiteA", 
            
            "CTSpawn": "BombsiteA",
            "ShortStairs": "Catwalk", 
            "Catwalk": "Catwalk",

            "BombsiteB": "BombsiteB", 
            "BDoors": "BombsiteB",

            "Bucket": "Middle", 
            "OutsideTunnel": "Middle", 
            "Middle": "Middle", 
            "MidDoors": "Middle", 
            "TopofMid": "Middle",

            "ExtendedA": "Side", 
            "LongA": "Side", 
            "LongDoors": "Side", 
            "OutsideLong": "Side", 
            "Pit": "Side", 
            "Side": "Side",

            "TunnelStairs": "Tunnels", 
            "UpperTunnel": "Tunnels", 
            "LowerTunnel": "Tunnels"
        }
        
        #Objective analysis - consider changing the exponential decay to something else that fits better
        self.HALF_LIFE_ACTIVTIY_POINTS = 3 #Im assuming 8 seconds skirmishes... is that right?
        self.UPPER_THRESHHOLD = 10 
        self.LOWERTHRESHHOLD = 0.75 * self.UPPER_THRESHHOLD
        self.WINDOW = self.TICK_RATE

        #Objective winner tuning
        self.POINT_FOR_KILL = 50
        self.DAMAGE_PER_POINT_RATIO = 1
        self.EVEN_COEFFICENT = 1.3 #if points is even by 30%, then 
        
        #Filters & stuff
        self.DELAY_WEAPON_FIRE_RECORDING_SPRAY = 1 #1 sec between recording of fires events, to avoid spraying giving a lot of activtiy points
        self.WEAPON_FIRE_FILTER = ["knife", "flashbang", "hegrenade", "smokegrenade", "decoy", "molotov", "incendiary"]

        self.FILTER_FRACTION_EVENTS_AFTER_MAPPING_PER_ROUND = 0.90 #If filtered events are more than 10%, dont consider this level #TODO add this as trace attribute
        self.CASH_FILTER = 1.30 #If the difference between teams cash is more than 30% in that round, dont consider it #TODO add this as trace attribute

        #Round data
        self.totalRounds = 0
        
        self.DIFF_GOLD = "DIFF_IN_GOLD"
        self.ROUND = "ROUND"
        self.FAIRNESS = "FAIRNESS"
        self.allCashDataPerRound = []
        self.roundSkipDueToCash = 0

        self.DIFF_ACTIVITY_POINTS = "DIFF_ACTIVITY_POINTS"
        self.ROUND = "ROUND"
        self.FRACTION_ACTIVITY_POINTS_BEFORE_AFTER = "FRACTION_ACTIVITY_POINTS_BEFORE_AFTER"
        self.allFilterDataPerRound = []
        self.roundSkipDueToEventsFiltered = 0

        #Match data
        self.DIFF_AFTER_SPRAY_FILTER = "DIFF_AFTER_SPRAY_FILTER"
        self.BEFORE_SPRAY_FILTER = "BEFORE_SPRAY_FILTER"
        self.AFTER_SPRAY_FILTER = "AFTER_SPRAY_FILTER"
        self.MATCH_NUMBER = "MATCH"
        self.allMatchSprayFilterData = []
    def plotAllCashData(self):
        if not hasattr(self, "allCashDataPerRound") or not self.allCashDataPerRound:
            print("No cash data to plot.")
            return

        # Extract diff gold values
        diff_gold = [entry[self.DIFF_GOLD] for entry in self.allCashDataPerRound]
        n_entries = len(diff_gold)

        # Compute quantiles
        q25, q50, q75 = np.percentile(diff_gold, [25, 50, 75])

        # Plot diff gold over rounds
        plt.figure(figsize=(12, 5))
        plt.plot(range(1, n_entries + 1), diff_gold, marker='o', linestyle='-', color='blue', alpha=0.7)
        plt.xlabel("Round entry")
        plt.ylabel("Cash Difference (gold)")
        plt.title("Cash Differences per Round")

        # Show quantile lines
        plt.axhline(q25, color='green', linestyle='--', label=f"25th percentile: {q25:.0f}")
        plt.axhline(q50, color='orange', linestyle='--', label=f"50th percentile (median): {q50:.0f}")
        plt.axhline(q75, color='red', linestyle='--', label=f"75th percentile: {q75:.0f}")

        plt.legend()
        plt.grid(True)
        plt.show()
    def getRoundCashSpentEvenDict(self, parser: DemoParser) -> Dict[int, bool]:
    
        roundCashSpentEvenDict = {}
        df = parser.parse_event("round_freeze_end")
        ticks = list(df["tick"])
        dfticks = parser.parse_ticks(["team_name", "player_name", "cash_spent_this_round"], ticks = ticks)
        for roundNum, tick in enumerate(ticks):
            tick_rows = dfticks[dfticks["tick"] == tick]      # rows for this tick
            ctRows = tick_rows[tick_rows["team_name"] == "CT"]
            tRows = tick_rows[tick_rows["team_name"] == "TERRORIST"]
            
            ctCash = ctRows["cash_spent_this_round"].sum()
            tCash = tRows["cash_spent_this_round"].sum()

            diff = abs(ctCash - tCash)

            fairness = ""
            if diff <= 3600:
                fairness = 3 
            elif diff <= 7800:
                fairness = 2
            elif diff <= 10000:
                fairness = 1
            else: 
                fairness = 0

            roundCashSpentEvenDict[roundNum] = (fairness, diff)

            roundCashData = {
                self.DIFF_GOLD: diff,
                self.ROUND: roundNum,
                self.FAIRNESS: fairness
            }
            self.allCashDataPerRound.append(roundCashData)

        return roundCashSpentEvenDict
    def initParser(self, match_file: str):
        full_path = os.path.join(self.folder_path, match_file)
        self.parser = DemoParser(full_path)
    def mapPlacesToZones(self, df: pd.DataFrame) -> pd.DataFrame:
        roundEvents = df.copy()
        placeKeys = [
            'last_place_name', 'user_last_place_name',
            'attacker_last_place_name', 'victim_last_place_name',
            'place', 'position'
        ]

        validKeys = [k for k in placeKeys if k in roundEvents.columns]

        best_key = None
        best_activity_sum = -1
    
        for key in validKeys:
            mapped = roundEvents[key].map(self.ZONE_MAP)  # Map places to zones
            # Only consider rows that successfully map to a zone
            mask_valid = mapped.notna()
            activity_sum = roundEvents.loc[mask_valid, "activityPoints"].sum()

            if activity_sum > best_activity_sum:
                best_activity_sum = activity_sum
                best_key = key

       
        # Assign zones using the key that maximizes total activityPoints
        roundEvents["zone"] = roundEvents[best_key].map(self.ZONE_MAP).fillna("NO_ZONE")
        roundEvents = roundEvents[roundEvents["zone"] != "NO_ZONE"]

        return roundEvents
    def prepareEvents(self, matchNumber) -> pd.DataFrame:
       
        all_events = []
        gameEvents = self.GAME_EVENTS

        for gameEvent in gameEvents:
            #check if event exist
            list1 = self.parser.list_game_events()
            if gameEvent not in list1:
                return gameEvent
            
            dfEvents = self.parser.parse_event(gameEvent, player=["team_name",'last_place_name',"total_rounds_played","health","armor"], other=["team_score_overtime"])
            dfEvents["event"] = gameEvent #add its event type in columns

            if gameEvent == "weapon_fire":
                # Remove unimportant weapons
                remove_weapons = self.WEAPON_FIRE_FILTER
                pattern = "|".join(remove_weapons)
                dfEvents = dfEvents[~dfEvents["weapon"].str.lower().str.contains(pattern, regex=True, na=False)]
                dfEvents = dfEvents.sort_values("tick").reset_index(drop=True)

                # Count sprays as single shot 
                tick_threshold = int(self.TICK_RATE * self.DELAY_WEAPON_FIRE_RECORDING_SPRAY)

                eventsBeforeSprayFilter = len(dfEvents) #data

                from collections import deque
                last_ticks_dict = {}
                keep_indices = []
                for idx, row in dfEvents.iterrows():
                    key = (row["user_name"], row["weapon"].lower())
                    tick = row["tick"]

                    if key not in last_ticks_dict:
                        last_ticks_dict[key] = deque(maxlen=1)  # only store last shot

                    # Keep shot only if cooldown has passed since last one
                    if not last_ticks_dict[key] or tick - last_ticks_dict[key][-1] > tick_threshold:
                        keep_indices.append(idx)
                        last_ticks_dict[key].append(tick)
        
                
                dfEvents = dfEvents.iloc[keep_indices].reset_index(drop=True)
                dfEvents["activityPoints"] = self.activityPoints[gameEvent]

                #data
                eventsAfterSprayFilter = len(dfEvents)
                sprayFilterData = {
                    self.DIFF_AFTER_SPRAY_FILTER: eventsBeforeSprayFilter - eventsAfterSprayFilter,
                    self.BEFORE_SPRAY_FILTER: eventsBeforeSprayFilter,
                    self.AFTER_SPRAY_FILTER: eventsAfterSprayFilter,
                    self.MATCH_NUMBER: matchNumber

                }
                self.allMatchSprayFilterData.append(sprayFilterData)       
            elif gameEvent == "player_hurt":
                dfEvents = dfEvents[dfEvents["dmg_health"] > 0]
                dfEvents["damage_capped"] = dfEvents["dmg_health"].clip(upper=100)
                damage = np.minimum(dfEvents["damage_capped"], dfEvents["user_health"])

                minPoints  = self.activityPoints[gameEvent][0]
                maxPoints  = self.activityPoints[gameEvent][1]

                dfEvents["activityPoints"] = np.clip(maxPoints * (damage / 100), a_min=minPoints, a_max=None)
                dfEvents["activityPoints"] = dfEvents["activityPoints"].round(2)
            elif gameEvent == "player_death":
                dfEvents["activityPoints"] = self.activityPoints[gameEvent]
            elif gameEvent == "grenade_thrown":
                dfEvents["activityPoints"] = self.activityPoints[gameEvent]
            else:
                raise ValueError("Implement gameEvent")
            
            all_events.append(dfEvents)

        allEventsDict = pd.concat(all_events)
        return allEventsDict
    def findHighActivitySegmentsInZone(self, zone:str, roundEvents:pd.DataFrame):
        roundEvents = roundEvents.copy()

        df_zone = roundEvents[roundEvents["zone"] == zone].copy()
        if df_zone.empty:
            return []

        # preserve original ordering as tiebreaker for events with same tick
        df_zone = df_zone.reset_index().rename(columns={"index": "orig_index"})
        df_zone = df_zone.sort_values(["tick", "orig_index"]).reset_index(drop=True)

        # decay per tick (use configured tick rate)
        lambda_decay = np.log(2) / (self.HALF_LIFE_ACTIVTIY_POINTS * self.TICK_RATE)
        activityPoints = 0.0
        previousTick = int(df_zone["tick"].iloc[0])
        activity_over_time = []
        high_activity_segments = []
        high_activity_index_sets = []  # parallel list of df_zone index sets for each saved segment
        current_segment_rows = []
        upper_threshold = getattr(self, "UPPER_THRESHHOLD", 10)
        lower_threshold = getattr(self, "LOWERTHRESHHOLD", 0.75 * upper_threshold)
        recording = False
        peakActivity = 0.0
        peak_tick = previousTick

        included_indices = set()  # indices included in the current building segment

        for idx, row in df_zone.iterrows():
            current_tick = int(row["tick"])
            dt = current_tick - previousTick
            activityPoints *= np.exp(-lambda_decay * dt)
            activityPoints += float(row.get("activityPoints", 0.0))

            if activityPoints > peakActivity:
                peakActivity = activityPoints
                peak_tick = current_tick
            previousTick = current_tick

            if not recording:
                if activityPoints >= upper_threshold:
                    # start a new segment
                    recording = True
                    current_segment_rows = []
                    included_indices = set()

                    # include this row
                    current_segment_rows.append(row.to_dict())
                    included_indices.add(idx)

                    # backward-expand: include events in successive 1s windows until none found
                    search_index = idx
                    spike_tick = current_tick
                    window_start = spike_tick - int(self.WINDOW)

                    merged_into_prev = False
                    while True:
                        # include events on same tick and earlier ones (index < search_index)
                        prev_mask = (df_zone["tick"] >= window_start) & (df_zone["tick"] <= spike_tick)
                        prev_rows = df_zone[prev_mask & (df_zone.index < search_index)]
                        # exclude already-included indices
                        prev_rows = prev_rows[~prev_rows.index.isin(included_indices)]
                        if prev_rows.empty:
                            break

                        # if any of prev_rows indices overlap an already-saved segment, merge and stop
                        prev_row_indices = set(prev_rows.index.tolist())
                        overlapping_seg_idx = None
                        for s_i, s_idx_set in enumerate(high_activity_index_sets):
                            if prev_row_indices & s_idx_set:
                                overlapping_seg_idx = s_i
                                break

                        if overlapping_seg_idx is not None:
                            # merge current included indices + prev_row_indices into the existing saved segment
                            union_idxs = s_idx_set.union(prev_row_indices).union(included_indices)
                            merged_df = df_zone.loc[sorted(union_idxs)].sort_values(["tick", "orig_index"]).reset_index(drop=True)
                            high_activity_segments[overlapping_seg_idx] = merged_df
                            high_activity_index_sets[overlapping_seg_idx] = set(df_zone.loc[merged_df.index].index.tolist()) if not merged_df.empty else set()
                            merged_into_prev = True
                            break

                        # prepend prev_rows in chronological order
                        prev_list = [prow.to_dict() for _, prow in prev_rows.sort_values(["tick", "orig_index"]).iterrows()]
                        current_segment_rows = prev_list + current_segment_rows
                        included_indices.update(prev_rows.index.tolist())

                        # move search window to earliest included event
                        search_index = int(prev_rows.index.min())
                        spike_tick = int(prev_rows["tick"].min())
                        window_start = spike_tick - int(self.WINDOW)

                    # if we merged into a previous segment, stop recording this new one
                    if merged_into_prev:
                        recording = False
                        current_segment_rows = []
                        included_indices = set()
            else:
                if activityPoints >= lower_threshold:
                    # continue recording
                    if idx not in included_indices:
                        current_segment_rows.append(row.to_dict())
                        included_indices.add(idx)
                else:
                    # finish segment
                    if current_segment_rows:
                        high_activity_segments.append(pd.DataFrame(current_segment_rows))
                        # store the set of df_zone indices for this segment for future overlap checks
                        high_activity_index_sets.append(set(included_indices))
                    current_segment_rows = []
                    recording = False
                    included_indices = set()

            activity_over_time.append((current_tick, activityPoints, row.get("event")))

        # flush if still recording
        if recording and current_segment_rows:
            high_activity_segments.append(pd.DataFrame(current_segment_rows))
            high_activity_index_sets.append(set(included_indices))

        # build plottingData (kept for compatibility)
        if activity_over_time:
            ticks_plot, activities_plot, events_plot = zip(*activity_over_time)
        else:
            ticks_plot, activities_plot, events_plot = (), (), ()

        plottingData = {
            "half_life_seconds": self.HALF_LIFE_ACTIVTIY_POINTS,
            "firstTickInRound": int(roundEvents["tick"].min()),
            "lastTickInRound": int(roundEvents["tick"].max()),
            "activityOverTime": activity_over_time,
            "ticks": ticks_plot,
            "activities_plot": activities_plot,
            "events_plot": events_plot,
            "peak_tick": peak_tick,
            "peak_activity": peakActivity,
            "upper_threshold": upper_threshold,
            "lower_threshold": lower_threshold
        }

        if self.PLOTTING:
            pd_copy = ensure_plotdata(plottingData, roundEvents)
            pd_copy.setdefault("round_number", getattr(self, "roundNumber", None))
            pd_copy.setdefault("zone_name", zone)
            plot_activity_with_decay(pd_copy, tick_rate=self.TICK_RATE, show_legend=True)

        return high_activity_segments
    def determineActivties(self, objective: pd.DataFrame):
        df = objective.copy()
        
        zone = df["zone"].iloc[0]
        kills = df[df["event"] == "player_death"]
        ctKills = tKills = 0.0
        for _, row in kills.iterrows():
            if row["attacker_team_name"] == "TERRORIST":
                tKills += 1
            else:
                ctKills += 1
        

        ctDamage = tDamage = 0.0
        damagedf = df[df["event"] == "player_hurt"]
        for _, row in damagedf.iterrows():
            damage = np.minimum(row["damage_capped"], row["user_health"]) * self.DAMAGE_PER_POINT_RATIO
            if row["attacker_team_name"] == "TERRORIST":
                tDamage += damage
            else:
                ctDamage += damage 
        
        ctPoints = ctKills * self.POINT_FOR_KILL + (ctDamage) 
        tPoints = tKills * self.POINT_FOR_KILL + (tDamage)
        isEven = max(ctPoints, tPoints) < self.EVEN_COEFFICENT * min(ctPoints, tPoints)
        ctWin = ctPoints > tPoints
        if isEven:
            activity = f"Even_{zone}"
        elif ctWin:
            activity = f"CT_{zone}"
        else:
            activity = f"T_{zone}"

        firstTick = min(df["tick"])
        lastTick = max(df["tick"])
        totalKills = tKills + ctKills
        totalDamage = ctDamage + tDamage
        return {
            "activtiy": activity,
            "ctPoints": ctPoints,
            "tPoints": tPoints,
            "totalKills": totalKills,
            "totalDamage": totalDamage,
            "seconds": round((lastTick - firstTick) / self.TICK_RATE, 2),
        }
    
    def _createLog(self, traces):
        log = {}
        for (roundNum, trace, roundWinnerDict, roundCashSpentEvenDict) in traces:
            fairness, diff = roundCashSpentEvenDict[roundNum]
            trace_dict = {
                    "match": self.matchNumber,
                    "trace": trace,
                    "cashFairness": fairness,
                    "cashDiff": diff,
                    "mapEventAccuracy": round((self.allFilterDataPerRound[roundNum]["FRACTION_ACTIVITY_POINTS_BEFORE_AFTER"]), 2),
                    "winner": roundWinnerDict[roundNum],
                    "isPistolRound": 1 if roundNum == 0 or roundNum == 12 else 0
                }
            log[self.caseID] = trace_dict
            self.caseID += 1
        return log
    

    def createLog(self):
        traces = []
        
        for matchNumber, match_file in enumerate(self.matches):
            print(match_file)
            self.matchNumber = matchNumber
            self.initParser(match_file)
            allEvents = self.prepareEvents(matchNumber)
            if isinstance(allEvents, str): #some event were missing
                print(f"{allEvents} event were missing in {match_file}")
                continue
            
            #matchwise
            roundCashSpentEvenDict = self.getRoundCashSpentEvenDict(self.parser)
            roundWinnerDict = getRoundWinnerDict(self.parser)

            for round in range(len(roundWinnerDict)):
                self.roundNumber = round
                self.totalRounds +=1 #data

                #is mapping good enough
                roundEvents = allEvents[allEvents["total_rounds_played"] == round]
                before = roundEvents["activityPoints"].sum()
                roundEvents = self.mapPlacesToZones(roundEvents)
                after = roundEvents["activityPoints"].sum()
                fractionBeforeAfter = after/before 
                filterData = { #data
                    self.DIFF_ACTIVITY_POINTS: abs(before-after),
                    self.FRACTION_ACTIVITY_POINTS_BEFORE_AFTER: fractionBeforeAfter,
                    self.ROUND: round
                }
                self.allFilterDataPerRound.append(filterData) #data

                trace = []
                for zone in self.zones:
                    

                    if self.matchNumber == 0 and self.roundNumber == 3 and zone == "Side":
                        pass
                    objectives = self.findHighActivitySegmentsInZone(zone, roundEvents)
                    
                    for objective in objectives:
                        activity_dict = self.determineActivties(objective)
                        if activity_dict:
                            trace.append(activity_dict)
                traces.append((round, trace, roundWinnerDict, roundCashSpentEvenDict))
        return self._createLog(traces)
    
def convert_to_event_log(log_dict):
    event_log = EventLog()

    for case_id, case_data in log_dict.items():
        trace = Trace()
        trace.attributes["concept:name"] = f"Round_{case_id}"
        
        for attribute, value in case_data.items():
                if attribute != "trace":
                    trace.attributes[attribute] = value

        for activity in case_data["trace"]:
            event = Event()
            event["concept:name"] = activity["activtiy"]
            for attribute, value in activity.items():
                if attribute != "activity":
                    event[attribute] = value
            trace.append(event)
        event_log.append(trace)
    return event_log


def write_txt_log(log_dict, path):
    import json
    with open(path, "w", encoding="utf-8") as f:
        for case_id, case_data in log_dict.items():
            f.write(f"Case {case_id}: \n")
            for attribute, value in case_data.items():
                    if attribute != "trace":
                        f.write(f"{attribute}: {value}\n")
            for event in case_data.get("trace", []):
                try:
                    f.write("  - " + json.dumps(event, default=str) + "\n")
                except Exception:
                    f.write("  - " + str(event) + "\n")
            f.write("\n")

if __name__ == '__main__':
    workflowlog = WorkflowLog()
    log = workflowlog.createLog()
    #workflowlog.plotAllCashData()
    # Convert to pm4py EventLog
    event_log = convert_to_event_log(log)
    pm4py.write_xes(event_log, "Log.xes")
    write_txt_log(log, "Log.txt")