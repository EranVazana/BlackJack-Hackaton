
# 🃏 Blackjack Multiplayer Game System

A fully featured Blackjack application built on a **custom-designed UDP and TCP communication protocol**, featuring a real-time multiplayer server, an interactive command-line client, persistent game state management, and a comprehensive **statistics dashboard**.

The system was developed with a strong focus on networking architecture, including protocol design, concurrent connection handling, data serialization, fault tolerance, and post-game analytical reporting.

This project was developed as part of a competitive **networking hackathon**, 
where it was recognized as the **winning submission** for its technical depth, architectural design, and overall execution.

----------

## 💡 Key Skills Demonstrated

🌐 Networking:

Custom UDP/TCP binary protocol design, socket programming, packet serialization, server discovery via broadcast

⚡ Concurrency:

Multi-threaded server, thread-safe database access, singleton pattern, race condition handling

🏛️ Architecture:

Clean separation of concerns, modular design, shared libraries, cross-platform scripting

📊 Data & Analytics:

Real-time statistics, visualizations, persistent storage, data aggregation

🛠️ Software Engineering:

Structured logging, error handling, input validation, protocol versioning with magic cookies

----------

## 🏗️ Architecture

```
┌─────────────────┐         UDP Broadcast          ┌─────────────────┐
│                 │ ◄──────────────────────────────│                 │
│   CLI Client    │                                │                 │
│   (cli.py)      │ ◄──────── TCP ────────────────►│     Server      │
│                 │                                │   (server.py)   │
├─────────────────┤                                │                 │
│                 │                                │        │        │
│   GUI Client    │ ◄──────── TCP ────────────────►│        ▼        │
│   (ui.py)       │                                │  Game Manager   │
│                 │                                │        │        │
└─────────────────┘                                │        ▼        │
                                                   │    TinyDB       │
┌─────────────────┐                                │   (storage)     │
│   Dashboard     │ ◄───── Reads Game Data ────────│                 │
│   (app.py)      │                                └─────────────────┘
└─────────────────┘

```

----------

## ✨ Features

### 🌐 Networking:

-   **UDP Broadcast** - Automatic server discovery without hardcoded IPs
-   **TCP Communication** - Reliable gameplay with custom binary protocol
-   **Magic Cookie Validation** - Protocol integrity verification
-   **Fixed-size Payloads** - Efficient binary serialization using `struct`

### 🎮 Game System:

-   **Full Blackjack Logic** - Hit, stand, bust detection, dealer AI (draws until ≥17)
-   **Multi-client Support** - Concurrent players with isolated game states
-   **Two Client Options** - Terminal CLI or animated Streamlit GUI

### 📊 Analytics Dashboard:

-   Win/Loss/Tie distributions
-   Player vs Dealer hand value analysis
-   Bust rate tracking
-   Response time metrics
-   Team leaderboard with win rates

### 🔧 Engineering:

-   Thread-safe singleton database wrapper
-   Colored, structured logging system
-   Cross-platform run scripts (Linux/Windows/PowerShell)
-   Clean modular architecture

## 📸 GUI Screenshots

<details> <summary>Click to expand screenshots</summary>

### GUI Client
![ui.png](https://imgur.com/a/dKVLBjg)

### Statistics Dashboard
![dashboard.png](https://imgur.com/a/xEeCpi4)

</details>
---


## 🛠️ Tech Stack

### 🌐 Networking:

* `socket` · `struct` · `threading`

### ♠️ Game Logic:

* Pure Python with OOP design

### 💾 Persistence:

* TinyDB with caching middleware

### 🖥️ CLI Client:

* Colorama for colored terminal output

### 🎨 GUI Client:

* Streamlit with custom CSS animations

### 📊 Dashboard:

* Streamlit · Plotly · Pandas · NumPy


## 📂 Project Structure

```
BlackJack-Hackaton/
│
├── client/                          # Client-side applications
│   ├── cli.py                       # Terminal-based Blackjack client
│   └── ui.py                        # Streamlit GUI client with animations
│
├── server/                          # Server-side components
│   ├── server.py                    # Concurrent multiplayer game server
│   └── game_manager.py              # Core game logic & state management
│
├── shared/                          # Shared modules (client & server)
│   ├── card.py                      # Card model with binary encoding/decoding
│   ├── packets.py                   # Custom UDP/TCP protocol definitions
│   └── logger.py                    # Colored, structured logging system
│
├── storage/                         # Data persistence layer
│   ├── wrapper.py                   # Thread-safe TinyDB singleton
│   └── data/
│       ├── db.json                  # Game history database
│       └── db_mock.json             # Mock data for testing
│
├── statistics_dashboard/            # Analytics & visualization
│   └── app.py                       # Streamlit dashboard with Plotly
│
├── utilities/
│   └── scripts/
│       ├── linux/                   # Bash scripts (.sh)
│       ├── windows/                 # Batch scripts (.bat)
│
├── .gitignore
├── README.md
└── requirements.txt

```

----------

## 🚀 Quick Start

### Prerequisites

```bash
pip install -r requirements.txt
```

### Run the Server

```bash
# Linux/Mac
utilities\scripts\linux\run_server.sh

# Windows CMD
utilities\scripts\windows\run_server.bat
```

### Run a Client

```bash
# -- CLI Client: --
# Linux/Mac
utilities\scripts\linux\run_client.sh

# Windows CMD
utilities\scripts\windows\run_client.bat

# -- GUI Client (Streamlit): --
# Linux/Mac
utilities\scripts\linux\run_client_ui.sh

# Windows CMD
utilities\scripts\windows\run_client_ui.bat
```
> 💡 Multiple clients can connect simultaneously - try running both CLI and GUI clients!

### View Analytics Dashboard
```bash
# Linux/Mac
utilities\scripts\linux\run_dashboard.sh

# Windows CMD
utilities\scripts\windows\run_dashboard.bat
```

## 🌐 Protocol Specification

### UDP Discovery Packet (Server --> Client)

| Field         | Size     | Description              |
|--------------|----------|--------------------------|
| Magic Cookie | 4 bytes  | `0xABCDDCBA`             |
| Message Type | 1 byte   | `0x02` (Offer)           |
| TCP Port     | 2 bytes  | Server's TCP port        |
| Server Name  | 32 bytes | Null-padded string       |

---

### TCP Message Format

| Field         | Size     | Description                     |
|--------------|----------|---------------------------------|
| Magic Cookie | 4 bytes  | `0xABCDDCBA`                    |
| Message Type | 1 byte   | Request / Payload / Validation  |
| Payload      | Variable | Type-dependent data             |

----------
