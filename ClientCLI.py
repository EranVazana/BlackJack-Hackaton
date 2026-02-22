import socket

from Packets import UDP, TCP
from Card import Card
from GameManager import get_result_as_string

from Logger import get_logger

class Client:
    # Input: none
    # Output: initializes client instance
    # Description: Sets networking defaults, game state, and logger.
    def __init__(self):
        self.CLIENT_UDP_PORT = 13122

        self.server_name = None
        self.server_ip = None
        self.server_port = None
        self.server_addr = None

        self.udp_sock = None
        self.tcp_sock = None

        self.team_name = None
        self.number_of_rounds = 0
        self.game_stats = {TCP.GAME_CLIENT_WIN_RESULT: 0, TCP.GAME_SERVER_WIN_RESULT: 0, TCP.GAME_TIE_RESULT: 0}

        self.player_round_sum = 0

        self.client_logger = get_logger()

    # Input: none
    # Output: sets server address/name fields
    # Description: Listens for UDP offers and saves discovered server info.
    def discover_server(self):
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_sock.bind(('', self.CLIENT_UDP_PORT))

        self.client_logger.info("UDP Client started. Listening for offers...")

        self.server_addr, self.server_name = UDP.receive_response(self.udp_sock)
        self.server_name = '"' + self.server_name.rstrip(b'\x00').decode('utf-8') + '"'
        self.server_ip = self.server_addr[0]
        self.server_port = self.server_addr[1]
        self.client_logger.info(f"Received offer from {self.server_name} at {self.server_ip} on port {self.server_port}")

        self.udp_sock.close()

    # Input: none
    # Output: opens TCP connection
    # Description: Connects to the discovered server using TCP.
    def connect_to_server(self):
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.connect((self.server_ip, self.server_port))
        #self.tcp_sock.timeout(10)
        self.client_logger.info(f"Connected to: {self.server_addr}")

    # Input: input_message (str)
    # Output: user input string
    # Description: Prints a prompt and reads input from the user.
    def get_input_from_user(self, input_message):
        self.client_logger.input(input_message)
        result = input('\033[33m> \033[33m') # \033[33m = Yellow Color
        return result

    # Input: none
    # Output: sends team name and number of rounds
    # Description: Collects settings from user, sends request, and waits for validation.
    def send_game_settings(self):
        while True:
            try:
                self.team_name = self.get_input_from_user("👥 Team name (1–32 chars): ")
                self.number_of_rounds = int(self.get_input_from_user("🔢 Number of rounds (1–255):"))

                self.tcp_sock.sendall(TCP.create_request_message(self.team_name, self.number_of_rounds))
                self.client_logger.info(f"Sent game request to {self.server_addr}")

                validation = TCP.receive_response(self.tcp_sock, 1, TCP.MSG_TYPE_VALIDATION)
                if (not TCP.verify_validation_message(validation, TCP.PAYLOAD_VALID)):
                    self.client_logger.error(f"Invalid Team Name or Round Numbers sent to Server! {self.server_addr}")
                    continue
                else:
                    self.client_logger.info(f"Server - {self.server_addr} approved game request")
                    break
            except:
                self.client_logger.error(f"Invalid Team Name or Round Numbers sent to Server! {self.server_addr}")

    # Input: none
    # Output: "Hittt" or "Stand"
    # Description: Asks the player whether to hit or stand and returns normalized action.
    def ask_decision(self):
        while True:
            decision = self.get_input_from_user("Hit(H) 😈 / Stand(S) 😎:").lower()
            if decision in ("h", 'hit'):
                return "Hittt"
            if decision in ('s', 'stand'):
                return "Stand"
            print("Please type Hit or Stand")

    # Input: round_num (int)
    # Output: none
    # Description: Receives initial cards for a round and initializes player/dealer state.
    def init_round(self, round_num):
        self.client_logger.info(f"{self.server_addr} --- Starting new round {round_num} of {self.number_of_rounds} ---")
        self.player_round_sum = 0

        for card_number in range(4):
            payload = TCP.receive_response(self.tcp_sock, TCP.MSG_PAYLOAD_CARD_SIZE, TCP.MSG_TYPE_PAYLOAD)
            card = Card.decode_from_bytes(payload)

            match(card_number):
                case 0:
                    self.client_logger.info(f"{self.server_addr} - Dealer card (visible): {card.emoji_str()}")
                    self.dealer_revealed_card = card
                case 1:
                    self.client_logger.info(f"{self.server_addr} - Dealer card (hidden): rank=? suit=?")
                case 2:
                    self.client_logger.info(f"{self.server_addr} - Your card #1: {card.emoji_str()}")
                    self.player_round_sum += card.value
                case 3:
                    self.client_logger.info(f"{self.server_addr} - Your card #2: {card.emoji_str()}")
                    self.player_round_sum += card.value

    # Input: none
    # Output: round result constant
    # Description: Plays the client turn: hit/stand loop and bust detection.
    def handle_client_turn(self):
        result = TCP.receive_response(self.tcp_sock, TCP.MSG_PAYLOAD_RESULT_SIZE, TCP.MSG_TYPE_PAYLOAD)
        result = int.from_bytes(result, byteorder='big')
        if (result == TCP.GAME_SERVER_WIN_RESULT):
            self.client_logger.info(f"{self.server_addr} - ROUND LOST: Player busted")
            return TCP.GAME_SERVER_WIN_RESULT
        else:
            self.client_logger.info(f"{self.server_addr} --- Starting player turn ---")

        while True:
            self.client_logger.info(f"{self.server_addr} - Player current card sum is: {self.player_round_sum}")
            action = self.ask_decision()

            if action == "Hittt":
                self.client_logger.info(f"{self.server_addr} - Player decision: hit")
                self.tcp_sock.sendall(TCP.create_payload_response(action))

                payload = TCP.receive_response(self.tcp_sock, TCP.MSG_PAYLOAD_CARD_SIZE, TCP.MSG_TYPE_PAYLOAD)
                card = Card.decode_from_bytes(payload)
                self.client_logger.info(f"{self.server_addr} - Received new card: {card.emoji_str()}")
                self.player_round_sum += card.value

                result = TCP.receive_response(self.tcp_sock, TCP.MSG_PAYLOAD_RESULT_SIZE, TCP.MSG_TYPE_PAYLOAD)
                result = int.from_bytes(result, byteorder='big')
                if (result == TCP.GAME_SERVER_WIN_RESULT):
                    self.client_logger.info(f"{self.server_addr} - ROUND LOST: Player busted")
                    return TCP.GAME_SERVER_WIN_RESULT

            elif action == "Stand":
                self.client_logger.info(f"{self.server_addr} - Player chose to stand")
                self.tcp_sock.sendall(TCP.create_payload_response(action))
                return TCP.GAME_ROUND_NOT_OVER

    # Input: none
    # Output: final round result constant
    # Description: Handles dealer turn updates received from server until round ends.
    def handle_dealer_turn(self):
        self.client_logger.info(f"{self.server_addr} --- Starting dealer turn ---")

        self.client_logger.info(f"{self.server_addr} - Dealer revealed card: {self.dealer_revealed_card.emoji_str()}")
        payload = TCP.receive_response(self.tcp_sock, TCP.MSG_PAYLOAD_CARD_SIZE, TCP.MSG_TYPE_PAYLOAD)
        hidden_card = Card.decode_from_bytes(payload)
        self.client_logger.info(f"{self.server_addr} - Revealing dealer's hidden card: {hidden_card.emoji_str()}")
        
        while True:
            result = TCP.receive_response(self.tcp_sock, TCP.MSG_PAYLOAD_RESULT_SIZE, TCP.MSG_TYPE_PAYLOAD)
            result = int.from_bytes(result, byteorder='big')
            if result != TCP.GAME_ROUND_NOT_OVER:
                self.client_logger.info(f"{self.server_addr} --- Round ended! Result: {get_result_as_string(result)} ---")
                return result
                
            self.client_logger.info(f"{self.server_addr} - Dealer choses to draw another card.")

            payload = TCP.receive_response(self.tcp_sock, TCP.MSG_PAYLOAD_CARD_SIZE, TCP.MSG_TYPE_PAYLOAD)
            card = Card.decode_from_bytes(payload)
            self.client_logger.info(f"{self.server_addr} - Dealer drew card: {card.emoji_str()}")

    # Input: round_num (int)
    # Output: none
    # Description: Plays a full round and updates win/loss/tie stats.
    def play_round(self, round_num):
        self.init_round(round_num)

        client_result = self.handle_client_turn()
        if client_result == TCP.GAME_SERVER_WIN_RESULT:
            self.client_logger.info(f"{self.server_addr} --- Round ended! Result: SERVER WINS! ---")
            self.game_stats[TCP.GAME_SERVER_WIN_RESULT] += 1
        else:
            final_result = self.handle_dealer_turn()
            self.game_stats[final_result] += 1

        self.client_logger.info(f"{self.server_addr} --- Round {round_num} complete ---\n")

    # Input: none
    # Output: none
    # Description: Plays all rounds for the game and prints final win rate.
    def play_game(self):
        self.client_logger.info(f"{self.server_addr} --- Game started for team: {self.team_name} with {self.number_of_rounds} rounds ---")

        for i in range(self.number_of_rounds):
            self.play_round(i + 1)

        self.client_logger.info(f"{self.server_addr} --- Finished playing {self.number_of_rounds} rounds, win rate: {self.game_stats[TCP.GAME_CLIENT_WIN_RESULT] / self.number_of_rounds}")
                                
    # Input: none
    # Output: none
    # Description: Runs full client flow with cleanup and error handling.
    def start_client(self):
        try:
            self.discover_server()
            self.connect_to_server()
            self.send_game_settings()
            self.play_game()
        except ConnectionResetError:
            self.client_logger.error("Connection lost to server")
        except Exception as ex:
            self.client_logger.error(f"Error: {ex}")
        finally:
            if self.tcp_sock:
                self.tcp_sock.close()
            self.client_logger.info(f"Disconnected from server: {self.server_addr}")

# Input: none
# Output: none
# Description: Entry point that creates a client and starts the game.
def main():
    client = Client()
    client.start_client()

if __name__ == "__main__":
    main()