from demoparser2 import DemoParser
import pandas as pd
from pandas.core.api import DataFrame


class Parser:
    def __init__(self, path: str) -> None:
        self.path: str = path
        self.parser: DemoParser = DemoParser(self.path)
        parser_attributes = ["total_rounds_played"]
        self.events_bomb_defused: pd.DataFrame = self.parser.parse_event(
            "bomb_defused", other=parser_attributes
        )
        self.events_bomb_planted: pd.DataFrame = self.parser.parse_event(
            "bomb_planted", other=parser_attributes
        )

    def parse(self) -> list[list[str]]:
        print(f"Considering {self.path}")

        traces: list[list[str]] = []
        rounds = self.events_bomb_defused["total_rounds_played"]
        count = len(rounds)

        print(f"  Found {count} rounds with bomb defusions!")
        for round in rounds:
            trace = self.parse_round(round)
            traces.extend(trace)
            print(f"  Parsed round {round}")

        return traces

    def parse_round(self, round: int) -> list[list[str]]:
        start_t, end_t = self.extract_ticks(round)

        df = self.get_CT_dataframe(start_t, end_t)
        alive_start = self.alive_at_t(df, start_t)

        players: list[str] = list(df["name"].unique())

        traces: list[list[str]] = []

        for player in players:
            if not alive_start[player]:
                continue
            trace = self.parse_player(player, df, end_t)
            traces.append(trace)

        return traces

    def parse_player(self, player: str, df: pd.DataFrame, end_t: int) -> list[str]:
        alive_end = self.alive_at_t(df, end_t)
        df = self.mask_df_to_player(player, df)

        trace = list(df["last_place_name"])
        if not alive_end[player]:
            trace.append("Die")
        trace.append("Round End")

        return trace

    def extract_ticks(self, round: int) -> tuple[int, int]:
        bomb_defused = self.events_bomb_defused[
            self.events_bomb_defused["total_rounds_played"] == round
        ].iloc[0]
        end_t = bomb_defused["tick"]

        bomb_planted = self.events_bomb_planted[
            self.events_bomb_planted["total_rounds_played"] == round
        ].iloc[0]
        start_t = bomb_planted["tick"]

        return (start_t, end_t)

    def get_CT_dataframe(self, start_t: int, end_t: int) -> pd.DataFrame:
        trace = self.parser.parse_ticks(
            ["last_place_name", "team_name", "is_alive"],
            ticks=range(int(start_t), int(end_t + 1)),
        )
        team_mask = trace["team_name"] == "CT"
        trace = trace[team_mask]
        return trace

    def alive_at_t(self, df: pd.DataFrame, tick: int) -> dict[str, int]:
        tick_mask = df["tick"] == tick
        df = df[tick_mask]
        return df[["name", "is_alive"]].set_index("name")["is_alive"].to_dict()

    def mask_df_to_player(self, player: str, df: pd.DataFrame) -> DataFrame:
        player_mask = df["name"] == player
        df = df[player_mask]
        change_mask = df["last_place_name"] != df["last_place_name"].shift(1)
        df = df[change_mask]
        return df


parser = Parser("heroic-vs-3dmax-m1-dust2.dem")

parser.parse()

