import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import argparse
import sys
import textwrap

"""Field Days Statistics Tracker

The module supports:
- Multiple game types (PK's, Cross, A/D, etc.)
- Player statistics tracking
- Team formation and history
- Season-based record keeping
- Excel-based data storage and retrieval

Usage:
    python program.py                     # Process all data without adding new day
    python program.py --new-day          # Add a new field day before processing
    python program.py -h, --help         # Show this help message
"""

# Configuration constants
CONFIG = {
    "EXCEL_FILE": Path("./Field_Days.xlsx"),
    "SEASONS_RANGE": range(23, 26),  # Current seasons range
    "GAME_TYPES": {
        "PK's": "pk",
        "Cross": "cross",
        "A/D": "ad",
        "P&F": "pf",
        "SS": "ss",
        "FK's": "fk",
        "Days": "days",
        "Games": "games"
    }
}

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="""Field Days Statistics Tracker

Processes field day statistics and maintains records in an Excel spreadsheet.
Tracks wins, losses, and various other statistics across different game types.""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
                %(prog)s                    # Process all data
                %(prog)s --new-day          # Add new field day
                %(prog)s -h, --help         # Show this help message
            """)
    )
    
    parser.add_argument(
        '--new-day',
        action='store_true',
        help='Add a new field day before processing data'
    )
    
    return parser.parse_args()

# Global lists of players and names for season resets
players: List['Player'] = []
player_names = ["Aaron",  "AB",  "Anthony",  "Brandon", "Eric", "Jacob", "Kiernan", "Quinn", "Sam G", "Sam S", "Tighe"]


# CLASS/OBJECT DEFINITIONS

@dataclass
class GameStats:
    """Statistics for a single game type.
    
    Attributes:
        wins (int): Number of wins for this game type.
        losses (int): Number of losses for this game type.
    """
    wins: int = 0
    losses: int = 0


@dataclass
class Player:
    """Represents a player and their statistics.
    
    This class maintains all statistics for a single player, including their
    performance in different game types, MVP/clown counts, and teammate history.
    
    Attributes:
        name (str): The player's name.
        stats (Dict[str, GameStats]): Statistics for each game type.
        mvp (int): Number of MVP awards.
        clown (int): Number of Clown of the Match awards.
        teammates (Dict[str, int]): Frequency of playing with other players.
    """
    name: str
    
    def __post_init__(self):
        """Initialize player statistics after instance creation.
        
        Creates statistics tracking for all game types defined in CONFIG["GAME_TYPES"]
        and initializes teammate tracking for all known players.
        """
        # Initialize all stats to 0
        self.stats: Dict[str, GameStats] = {
            game_type: GameStats()
            for game_type in CONFIG["GAME_TYPES"].values()
        }
        self.mvp: int = 0
        self.clown: int = 0
        self.teammates: Dict[str, int] = {name: 0 for name in player_names}
    
    @property
    def games_w(self) -> int:
        """Total number of individual game wins (excluding Days).
        
        Returns:
            int: Sum of wins across all game types except Days.
        """
        return sum(self.stats[game].wins for game in ["pk", "cross", "ad", "pf", "ss", "fk"])
    
    @property
    def games_l(self) -> int:
        """Total number of individual game losses (excluding Days).
        
        Returns:
            int: Sum of losses across all game types except Days.
        """
        return sum(self.stats[game].losses for game in ["pk", "cross", "ad", "pf", "ss", "fk"])


@dataclass
class Game:
    """Represents a single game within a field day.
    
    Tracks the game type and score between two teams.
    
    Attributes:
        name (str): The type of game (e.g., "PK's", "Cross").
        score (str): The score in format "X-Y".
        team1_score (int): Team 1's score (computed from score string).
        team2_score (int): Team 2's score (computed from score string).
    
    Raises:
        ValueError: If score format is invalid or contains negative numbers.
    """
    name: str
    score: str
    team1_score: int = 0
    team2_score: int = 0
    
    def __post_init__(self):
        """Parse and validate the score string after instance creation."""
        try:
            self.team1_score, self.team2_score = map(int, self.score.split("-"))
            if self.team1_score < 0 or self.team2_score < 0:
                raise ValueError("Scores cannot be negative")
        except (ValueError, TypeError):
            raise ValueError(f"Invalid score format: {self.score}. Expected format: 'number-number'")


@dataclass
class Day:
    """Represents a complete field day session.
    
    Tracks teams, overall score, and individual games played during the session.
    
    Attributes:
        team1 (List[Player]): Players on team 1.
        team2 (List[Player]): Players on team 2.
        score (str): Overall score in format "X-Y".
        games (List[Game]): Individual games played during the session.
        team1_score (int): Team 1's overall score (computed from score string).
        team2_score (int): Team 2's overall score (computed from score string).
    
    Raises:
        ValueError: If score format is invalid or contains negative numbers.
    """
    team1: List[Player]
    team2: List[Player]
    score: str
    games: List[Game]
    team1_score: int = 0
    team2_score: int = 0
    
    def __post_init__(self):
        """Parse and validate the score string after instance creation."""
        try:
            self.team1_score, self.team2_score = map(int, self.score.split("-"))
            if self.team1_score < 0 or self.team2_score < 0:
                raise ValueError("Scores cannot be negative")
        except (ValueError, TypeError):
            raise ValueError(f"Invalid score format: {self.score}. Expected format: 'number-number'")


# HELPER FUNCTIONS

def get_player(name: str) -> Player:
    """Get or create a player by name.
    
    Looks up a player by name in the global players list. If the player
    doesn't exist, creates a new Player instance and adds it to the list.
    
    Args:
        name (str): The name of the player to find or create.
    
    Returns:
        Player: The existing or newly created player instance.
    
    Raises:
        ValueError: If name is empty or not a string.
    """
    if not name or not isinstance(name, str):
        raise ValueError("Player name must be a non-empty string")
    
    player = next((p for p in players if p.name == name), None)
    if not player:
        player = Player(name)
        players.append(player)
    return player


def init_team(player_names: List[str]) -> List[Player]:
    """Initialize a team from a list of player names.
    
    Creates or retrieves Player instances for each name in the list.
    
    Args:
        player_names (List[str]): List of player names to initialize.
    
    Returns:
        List[Player]: List of Player instances corresponding to the names.
    
    Raises:
        ValueError: If player_names list is empty.
    """
    if not player_names:
        raise ValueError("Player names list cannot be empty")
    return [get_player(name.strip()) for name in player_names]


def add_win(game: str, team: List[Player], amt: int = 1) -> None:
    """Add wins to all players on a team for a given game.
    
    Updates the win statistics for each player on the team for the specified game type.
    
    Args:
        game (str): The game type (must be a key in CONFIG["GAME_TYPES"]).
        team (List[Player]): List of players to update statistics for.
        amt (int, optional): Number of wins to add. Defaults to 1.
    
    Raises:
        ValueError: If game type is invalid or amount is negative.
    """
    if game not in CONFIG["GAME_TYPES"]:
        raise ValueError(f"Invalid game type: {game}")
    if amt < 0:
        raise ValueError("Amount cannot be negative")
    
    game_type = CONFIG["GAME_TYPES"][game]
    for player in team:
        player.stats[game_type].wins += amt


def add_loss(game: str, team: List[Player], amt: int = 1) -> None:
    """Add losses to all players on a team for a given game.
    
    Updates the loss statistics for each player on the team for the specified game type.
    
    Args:
        game (str): The game type (must be a key in CONFIG["GAME_TYPES"]).
        team (List[Player]): List of players to update statistics for.
        amt (int, optional): Number of losses to add. Defaults to 1.
    
    Raises:
        ValueError: If game type is invalid or amount is negative.
    """
    if game not in CONFIG["GAME_TYPES"]:
        raise ValueError(f"Invalid game type: {game}")
    if amt < 0:
        raise ValueError("Amount cannot be negative")
    
    game_type = CONFIG["GAME_TYPES"][game]
    for player in team:
        player.stats[game_type].losses += amt


def remove_player(rem_player: Player, player_list: List[Player]) -> List[Player]:
    """Create a new list excluding the specified player.
    
    Args:
        rem_player (Player): Player to exclude from the list.
        player_list (List[Player]): Original list of players.
    
    Returns:
        List[Player]: New list containing all players except rem_player.
    
    Raises:
        ValueError: If rem_player is not a Player instance.
    """
    if not isinstance(rem_player, Player):
        raise ValueError("rem_player must be a Player instance")
    return [player for player in player_list if player.name != rem_player.name]


def update_team_lists(team: List[Player]) -> None:
    """Update teammate frequency counts for all players on a team.
    
    For each player on the team, increments the count of times they've
    played with every other player on the team.
    
    Args:
        team (List[Player]): List of players who played together.
    
    Raises:
        ValueError: If team is empty.
    """
    if not team:
        raise ValueError("Team cannot be empty")
    
    for player in team:
        for other_player in remove_player(player, team):
            player.teammates[other_player.name] += 1


def update_stat(table: pd.DataFrame, player_num: int, wins: int, losses: int, record: str, pct: str) -> None:
    """Update win-loss record and winning percentage in statistics table.
    
    Args:
        table (pd.DataFrame): DataFrame containing player statistics.
        player_num (int): Row index for the player in the table.
        wins (int): Number of wins to record.
        losses (int): Number of losses to record.
        record (str): Column name for the win-loss record.
        pct (str): Column name for the winning percentage.
    
    Raises:
        ValueError: If wins or losses are negative.
    """
    if wins < 0 or losses < 0:
        raise ValueError("Wins and losses cannot be negative")
    
    table.at[player_num, record] = f"{wins}-{losses}"
    table.at[player_num, pct] = 0 if wins == 0 and losses == 0 else round(wins / (wins + losses), 4)


def get_new_day_input() -> List:
    """Collect input for a new field day.
    
    Prompts the user for all necessary information about a new field day,
    including date, teams, scores, and awards.
    
    Returns:
        List: Row data ready to be added to the Excel sheet.
    
    Raises:
        ValueError: If any input validation fails or user cancels.
    """
    print("\nEntering new field day data:")
    print("----------------------------")
    
    # Get basic day information
    nd_date = input("Date (MM/DD/YY): ").strip()
    nd_team1 = input("Team 1 Players (comma-separated): ").strip()
    nd_team2 = input("Team 2 Players (comma-separated): ").strip()
    nd_score = input("Score (X-Y): ").strip()
    
    # Initialize row with basic info
    nd_row = [nd_date, nd_team1, nd_team2, nd_score]
    
    # Get game results
    print("\nEnter game results (press Enter with no input when done):")
    while True:
        nd_game = input("Next Game (format: 'GameType (X-Y)'): ").strip()
        if not nd_game:
            # Fill remaining game columns with None
            while len(nd_row) < 11:
                nd_row.append(None)
            break
        nd_row.append(nd_game)
    
    # Get awards
    print("\nAwards (press Enter to skip):")
    mvp = input("MVP: ").strip()
    nd_row.append(mvp if mvp else None)
    
    clown = input("Clown of the Match: ").strip()
    nd_row.append(clown if clown else None)
    
    # Show confirmation
    print("\nNew day summary:")
    print("---------------")
    print(f"Date: {nd_row[0]}")
    print(f"Team 1: {nd_row[1]}")
    print(f"Team 2: {nd_row[2]}")
    print(f"Score: {nd_row[3]}")
    print(f"Games: {nd_row[4:11]}")
    print(f"MVP: {nd_row[11]}")
    print(f"Clown: {nd_row[12]}")
    
    confirm = input("\nConfirm new day? (y/n): ").strip().lower()
    if confirm in ['', 'y', 'yes']:
        return nd_row
    raise ValueError("New day entry cancelled by user")


def read_excel(filename: str, season: int = None, new_day: bool = False) -> List[Day]:
    """Read and parse field day data from Excel spreadsheet.
    
    Args:
        filename (str): Path to the Excel file.
        new_day (bool, optional): Whether to prompt for new day input.
    
    Returns:
        List[Day]: List of Day objects containing the parsed field day data.
    
    Raises:
        FileNotFoundError: If Excel file doesn't exist.
        ValueError: If Excel data is malformed or invalid.
    """
    # Reset player stats for each season
    global players, player_names
    players = [Player(name) for name in player_names]
    days = []
    days_df = pd.read_excel(filename, sheet_name="Days")
    
    if new_day and not season:
        try:
            nd_row = get_new_day_input()
            days_df.loc[len(days_df)] = nd_row
            with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                days_df.to_excel(writer, sheet_name='Days', index=False, startrow=0, startcol=0)
            print("New day added successfully!")
        except ValueError as e:
            print(f"Error adding new day: {e}")
            if str(e) != "New day entry cancelled by user":
                raise
    
    for index, row in days_df.iterrows():
        if not season or (season and str(row['Date']).split("/")[-1] == str(season)):
            team1 = init_team(row['Team 1'].split(", "))
            team2 = init_team(row['Team 2'].split(", "))
            score = row['Score']
            if isinstance(row['MVP'], str):
                today_mvp = get_player(row['MVP'])
                today_mvp.mvp += 1
            if isinstance(row['Clown of the Match'], str):
                today_clown = get_player(row['Clown of the Match'])
                today_clown.clown += 1

            game_columns = [col for col in days_df.columns if col.startswith('Game')]
            games = []
            for game_col in game_columns:
                game_data = row[game_col]
                if pd.notna(game_data):
                    game_name, game_score = game_data.split(" ")
                    game_score = game_score[1:-1]  # Removing parentheses around score
                    games.append(Game(game_name, game_score))

            days.append(Day(team1, team2, score, games))

    return days


def parse_days(days_list: List[Day]) -> None:
    """Process a list of field days and update player statistics.
    
    For each day, updates:
    - Teammate frequencies
    - Win/loss records for the overall day
    - Win/loss records for individual games
    - Point totals for games played
    
    Args:
        days_list (List[Day]): List of Day objects to process.
    """
    for day in days_list:
        update_team_lists(day.team1)
        update_team_lists(day.team2)
        if day.team1_score > day.team2_score:
            day_winning_team, day_losing_team, day_winning_team_score, day_losing_team_score = \
             day.team1, day.team2, day.team1_score, day.team2_score
        else:
            day_winning_team, day_losing_team, day_winning_team_score, day_losing_team_score = \
             day.team2, day.team1, day.team2_score, day.team1_score

        add_win("Days", day_winning_team)
        add_loss("Days", day_losing_team)
        add_win("Games", day_winning_team, day_winning_team_score)
        add_loss("Games", day_winning_team, day_losing_team_score)
        add_win("Games", day_losing_team, day_losing_team_score)
        add_loss("Games", day_losing_team, day_winning_team_score)

        for game in day.games:
            if game.team1_score > game.team2_score:
                game_winning_team, game_losing_team, game_winning_team_score, game_losing_team_score = \
                    day.team1, day.team2, game.team1_score, game.team2_score
            else:
                game_winning_team, game_losing_team, game_winning_team_score, game_losing_team_score = \
                    day.team2, day.team1, game.team2_score, game.team1_score
                
            add_win(game.name, game_winning_team, game_winning_team_score)
            add_loss(game.name, game_winning_team, game_losing_team_score)
            add_win(game.name, game_losing_team, game_losing_team_score)
            add_loss(game.name, game_losing_team, game_winning_team_score)


def update_excel(filename: str, season: Optional[int] = None) -> None:
    """Update Excel spreadsheet with current player statistics.
    
    Writes current player statistics to either the main Stats sheet or a
    season-specific sheet. Also updates the Teams sheet with teammate
    frequencies when writing to the main Stats sheet.
    
    Args:
        filename (str): Path to the Excel file.
        season (Optional[int], optional): Two-digit year to write stats for.
            If None, writes to main Stats sheet and Teams sheet.
    
    Raises:
        FileNotFoundError: If Excel file doesn't exist.
        PermissionError: If Excel file is locked for editing.
    """
    stats = pd.read_excel(filename, sheet_name="Stats")
    teams = pd.read_excel(filename, sheet_name="Teams")
    
    sorted_players = sorted(players, key=lambda p: p.name.lower())


    # EXCEL ROW/COLUMN HEADERS NEED TO BE MANUALLY UPDATED IF/WHEN MORE PLAYERS OR GAMES ARE ADDED
    for player in sorted_players:
        wins = [player.stats["days"].wins, player.stats["games"].wins, player.stats["pk"].wins, player.stats["cross"].wins,
                player.stats["ad"].wins, player.stats["pf"].wins, player.stats["ss"].wins, player.stats["fk"].wins]
        losses = [player.stats["days"].losses, player.stats["games"].losses, player.stats["pk"].losses, player.stats["cross"].losses,
                  player.stats["ad"].losses, player.stats["pf"].losses, player.stats["ss"].losses, player.stats["fk"].losses]
        record_text = ['Days Record', 'Games Record', "PK's Record", 'Cross Record',
                       'A/D Record', 'P&F Record', 'SS Record', "FK's Record"]
        pct_txt = ['Days Pct', 'Games Pct', "PK's Pct", 'Cross Pct', 'A/D Pct',
                   'P&F Pct', 'SS Pct', "FK's Pct"]

        stats.at[(sorted_players.index(player)), 'Name'] = player.name
        for i in range(len(wins)):
            update_stat(stats, (sorted_players.index(player)), wins[i], losses[i], record_text[i], pct_txt[i])
        stats.at[(sorted_players.index(player)), 'MVP'] = player.mvp
        stats.at[(sorted_players.index(player)), 'Clown'] = player.clown
        stats.at[(sorted_players.index(player)), '(Name)'] = player.name
        
        if not season:
            for teammate in player.teammates.items():
                teams.at[(sorted_players.index(player)), teammate[0]] = round(teammate[1] / (player.stats["days"].wins + player.stats["days"].losses), 3)
                
    with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
        if season:
            stats.to_excel(writer, sheet_name='20' + str(season) + ' Stats', index=False, startrow=0, startcol=0)
        else:
            stats.to_excel(writer, sheet_name='Stats', index=False, startrow=0, startcol=0)
            teams.to_excel(writer, sheet_name='Teams', index=False, startrow=0, startcol=0)


def main() -> None:
    """Main program entry point.
    
    Processes field day data according to command line arguments:
    - With no arguments: processes all data
    - With --new-day: adds a new field day before processing
    
    Returns:
        int: 0 for success, 1 for error
    """
    args = parse_arguments()
    filename = CONFIG["EXCEL_FILE"]
    
    try:
        print("Processing all field days...")
        days = read_excel(filename, new_day=args.new_day)
        parse_days(days)
        update_excel(filename)
        print(f"Processed {len(days)} total days")
        
        # Process individual seasons
        for season in CONFIG["SEASONS_RANGE"]:
            yr_days = read_excel(filename, season)
            parse_days(yr_days)
            update_excel(filename, season)
            print(f"Processed {len(yr_days)} days for 20{season} season")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0


# On start:
if __name__ == '__main__':
    sys.exit(main())
