from Card import Card
from Packets import TCP
from TinyDBWrapper import TinyDBWrapper
import random
import time


class ServerGameManager:
    # Input: number_of_rounds (int), team_name (str)
    # Output: initializes game manager instance
    # Description: Manages game state, statistics, and timing for a single client.
    def __init__(self, number_of_rounds, team_name):
        self.team_name = team_name
        self.number_of_rounds = number_of_rounds
        self.current_round = 0

        self.game_stats = {
            TCP.GAME_CLIENT_WIN_RESULT: 0,
            TCP.GAME_SERVER_WIN_RESULT: 0,
            TCP.GAME_TIE_RESULT: 0
        }

        self.client_game_cards = []
        self.server_game_cards = []

        self.client_round_busts = []
        self.server_round_busts = []

        self.client_response_time_in_round = []
        self.client_response_time_in_game = []

        self.total_game_time = None
        
    # Input: none
    # Output: list of Card objects
    # Description: Creates a fresh deck of cards.
    def create_deck(self):
        return Card.create_deck()
    
    # Input: none
    # Output: none
    # Description: Randomly shuffles the current deck.
    def shuffle_deck(self):
        random.shuffle(self.deck)

    # Input: none
    # Output: Card object
    # Description: Removes and returns the top card from the deck.
    def pop_card(self):
        return self.deck.pop()
    
    # Input: none
    # Output: none
    # Description: Initializes all values for a new round and deals starting cards.
    def init_round(self):
        self.deck = self.create_deck()
        self.shuffle_deck()

        self.current_round_client_sum = 0
        self.current_round_server_sum = 0

        self.server_cards = []
        self.client_cards = []
    
        client_card_1 = self.pop_card()
        client_card_2 = self.pop_card()
        server_card_1 = self.pop_card()
        server_card_2 = self.pop_card()

        self.current_round_client_cards = [client_card_1, client_card_2]
        self.current_round_server_cards = [server_card_1, server_card_2]

        self.current_round_client_sum = client_card_1.value + client_card_2.value
        self.current_round_server_sum = server_card_1.value + server_card_2.value

        self.client_response_time_in_round = []

    # Input: card (Card)
    # Output: none
    # Description: Adds a card to the client hand and updates the sum.
    def add_client_card(self, card):
        self.client_cards.append(card)
        self.current_round_client_sum += card.value

    # Input: card (Card)
    # Output: none
    # Description: Adds a card to the dealer hand and updates the sum.
    def add_server_card(self, card):
        self.server_cards.append(card)
        self.current_round_server_sum += card.value

    # Input: response_time (float)
    # Output: none
    # Description: Records client response time for the current round.
    def add_client_response_time(self, response_time):
        self.client_response_time_in_round.append(response_time)

    # Input: none
    # Output: none
    # Description: Records that the client busted in the current round.
    def add_client_bust(self):
        self.client_round_busts.append(self.current_round)

    # Input: none
    # Output: none
    # Description: Records that the dealer busted in the current round.
    def add_server_bust(self):
        self.server_round_busts.append(self.current_round)

    # Input: none
    # Output: bool
    # Description: Checks whether the client exceeded 21.
    def is_client_busted(self):
        return self.current_round_client_sum > 21

    # Input: none
    # Output: bool
    # Description: Checks whether the dealer exceeded 21.
    def is_server_busted(self):
        return self.current_round_server_sum > 21

    # Input: none
    # Output: none
    # Description: Starts measuring total game duration.
    def start_timer(self):
        self.total_game_time = time.time()

    # Input: none
    # Output: none
    # Description: Stops timer and stores total game time.
    def stop_timer(self):
        self.total_game_time = time.time() - self.total_game_time
    
    # Input: none
    # Output: round result constant
    # Description: Determines the winner of the current round.
    def get_round_result(self):
        if self.current_round_client_sum < self.current_round_server_sum:
            return TCP.GAME_SERVER_WIN_RESULT
        elif self.current_round_client_sum > self.current_round_server_sum:
            return TCP.GAME_CLIENT_WIN_RESULT
        else:
            return TCP.GAME_TIE_RESULT
    
    # Input: result (int)
    # Output: none
    # Description: Updates overall game statistics after a round ends.
    def update_game_stats(self, result):
        self.game_stats[result] += 1
        self.client_game_cards.append(
            [card.to_dict() for card in self.current_round_client_cards]
        )
        self.server_game_cards.append(
            [card.to_dict() for card in self.current_round_server_cards]
        )
        self.client_response_time_in_game.append(self.client_response_time_in_round)

    # Input: none
    # Output: dict
    # Description: Converts full game data into a dictionary for storage.
    def to_dict(self) -> dict:
        return {
            "team_name": self.team_name,
            "number_of_rounds": self.number_of_rounds,
            "game_stats": self.game_stats,
            "client_game_cards": self.client_game_cards,
            "server_game_cards": self.server_game_cards,
            "client_round_busts": self.client_round_busts,
            "server_round_busts": self.server_round_busts,
            "client_response_time_in_game": self.client_response_time_in_game,
            "total_game_time": self.total_game_time
        }
    
    # Input: none
    # Output: none
    # Description: Saves game results to the database.
    def save_to_db(self):
        db = TinyDBWrapper()
        db.insert(self.to_dict())
        db.flush()

    # Input: other (ServerGameManager)
    # Output: bool
    # Description: Compares two games by team name and number of rounds.
    def __eq__(self, other):
        return (
            self.team_name == other.team_name and
            self.number_of_rounds == other.number_of_rounds
        )


# Input: result (int)
# Output: string
# Description: Converts a round result constant to a readable string.
@staticmethod
def get_result_as_string(result):
    result_map = {
        TCP.GAME_TIE_RESULT: "TIE!",
        TCP.GAME_SERVER_WIN_RESULT: "SERVER WINS!",
        TCP.GAME_CLIENT_WIN_RESULT: "CLIENT WINS!"
    }
    return result_map[result]
