##########################################
# poker_logic.py
# Updated to incorporate a custom push/fold ranking system 
# that prioritizes pairs, strong A combos, etc.
##########################################

import math
import itertools
import random
import csv
import os

# Attempt to import treys for card evaluations (optional if you need it)
try:
    from treys import Card, Evaluator, Deck
except ImportError:
    print("WARNING: 'treys' library not found. If you need card evaluation, install it via: pip install treys")
    Card = None
    Evaluator = None
    Deck = None

########################
# Basic Poker Constants
########################
RANKS = "AKQJT98765432"
TOTAL_COMBOS = 1326
SUITS_TREYS = "shdc"  # For treys usage if needed

# This is your custom push/fold hand ordering that prioritizes pairs first, 
# then suited Aces, etc. It's exactly what you had in your code.
SIMPLIFIED_HAND_RANKING = [
    # Pairs (Strongest to Weakest)
    "AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
    # Suited Aces
    "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
    # Suited Kings
    "KQs","KJs","KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
    # Suited Queens
    "QJs","QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
    # Suited Jacks
    "JTs","J9s","J8s","J7s","J6s","J5s","J4s","J3s","J2s",
    # Suited Tens
    "T9s","T8s","T7s","T6s","T5s","T4s","T3s","T2s",
    # Suited Nines... (etc. fill out if needed)
    "98s","97s","96s","95s","94s","93s","92s",
    "87s","86s","85s","84s","83s","82s",
    "76s","75s","74s","73s","72s",
    "65s","64s","63s","62s",
    "54s","53s","52s",
    "43s","42s",
    "32s",
    # Offsuit Aces
    "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
    # Offsuit Kings
    "KQo","KJo","KTo","K9o","K8o","K7o","K6o","K5o","K4o","K3o","K2o",
    # Offsuit Queens
    "QJo","QTo","Q9o","Q8o","Q7o","Q6o","Q5o","Q4o","Q3o","Q2o",
    # Offsuit Jacks
    "JTo","J9o","J8o","J7o","J6o","J5o","J4o","J3o","J2o",
    # Offsuit Tens ...
    "T9o","T8o","T7o","T6o","T5o","T4o","T3o","T2o",
    "98o","97o","96o","95o","94o","93o","92o",
    "87o","86o","85o","84o","83o","82o",
    "76o","75o","74o","73o","72o",
    "65o","64o","63o","62o",
    "54o","53o","52o",
    "43o","42o",
    "32o"
]

########################
# Utility: get combos
########################
def get_hand_combos(hand_str):
    """
    Returns how many combos a canonical hand string has:
    - Pair => 6 combos
    - Suited => 4 combos
    - Offsuit => 12 combos
    """
    if not isinstance(hand_str, str):
        return 0
    if len(hand_str) == 2:
        # Pair
        if hand_str[0] in RANKS and hand_str[1] == hand_str[0]:
            return 6
        else:
            return 0
    elif len(hand_str) == 3:
        if hand_str[0] in RANKS and hand_str[1] in RANKS and hand_str[0] != hand_str[1]:
            if hand_str[2] == 's':
                return 4
            elif hand_str[2] == 'o':
                return 12
    return 0

def calculate_range_percentage(hand_range):
    """
    Calculates what percentage of total combos a range represents.
    hand_range: set or list of canonical hand strings (e.g. ["AA", "AKs"])
    Returns float percentage (0-100)
    """
    if not isinstance(hand_range, (list, set)) or not hand_range:
        return 0.0
    total_combos = sum(get_hand_combos(h) for h in hand_range)
    return (total_combos / TOTAL_COMBOS) * 100.0

########################
# Utility: top X% 
########################
def get_top_hands_by_percentage(percentage):
    """
    Returns a list of canonical hands that cover top `percentage` of combos
    based on SIMPLIFIED_HAND_RANKING. We sum combos until we reach 
    (TOTAL_COMBOS * percentage/100). 
    """
    if not isinstance(percentage, (int,float)) or percentage <= 0:
        return []
    if percentage >= 100:
        # entire ranking
        return list(SIMPLIFIED_HAND_RANKING)

    combos_needed = TOTAL_COMBOS * (percentage / 100.0)
    selected_hands = []
    running_combos = 0

    for hand in SIMPLIFIED_HAND_RANKING:
        ccount = get_hand_combos(hand)
        if ccount == 0:
            continue
        if running_combos < combos_needed:
            selected_hands.append(hand)
            running_combos += ccount
        else:
            break

    return selected_hands

########################
# Parse CSV
########################
def parse_push_fold_csv(csv_data):
    """
    Parses lines from 'push ranges.csv' into a dictionary:
      { stack: { 'SB': float, 'B': float, 'CO': float, ... } }
    The CSV must have a column 'Stack' and columns for 'SB','B','CO','HJ','LJ','UTG+3','UTG+2','UTG+1','UTG'.
    Example row:
      Stack,SB,B,CO,HJ,LJ,UTG+3,UTG+2,UTG+1,UTG
      3,35,50,22,18,16,14,11,10,8
    """
    ranges = {}
    try:
        reader = csv.DictReader(csv_data.splitlines())
        headers = reader.fieldnames
        if not headers or 'Stack' not in headers:
            print("ERROR: CSV missing 'Stack' column header.")
            return {}

        # The columns we expect in the CSV for positions:
        expected_pos_headers = ['SB','B','CO','HJ','LJ','UTG+3','UTG+2','UTG+1','UTG']

        for row in reader:
            stack_str = row.get('Stack','').strip()
            if not stack_str:
                # skip empty stack line
                continue
            try:
                stack_val = float(stack_str)
            except ValueError:
                print(f"Skipping row with invalid stack '{stack_str}'")
                continue
            subdict = {}
            for col in expected_pos_headers:
                val_str = row.get(col,'').strip()
                if val_str:
                    try:
                        subdict[col] = float(val_str)
                    except ValueError:
                        print(f"WARNING: Invalid float at stack={stack_val}, col={col}, val={val_str}")
            ranges[stack_val] = subdict

    except csv.Error as e:
        print(f"ERROR parsing CSV data: {e}")
        return {}
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        return {}

    return ranges

########################
# Global dictionary: 
# { stack_size: { pos: percentage } }
########################
PUSH_FOLD_RANGES = {}

########################
# Attempt to load "push ranges.csv" at module load
########################
try:
    module_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(module_dir, "push ranges.csv")
    if os.path.isfile(csv_file_path):
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            csv_data = f.read()
        loaded = parse_push_fold_csv(csv_data)
        if loaded:
            PUSH_FOLD_RANGES = loaded
            print("INFO: push_fold_data loaded from 'push ranges.csv' at module load.")
        else:
            print("WARNING: 'push ranges.csv' parsed but got empty data dictionary.")
    else:
        print(f"WARNING: 'push ranges.csv' not found in {csv_file_path}. The CSV data won't be available.")
except Exception as e:
    print(f"ERROR loading 'push ranges.csv' at import: {e}")


########################
# get_push_fold_advice
########################
def get_push_fold_advice(stack_bb, position, players_left):
    """
    Provides push/fold advice based on:
      stack_bb, position, players_left.
    Returns a 4-tuple:
      (advice_str, range_list, percentage_float, tips_str)
    Example:
      -> ("Push top 18.0%", ["A2s","A3s","TT","JJ"], 18.0, "some tips")
    """
    if not isinstance(stack_bb, (int,float)) or stack_bb <= 0:
        return ("Error: Invalid Stack Size.", [], None, "No tips - invalid stack.")
    
    # Make sure data is loaded
    if not PUSH_FOLD_RANGES:
        # We might attempt to load again or just error
        return ("Error: 'push ranges.csv' data not loaded.", [], None, "No tips - data missing.")

    # Validate position
    # Our CSV uses columns = SB,B,CO,HJ,LJ,UTG+3,UTG+2,UTG+1,UTG
    if position not in ['SB','B','CO','HJ','LJ','UTG+3','UTG+2','UTG+1','UTG']:
        return (f"Error: Invalid position '{position}'.", [], None, "No tips - invalid position.")
    
    # Validate players_left
    if not isinstance(players_left, int) or players_left < 2 or players_left > 10:
        return ("Error: Invalid players_left (2-10).", [], None, "No tips - invalid player count.")

    # Find the closest stack in PUSH_FOLD_RANGES
    stack_keys = sorted(PUSH_FOLD_RANGES.keys())
    if not stack_keys:
        return ("Error: No stack data found in memory.", [], None, "No tips - no data.")
    # find closest
    try:
        closest_stack = min(stack_keys, key=lambda x: abs(x - stack_bb))
    except Exception as e:
        return (f"Error: Could not find nearest stack for {stack_bb}BB.", [], None, f"No tips - stack error: {e}")

    data_for_stack = PUSH_FOLD_RANGES.get(closest_stack)
    if not isinstance(data_for_stack, dict):
        return (f"Error: Data for {closest_stack}BB not found or invalid format.", [], None, "No tips - data error.")

    percentage = data_for_stack.get(position, None)
    if percentage is None:
        return (f"Error: Position '{position}' not found for stack={closest_stack}BB.", [], None, "No tips - data mismatch.")
    if not isinstance(percentage, (int,float)):
        return (f"Error: Invalid percentage for pos='{position}', stack={closest_stack}BB => {percentage}", [], None, "No tips - data mismatch.")

    # Get the top range
    push_range_list = get_top_hands_by_percentage(percentage)

    # Advice
    advice_str = f"Push top {percentage:.1f}%"
    # Tips string (customize as needed)
    tips_str = (f"At ~{closest_stack:.1f}BB in {position}, pushing around {percentage:.1f}% of hands is suggested. "
                "Adjust for ICM or if players are calling more tightly/loosely.")

    return (advice_str, push_range_list, percentage, tips_str)



########################
# Additional calculations if needed
# (Pot Odds, MDF, etc.) 
########################

def calculate_pot_odds(amount_to_call, pot_size_before_call):
    """Calculates Pot Odds as a percentage."""
    if not isinstance(amount_to_call, (int, float)) or not isinstance(pot_size_before_call, (int, float)):
        return "Invalid Input: Numeric values required."
    if amount_to_call <= 0:
        return "Invalid Input: Call must be > 0."
    final_pot_size = pot_size_before_call + amount_to_call
    if final_pot_size <= 0:
        return "Invalid Calculation: Final pot non-positive."
    pot_odds_decimal = amount_to_call / final_pot_size
    return pot_odds_decimal * 100

def calculate_required_equity(amount_to_call, pot_size_before_call):
    """Calculates the minimum equity required to break even on a call."""
    if not isinstance(amount_to_call, (int, float)) or not isinstance(pot_size_before_call, (int, float)):
        return "Invalid Input: Numeric values required."
    if amount_to_call <= 0:
        return "Invalid Input: Call must be > 0."
    denominator = pot_size_before_call + amount_to_call
    if denominator <= 0:
        return "Invalid Calculation: Total pot non-positive."
    required_equity_decimal = amount_to_call / denominator
    return required_equity_decimal * 100

def calculate_equity_from_outs(outs, street):
    """Calculates approximate equity using the Rule of 2 and 4."""
    if not isinstance(outs, int) or not (0 <= outs <= 47): # Allow 0 outs
        return "Invalid Input: Outs must be 0-47."
    if not isinstance(street, str):
        return "Invalid Input: Street must be 'flop' or 'turn'."
    street_lower = street.lower()
    if street_lower == 'flop': return min(outs * 4, 100)
    elif street_lower == 'turn': return min(outs * 2, 100)
    else: return "Invalid Input: Street must be 'flop' or 'turn'."

def calculate_mdf(bet_size, pot_size_before_bet):
    """Calculates the Minimum Defense Frequency (MDF) as a percentage."""
    if not isinstance(bet_size, (int, float)) or not isinstance(pot_size_before_bet, (int, float)):
        return "Invalid Input: Numeric values required."
    if bet_size <= 0 or pot_size_before_bet < 0:
        return "Invalid Input: Bet > 0, Pot >= 0."
    pot_after_bet = pot_size_before_bet + bet_size
    mdf_decimal = pot_size_before_bet / pot_after_bet
    return mdf_decimal * 100

def calculate_bluff_break_even(bet_size, pot_size_before_bet):
    """Calculates the frequency a bluff needs to work to be break-even."""
    if not isinstance(bet_size, (int, float)) or not isinstance(pot_size_before_bet, (int, float)):
        return "Invalid Input: Numeric values required."
    if bet_size <= 0 or pot_size_before_bet < 0:
        return "Invalid Input: Bet > 0, Pot >= 0."
    pot_plus_bet = pot_size_before_bet + bet_size
    break_even_decimal = bet_size / pot_plus_bet
    return break_even_decimal * 100

def parse_card_input(card_text):
    """Basic parsing for card input strings like "As", "Td", "2c"."""
    if not isinstance(card_text, str) or len(card_text) != 2: return None
    rank = card_text[0].upper()
    suit = card_text[1].lower()
    if rank not in RANKS or suit not in "shdc": return None
    return f"{rank}{suit}"

def calculate_spr(effective_stack, pot_size):
    """Calculates the Stack-to-Pot Ratio (SPR)."""
    if not isinstance(effective_stack, (int, float)) or not isinstance(pot_size, (int, float)):
        return "Invalid Input: Numeric values required."
    if effective_stack < 0 or pot_size <= 0:
        return "Invalid Input: Stack >= 0, Pot > 0."
    if pot_size < 1e-9: return float('inf')
    spr = effective_stack / pot_size
    return spr

def calculate_bet_size(pot_size, fraction):
    """Calculates the bet size based on a fraction of the pot."""
    if not isinstance(pot_size, (int, float)) or not isinstance(fraction, (int, float)):
        return "Invalid Input: Numeric values required."
    if pot_size <= 0 or fraction <= 0:
        return "Invalid Input: Pot > 0, Fraction > 0."
    bet_size = pot_size * fraction
    return bet_size

def calculate_icm(chip_stacks, payouts):
    """Calculates tournament equity ($EV) using a simplified CHIP CHOP model (NOT true ICM)."""
    num_players = len(chip_stacks)
    if num_players == 0: return []
    if not payouts or len(payouts) < num_players: return ["Error: Insufficient payouts provided."] * num_players
    total_chips_final = sum(chip_stacks)
    if total_chips_final <= 0: return ["Error: Total chips must be > 0."] * num_players
    relevant_payouts = payouts[:num_players]
    total_payout_final = sum(relevant_payouts)
    result_ev = []
    for stack in chip_stacks:
        if stack < 0: return ["Error: Negative stack size."] * num_players
        player_ev = (stack / total_chips_final) * total_payout_final
        result_ev.append(player_ev)
    return result_ev


# --- Hand Strength Evaluation & Equity Calculation Helpers (using treys) ---
# (These functions also remain unchanged from the user's provided version)

def hand_string_to_treys_cards(hand_str):
    """Converts a 2-card hand string like 'AsKh' or canonical like 'AKs'/'77'/'T9o'
       to a list of treys Card objects. Returns None on failure."""
    # (Code from previous correct version)
    cards = []
    if not isinstance(hand_str, str): return None
    if len(hand_str) == 4: # Specific cards like 'AsKh'
        c1_str = hand_str[0:2]; c2_str = hand_str[2:4]
        try:
            card1 = Card.new(c1_str); card2 = Card.new(c2_str)
            if card1 == card2: return None
            return [card1, card2]
        except ValueError: return None
    suits_to_use = random.sample(SUITS_TREYS, 2)
    if len(hand_str) == 2: # Pocket Pair
        rank = hand_str[0]
        if rank not in RANKS or hand_str[1] != rank: return None
        try: return [Card.new(rank + suits_to_use[0]), Card.new(rank + suits_to_use[1])]
        except ValueError: return None
    elif len(hand_str) == 3: # Non-pair
        rank1, rank2, type = hand_str[0], hand_str[1], hand_str[2]
        if rank1 not in RANKS or rank2 not in RANKS or rank1 == rank2: return None
        if type == 's':
            suit = random.choice(SUITS_TREYS)
            try: return [Card.new(rank1 + suit), Card.new(rank2 + suit)]
            except ValueError: return None
        elif type == 'o':
            try: return [Card.new(rank1 + suits_to_use[0]), Card.new(rank2 + suits_to_use[1])]
            except ValueError: return None
        else: return None
    else: return None


def board_string_to_treys_cards(board_list):
    """Converts a list of board card strings ['Ah', 'Kd', 'Tc'] to treys Card objects."""
    # (Code from previous correct version)
    cards = []
    if not isinstance(board_list, list): return None
    for card_str in board_list:
        parsed = parse_card_input(card_str)
        if parsed:
            try: cards.append(Card.new(parsed))
            except ValueError: print(f"ERROR: Invalid card string '{card_str}' in board."); return None
        elif card_str: print(f"ERROR: Invalid card format '{card_str}' in board."); return None
    return cards


def get_hand_strength(hand_card_list, board_card_list):
    """Evaluates the strength of a hand given a board using treys."""
    # (Code from previous correct version)
    if not isinstance(hand_card_list, list) or len(hand_card_list) != 2: return None, "Error: Hand must be a list of exactly 2 treys Card objects."
    if not isinstance(board_card_list, list) or not (0 <= len(board_card_list) <= 5): return None, "Error: Board must be a list of 0 to 5 treys Card objects."
    evaluator = Evaluator()
    all_cards = hand_card_list + board_card_list
    all_card_ints = [c for c in all_cards]
    if len(set(all_card_ints)) != len(all_card_ints):
        hand_str = Card.ints_to_pretty_str(hand_card_list) if hand_card_list else "N/A"
        board_str = Card.ints_to_pretty_str(board_card_list) if board_card_list else "N/A"
        print(f"ERROR: Duplicate cards detected between hand {hand_str} and board {board_str}.")
        return None, "Error: Duplicate cards between hand and board."
    try:
        if len(board_card_list) < 3: return None, f"Need at least 3 board cards to evaluate (have {len(board_card_list)})."
        score = evaluator.evaluate(hand_card_list, board_card_list)
        rank_class = evaluator.get_rank_class(score)
        rank_class_str = evaluator.class_to_string(rank_class)
        return score, rank_class_str
    except Exception as e: print(f"ERROR during hand strength evaluation: {e}"); return None, f"Error during evaluation: {e}"


def generate_combos(hand_range_list):
    """Generates all specific 2-card combos from a list of canonical hand range strings."""
    # (Code from previous correct version)
    combos = []
    if not isinstance(hand_range_list, list): return []
    for hand_str in hand_range_list:
        if not isinstance(hand_str, str): continue
        if len(hand_str) == 2: # Pair
            rank = hand_str[0]
            if rank not in RANKS or hand_str[1] != rank : continue
            suits_for_pair = list(SUITS_TREYS)
            for s1, s2 in itertools.combinations(suits_for_pair, 2):
                try: combos.append([Card.new(rank + s1), Card.new(rank + s2)])
                except ValueError: continue
        elif len(hand_str) == 3: # Non-pair
            rank1, rank2, type = hand_str[0], hand_str[1], hand_str[2]
            if rank1 not in RANKS or rank2 not in RANKS or rank1 == rank2: continue
            if type == 's':
                for suit in SUITS_TREYS:
                    try: combos.append([Card.new(rank1 + suit), Card.new(rank2 + suit)])
                    except ValueError: continue
            elif type == 'o':
                for s1 in SUITS_TREYS:
                    for s2 in SUITS_TREYS:
                        if s1 != s2:
                            try: combos.append([Card.new(rank1 + s1), Card.new(rank2 + s2)])
                            except ValueError: continue
    return combos


def calculate_hand_vs_range_equity(hero_hand_str, villain_range_list, board_str_list, simulations=10000):
    """Calculates hero's equity against a villain range on a given board via Monte Carlo."""
    # (Code from previous correct version)
    evaluator = Evaluator()
    hero_cards = hand_string_to_treys_cards(hero_hand_str)
    if not hero_cards: print(f"ERROR: Invalid hero hand format: {hero_hand_str}"); return None
    if len(set(hero_cards)) != 2: print(f"ERROR: Duplicate cards in hero hand: {hero_hand_str}"); return None
    board_cards = board_string_to_treys_cards(board_str_list)
    if board_cards is None: print(f"ERROR: Invalid board card format in: {board_str_list}"); return None
    if len(board_cards) > 5: print(f"ERROR: Board cannot have more than 5 cards: {len(board_cards)}"); return None
    known_dead_cards = hero_cards + board_cards
    if len(set(known_dead_cards)) != len(known_dead_cards): print(f"ERROR: Conflict between hero hand and board cards: {hero_hand_str} | {board_str_list}"); return None
    villain_combos_all = generate_combos(villain_range_list)
    if not villain_combos_all: print("ERROR: Villain range generated no valid combos."); return None
    valid_villain_combos = [combo for combo in villain_combos_all if not any(card in known_dead_cards for card in combo)]
    if not valid_villain_combos: print("Warning: No valid villain combos remain after removing known dead cards."); return 0.0
    wins = 0; ties = 0; total_sims_run = 0
    cards_to_deal = 5 - len(board_cards)
    for i in range(simulations):
        try:
            villain_hand = random.choice(valid_villain_combos)
            current_dead_cards = known_dead_cards + villain_hand
            if len(set(current_dead_cards)) != len(current_dead_cards): continue
            deck = Deck()
            dead_card_ints = set(c for c in current_dead_cards)
            deck.cards = [card for card in deck.cards if card not in dead_card_ints]
            runout_board = list(board_cards)
            if cards_to_deal > 0:
                 if len(deck.cards) < cards_to_deal: continue
                 drawn_cards = deck.draw(cards_to_deal)
                 if not isinstance(drawn_cards, list): drawn_cards = [drawn_cards]
                 runout_board.extend(drawn_cards)
            if len(runout_board) != 5: continue
            hero_score = evaluator.evaluate(hero_cards, runout_board)
            villain_score = evaluator.evaluate(villain_hand, runout_board)
            total_sims_run += 1
            if hero_score < villain_score: wins += 1
            elif hero_score == villain_score: ties += 1
        except Exception as e: print(f"UNEXPECTED ERROR during simulation run {i+1}: {e}. Skipping."); continue
    if total_sims_run == 0: print("ERROR: No simulations were successfully run."); return None
    equity = (wins + (ties / 2.0)) / total_sims_run
    return equity * 100.0

# --- Example Usage ---
if __name__ == "__main__":
    print("-" * 20)
    print("RUNNING poker_logic.py STANDALONE TESTS")
    print("-" * 20)
    # ... (keep all tests - they should reflect the updated logic now) ...
    print(f"Pot Odds (Call 50 into 150): {calculate_pot_odds(50, 150):.2f}%")
    print(f"Required Equity (Call 36 into 81): {calculate_required_equity(36, 81):.2f}%")
    print(f"Equity (9 outs on flop): {calculate_equity_from_outs(9, 'flop')}%")
    print(f"Equity (9 outs on turn): {calculate_equity_from_outs(9, 'turn')}%")
    print("-" * 20)
    test_range = {"AA", "KK", "QQ", "AKs", "AQs", "KQs"}
    print(f"Combos for {test_range}: {sum(get_hand_combos(h) for h in test_range)}")
    print(f"Percentage for {test_range}: {calculate_range_percentage(test_range):.2f}%")
    print("-" * 20)
    print(f"MDF (Bet 50 into 100): {calculate_mdf(50, 100):.2f}%")
    print(f"Bluff BE% (Bet 50 into 100): {calculate_bluff_break_even(50, 100):.2f}%")
    print("-" * 20)
    print(f"SPR (Stack 200, Pot 50): {calculate_spr(200, 50):.2f}")
    print("-" * 20)
    print(f"Bet Size (Pot 100, 1/2 Pot): {calculate_bet_size(100, 0.5):.2f}")
    print(f"Bet Size (Pot 75, 2/3 Pot): {calculate_bet_size(75, 2/3):.2f}")
    print("-" * 20)
    stacks = [1000, 500, 200]
    pays = [100, 60, 40]
    icm_ev = calculate_icm(stacks, pays)
    print(f"ICM EV (Chip Chop Placeholder) for Stacks {stacks}, Payouts {pays}:")
    if icm_ev and isinstance(icm_ev[0], str): print(icm_ev[0]) # Print error if needed
    elif icm_ev:
        for i, ev in enumerate(icm_ev): print(f" Player {i+1}: ${ev:.2f}")
    print("-" * 20)

    # Test Push/Fold Advice
    print("Testing Push/Fold Advice:")
    advice, p_range, p_perc = get_push_fold_advice(8, 'BTN', 6) # Use BTN
    print(f" Advice (8 BB, BTN, 6p): {advice}")
    if p_range: print(f"  Range ({len(p_range)} hands): {p_range[:10]}...")
    print(f"  Percentage: {p_perc if p_perc is not None else 'N/A'}")

    advice, p_range, p_perc = get_push_fold_advice(6, 'BTN', 9) # Test the problematic case
    print(f" Advice (6 BB, BTN, 9p): {advice}")
    if p_range: print(f"  Range ({len(p_range)} hands): {p_range[:10]}...")
    print(f"  Percentage: {p_perc if p_perc is not None else 'N/A'}") # Should now work if CSV has 'B' for 6BB

    advice, _, p_perc = get_push_fold_advice(12, 'UTG+1', 9)
    print(f" Advice (12 BB, UTG+1, 9p): {advice} ({p_perc}%)")
    advice, _, p_perc = get_push_fold_advice(5, 'CO', 3)
    print(f" Advice (5 BB, CO, 3p): {advice} ({p_perc}%)")
    advice, _, _ = get_push_fold_advice(10, 'XYZ', 6) # Invalid Position Test
    print(f" Advice (10 BB, XYZ, 6p): {advice}")
    advice, _, _ = get_push_fold_advice(10, 'UTG', 1) # Invalid Player Count Test
    print(f" Advice (10 BB, UTG, 1p): {advice}")
    advice, _, _ = get_push_fold_advice(-5, 'SB', 5) # Invalid Stack Test
    print(f" Advice (-5 BB, SB, 5p): {advice}")

    # Test range generation edge cases
    print("Testing Range Generation:")
    range_0 = get_top_hands_by_percentage(0)
    print(f" 0% Range: {range_0} (Count: {len(range_0)})")
    range_1 = get_top_hands_by_percentage(0.5) # Very small %
    print(f" ~0.5% Range: {range_1} (Count: {len(range_1)}) -> {calculate_range_percentage(set(range_1)):.2f}% combos")
    range_10 = get_top_hands_by_percentage(10)
    print(f" 10% Range (first 10): {range_10[:10]}... (Count: {len(range_10)}) -> {calculate_range_percentage(set(range_10)):.2f}% combos")
    range_100 = get_top_hands_by_percentage(100)
    print(f" 100% Range (Count): {len(range_100)} -> {calculate_range_percentage(set(range_100)):.2f}% combos")


    # Test Hand Strength (Optional, commented out)
    # print("-" * 20)
    # print("Testing Hand Strength:")
    # hs_hand = ["As", "Ks"]; hs_board = ["Qs", "Js", "Ts", "2d", "3h"]
    # hs_hand_cards = [Card.new(c) for c in hs_hand]; hs_board_cards = [Card.new(c) for c in hs_board]
    # hs_score, hs_rank = get_hand_strength(hs_hand_cards, hs_board_cards)
    # print(f" Hand Strength for {hs_hand} on {hs_board}: Rank={hs_rank} (Score: {hs_score})")

    # Test Equity Calculation (Optional, commented out)
    # print("-" * 20)
    # print("Testing Equity Calculation (may take a moment):")
    # hero = "AsKc"; villain_r = ["QQ", "JJ", "AKs", "AQs", "KQs"]; board = ["Qh", "Tc", "2d"]
    # equity = calculate_hand_vs_range_equity(hero, villain_r, board, simulations=1000)
    # if equity is not None: print(f" Equity for {hero} vs {villain_r} on {board}: {equity:.2f}%")
    # else: print(f" Equity calculation failed for {hero} vs {villain_r} on {board}")

    print("-" * 20)
    print("poker_logic.py tests finished.")
