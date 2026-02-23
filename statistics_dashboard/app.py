"""
Blackjack Statistics Dashboard
Displays various graphs and statistics from game data
"""

import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import Counter
import numpy as np

# Card values for calculating hand totals
CARD_VALUES = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11
}

SUIT_SYMBOLS = {'H': '♥️', 'D': '♦️', 'C': '♣️', 'S': '♠️'}

def load_data(file_path: str = "storage/data/db_mock.json") -> dict:
    """Load game data from JSON file"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        # Support both 'default' and 'games' keys
        return data.get("games", data.get("default", {}))
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return {}


def calculate_hand_value(cards: list) -> int:
    """Calculate the value of a hand"""
    total = 0
    aces = 0
    for card in cards:
        rank = card.get('rank', '0')
        if rank == 'A':
            aces += 1
            total += 11
        else:
            total += CARD_VALUES.get(rank, 0)
    
    # Adjust for aces
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    
    return total


def calculate_data_size(client_cards: list, server_cards: list, num_rounds: int) -> int:
    """
    Calculate total data size sent for a game.
    Base size: 33 bytes
    Client cards: first 2 cards = 3 bytes each, rest = 8 bytes each
    Server cards: all cards = 4 bytes each
    Round results: 1 byte per round
    """
    base_size = 33
    
    # Client cards size
    client_size = 0
    for round_cards in client_cards:
        for i, card in enumerate(round_cards):
            if i < 2:
                client_size += 3  # First 2 cards are 3 bytes
            else:
                client_size += 8  # Hit cards are 8 bytes
    
    # Server cards size
    server_size = 0
    for round_cards in server_cards:
        for card in round_cards:
            server_size += 4  # All server cards are 4 bytes
    
    # Round results
    round_results_size = num_rounds
    
    return base_size + client_size + server_size + round_results_size


def process_data(data: dict) -> dict:
    """Process raw data into statistics"""
    stats = {
        'total_games': 0,
        'total_rounds': 0,
        'client_wins': 0,
        'dealer_wins': 0,
        'total_ties': 0,
        'client_busts': 0,
        'server_busts': 0,
        'client_hand_values': [],
        'server_hand_values': [],
        'hits_per_round': [],
        'all_client_cards': [],
        'all_server_cards': [],
        'response_times': [],
        'avg_response_per_game': [],
        'teams': [],
        'team_stats': [],
        'game_times': [],
        'total_game_time': 0,
        'data_sizes': [],
        'total_data_size': 0,
        'data_size_per_game': [],
    }
    
    for game_id, game in data.items():
        stats['total_games'] += 1
        num_rounds = game.get('number_of_rounds', 0)
        stats['total_rounds'] += num_rounds
        
        game_stats = game.get('game_stats', {})
        client_wins = game_stats.get('3', 0)
        dealer_wins = game_stats.get('2', 0)
        ties = game_stats.get('1', 0)
        
        stats['client_wins'] += client_wins
        stats['dealer_wins'] += dealer_wins
        stats['total_ties'] += ties
        
        # Bust counts
        stats['client_busts'] += len(game.get('client_round_busts', []))
        stats['server_busts'] += len(game.get('server_round_busts', []))
        
        # Process cards
        client_cards = game.get('client_game_cards', [])
        server_cards = game.get('server_game_cards', [])
        
        for round_cards in client_cards:
            if round_cards:
                hand_value = calculate_hand_value(round_cards)
                stats['client_hand_values'].append(hand_value)
                hits = len(round_cards) - 2  # Initial 2 cards don't count as hits
                stats['hits_per_round'].append(max(0, hits))
                for card in round_cards:
                    stats['all_client_cards'].append(card)
        
        for round_cards in server_cards:
            if round_cards:
                hand_value = calculate_hand_value(round_cards)
                stats['server_hand_values'].append(hand_value)
                for card in round_cards:
                    stats['all_server_cards'].append(card)
        
        # Response times
        response_times = game.get('client_response_time_in_game', [])
        game_times = []
        for round_times in response_times:
            for t in round_times:
                stats['response_times'].append(t)
                game_times.append(t)
        
        if game_times:
            stats['avg_response_per_game'].append({
                'team': game.get('team_name', 'Unknown'),
                'avg_time': np.mean(game_times),
                'total_time': sum(game_times),
                'rounds': num_rounds
            })
        
        # Game time - always add even if 0, to avoid empty list issues
        total_game_time = game.get('total_game_time', 0)
        stats['game_times'].append({
            'team': game.get('team_name', 'Unknown'),
            'time': total_game_time,
            'rounds': num_rounds
        })
        stats['total_game_time'] += total_game_time
        
        # Data size calculation
        data_size = calculate_data_size(client_cards, server_cards, num_rounds)
        stats['data_sizes'].append(data_size)
        stats['total_data_size'] += data_size
        stats['data_size_per_game'].append({
            'team': game.get('team_name', 'Unknown'),
            'size': data_size,
            'rounds': num_rounds
        })
        
        # Team stats
        stats['teams'].append(game.get('team_name', 'Unknown'))
        stats['team_stats'].append({
            'team': game.get('team_name', 'Unknown'),
            'client_wins': client_wins,
            'dealer_wins': dealer_wins,
            'ties': ties,
            'rounds': num_rounds,
            'win_rate': (client_wins / (client_wins + dealer_wins + ties) * 100) if (client_wins + dealer_wins + ties) > 0 else 0
        })
    
    return stats


def inject_css():
    """Inject custom CSS"""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0f3460 100%);
    }
    
    h1, h2, h3 {
        text-align: center !important;
    }
    
    /* Center tabs */
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
        gap: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1.5rem;
    }
    
    .main-title {
        font-size: 3rem;
        text-align: center;
        background: linear-gradient(135deg, #ffd700 0%, #ffaa00 50%, #ff8c00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        text-align: center;
        color: #888;
        letter-spacing: 0.2em;
        margin-bottom: 2rem;
    }
    
    .stat-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
    
    .stat-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .stat-label {
        color: #aaa;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    
    .win { color: #4caf50; }
    .loss { color: #f44336; }
    .tie { color: #ff9800; }
    .neutral { color: #2196f3; }
    .purple { color: #9c27b0; }
    .cyan { color: #00bcd4; }
    
    .section-title {
        color: #ffd700;
        font-size: 1.5rem;
        margin: 2rem 0 1rem 0;
        text-align: center;
        letter-spacing: 0.1em;
    }
    
    .card-display {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 55px;
        background: white;
        border-radius: 5px;
        margin: 3px;
        font-size: 0.9rem;
        font-weight: bold;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    .hearts, .diamonds { color: #e63946; }
    .clubs, .spades { color: #1d3557; }
    </style>
    """, unsafe_allow_html=True)


def render_stat_card(value, label, color_class="neutral"):
    """Render a statistic card"""
    return f"""
    <div class="stat-card">
        <div class="stat-value {color_class}">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    """


def main():
    st.set_page_config(
        page_title="Blackjack Statistics",
        page_icon="📊",
        layout="wide"
    )
    
    inject_css()
    
    # Title
    st.markdown('<div class="main-title">📊 BLACKJACK STATISTICS</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">GAME ANALYTICS DASHBOARD</div>', unsafe_allow_html=True)
    
    # Load and process data
    data = load_data()
    
    if not data:
        st.error("No data found. Please ensure db_mock.json is in the same directory.")
        return
    
    stats = process_data(data)
    
    # ==================== TABS ====================
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Overview",
        "🎯 Results",
        "🃏 Hand Values",
        "🎴 Cards",
        "⏱️ Time & Data",
        "🏆 Leaderboard"
    ])
    
    # ==================== TAB 1: OVERVIEW ====================
    with tab1:
        st.markdown('<div class="section-title">📈 OVERVIEW</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(render_stat_card(stats['total_games'], "Total Games", "neutral"), unsafe_allow_html=True)
        with col2:
            st.markdown(render_stat_card(stats['total_rounds'], "Total Rounds", "cyan"), unsafe_allow_html=True)
        with col3:
            st.markdown(render_stat_card(stats['client_wins'], "Client Wins", "win"), unsafe_allow_html=True)
        with col4:
            st.markdown(render_stat_card(stats['dealer_wins'], "Dealer Wins", "loss"), unsafe_allow_html=True)
        with col5:
            st.markdown(render_stat_card(stats['total_ties'], "Ties", "tie"), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Win Rate and Bust Rates
        total_results = stats['client_wins'] + stats['dealer_wins'] + stats['total_ties']
        win_rate = (stats['client_wins'] / total_results * 100) if total_results > 0 else 0
        client_bust_rate = (stats['client_busts'] / stats['total_rounds'] * 100) if stats['total_rounds'] > 0 else 0
        server_bust_rate = (stats['server_busts'] / stats['total_rounds'] * 100) if stats['total_rounds'] > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(render_stat_card(f"{win_rate:.1f}%", "Client Win Rate", "win"), unsafe_allow_html=True)
        with col2:
            st.markdown(render_stat_card(f"{client_bust_rate:.1f}%", "Client Bust Rate", "loss"), unsafe_allow_html=True)
        with col3:
            st.markdown(render_stat_card(f"{server_bust_rate:.1f}%", "Dealer Bust Rate", "purple"), unsafe_allow_html=True)
        with col4:
            avg_hits = np.mean(stats['hits_per_round']) if stats['hits_per_round'] else 0
            st.markdown(render_stat_card(f"{avg_hits:.2f}", "Avg Hits/Round", "cyan"), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Quick summary pie chart
        col1, col2 = st.columns(2)
        with col1:
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Client Wins', 'Dealer Wins', 'Ties'],
                values=[stats['client_wins'], stats['dealer_wins'], stats['total_ties']],
                hole=0.4,
                marker_colors=['#4caf50', '#f44336', '#ff9800'],
                textinfo='label+percent',
                textfont_size=14
            )])
            fig_pie.update_layout(
                title="Overall Results Distribution",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                showlegend=True,
                legend=dict(font=dict(color='white')),
                height=350
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Bust comparison
            fig_bust = go.Figure()
            fig_bust.add_trace(go.Bar(
                x=['Client Busts', 'Dealer Busts'],
                y=[stats['client_busts'], stats['server_busts']],
                marker_color=['#f44336', '#9c27b0'],
                text=[stats['client_busts'], stats['server_busts']],
                textposition='outside'
            ))
            fig_bust.update_layout(
                title="Bust Comparison",
                yaxis_title="Count",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                height=350
            )
            st.plotly_chart(fig_bust, use_container_width=True)
    
    # ==================== TAB 2: RESULTS ====================
    with tab2:
        st.markdown('<div class="section-title">🎯 GAME RESULTS DISTRIBUTION</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart for overall results
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Client Wins', 'Dealer Wins', 'Ties'],
                values=[stats['client_wins'], stats['dealer_wins'], stats['total_ties']],
                hole=0.4,
                marker_colors=['#4caf50', '#f44336', '#ff9800'],
                textinfo='label+percent',
                textfont_size=14
            )])
            fig_pie.update_layout(
                title="Overall Results Distribution",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                showlegend=True,
                legend=dict(font=dict(color='white')),
                height=400
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Bar chart for team performance
            team_df = pd.DataFrame(stats['team_stats'])
            team_df = team_df.sort_values('win_rate', ascending=True).tail(10)
            
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                y=team_df['team'],
                x=team_df['client_wins'],
                name='Client Wins',
                orientation='h',
                marker_color='#4caf50'
            ))
            fig_bar.add_trace(go.Bar(
                y=team_df['team'],
                x=team_df['dealer_wins'],
                name='Dealer Wins',
                orientation='h',
                marker_color='#f44336'
            ))
            fig_bar.add_trace(go.Bar(
                y=team_df['team'],
                x=team_df['ties'],
                name='Ties',
                orientation='h',
                marker_color='#ff9800'
            ))
            fig_bar.update_layout(
                title="Top 10 Teams by Win Rate",
                barmode='stack',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                xaxis_title="Games",
                yaxis_title="",
                legend=dict(font=dict(color='white')),
                height=400
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Hits analysis
        st.markdown('<div class="section-title">👆 HITS PER ROUND ANALYSIS</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if stats['hits_per_round']:
                hit_counts = Counter(stats['hits_per_round'])
                max_hits = max(stats['hits_per_round']) if stats['hits_per_round'] else 0
                
                fig_hits = go.Figure()
                fig_hits.add_trace(go.Bar(
                    x=list(range(max_hits + 1)),
                    y=[hit_counts.get(i, 0) for i in range(max_hits + 1)],
                    marker_color='#ff9800',
                    text=[hit_counts.get(i, 0) for i in range(max_hits + 1)],
                    textposition='outside'
                ))
                fig_hits.update_layout(
                    title="Hits Per Round Distribution",
                    xaxis_title="Number of Hits",
                    yaxis_title="Frequency",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    height=350
                )
                st.plotly_chart(fig_hits, use_container_width=True)
        
        with col2:
            hit_categories = ['0 Hits\n(Stand)', '1 Hit', '2 Hits', '3+ Hits']
            stand_rounds = sum(1 for h in stats['hits_per_round'] if h == 0)
            one_hit = sum(1 for h in stats['hits_per_round'] if h == 1)
            two_hits = sum(1 for h in stats['hits_per_round'] if h == 2)
            three_plus = sum(1 for h in stats['hits_per_round'] if h >= 3)
            
            fig_hit_dist = go.Figure()
            fig_hit_dist.add_trace(go.Bar(
                x=hit_categories,
                y=[stand_rounds, one_hit, two_hits, three_plus],
                marker_color=['#4caf50', '#2196f3', '#ff9800', '#f44336'],
                text=[stand_rounds, one_hit, two_hits, three_plus],
                textposition='outside'
            ))
            fig_hit_dist.update_layout(
                title="Player Decision Distribution",
                xaxis_title="Strategy",
                yaxis_title="Number of Rounds",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                height=350
            )
            st.plotly_chart(fig_hit_dist, use_container_width=True)
    
    # ==================== TAB 3: HAND VALUES ====================
    with tab3:
        st.markdown('<div class="section-title">🃏 HAND VALUE ANALYSIS</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if stats['client_hand_values']:
                fig_hist_player = go.Figure()
                fig_hist_player.add_trace(go.Histogram(
                    x=stats['client_hand_values'],
                    nbinsx=15,
                    marker_color='#2196f3',
                    opacity=0.8,
                    name='Player Hands'
                ))
                fig_hist_player.update_layout(
                    title="Player Final Hand Values",
                    xaxis_title="Hand Value",
                    yaxis_title="Frequency",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    bargap=0.1,
                    height=400
                )
                fig_hist_player.add_vline(x=21, line_dash="dash", line_color="#4caf50", annotation_text="21")
                st.plotly_chart(fig_hist_player, use_container_width=True)
        
        with col2:
            if stats['server_hand_values']:
                fig_hist_dealer = go.Figure()
                fig_hist_dealer.add_trace(go.Histogram(
                    x=stats['server_hand_values'],
                    nbinsx=15,
                    marker_color='#9c27b0',
                    opacity=0.8,
                    name='Dealer Hands'
                ))
                fig_hist_dealer.update_layout(
                    title="Dealer Final Hand Values",
                    xaxis_title="Hand Value",
                    yaxis_title="Frequency",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    bargap=0.1,
                    height=400
                )
                fig_hist_dealer.add_vline(x=21, line_dash="dash", line_color="#4caf50", annotation_text="21")
                st.plotly_chart(fig_hist_dealer, use_container_width=True)
        
        # Average hand values
        avg_player_hand = np.mean(stats['client_hand_values']) if stats['client_hand_values'] else 0
        avg_dealer_hand = np.mean(stats['server_hand_values']) if stats['server_hand_values'] else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(render_stat_card(f"{avg_player_hand:.1f}", "Avg Player Hand", "neutral"), unsafe_allow_html=True)
        with col2:
            st.markdown(render_stat_card(f"{avg_dealer_hand:.1f}", "Avg Dealer Hand", "purple"), unsafe_allow_html=True)
        with col3:
            max_player = max(stats['client_hand_values']) if stats['client_hand_values'] else 0
            st.markdown(render_stat_card(max_player, "Max Player Hand", "win"), unsafe_allow_html=True)
        with col4:
            blackjacks = sum(1 for v in stats['client_hand_values'] if v == 21)
            st.markdown(render_stat_card(blackjacks, "Player Blackjacks", "cyan"), unsafe_allow_html=True)
    
    # ==================== TAB 4: CARDS ====================
    with tab4:
        st.markdown('<div class="section-title">🎴 CARD STATISTICS</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            all_cards = stats['all_client_cards'] + stats['all_server_cards']
            rank_counts = Counter([card['rank'] for card in all_cards])
            
            ranks_order = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
            rank_data = [(r, rank_counts.get(r, 0)) for r in ranks_order]
            
            fig_ranks = go.Figure()
            fig_ranks.add_trace(go.Bar(
                x=[r[0] for r in rank_data],
                y=[r[1] for r in rank_data],
                marker_color=['#e63946' if r[0] == 'A' else '#2196f3' for r in rank_data],
                text=[r[1] for r in rank_data],
                textposition='outside'
            ))
            fig_ranks.update_layout(
                title="Card Rank Distribution (All Games)",
                xaxis_title="Rank",
                yaxis_title="Frequency",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                height=400
            )
            st.plotly_chart(fig_ranks, use_container_width=True)
        
        with col2:
            suit_counts = Counter([card['suit'] for card in all_cards])
            
            suit_labels = [f"{SUIT_SYMBOLS.get(s, s)} {s}" for s in ['H', 'D', 'C', 'S']]
            suit_values = [suit_counts.get(s, 0) for s in ['H', 'D', 'C', 'S']]
            
            fig_suits = go.Figure(data=[go.Pie(
                labels=suit_labels,
                values=suit_values,
                hole=0.3,
                marker_colors=['#e63946', '#e63946', '#1d3557', '#1d3557'],
                textinfo='label+percent'
            )])
            fig_suits.update_layout(
                title="Suit Distribution",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                height=400
            )
            st.plotly_chart(fig_suits, use_container_width=True)
        
        # Card stats
        all_cards = stats['all_client_cards'] + stats['all_server_cards']
        rank_counts = Counter([card['rank'] for card in all_cards])
        ace_count = rank_counts.get('A', 0)
        total_cards = len(all_cards)
        ace_frequency = (ace_count / total_cards * 100) if total_cards > 0 else 0
        most_common_rank = rank_counts.most_common(1)[0] if rank_counts else ('N/A', 0)
        face_cards = sum(rank_counts.get(r, 0) for r in ['J', 'Q', 'K'])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(render_stat_card(total_cards, "Total Cards Dealt", "neutral"), unsafe_allow_html=True)
        with col2:
            st.markdown(render_stat_card(f"{ace_frequency:.1f}%", "Ace Frequency", "loss"), unsafe_allow_html=True)
        with col3:
            st.markdown(render_stat_card(most_common_rank[0], "Most Common Rank", "win"), unsafe_allow_html=True)
        with col4:
            st.markdown(render_stat_card(face_cards, "Face Cards (J/Q/K)", "purple"), unsafe_allow_html=True)
    
    # ==================== TAB 5: TIME & DATA ====================
    with tab5:
        st.markdown('<div class="section-title">⏱️ RESPONSE TIME ANALYSIS</div>', unsafe_allow_html=True)
        
        # Response time stats cards
        if stats['response_times']:
            avg_rt = np.mean(stats['response_times'])
            min_rt = np.min(stats['response_times'])
            max_rt = np.max(stats['response_times'])
            median_rt = np.median(stats['response_times'])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(render_stat_card(f"{avg_rt:.2f}s", "Avg Response Time", "cyan"), unsafe_allow_html=True)
            with col2:
                st.markdown(render_stat_card(f"{min_rt:.2f}s", "Fastest Response", "win"), unsafe_allow_html=True)
            with col3:
                st.markdown(render_stat_card(f"{max_rt:.2f}s", "Slowest Response", "loss"), unsafe_allow_html=True)
            with col4:
                st.markdown(render_stat_card(f"{median_rt:.2f}s", "Median Response", "purple"), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if stats['response_times']:
                fig_rt_hist = go.Figure()
                fig_rt_hist.add_trace(go.Histogram(
                    x=stats['response_times'],
                    nbinsx=20,
                    marker_color='#00bcd4',
                    opacity=0.8
                ))
                fig_rt_hist.update_layout(
                    title="Response Time Distribution",
                    xaxis_title="Response Time (seconds)",
                    yaxis_title="Frequency",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    height=350
                )
                st.plotly_chart(fig_rt_hist, use_container_width=True)
        
        with col2:
            if stats['avg_response_per_game']:
                rt_df = pd.DataFrame(stats['avg_response_per_game'])
                rt_df = rt_df.sort_values('avg_time', ascending=True)
                
                fig_rt_bar = go.Figure()
                fig_rt_bar.add_trace(go.Bar(
                    x=rt_df['avg_time'],
                    y=rt_df['team'],
                    orientation='h',
                    marker_color='#00bcd4',
                    text=[f"{t:.2f}s" for t in rt_df['avg_time']],
                    textposition='outside'
                ))
                fig_rt_bar.update_layout(
                    title="Average Response Time by Team",
                    xaxis_title="Average Response Time (s)",
                    yaxis_title="",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    height=350
                )
                st.plotly_chart(fig_rt_bar, use_container_width=True)
        
        st.markdown('<div class="section-title">🕐 GAME TIME ANALYTICS</div>', unsafe_allow_html=True)
        
        # Game Time Stats
        game_times_values = [g['time'] for g in stats['game_times']] if stats['game_times'] else [0]
        avg_game_time = np.mean(game_times_values)
        min_game_time = min(game_times_values)
        max_game_time = max(game_times_values)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(render_stat_card(f"{stats['total_game_time']:.1f}s", "Total Game Time", "cyan"), unsafe_allow_html=True)
        with col2:
            st.markdown(render_stat_card(f"{avg_game_time:.1f}s", "Avg Game Time", "neutral"), unsafe_allow_html=True)
        with col3:
            st.markdown(render_stat_card(f"{min_game_time:.1f}s", "Fastest Game", "win"), unsafe_allow_html=True)
        with col4:
            st.markdown(render_stat_card(f"{max_game_time:.1f}s", "Longest Game", "loss"), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Game time by team
            if stats['game_times']:
                game_time_df = pd.DataFrame(stats['game_times'])
                game_time_df = game_time_df.sort_values('time', ascending=True)
                
                fig_game_time = go.Figure()
                fig_game_time.add_trace(go.Bar(
                    x=game_time_df['time'],
                    y=game_time_df['team'],
                    orientation='h',
                    marker_color='#9c27b0',
                    text=[f"{t:.1f}s" for t in game_time_df['time']],
                    textposition='outside'
                ))
                fig_game_time.update_layout(
                    title="Game Time by Team",
                    xaxis_title="Total Game Time (s)",
                    yaxis_title="",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    height=350
                )
                st.plotly_chart(fig_game_time, use_container_width=True)
        
        with col2:
            # Game time histogram
            if stats['game_times']:
                fig_time_hist = go.Figure()
                fig_time_hist.add_trace(go.Histogram(
                    x=[g['time'] for g in stats['game_times']],
                    nbinsx=15,
                    marker_color='#9c27b0',
                    opacity=0.8
                ))
                fig_time_hist.update_layout(
                    title="Game Time Distribution",
                    xaxis_title="Game Time (seconds)",
                    yaxis_title="Frequency",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    height=350
                )
                st.plotly_chart(fig_time_hist, use_container_width=True)
        
        st.markdown('<div class="section-title">📦 DATA SIZE ANALYTICS</div>', unsafe_allow_html=True)
        
        # Data Size Stats
        avg_data_size = np.mean(stats['data_sizes']) if stats['data_sizes'] else 0
        min_data_size = min(stats['data_sizes']) if stats['data_sizes'] else 0
        max_data_size = max(stats['data_sizes']) if stats['data_sizes'] else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_bytes = stats['total_data_size']
            if total_bytes >= 1024:
                size_str = f"{total_bytes/1024:.2f} KB"
            else:
                size_str = f"{total_bytes} B"
            st.markdown(render_stat_card(size_str, "Total Data Sent", "cyan"), unsafe_allow_html=True)
        with col2:
            st.markdown(render_stat_card(f"{avg_data_size:.0f} B", "Avg Data/Game", "neutral"), unsafe_allow_html=True)
        with col3:
            st.markdown(render_stat_card(f"{min_data_size} B", "Min Data/Game", "win"), unsafe_allow_html=True)
        with col4:
            st.markdown(render_stat_card(f"{max_data_size} B", "Max Data/Game", "loss"), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if stats['data_size_per_game']:
                data_size_df = pd.DataFrame(stats['data_size_per_game'])
                data_size_df = data_size_df.sort_values('size', ascending=True)
                
                fig_data_size = go.Figure()
                fig_data_size.add_trace(go.Bar(
                    x=data_size_df['size'],
                    y=data_size_df['team'],
                    orientation='h',
                    marker_color='#ff9800',
                    text=[f"{s} B" for s in data_size_df['size']],
                    textposition='outside'
                ))
                fig_data_size.update_layout(
                    title="Data Size by Team",
                    xaxis_title="Data Size (bytes)",
                    yaxis_title="",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    height=350
                )
                st.plotly_chart(fig_data_size, use_container_width=True)
        
        with col2:
            if stats['data_sizes']:
                fig_size_hist = go.Figure()
                fig_size_hist.add_trace(go.Histogram(
                    x=stats['data_sizes'],
                    nbinsx=15,
                    marker_color='#4caf50',
                    opacity=0.8
                ))
                fig_size_hist.update_layout(
                    title="Data Size Distribution",
                    xaxis_title="Data Size (bytes)",
                    yaxis_title="Frequency",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    height=350
                )
                st.plotly_chart(fig_size_hist, use_container_width=True)
    
    # ==================== TAB 6: LEADERBOARD ====================
    with tab6:
        st.markdown('<div class="section-title">🏆 TEAM LEADERBOARD</div>', unsafe_allow_html=True)
        
        team_df = pd.DataFrame(stats['team_stats'])
        team_df = team_df.sort_values(['win_rate', 'client_wins'], ascending=[False, False])
        
        # Top 3 podium
        if len(team_df) >= 3:
            col1, col2, col3 = st.columns(3)
            top3 = team_df.head(3).to_dict('records')
            
            with col1:
                st.markdown(f"""
                <div class="stat-card" style="border: 2px solid #c0c0c0;">
                    <div style="font-size: 2rem;">🥈</div>
                    <div class="stat-value" style="font-size: 1.5rem; color: #c0c0c0;">{top3[1]['team']}</div>
                    <div class="stat-label">{top3[1]['win_rate']:.1f}% Win Rate</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stat-card" style="border: 2px solid #ffd700;">
                    <div style="font-size: 2.5rem;">🥇</div>
                    <div class="stat-value" style="font-size: 1.8rem; color: #ffd700;">{top3[0]['team']}</div>
                    <div class="stat-label">{top3[0]['win_rate']:.1f}% Win Rate</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="stat-card" style="border: 2px solid #cd7f32;">
                    <div style="font-size: 2rem;">🥉</div>
                    <div class="stat-value" style="font-size: 1.5rem; color: #cd7f32;">{top3[2]['team']}</div>
                    <div class="stat-label">{top3[2]['win_rate']:.1f}% Win Rate</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Full leaderboard table
        st.dataframe(
            team_df[['team', 'client_wins', 'dealer_wins', 'ties', 'rounds', 'win_rate']].rename(columns={
                'team': 'Team',
                'client_wins': 'Client Wins',
                'dealer_wins': 'Dealer Wins',
                'ties': 'Ties',
                'rounds': 'Rounds',
                'win_rate': 'Win Rate %'
            }).style.format({'Win Rate %': '{:.1f}'}).background_gradient(
                subset=['Win Rate %'],
                cmap='RdYlGn'
            ),
            use_container_width=True,
            hide_index=True
        )
    
    # Footer
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem; margin-top: 2rem;">
        <p>📊 Blackjack Statistics Dashboard</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()