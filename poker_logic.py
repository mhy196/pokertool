# poker_logic.py
# Contains the core poker calculation functions

import math
import itertools
import random # Import random for safer selection
# Make sure treys is installed: pip install treys
try:
    from treys import Card, Evaluator, Deck # Import treys components
except ImportError:
    print("ERROR: 'treys' library not found. Please install it using: pip install treys")
    # Optionally raise the error again or exit if treys is critical
    raise
import csv
import os

# --- Hand Range Constants ---
RANKS = "AKQJT98765432"
TOTAL_COMBOS = 1326
SUITS_TREYS = "shdc" # Spades, Hearts, Diamonds, Clubs

# --- Canonical Hand Ranking (Defines "Top X%") ---
# This list dictates the order of strength. Strongest hands first.
# Pairs > Suited High Cards > Offsuit High Cards > Suited Connectors > etc.
# (Ensure this order matches standard push/fold priorities)
SIMPLIFIED_HAND_RANKING = [
    # Pairs (Strongest to Weakest)
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
    # Suited Aces
    "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
    # Suited Kings
    "KQs", "KJs", "KTs", "K9s", "K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s",
    # Suited Queens
    "QJs", "QTs", "Q9s", "Q8s", "Q7s", "Q6s", "Q5s", "Q4s", "Q3s", "Q2s",
    # Suited Jacks
    "JTs", "J9s", "J8s", "J7s", "J6s", "J5s", "J4s", "J3s", "J2s",
    # Suited Tens
    "T9s", "T8s", "T7s", "T6s", "T5s", "T4s", "T3s", "T2s",
    # Suited Nines ... Eight ... etc.
    "98s", "97s", "96s", "95s", "94s", "93s", "92s",
    "87s", "86s", "85s", "84s", "83s", "82s",
    "76s", "75s", "74s", "73s", "72s",
    "65s", "64s", "63s", "62s",
    "54s", "53s", "52s",
    "43s", "42s",
    "32s",
    # Offsuit Aces
    "AKo", "AQo", "AJo", "ATo", "A9o", "A8o", "A7o", "A6o", "A5o", "A4o", "A3o", "A2o",
    # Offsuit Kings
    "KQo", "KJo", "KTo", "K9o", "K8o", "K7o", "K6o", "K5o", "K4o", "K3o", "K2o",
    # Offsuit Queens
    "QJo", "QTo", "Q9o", "Q8o", "Q7o", "Q6o", "Q5o", "Q4o", "Q3o", "Q2o",
    # Offsuit Jacks
    "JTo", "J9o", "J8o", "J7o", "J6o", "J5o", "J4o", "J3o", "J2o",
    # Offsuit Tens ... etc.
    "T9o", "T8o", "T7o", "T6o", "T5o", "T4o", "T3o", "T2o",
    "98o", "97o", "96o", "95o", "94o", "93o", "92o",
    "87o", "86o", "85o", "84o", "83o", "82o",
    "76o", "75o", "74o", "73o", "72o",
    "65o", "64o", "63o", "62o",
    "54o", "53o", "52o",
    "43o", "42o",
    "32o"
]

# Generate all 169 canonical hand representations (e.g., "AKs", "77", "T9o")
def get_all_hands():
    """Returns the predefined canonical hand ranking list."""
    # This ensures consistency and uses the established order
    return list(SIMPLIFIED_HAND_RANKING)

def get_hand_combos(hand_str):
    """Calculates the number of combos for a specific hand string."""
    if not isinstance(hand_str, str): return 0 # Handle non-string input
    if len(hand_str) == 2: # Pocket pair (e.g., "AA", "77")
        # Basic validation
        if hand_str[0] not in RANKS or hand_str[1] not in RANKS or hand_str[0] != hand_str[1]:
            return 0
        return 6
    elif len(hand_str) == 3:
        # Basic validation
        if hand_str[0] not in RANKS or hand_str[1] not in RANKS or hand_str[0] == hand_str[1]:
             return 0
        if hand_str[2] == 's': # Suited (e.g., "AKs", "T9s")
            return 4
        elif hand_str[2] == 'o': # Offsuit (e.g., "AKo", "T9o")
            return 12
    return 0 # Invalid format

def calculate_range_percentage(selected_hands_set):
    """Calculates the percentage of total combos represented by the selected hands."""
    if not isinstance(selected_hands_set, set): return 0.0 # Expecting a set
    current_combos = sum(get_hand_combos(hand) for hand in selected_hands_set)
    return (current_combos / TOTAL_COMBOS) * 100 if TOTAL_COMBOS > 0 else 0.0

# --- Push/Fold Logic ---

def parse_push_fold_csv(csv_data):
    """Parses CSV data string into a dictionary {stack: {pos: percentage}}."""
    ranges = {}
    try:
        # Use DictReader to handle header mapping
        reader = csv.DictReader(csv_data.splitlines())
        headers = reader.fieldnames # Get header names
        if not headers or 'Stack' not in headers:
             print("ERROR: CSV missing 'Stack' column header.")
             return {}

        # Map CSV headers to internal keys if needed (e.g., 'B' to 'BTN')
        # Here we assume the keys used in get_push_fold_advice ('B', 'SB' etc) match the CSV headers
        expected_pos_headers = ['SB', 'B', 'CO', 'HJ', 'LJ', 'UTG+3', 'UTG+2', 'UTG+1', 'UTG'] # Headers expected in the CSV file

        for row in reader:
            try:
                # Clean and convert stack value
                stack_str = row.get('Stack', '').replace('BB', '').strip()
                stack = float(stack_str.replace(',', '.')) # Handle comma decimal separator

                ranges[stack] = {}
                for header in expected_pos_headers:
                    # Check if header exists in the row AND the value is not None AND the value is not just whitespace
                    if header in row and row[header] is not None and row[header].strip() != '':
                        try:
                            # Clean and convert percentage value
                            percent_str = row[header].replace('%', '').strip()
                            percentage = float(percent_str.replace(',', '.')) # Handle comma decimal separator
                            # Store percentage directly, e.g. ranges[6.0]['B'] = 50.8
                            ranges[stack][header] = percentage
                        except (ValueError, TypeError):
                            print(f"WARNING: Invalid percentage format for Stack {stack}, Pos {header}: '{row[header]}'. Skipping.")
                    # else: # Optional: Warn if an expected header is missing or empty in a row
                        # if header in row: print(f"INFO: Empty cell for Stack {stack}, Pos {header}.")
                        # else: print(f"WARNING: Missing header '{header}' for Stack {stack}.")

            except (ValueError, TypeError):
                print(f"WARNING: Invalid stack format: '{row.get('Stack', '')}'. Skipping row.")
            except Exception as e:
                print(f"ERROR processing CSV row {row}: {e}. Skipping row.")

    except csv.Error as e:
        print(f"ERROR parsing CSV data: {e}")
        return {}
    except Exception as e:
        print(f"UNEXPECTED ERROR during CSV parsing: {e}")
        return {}

    return ranges

# --- CORRECTED: get_top_hands_by_percentage ---
def get_top_hands_by_percentage(percentage):
    """
    Gets the top N% of hands based on the fixed SIMPLIFIED_HAND_RANKING list.
    It iterates through the ranked list and adds hands until the cumulative
    combo count reaches the target percentage.
    """
    # Validate percentage input
    if not isinstance(percentage, (int, float)) or not (0 <= percentage <= 100):
        print(f"WARNING: Invalid percentage ({percentage}, type: {type(percentage)}) requested. Returning empty range.")
        return []
    if percentage == 0: return [] # Handle 0% case explicitly

    # Calculate the target number of hand combinations
    # Use a small epsilon to handle potential floating point inaccuracies
    target_combos = TOTAL_COMBOS * (percentage / 100.0) - 1e-9
    selected_hands = []
    current_combos = 0

    # Iterate through the pre-defined ranked list of hands
    for hand in SIMPLIFIED_HAND_RANKING:
        combos = get_hand_combos(hand)
        if combos == 0: # Skip invalid hand strings if any in ranking
            continue

        # Add the hand if we haven't reached the target combo count yet.
        # This ensures we get the strongest hands first according to the list.
        # Use <= target_combos to include the hand that reaches/crosses the threshold
        if current_combos < target_combos:
             selected_hands.append(hand)
             current_combos += combos
             # Optional: Stop exactly if adding the next hand would overshoot significantly?
             # This version includes the hand that crosses the threshold.
        else:
             # If adding the current hand brings us exactly to the target, add it and break
             if abs(current_combos - target_combos) < 1e-9:
                 # We might have already added it in the loop above if current_combos was slightly less
                 # This check is likely redundant with the logic above but safe.
                 if hand not in selected_hands:
                      selected_hands.append(hand)
                      current_combos += combos
             break # Stop adding hands once the target combo count is met or exceeded.


    # Debugging log (optional)
    # actual_perc = (current_combos / TOTAL_COMBOS) * 100 if TOTAL_COMBOS > 0 else 0
    # print(f"DEBUG: Target {percentage:.1f}% ({target_combos:.1f} combos). Selected {len(selected_hands)} hands ({current_combos} combos, {actual_perc:.1f}%).")

    return selected_hands


# Load push/fold ranges GLOBALLY when the module is imported
PUSH_FOLD_RANGES = {} # Initialize
try:
    # Define the expected path relative to this script file
    # Use os.path.abspath to handle different execution contexts better
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(script_dir, 'push ranges.csv')

    if not os.path.exists(csv_file_path):
         print(f"ERROR: 'push ranges.csv' not found at expected path: {csv_file_path}")
    else:
        # Try reading with utf-8 first, fallback if needed
        csv_data = None
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                csv_data = f.read()
        except UnicodeDecodeError:
            print("WARNING: Failed to read CSV as UTF-8, trying default encoding.")
            try:
                with open(csv_file_path, 'r') as f:
                     csv_data = f.read()
            except Exception as e_read:
                 print(f"ERROR: Failed to read CSV with default encoding either: {e_read}")

        if csv_data:
            PUSH_FOLD_RANGES = parse_push_fold_csv(csv_data)
            if PUSH_FOLD_RANGES:
                 print("INFO: Push/Fold Ranges loaded successfully at module level.")
                 # Optional: Print loaded stacks/positions for verification
                 # print("DEBUG: Loaded stacks:", sorted(PUSH_FOLD_RANGES.keys()))
                 # if 6.0 in PUSH_FOLD_RANGES: print("DEBUG: Keys for 6.0BB:", PUSH_FOLD_RANGES[6.0].keys())
            else:
                 print("WARNING: Push/Fold Ranges loaded but resulted in an empty dictionary. Check CSV format/content and parsing logic.")
        else:
             print("ERROR: Failed to read any data from CSV file.")


except FileNotFoundError:
    # This might occur if __file__ is not defined (e.g., in some interactive environments)
    print(f"ERROR: Could not determine script directory or 'push ranges.csv' not found relative to execution path during module load.")
except Exception as e:
    print(f"ERROR: Failed to load or parse 'push ranges.csv' during module load: {e}")
    # PUSH_FOLD_RANGES remains {}


# --- Updated get_push_fold_advice function (with refined error check) ---
def get_push_fold_advice(stack_bb, position, players_left):
    """
    Provides push/fold advice based on stack size, position, and players left.
    Returns a 4-tuple:
      (advice_string, range_list, percentage, tips_string)

    Example:
      -> ("Push top 18.0%", ["A2s","A3s","TT","JJ","..."], 18.0, "Some strategy tips here...")
    """

    # --- Input Validation ---
    if not isinstance(stack_bb, (int, float)) or stack_bb <= 0:
        # Return a specific error message
        return ("Error: Invalid Stack Size provided.", [], None, "No tips available due to error.")

    position_map = {
        'SB': 'SB', 'BTN': 'B', 'CO': 'CO', 'HJ': 'HJ', 'LJ': 'LJ',
        'UTG+3': 'UTG+3', 'UTG+2': 'UTG+2', 'UTG+1': 'UTG+1', 'UTG': 'UTG'
    }
    if position not in position_map:
        return (f"Error: Unknown input position '{position}'.", [], None, "No tips available due to error.")

    mapped_position = position_map.get(position)
    if mapped_position is None:
        print(f"ERROR: Logic error in position_map for '{position}'.")
        return (f"Error: Internal mapping failed for position '{position}'.", [], None, "No tips available.")

    if not isinstance(players_left, int) or not (2 <= players_left <= 10):
        return ("Error: Invalid Player Count (must be 2-10).", [], None, "Tips not available for invalid player count.")

    # --- Check if Ranges Loaded ---
    if not PUSH_FOLD_RANGES or not isinstance(PUSH_FOLD_RANGES, dict):
        print("ERROR: PUSH_FOLD_RANGES dictionary is empty or failed to load correctly!")
        return ("Error: Push range data not available or failed to load.", [], None, "No tips available due to data error.")

    # Find the closest stack size in the data
    stack_sizes = sorted(PUSH_FOLD_RANGES.keys())
    if not stack_sizes:
        print("ERROR: PUSH_FOLD_RANGES loaded but contains no stack size keys.")
        return ("Error: No stack sizes found in loaded range data.", [], None, "Tips not available.")

    try:
        closest_stack = min(stack_sizes, key=lambda x: abs(x - stack_bb))
    except Exception as e:
        print(f"ERROR finding closest stack for {stack_bb} among {stack_sizes}: {e}")
        return (f"Error processing stack size {stack_bb}BB.", [], None, "No tips due to stack lookup error.")

    position_data = PUSH_FOLD_RANGES.get(closest_stack)
    if position_data is None or not isinstance(position_data, dict):
        print(f"ERROR: Missing data for stack key {closest_stack} in PUSH_FOLD_RANGES.")
        return (f"Error: No valid range data for stack near {stack_bb}BB", [], None, "No tips available.")

    percentage = position_data.get(mapped_position)
    if percentage is None:
        available_keys = list(position_data.keys())
        print(f"ERROR: Key '{mapped_position}' (from '{position}') not found for stack {closest_stack}BB.")
        print(f"DEBUG: Available keys: {available_keys}")
        return (f"Error: No range data for position '{position}' at {closest_stack}BB stack.", [], None, "No tips available.")

    if not isinstance(percentage, (int, float)):
        print(f"ERROR: Percentage value for {closest_stack}BB/{mapped_position} is not a number: {percentage}")
        return (f"Error: Invalid percentage data for {position} at {closest_stack}BB.", [], None, "No tips for data error.")

    # --- Generate Hand Range ---
    try:
        range_list = get_top_hands_by_percentage(percentage)  # Must exist in your code
        if not isinstance(range_list, list):
            print(f"ERROR: get_top_hands_by_percentage returned type {type(range_list)} for {percentage}%.")
            return ("Error generating hand range.", [], percentage, "No tips due to range generation error.")
    except NameError:
        print("ERROR: get_top_hands_by_percentage function not defined!")
        return ("Code Error: Hand generation function missing.", [], percentage, "No tips - function missing.")
    except Exception as e:
        print(f"ERROR generating hand range for {percentage}%: {e}")
        return (f"Runtime Error generating range: {e}", [], percentage, "No tips - runtime error in range gen.")

    # --- Build Advice & Tips ---
    advice_string = f"Push top {percentage:.1f}%"
    # Example tips: adjust or fill in with your real strategy text
    tips_string = (
        f"With around {closest_stack}BB in {position}, pushing around {percentage:.1f}% can be profitable. "
        "Consider table dynamics and how many players are left to act."
    )

    # Return the 4-tuple
    return (advice_string, range_list, percentage, tips_string)



# --- Other Calculation Functions (Pot Odds, Equity, MDF, SPR etc.) ---
# (These functions remain unchanged from the user's provided version)

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