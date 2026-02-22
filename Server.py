import socket
import struct

import time
import threading

from Card import Card
from Packets import UDP, TCP, get_local_ip
from GameManager import ServerGameManager, get_result_as_string

from Logger import get_logger

class Server:
    # Input: none
    # Output: initializes server instance
    # Description: Sets server configuration, ports, logger, and active game storage.
    def __init__(self):
        self.SERVER_NAME = "Cool Server Name"
        self.SERVER_HOST = get_local_ip()
        self.SERVER_TCP_PORT = 8080 

        self.SERVER_UDP_BROADCAST_PORT = 13122
        self.SERVER_BROADCAST_INTERVAL = 1

        self.active_games_map = {}

        self.server_logger = get_logger()

    # Input: none
    # Output: continuously sends UDP broadcast messages
    # Description: Periodically broadcasts server availability to clients via UDP.
    def broadcast_offers(self):
        server_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        server_udp_socket.bind((self.SERVER_HOST, self.SERVER_UDP_BROADCAST_PORT))

        self.server_logger.info("UDP Offer Server started. Broadcasting offers...")

        offer_message = UDP.create_offer_message(self.SERVER_TCP_PORT, self.SERVER_NAME)
        while True:
            server_udp_socket.sendto(offer_message, ('<broadcast>', self.SERVER_UDP_BROADCAST_PORT))
            time.sleep(self.SERVER_BROADCAST_INTERVAL)

    # Input: none
    # Output: accepts incoming TCP connections
    # Description: Listens for TCP clients and spawns a thread per connection.
    def accept_client_connections(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.SERVER_HOST, self.SERVER_TCP_PORT))
        server_socket.listen()  

        self.server_logger.info(f"TCP server listening on port:{self.SERVER_TCP_PORT}")

        while True:
            client_socket, client_addr = server_socket.accept()  
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_addr), daemon=True)
            client_thread.start()

    # Input: client socket, client address
    # Output: none
    # Description: Manages full lifecycle of a connected client and its game.
    def handle_client(self, client_socket, client_addr):
        self.server_logger.info(f"Connected to: {client_addr}")
        try:
            #client_socket.settimeout(10.0)
            num_rounds , team_name_bytes = self.get_game_settings_from_client(client_socket, client_addr)
            self.active_games_map[client_addr] = ServerGameManager(number_of_rounds=num_rounds, team_name=team_name_bytes)
            self.handle_client_game(client_socket, client_addr, self.active_games_map[client_addr])
                                    
        except ConnectionResetError:
            pass
        except Exception as ex:
            self.server_logger.error(f"Error at handling client {client_addr}: with {ex}")
        finally:
            client_socket.close()
            if client_addr in self.active_games_map:
                del self.active_games_map[client_addr]
            self.server_logger.info(f"Disconnected client: {client_addr}")

    # Input: client socket, client address
    # Output: (num_rounds, team_name)
    # Description: Receives and validates initial game request from client.
    def get_game_settings_from_client(self, client_socket, client_addr):
        while True:
            client_data = TCP.receive_response(client_socket, TCP.MSG_REQUEST_SIZE, TCP.MSG_TYPE_REQUEST)
            self.server_logger.info(f"Received game request from {client_addr}")
            num_rounds, team_name = client_data[0], client_data[1:].rstrip(b'\x00').decode('utf-8')
            if (not str(num_rounds).isdigit() or num_rounds < 1):
                self.server_logger.warning(f"Invalid number of rounds received from {client_addr}: {num_rounds}")
                client_socket.sendall(TCP.create_payload_validation(TCP.PAYLOAD_NOT_VALID))
                continue
            else:
                client_socket.sendall(TCP.create_payload_validation(TCP.PAYLOAD_VALID))
                return num_rounds, team_name

    # Input: client socket, client address, game manager
    # Output: none
    # Description: Runs all game rounds for a client and records results.
    def handle_client_game(self, client_socket, client_addr, server_game_manager):
        self.server_logger.info(f"{client_addr} --- Game started for team: {server_game_manager.team_name} with {server_game_manager.number_of_rounds} rounds ---")
        server_game_manager.start_timer()
        for i in range(server_game_manager.number_of_rounds):
            self.server_logger.info(f"{client_addr} --- Starting new round {i + 1} of {server_game_manager.number_of_rounds} ---")

            self.init_client_game(client_socket, client_addr, server_game_manager)

            round_result = self.handle_client_game_turn(client_socket, client_addr, server_game_manager)
            self.server_logger.info(f"{client_addr} - Client final card score is - {server_game_manager.current_round_client_sum}")
            if (round_result == TCP.GAME_ROUND_NOT_OVER):
                round_result = self.handle_server_game_turn(client_socket, client_addr, server_game_manager)
            
            server_game_manager.current_round += 1
            server_game_manager.update_game_stats(round_result)
            self.server_logger.info(f"{client_addr} --- Round {i + 1} complete ---\n")
        
        server_game_manager.stop_timer()
        server_game_manager.save_to_db()

    # Input: client socket, client address, game manager
    # Output: none
    # Description: Initializes a new round and sends initial cards to client.
    def init_client_game(self, client_socket, client_addr, server_game_manager):
        server_game_manager.init_round()
        self.server_logger.info(f"{client_addr} - Dealer card (visible): {server_game_manager.current_round_server_cards[0]}")
        self.server_logger.info(f"{client_addr} - Dealer card (hidden): {server_game_manager.current_round_server_cards[1]}")
        self.server_logger.info(f"{client_addr} - Client card #1: {server_game_manager.current_round_client_cards[0]}")
        self.server_logger.info(f"{client_addr} - Client card #2: {server_game_manager.current_round_client_cards[1]}") 

        for card in server_game_manager.current_round_server_cards + server_game_manager.current_round_client_cards:
            client_socket.sendall(TCP.create_payload_card(card))

    # Input: client socket, client address, game manager
    # Output: round result constant
    # Description: Handles the client’s turn including hit/stand decisions.
    def handle_client_game_turn(self, client_socket, client_addr, server_game_manager):
        if (server_game_manager.is_client_busted()):
            self.server_logger.info(f"{client_addr} - Client busted")
            client_socket.sendall(TCP.create_payload_round_result(TCP.GAME_SERVER_WIN_RESULT))
            return TCP.GAME_SERVER_WIN_RESULT
        else:
            self.server_logger.info(f"{client_addr} --- Starting player turn ---")
            client_socket.sendall(TCP.create_payload_round_result(TCP.GAME_ROUND_NOT_OVER))
        while True:
            decision_time_start = time.time()
            client_decision = self.get_client_decision(client_socket, client_addr)
            decision_time_end = time.time()
            server_game_manager.add_client_response_time(response_time=decision_time_end - decision_time_start)
            self.server_logger.info(f"{client_addr} - Client decision: {client_decision}")
            if (client_decision == "hittt"):
                new_card = server_game_manager.pop_card()
                server_game_manager.add_client_card(new_card)
                self.server_logger.info(f"{client_addr} - Dealt new card to client: rank={new_card.rank} suit={new_card.suit}")
                client_socket.sendall(TCP.create_payload_card(new_card))

                self.server_logger.info(f"{client_addr} - Client current sum: {server_game_manager.current_round_client_sum}")
                if (server_game_manager.current_round_client_sum > 21):
                    self.server_logger.info(f"{client_addr} - Client busted")
                    server_game_manager.add_client_bust()
                    client_socket.sendall(TCP.create_payload_round_result(TCP.GAME_SERVER_WIN_RESULT))
                    return TCP.GAME_SERVER_WIN_RESULT
                else:
                    client_socket.sendall(TCP.create_payload_round_result(TCP.GAME_ROUND_NOT_OVER))
                    
            elif (client_decision == "stand"):
                return TCP.GAME_ROUND_NOT_OVER
            
    # Input: client socket, client address
    # Output: "hittt" or "stand"
    # Description: Receives and validates a single player decision from client.
    def get_client_decision(self, client_socket, client_addr):
        while True:
            client_data = TCP.receive_response(client_socket, TCP.MSG_PAYLOAD_RESPONSE_SIZE, TCP.MSG_TYPE_PAYLOAD)
            decision = client_data.decode("utf-8", errors="ignore").strip('\x00').lower()
            if (decision not in ('hittt','stand')):
                    self.server_logger.warning(f"Invalid client decision from {client_addr}: {decision}")
                    client_socket.sendall(TCP.create_payload_validation(TCP.PAYLOAD_NOT_VALID))
            else:
                return decision
            
    # Input: client socket, client address, game manager
    # Output: round result constant
    # Description: Executes dealer logic according to Blackjack rules.
    def handle_server_game_turn(self, client_socket, client_addr, server_game_manager):
        self.server_logger.info(f"{client_addr} --- Starting dealer turn ---")
        dealer_revealed_card = server_game_manager.current_round_server_cards[0]
        dealer_hidden_card = server_game_manager.current_round_server_cards[1]
        self.server_logger.info(f"{client_addr} - Dealer's revealed card: rank={dealer_revealed_card.rank} suit={dealer_revealed_card.suit}")
        self.server_logger.info(f"{client_addr} - Revealing dealer's hidden card: rank={dealer_hidden_card.rank} suit={dealer_hidden_card.suit}")
        client_socket.sendall(TCP.create_payload_card(dealer_hidden_card))
        while True:
            if (server_game_manager.current_round_server_sum > 21):
                self.server_logger.info(f"{client_addr} - Dealer busted with sum {server_game_manager.current_round_server_sum}")
                server_game_manager.add_server_bust()
                client_socket.sendall(TCP.create_payload_round_result(TCP.GAME_CLIENT_WIN_RESULT))
                return TCP.GAME_CLIENT_WIN_RESULT
            elif (server_game_manager.current_round_server_sum >= 17):
                self.server_logger.info(f"{client_addr} - Dealer choses to stand")
                return self.calculate_final_game_result(client_socket, client_addr, server_game_manager)
            else:               
                self.server_logger.info(f"{client_addr} - Dealer choses to draw another card.")
                client_socket.sendall(TCP.create_payload_round_result(TCP.GAME_ROUND_NOT_OVER))
                new_card = server_game_manager.pop_card()
                server_game_manager.add_server_card(new_card)
                self.server_logger.info(f"{client_addr} - Dealer drew card: rank={new_card.rank} suit={new_card.suit}")
                self.server_logger.info(f"{client_addr} - Dealer current sum: {server_game_manager.current_round_server_sum}")
                client_socket.sendall(TCP.create_payload_card(new_card))


    # Input: client socket, client address, game manager
    # Output: final round result
    # Description: Compares dealer and player scores and sends result.
    def calculate_final_game_result(self, client_socket, client_addr, server_game_manager):
        self.server_logger.info(f"{client_addr} --- Round ended. Calculating result... ---")
        round_result = server_game_manager.get_round_result()
        self.server_logger.info(f"{client_addr} --- Final Result is: {get_result_as_string(round_result)} ---")
        client_socket.sendall(TCP.create_payload_round_result(round_result))
        return round_result

    # Input: none
    # Output: none (blocks execution)
    # Description: Starts UDP broadcasting and TCP listener threads.
    def start_server(self):
        broadcast_thread = threading.Thread(target=self.broadcast_offers, daemon=True)
        broadcast_thread.start()

        accept_thread = threading.Thread(target=self.accept_client_connections, daemon=True)
        accept_thread.start()

        broadcast_thread.join()
        accept_thread.join()

# Input: none
# Output: none
# Description: Entry point that creates and starts the server.
def main():
    server = Server()
    server.start_server()

if __name__ == "__main__":
    main()
