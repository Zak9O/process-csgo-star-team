from pm4py.objects.log.obj import EventLog, Trace, Event
from demoparser2 import DemoParser
import pandas as pd
from pandas.core.api import DataFrame


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


class Decorator:
    def __init__(
        self, case_attributes: list[str], activity_attributes: list[str]
    ) -> None:
        self.case_attributes: list[str] = case_attributes
        self.activity_attributes: list[str] = activity_attributes
        self._path: str

    def set_path(self, path: str) -> None:
        self._path = path


class Parser:
    def __init__(self, path: str, decorator: Decorator) -> None:
        self.path: str = path
        self.parser: DemoParser = DemoParser(self.path)
        self.decorator: Decorator = decorator
        self.decorator.set_path(self.path)

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

    def parse(self) -> list[Case]:
        print(f"Parsing {self.path}")

        traces: list[Case] = []

        incident_intervals: list[tuple[int, int, int]] = self.get_incident_intervals()

        print(f"  Found {len(incident_intervals)} rounds with bomb planted!")
        for start, end, round in incident_intervals:
            df = self.parser.parse_ticks(
                ["tick", "name", "is_alive", "team_name", "last_place_name", "total_rounds_played"],
                ticks=range(start, end + 1),
            )
            events_death = self.filter_deahts(start, end)
            round_end_reason = self.get_reason(round)
            incident_parser = IncidentParser(
                df, events_death, round_end_reason, self.decorator
            )
            trace = incident_parser.parse()
            traces.extend(trace)
            print(f"  Parsed round {round}")

        return traces

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
            start_t = int(round_end["tick"])

            output.append((start, start_t, int(round)))

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
        round_end_reason: str,
        decorator: Decorator,
    ) -> None:
        self.df: pd.DataFrame = df
        self.terrorits_alive_at_begining = self.get_terrorits_alive_at_begining()
        self.df = self.filter_ct(self.df)
        self.round_end_reason: str = round_end_reason
        self.decorator: Decorator = decorator
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

            case_attributes = self.get_case_attributes(player)

            case_parser = CaseParser(df, case_attributes, self.decorator)
            case = case_parser.parse()
            cases.append(case)

        return cases

    def get_case_attributes(self, player: str) -> dict[str, object]:
        # TODO: Incorporate other attributes from decorator
        return {
            "round_end_reason": self.round_end_reason,
            "name": player,
            "terrorists_alive_at_begining": self.terrorits_alive_at_begining,
        }

    def get_terrorits_alive_at_begining(self) -> int:
        start = self.df.iloc[0]["tick"]
        df = self.df[self.df["tick"] == start]
        df = df[df["team_name"] == "TERRORIST"]
        df = df[df["is_alive"]]
        return len(df)

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
        self, df: pd.DataFrame, case_attributes: dict[str, object], decorator: Decorator
    ) -> None:
        self.df: pd.DataFrame = df
        self.start = self.df.iloc[0]["tick"]
        self.end = self.df.iloc[-1]["tick"]  # This might be weird if everybody is dead
        self.decorator: Decorator = decorator
        self.start = self.df.iloc[0]["tick"]
        self.round = self.df.iloc[0]["total_rounds_played"]
        self.player = self.df.iloc[0]["name"]
        self.case_attributes = case_attributes

    def parse(self) -> Case:
        trace: list[Activity] = []

        for _, row in self.df.iterrows():
            name = row["activity_name"]
            time = row["tick"] - self.start
            attributes = dict()
            for attr in self.decorator.activity_attributes:
                attributes[attr] = row[attr]
            trace.append(Activity(name, time, attributes))

        trace.append(Activity("RoundEnd", self.end))

        case = Case(
            self.decorator._path + str(self.round) + self.player, trace, self.case_attributes
        )
        return case


def create_event_log(cases: list[Case]) -> EventLog:
    event_log = EventLog()
    event_log.attributes["concept:name"] = "csgo_demo_log"
    for case in cases:
        trace = Trace()
        trace.attributes["concept:name"] = case.name
        for attr, value in case.attributes.items():
            trace.attributes[attr] = value
        for activity in case.trace:
            event = Event()
            event["concept:name"] = activity.name

            # 0.0156 seconds per tick for a 64-tick server
            # 0.0078 seconds per tick for a 128-tick server
            event["time:seconds"] = int(activity.time * 0.0156)
            for attr, value in activity.attributes.items():
                event[attr] = value

            trace.append(event)

        event_log.append(trace)

    return event_log
