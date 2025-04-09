# poker_logic.py
# Contains the core poker calculation functions

import math
import itertools
import random # Import random for safer selection
from treys import Card, Evaluator, Deck # Import treys components

# --- Hand Range Constants ---
RANKS = "AKQJT98765432"
TOTAL_COMBOS = 1326

# Generate all 169 canonical hand representations (e.g., "AKs", "77", "T9o")
def get_all_hands():
    hands = []
    for i in range(len(RANKS)):
        for j in range(i, len(RANKS)):
            rank1 = RANKS[i]
            rank2 = RANKS[j]
            if i == j:  # Pocket pair
                hands.append(f"{rank1}{rank2}")
            else:
                hands.append(f"{rank1}{rank2}s") # Suited
                hands.append(f"{rank1}{rank2}o") # Offsuit
    # Ensure standard order (Pairs, Suited, Offsuit descending) - optional but good practice
    # This basic generation doesn't guarantee perfect order, but functionally sufficient for now
    return hands

def get_hand_combos(hand_str):
    """Calculates the number of combos for a specific hand string."""
    if len(hand_str) == 2: # Pocket pair (e.g., "AA", "77")
        return 6
    elif len(hand_str) == 3:
        if hand_str[2] == 's': # Suited (e.g., "AKs", "T9s")
            return 4
        elif hand_str[2] == 'o': # Offsuit (e.g., "AKo", "T9o")
            return 12
    return 0 # Should not happen with valid input

def calculate_range_percentage(selected_hands_set):
    """Calculates the percentage of total combos represented by the selected hands."""
    current_combos = sum(get_hand_combos(hand) for hand in selected_hands_set)
    return (current_combos / TOTAL_COMBOS) * 100 if TOTAL_COMBOS > 0 else 0

# --- Calculation Functions ---

def calculate_pot_odds(amount_to_call, pot_size_before_call):
    """Calculates Pot Odds as a percentage."""
    if not isinstance(amount_to_call, (int, float)) or not isinstance(pot_size_before_call, (int, float)):
        return "Invalid Input"
    if amount_to_call <= 0:
        return "Call > 0" # Or handle as needed, maybe return 0% or 100% depending on interpretation

    final_pot_size = pot_size_before_call + amount_to_call
    if final_pot_size <= 0:
         # Avoid division by zero if pot somehow ends up zero or negative after call
         # This scenario is unlikely in poker but good for robustness
        return "Invalid Pot"

    # Original formula asked for Amount to Call / (Pot + Bet + Call) = Amount to Call / Final Pot
    pot_odds_decimal = amount_to_call / final_pot_size
    return pot_odds_decimal * 100

def calculate_required_equity(amount_to_call, pot_size_before_call):
    """Calculates the minimum equity required to break even on a call."""
    if not isinstance(amount_to_call, (int, float)) or not isinstance(pot_size_before_call, (int, float)):
        return "Invalid Input"
    if amount_to_call <= 0:
        return "Call > 0"

    total_pot_after_bet = pot_size_before_call # Pot *before* opponent's bet is needed here based on formula source
                                            # Let's assume pot_size_before_call *is* the pot *after* the bet but *before* our call
                                            # Formula used: Call / (Pot After Bet + Call)
    denominator = pot_size_before_call + amount_to_call
    if denominator <= 0:
        return "Invalid Pot" # Avoid division by zero

    required_equity_decimal = amount_to_call / denominator
    return required_equity_decimal * 100

def calculate_equity_from_outs(outs, street):
    """Calculates approximate equity using the Rule of 2 and 4."""
    if not isinstance(outs, int) or outs < 0 or outs > 47: # Max outs possible usually less
        return "Invalid Outs"

    if street.lower() == 'flop': # Flop to River (2 cards to come)
        return min(outs * 4, 100) # Cap at 100%
    elif street.lower() == 'turn': # Turn to River (1 card to come)
        return min(outs * 2, 100) # Cap at 100%
    else:
        return "Invalid Street"

# --- Example Usage (for testing) ---
if __name__ == "__main__":
    print(f"Pot Odds (Call 50 into 150): {calculate_pot_odds(50, 150):.2f}%") # Pot was 100, opponent bet 50 -> current pot is 150
    print(f"Required Equity (Call 36 into 81): {calculate_required_equity(36, 81):.2f}%") # Pot was 45, opponent bet 36 -> pot is 81 before call
    print(f"Equity (9 outs on flop): {calculate_equity_from_outs(9, 'flop')}%")
    print(f"Equity (9 outs on turn): {calculate_equity_from_outs(9, 'turn')}%")

    # Test Range Calculation
    test_range = {"AA", "KK", "QQ", "AKs", "AQs", "KQs"}
    print(f"Combos for {test_range}: {sum(get_hand_combos(h) for h in test_range)}")
    print(f"Percentage for {test_range}: {calculate_range_percentage(test_range):.2f}%")
    # poker_logic.py
# (Keep the existing code from the previous step)
# ... (RANKS, get_all_hands, get_hand_combos, calculate_range_percentage,
#      calculate_pot_odds, calculate_required_equity, calculate_equity_from_outs) ...

# --- New Calculation Functions ---

def calculate_mdf(bet_size, pot_size_before_bet):
    """Calculates the Minimum Defense Frequency (MDF) as a percentage."""
    if not isinstance(bet_size, (int, float)) or not isinstance(pot_size_before_bet, (int, float)):
        return "Invalid Input"
    if bet_size <= 0 or pot_size_before_bet < 0: # Pot can be 0 pre-bet, bet must be > 0
        return "Invalid Sizes"

    pot_after_bet = pot_size_before_bet + bet_size
    if pot_after_bet <= 0: # Should not happen if bet_size > 0
         return "Invalid Pot+Bet"

    # MDF = Pot Size / (Pot Size + Bet Size) = Original Pot / Final Pot (before calling)
    mdf_decimal = pot_size_before_bet / pot_after_bet
    return mdf_decimal * 100

def calculate_bluff_break_even(bet_size, pot_size_before_bet):
    """Calculates the frequency a bluff needs to work to be break-even."""
    if not isinstance(bet_size, (int, float)) or not isinstance(pot_size_before_bet, (int, float)):
        return "Invalid Input"
    if bet_size <= 0 or pot_size_before_bet < 0:
        return "Invalid Sizes"

    pot_plus_bet = pot_size_before_bet + bet_size
    if pot_plus_bet <= 0:
        return "Invalid Pot+Bet"

    # Break-Even % = Bet Size / (Pot Size + Bet Size)
    break_even_decimal = bet_size / pot_plus_bet
    return break_even_decimal * 100

# --- Card Representation (Basic - for future use) ---
# We can expand this later for validation and dead card removal
def parse_card_input(card_text):
    """
    Basic parsing for card input strings like "As", "Td", "2c".
    Returns a canonical representation or None if invalid.
    Example: Input "as", Output "As". Input "TD", Output "Td". Input "ax", Output None.
    """
    if not isinstance(card_text, str) or len(card_text) != 2:
        return None
    rank = card_text[0].upper()
    suit = card_text[1].lower()
    if rank not in RANKS or suit not in "shdc":
        return None
    return f"{rank}{suit}"

# --- Example Usage (for testing new functions) ---
if __name__ == "__main__":
    # ... (previous print statements) ...
    print("-" * 20)
    # Test MDF: Bet 50 into 100 pot
    print(f"MDF (Bet 50 into 100): {calculate_mdf(50, 100):.2f}%") # Expect 100 / 150 = 66.67%
    # Test Bluff Break Even: Bet 50 into 100 pot
    print(f"Bluff BE% (Bet 50 into 100): {calculate_bluff_break_even(50, 100):.2f}%") # Expect 50 / 150 = 33.33%

    # Test Card Parsing
    print(f"Parse 'As': {parse_card_input('As')}")
    print(f"Parse 'td': {parse_card_input('td')}")
    print(f"Parse '7H': {parse_card_input('7H')}")
    print(f"Parse 'xx': {parse_card_input('xx')}")
    print(f"Parse 'A': {parse_card_input('A')}")

# --- SPR Calculation ---
def calculate_spr(effective_stack, pot_size):
    """Calculates the Stack-to-Pot Ratio (SPR)."""
    if not isinstance(effective_stack, (int, float)) or not isinstance(pot_size, (int, float)):
        return "Invalid Input"
    if effective_stack < 0 or pot_size <= 0: # Stack can be 0, pot must be > 0
        return "Invalid Sizes"
    
    spr = effective_stack / pot_size
    return spr

# --- Example Usage for SPR ---
if __name__ == "__main__":
    # ... (previous print statements) ...
    print("-" * 20)
    # Test SPR: 200 effective stack, 50 pot
    print(f"SPR (Stack 200, Pot 50): {calculate_spr(200, 50):.2f}") # Expect 4.00

# --- Bet Sizing Calculation ---
def calculate_bet_size(pot_size, fraction):
    """Calculates the bet size based on a fraction of the pot."""
    if not isinstance(pot_size, (int, float)) or not isinstance(fraction, (int, float)):
        return "Invalid Input"
    if pot_size <= 0 or fraction <= 0:
        return "Invalid Sizes"
        
    bet_size = pot_size * fraction
    return bet_size

# --- Example Usage for Bet Sizing ---
if __name__ == "__main__":
    # ... (previous print statements) ...
    print("-" * 20)
    # Test Bet Sizing: 100 pot, 0.5 fraction (half pot)
    print(f"Bet Size (Pot 100, 1/2 Pot): {calculate_bet_size(100, 0.5):.2f}") # Expect 50.00
    # Test Bet Sizing: 75 pot, 0.6667 fraction (2/3 pot)
    print(f"Bet Size (Pot 75, 2/3 Pot): {calculate_bet_size(75, 2/3):.2f}") # Expect 50.00

# --- ICM Calculation (Simplified Malmuth-Harville) ---
def calculate_icm(chip_stacks, payouts):
    """
    Calculates tournament equity ($EV) using a simplified ICM model.
    chip_stacks: List of chip counts for each player.
    payouts: List of payouts for 1st, 2nd, 3rd, etc. Must have at least as many payouts as players.
    Returns: List of $EV for each player corresponding to chip_stacks order.
    """
    num_players = len(chip_stacks)
    if num_players == 0 or len(payouts) < num_players:
        return ["Invalid Input: Need stacks and sufficient payouts."] * num_players

    if sum(chip_stacks) <= 0:
         return ["Invalid Input: Total chips must be > 0."] * num_players

    # Ensure payouts has enough entries (pad with last payout if necessary, though ideally should match num_players)
    if len(payouts) > num_players:
        payouts = payouts[:num_players] # Use only the top N payouts

    # Recursive function to calculate finish probabilities
    memo = {}
    def get_finish_prob(current_stacks_tuple, places_left):
        current_stacks_tuple = tuple(sorted(current_stacks_tuple, reverse=True)) # Canonical representation
        state = (current_stacks_tuple, places_left)
        if state in memo:
            return memo[state]
            
        n = len(current_stacks_tuple)
        if places_left == 0 or n == 0:
            return [0.0] * len(chip_stacks) # Base case: No places left or no players

        if n == 1: # Base case: Only one player left
            # Find original index of this player
            original_index = -1
            for i, initial_stack in enumerate(chip_stacks):
                 # This mapping is tricky if stacks aren't unique. Assumes unique for simplicity here.
                 # A better approach would pass original indices through recursion.
                 # For now, we approximate by assuming the single remaining stack corresponds
                 # to the player who had that stack value initially (highly simplified).
                 # This part needs significant improvement for real accuracy.
                 # Let's return a placeholder indicating 100% for the winner.
                 # A proper implementation needs robust index tracking.
                 # Placeholder: Assume the player with this stack value wins 100%
                 # This is incorrect if stacks aren't unique or recursion changes order significantly.
                 # We'll return probabilities relative to the *current* tuple for now.
                probs = [0.0] * n
                probs[0] = 1.0 # The single player gets 100% of *this* finish place
                return probs # Needs mapping back to original players

        total_chips = sum(current_stacks_tuple)
        if total_chips <= 0:
            return [0.0] * n # Avoid division by zero

        # Calculate probability of each player finishing in the *next* available place
        finish_probs = [0.0] * n
        for i in range(n):
            prob_i_finishes_next = current_stacks_tuple[i] / total_chips
            
            # Create stacks for the next recursive call (player i is removed)
            remaining_stacks = list(current_stacks_tuple[:i]) + list(current_stacks_tuple[i+1:])
            
            # Recursively get probabilities for the remaining players and places
            # The result needs careful mapping back if indices change.
            # This simplified version assumes the recursive result maps directly, which is flawed.
            if remaining_stacks:
                 sub_probs = get_finish_prob(tuple(remaining_stacks), places_left - 1)
                 # Distribute the probability among the remaining players
                 # This mapping is the core difficulty without proper index tracking.
                 # Simplified: Add prob_i_finishes_next * sub_prob[j] to the correct original player.
                 # This requires a way to know which sub_prob corresponds to which original player.
                 # --- THIS RECURSIVE STEP IS HIGHLY SIMPLIFIED AND LIKELY INCORRECT ---
                 # A full implementation is complex. We'll return placeholder values.
                 pass # Placeholder - complex logic needed here

            # For now, just assign the direct probability for this place
            finish_probs[i] = prob_i_finishes_next # This is P(player i finishes exactly N-places_left+1)

        # --- THIS IS NOT THE FULL ICM CALCULATION ---
        # It only calculates the probability of finishing in the *next* place.
        # A full calculation requires summing probabilities for all finishing positions.
        # Due to complexity, we'll return a placeholder result based on chip proportion.

        # Placeholder: Return chip proportion as a proxy for equity (NOT ICM)
        # This is just to have *some* output, not accurate ICM.
        equity_proxy = [(stack / total_chips) if total_chips > 0 else 0 for stack in current_stacks_tuple]
        
        # Calculate $EV based on this proxy equity and payouts
        # This is also incorrect as it doesn't account for finishing order probabilities.
        ev_proxy = [0.0] * n
        if places_left <= len(payouts):
             current_payout = payouts[num_players - places_left] # Payout for this finishing position
             for i in range(n):
                 # Incorrectly assumes equity_proxy is P(finish in this place)
                 # ev_proxy[i] = equity_proxy[i] * current_payout
                 # A better proxy: EV = sum over all places k [ P(finish place k) * payout[k] ]
                 # We don't have P(finish place k) correctly.
                 pass # Placeholder

        # --- Returning simplified chip chop equity as placeholder ---
        total_payout_pool = sum(payouts[:n]) # Sum payouts for remaining players
        chip_chop_ev = [(stack / total_chips * total_payout_pool) if total_chips > 0 else 0 for stack in current_stacks_tuple]

        memo[state] = chip_chop_ev # Store the placeholder result
        return chip_chop_ev

    # Initial call - This will return the chip chop EV placeholder
    # A real ICM calculation is significantly more involved.
    chip_stacks_tuple = tuple(chip_stacks)
    # result_ev = get_finish_prob(chip_stacks_tuple, num_players) # This recursive function is flawed

    # --- Using simple chip chop as placeholder ---
    total_chips_final = sum(chip_stacks)
    total_payout_final = sum(payouts)
    if total_chips_final <= 0: return [0.0] * num_players
    
    result_ev = [(s / total_chips_final) * total_payout_final for s in chip_stacks]

    return result_ev

# --- Example Usage for ICM ---
if __name__ == "__main__":
    # ... (previous print statements) ...
    print("-" * 20)
    # Test ICM (Placeholder - Chip Chop)
    stacks = [1000, 500, 200]
    pays = [100, 60, 40]
    icm_ev = calculate_icm(stacks, pays)
    print(f"ICM EV (Placeholder) for Stacks {stacks}, Payouts {pays}:")
    for i, ev in enumerate(icm_ev):
        print(f" Player {i+1}: ${ev:.2f}")

import csv

# Load push/fold ranges from CSV
def parse_push_fold_csv(csv_data):
    ranges = {}
    reader = csv.DictReader(csv_data.splitlines())
    for row in reader:
        stack = float(row['Stack'].replace('BB', '').replace(',', '.'))
        ranges[stack] = {
            'SB': float(row['SB'].replace('%', '').replace(',', '.')),
            'BTN': float(row['B'].replace('%', '').replace(',', '.')),
            'CO': float(row['CO'].replace('%', '').replace(',', '.')),
            'HJ': float(row['HJ'].replace('%', '').replace(',', '.')),
            'LJ': float(row['LJ'].replace('%', '').replace(',', '.')),
            'UTG+3': float(row['UTG+3'].replace('%', '').replace(',', '.')),
            'UTG+2': float(row['UTG+2'].replace('%', '').replace(',', '.')),
            'UTG+1': float(row['UTG+1'].replace('%', '').replace(',', '.')),
            'UTG': float(row['UTG'].replace('%', '').replace(',', '.'))
        }
    return ranges

# Utility function to get top hands based on percentage
def evaluate_hand_strength(hand_str):
    # Simplified hand strength evaluation
    evaluator = Evaluator()
    hand_cards = hand_string_to_treys_cards(hand_str)
    if hand_cards is None:
        return float('inf')  # Assign a high value for invalid hands
    score = evaluator.evaluate(hand_cards, [Card.new('As'), Card.new('Ks'), Card.new('Qs'), Card.new('Js'), Card.new('Ts')])
    return score

def get_top_hands_by_percentage(percentage):
    all_hands = get_all_hands()
    hand_strengths = {hand: evaluate_hand_strength(hand) for hand in all_hands}
    # Filter out hands with None strength (if any)
    hand_strengths = {hand: strength for hand, strength in hand_strengths.items() if strength is not None}
    pairs = [hand for hand in hand_strengths if hand[0] == hand[1]]  # Identify pairs
    non_pairs = [hand for hand in hand_strengths if hand[0] != hand[1]]  # Identify non-pairs

    # Sort both lists based on hand strength
    sorted_pairs = sorted(pairs, key=hand_strengths.get)
    sorted_non_pairs = sorted(non_pairs, key=hand_strengths.get)

    # Combine pairs and non-pairs, prioritizing pairs
    sorted_hands = sorted_pairs + sorted_non_pairs
    total_combos = sum(get_hand_combos(hand) for hand in hand_strengths)
    target_combos = (percentage / 100) * total_combos
    selected_hands = []
    current_combos = 0
    for hand in sorted_hands:
        combos = get_hand_combos(hand)
        if current_combos + combos <= target_combos:
            selected_hands.append(hand)
            current_combos += combos
        else:
            break
    return selected_hands

# Load push/fold ranges from CSV
with open('push ranges.csv', 'r') as f:
    csv_data = f.read()
PUSH_FOLD_RANGES = parse_push_fold_csv(csv_data)

def get_push_fold_advice(stack_bb, position, players_left):
    """
    Provides push/fold advice based on stack size, position, and players left.
    Returns: (recommendation, range_list) tuple
    """
    if not isinstance(stack_bb, (int, float)) or stack_bb <= 0:
        return ("Invalid Stack Size", [])
    position_map = {
        'UTG': 'UTG',
        'UTG+1': 'UTG+1',
        'UTG+2': 'UTG+2',
        'UTG+3': 'UTG+3',
        'LJ': 'LJ',
        'HJ': 'HJ',
        'CO': 'CO',
        'BTN': 'BTN',
        'SB': 'SB',
        'BB': 'BB'
    }
    position = position_map.get(position, None)
    if position is None:
        return ("Invalid Position", [])
    if not isinstance(players_left, int) or players_left < 2 or players_left > 9:
        return ("Invalid Player Count", [])

    # Find the closest stack size in the data
    stack_sizes = sorted(PUSH_FOLD_RANGES.keys())
    closest_stack = min(stack_sizes, key=lambda x:abs(x-stack_bb))
    percentage = PUSH_FOLD_RANGES[closest_stack].get(position, None)
    if percentage is None:
        return ("Invalid Position for given stack size", [])

    range_list = get_top_hands_by_percentage(percentage)
    return ("Push recommended with:", range_list)

# --- Example Usage for Push/Fold ---
if __name__ == "__main__":
    # ... (previous print statements) ...
    print("-" * 20)
    # Test Push/Fold (Placeholder)
    print(f"Push/Fold (8 BB, BTN, 6 players): {get_push_fold_advice(8, 'BTN', 6)}")

# --- Hand Strength Evaluation ---
def get_hand_strength(hand_str_list, board_str_list):
    """
    Evaluates the strength of a hand given a board.
    hand_str_list: List of 2 card strings (e.g., ["As", "Kh"])
    board_str_list: List of 3 to 5 board card strings (e.g., ["Qh", "Js", "Td"])
    Returns: A tuple (hand_rank_int, hand_rank_str) or (None, "Error Message")
    """
    if len(hand_str_list) != 2:
        return None, "Error: Hand must have exactly 2 cards."
        
    evaluator = Evaluator()
    hand_cards = board_string_to_treys_cards(hand_str_list) # Can reuse this function
    board_cards = board_string_to_treys_cards(board_str_list)

    if hand_cards is None or len(hand_cards) != 2:
        return None, "Error: Invalid hand card format."
    if board_cards is None:
         return None, "Error: Invalid board card format."
    if not (3 <= len(board_cards) <= 5):
        return None, "Error: Board must have 3, 4, or 5 cards."
        
    # Check for conflicts
    all_cards = hand_cards + board_cards
    if len(set(all_cards)) != len(all_cards):
        return None, "Error: Duplicate cards between hand and board."

    try:
        score = evaluator.evaluate(hand_cards, board_cards)
        rank_class = evaluator.get_rank_class(score)
        rank_class_str = evaluator.class_to_string(rank_class)
        return score, rank_class_str
    except Exception as e:
        print(f"Hand strength evaluation error: {e}")
        return None, f"Error during evaluation: {e}"

# --- Example Usage for Hand Strength ---
if __name__ == "__main__":
    # ... (previous print statements) ...
    print("-" * 20)
    # Test Hand Strength
    hs_hand = ["As", "Ks"]
    hs_board = ["Qs", "Js", "Ts", "2d"]
    hs_score, hs_rank = get_hand_strength(hs_hand, hs_board)
    print(f"Hand Strength for {hs_hand} on {hs_board}: Rank={hs_rank} (Score: {hs_score})") # Expect Royal Flush


# --- Equity Calculation Helpers (using treys) ---

# Map our rank characters to treys integer ranks (2-9, T=10, J=11, Q=12, K=13, A=14)
# treys uses 2=0, 3=1, ..., A=12 internally for lookups, but Card.new accepts strings.
SUITS_TREYS = "shdc" # Spades, Hearts, Diamonds, Clubs

def hand_string_to_treys_cards(hand_str):
    """Converts a 2-card hand string like 'AsKh' to a list of treys Card objects."""
    if len(hand_str) != 4:
        return None # Expecting format like AsKh
    c1_str = hand_str[0:2]
    c2_str = hand_str[2:4]
    try:
        card1 = Card.new(c1_str)
        card2 = Card.new(c2_str)
        return [card1, card2]
    except ValueError: # treys raises ValueError for invalid card strings
        return None

def board_string_to_treys_cards(board_list):
    """Converts a list of board card strings ['Ah', 'Kd', 'Tc'] to treys Card objects."""
    cards = []
    for card_str in board_list:
        if card_str and len(card_str) == 2:
            try:
                cards.append(Card.new(card_str))
            except ValueError:
                return None # Invalid card found
        elif card_str: # Non-empty but invalid format
            return None
    return cards

def generate_combos(hand_range_list):
    """
    Generates all specific 2-card combos (as lists of treys Card objects)
    from a list of canonical hand range strings (e.g., ['AA', 'AKs', 'T9o']).
    """
    combos = []
    ranks_list = list(RANKS) # Use the defined RANKS string

    for hand_str in hand_range_list:
        if len(hand_str) == 2: # Pocket Pair (e.g., "QQ")
            rank = hand_str[0]
            if rank not in ranks_list: continue
            # Generate 6 combos (e.g., QsQh, QsQd, QsQc, QhQd, QhQc, QdQc)
            suits_for_pair = list(SUITS_TREYS)
            for s1, s2 in itertools.combinations(suits_for_pair, 2):
                try:
                    combos.append([Card.new(rank + s1), Card.new(rank + s2)])
                except ValueError: continue # Should not happen with valid ranks/suits

        elif len(hand_str) == 3:
            rank1 = hand_str[0]
            rank2 = hand_str[1]
            type = hand_str[2]
            if rank1 not in ranks_list or rank2 not in ranks_list: continue

            if type == 's': # Suited (e.g., "AKs")
                # Generate 4 combos (e.g., AsKs, AhKh, AdKd, AcKc)
                for suit in SUITS_TREYS:
                    try:
                        combos.append([Card.new(rank1 + suit), Card.new(rank2 + suit)])
                    except ValueError: continue
            elif type == 'o': # Offsuit (e.g., "AKo")
                # Generate 12 combos (e.g., AsKh, AsKd, AsKc, AhKs, ...)
                for s1 in SUITS_TREYS:
                    for s2 in SUITS_TREYS:
                        if s1 != s2: # Ensure suits are different
                            try:
                                combos.append([Card.new(rank1 + s1), Card.new(rank2 + s2)])
                            except ValueError: continue
    return combos

# --- Main Equity Calculation Function (Refactored) ---

def calculate_hand_vs_range_equity(hero_hand_str, villain_range_list, board_str_list):
    """
    Calculates hero's equity against a villain range on a given board.
    Runs separate simulations for each street (preflop, flop, turn, river).
    """
    # --- Input Validation ---
    if not villain_range_list:
        print("Error: Villain range list cannot be empty.")
        return None

    evaluator = Evaluator()
    hero_cards = hand_string_to_treys_cards(hero_hand_str)
    if not hero_cards:
        print(f"Error: Invalid hero hand format: {hero_hand_str}")
        return None
    if len(set(hero_cards)) != 2:
        print(f"Error: Duplicate cards in hero hand: {hero_hand_str}")
        return None

    board_cards = board_string_to_treys_cards(board_str_list)
    if board_cards is None:
        print(f"Error: Invalid board card format in: {board_str_list}")
        return None
    if len(board_cards) > 5:
        print(f"Error: Too many board cards: {len(board_cards)}")
        return None
    if len(set(board_cards)) != len(board_cards):
        print(f"Error: Duplicate cards on board: {board_str_list}")
        return None

    known_cards = hero_cards + board_cards
    if len(set(known_cards)) != len(known_cards):
        print(f"Error: Conflict between hero hand and board cards: {hero_hand_str} | {board_str_list}")
        return None

    villain_combos_all = generate_combos(villain_range_list)
    if not villain_combos_all:
        print("Error: Villain range generated no valid combos.")
        return None

    # --- Simulation Parameters ---
    simulations = 10000 # Adjust for speed/accuracy trade-off
    max_attempts_multiplier = 5 # Try up to 5x simulations if conflicts occur

    # --- Results Storage ---
    final_results = {'preflop': None, 'flop': None, 'turn': None, 'river': None}
    street_results = {
        'preflop': {'wins': 0, 'ties': 0, 'total': 0},
        'flop': {'wins': 0, 'ties': 0, 'total': 0},
        'turn': {'wins': 0, 'ties': 0, 'total': 0},
        'river': {'wins': 0, 'ties': 0, 'total': 0}
    }

    # --- Determine Streets to Simulate ---
    streets_to_simulate = ['preflop']
    if len(board_cards) >= 3: streets_to_simulate.append('flop')
    if len(board_cards) >= 4: streets_to_simulate.append('turn')
    if len(board_cards) == 5: streets_to_simulate.append('river')

    # --- Run Simulation for Each Relevant Street ---
    for street in streets_to_simulate:
        sim_count = 0
        successful_sims = 0
        
        # Filter villain combos based on known cards *for this street*
        current_board = []
        if street == 'flop': current_board = board_cards[:3]
        elif street == 'turn': current_board = board_cards[:4]
        elif street == 'river': current_board = board_cards[:5]
        
        # Known cards for this specific street simulation
        street_known_cards = hero_cards + current_board
        
        # Filter villain combos against hero cards and the current street's board
        street_villain_combos = [
            combo for combo in villain_combos_all
            if not any(card in street_known_cards for card in combo) and len(set(combo)) == 2
        ]
        
        if not street_villain_combos:
            print(f"Warning: No valid villain combos for {street} simulation after filtering.")
            continue # Skip this street if no valid combos

        while successful_sims < simulations:
            if sim_count > simulations * max_attempts_multiplier and successful_sims == 0:
                print(f"Error: Failed to run any simulations for {street}. Check for card conflicts.")
                break # Bail out for this street

            sim_count += 1

            # --- Per-Simulation Setup for the Street ---
            chosen_villain_hand = random.choice(street_villain_combos)
            
            # Create a fresh deck for this runout
            deck_run = Deck()
            
            # Remove cards known up to this street + hero + chosen villain
            runout_dead_cards = street_known_cards + chosen_villain_hand
            if len(set(runout_dead_cards)) != len(runout_dead_cards):
                continue # Conflict detected, skip this attempt

            deck_run.cards = [card for card in deck_run.cards if card not in runout_dead_cards]

            # --- Runout Simulation from Current Street ---
            board_run = list(current_board) # Start with the known board for this street
            cards_needed = 5 - len(board_run)

            if cards_needed < 0: continue # Should not happen
            
            if cards_needed > 0:
                if len(deck_run.cards) < cards_needed:
                    continue # Not enough cards in deck

                drawn_cards = deck_run.draw(cards_needed)
                if not isinstance(drawn_cards, list): drawn_cards = [drawn_cards]
                board_run.extend(drawn_cards)

            if len(board_run) != 5:
                continue # Should not happen

            # --- Evaluate Hands at River ---
            try:
                # Final check for duplicates before evaluation
                if len(set(hero_cards + board_run)) != 7 or len(set(chosen_villain_hand + board_run)) != 7:
                    continue

                hero_score = evaluator.evaluate(hero_cards, board_run)
                villain_score = evaluator.evaluate(chosen_villain_hand, board_run)
            except Exception as e:
                # print(f"Warning: Evaluation error on {street}: {e}")
                continue

            # --- Tally Result for this Street ---
            successful_sims += 1
            street_results[street]['total'] += 1
            if hero_score < villain_score:
                street_results[street]['wins'] += 1
            elif hero_score == villain_score:
                street_results[street]['ties'] += 1
            # --- End Simulation Loop for Street ---

        # --- Calculate Equity for the Street ---
        total = street_results[street]['total']
        if total > 0:
            wins = street_results[street]['wins']
            ties = street_results[street]['ties']
            equity = (wins + (ties / 2)) / total
            final_results[street] = equity * 100
        elif successful_sims == 0 and sim_count > simulations * max_attempts_multiplier:
             final_results[street] = 0.0 # Indicate failure if no sims ran
        # else: leave as None if street wasn't simulated or had no valid combos initially

    return final_results
