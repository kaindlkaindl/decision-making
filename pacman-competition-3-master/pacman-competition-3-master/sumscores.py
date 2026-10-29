import argparse
import html.parser
import os
from math import ceil, log10
from typing import Any

from competition import Record, Result


DEFAULT_FILE = "scoreboard.html"

HTML_OUTPUT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
.disqualified {{
  color: red;
}}
td, th {{
  text-align: center;
}}

th[scope="row"] {{
  text-align: right;
}}

.win {{
  background-color: lightgreen;
}}
.tie {{
  background-color: lavender;
}}
.lost {{
  background-color: lightblue;
}}
.error {{
  background-color: lightsalmon;
}}
.points {{
  background-color: lightgoldenrodyellow;
}}
.note {{
  text-align: left;
}}

td[colspan] {{
  background-color: lightgrey;
}}

caption, figcaption {{
  font-style: italic;
  text-align: center;
}}

.layout {{
  width: min-content;
}}

.layout > pre {{
  border: 2px solid lightgrey;
  padding: 0.5em;
  width: min-content;
}}
</style>
</head>

<body>
<h2>Team ranking</h2>
The team ranking is based on a total competition score.  Each result type is
worth a number of points, as can be seen in the table below.  In case of equal
competition scores, teams with more points collected will be ranked higher.
<table>
  <thead>
    <tr>
      <th>Outcome type</th>
      <th>Competition points</th>
    <tr>
  </thead>
  <tbody>
    <tr class="win">
      <td>Win</td>
      <td>{Result.WIN}</td>
    </tr>
    <tr class="tie">
      <td>Tie</td>
      <td>{Result.TIE}</td>
    </tr>
    <tr class="lost">
      <td>Lost</td>
      <td>{Result.LOST}</td>
    </tr>
    <tr class="error">
      <td>Error</td>
      <td>{Result.ERROR}</td>
    </tr>
  </tbody>
</table>

<table>
  <caption>Ranking of all qualified teams.</caption>
  <thead>
    <tr>
      <th>Position</th>
      <th>Team name</th>
      <th>Points</th>
      <th>Win</th>
      <th>Tie</th>
      <th>Lost</th>
      <th>Failed</th>
      <th>Competition score</th>
      <th>Criterium "Deelname"</th>
    </tr>
  </thead>
  <tbody>
{ranking}
  </tbody>
</table>
</body>
</html>"""


class TeamSummary:
    """
    Summarizes the results of a single team in the competition.
    """

    def __init__(
        self,
        position=None,
        team_name="",
        points: int | str = 0,
        win: int | str = 0,
        tie: int | str = 0,
        lost: int | str = 0,
        failed: int | str = 0,
        score: int | str = 0,
    ):
        """
        Create a summary for a single team.

        You can pass a raw data line split by tabs, or pass the individual parameters.
        """
        # Ignore position and score
        # Score can be computed from win, tie, lost, failed.
        self.team_name = team_name
        self._record = Record(
            win=int(win),
            tie=int(tie),
            lost=int(lost),
            error=int(failed),
            points=int(points),
        )

    @property
    def points(self) -> int:
        return self._record.points

    @points.setter
    def points(self, value: int):
        self._record.points = value

    @property
    def win(self) -> int:
        return self._record.win

    @win.setter
    def win(self, value: int):
        self._record._counter[Result.WIN] = max(value, 0)

    @property
    def tie(self) -> int:
        return self._record.tie

    @tie.setter
    def tie(self, value: int):
        self._record._counter[Result.TIE] = max(value, 0)

    @property
    def lost(self) -> int:
        return self._record.lost

    @lost.setter
    def lost(self, value: int):
        self._record._counter[Result.LOST] = max(value, 0)

    @property
    def failed(self) -> int:
        return self._record.error

    @failed.setter
    def failed(self, value: int):
        self._record._counter[Result.ERROR] = max(value, 0)

    @property
    def score(self) -> int:
        return self._record.score()

    def count_matches(self) -> int:
        """
        Counts the number of games played by this team.

        Effectively computes numParticipants * numGames, where numGames is the number of matches between each team.
        numParticipants includes baselineTeam, if present.
        """
        return self.win + self.tie + self.lost + self.failed

    def __add__(self, other: "TeamSummary") -> "TeamSummary":
        self_type = type(self)
        other_type = type(other)
        if self_type != other_type:
            raise ValueError(f"Can't add {self_type} and {other_type}")
        if self.team_name != other.team_name:
            raise ValueError(
                f"Can't add scores of two different teams: {self.team_name} and {other.team_name}"
            )
        record = self._record + other._record
        return TeamSummary(
            team_name=self.team_name,
            points=self.points + other.points,
            win=record.win,
            tie=record.tie,
            lost=record.lost,
            failed=record.error,
            score=record.score(),
        )

    def __repr__(self) -> str:
        return (
            f"TeamSummary(team_name={self.team_name!r}, "
            f"points={self.points}, "
            f"win={self.win}, "
            f"tie={self.tie}, "
            f"lost={self.lost}, "
            f"failed={self.failed}, "
            f"score={self.score})"
        )

    def __str__(self) -> str:
        return (
            f"Team: {self.team_name}\n"
            f"  points: {self.points}\n"
            f"  win:    {self.win}\n"
            f"  tie:    {self.tie}\n"
            f"  lost:   {self.lost}\n"
            f"  failed: {self.failed}\n"
            f"  score:  {self.score}\n"
        )

    def __cmp__(self, other: Any) -> int:
        """
        Makes TeamSummaries sortable.

        Sorting is based on the tie-breaker rules in competition.Record.
        """
        if type(self) is not type(other):
            return -1
        return (self._record > other._record) - (self._record < other._record)

    def __lt__(self, other: Any) -> bool:
        """
        Defines self < other.
        """
        return self._record < other._record

    def __le__(self, other: Any) -> bool:
        """
        Defines self <= other.
        """
        return self._record <= other._record

    def __gt__(self, other: Any) -> bool:
        """
        Defines self > other.
        """
        return self._record > other._record

    def __ge__(self, other: Any) -> bool:
        """
        Defines self >= other.
        """
        return self._record >= other._record


class CompetitionSummary:
    """
    Summarizes the results of a competition run.
    """

    def __init__(self):
        self.team_summaries: dict[str, TeamSummary] = {}

    def add_team_summary(self, summary: TeamSummary) -> None:
        """
        Adds a team summary to the competition summary.
        """
        if summary.team_name in self.team_summaries:
            self.team_summaries[summary.team_name] += summary
        else:
            self.team_summaries[summary.team_name] = summary

    def parse_raw_data(self, data: str):
        """
        Parses raw data from a single competition run.
        """
        data_lines = data.split("\n")
        # Skip header line
        while data_lines and not data_lines[0].strip()[0].isnumeric():
            data_lines = data_lines[1:]

        for line in data_lines:
            d = line.strip().split("\t")
            summary = TeamSummary(*d)
            self.add_team_summary(summary)

    def remove_only_errors(self):
        """
        Remove teams that only have errors (no wins, ties, or losses).

        As their competetors get a win for free, this can skew the results.
        Remove those wins as well.  As we can't say how many points were scored
        in these matches, do not modify the points.
        """
        while True:
            only_errors = [
                (name, summary.failed)
                for name, summary in self.team_summaries.items()
                if summary.win == 0 and summary.tie == 0 and summary.lost == 0
            ]
            if not only_errors:
                break
            for error_team, errors in only_errors:
                d_err = int(errors / (len(self.team_summaries) - 1))
                for team in self.team_summaries:
                    summary = self.team_summaries[team]
                    summary.win -= d_err
                    self.team_summaries[team] = summary
                del self.team_summaries[error_team]

    def rank_teams(self) -> list[TeamSummary]:
        """
        Ranks teams based on their competition score and points.
        """
        return sorted(list(self.team_summaries.values()), reverse=True)

    def compute_grade(
        self, team: TeamSummary, is_below_baseline: bool
    ) -> tuple[int | None, str]:
        """
        Computes the grade for the 'Deelname' criterium.
        """
        if team.team_name.lower().startswith("baseline"):
            return None, "-----------------"
        # team.count_matches == num_participants * num_games
        # when you exclude baselineTeam as a competitor
        matches = team.count_matches()
        if team.failed >= matches / 10:
            return (
                0,
                f"errors ≥ numParticipants * numGames / 10 = {int(matches / 10 + 1)}",
            )
        if is_below_baseline:
            return 1, "onder baselineTeam"
        if team.win > matches / 2:
            return 3, f"wins &gt; numParticipants * numGames / 2 = {int(matches / 2)}"
        return 2, ""

    def __add__(self, other: "CompetitionSummary") -> "CompetitionSummary":
        self_type = type(self)
        other_type = type(other)
        if self_type != other_type:
            raise ValueError(f"Can't add {self_type} and {other_type}")
        summed = CompetitionSummary()
        for name, summary in self.team_summaries.items():
            if name not in other.team_summaries:
                summed.team_summaries[name] = summary
            else:
                summed.team_summaries[name] = summary + other.team_summaries[name]
        for name, summary in other.team_summaries.items():
            if name not in summed.team_summaries:
                summed.team_summaries[name] = summary
        return summed

    def __str__(self) -> str:
        num_teams = len(self.team_summaries)

        def get_padding(fn):
            try:
                return ceil(log10(max(map(fn, self.team_summaries.values()))))
            except ValueError:
                return 1

        header = (
            "RANK",
            "NAME",
            "POINTS",
            "WIN",
            "TIE",
            "LOST",
            "FAILED",
            "SCORE",
            "BEOORDELING DEELNAME",
        )
        padding_rank = max(ceil(log10(num_teams)), len(header[0]))
        padding_name = max(
            max(map(lambda t: len(t.team_name), self.team_summaries.values())),
            len(header[1]),
        )
        padding_points = max(get_padding(lambda t: t.points), len(header[2]))
        padding_win = max(get_padding(lambda t: t.win), len(header[3]))
        padding_tie = max(get_padding(lambda t: t.tie), len(header[4]))
        padding_lost = max(get_padding(lambda t: t.lost), len(header[5]))
        padding_failed = max(get_padding(lambda t: t.failed), len(header[6]))
        padding_score = max(get_padding(lambda t: t.score), len(header[7]))
        format_str = (
            f"| {{rank:>{padding_rank}}} | "
            f"{{team.team_name:<{padding_name}}} | "
            f"{{team.points:>{padding_points}}} | "
            f"{{team.win:>{padding_win}}} | "
            f"{{team.tie:>{padding_tie}}} | "
            f"{{team.lost:>{padding_lost}}} | "
            f"{{team.failed:>{padding_failed}}} | "
            f"{{team.score:>{padding_score}}} | "
            f"{{note}} |\n"
        )
        output = (
            f"| {{0:>{padding_rank}}} | "
            f"{{1:<{padding_name}}} | "
            f"{{2:>{padding_points}}} | "
            f"{{3:>{padding_win}}} | "
            f"{{4:>{padding_tie}}} | "
            f"{{5:>{padding_lost}}} | "
            f"{{6:>{padding_failed}}} | "
            f"{{7:>{padding_score}}} | "
            "{8} |\n"
        ).format(*header)
        output += (
            "|-"
            + (padding_rank * "-")
            + "-|-"
            + (padding_name * "-")
            + "-|-"
            + (padding_points * "-")
            + "-|-"
            + (padding_win * "-")
            + "-|-"
            + (padding_tie * "-")
            + "-|-"
            + (padding_lost * "-")
            + "-|-"
            + (padding_failed * "-")
            + "-|-"
            + (padding_score * "-")
            + "-|-"
            + (len(header[8]) * "-")
            + "-|\n"
        )

        below_baseline = False
        for index, team in enumerate(self.rank_teams()):
            rank = index + 1
            grade, motivation = self.compute_grade(team, below_baseline)
            if grade is None:
                below_baseline = True
                note = motivation
            else:
                note = f"{grade}: {motivation}"
            output += format_str.format(rank=rank, team=team, note=note)
        return output

    def to_html(self):
        ranking_html = ""
        below_baseline = False
        ## Grades are computed based on the following properties:
        # total_games = sum(team.count_matches() for team in self.team_summaries.values()) / 2
        # threshold_fail = total_games / 10
        # threshold_excellent = total_games / 2
        ## These values are divided by 2, as both A vs B as well as B vs A are stored.
        for index, team in enumerate(self.rank_teams()):
            rank = index + 1
            grade, motivation = self.compute_grade(team, below_baseline)
            if grade is None:
                below_baseline = True
                note = motivation
            else:
                note = f"{grade}: {motivation}"
            ranking_html += f"""<tr>
  <td>{rank}</td>
  <td>{team.team_name}</td>
  <td class="points">{team.points}</td>
  <td class="win">{team.win}</td>
  <td class="tie">{team.tie}</td>
  <td class="lost">{team.lost}</td>
  <td class="error">{team.failed}</td>
  <td class="score">{team.score}</td>
  <td class="note">{note}</td>
</tr>
"""
        return HTML_OUTPUT.format(Result=Result, ranking=ranking_html)


class ResultsHTMLParser(html.parser.HTMLParser):
    """
    HTML parser for competition scoreboard.
    """

    def __init__(self) -> None:
        super().__init__()
        self.in_table: int = 0
        self.skip_table: bool = False
        self.collecting_row: bool = False
        self.collecting_cell: bool = False
        self.row_buffer: list[str] = []
        self.cell_buffer: str = ""
        self.summary: CompetitionSummary = CompetitionSummary()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.in_table += 1
        if tag == "tr" and self.in_table != 0 and not self.skip_table:
            self.collecting_row = True
            self.row_buffer = []
        if tag == "td" and self.collecting_row and not self.skip_table:
            self.collecting_cell = True
            self.cell_buffer = ""

    def handle_data(self, data: str) -> None:
        if self.collecting_cell:
            self.cell_buffer += data.strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            self.in_table -= 1
            self.skip_table = False
        if tag == "tr" and self.collecting_row and not self.skip_table:
            self.collecting_row = False
            if len(self.row_buffer) < 8:
                # Insufficient data in row
                if len(self.row_buffer) > 0:
                    self.skip_table = True
                return
            try:
                self.summary.add_team_summary(TeamSummary(*self.row_buffer))
            except (ValueError, TypeError):
                # Could not create TeamSummary from row data, either because
                # of insufficient data or invalid data.
                self.skip_table = True
            self.row_buffer = []
        if tag == "td" and self.collecting_cell and not self.skip_table:
            self.collecting_cell = False
            self.row_buffer.append(self.cell_buffer.strip())
            self.cell_buffer = ""


def parse_html(path: os.PathLike) -> CompetitionSummary:
    """
    Parses a scoreboard HTML file and returns a CompetitionSummary.
    """
    try:
      with open(path, "r", encoding="utf-8") as f:
          html_content = f.read()
    except FileNotFoundError:
      with open(os.path.join(path, "scoreboard.html"), "r", encoding="utf-8") as f:
          html_content = f.read()
    parser = ResultsHTMLParser()
    parser.feed(html_content)
    return parser.summary


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarizes competition results from an HTML file."
    )
    parser.add_argument(
        "paths",
        type=str,
        nargs="+",
        help="Paths to the scoreboard HTML file",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    print("# Data inclusief OnlyErrors")
    total = CompetitionSummary()
    for path in args.paths:
      summary = parse_html(path)
      total += summary
      print(f"## {path}:")
      print(summary)
    print(f"## Alle {len(args.paths)} scoreboards bij elkaar opgeteld")
    print(total)

    with open('results-summed-up.html', 'w', encoding='utf-8') as f:
       f.write(total.to_html())

    print("# Data exclusief OnlyErrors")
    print(f"## Alle {len(args.paths)} scoreboards bij elkaar opgeteld")
    total.remove_only_errors()
    print(total)

    with open('results-summed-up-zonder-onlyerror.html', 'w') as f:
        f.write(total.to_html())
