import os
from demoparser2 import DemoParser
import pandas as pd
from typing import Dict, List, Any
import os
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from demoparser2 import DemoParser
import numpy as np
import matplotlib.pyplot as plt


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
    """Plot activity using the provided plotData dictionary.

    plotData will be filled with defaults by `ensure_plotdata` if keys are missing.
    """
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
        if round_num == 0:
            continue
        tWinThisRound = row["t_team_rounds_total"]
        isCTwin = tWinLastRound == tWinThisRound
        if isCTwin:
            winners[round_num] = "CT_win"
        else:
            winners[round_num] = "TERRORIST_win"
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


        #Values
        self.case = 0 #increments for each trace
        self.TICK_RATE = 64.0 #server tick rate


        #Events & Activity points
        self.GAME_EVENTS = ['grenade_thrown', 'weapon_fire', 'player_hurt', 'player_death']
        self.activityPoints = {
                    "grenade_thrown": 3,
                    "weapon_fire": 1,
                    "player_hurt": (1,10), #at least 1, at most 10, scaling with damage
                    "player_death": 5
                }
        
        #plt
        self.PLOTTING = False
        
        #Objectives mapping
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
        
        #Objective analysis #TODO consider changing the exponential decay to something else that fits better
        self.HALF_LIFE_ACTIVTIY_POINTS = 3 #Im assuming 8 seconds skirmishes.
        self.UPPER_THRESHHOLD = 10 
        self.LOWERTHRESHHOLD = 0.75 * self.UPPER_THRESHHOLD

        #Filters & stuff
        self.DELAY_WEAPON_FIRE_RECORDING = 1 #1 sec between recording of fires events, to avoid spraying giving a lot of activtiy points
        self.FILTER_FRACTION_EVENTS_AFTER_MAPPING = 0.90 #If filtered events are more than 10%, dont consider this level
        self.CASH_FILTER = 1.30 #If the difference between teams cash is more than 30%, dont consider this level
        self.WEAPON_FIRE_FILTER = ["knife", "flashbang", "hegrenade", "smokegrenade", "decoy", "molotov", "incendiary"]

        #Round data
        self.totalRounds = 0
        
        self.DIFF_GOLD = "DIFF_IN_GOLD"
        self.ROUND = "ROUND"
        self.allCashDataPerRound = []
        self.roundSkipDueToCash = 0

        self.DIFF_ACTIVITY_POINTS = "DIFF_ACTIVITY_POINTS"
        self.ROUND = "ROUND"
        self.FILTERED = "FILTERED"
        self.allFilterDataPerRound = []
        self.roundSkipDueToEventsFiltered = 0

        #Match data
        self.DIFF_AFTER_SPRAY_FILTER = "DIFF_AFTER_SPRAY_FILTER"
        self.BEFORE_SPRAY_FILTER = "BEFORE_SPRAY_FILTER"
        self.AFTER_SPRAY_FILTER = "AFTER_SPRAY_FILTER"
        self.MATCH_NUMBER = "MATCH"
        self.allMatchSprayFilterData = []


    def getRoundCashSpentEvenDict(self, parser: DemoParser) -> Dict[int, bool]:
    
        roundCashSpentEvenDict = {}
        df = parser.parse_event("round_freeze_end")
        ticks = list(df["tick"])
        dfticks = parser.parse_ticks(["team_name", "player_name", "cash_spent_this_round"], ticks = ticks)
        for roundNum, tick in enumerate(ticks):
            if roundNum == 0:
                continue
            tick_rows = dfticks[dfticks["tick"] == tick]      # rows for this tick
            ctRows = tick_rows[tick_rows["team_name"] == "CT"]
            tRows = tick_rows[tick_rows["team_name"] == "TERRORIST"]
            
            ctCash = ctRows["cash_spent_this_round"].sum()
            tCash = tRows["cash_spent_this_round"].sum()

            if ctCash == 0 or tCash == 0:
                isCashEven = False
            else:
                isCashEven = max(ctCash, tCash) < self.CASH_FILTER * min(ctCash, tCash)

            roundCashData = {
                self.DIFF_GOLD: abs(ctCash-tCash),
                self.ROUND: roundNum
            }
            self.allCashDataPerRound.append(roundCashData)
            roundCashSpentEvenDict[roundNum] = isCashEven


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
                tick_threshold = int(self.TICK_RATE * self.DELAY_WEAPON_FIRE_RECORDING)

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

    def findHighActivitySegmentsInZone(self, zone:str, dfEventsRound:pd.DataFrame):
        dfEventsRound = dfEventsRound.copy()

        df_zone = dfEventsRound[dfEventsRound["zone"] == zone].sort_values("tick")
        lambda_decay = np.log(2)/(self.HALF_LIFE_ACTIVTIY_POINTS *64)
        activtiyPoints = 0
        last_tick = dfEventsRound["tick"].min()
        activity_over_time = []
        high_activity_segments = []
        current_segment_rows = []
        upper_threshold = 10
        lower_threshold = 0.75 * upper_threshold
        recording = False
        peakActivity = 0
        peak_tick = last_tick

        for _, row in df_zone.iterrows():
            current_tick = row["tick"]
            dt = current_tick - last_tick
            activtiyPoints *= np.exp(-lambda_decay * dt)
            activtiyPoints += row["activityPoints"]

            if activtiyPoints > peakActivity:
                peakActivity = activtiyPoints
                peak_tick = current_tick
            last_tick = current_tick

            if not recording:
                if activtiyPoints >= upper_threshold:
                    recording = True
                    current_segment_rows = [row.to_dict()]
            else:
                if activtiyPoints >= lower_threshold:
                    current_segment_rows.append(row.to_dict())
                else:
                    high_activity_segments.append(pd.DataFrame(current_segment_rows))
                    current_segment_rows = []
                    recording = False

            activity_over_time.append((current_tick, activtiyPoints, row["event"])) #plotting 

        if recording and current_segment_rows:
            high_activity_segments.append(pd.DataFrame(current_segment_rows))

        if activity_over_time:
            ticks_plot, activities_plot, events_plot = zip(*activity_over_time)
        else:
            ticks_plot, activities_plot, events_plot = (), (), ()

        plottingData = {
            "half_life_seconds": self.HALF_LIFE_ACTIVTIY_POINTS,
            "firstTickInRound": dfEventsRound["tick"].min(),
            "lastTickInRound": dfEventsRound["tick"].max(),
            "activityOverTime": activity_over_time,
            "ticks": ticks_plot,
            "activities_plot": activities_plot,
            "events_plot": events_plot,
            "peak_tick": peak_tick,
            "peak_activity": peakActivity,
            "upper_threshold": upper_threshold,
            "lower_threshold": lower_threshold
        }

        return high_activity_segments, plottingData

    def determineActivties(self, objective: pd.DataFrame):
        df = objective.copy()
        zone = df["zone"].iloc[0]
        ctPoints = tPoints = 0.0

        kills = df[df["event"] == "player_death"]
        ctKills = tKills = 0.0
        for _, row in kills.iterrows():
            if row["attacker_team_name"] == "TERRORIST":
                tKills += 1.0
            else:
                ctKills += 1.0
        ctPoints += ctKills
        tPoints += tKills

        damagedf = df[df["event"] == "player_hurt"]
        for _, row in damagedf.iterrows():
            damage = np.minimum(row["damage_capped"], row["user_health"])
            if row["attacker_team_name"] == "TERRORIST":
                tPoints += damage / 100
            else:
                ctPoints += damage / 100

        SIGNIFICANT_DAMAGE_THRESHOLD = 50.0
        totalKills = ctKills + tKills
        totalDamage = ctPoints + tPoints
        if totalKills == 0 and totalDamage < SIGNIFICANT_DAMAGE_THRESHOLD:
            return None

        isEven = max(ctPoints, tPoints) < 1.3 * min(ctPoints, tPoints)
        ctWin = ctPoints > tPoints

        if isEven:
            activity = f"Even_{zone}"
        elif ctWin:
            activity = f"CT_{zone}"
        else:
            activity = f"T_{zone}"

        return {
            "concept:name": activity,
            "ctPoints": ctPoints,
            "tPoints": tPoints
        }

    def createLog(self):
        log = {}
        for matchNumber, match_file in enumerate(self.matches):
            self.initParser(match_file)
            allEvents = self.prepareEvents(matchNumber)
            if isinstance(allEvents, str): #some event were missing
                print(f"{allEvents} event were missing in {match_file}")
                continue

            roundWinnerDict = getRoundWinnerDict(self.parser)
            roundCashSpentEvenDict = self.getRoundCashSpentEvenDict(self.parser)
            for round in range(1, len(roundWinnerDict)+1):
                #is fair round
                self.totalRounds +=1 #data
                isCashSpentEven = roundCashSpentEvenDict[round]
                if isCashSpentEven:
                    self.roundSkipDueToCash +=1 #data
                    continue
                    
                #is mapping good enough
                roundEvents = allEvents[allEvents["total_rounds_played"] == round]
                before = roundEvents["activityPoints"].sum()
                roundEvents = self.mapPlacesToZones(roundEvents)
                after = roundEvents["activityPoints"].sum()
                fractionKept = after/before 
                
                filterData = { #data
                    self.DIFF_ACTIVITY_POINTS: abs(before-after),
                    self.FILTERED: fractionKept > self.FILTER_FRACTION_EVENTS_AFTER_MAPPING,
                    self.ROUND: round
                }
                self.allFilterDataPerRound.append(filterData) #data

                notEnoughEvents = not fractionKept > self.FILTER_FRACTION_EVENTS_AFTER_MAPPING
                if notEnoughEvents: 
                    self.roundSkipDueToEventsFiltered +=1 #data
                    continue
            
                trace = []
                for zone in self.zones:
                    objectives, plotData = self.findHighActivitySegmentsInZone(zone, roundEvents)
                    
                    if self.PLOTTING:
                        
                        if plotData is None: 
                            continue
                        

                        pd_copy = ensure_plotdata(plotData, roundEvents) 
                        pd_copy.setdefault('round_number', round) 
                        pd_copy.setdefault('zone_name', zone)
                        plot_activity_with_decay(pd_copy, tick_rate=self.TICK_RATE, show_legend=False)

                    for objective in objectives:
                        activity_dict = self.determineActivties(objective)
                        if activity_dict:
                            trace.append(activity_dict)

                if trace:
                    trace_dict = {
                        "match": matchNumber,
                        "trace": trace,
                        "roundAttributes": roundWinnerDict[round]
                    }
                    self.case += 1
                    log[self.case] = trace_dict


        return log


import pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event
def convert_to_event_log(log_dict):
    event_log = EventLog()

    for case_id, case_data in log_dict.items():
        trace = Trace()
        trace.attributes["concept:name"] = f"Round_{case_id}"
        trace.attributes["round_winner"] = case_data["roundAttributes"]

        for ev in case_data["trace"]:
            event = Event()

            # Event name (mandatory)
            event["concept:name"] = ev.get("concept:name", "UnknownActivity")

            # Copy all attributes
            for k, v in ev.items():
                if k != "concept:name":
                    event[k] = v

            trace.append(event)

        event_log.append(trace)

    return event_log
def write_txt_log(log_dict, path):
    with open(path, "w") as f:
        for case_id, case_data in log_dict.items():
            f.write(f"Case {case_id} (Winner: {case_data['roundAttributes']}):\n")
            for ev in case_data["trace"]:
                f.write("  - " + str(ev) + "\n")
            f.write("\n")

if __name__ == '__main__':
    workflowlog = WorkflowLog()
    log = workflowlog.createLog()
    # Convert to pm4py EventLog
    event_log = convert_to_event_log(log)

    # Write XES
    pm4py.write_xes(event_log, "Log.xes")

    # Write TXT
    write_txt_log(log, "Log.txt")