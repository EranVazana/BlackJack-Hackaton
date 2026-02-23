"""
Blackjack Client with Streamlit UI
Matches ClientCLI.py protocol with smooth animations

Flow: Connect to Server -> Enter Name/Rounds -> Play Game
"""

import os
import socket
import subprocess
import time
import json
import sys
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from shared.card import Card
from shared.packets import TCP, UDP

# States
STATE_DISCONNECTED = "disconnected"
STATE_DISCOVERING = "discovering"
STATE_SERVER_FOUND = "server_found"
STATE_PLAYER_TURN = "player_turn"
STATE_DEALER_TURN = "dealer_turn"
STATE_ROUND_END = "round_end"
STATE_GAME_OVER = "game_over"

# Result codes from TCP class
RESULT_NOT_OVER = 0x00
RESULT_TIE = 0x01
RESULT_SERVER_WIN = 0x02
RESULT_CLIENT_WIN = 0x03


def get_suit_symbol(suit: str) -> tuple:
    """Returns (symbol, color) for a suit"""
    suit_upper = str(suit).upper().strip()
    if suit_upper in ["H", "HEARTS", "HEART", "♥"]:
        return ("♥", "#e63946")
    elif suit_upper in ["D", "DIAMONDS", "DIAMOND", "♦"]:
        return ("♦", "#e63946")
    elif suit_upper in ["C", "CLUBS", "CLUB", "♣"]:
        return ("♣", "#1d3557")
    elif suit_upper in ["S", "SPADES", "SPADE", "♠"]:
        return ("♠", "#1d3557")
    else:
        return (suit, "#1d3557")


def card_html(rank: str, suit: str, hidden: bool = False, animate: bool = False) -> str:
    """Generate HTML for a playing card with optional animation"""
    animation_style = ""
    if animate:
        animation_style = "animation: cardDeal 0.5s ease-out;"
    
    if hidden:
        return f'''<div style="width:75px;height:105px;background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
            border-radius:10px;display:inline-flex;align-items:center;justify-content:center;margin:5px;
            border:2px solid #0f3460;box-shadow:0 4px 15px rgba(0,0,0,0.3);{animation_style}">
            <span style="font-size:40px;color:#e94560;">🂠</span></div>'''
    
    sym, col = get_suit_symbol(suit)
    
    return f'''<div style="width:75px;height:105px;background:linear-gradient(145deg,#ffffff 0%,#f8f9fa 100%);
        border-radius:10px;display:inline-flex;flex-direction:column;align-items:center;justify-content:center;
        margin:5px;border:1px solid #dee2e6;position:relative;box-shadow:0 4px 15px rgba(0,0,0,0.2);{animation_style}">
        <span style="position:absolute;top:6px;left:8px;font-size:14px;font-weight:bold;color:{col};
            font-family:Georgia,serif;">{rank}</span>
        <span style="font-size:36px;color:{col};">{sym}</span>
        <span style="position:absolute;bottom:6px;right:8px;font-size:14px;font-weight:bold;color:{col};
            font-family:Georgia,serif;transform:rotate(180deg);">{rank}</span></div>'''


def cards_html(cards: List[dict], hide_second: bool = False, new_card_index: int = -1) -> str:
    """Render cards with optional animation for new card"""
    if not cards:
        return '<div style="color:#888;font-style:italic;">No cards</div>'
    
    html = '<div style="display:flex;flex-wrap:wrap;justify-content:center;align-items:center;">'
    for i, c in enumerate(cards):
        animate = (i == new_card_index)
        if hide_second and i == 1:
            html += card_html("", "", hidden=True, animate=animate)
        else:
            html += card_html(str(c.get("rank", "?")), str(c.get("suit", "?")), animate=animate)
    html += "</div>"
    return html


def get_result_string(result: int) -> tuple:
    """Returns (result_string, css_class)"""
    if result == RESULT_CLIENT_WIN:
        return ("🏆 YOU WIN! 🏆", "win")
    elif result == RESULT_SERVER_WIN:
        return ("💔 YOU LOSE 💔", "loss")
    elif result == RESULT_TIE:
        return ("🤝 TIE 🤝", "tie")
    else:
        return ("???", "tie")


# ============ DISCOVERY SCRIPT (runs as separate process) ============
DISCOVERY_SCRIPT = '''
import socket
import struct
import json

MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x02
UDP_PORT = 13122
TIMEOUT = 15

result = {"status": "searching"}

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(2.0)
    sock.bind(('', UDP_PORT))
    
    start = __import__('time').time()
    while __import__('time').time() - start < TIMEOUT:
        try:
            data, addr = sock.recvfrom(1024)
            if len(data) >= 7:
                magic, msg_type, port = struct.unpack("!IBH", data[:7])
                if magic == MAGIC_COOKIE and msg_type == OFFER_MESSAGE_TYPE:
                    result = {"status": "found", "ip": addr[0], "port": port}
                    break
        except socket.timeout:
            continue
    else:
        result = {"status": "timeout"}
except Exception as e:
    result = {"status": "error", "error": str(e)}
finally:
    try:
        sock.close()
    except:
        pass

print(json.dumps(result))
'''


def run_discovery_subprocess() -> dict:
    """Run UDP discovery in a separate Python process"""
    try:
        result = subprocess.run(
            [sys.executable, '-c', DISCOVERY_SCRIPT],
            capture_output=True,
            text=True,
            timeout=20
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        else:
            return {"status": "error", "error": result.stderr.strip() if result.stderr else "Unknown error"}
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class SocketManager:
    """Manages TCP socket operations - matches ClientCLI protocol"""
    
    def __init__(self):
        self.tcp_sock: Optional[socket.socket] = None
        self.server_ip: Optional[str] = None
        self.server_port: Optional[int] = None
        self.dealer_revealed_card: Optional[dict] = None
    
    def connect_tcp(self, ip: str, port: int) -> bool:
        self.server_ip = ip
        self.server_port = port
        try:
            self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_sock.settimeout(10.0)
            self.tcp_sock.connect((ip, port))
            self.tcp_sock.settimeout(60.0)
            return True
        except Exception as e:
            print(f"TCP connect error: {e}")
            return False
    
    def send_settings(self, team: str, rounds: int) -> bool:
        """Send game settings and verify validation"""
        try:
            self.tcp_sock.sendall(TCP.create_request_message(team, rounds))
            validation = TCP.receive_response(self.tcp_sock, 1, TCP.MSG_TYPE_VALIDATION)
            return TCP.verify_validation_message(validation, TCP.PAYLOAD_VALID)
        except Exception as e:
            print(f"Send settings error: {e}")
            return False
    
    def init_round(self) -> tuple:
        """
        Receive 4 initial cards.
        Returns: (dealer_visible, dealer_hidden, player_card1, player_card2)
        """
        cards = []
        try:
            for _ in range(4):
                payload = TCP.receive_response(self.tcp_sock, 3, TCP.MSG_TYPE_PAYLOAD)
                card = Card.decode_from_bytes(payload)
                cards.append({"rank": card.rank, "suit": card.suit, "value": card.value})
            
            # Store dealer's visible card for later
            self.dealer_revealed_card = cards[0]
            return tuple(cards)
        except Exception as e:
            print(f"Init round error: {e}")
            return None
    
    def check_initial_bust(self) -> int:
        """Check if player busted on initial deal (21+ with first 2 cards)"""
        try:
            result = TCP.receive_response(self.tcp_sock, 1, TCP.MSG_TYPE_PAYLOAD)
            return int.from_bytes(result, byteorder='big')
        except Exception as e:
            print(f"Check initial bust error: {e}")
            return -1
    
    def send_hit(self) -> tuple:
        """Send hit action. Returns (card_dict, result_code)"""
        try:
            self.tcp_sock.sendall(TCP.create_payload_response("Hittt"))
            
            # Receive new card
            payload = TCP.receive_response(self.tcp_sock, 3, TCP.MSG_TYPE_PAYLOAD)
            card = Card.decode_from_bytes(payload)
            card_dict = {"rank": card.rank, "suit": card.suit, "value": card.value}
            
            # Receive result
            result = TCP.receive_response(self.tcp_sock, 1, TCP.MSG_TYPE_PAYLOAD)
            result_code = int.from_bytes(result, byteorder='big')
            
            return (card_dict, result_code)
        except Exception as e:
            print(f"Hit error: {e}")
            return (None, -1)
    
    def send_stand(self) -> bool:
        """Send stand action"""
        try:
            self.tcp_sock.sendall(TCP.create_payload_response("Stand"))
            return True
        except Exception as e:
            print(f"Stand error: {e}")
            return False
    
    def receive_dealer_hidden_card(self) -> dict:
        """Receive the dealer's hidden card reveal"""
        try:
            payload = TCP.receive_response(self.tcp_sock, 3, TCP.MSG_TYPE_PAYLOAD)
            card = Card.decode_from_bytes(payload)
            return {"rank": card.rank, "suit": card.suit, "value": card.value}
        except Exception as e:
            print(f"Receive hidden card error: {e}")
            return None
    
    def receive_dealer_result(self) -> int:
        """Receive dealer turn result. Returns result code."""
        try:
            result = TCP.receive_response(self.tcp_sock, 1, TCP.MSG_TYPE_PAYLOAD)
            return int.from_bytes(result, byteorder='big')
        except Exception as e:
            print(f"Receive dealer result error: {e}")
            return -1
    
    def receive_dealer_card(self) -> dict:
        """Receive a dealer card"""
        try:
            payload = TCP.receive_response(self.tcp_sock, 3, TCP.MSG_TYPE_PAYLOAD)
            card = Card.decode_from_bytes(payload)
            return {"rank": card.rank, "suit": card.suit, "value": card.value}
        except Exception as e:
            print(f"Receive dealer card error: {e}")
            return None
    
    def close(self):
        if self.tcp_sock:
            try:
                self.tcp_sock.close()
            except:
                pass
            self.tcp_sock = None


@st.cache_resource
def get_socket_manager():
    return SocketManager()


def init_state():
    defaults = {
        "state": STATE_DISCONNECTED,
        "server_ip": "127.0.0.1",
        "server_port": 8080,
        "team": "",
        "rounds": 3,
        "cur_round": 0,
        "player_cards": [],
        "dealer_cards": [],
        "player_sum": 0,
        "result": None,
        "logs": [],
        "wins": 0,
        "losses": 0,
        "ties": 0,
        "new_card_index": -1,
        "dealer_new_card_index": -1,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def log(msg):
    st.session_state.logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    st.session_state.logs = st.session_state.logs[-30:]


def reset():
    sm = get_socket_manager()
    sm.close()
    st.session_state.state = STATE_DISCONNECTED
    st.session_state.cur_round = 0
    st.session_state.player_cards = []
    st.session_state.dealer_cards = []
    st.session_state.player_sum = 0
    st.session_state.result = None
    st.session_state.wins = 0
    st.session_state.losses = 0
    st.session_state.ties = 0
    st.session_state.logs = []
    st.session_state.new_card_index = -1
    st.session_state.dealer_new_card_index = -1


def update_stats(result: int):
    """Update win/loss/tie stats based on result code"""
    if result == RESULT_CLIENT_WIN:
        st.session_state.wins += 1
    elif result == RESULT_SERVER_WIN:
        st.session_state.losses += 1
    elif result == RESULT_TIE:
        st.session_state.ties += 1


def inject_css():
    """Inject CSS with animations"""
    st.markdown("""
    <style>
    @keyframes cardDeal {
        0% { transform: translateY(-50px) rotate(-10deg); opacity: 0; }
        100% { transform: translateY(0) rotate(0deg); opacity: 1; }
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .stApp { background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0f3460 100%); }
    
    /* Center all h3 headers */
    h3 {
        text-align: center !important;
    }
    
    /* Center the tabs */
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
    }
    
    /* Center tab content */
    .stTabs [data-baseweb="tab-panel"] {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    
    /* Center info boxes */
    .stAlert {
        text-align: center;
    }
    
    .title { 
        font-size: 3.5rem; 
        text-align: center; 
        background: linear-gradient(135deg, #ffd700 0%, #ffaa00 50%, #ff8c00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        text-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
    }
    
    .sub { 
        text-align: center; 
        color: #888; 
        letter-spacing: 0.3em; 
        margin-bottom: 1.5rem;
        font-size: 0.9rem;
    }
    
    .table {
        background: linear-gradient(145deg, #1b5e20 0%, #145214 50%, #0d3d0d 100%);
        border-radius: 150px 150px 20px 20px;
        padding: 2rem;
        margin: 1rem auto;
        max-width: 800px;
        box-shadow: 
            inset 0 0 60px rgba(0,0,0,0.4),
            0 10px 40px rgba(0,0,0,0.6),
            0 0 0 10px #3e2723,
            0 0 0 14px #2d1f1f;
        border: 2px solid #4e342e;
    }
    
    .lbl { 
        color: #ffd700; 
        text-align: center; 
        font-size: 1.2rem; 
        margin: 0.5rem 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
        letter-spacing: 0.1em;
    }
    
    .score {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: #fff;
        padding: 0.4rem 1.2rem;
        border-radius: 20px;
        display: inline-block;
        border: 2px solid #e94560;
        font-size: 1.1rem;
        box-shadow: 0 4px 15px rgba(233, 69, 96, 0.3);
    }
    
    .win { 
        color: #4caf50; 
        font-size: 2rem; 
        text-align: center;
        animation: pulse 1s ease-in-out infinite;
        text-shadow: 0 0 20px rgba(76, 175, 80, 0.5);
    }
    
    .loss { 
        color: #f44336; 
        font-size: 2rem; 
        text-align: center;
        text-shadow: 0 0 20px rgba(244, 67, 54, 0.5);
    }
    
    .tie { 
        color: #ff9800; 
        font-size: 2rem; 
        text-align: center;
        text-shadow: 0 0 20px rgba(255, 152, 0, 0.5);
    }
    
    .stats { 
        display: flex; 
        justify-content: center; 
        gap: 1.5rem; 
        margin: 1rem 0; 
        flex-wrap: wrap; 
    }
    
    .sbox {
        background: rgba(255,255,255,0.08);
        padding: 0.6rem 1.2rem;
        border-radius: 10px;
        text-align: center;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .slbl { color: #aaa; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; }
    .sval { color: #fff; font-size: 1.4rem; font-weight: 600; }
    
    .logbox {
        background: rgba(0,0,0,0.6);
        border-radius: 10px;
        padding: 0.8rem;
        max-height: 120px;
        overflow-y: auto;
        font-family: 'Consolas', monospace;
        font-size: 0.7rem;
        color: #8892b0;
        margin-top: 1.5rem;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .stbox { text-align: center; padding: 0.6rem; border-radius: 10px; margin: 0.5rem 0; }
    .on { background: rgba(76,175,80,0.2); border: 1px solid #4caf50; color: #4caf50; }
    .srch { background: rgba(255,152,0,0.2); border: 1px solid #ff9800; color: #ff9800; }
    
    .dealer-drawing {
        text-align: center;
        color: #ff9800;
        font-size: 1.3rem;
        margin: 1rem 0;
        animation: pulse 1s ease-in-out infinite;
    }
    
    .card-area {
        min-height: 130px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)


def render_stats():
    st.markdown(f'''<div class="stats">
        <div class="sbox"><div class="slbl">Round</div><div class="sval">{st.session_state.cur_round}/{st.session_state.rounds}</div></div>
        <div class="sbox"><div class="slbl">Wins</div><div class="sval" style="color:#4caf50;">{st.session_state.wins}</div></div>
        <div class="sbox"><div class="slbl">Losses</div><div class="sval" style="color:#f44336;">{st.session_state.losses}</div></div>
        <div class="sbox"><div class="slbl">Ties</div><div class="sval" style="color:#ff9800;">{st.session_state.ties}</div></div>
    </div>''', unsafe_allow_html=True)


def render_table(hide_dealer: bool = True, dealer_drawing: bool = False):
    st.markdown('<div class="table">', unsafe_allow_html=True)
    
    # Dealer label
    if dealer_drawing:
        st.markdown('<div class="lbl">🎩 DEALER (Drawing...)</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="lbl">🎩 DEALER</div>', unsafe_allow_html=True)
    
    # Dealer cards
    dealer_html = cards_html(
        st.session_state.dealer_cards, 
        hide_second=hide_dealer,
        new_card_index=st.session_state.dealer_new_card_index
    )
    st.markdown(f'<div class="card-area">{dealer_html}</div>', unsafe_allow_html=True)
    
    st.markdown('<hr style="border-color:rgba(255,215,0,0.3);margin:1rem 0;">', unsafe_allow_html=True)
    
    # Player
    st.markdown('<div class="lbl">🎴 YOUR HAND</div>', unsafe_allow_html=True)
    player_html = cards_html(
        st.session_state.player_cards,
        new_card_index=st.session_state.new_card_index
    )
    st.markdown(f'<div class="card-area">{player_html}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align:center;"><span class="score">Total: {st.session_state.player_sum}</span></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_logs():
    if st.session_state.logs:
        st.markdown('<div class="logbox">' + '<br>'.join(st.session_state.logs[-15:]) + '</div>', unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="Blackjack", page_icon="🃏", layout="wide")
    
    inject_css()
    init_state()
    sm = get_socket_manager()
    
    st.markdown('<div class="title">♠ ByteMe BlackJack ♥</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub">From Liel And Eran</div>', unsafe_allow_html=True)
    
    state = st.session_state.state
    
    # ==================== DISCONNECTED ====================
    if state == STATE_DISCONNECTED:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🔌 Connect to Server")
            
            tab1, tab2 = st.tabs(["🔍 Auto-Discover", "📝 Manual Entry"])
            
            with tab1:
                st.info("Auto-discover server via UDP broadcast")
                if st.button("🔍 Search for Server", use_container_width=True, type="primary", key="discover"):
                    log("🔍 Searching for server...")
                    st.session_state.state = STATE_DISCOVERING
                    st.rerun()
            
            with tab2:
                st.info("Enter the server IP (use 127.0.0.1 if server is on same machine)")
                server_ip = st.text_input("Server IP", value=st.session_state.server_ip, key="ip_input")
                server_port = st.number_input("Server Port", value=st.session_state.server_port, min_value=1, max_value=65535, key="port_input")
                
                if st.button("🔗 Connect", use_container_width=True, type="primary", key="connect_manual"):
                    st.session_state.server_ip = server_ip
                    st.session_state.server_port = int(server_port)
                    sm.server_ip = server_ip
                    sm.server_port = int(server_port)
                    log(f"📡 Server set to {server_ip}:{server_port}")
                    st.session_state.state = STATE_SERVER_FOUND
                    st.rerun()
            
            render_logs()
    
    # ==================== DISCOVERING ====================
    elif state == STATE_DISCOVERING:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="stbox srch">🔍 Searching for server...</div>', unsafe_allow_html=True)
            
            with st.spinner("Running UDP discovery..."):
                result = run_discovery_subprocess()
            
            if result["status"] == "found":
                st.session_state.server_ip = result["ip"]
                st.session_state.server_port = result["port"]
                sm.server_ip = result["ip"]
                sm.server_port = result["port"]
                log(f"✅ Found server: {result['ip']}:{result['port']}")
                st.session_state.state = STATE_SERVER_FOUND
                st.rerun()
            elif result["status"] == "timeout":
                log("❌ Timeout - no server found")
                st.error("No server found. Try manual connection.")
                st.session_state.state = STATE_DISCONNECTED
                time.sleep(2)
                st.rerun()
            else:
                log(f"❌ Error: {result.get('error', 'Unknown')}")
                st.error(f"Discovery error. Try manual connection.")
                st.session_state.state = STATE_DISCONNECTED
                time.sleep(2)
                st.rerun()
    
    # ==================== SERVER FOUND ====================
    elif state == STATE_SERVER_FOUND:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            ip = st.session_state.server_ip
            port = st.session_state.server_port
            st.markdown(f'<div class="stbox on">🟢 Server: {ip}:{port}</div>', unsafe_allow_html=True)
            
            st.markdown("### 🎮 Game Setup")
            team = st.text_input("👥 Team Name (1-32 chars)", max_chars=32, value="", key="team_input")
            rounds = st.number_input("🔢 Rounds (1-255)", min_value=1, max_value=255, value=3, key="rounds_input")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🎮 Start Game", use_container_width=True, type="primary", key="start"):
                    if not team or len(team) < 1:
                        st.error("Enter a team name!")
                    else:
                        log(f"🔗 Connecting to {ip}:{port}...")
                        if sm.connect_tcp(ip, port):
                            log("✅ TCP connected")
                            if sm.send_settings(team, rounds):
                                log("✅ Game settings accepted!")
                                st.session_state.team = team
                                st.session_state.rounds = rounds
                                st.session_state.cur_round = 0
                                st.session_state.wins = 0
                                st.session_state.losses = 0
                                st.session_state.ties = 0
                                
                                # Start first round
                                start_new_round(sm)
                                st.rerun()
                            else:
                                st.error("Server rejected settings!")
                                log("❌ Rejected")
                        else:
                            st.error("Connection failed!")
                            log("❌ TCP failed")
            with c2:
                if st.button("🔙 Back", use_container_width=True, key="back_setup"):
                    reset()
                    st.rerun()
            
            render_logs()
    
    # ==================== PLAYER TURN ====================
    elif state == STATE_PLAYER_TURN:
        render_stats()
        render_table(hide_dealer=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("👆 HIT", use_container_width=True, type="primary", key="hit"):
                    card, result = sm.send_hit()
                    if card:
                        st.session_state.player_cards.append(card)
                        st.session_state.player_sum += card["value"]
                        st.session_state.new_card_index = len(st.session_state.player_cards) - 1
                        log(f"🎴 Drew {card['rank']} of {card['suit']} | Total: {st.session_state.player_sum}")
                        
                        if result == RESULT_SERVER_WIN:
                            log("💥 BUST! You lose this round.")
                            st.session_state.result = result
                            update_stats(result)
                            st.session_state.state = STATE_ROUND_END
                    st.rerun()
            
            with c2:
                if st.button("✋ STAND", use_container_width=True, key="stand"):
                    log("✋ Stand - Dealer's turn...")
                    st.session_state.new_card_index = -1
                    
                    if sm.send_stand():
                        st.session_state.state = STATE_DEALER_TURN
                    else:
                        log("❌ Error sending stand")
                        st.session_state.state = STATE_DISCONNECTED
                    st.rerun()
        
        render_logs()
    
    # ==================== DEALER TURN ====================
    elif state == STATE_DEALER_TURN:
        render_stats()
        
        # First, reveal hidden card if not done yet
        if len(st.session_state.dealer_cards) == 2 and st.session_state.dealer_cards[1].get("rank") == "?":
            # Reveal hidden card
            hidden_card = sm.receive_dealer_hidden_card()
            if hidden_card:
                st.session_state.dealer_cards[1] = hidden_card
                st.session_state.dealer_new_card_index = 1
                log(f"🔓 Dealer reveals: {hidden_card['rank']} of {hidden_card['suit']}")
        
        render_table(hide_dealer=False, dealer_drawing=True)
        
        st.markdown('<div class="dealer-drawing">🎰 Dealer is playing...</div>', unsafe_allow_html=True)
        
        render_logs()
        
        # Small delay for animation
        time.sleep(1.0)
        
        # Receive result first (as per new protocol)
        result = sm.receive_dealer_result()
        
        if result != RESULT_NOT_OVER:
            # Round is over
            result_str, _ = get_result_string(result)
            log(f"🎲 Round ended: {result_str}")
            st.session_state.result = result
            update_stats(result)
            st.session_state.dealer_new_card_index = -1
            st.session_state.state = STATE_ROUND_END
            st.rerun()
        else:
            # Dealer draws another card
            log("🃏 Dealer draws another card...")
            card = sm.receive_dealer_card()
            if card:
                st.session_state.dealer_cards.append(card)
                st.session_state.dealer_new_card_index = len(st.session_state.dealer_cards) - 1
                log(f"🃏 Dealer drew: {card['rank']} of {card['suit']}")
            
            # Stay in dealer turn state
            st.rerun()
    
    # ==================== ROUND END ====================
    elif state == STATE_ROUND_END:
        render_stats()
        render_table(hide_dealer=False)
        
        # Show result
        result_str, result_class = get_result_string(st.session_state.result)
        st.markdown(f'<div class="{result_class}">{result_str}</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.session_state.cur_round < st.session_state.rounds:
                if st.button("▶️ Next Round", use_container_width=True, type="primary", key="next"):
                    st.session_state.new_card_index = -1
                    st.session_state.dealer_new_card_index = -1
                    start_new_round(sm)
                    st.rerun()
            else:
                if st.button("🏁 Finish Game", use_container_width=True, type="primary", key="finish"):
                    st.session_state.state = STATE_GAME_OVER
                    st.rerun()
        
        render_logs()
    
    # ==================== GAME OVER ====================
    elif state == STATE_GAME_OVER:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div style="text-align:center;color:#ffd700;font-size:2.5rem;margin:1rem 0;">🎰 GAME OVER 🎰</div>', unsafe_allow_html=True)
            
            total = st.session_state.wins + st.session_state.losses + st.session_state.ties
            wr = (st.session_state.wins / total * 100) if total > 0 else 0
            
            st.markdown(f'''<div class="stats">
                <div class="sbox"><div class="slbl">Wins</div><div class="sval" style="color:#4caf50;">{st.session_state.wins}</div></div>
                <div class="sbox"><div class="slbl">Losses</div><div class="sval" style="color:#f44336;">{st.session_state.losses}</div></div>
                <div class="sbox"><div class="slbl">Ties</div><div class="sval" style="color:#ff9800;">{st.session_state.ties}</div></div>
                <div class="sbox"><div class="slbl">Win Rate</div><div class="sval" style="color:#ffd700;">{wr:.0f}%</div></div>
            </div>''', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🔄 Play Again", use_container_width=True, type="primary", key="again"):
                reset()
                st.rerun()
        
        render_logs()
    
    else:
        st.error(f"Unknown state: {state}")
        if st.button("Reset", key="reset_unknown"):
            reset()
            st.rerun()


def start_new_round(sm: SocketManager):
    """Initialize a new round"""
    st.session_state.cur_round += 1
    st.session_state.player_cards = []
    st.session_state.dealer_cards = []
    st.session_state.player_sum = 0
    st.session_state.result = None
    st.session_state.new_card_index = -1
    st.session_state.dealer_new_card_index = -1
    
    log(f"🎰 === Round {st.session_state.cur_round}/{st.session_state.rounds} ===")
    
    cards = sm.init_round()
    if cards and len(cards) == 4:
        dealer_visible, dealer_hidden, player1, player2 = cards
        
        # Dealer cards
        st.session_state.dealer_cards.append(dealer_visible)
        st.session_state.dealer_cards.append({"rank": "?", "suit": "?", "value": 0})  # Hidden
        log(f"🃏 Dealer shows: {dealer_visible['rank']} of {dealer_visible['suit']}")
        log("🃏 Dealer's second card is hidden")
        
        # Player cards
        st.session_state.player_cards.append(player1)
        st.session_state.player_cards.append(player2)
        st.session_state.player_sum = player1["value"] + player2["value"]
        log(f"🎴 Your card: {player1['rank']} of {player1['suit']}")
        log(f"🎴 Your card: {player2['rank']} of {player2['suit']}")
        log(f"📊 Your total: {st.session_state.player_sum}")
        
        # Check for initial bust (server sends result after cards)
        initial_result = sm.check_initial_bust()
        
        if initial_result == RESULT_SERVER_WIN:
            log("💥 BUST on initial deal! You lose this round.")
            st.session_state.result = initial_result
            update_stats(initial_result)
            st.session_state.state = STATE_ROUND_END
        else:
            st.session_state.state = STATE_PLAYER_TURN
    else:
        log("❌ Failed to receive cards")
        st.session_state.state = STATE_DISCONNECTED


if __name__ == "__main__":
    main()