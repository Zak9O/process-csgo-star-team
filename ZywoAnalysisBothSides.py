import os
from demoparser2 import DemoParser
import pandas as pd
from pm4py.objects.log.obj import EventLog, Trace, Event
import pm4py


def printColumns(df):
    for column in df.columns:
        print(column)


class WorkflowLog():

    def __init__(self):
        self.playerData = ["last_place_name", "inventory", "team_name"]
        self.gameStateData = ["total_rounds_played"]
        self.folder_path = r"C:\Users\felim\Desktop\School\PM\matches"
        self.matches = os.listdir(self.folder_path)
        self.parser = None
        self.case = 1

    def initParser(self, match_file):
        full_path = os.path.join(self.folder_path, match_file)
        self.parser = DemoParser(full_path)

    # ---------------------------------------------------------
    #   FIRST BLOOD DETECTION
    # ---------------------------------------------------------

    def findFBs(self):
        deaths_df = self.parser.parse_event(
            "player_death",
            player=self.playerData,
            other=self.gameStateData
        )
        deaths_df = deaths_df.loc[
            deaths_df.groupby('total_rounds_played')['tick'].idxmin()
        ].reset_index(drop=True)
        return deaths_df

    def findHeroFBdata(self, hero, weapon_filter="awp"):
        fbs = self.findFBs()                    # all FB
        fbs = fbs[fbs["attacker_name"] == hero] # only hero FB

        # Keep only FBs where hero holds the weapon (AWP by default)
        fbs = fbs[fbs["attacker_inventory"].apply(
            lambda inv: any(weapon_filter.lower() == w.lower() for w in inv)
        )]

        # NO team filtering anymore (old code removed)

        fbs = self.addPlayersInvolvedInFB(fbs)
        return fbs


    # ---------------------------------------------------------
    #   TEAMMATES + ENEMIES AT THE FB TICK
    # ---------------------------------------------------------

    def addPlayersInvolvedInFB(self, fb_df):
        fb_df = fb_df.copy()
        fb_df['teamates'] = None
        fb_df['enemies'] = None

        for idx, fb in fb_df.iterrows():

            tick = fb['tick']
            attacker_team = fb['attacker_team_name']
            victim_team = fb['user_team_name']

            attacker_zone = fb['attacker_last_place_name']
            victim_zone = fb['user_last_place_name']

            players_at_tick = self.parser.parse_ticks(
                ["last_place_name", "team_name", "name"],
                ticks=[tick]
            )

            players_in_zone = players_at_tick[
                players_at_tick['last_place_name'].isin([attacker_zone, victim_zone])
            ]

            teammates = players_in_zone[
                (players_in_zone['team_name'] == attacker_team) &
                (players_in_zone['name'] != fb['attacker_name'])
            ]['name'].tolist()

            enemies = players_in_zone[
                (players_in_zone['team_name'] == victim_team)
            ]['name'].tolist()

            fb_df.at[idx, 'teamates'] = teammates
            fb_df.at[idx, 'enemies'] = enemies

        return fb_df

    # ---------------------------------------------------------
    #   FLASH DETECTION
    # ---------------------------------------------------------

    def defineFlashEvent(self, event):
        flasher = event["user_name"]
        flasher_team = event["user_team_name"]
        tick = event["tick"]

        before = self.parser.parse_ticks(["player_name", "flash_duration"], ticks=[tick - 1])
        after = self.parser.parse_ticks(["player_name", "flash_duration"], ticks=[tick])

        merged = before.merge(after, on="player_name", suffixes=("_before", "_after"))
        flashed = merged[merged["flash_duration_after"] > merged["flash_duration_before"]].copy()
        flashed["flash_increase"] = flashed["flash_duration_after"] - flashed["flash_duration_before"]
        flashed = flashed[flashed["flash_increase"] >= 0.3]

        players_now = self.parser.parse_ticks(["player_name", "team_name"], ticks=[tick])
        flashed = flashed.merge(players_now, on="player_name", how="left")

        result_events = []
        for _, row in flashed.iterrows():
            flashed_team = row["team_name"]
            role = "team_flash" if flashed_team == flasher_team else "enemy_flash"
            result_events.append(role)

        if "team_flash" in result_events and "enemy_flash" in result_events:
            return "flashHitBothTeams"
        elif "team_flash" in result_events:
            return "flashHitTeammates"
        elif "enemy_flash" in result_events:
            return "flashHitEnemies"
        else:
            return "flashHitNone"

    # ---------------------------------------------------------
    #   EVENT COLLECTION FOR FB CONTEXT
    # ---------------------------------------------------------

    def get_players_events_dict(self, fb):
        TICKS_BACK = 64 * 1

        tick_end = fb["tick"]
        tick_start = max(0, tick_end - TICKS_BACK)

        hero = fb["attacker_name"]
        teammates = fb["teamates"]
        enemies = fb["enemies"]

        # NO SIDE FILTERING — collect all players involved
        all_players = [hero] + teammates + enemies

        event_list = [
            "weapon_fire", "player_hurt", "grenade_thrown",
            "flashbang_detonate", "smokegrenade_detonate",
            "decoy_detonate", "grenade_detonate"
        ]

        events_df_list = []

        for event in event_list:
            df = self.parser.parse_event(
                event, player=["health", "armor_value", "team_name", "dmg_health", "dmg_armor"]
            )
            if isinstance(df, list) or df.empty:
                continue

            df = df[
                df["user_name"].isin(all_players) &
                (df["tick"] >= tick_start) &
                (df["tick"] <= tick_end)
            ].copy()

            df["event_type"] = event
            events_df_list.append(df)

        if not events_df_list:
            return []

        all_events_df = pd.concat(events_df_list, ignore_index=True)

        # Keep role labels (no filtering)
        role_map = {hero: "teamate"}
        role_map.update({name: "teammate" for name in teammates})
        role_map.update({name: "enemy" for name in enemies})

        trace = []
        for _, row in all_events_df.iterrows():

            tick = row["tick"]
            player_name = row["user_name"]
            role = role_map.get(player_name, "unknown")
            label = role
            event_type = row["event_type"]

            # weapon_fire
            if event_type == "weapon_fire":
                weapon = row.get("weapon", "").lower()
                if any(w in weapon for w in ["knife", "flashbang", "hegrenade", "smokegrenade", "decoy", "molotov", "incendiary"]):
                    continue
                event_data = {
                    "tick": tick,
                    "name": label,
                    "concept:name": f"weapon_fire_{label}",
                    "weapon": row["weapon"],
                    "team": row["user_team_name"]
                }

            # player_hurt
            elif event_type == "player_hurt":
                event_name = "first_blood" if row["health"] == 0 else "player_hurt"
                event_data = {
                    "tick": tick,
                    "name": label,
                    "concept:name": event_name if event_name == "first_blood" else f"{event_name}_{label}",
                    "dmg_health": row["dmg_health"],
                    "dmg:armor": row["dmg_armor"],
                    "team": row["user_team_name"]
                }

            # grenade / flash / smoke
            elif event_type == "grenade_thrown":
                event_data = {
                    "tick": tick,
                    "name": label,
                    "concept:name": f"grenade_thrown_{row['weapon']}_{label}",
                    "team": row["user_team_name"]
                }

            elif event_type == "flashbang_detonate":
                flash_type = self.defineFlashEvent(row)
                event_data = {
                    "tick": tick,
                    "name": label,
                    "concept:name": f"{flash_type}_{label}",
                    "team": row["user_team_name"]
                }

            elif event_type == "smokegrenade_detonate":
                event_data = {
                    "tick": tick,
                    "name": label,
                    "concept:name": f"smokegrenade_detonate_{label}",
                    "team": row["user_team_name"]
                }

            elif event_type == "decoy_detonate":
                event_data = {
                    "tick": tick,
                    "name": label,
                    "concept:name": f"decoy_detonate_{label}",
                    "team": row["user_team_name"]
                }

            trace.append(event_data)

        # FILTERING
        filtered_trace = []
        last_weapon_fire = {}
        last_hurt = {}

        for e in trace:
            cname = e["concept:name"]

            if cname.startswith("weapon_fire"):
                    # collapse only if same player_name AND same tick
                    key = (e["name"], e["tick"])
                    if key in last_weapon_fire:
                        continue  # ignore exact duplicate
                    last_weapon_fire[key] = True
                    filtered_trace.append(e)
                    continue

            # collapse player_hurt duplicates
            if cname.startswith("player_hurt"):
                key = (e["name"], e["tick"])
                if key in last_hurt:
                    filtered_trace[last_hurt[key]] = e
                else:
                    last_hurt[key] = len(filtered_trace)
                    filtered_trace.append(e)
                continue

            filtered_trace.append(e)

        return sorted(filtered_trace, key=lambda x: x["tick"])

    # ---------------------------------------------------------
    #   TRACE CREATION
    # ---------------------------------------------------------

    def findActivitiesLeadingToFirstBlood(self, fb_df):
        log = {}
        for _, fb in fb_df.iterrows():
            log[self.case] = self.get_players_events_dict(fb)
            self.case += 1
        return log

    # ---------------------------------------------------------
    #   CREATE LOG
    # ---------------------------------------------------------

    def createLog(self, hero="ZywOo"):
        log = {}
        try:
            for match_file in self.matches:
                self.initParser(match_file)

                fb_df = self.findHeroFBdata(hero)
                if fb_df.empty:
                    continue

                match_log = self.findActivitiesLeadingToFirstBlood(fb_df)
                log |= match_log

        except KeyboardInterrupt:
            print("Interrupted, returning partial log.")

        return log


# ---------------------------------------------------------
#   EVENT LOG CONVERSION + EXPORT
# ---------------------------------------------------------


def write_txt_log(log_dict, filename="Log.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        for cid, trace_list in log_dict.items():
            f.write(f"CASE {cid}\n")
            f.write("-" * 40 + "\n")
            for e in trace_list:
                tick = e.get("tick", "")
                cname = e.get("concept:name", "")
                pname = e.get("name", "")
                team = e.get("team", "")

                f.write(f"[tick {tick}]  {cname}  (player={pname}, team={team})\n")

            f.write("\n\n")

def convert_to_event_log(log_dict):
    event_log = EventLog()
    for cid, trace_list in log_dict.items():
        trace = Trace()
        trace.attributes["concept:name"] = str(cid)
        for e in trace_list:
            trace.append(Event(e))
        event_log.append(trace)
    return event_log


workflowlog = WorkflowLog()
log = workflowlog.createLog()

# Write XES
event_log = convert_to_event_log(log)
pm4py.write_xes(event_log, "Log.xes")

# Write TXT
write_txt_log(log, "Log.txt")