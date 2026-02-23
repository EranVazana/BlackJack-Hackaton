import struct
import socket

from shared.card import Card
from shared.logger import get_logger

# Input: none
# Output: local IP address string
# Description: Detects local IP by connecting a UDP socket to a public address.
def get_local_ip():
    temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        temp_socket.connect(("8.8.8.8", 80))
        ip = temp_socket.getsockname()[0]
    finally:
        temp_socket.close()
    return ip
    
class UDP:
    MAGIC_COOKIE = 0xabcddcba
    OFFER_MESSAGE_TYPE = 0x02

    SERVER_NAME_SIZE = 32
    PORT_SIZE = 0x02

    @staticmethod
    # Input: socket (UDP socket)
    # Output: (server_addr, server_name_bytes)
    # Description: Receives and validates a UDP offer message.
    # Input: socket (TCP socket), payload_size (int), message_type (int)
    # Output: payload bytes or None
    # Description: Receives one framed TCP message and validates magic cookie and type.
    def receive_response(socket):
        while True:
            data, addr = socket.recvfrom(4 + 1 + UDP.PORT_SIZE + UDP.SERVER_NAME_SIZE)
            if len(data) < 39:
                continue
            magic, msg_type, port, server_name = struct.unpack(f"!IBH{UDP.SERVER_NAME_SIZE}s", data[:39])

            if magic == UDP.MAGIC_COOKIE and msg_type == UDP.OFFER_MESSAGE_TYPE:
                server_ip = addr[0]
                server_port = port
                server_addr = (server_ip, server_port)
                return server_addr, server_name

    @staticmethod
    # Input: tcp_port (int), server_name (str)
    # Output: bytes offer message
    # Description: Builds a UDP offer packet with fixed-length server name.
    def create_offer_message(tcp_port, server_name):
        name_bytes = server_name.encode("utf-8", errors="ignore")
        name_bytes = name_bytes[:UDP.SERVER_NAME_SIZE].ljust(UDP.SERVER_NAME_SIZE, b"\x00")
        return struct.pack(f"!IBH{UDP.SERVER_NAME_SIZE}s", UDP.MAGIC_COOKIE,UDP.OFFER_MESSAGE_TYPE, tcp_port, name_bytes)
    
class TCP:
    MAGIC_COOKIE = 0xabcddcba

    MSG_TYPE_REQUEST = 0x03
    MSG_REQUEST_SIZE = 33

    MSG_TYPE_PAYLOAD = 0x04
    MSG_PAYLOAD_CARD_SIZE = 3
    MSG_PAYLOAD_RESPONSE_SIZE = 5
    MSG_PAYLOAD_RESULT_SIZE = 1

    MSG_TYPE_VALIDATION = 0x05
    PAYLOAD_VALID = 0x01
    PAYLOAD_NOT_VALID = 0x00

    GAME_CLIENT_WIN_RESULT = 0x03
    GAME_SERVER_WIN_RESULT = 0x02
    GAME_TIE_RESULT = 0x01
    GAME_ROUND_NOT_OVER = 0x00

    @staticmethod
    # Input: socket (UDP socket)
    # Output: (server_addr, server_name_bytes)
    # Description: Receives and validates a UDP offer message.
    # Input: socket (TCP socket), payload_size (int), message_type (int)
    # Output: payload bytes or None
    # Description: Receives one framed TCP message and validates magic cookie and type.
    def receive_response(socket, payload_size, message_type):
        logger = get_logger()
        while True:
            data = socket.recv(4 + 1 + payload_size)
            if not data:
                return None
            
            magic = struct.unpack("!I", data[:4])[0]
            if (magic != TCP.MAGIC_COOKIE):
                logger.warning("Invalid magic cookie from:", socket.getpeername())
                continue
            
            type = struct.unpack("!B", data[4:5])[0]
            if (message_type != type):
                logger.warning("Invalid message type from:", socket.getpeername())
                continue
            
            _, _ , payload = struct.unpack(f"!IB{payload_size}s", data[:4+1+payload_size])
            return payload

    @staticmethod
    # Input: team_name (str), num_rounds (int)
    # Output: bytes request message
    # Description: Builds a TCP request packet containing rounds and team name.
    def create_request_message(team_name, num_rounds):
        if not (0 < num_rounds <= 255):
            raise ValueError("num_rounds must fit in 1 byte (1-255)")
                
        name_bytes = team_name.encode("utf-8", errors="ignore")
        name_bytes = name_bytes[:(TCP.MSG_REQUEST_SIZE-1)].ljust((TCP.MSG_REQUEST_SIZE-1), b"\x00")

        return struct.pack(f"!IBB{TCP.MSG_REQUEST_SIZE-1}s", TCP.MAGIC_COOKIE, TCP.MSG_TYPE_REQUEST, num_rounds, name_bytes)
    
    @staticmethod
    # Input: card (Card)
    # Output: bytes payload message
    # Description: Encodes a Card object as a TCP payload message.
    def create_payload_card(card):
        card_bytes = card.encode_to_bytes()
        return struct.pack(f"!IB{TCP.MSG_PAYLOAD_CARD_SIZE}s", TCP.MAGIC_COOKIE, TCP.MSG_TYPE_PAYLOAD, card_bytes)
    
    @staticmethod
    # Input: response (str)
    # Output: bytes payload message
    # Description: Encodes the player action string as a TCP payload message.
    def create_payload_response(response):
        response_bytes = response.encode("utf-8", errors="ignore")
        response_bytes = response_bytes[:TCP.MSG_PAYLOAD_RESPONSE_SIZE]
        return struct.pack(f"!IB{TCP.MSG_PAYLOAD_RESPONSE_SIZE}s", TCP.MAGIC_COOKIE, TCP.MSG_TYPE_PAYLOAD, response_bytes)
    
    @staticmethod
    # Input: result (int)
    # Output: bytes payload message
    # Description: Encodes the round result byte as a TCP payload message.
    def create_payload_round_result(result):
        return struct.pack("!IBB", TCP.MAGIC_COOKIE, TCP.MSG_TYPE_PAYLOAD, result)
    
    @staticmethod
    # Input: result (int)
    # Output: bytes validation message
    # Description: Encodes a validation byte (valid/invalid) as a TCP message.
    def create_payload_validation(result):
        return struct.pack("!IBB", TCP.MAGIC_COOKIE, TCP.MSG_TYPE_VALIDATION, result)
    
    @staticmethod
    # Input: vr1 (bytes), vr2 (int)
    # Output: bool
    # Description: Checks whether the validation payload matches the expected value.
    def verify_validation_message(vr1, vr2):
        return vr2 == vr1[0]
