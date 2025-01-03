import pandas as pd
import sys


# Global lists of players and names for season resets
players = []
player_names = ["Aaron",  "AB",  "Anthony",  "Brandon", "Eric", "Jacob", "Kiernan", "Quinn", "Sam G", "Sam S", "Tighe"]


# CLASS/OBJECT DEFINITIONS

# Object to represent a player, including values for each game to keep track of stats
class Player:
    def __init__(self, name: str):
        self.name = name

        self.pk_w, self.pk_l, self.cross_w, self.cross_l = 0, 0, 0, 0
        self.ad_w, self.ad_l, self.pf_w, self.pf_l = 0, 0, 0, 0
        self.ss_w, self.ss_l, self.fk_w, self.fk_l = 0, 0, 0, 0

        self.days_w, self.days_l = 0, 0
        self.games_w = self.pk_w + self.cross_w + self.ad_w + self.pf_w + self.ss_w + self.fk_w
        self.games_l = self.pk_l + self.cross_l + self.ad_l + self.pf_l + self.ss_l + self.fk_l

        self.mvp, self.clown = 0, 0

        self.teammates = {name: 0 for name in player_names}


# Object to represent a game, including its name and score
class Game:
    def __init__(self, name: str, score: str):
        self.name = name
        self.team1_score, self.team2_score = list(map(int, score.split("-")))


# Object to represent a day, including date, teams, score, and games played
class Day:
    def __init__(self, team1: list[Player], team2: list[Player], score: str, games: list[Game]):
        self.team1 = team1
        self.team2 = team2
        self.team1_score, self.team2_score = list(map(int, score.split("-")))
        self.games = games


# HELPER FUNCTIONS


# Checks name (as a string) and returns Player object with that name.
# If player has not been created yet, create new Player object and return it
def get_player(name: str):
    for player in players:
        if player.name == name:
            return player
    new_player = Player(name)
    players.append(new_player)
    return new_player


# Takes in a list of player names and returns a list of Player objects with those names
def init_team(player_names: list[str]):
    player_list = []
    for name in player_names:
        player_list.append(get_player(name))
    return player_list


# Add win to all players on a team for a given game
def add_win(game: str, team: list[Player], amt: int = 1):
    for player in team:
        if game == "PK's":
            player.pk_w += amt
        elif game == "Cross":
            player.cross_w += amt
        elif game == "A/D":
            player.ad_w += amt
        elif game == "P&F":
            player.pf_w += amt
        elif game == "SS":
            player.ss_w += amt
        elif game == "FK's":
            player.fk_w += amt
        elif game == "Days":
            player.days_w += amt
        elif game == "Games":
            player.games_w += amt
        else:
            print(f"Game {game} does not exist!")
            sys.exit(1)


# Add loss to all players on a team for a given game
def add_loss(game: str, team: list[Player], amt: int = 1):
    for player in team:
        if game == "PK's":
            player.pk_l += amt
        elif game == "Cross":
            player.cross_l += amt
        elif game == "A/D":
            player.ad_l += amt
        elif game == "P&F":
            player.pf_l += amt
        elif game == "SS":
            player.ss_l += amt
        elif game == "FK's":
            player.fk_l += amt
        elif game == "Days":
            player.days_l += amt
        elif game == "Games":
            player.games_l += amt
        else:
            print(f"Game {game} does not exist!")
            sys.exit(1)


# Returns list of players minus the one specified
def remove_player(rem_player: Player, player_list: list[Player]) -> list[Player]:
    new_player_list = []
    for player in player_list:
        if player.name != rem_player.name:
            new_player_list.append(player)
    return new_player_list


# Increment teammate frequency dictionaries for each player on each team for each day
def update_team_lists(team: list[Player]):
    for player in team:
        for other_player in remove_player(player, team):
            player.teammates[other_player.name] += 1


# Update an individual stat with appropriate win and loss counts, also check for 0-0 record to avoid division by 0
def update_stat(table, player_num: int, wins: int, losses: int, record: str, pct: str):
    table.at[player_num, record] = f"{wins}-{losses}"
    table.at[player_num, pct] = 0 if wins == 0 and losses == 0 else round(wins / (wins + losses), 4)


# ACTUAL PROGRAM


# Read Excel sheet of days/games, and isolate teams + scores for each
# Optional: season parameter only reads days from a given year (as a 2 digit number)
def read_excel(filename: str, season: int = None):
    # Reset player stats for each season
    global players, player_names
    players = [Player(name) for name in player_names]
    days = []
    days_df = pd.read_excel(filename, sheet_name="Days")
    if not season:
        new_day_check = input("Is there a new field day to input? (y): ").lower()
        if new_day_check == "y":
            # Add new day to dataframe
            nd_date = input("Date: ")
            nd_team1 = input("Team 1 Players: ")
            nd_team2 = input("Team 2 Players: ")
            nd_score = input("Score: ")
            nd_row = [nd_date, nd_team1, nd_team2, nd_score]
            while True:
                nd_game = input("Next Game: ")
                if not nd_game:
                    while len(nd_row) < 11:
                        nd_row.append(None)
                    break
                else:
                    nd_row.append(nd_game)
            mvp = input("MVP: ")
            if mvp == "":
                nd_row.append(None)
            else:
                nd_row.append(mvp)
            clown = input("Clown: ")
            if clown == "":
                nd_row.append(None)
            else:
                nd_row.append(clown)
            row_check = input(f"Confirm new day (y): {nd_row}\n").lower()
            if row_check == "y" or not row_check:
                days_df.loc[len(days_df)] = nd_row
                with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                    days_df.to_excel(writer, sheet_name='Days', index=False, startrow=0, startcol=0)
    
    for index, row in days_df.iterrows():
        if not season or (season and row['Date'].split("/")[-1] == str(season)):
            team1 = init_team(row['Team 1'].split(", "))
            team2 = init_team(row['Team 2'].split(", "))
            score = row['Score']
            if isinstance(row['MVP'], str) is True:
                today_mvp = get_player(row['MVP'])
                today_mvp.mvp += 1
            if isinstance(row['Clown of the Match'], str) is True:
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

# Iterate through list of days, determine winner of each game and increment stats
def parse_days(days_list: list[Day]):
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


# Update Excel sheet with stats
def update_excel(filename: str, season = None):
    stats = pd.read_excel(filename, sheet_name="Stats")
    teams = pd.read_excel(filename, sheet_name="Teams")
    
    sorted_players = sorted(players, key=lambda p: p.name.lower())

    # EXCEL ROW/COLUMN HEADERS NEED TO BE MANUALLY UPDATED IF/WHEN MORE PLAYERS OR GAMES ARE ADDED
    for player in sorted_players:
        wins = [player.days_w, player.games_w, player.pk_w, player.cross_w,
                player.ad_w, player.pf_w, player.ss_w, player.fk_w]
        losses = [player.days_l, player.games_l, player.pk_l, player.cross_l,
                  player.ad_l, player.pf_l, player.ss_l, player.fk_l]
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
                teams.at[(sorted_players.index(player)), teammate[0]] = round(teammate[1] / (player.days_w + player.days_l), 3)
                
    with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
        if season:
            stats.to_excel(writer, sheet_name='20' + str(season) + ' Stats', index=False, startrow=0, startcol=0)
        else:
            stats.to_excel(writer, sheet_name='Stats', index=False, startrow=0, startcol=0)
            teams.to_excel(writer, sheet_name='Teams', index=False, startrow=0, startcol=0)


# Main method to call functions and parse data
def main():
    filename = "./Field_Days.xlsx"
    days = read_excel(filename)
    print("Excel file read")
    parse_days(days)
    print("All days parsed")
    update_excel(filename)
    for i in range(24, 26): # Manually update when more seasons are played
        yr_days = read_excel(filename, i)
        parse_days(yr_days)
        print(f"{len(yr_days)} days parsed for 20{i}")
        update_excel(filename, i)
    print(f"Excel file updated with {len(days)} total field days.")


# On start:
if __name__ == '__main__':
    main()
