from pm4py.objects.log.obj import EventLog, Trace, Event
from demoparser2 import DemoParser
import pandas as pd
from pandas.core.api import DataFrame
import datetime
from pathlib import Path


class Activity:
    def __init__(
        self, name: str, time: int, attributes: dict[str, object] = dict()
    ) -> None:
        self.name: str = name
        self.time: int = time
        self.attributes: dict[str, object] = attributes


class Case:
    def __init__(
        self, name: str, trace: list[Activity], attributes: dict[str, object] = dict()
    ) -> None:
        self.name: str = name
        self.trace: list[Activity] = trace
        self.attributes: dict[str, object] = attributes


class Attributes:
    def __init__(self, path: str, end: int) -> None:
        self.case_attributes: dict[str, object] = dict()
        self.activity_attributes: dict[str, object] = dict()
        self.end: int = end
        self.path: str = path


class Parser:
    def __init__(self, path: str) -> None:
        self.path: str = path
        self.parser: DemoParser = DemoParser(self.path)

        parser_attributes = ["total_rounds_played"]
        self.events_bomb_planted: pd.DataFrame = self.parser.parse_event(
            "bomb_planted", other=parser_attributes
        )
        self.events_round_end: pd.DataFrame = self.parser.parse_event(
            "round_end", other=parser_attributes
        )
        # total_rounds_played changes the moment the round ends. - 1 to match events_bomb_planted
        self.events_round_end["total_rounds_played"] = (
            self.events_round_end["total_rounds_played"] - 1
        )

        self.events_death = self.parser.parse_event("player_death")
        self.rounds = 0
        self.traces = 0

    def parse(self) -> list[Case]:
        print(f"Parsing {self.path}")

        traces: list[Case] = []

        incident_intervals: list[tuple[int, int, int]] = self.get_incident_intervals()

        print(f"  Found {len(incident_intervals)} rounds with bomb planted!")
        for start, end, round in incident_intervals:
            # There is some very weird behavoir where the same round is finished twice.
            # I have chosen to skip it, since it is VERY rare
            # It happens in round 0 of game: "drgn-vs-ursa-m3-dust2.dem"
            if end < start:
                print("WARNING: Weird round behavoir where end < start")
                continue
            df = self.parser.parse_ticks(
                [
                    "tick",
                    "name",
                    "is_alive",
                    "team_name",
                    "last_place_name",
                    "total_rounds_played",
                ],
                ticks=range(start, end + 1),
            )
            bomb_site = self.get_bomb_site(round, df)
            events_death = self.filter_deahts(start, end)
            round_end_reason = self.get_reason(round)
            attributes: Attributes = Attributes(self.path, end + 1)
            attributes.case_attributes["round_end_reason"] = round_end_reason
            attributes.case_attributes["bomb_site"] = bomb_site

            incident_parser = IncidentParser(df, events_death, attributes)
            try:
                trace = incident_parser.parse()
                traces.extend(trace)
                self.rounds += 1
                self.traces += len(trace)
                print(f"  Parsed round {round}")
            except Exception as e:
                print("------------- An Error occured!!! -------------")
                print(e)

        print(f"Parsed {self.rounds} rounds with {self.traces} traces")
        return traces

    def get_bomb_site(self, round: int, df: pd.DataFrame) -> str:
        bomb_planter = self.events_bomb_planted[
            self.events_bomb_planted["total_rounds_played"] == round
        ].iloc[0]["user_name"]
        bomb_site = df[df["name"] == bomb_planter].iloc[0]["last_place_name"]
        return bomb_site

    def filter_deahts(self, start: int, end: int) -> pd.DataFrame:
        return self.events_death[
            (self.events_death["tick"] >= start) & (self.events_death["tick"] <= end)
        ]

    def get_incident_intervals(self) -> list[tuple[int, int, int]]:
        output = []
        for round in self.events_bomb_planted["total_rounds_played"].unique():
            bomb_planted = self.events_bomb_planted[
                self.events_bomb_planted["total_rounds_played"] == round
            ].iloc[0]
            start = int(bomb_planted["tick"])

            round_end = self.events_round_end[
                self.events_round_end["total_rounds_played"] == round
            ].iloc[0]
            end = int(round_end["tick"])

            output.append((start, end, int(round)))

        return output

    def get_reason(self, round: int) -> str:
        round_end = self.events_round_end[
            self.events_round_end["total_rounds_played"] == round
        ].iloc[0]
        return round_end["reason"]


class IncidentParser:
    def __init__(
        self,
        df: pd.DataFrame,
        events_death: pd.DataFrame,
        attributes: Attributes,
    ) -> None:
        self.df: pd.DataFrame = df
        self.terrorits_alive_at_begining, self.ct_alive_at_begining = (
            self.get_people_alive_at_begining()
        )
        self.df = self.filter_ct(self.df)
        self.attributes: Attributes = attributes
        self.events_death: pd.DataFrame = events_death

        # Added for execution speed
        self.is_player_alive_at_begining = self.get_alive_at_begining_dict()

    def parse(self) -> list[Case]:
        cases: list[Case] = []
        for player in self.df["name"].unique():
            if not self.is_player_alive_at_begining[player]:
                continue

            df = self.filter_player(self.df, player)
            df = self.filter_location_changes(df)
            df = df.rename(columns={"last_place_name": "activity_name"})

            if self.did_player_die(player):
                death_activity = self.get_death_activity(player)
                df = pd.concat([df, death_activity], ignore_index=True)
            else:
                round_end_activity = self.get_round_end_activity()
                df = pd.concat([df, round_end_activity], ignore_index=True)

            self.attributes.case_attributes.update(self.get_case_attributes(player))

            case_parser = CaseParser(df, self.attributes)
            case = case_parser.parse()
            cases.append(case)

        return cases

    def get_case_attributes(self, player: str) -> dict[str, object]:
        # TODO: Incorporate other attributes from decorator
        if self.ct_alive_at_begining <= self.terrorits_alive_at_begining:
            advantage = "T"
        else:
            advantage = "CT"
        return {
            "name": player,
            "terrorists_alive_at_begining": self.terrorits_alive_at_begining,
            "ct_alive_at_begining": self.ct_alive_at_begining,
            "T_CT_alive_ratio": f"{self.terrorits_alive_at_begining}:{self.ct_alive_at_begining}",
            "advantage": advantage,
        }

    def get_people_alive_at_begining(self) -> tuple[int, int]:
        start = self.df.iloc[0]["tick"]
        df = self.df[self.df["tick"] == start]
        df_terrorits = df[df["team_name"] == "TERRORIST"]
        df_terrorits = df_terrorits[df_terrorits["is_alive"]]
        df_ct = df[df["team_name"] == "CT"]
        df_ct = df_ct[df_ct["is_alive"]]
        return len(df_terrorits), len(df_ct)

    def get_round_end_activity(self) -> pd.DataFrame:
        data = {
            "activity_name": "RoundEnd",
            "tick": [self.attributes.end],
        }
        return pd.DataFrame(data)

    def get_death_activity(self, player: str) -> pd.DataFrame:
        died_at_tick = self.events_death[self.events_death["user_name"] == player][
            "tick"
        ]
        # Consider if attributes should be added as well
        data = {
            "activity_name": "PlayerDied",
            "tick": died_at_tick,
        }
        return pd.DataFrame(data)

    def did_player_die(self, player: str) -> bool:
        return player in self.events_death["user_name"].unique()

    def filter_location_changes(self, df: pd.DataFrame) -> DataFrame:
        """
        Mask df to only include location changes. We do not want all the rows where localtion changes are the same
        """
        change_mask = df["last_place_name"] != df["last_place_name"].shift(1)
        df = df[change_mask]
        return df

    def filter_ct(self, df: pd.DataFrame) -> DataFrame:
        team_mask = df["team_name"] == "CT"
        df = df[team_mask]
        return df

    def filter_player(self, df: pd.DataFrame, player: str) -> DataFrame:
        player_mask = df["name"] == player
        df = df[player_mask]
        return df

    def get_alive_at_begining_dict(self) -> dict[str, bool]:
        start = self.df.iloc[0]["tick"]
        start_mask = self.df["tick"] == start
        df = self.df[start_mask]
        return df[["name", "is_alive"]].set_index("name")["is_alive"].to_dict()


class CaseParser:
    def __init__(
        self,
        df: pd.DataFrame,
        decorator: Attributes,
    ) -> None:
        self.df: pd.DataFrame = df
        self.start = self.df.iloc[0]["tick"]
        self.decorator: Attributes = decorator
        self.round = self.df.iloc[0]["total_rounds_played"]
        self.player = self.df.iloc[0]["name"]

    def parse(self) -> Case:
        trace: list[Activity] = []

        for _, row in self.df.iterrows():
            name = row["activity_name"]
            time = row["tick"] - self.start
            attributes = dict()
            for attr in self.decorator.activity_attributes:
                attributes[attr] = row[attr]
            trace.append(Activity(name, time, attributes))

        p = Path(self.decorator.path)

        case = Case(
            '-'.join(p.name.split('-')[:3]) + '-' + str(self.round) + '-' + self.player,
            trace,
            self.decorator.case_attributes,
        )
        return case


def create_event_log(cases: list[Case], add_case_attr_to_activity: bool) -> EventLog:
    event_log = EventLog()
    event_log.attributes["concept:name"] = "csgo_demo_log"
    for case in cases:
        trace = Trace()
        trace.attributes["concept:name"] = case.name
        if not add_case_attr_to_activity:
            for attr, value in case.attributes.items():
                trace.attributes[attr] = value
        for activity in case.trace:
            event = Event()
            event["concept:name"] = activity.name

            # 0.0156 seconds per tick for a 64-tick server
            seconds = activity.time * 0.0156
            timestamp = datetime.datetime.fromtimestamp(seconds)

            event["time:timestamp"] = timestamp.isoformat(timespec="milliseconds")
            if add_case_attr_to_activity:
                attr = activity.attributes | case.attributes
            else:
                attr = activity.attributes

            for attr, value in attr.items():
                event[attr] = value

            trace.append(event)

        event_log.append(trace)

    return event_log
