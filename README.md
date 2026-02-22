# 🃏 Blackjack Client–Server Game

A full-featured Blackjack game implemented with a **custom UDP + TCP protocol**, including a real-time multiplayer server, interactive CLI client, persistent game storage, and an advanced **statistics dashboard**.

This project was built as a networking-focused system, emphasizing protocol design, concurrency, data serialization, robustness, and post-game analytics.

---

## ✨ Key Features

* **Automatic server discovery** using UDP broadcast (because hardcoding IPs is for quitters)
* **Reliable gameplay communication** over TCP with a custom binary protocol (no JSON was harmed in the making of this project)
* **Concurrent multi-client server** using threading (yes, multiple players can lose simultaneously)
* **Full Blackjack game logic** with dealer and player turns, exactly like the casino, but cheaper
* **Two client implementations**:

  * Terminal-based CLI client for the purists
  * Advanced **Streamlit UI client** with animations, visual cards, and zero Vegas smells
* **Persistent game history** stored using TinyDB (your losses are forever)
* **Rich logging system** with colored, structured logs (because print() is not a logging strategy)
* **Advanced analytics dashboard** built with Streamlit and Plotly

---

## 🧠 Architecture Overview

```
ClientCLI.py / ClientUI.py  <---TCP--->  Server.py
        ^                                    |
        |                                    v
   UDP Discovery                       GameManager.py
                                            |
                                            v
                                      TinyDBWrapper.py
                                            |
                                            v
                                      StatisticsUI.py
```

```

---

## 📂 Project Structure

```

.
├── Card.py               # Card model, encoding, decoding, emojis
├── ClientCLI.py          # Interactive CLI Blackjack client
├── ClientUI.py           # Streamlit-based graphical client with animations
├── Server.py             # Multiplayer game server (the house always runs here)
├── GameManager.py        # Core Blackjack game logic
├── Packets.py            # Custom UDP/TCP protocol definitions
├── Logger.py             # Colored, structured logging system
├── TinyDBWrapper.py      # Thread-safe persistent storage
├── StatisticsUI.py       # Streamlit analytics dashboard
├── db.json               # Persistent game database (real games)
├── db_mock.json          # Mock database for testing and demo

```
.
├── Card.py               # Card model, encoding, decoding, emojis
├── ClientCLI.py          # Interactive CLI Blackjack client
├── ClientUI.py           # Streamlit-based graphical client with animations
├── Server.py             # Multiplayer game server
├── GameManager.py        # Core Blackjack game logic
├── Packets.py            # Custom UDP/TCP protocol definitions
├── Logger.py             # Colored, structured logging system
├── TinyDBWrapper.py      # Thread-safe persistent storage
├── StatisticsUI.py       # Streamlit analytics dashboard
├── db.json               # Persistent game database (real games)
├── db_mock.json          # Mock database for testing and demo
```

.
├── Card.py               # Card model, encoding, decoding, emojis
├── ClientCLI.py          # Interactive Blackjack client
├── Server.py             # Multiplayer game server
├── GameManager.py        # Core Blackjack game logic
├── Packets.py            # Custom UDP/TCP protocol definitions
├── Logger.py             # Colored, structured logging system
├── TinyDBWrapper.py      # Thread-safe persistent storage
├── StatisticsUI.py       # Streamlit analytics dashboard
├── db.json               # Game history database

````

---

## 🌐 Networking Protocol

### UDP
- Used only for **server discovery**
- Broadcasts server name and TCP port
- Custom packet with magic cookie validation

### TCP
- Used for the full game lifecycle
- Binary messages with:
  - Magic cookie
  - Message type
  - Fixed-size payloads
- Supports:
  - Game requests
  - Card transfers
  - Player decisions
  - Round results
  - Validation messages

---

## 🎮 Gameplay Flow

1. Client listens for UDP offers or connects manually
2. Client establishes a TCP connection with the server
3. Client sends team name and number of rounds
4. Server validates the request and initializes a game session
5. Game rounds begin
6. Each round includes:
   - Initial deal to player and dealer
   - Player decision loop (Hit or Stand)
   - Dealer automated logic (draw until >= 17)
   - Result calculation and validation
7. Detailed round and game statistics are collected
8. Full game data is persisted to the database


---

## 📊 Statistics Dashboard

The project includes a **Streamlit-based analytics UI** that visualizes:

- Win, loss, and tie distributions
- Player and dealer hand values
- Bust rates
- Hit behavior analysis
- Response times per round and per game
- Total game duration
- Network data usage per game
- Team leaderboard with win rates

To run the dashboard:

```bash
streamlit run StatisticsUI.py
````

---

## 🛠️ Technologies Used

* Python 3
* socket, struct, threading
* TinyDB
* Streamlit
* Plotly
* Pandas, NumPy
* Colorama

---

## 🚀 How to Run

### Start the Server

```bash
python Server.py
```

### Start a CLI Client

```bash
python ClientCLI.py
```

### Start the Graphical UI Client

```bash
streamlit run ClientUI.py
```

Multiple clients can connect simultaneously, including a mix of CLI and UI clients.

---

## 🧪 Design Highlights

* Custom binary protocol with strict validation and magic cookies (the tasty kind)
* Clear separation between networking, game logic, persistence, and UI layers
* Thread-safe database access with a singleton pattern
* Deterministic server-side game flow, the dealer never cheats, the code does not lie
* Support for both CLI and graphical clients without protocol duplication
* Extensive logging for debugging, analysis, and mild emotional support

---

## 📌 Notes

* The server runs indefinitely and accepts multiple clients
* All game data is persisted automatically
* Dashboard supports historical analysis across all games

---

## 🏆 Final Words

This project demonstrates a complete end-to-end **networked software system**, combining low-level socket programming with high-level user experience and data analytics.

It showcases protocol design, concurrency handling, clean architecture, persistence, and visualization, all built from scratch with careful attention to software engineering principles.

In short: this is not just a Blackjack game.

It is a distributed system that happens to gamble.
