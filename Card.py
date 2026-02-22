class Card:
    ranks = ('2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A')
    suits = ('H', 'D', 'C', 'S')

    rank_to_idx = {r: i for i, r in enumerate(ranks)}
    suit_to_idx = {s: i for i, s in enumerate(suits)}
    values = (2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11)

    suits_emoji = {'H': '♥️', 'D': '♦️', 'C': '♣️', 'S': '♠️'}
    rank_emoji = {
        '2': '2️⃣', '3': '3️⃣', '4': '4️⃣', '5': '5️⃣', '6': '6️⃣',
        '7': '7️⃣', '8': '8️⃣', '9': '9️⃣', '10': '🔟',
        'J': '🃏(J)', 'Q': '👸(Q)', 'K': '👑(K)', 'A': '🅰️'
    }

    # Input: suit (str), rank (str)
    # Output: Card object
    # Description: Creates a card with suit, rank, and numerical value.
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.value = Card.values[Card.rank_to_idx[rank]]

    # Input: none
    # Output: list of Card objects
    # Description: Generates a standard 52-card deck.
    @staticmethod
    def create_deck():
        return [Card(suit, rank) for suit in Card.suits for rank in Card.ranks]

    # Input: none
    # Output: bytes (2 bytes)
    # Description: Encodes card rank and suit into a compact byte format.
    def encode_to_bytes(self):
        rank_idx = Card.rank_to_idx[self.rank]   # 0..12
        suit_idx = Card.suit_to_idx[self.suit]   # 0..3
        return bytes([rank_idx, suit_idx])

    # Input: byte_data (bytes)
    # Output: Card object
    # Description: Decodes a card from its byte representation.
    @staticmethod
    def decode_from_bytes(byte_data):
        rank_idx = byte_data[0]
        suit_idx = byte_data[1]
        return Card(Card.suits[suit_idx], Card.ranks[rank_idx])
    
    # Input: none
    # Output: dict
    # Description: Converts the card to a dictionary representation.
    def to_dict(self) -> dict:
        return {"rank": self.rank, "suit": self.suit}

    # Input: none
    # Output: string
    # Description: Returns a readable string representation of the card.
    def __str__(self):
        return f"rank={self.rank} suit={self.suit}"

    # Input: none
    # Output: string
    # Description: Returns a human-friendly emoji representation of the card.
    def emoji_str(self):
        return f"rank={Card.rank_emoji[self.rank]} , suit={Card.suits_emoji[self.suit]}"
