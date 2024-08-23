import sys
import csv
from enum import StrEnum
from scipy.optimize import linprog
from random import shuffle


class Country(StrEnum):
    ABYSSINIA = "Abyssinia"
    AJUURAN = "Ajuuran"
    ATHAPASCA = "Athapasca"
    AUSTRIA = "Austria"
    AYMARA = "Aymara"
    AYUTTHAYA = "Ayutthaya"
    ENGLAND = "England"
    FRANCE = "France"
    INUIT = "Inuit"
    KONGO = "Kongo"
    MALI = "Mali"
    MAPUCHETEHUELCHE = "Mapuche-Tehuelche"
    MING = "Ming"
    MUGHAL = "Mughal"
    NETHERLANDS = "Netherlands"
    OTTOMAN = "Ottoman"
    POLANDLITHUANIA = "Poland-Lithuania"
    PORTUGAL = "Portugal"
    QING = "Qing"
    RUSSIA = "Russia"
    SAFAVID = "Safavid"
    SPAIN = "Spain"
    SWEDEN = "Sweden"
    TOKUGAWA = "Tokugawa"
    UTESHOSHONE = "Ute-Shoshone"


# Play with these numbers, it tries to minimize the total.
# NO is for countries the player absolutely doesn't want to play (not applicable to impdip)
FIRST_PICK = 1
SECOND_PICK = 3
THIRD_PICK = 9
FOURTH_PICK = 27
FIFTH_PICK = 81
UNPICKED = 1000
NO = 9999999


# Get player preferences
# ex:
# preferences = {
#     '_bumble': { Country.ABYSSINIA: FIRST_PICK, Country.PERSIA: SECOND_PICK },
#     'icecream_guy': { Country.ENGLAND: FIRST_PICK }
# }
preferences = dict()
game_requirement = dict()
with open('assets/beginner.csv', newline='') as csvfile:
    preferences_reader = csv.DictReader(csvfile)
    for player in preferences_reader:
        username = player['Discord Username']

        game = player['Game']
        if game:
            game_requirement[username] = int(game) - 1

        preferences[username] = {}
        if player['Select Here If You Have No Preferences']:
            continue

        for country in Country:
            choice = player[f"Rank Your Country Choices [{country}]"]
            if not choice.strip():
                continue
            if choice == "1st":
                preference = FIRST_PICK
            elif choice == "2nd":
                preference = SECOND_PICK
            elif choice == "3rd":
                preference = THIRD_PICK
            elif choice == "4th":
                preference = FOURTH_PICK
            elif choice == "5th":
                preference = FIFTH_PICK
            else:
                raise ValueError(f"Could not parse choice {choice} for country {country} for player {username}")
            preferences[username][country] = preference


num_countries = len(Country)
if len(preferences) % num_countries != 0:
    print("Number of players does not match number of countries", file=sys.stderr)
    print("Filling in dummy players")
    for i in range(num_countries - (len(preferences) % num_countries)):
        preferences['dummy' + str(i)] = {}
num_games = len(preferences) // num_countries
print(f"{num_games} game(s) will be run")


# Shuffle keys since first players get precedence
players = list(preferences.keys())
shuffle(players)


# player_0_country_0_game_0, player_0_country_0_game_1, player_0_country_1_game_0, ...
assignment_coefficients = [preferences[player].setdefault(country, UNPICKED)
                           for player in players
                           for country in Country
                           for game in range(num_games)]
must_have_one_country_condition_lhs = [
    ([0]*num_countries*num_games*i + [1]*num_countries*num_games + [0]*num_countries*num_games*(len(players)-i-1))
    for i in range(len(players))
]
must_have_one_country_condition_rhs = [1]*len(players)
cant_have_same_country_condition_lhs = [
    ([0]*i + [1] + [0]*(len(players)-i-1)) * len(players)
    for i in range(num_countries*num_games)
]
cant_have_same_country_condition_rhs = [1]*num_countries*num_games
must_be_in_specific_game_lhs = []
must_be_in_specific_game_rhs = []
for game_requirement_player in game_requirement:
    player_index = players.index(game_requirement_player)
    game = game_requirement[game_requirement_player]
    must_be_in_specific_game_lhs.append(
        [0]*player_index*num_countries*num_games +
        ([0]*game + [1] + [0]*(num_games-game-1))*num_countries +
        [0]*(len(players)-player_index-1)*num_countries*num_games)
    must_be_in_specific_game_rhs.append(1)

assignment = linprog(assignment_coefficients,
                     A_eq=must_have_one_country_condition_lhs +
                          cant_have_same_country_condition_lhs +
                          must_be_in_specific_game_lhs,
                     b_eq=must_have_one_country_condition_rhs +
                          cant_have_same_country_condition_rhs +
                          must_be_in_specific_game_rhs,
                     bounds=[(0, 1)], method="highs", integrality=True)

print(assignment.message)

player_assignments = dict()
scrap_countries = []
unassigned_players = []
for index, val in enumerate(assignment.x):
    if val == 1.0:
        player = players[index // (num_countries * num_games)]
        country = list(Country)[(index % (num_countries * num_games)) // num_games]
        game = index % num_games
        weight = preferences[player][country]
        country_and_game = f"{country}, game {game}"
        if weight == UNPICKED:
            scrap_countries.append(country_and_game)
            unassigned_players.append(player)
        player_assignments[player] = {"country": country, "game": game, "weight": weight}
        # print(f"{player} -> {country_and_game} (weight: {weight})")
print(len(scrap_countries), sorted(scrap_countries), sorted(unassigned_players), sep='\n')
for player in sorted(player_assignments):
    if player_assignments[player]["weight"] != UNPICKED:
        print(player, player_assignments[player])