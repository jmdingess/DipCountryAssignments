import itertools
import sys
import csv
from enum import StrEnum, Enum
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


class ExperienceLevel(Enum):
    EXPERIENCED = 1
    MIXED = 2
    BEGINNER = 4


# Play with these numbers, it tries to minimize the total.
# NO is for countries the player absolutely doesn't want to play (not applicable to impdip)
class PreferenceWeights(Enum):
    FIRST_PICK = 1
    SECOND_PICK = 3
    THIRD_PICK = 9
    FOURTH_PICK = 27
    FIFTH_PICK = 81
    UNPICKED = 1000
    NO = 9999999


class Player:
    def __init__(self):
        self.username = None
        self.preferences = dict()
        self.scrap_weight = PreferenceWeights.UNPICKED
        self.game_levels = set()
        self.play_with = None
        self.play_without = []

    def __str__(self):
        return f"Player {self.username}"


# Parse player preferences from csv
players = dict()
with open('assets/allclean.csv', newline='') as playersfile:
    players_reader = csv.DictReader(playersfile)
    for player_row in players_reader:
        player = Player()
        player.username = player_row['Discord Username'].strip()

        skill_levels = player_row[
            'What skill levels would you like to play in? (Beginner and Experienced will be prioritized)'].split(',')
        skill_levels = [level.strip() for level in skill_levels]
        if "Experienced" in skill_levels:
            player.game_levels.add(ExperienceLevel.EXPERIENCED)
        if "Mixed" in skill_levels:
            player.game_levels.add(ExperienceLevel.MIXED)
        if "Beginner" in skill_levels:
            player.game_levels.add(ExperienceLevel.BEGINNER)
        if player.game_levels == {ExperienceLevel.BEGINNER, ExperienceLevel.EXPERIENCED}:
            print(f"Player {player.username} chose nonsense; setting them to all")
            player.game_levels = {level for level in ExperienceLevel}
        if player.game_levels == {}:
            print(f"Player {player.username} chose no game levels; setting them to all")
            player.game_levels = {level for level in ExperienceLevel}

        player.play_with = player_row[
            'Is there a person you desperately want to play with? (You may list up to one)'].strip()

        play_without = player_row['Are there any people you refuse to play with?'].split(',')
        play_without = [user.strip() for user in play_without]
        player.play_without = play_without

        if not player_row['Select Here If You Have No Preferences']:
            for country in Country:
                choice = player_row[f"Rank Your Country Choices [{country}]"]
                if not choice.strip():
                    continue
                if choice == "1st":
                    preference = PreferenceWeights.FIRST_PICK
                elif choice == "2nd":
                    preference = PreferenceWeights.SECOND_PICK
                elif choice == "3rd":
                    preference = PreferenceWeights.THIRD_PICK
                elif choice == "4th":
                    preference = PreferenceWeights.FOURTH_PICK
                elif choice == "5th":
                    preference = PreferenceWeights.FIFTH_PICK
                else:
                    raise ValueError(
                        f"Could not parse choice {choice} for country {country} for player {player.username}")
                player.preferences[country] = preference
        # If only a first pick is chosen, then everything else is a second pick. So on...
        player.scrap_weight = list(PreferenceWeights)[len(player.preferences)]
        if player.username == "Captainmeme" or player.username == "Ezio":
            player.preferences = { Country.SPAIN: PreferenceWeights.FIRST_PICK }
            player.scrap_weight = PreferenceWeights.NO
            player.game_levels = { ExperienceLevel.EXPERIENCED }

        players[player.username.lower()] = player

# Quick sanity check
country_set = set(Country)
for username in players:
    player = players[username]
    for country in Country:
        if country in player.preferences and country in country_set:
            country_set.remove(country)
    if len(country_set) == 0:
        break
if len(country_set) != 0:
    print(f"{country_set} countries are never chosen as a preference -- Check for spelling typos!", file=sys.stderr)

# Fit players that want to play with each other into the same game level (if it's mutual)
# i.e. if A wants to play with B, but B not with A, game level doesn't change
# but if A and B want to play together, combine their game levels
for username in players:
    if player.play_with:
        combined_game_levels = player.game_levels
        seen = [player.username]
        combined_play_without = set()
        for unwanted_player in player.play_without:
            combined_play_without.add(unwanted_player.lower())
        other_player = players.get(player.play_with.lower(), None)
        if other_player is None:
            print(f"{player.username} wanted to play with {player.play_with} who didn't sign up")
        while other_player is not None:
            if other_player.username in seen:
                # Check if the entire group is self-referential
                # It could be A -> B, B -> C, C -> B, in which case A isn't really a part of the group
                if other_player.username != seen[0]:
                    break
                # print(f"self-referential group {seen} has combined level {combined_game_levels}")
                if len(combined_game_levels) == 0:
                    print(f"self-referential group {seen} has no combined level", file=sys.stderr)
                    break
                for grouped_player in seen:
                    players[grouped_player.lower()].game_levels = combined_game_levels
                break

            seen.append(other_player.username)
            combined_game_levels = combined_game_levels & other_player.game_levels
            for unwanted_player in other_player.play_without:
                combined_play_without.add(unwanted_player.lower())
            if len(set([seen_player.lower() for seen_player in seen]) & combined_play_without) != 0:
                print(f"Players {seen} want to play with AND without {set([seen_player.lower() for seen_player in seen]) & combined_play_without}!")
                exit(1)
            other_player = players.get(other_player.play_with.lower(), None)

num_countries = len(Country)
if len(players) % num_countries != 0:
    print("Number of players does not match number of countries", file=sys.stderr)
    print("Filling in dummy players")
    for i in range(num_countries - (len(players) % num_countries)):
        dummy_player = Player()
        dummy_player.game_levels = {ExperienceLevel.BEGINNER, ExperienceLevel.MIXED, ExperienceLevel.EXPERIENCED}
        dummy_player.username = f"dummy{str(i)}"
        players[dummy_player.username.lower()] = dummy_player
num_games = len(players) // num_countries
print(f"{num_games} game(s) will be run")

game_level_counts = {game_level_bitcode: 0 for game_level_bitcode in range(2 ** len(ExperienceLevel))}
for username in players:
    player = players[username]
    game_level_bitcode = sum(game_level.value for game_level in player.game_levels)
    game_level_counts[game_level_bitcode] += 1
# Fill games; I think a lot of this ends up being useless
for base_level in [{ExperienceLevel.BEGINNER}, {ExperienceLevel.EXPERIENCED},
                   {ExperienceLevel.BEGINNER, ExperienceLevel.MIXED},
                   {ExperienceLevel.MIXED, ExperienceLevel.EXPERIENCED}]:
    surplus = game_level_counts[sum(level.value for level in base_level)] % num_countries
    if surplus == 0:
        continue
    required_players = num_countries - surplus
    for take_from_level in [base_level | {ExperienceLevel.MIXED},
                            {ExperienceLevel.BEGINNER, ExperienceLevel.MIXED, ExperienceLevel.EXPERIENCED},
                            {ExperienceLevel.MIXED}]:
        if take_from_level == base_level:
            continue
        available = min(game_level_counts[sum(level.value for level in take_from_level)], required_players)
        required_players -= available
        game_level_counts[sum(level.value for level in base_level)] += available
        game_level_counts[sum(level.value for level in take_from_level)] -= available
        if required_players == 0:
            break
    if required_players != 0:
        print("Not enough mixed players to fill games! Experienced and Beginner will need to mix - bad news", file=sys.stderr)
        exit(1)
beginner_game_count = game_level_counts[ExperienceLevel.BEGINNER.value] // num_countries
beginner_mixed_game_count = game_level_counts[ExperienceLevel.BEGINNER.value + ExperienceLevel.MIXED.value] // num_countries
experienced_mixed_game_count = game_level_counts[ExperienceLevel.EXPERIENCED.value + ExperienceLevel.MIXED.value] // num_countries
experienced_game_count = game_level_counts[ExperienceLevel.EXPERIENCED.value] // num_countries
mixed_game_count = num_games - (beginner_game_count + beginner_mixed_game_count + experienced_mixed_game_count + experienced_game_count)
print(f"{beginner_game_count} beginner games")
print(f"{beginner_mixed_game_count} beginner/mixed games")
print(f"{mixed_game_count} mixed games")
print(f"{experienced_mixed_game_count} experienced/mixed games")
print(f"{experienced_game_count} experienced games")
assert 0 <= mixed_game_count, "Something went horribly wrong"


# Shuffle keys since first players get precedence
usernames = list(players.keys())
shuffle(usernames)

# player_0_country_0_game_0, player_0_country_0_game_1, player_0_country_1_game_0, ...
assignment_coefficients = [players[username].preferences.get(country, player.scrap_weight).value
                           for username in usernames
                           for country in Country
                           for game in range(num_games)]

# must_have_one_country_condition_lhs = [
#     ([0] * num_countries * num_games * i + [1] * num_countries * num_games + [0] * num_countries * num_games * (
#                 len(usernames) - i - 1))
#     for i in range(len(usernames))
# ]
# must_have_one_country_condition_rhs = [1] * len(usernames)

cant_have_same_country_condition_lhs = [
    ([0] * i + [1] + [0] * ((num_countries * num_games) - i - 1)) * len(usernames)
    for i in range(num_countries * num_games)
]
cant_have_same_country_condition_rhs = [1] * num_countries * num_games

must_follow_game_level_lhs = []  # Doubles as must_have_one_county_condition
must_follow_game_level_rhs = []
for index, username in enumerate(usernames):
    player = players.get(username)
    game_levels = player.game_levels
    assert len(game_levels) != 0
    player_game_condition = [1] * num_games
    if ExperienceLevel.BEGINNER in game_levels:
        player_game_condition[-(experienced_game_count + experienced_mixed_game_count):] = (
                [0] * (experienced_game_count + experienced_mixed_game_count))
    if ExperienceLevel.MIXED not in game_levels:
        # player_game_condition[beginner_game_count + beginner_mixed_game_count:-(experienced_game_count + experienced_mixed_game_count)] = (
        #         [0] * mixed_game_count)
        player_game_condition[beginner_game_count:-experienced_game_count] = (
                [0] * (num_games - (beginner_game_count + experienced_game_count)))
    if ExperienceLevel.EXPERIENCED in game_levels:
        player_game_condition[:beginner_game_count + beginner_mixed_game_count] = (
                [0] * (beginner_game_count + beginner_mixed_game_count))
    if game_levels == {ExperienceLevel.MIXED}:
        player_game_condition = ([0] * beginner_game_count +
                                 [1] * (num_games - (beginner_game_count + experienced_game_count)) +
                                 [0] * experienced_game_count)
    if (game_levels == {ExperienceLevel.BEGINNER, ExperienceLevel.MIXED, ExperienceLevel.EXPERIENCED} or
            game_levels == {ExperienceLevel.BEGINNER, ExperienceLevel.EXPERIENCED}):
        player_game_condition = [1] * num_games
    assert len(player_game_condition) == num_games
    must_follow_game_level_lhs.append(
        [0] * index * num_countries * num_games +
        player_game_condition * num_countries +
        [0] * (len(usernames) - index - 1) * num_countries * num_games)
    must_follow_game_level_rhs.append(1)

respect_play_without_preferences_lhs = []
respect_play_without_preferences_rhs = []
for index, username in enumerate(usernames):
    player = players.get(username)
    if not player.play_without:
        continue
    for other_player_name in player.play_without:
        try:
            other_player_index = usernames.index(other_player_name.lower())
        except ValueError:
            continue
        for game in range(num_games):
            respect_play_without_preferences_lhs.append(  # At most one of these players in each game
                [0] * min(index, other_player_index) * num_countries * num_games +
                ([0] * game + [1] + [0] * (num_games - game - 1)) * num_countries +
                [0] * (abs(other_player_index - index) - 1) * num_countries * num_games +
                ([0] * game + [1] + [0] * (num_games - game - 1)) * num_countries +
                [0] * (len(usernames) - max(index, other_player_index) - 1) * num_countries * num_games
            )
            respect_play_without_preferences_rhs.append(1)

play_with_lhs = []
play_with_rhs = []
new_coefficients = []
for index, username in enumerate(usernames):
    player = players[username]
    if not player.play_with:
        continue
    if player.play_with.lower() not in usernames:
        continue
    other_player_index = usernames.index(player.play_with.lower())
    for game in range(num_games):
        new_coefficients += [10_000, 10_000]
        for constraint in play_with_lhs:
            constraint += [0, 0]
        play_with_lhs.append(
            [0] * min(index, other_player_index) * num_countries * num_games +
            ([0] * game + [1] + [0] * (num_games - game - 1)) * num_countries +
            [0] * (abs(other_player_index - index) - 1) * num_countries * num_games +
            ([0] * game + [-1] + [0] * (num_games - game - 1)) * num_countries +
            [0] * (len(usernames) - max(index, other_player_index) - 1) * num_countries * num_games +
            [0] * (len(new_coefficients) - 2) + [-1] + [0]
        )
        play_with_lhs.append(
            [0] * min(index, other_player_index) * num_countries * num_games +
            ([0] * game + [-1] + [0] * (num_games - game - 1)) * num_countries +
            [0] * (abs(other_player_index - index) - 1) * num_countries * num_games +
            ([0] * game + [1] + [0] * (num_games - game - 1)) * num_countries +
            [0] * (len(usernames) - max(index, other_player_index) - 1) * num_countries * num_games +
            [0] * (len(new_coefficients) - 2) + [0] + [-1]
        )
        play_with_rhs += [0, 0]
for constraint in cant_have_same_country_condition_lhs + must_follow_game_level_lhs + respect_play_without_preferences_lhs:
    constraint += [0] * len(new_coefficients)

assignment = linprog(assignment_coefficients + new_coefficients,
                     A_eq=#must_have_one_country_condition_lhs +
                          cant_have_same_country_condition_lhs +
                          must_follow_game_level_lhs,
                     b_eq=#must_have_one_country_condition_rhs +
                          cant_have_same_country_condition_rhs +
                          must_follow_game_level_rhs,
                     A_ub=respect_play_without_preferences_lhs + play_with_lhs,
                     b_ub=respect_play_without_preferences_rhs + play_with_rhs,
                     bounds=(0, 1), method="highs", integrality=[1] * len(assignment_coefficients + new_coefficients))

print(assignment.message)

player_assignments = dict()
scrap_countries_by_game = {game_number: [] for game_number in range(num_games)}
unassigned_players_by_game = {game_number: [] for game_number in range(num_games)}
for index, val in enumerate(assignment.x):
    if len(assignment_coefficients) <= index:
        break
    if val == 1.0:
        username = usernames[index // (num_countries * num_games)]
        country = list(Country)[(index % (num_countries * num_games)) // num_games]
        game = index % num_games
        player = players.get(username)
        country_and_game = f"{country}, game {game}"
        if country not in player.preferences:
            scrap_countries_by_game[game].append(country)
            unassigned_players_by_game[game].append(player.username)
        else:
            print(f"{player.username} -> {country_and_game} (weight: {player.preferences.get(country).value})")
        player_assignments[player.username] = {"country": country, "game": game, "weight": player.preferences.get(country, None)}
for game_number in range(num_games):
    print(game_number, sorted(scrap_countries_by_game[game_number]), sorted(unassigned_players_by_game[game_number]), sep='\n\t')
for player_name in sorted(player_assignments):
    if player_assignments[player_name]["weight"] is not None:
        print(player_name, player_assignments[player_name])

with open('outputs/assignments.csv', 'w', newline='') as csvfile:
    assignment_writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
    for player_name in sorted(player_assignments):
        player_assignment = player_assignments[player_name]
        assignment_writer.writerow([player_name, player_assignment["game"],
                                    player_assignment["country"].value, player_assignment["weight"]])

with open('outputs/scrap_countries.csv', 'w', newline='') as csvfile:
    scrap_writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
    for game in range(num_games):
        scrap_writer.writerow([country.value for country in sorted(scrap_countries_by_game[game])])

with open('outputs/unassigned_players.csv', 'w', newline='') as csvfile:
    unassigned_writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
    for game in range(num_games):
        unassigned_writer.writerow(sorted(unassigned_players_by_game[game]))
