import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import sys
import json

"""Field Days Statistics Tracker

The module supports:
- Player statistics tracking
- Team formation and history
- Season-based record keeping

Usage:
    python3 program.py
    cd docs && python3 -m http.server 8000 # for local testing of github pages deployment
    http://localhost:8000
"""

# Configuration constants
CONFIG = {
    "EXCEL_FILE": Path("./Field_Days.xlsx"),
    "RATING_VARIANCE_SCALE": 3.0,
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

# Global lists of players and names for season resets
players: List['Player'] = []
player_names: List[str] = []


# INITIALIZATION FUNCTIONS

def extract_player_names(filename: str) -> List[str]:
    """Extract all unique player names from the Days sheet in the Excel file.
    
    Args:
        filename (str): Path to the Excel file.
    
    Returns:
        List[str]: Sorted list of unique player names.
    
    Raises:
        FileNotFoundError: If Excel file doesn't exist.
    """
    days_df = pd.read_excel(filename, sheet_name="Days")
    player_set = set()

    for _, row in days_df.iterrows():
        if pd.notna(row['Team 1']):
            player_set.update(p.strip() for p in str(row['Team 1']).split(",") if p.strip())
        if pd.notna(row['Team 2']):
            player_set.update(p.strip() for p in str(row['Team 2']).split(",") if p.strip())

    return sorted(player_set)


def extract_year(value) -> int:
    """Extract a year from an Excel date value."""
    if isinstance(value, pd.Timestamp):
        return value.year
    date = pd.to_datetime(value, format='mixed', errors='raise')
    return date.year


def extract_seasons(filename: str) -> List[int]:
    """Extract the seasons (years) from the Days sheet in the Excel file.
    
    Args:
        filename (str): Path to the Excel file.
    
    Returns:
        List[int]: Sorted list of years found in the data.
    
    Raises:
        FileNotFoundError: If Excel file doesn't exist.
    """
    days_df = pd.read_excel(filename, sheet_name="Days")
    return sorted({extract_year(value) for value in days_df['Date']})


def build_rankings(days_df: pd.DataFrame, seasons: List[int]) -> Dict[str, List[Dict]]:
    """Build opponent-adjusted Elo rankings from the Days sheet."""
    scopes = {'total': days_df.copy()}
    scopes.update({
        str(season): days_df[days_df['Date'].map(extract_year) == season].copy()
        for season in seasons
    })

    rankings: Dict[str, List[Dict]] = {}
    # Generate one complete ranking table for every scope.
    for scope, scope_days in scopes.items():
        player_stats: Dict[str, Dict] = {}
        # Maintain each player's evolving Elo rating as the days are processed chronologically.
        player_ratings: Dict[str, float] = {}
        opponent_ratings: Dict[str, List[float]] = {}
        # Track the final Elo value immediately after every field day a player participates in.
        elo_history: Dict[str, List[Dict[str, float]]] = {}

        # Normalize dates so the Elo process always follows true chronological order.
        scope_days['_parsed_date'] = scope_days['Date'].map(
            lambda value: value if isinstance(value, pd.Timestamp)
            else pd.to_datetime(value, format='mixed', errors='raise')
        )
        scope_days = scope_days.sort_values('_parsed_date')

        # Process each field day once and update ratings from that day's result.
        for day_number, (_, row) in enumerate(scope_days.iterrows(), start=1):
            team1 = [name.strip() for name in str(row['Team 1']).split(',') if name.strip()]
            team2 = [name.strip() for name in str(row['Team 2']).split(',') if name.strip()]
            team1_score, team2_score = map(int, str(row['Score']).split('-'))

            # Initialize unseen players at 1500 Elo with empty supporting statistics.
            for name in team1 + team2:
                stats = player_stats.setdefault(name, {
                    'days_played': 0,
                    'day_wins': 0, 'day_losses': 0,
                    'game_wins': 0, 'game_losses': 0,
                    'mvp': 0, 'clown': 0,
                })
                stats['days_played'] += 1
                player_ratings.setdefault(name, 1500.0)
                opponent_ratings.setdefault(name, [])
                elo_history.setdefault(name, [])

            # Use the average of both rosters to represent the strength of each team.
            team1_rating = sum(player_ratings[name] for name in team1) / len(team1)
            team2_rating = sum(player_ratings[name] for name in team2) / len(team2)
            for name in team1:
                opponent_ratings[name].append(team2_rating)
            for name in team2:
                opponent_ratings[name].append(team1_rating)

            # Estimate Team 1's expected win probability from the Elo difference.
            expected_team1 = 1 / (1 + 10 ** ((team2_rating - team1_rating) / 400))
            if team1_score > team2_score:
                actual_team1 = 1.0
            elif team1_score < team2_score:
                actual_team1 = 0.0
            else:
                actual_team1 = 0.5

            # Scale surprise outcomes
            rating_change = 24 * (actual_team1 - expected_team1)
            # Split the result across teammates, reducing individual change with roster size.
            for name in team1:
                player_ratings[name] += rating_change / len(team1) ** 0.5
            for name in team2:
                player_ratings[name] -= rating_change / len(team2) ** 0.5

            for name in team1:
                if team1_score != team2_score:
                    player_stats[name]['day_wins' if team1_score > team2_score else 'day_losses'] += 1
            for name in team2:
                if team1_score != team2_score:
                    player_stats[name]['day_wins' if team2_score > team1_score else 'day_losses'] += 1

            for column in [column for column in scope_days.columns if str(column).startswith('Game ')]:
                game = row[column]
                if pd.isna(game):
                    continue
                _, score_text = str(game).rsplit(' ', 1)
                game_score1, game_score2 = map(int, score_text.strip('()').split('-'))
                # Attribute points earned and conceded to every Team 1 player.
                for name in team1:
                    player_stats[name]['game_wins'] += max(game_score1 - game_score2, 0)
                    player_stats[name]['game_losses'] += max(game_score2 - game_score1, 0)
                # Attribute points earned and conceded to every Team 2 player.
                for name in team2:
                    player_stats[name]['game_wins'] += max(game_score2 - game_score1, 0)
                    player_stats[name]['game_losses'] += max(game_score1 - game_score2, 0)

            # Count MVP awards for the player when their name is present on the day's row.
            if isinstance(row['MVP'], str):
                name = row['MVP'].strip()
                if name in player_stats:
                    player_stats[name]['mvp'] += 1
            # Count Clown of the Match awards for the player when present.
            if isinstance(row['Clown of the Match'], str):
                name = row['Clown of the Match'].strip()
                if name in player_stats:
                    player_stats[name]['clown'] += 1

            # Record the blended Elo for each participating player at this chronological day.
            for name in team1 + team2:
                stats = player_stats[name]
                history_days = stats['days_played']
                history_games = stats['game_wins'] + stats['game_losses']
                history_day_pct = (stats['day_wins'] + 2.5) / (history_days + 5)
                history_game_pct = (stats['game_wins'] + 5) / (history_games + 10)
                history_mvp_rate = stats['mvp'] / history_days
                history_clown_rate = stats['clown'] / history_days
                history_confidence = min(history_days / 10, 1)
                history_average_opponent_rating = (
                    sum(opponent_ratings[name]) / len(opponent_ratings[name])
                    if opponent_ratings[name]
                    else 1500
                )
                history_expected_game_pct = 1 / (
                    1 + 10 ** (
                        (history_average_opponent_rating - player_ratings[name]) / 400
                    )
                )
                history_day_adjustment = (history_day_pct - 0.5) * 200
                history_game_adjustment = (
                    history_game_pct - history_expected_game_pct
                ) * 160
                history_award_adjustment = (
                    history_mvp_rate - history_clown_rate
                ) * 100
                history_rating = player_ratings[name] + history_confidence * (
                    history_day_adjustment
                    + history_game_adjustment
                    + history_award_adjustment
                ) * CONFIG["RATING_VARIANCE_SCALE"]
                elo_history[name].append({
                    'day': day_number,
                    'rating': round(history_rating, 1),
                })

        rows = []
        # Convert stored raw statistics into the final display fields for one scope.
        for name, stats in player_stats.items():
            # Count the player's field days to support records and low-sample confidence.
            days_played = stats['days_played']
            # Count scored and conceded games to support the game-win percentage.
            games_played = stats['game_wins'] + stats['game_losses']
            # Shrink the day win percentage toward 50% using a five-day prior.
            day_pct = (stats['day_wins'] + 5 * 0.5) / (days_played + 5)
            # Shrink the game-point win percentage toward 50% using a ten-point prior.
            game_pct = (stats['game_wins'] + 10 * 0.5) / (games_played + 10)
            # Calculate MVP frequency so awards contribute as a rate rather than a raw count.
            mvp_rate = stats['mvp'] / days_played if days_played else 0
            # Calculate Clown of the Match frequency so awards apply a relative penalty.
            clown_rate = stats['clown'] / days_played if days_played else 0
            # Shrink players with fewer than ten days toward the 1500 baseline.
            confidence = min(days_played / 10, 1)
            established_player_rating = player_ratings[name]
            # Summarize the typical strength of opponents faced by this player.
            average_opponent_rating = (
                sum(opponent_ratings[name]) / len(opponent_ratings[name])
                if opponent_ratings[name]
                else 1500
            )
            expected_game_pct = 1 / (
                1 + 10 ** (
                    (average_opponent_rating - established_player_rating) / 400
                )
            )
            actual_game_pct = game_pct
            # Convert day win percentage deviations into Elo adjustments.
            day_adjustment = (day_pct - 0.5) * 200
            # Reward game performance above expectation based on opponent strength.
            game_adjustment = (actual_game_pct - expected_game_pct) * 160
            # Add 100 Elo per MVP-per-day and subtract 100 Elo per Clown-per-day.
            award_adjustment = (mvp_rate - clown_rate) * 100
            # Add confidence-weighted personal performance to the established Elo.
            rating = established_player_rating + confidence * (
                day_adjustment + game_adjustment + award_adjustment
            ) * CONFIG["RATING_VARIANCE_SCALE"]
            # Assemble all ranking and supporting statistics into one exportable row.
            rows.append({
                'name': name,
                'score': round(rating, 1),
                'rating': round(rating),
                'average_opponent_rating': round(average_opponent_rating),
                'day_record': f"{stats['day_wins']}-{stats['day_losses']}",
                'day_pct': round(day_pct * 100, 1),
                'game_pct': round(game_pct * 100, 1),
                'mvp_rate': round(mvp_rate * 100, 1),
                'clown_rate': round(clown_rate * 100, 1),
                'mvp': stats['mvp'],
                'clown': stats['clown'],
                'days': days_played,
                'history': elo_history[name],
            })

        # Sort from strongest displayed Elo to weakest, with names as a stable tie-breaker.
        rows.sort(key=lambda row: (-row['score'], row['name'].lower()))
        for rank, row in enumerate(rows, start=1):
            row['rank'] = rank
        rankings[scope] = rows

    return rankings


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
    
    Attributes:
        name (str): The player's name.
        stats (Dict[str, GameStats]): Statistics for each game type.
        mvp (int): Number of MVP awards.
        clown (int): Number of Clown of the Match awards.
        teammates (Dict[str, int]): Frequency of playing with other players.
    """
    name: str
    
    def __post_init__(self):
        """Creates statistics tracking for all game types defined in CONFIG["GAME_TYPES"]
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
        """Returns:
            int: Sum of wins across all game types except Days.
        """
        return sum(self.stats[game].wins for game in ["pk", "cross", "ad", "pf", "ss", "fk"])
    
    @property
    def games_l(self) -> int:
        """Returns:
            int: Sum of losses across all game types except Days.
        """
        return sum(self.stats[game].losses for game in ["pk", "cross", "ad", "pf", "ss", "fk"])


@dataclass
class Game:
    """Represents a single game within a field day.
    
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
    """Represents a complete field day.
        
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
    """Looks up a player by name in the global players list. If the player
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
    """Updates the win statistics for each player on the team for the specified game type.
    
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
    """Updates the loss statistics for each player on the team for the specified game type.
    
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
    """For each player on a team, increments the count of times they've
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

def get_active_players(days_list: List[Day]) -> List[Player]:
    """Return a sorted list of players who played at least one day in the given season."""
    active_names = set()
    for day in days_list:
        for player in day.team1 + day.team2:
            active_names.add(player.name)
    return sorted([get_player(name) for name in active_names], key=lambda p: p.name.lower())


def validate_score(score_str: str) -> bool:
    """Validate score string format (X-Y).
    
    Args:
        score_str (str): Score string to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        score1, score2 = map(int, score_str.split("-"))
        if score1 < 0 or score2 < 0:
            return False
        return True
    except ValueError:
        return False


def get_new_day_input() -> List:
    """Prompts the user for all necessary information about a new field day,
    including date, teams, scores, and awards.
    
    Returns:
        List: Row data ready to be added to the Excel sheet.
    
    Raises:
        ValueError: If any input validation fails or user cancels.
    """
    print("\nEntering new field day data:")
    print("----------------------------")
    
    # Get and validate date
    while True:
        nd_date = input("Date (MM/DD/YYYY): ").strip()
        try:
            month, day, year = map(int, nd_date.split("/"))
            if 1 <= month <= 12 and 1 <= day <= 31 and len(str(year)) in [2, 4]:
                break
            print("Error: Invalid date values. Month: 1-12, Day: 1-31, Year: 0000-9999")
        except ValueError:
            print("Error: Invalid date format. Use MM/DD/YYYY (e.g., 05/15/2024)")
    
    # Get and validate teams
    while True:
        nd_team1 = input("Team 1 Players (comma-separated): ").strip()
        team1_players = [p.strip() for p in nd_team1.split(",")]
        if all(p in player_names for p in team1_players):
            break
        print("Error: Unknown player(s) in Team 1.")
        print("Valid players:", ", ".join(player_names))
    
    while True:
        nd_team2 = input("Team 2 Players (comma-separated): ").strip()
        team2_players = [p.strip() for p in nd_team2.split(",")]
        if all(p in player_names for p in team2_players):
            break
        print("Error: Unknown player(s) in Team 2.")
        print("Valid players:", ", ".join(player_names))
    
    # Get and validate day score
    while True:
        nd_score = input("Score (X-Y): ").strip()
        if validate_score(nd_score):
            break
        print("Error: Invalid score format. Use X-Y where X and Y are non-negative numbers")
    
    nd_row = [nd_date, nd_team1, nd_team2, nd_score]
    
    # Track all players for award validation
    all_players = set(team1_players + team2_players)
    
    print("\nValid game types:", ", ".join(CONFIG["GAME_TYPES"].keys()))
    print("Enter game results (press Enter with no input when done):")
    while True:
        nd_game = input("Next Game (format: 'GameType (X-Y)'): ").strip()
        if not nd_game:
            while len(nd_row) < 11:
                nd_row.append(None)
            break
        
        try:
            game_type, score = nd_game.split(" ", 1)
            if game_type not in CONFIG["GAME_TYPES"]:
                print(f"Error: '{game_type}' is not a valid game type.")
                print("Valid types:", ", ".join(CONFIG["GAME_TYPES"].keys()))
                continue
            
            if not (score.startswith("(") and score.endswith(")")):
                print("Error: Score must be in format '(X-Y)'")
                continue
                
            score = score[1:-1]  # Remove parentheses
            if not validate_score(score):
                print("Error: Invalid score format. Use X-Y where X and Y are non-negative numbers")
                continue
                
            nd_row.append(f"{game_type} ({score})")
        except ValueError as e:
            print("Error: Invalid format. Use 'GameType (X-Y)' where X and Y are numbers")
            continue
    
    print("\nAwards (press Enter to skip):")
    print("Available players:", ", ".join(sorted(all_players)))
    
    # Get and validate MVP
    while True:
        mvp = input("MVP: ").strip()
        if not mvp:
            nd_row.append(None)
            break
        if mvp in all_players:
            nd_row.append(mvp)
            break
        print("Error: MVP must be a player from today's teams")
        print("Available players:", ", ".join(sorted(all_players)))
    
    # Get and validate Clown
    while True:
        clown = input("Clown of the Match: ").strip()
        if not clown:
            nd_row.append(None)
            break
        if clown in all_players:
            nd_row.append(clown)
            break
        print("Error: Clown must be a player from today's teams")
        print("Available players:", ", ".join(sorted(all_players)))
    
    print("\nNew day summary:")
    print("---------------")
    print(f"Date: {nd_row[0]}")
    print(f"Team 1: {nd_row[1]}")
    print(f"Team 2: {nd_row[2]}")
    print(f"Score: {nd_row[3]}")
    print("Games:")
    for game in nd_row[4:11]:
        if game:
            print(f"  {game}")
    print(f"MVP: {nd_row[11] or 'None'}")
    print(f"Clown: {nd_row[12] or 'None'}")
    
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
    
    for _, row in days_df.iterrows():
        year_full = extract_year(row['Date'])
        if not season or (season and year_full == int(season)):
            team1 = init_team([name.strip() for name in str(row['Team 1']).split(",")])
            team2 = init_team([name.strip() for name in str(row['Team 2']).split(",")])
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


def update_excel(filename: str, season: Optional[int] = None, active_players: Optional[List[Player]] = None) -> None:
    """Update Excel spreadsheet with current player statistics.
    
    Args:
        filename (str): Path to the Excel file.
        season (Optional[int], optional): Four-digit year to write stats for.
            If None, writes to main Stats sheet and Teams sheet.
    
    Raises:
        FileNotFoundError: If Excel file doesn't exist.
        PermissionError: If Excel file is locked for editing.
    """
    stats = pd.read_excel(filename, sheet_name="Stats")

    # Build the combinations grid from the source player list on every run.
    team_names = sorted(player_names, key=str.casefold)
    teams = pd.DataFrame(0.0, index=team_names, columns=team_names)
    teams.index.name = "Name"
    
    if active_players is not None:
        sorted_players = active_players
    else:
        sorted_players = sorted(players, key=lambda p: p.name.lower())

    # For season sheets, only include players who played at least one day in that season
    filtered_players = []
    if season:
        for player in sorted_players:
            days_wins = player.stats["days"].wins
            days_losses = player.stats["days"].losses
            if days_wins == 0 and days_losses == 0:
                continue
            filtered_players.append(player)
    else:
        filtered_players = sorted_players

    # EXCEL ROW/COLUMN HEADERS NEED TO BE MANUALLY UPDATED IF/WHEN MORE PLAYERS OR GAMES ARE ADDED
    for idx, player in enumerate(filtered_players):
        days_wins = player.stats["days"].wins
        days_losses = player.stats["days"].losses
        wins = [days_wins, player.stats["games"].wins, player.stats["pk"].wins, player.stats["cross"].wins,
                player.stats["ad"].wins, player.stats["pf"].wins, player.stats["ss"].wins, player.stats["fk"].wins]
        losses = [days_losses, player.stats["games"].losses, player.stats["pk"].losses, player.stats["cross"].losses,
                  player.stats["ad"].losses, player.stats["pf"].losses, player.stats["ss"].losses, player.stats["fk"].losses]
        record_text = ['Days Record', 'Games Record', "PK's Record", 'Cross Record',
                       'A/D Record', 'P&F Record', 'SS Record', "FK's Record"]
        pct_txt = ['Days Pct', 'Games Pct', "PK's Pct", 'Cross Pct', 'A/D Pct',
                   'P&F Pct', 'SS Pct', "FK's Pct"]

        stats.at[idx, 'Name'] = player.name
        for i in range(len(wins)):
            update_stat(stats, idx, wins[i], losses[i], record_text[i], pct_txt[i])
        stats.at[idx, 'MVP'] = player.mvp
        stats.at[idx, 'Clown'] = player.clown
        stats.at[idx, '(Name)'] = player.name

        if not season:
            for teammate in player.teammates.items():
                stats_days_total = days_wins + days_losses
                teams.at[player.name, teammate[0]] = round(teammate[1] / stats_days_total, 3) if stats_days_total > 0 else 0

    if season:
        with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
            stats.iloc[:len(filtered_players)].to_excel(writer, sheet_name=str(season) + ' Stats', index=False, startrow=0, startcol=0)
    else:
        with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
            stats.to_excel(writer, sheet_name='Stats', index=False, startrow=0, startcol=0)
        with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            teams.reset_index().to_excel(writer, sheet_name='Teams', index=False)


# JSON EXPORT FUNCTIONS

def export_teams_to_json(filename: str, output_dir: str = "./data") -> None:
    """Export teammate frequency data to JSON for GitHub Pages.
    
    Args:
        filename (str): Path to the Excel file.
        output_dir (str): Directory to save JSON files to.
    """
    global player_names
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    teams = pd.read_excel(filename, sheet_name="Teams")
    teams_data = teams.to_dict('records')
    
    # Clean NaN values and keep only rows with a valid player name
    cleaned_teams = []
    for record in teams_data:
        name = record.get('Name')
        if name not in player_names:
            continue
        cleaned_record = {}
        for key, value in record.items():
            if key != 'Name' and key not in player_names:
                continue
            if pd.isna(value):
                cleaned_record[key] = None
            elif isinstance(value, (int, float)):
                cleaned_record[key] = f"{value * 100:.1f}%"
            else:
                cleaned_record[key] = value
        cleaned_teams.append(cleaned_record)
    
    with open(output_path / "teams.json", "w") as f:
        json.dump(cleaned_teams, f, indent=2)
    

def export_days_to_json(filename: str, output_dir: str = "./data") -> None:
    """Export game history (days) to JSON for GitHub Pages.
    
    Args:
        filename (str): Path to the Excel file.
        output_dir (str): Directory to save JSON files to.
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    days = pd.read_excel(filename, sheet_name="Days")
    
    # Convert dates to proper format
    days['Date'] = pd.to_datetime(days['Date'], format='mixed', errors='raise')
    days = days.sort_values('Date', ascending=False)
    
    days_data = days.to_dict('records')
    
    # Clean and format data
    cleaned_days = []
    for day in days_data:
        cleaned_day = {}
        for key, value in day.items():
            if pd.isna(value):
                if key == 'Date':
                    cleaned_day[key] = None
                    cleaned_day['year'] = None
                else:
                    cleaned_day[key] = None
            else:
                if key == 'Date':
                    if not isinstance(value, pd.Timestamp):
                        value = pd.to_datetime(value, format='mixed', errors='raise')
                    if pd.isna(value):
                        cleaned_day[key] = None
                        cleaned_day['year'] = None
                    else:
                        cleaned_day['year'] = value.year
                        cleaned_day[key] = value.strftime('%m/%d/%Y')
                else:
                    cleaned_day[key] = value
        cleaned_days.append(cleaned_day)
    
    with open(output_path / "days.json", "w") as f:
        json.dump(cleaned_days, f, indent=2)
    

def export_season_stats_to_json(filename: str, output_dir: str = "./data") -> None:
    """Export season-specific statistics to JSON for GitHub Pages.
    
    Args:
        filename (str): Path to the Excel file.
        output_dir (str): Directory to save JSON files to.
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    season_stats = {}
    
    stats_df = pd.read_excel(filename, sheet_name="Stats")
    season_stats['total'] = stats_df.to_dict('records')
    
    # Read season-specific stats
    excel = pd.ExcelFile(filename)
    for sheet in excel.sheet_names:
        if sheet.endswith(" Stats") and sheet != "Stats":
            year = sheet.replace(" Stats", "")
            season_df = pd.read_excel(filename, sheet_name=sheet)
            season_stats[year] = season_df.to_dict('records')
    
    # Clean NaN values
    cleaned_season_stats = {}
    for year, data in season_stats.items():
        records = data if isinstance(data, list) else data.to_dict('records')
        cleaned_records = []
        for record in records:
            cleaned_record = {}
            for key, value in record.items():
                if pd.isna(value):
                    cleaned_record[key] = None
                else:
                    cleaned_record[key] = value
            cleaned_records.append(cleaned_record)
        cleaned_season_stats[year] = cleaned_records
    
    with open(output_path / "season_stats.json", "w") as f:
        json.dump(cleaned_season_stats, f, indent=2)
    

def export_metadata_to_json(seasons: List[int], players_list: List[str], output_dir: str = "./data") -> None:
    """Export metadata (seasons and players) for GitHub Pages.
    
    Args:
        seasons (List[int]): Seasons found in the Excel data.
        players_list (List[str]): List of all players.
        output_dir (str): Directory to save JSON files to.
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    metadata = {
        "seasons": seasons,
        "players": players_list,
        "game_types": list(CONFIG["GAME_TYPES"].keys())
    }
    
    with open(output_path / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)


def export_rankings_to_json(filename: str, seasons: List[int], output_dir: str = "./data") -> None:
    """Export composite player rankings derived from the Days sheet."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    days_df = pd.read_excel(filename, sheet_name="Days")
    rankings = build_rankings(days_df, seasons)

    with open(output_path / "rankings.json", "w") as f:
        json.dump(rankings, f, indent=2)
        

def export_all_data(filename: str, seasons: List[int], players_list: List[str], output_dir: str = "./docs/data") -> None:
    """Export all necessary data for GitHub Pages site.
    
    Args:
        filename (str): Path to the Excel file.
        seasons (List[int]): Seasons found in the Excel data.
        players_list (List[str]): List of all players.
        output_dir (str): Directory to save JSON files to.
    """
    export_teams_to_json(filename, output_dir)
    export_days_to_json(filename, output_dir)
    export_season_stats_to_json(filename, output_dir)
    export_metadata_to_json(seasons, players_list, output_dir)
    export_rankings_to_json(filename, seasons, output_dir)
    print("All data exported successfully")



def main() -> None:
    """Main program entry point - Processes field day data
    
    Returns:
        int: 0 for success, 1 for error
    """
    global player_names
    
    filename = CONFIG["EXCEL_FILE"]
    
    player_names = extract_player_names(filename)
    seasons = extract_seasons(filename)
    print(f"Loaded {len(player_names)} players from Excel:")
    print(", ".join(player_names))
    print("Seasons:", ", ".join(str(season) for season in seasons))
    
    new_day = input("Do you want to add a new day? (y/n): ").strip().lower() in ['y', 'yes']
    
    print("Processing all field days...")
    days = read_excel(filename, new_day=new_day)
    parse_days(days)
    update_excel(filename)
    print(f"Processing {len(days)} total days")

    for season in seasons:
        yr_days = read_excel(filename, season)
        parse_days(yr_days)
        active_players = get_active_players(yr_days)
        update_excel(filename, season, active_players)
        print(f"Processed {len(yr_days)} days for {season} season")

    export_all_data(filename, seasons, player_names)
    
    return 0


# On start:
if __name__ == '__main__':
    sys.exit(main())
