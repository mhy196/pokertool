##########################################
# trainer_app.py
##########################################
import streamlit as st
import os
import random
from PIL import Image
import time # Needed for sleep

# --- Import from poker_logic ---
try:
    # Import necessary functions and constants from your logic file
    # Make sure poker_logic.py is updated and in the same directory
    from poker_logic import (
        get_push_fold_advice,
        RANKS,
        # Import others if needed, but these are key for the current trainer
        # get_all_hands, get_hand_combos, hand_string_to_treys_cards
    )
    logic_available = True
    print("DEBUG: poker_logic imported successfully.") # Add debug print
except ImportError as e:
    st.error(f"Critical Error: Could not import 'poker_logic.py'. Ensure it's in the same directory and has no syntax errors. Details: {e}")
    logic_available = False # Explicitly set to False
    st.stop()
except NameError as e:
    # This might happen if PUSH_FOLD_RANGES failed to load within poker_logic.py
    st.error(f"Critical Error: Initialization failed in 'poker_logic.py' (likely missing 'push ranges.csv' or CSV parsing error). Details: {e}")
    logic_available = False # Explicitly set to False
    st.stop()
except Exception as e: # Catch any other potential import errors
    st.error(f"An unexpected error occurred during poker_logic import: {e}")
    logic_available = False
    st.stop()


# --- Configuration & Constants ---
# Use RANKS from poker_logic
# Define UI positions (user-facing, mapping handled in poker_logic)
POSITIONS = ["SB", "BTN", "CO", "HJ", "LJ", "UTG+3", "UTG+2", "UTG+1", "UTG"]
MAX_QUESTIONS = 5
CARD_IMG_WIDTH = 170 # Adjust card size as desired
FEEDBACK_DELAY_SECONDS = 1.0 # Delay before auto-advancing

# --- Helper Functions ---
def load_card_images():
    """Loads card images into session state."""
    if "card_images" not in st.session_state:
        st.session_state.card_images = {}
        rank_map = {
            'A': 'ace', 'K': 'king', 'Q': 'queen', 'J': 'jack', 'T': '10',
            '9': '9', '8': '8', '7': '7', '6': '6', '5': '5', '4': '4', '3': '3', '2': '2'
        }
        suit_map = {'s': 'spades', 'h': 'hearts', 'd': 'diamonds', 'c': 'clubs'}
        base_path = "assets/cards" # Make sure this path is correct

        # Check if base_path exists, provide helpful error if not
        if not os.path.isdir(base_path):
            st.error(f"Error: Card image directory not found at '{base_path}'. Please ensure the 'assets/cards' folder exists and contains card images.")
            st.stop() # Stop execution if images can't be loaded

        loaded_count = 0
        for r, rname in rank_map.items():
            for s, sname in suit_map.items():
                filename = f"{rname}_of_{sname}.png"
                full_path = os.path.join(base_path, filename)
                short_code = f"{r}{s}"
                if os.path.exists(full_path):
                    st.session_state.card_images[short_code] = full_path
                    loaded_count += 1
                # else:
                #     print(f"Debug: Image not found - {full_path}") # Optional debug print

        if loaded_count < 52:
             st.warning(f"Warning: Only loaded {loaded_count}/52 card images. Some cards may not display correctly.")

def generate_specific_card_codes(hand_str):
    """
    Generates specific card codes (e.g., 'As', 'Kc') for a canonical hand string.
    Returns (card1_code, card2_code)
    """
    if len(hand_str) == 2: # Pair
        rank = hand_str[0]
        suits_avail = ['s', 'h', 'd', 'c']
        s1 = random.choice(suits_avail)
        suits_avail.remove(s1)
        s2 = random.choice(suits_avail)
        card1_code = f"{rank}{s1}"
        card2_code = f"{rank}{s2}"
    else: # Non-pair
        rank1, rank2, type = hand_str[0], hand_str[1], hand_str[2]
        if type == 's': # Suited
            chosen_suit = random.choice(['s', 'h', 'd', 'c'])
            card1_code = f"{rank1}{chosen_suit}"
            card2_code = f"{rank2}{chosen_suit}"
        else: # Offsuit ('o')
            suits_avail = ['s', 'h', 'd', 'c']
            s1 = random.choice(suits_avail)
            suits_avail.remove(s1)
            s2 = random.choice(suits_avail)
            # Ensure card codes are consistent order relative to hand string (optional but good practice)
            if RANKS.index(rank1) < RANKS.index(rank2):
                 card1_code = f"{rank1}{s1}"
                 card2_code = f"{rank2}{s2}"
            else: # Swap ranks if needed based on original hand_str
                 card1_code = f"{rank2}{s1}" # Map s1 to the second rank in hand_str
                 card2_code = f"{rank1}{s2}" # Map s2 to the first rank in hand_str

    # Return codes consistently (e.g., higher rank card first if applicable) - maybe not strictly needed here
    return card1_code, card2_code

def generate_random_scenario():
    """
    Generates a single random poker scenario including specific card codes.
    Returns (hand_string, stack_bb, pos, players_left, card1_code, card2_code) tuple.
    """
    r1 = random.choice(RANKS)
    r2 = random.choice(RANKS)
    suits = ["s", "o"]

    # Determine canonical hand string
    if r1 == r2:
        hand = f"{r1}{r2}"
    else:
        s = random.choice(suits)
        if RANKS.index(r1) < RANKS.index(r2):
            hand = f"{r1}{r2}{s}"
        else:
            hand = f"{r2}{r1}{s}"

    stack_bb = random.randint(1, 15)
    pos = random.choice(POSITIONS)
    players_left = random.randint(2, 9)

    # Generate specific card codes ONCE
    card1_code, card2_code = generate_specific_card_codes(hand)

    return (hand, stack_bb, pos, players_left, card1_code, card2_code) # Return 6 items now

# --- Session State Initialization ---
def initialize_session_state():
    """Initialize or reset the session state for the quiz."""
    # Check if scenarios exist and if the structure is old (5 items) vs new (6 items)
    # This handles cases where the app might be running with old state after code update
    needs_reset = False
    if "quiz_started" not in st.session_state or not st.session_state.quiz_started:
        needs_reset = True
    elif "scenarios" not in st.session_state or not st.session_state.scenarios:
        needs_reset = True
    # Safely check tuple length only if scenarios is not empty
    elif st.session_state.scenarios and len(st.session_state.scenarios[0]) != 6:
         print("INFO: Scenario structure changed. Resetting state.")
         needs_reset = True

    if needs_reset:
        st.session_state.scenarios = [generate_random_scenario() for _ in range(MAX_QUESTIONS)]
        # scenarios now contain (hand, stack, pos, pls, c1, c2)
        st.session_state.current_index = 0
        st.session_state.score = 0
        st.session_state.review_data = []
        st.session_state.show_feedback = False
        st.session_state.user_choice = None
        st.session_state.correct_action = None
        st.session_state.push_range_details = None # Store (advice_str, range_list, percentage)
        st.session_state.quiz_started = True
        st.session_state.feedback_processed = False
        print("INFO: Session state initialized/reset.")


# --- UI Rendering Functions ---

def display_cards(card1_code, card2_code, container):
    """
    Displays the two cards given their specific codes within a container.
    Uses small gap between card columns.
    """
    img1_path = st.session_state.card_images.get(card1_code)
    img2_path = st.session_state.card_images.get(card2_code)

    # This 'with container:' line requires 'container' to be a valid context manager (like a column object)
    with container:
        # The card_container class is styled in main() CSS
        st.markdown('<div class="card-container">', unsafe_allow_html=True)
        # Use gap="small" to minimize space between card images
        col_img1, col_img2 = st.columns(2, gap="small")
        with col_img1:
            if img1_path:
                st.image(Image.open(img1_path), width=CARD_IMG_WIDTH)
            else:
                # Display text placeholder if image missing
                st.error(f"Img Err: {card1_code}") # Log error visually
                st.markdown(f"<div class='card-placeholder'>{card1_code}</div>", unsafe_allow_html=True)
        with col_img2:
            if img2_path:
                st.image(Image.open(img2_path), width=CARD_IMG_WIDTH)
            else:
                # Display text placeholder if image missing
                st.error(f"Img Err: {card2_code}")
                st.markdown(f"<div class='card-placeholder'>{card2_code}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def show_question_ui():
    """Displays the current question UI - HORIZONTAL LAYOUT (3 columns)."""
    index = st.session_state.current_index
    # Unpack all 6 items from the scenario tuple
    hand, stack, pos, players, card1_code, card2_code = st.session_state.scenarios[index]

    st.markdown("---")
    progress = (index + 1) / MAX_QUESTIONS
    st.progress(progress, text=f"Question {index + 1} of {MAX_QUESTIONS}")
    # Style the progress bar itself via CSS

    st.markdown("<br>", unsafe_allow_html=True) # Add space

    # --- Main Content: Info | Cards | Decision ---
    col_info, col_cards, col_action = st.columns([0.35, 0.3, 0.35]) # Adjust ratios as needed

    # --- Left Column: Scenario Info ---
    with col_info:
        with st.container(): # Group info elements
            st.markdown("### Scenario Details")
            # Stack Block
            st.markdown(f"""
            <div class="info-block stack-block">
                 <span class="info-label">Stack</span>
                 <span class="info-value">{stack} BB</span>
            </div>
            """, unsafe_allow_html=True)
            # Position Block
            st.markdown(f"""
            <div class="info-block position-block">
                 <span class="info-label">Position</span>
                 <span class="info-value">{pos}</span>
            </div>
            """, unsafe_allow_html=True)
            # Players Block
            st.markdown(f"""
            <div class="info-block players-block">
                 <span class="info-label">Players Left</span>
                 <span class="info-value">{players}</span>
            </div>
            """, unsafe_allow_html=True)
             # Hand Text (Separate from blocks)
            st.markdown(f"""
            <p class='info-text hand-text'>Your Hand: <strong class='highlight-text'>{hand}</strong></p>
            """, unsafe_allow_html=True)

    # --- Middle Column: Cards ---
    with col_cards:
        # Display cards directly within this column
        display_cards(card1_code, card2_code, col_cards) # Pass col_cards as container

    # --- Right Column: Decision ---
    with col_action:
        with st.container(): # Group decision elements
            st.markdown("### Your Decision")
            st.markdown("<p class='prompt-text'>Push All-In or Fold?</p>", unsafe_allow_html=True)
            # Keep buttons side-by-side within this column
            b_col1, b_col2 = st.columns(2)
            # Add unique part to key using time to try and force button uniqueness if needed
            time_key = time.time()
            with b_col1:
                 if st.button("PUSH ALL-IN 🚀", key=f"push_{index}_{time_key}", use_container_width=True):
                     handle_user_action("push")
                     st.rerun()
            with b_col2:
                 if st.button("FOLD ✋", key=f"fold_{index}_{time_key}", use_container_width=True):
                     handle_user_action("fold")
                     st.rerun()


def show_feedback_ui():
    """Displays feedback and automatically advances - HORIZONTAL LAYOUT."""
    index = st.session_state.current_index
    # Unpack all 6 items
    hand, stack, pos, players, card1_code, card2_code = st.session_state.scenarios[index]
    user_choice = st.session_state.user_choice

    # Get advice details IF they haven't been processed yet for this feedback instance
    # This prevents re-fetching if the screen reruns unexpectedly during sleep
    if not st.session_state.get('feedback_processed', False):
        # Details should have been fetched and stored in handle_user_action
        if 'push_range_details' not in st.session_state or st.session_state.push_range_details is None:
             print("ERROR: push_range_details not found in session state during feedback.")
             try:
                 advice_str, push_range, percentage = get_push_fold_advice(stack, pos, players)
                 st.session_state.push_range_details = (advice_str, push_range, percentage)
             except Exception as e:
                 advice_str, push_range, percentage = (f"Runtime Error: {e}", None, None)
                 st.session_state.push_range_details = (advice_str, push_range, percentage)
        else:
            advice_str, push_range, percentage = st.session_state.push_range_details

        # --- Logic for determining correctness ---
        is_correct = None
        correct_action = "fold" # Default assumption
        logic_error = False

        # Explicitly check if the advice string indicates an error from the logic function
        if isinstance(advice_str, str) and "Error:" in advice_str:
            logic_error = True
            correct_action = "Unknown"
            push_range = None # Ensure push_range is None if there was an error
            percentage = None
        elif isinstance(push_range, list):
            # Logic returned a valid range (could be empty for a fold)
            correct_action = "push" if hand in push_range else "fold"
            is_correct = (user_choice == correct_action)
        else:
            # Unexpected case: advice wasn't error string, but range wasn't a list
            print(f"WARNING: Unexpected push_range type: {type(push_range)}. Treating as error.")
            logic_error = True
            correct_action = "Unknown"
            advice_str = "Error: Invalid range data received." # Override advice
            push_range = None
            percentage = None

        # --- Process Answer Logic ---
        if is_correct is True:
            st.session_state.score += 1
        example_hands = []
        if isinstance(push_range, list) and push_range: # Generate examples only if range is valid list
             example_hands = random.sample(push_range, min(5, len(push_range)))

        # Store processed results for display and review
        # Use different key to avoid conflict with main storage if needed, or just use directly
        st.session_state.processed_feedback = {
            "is_correct": is_correct,
            "correct_action": correct_action,
            "logic_error": logic_error,
            "advice_str": advice_str,
            "percentage": percentage,
            "example_hands": example_hands
        }

        st.session_state.review_data.append({
            "hand": hand, "stack": stack, "pos": pos, "players": players,
            "card1": card1_code, "card2": card2_code,
            "user_action": user_choice,
            "correct_action": correct_action,
            "is_correct": is_correct,
            "advice": advice_str, # Store the potentially modified advice/error string
            "push_range_example": example_hands, # Use processed examples
            "percentage": percentage,
            "logic_error": logic_error
        })
        st.session_state.feedback_processed = True
    else:
        # If already processed, retrieve stored results for display consistency
        processed = st.session_state.processed_feedback
        is_correct = processed["is_correct"]
        correct_action = processed["correct_action"]
        logic_error = processed["logic_error"]
        advice_str = processed["advice_str"]
        percentage = processed["percentage"]
        example_hands = processed["example_hands"]


    # --- Display Feedback (Using 3-Column Layout) ---
    col_info, col_cards, col_feedback = st.columns([0.35, 0.3, 0.35])

    with col_info:
        with st.container():
             st.markdown("### Scenario Recap")
             # Dimmed recap text using smaller font classes
             st.markdown(f"""
             <div style="opacity: 0.75; margin-top: 10px;">
                 <p class='info-text info-text-small'>Stack: <strong>{stack} BB</strong></p>
                 <p class='info-text info-text-small'>Position: <strong>{pos}</strong></p>
                 <p class='info-text info-text-small'>Players: <strong>{players}</strong></p>
                 <p class='info-text info-text-small'>Hand: <strong>{hand}</strong></p>
             </div>
             """, unsafe_allow_html=True)

    with col_cards:
        # Display cards directly in the middle column
        display_cards(card1_code, card2_code, col_cards)

    with col_feedback:
        with st.container():
            st.markdown("### Result & Advice")

            # Use larger alert boxes via CSS
            if logic_error:
                # Display the specific error message stored in advice_str
                st.error(f"⚠️ {advice_str}", icon="🚨")
            elif is_correct:
                st.success(f"✅ Correct! You chose {user_choice.upper()}.", icon="👍")
            else:
                st.error(f"❌ Incorrect. Correct play: {correct_action.upper()}.", icon="👎")

            # Display advice string (could be error or actual advice)
            advice_display = advice_str
            # Only add percentage if it's not an error and percentage is valid
            if not logic_error and percentage is not None:
                advice_display += f" (~{percentage:.1f}%)"

            # Display advice in a styled paragraph
            # Avoid showing advice details if there was a logic error getting the advice itself
            if not logic_error:
                st.markdown(f"<p class='advice-text'>ℹ️ <strong>Advice:</strong> {advice_display}</p>", unsafe_allow_html=True)

                # Only show examples if no error and examples exist
                if example_hands:
                    example_hands_str = ', '.join(example_hands)
                    st.markdown(f"<p class='info-text-small'><em>Examples: {example_hands_str}...</em></p>", unsafe_allow_html=True)
                else: # Handle case where push_range was an empty list (valid fold)
                     st.markdown("<p class='info-text-small'><em>No hands recommended for pushing.</em></p>", unsafe_allow_html=True)
            # If there was a logic_error, the error message is already shown in st.error


    # --- Auto-Advance Logic ---
    st.markdown(f"<div style='text-align: center; margin-top: 25px; font-size: 0.9rem; opacity: 0.7;'>Next question in {FEEDBACK_DELAY_SECONDS:.1f} seconds...</div>", unsafe_allow_html=True) # Added more margin-top
    time.sleep(FEEDBACK_DELAY_SECONDS)

    st.session_state.current_index += 1
    st.session_state.show_feedback = False
    st.session_state.user_choice = None
    if 'processed_feedback' in st.session_state: # Clean up temporary state
         del st.session_state['processed_feedback']
    st.session_state.feedback_processed = False # Reset for the *next* question's feedback

    # Trigger rerun to show next question or final score
    st.rerun()


def show_final_score_ui():
    """Displays the final score and review - BLOCK LAYOUT."""
    st.subheader("🏁 Quiz Completed!")
    score = st.session_state.score
    total = MAX_QUESTIONS
    percent_correct = (score / total * 100) if total > 0 else 0

    # Center the final score block
    col_spacer1, col_score_disp, col_spacer2 = st.columns([0.2, 0.6, 0.2])
    with col_score_disp:
         # Use markdown for a custom score block
         st.markdown(f"""
         <div class="final-score-block">
             <p style='font-size: 1.6rem; margin-bottom: 8px; opacity: 0.9;'>Your Final Score</p>
             <p style='font-size: 4.0rem; font-weight: bold; color: #2ECC71; margin-bottom: 8px;'>{score} / {total}</p>
             <p style='font-size: 1.6rem; opacity: 0.9;'>({percent_correct:.0f}% Correct)</p>
         </div>
         """, unsafe_allow_html=True)
         st.markdown("<br>", unsafe_allow_html=True) # Add space


    st.markdown("### Review Your Answers:")

    review_data = st.session_state.review_data
    if not review_data:
        st.warning("No review data found.")
        return

    # Display review items clearly
    for i, row in enumerate(review_data):
        with st.container(border=True): # Use container with border for separation
            col1, col2 = st.columns([0.75, 0.25])
            with col1:
                # Note: If you want to show the specific cards in review, you'd use row['card1'], row['card2'] here
                # For now, just showing the canonical hand string
                st.markdown(
                    f"<p class='review-question'><strong>Q{i+1}: {row['hand']}</strong> ({row['stack']}BB, {row['pos']}, {row['players']} left)</p>",
                    unsafe_allow_html=True
                )
                your_action_str = row['user_action'].upper()
                correct_action_str = row['correct_action'].upper() if not row['logic_error'] else "N/A"
                st.markdown(
                     f"<p class='review-details'>Your Choice: <strong>{your_action_str}</strong> | Correct: <strong>{correct_action_str}</strong></p>",
                     unsafe_allow_html=True
                )

                # Use the advice string stored in the review data
                advice_disp = row['advice']
                # Add percentage only if it wasn't a logic error getting the advice
                if not row['logic_error'] and row['percentage'] is not None:
                    advice_disp += f" (~{row['percentage']:.1f}%)"

                if row['logic_error']:
                     # Display the specific error message stored in 'advice'
                     st.markdown(f"<p class='review-advice error'>⚠️ {row['advice']}</p>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<p class='review-advice'>ℹ️ Advice: {advice_disp}</p>", unsafe_allow_html=True)
                    if row['push_range_example']:
                        st.caption(f"<small>Examples: {', '.join(row['push_range_example'])}</small>", unsafe_allow_html=True)

            with col2:
                # Use larger text/icons or custom markdown for review feedback
                if row["logic_error"]:
                    st.warning("Data Error", icon="⚠️") # More generic message if logic failed
                elif row["is_correct"]:
                    st.success("✅ Correct")
                else:
                    st.error("❌ Incorrect")

    st.markdown("---")
    # Centered Try Again button
    col_b1, col_b2, col_b3 = st.columns([0.3, 0.4, 0.3])
    with col_b2:
        if st.button("🔄 TRY AGAIN", key="retry_final", use_container_width=True):
            st.session_state.quiz_started = False
            st.rerun()

# --- Main Application Logic ---
def handle_user_action(user_action):
    """Stores user action and gets advice from poker_logic."""
    st.session_state.user_choice = user_action
    index = st.session_state.current_index
    # Unpack scenario to get needed info for logic
    # We unpack all 6 items, but only need some for get_push_fold_advice
    hand, stack, pos, players, _, _ = st.session_state.scenarios[index]

    # Check if logic is available before calling
    if not logic_available:
        print("ERROR: poker_logic not available in handle_user_action")
        st.error("Poker logic module not available. Cannot process action.")
        st.session_state.push_range_details = ("Error: Logic unavailable", None, None) # Set error state
        st.session_state.show_feedback = True # Show feedback screen with error
        return # Stop processing here

    try:
        # Call the potentially updated get_push_fold_advice
        advice_str, push_range, percentage = get_push_fold_advice(stack, pos, players)
        st.session_state.push_range_details = (advice_str, push_range, percentage)
        # Check if the advice string indicates an error from the logic function itself
        if isinstance(advice_str, str) and "Error:" in advice_str:
             print(f"WARNING from poker_logic: {advice_str}") # Log the specific error
             # Ensure push_range is None if logic signaled an error
             # The tuple stored might already reflect this based on get_push_fold_advice return
             if push_range is not None or percentage is not None:
                 st.session_state.push_range_details = (advice_str, None, None)


    except Exception as e:
        print(f"ERROR calling get_push_fold_advice: {e}") # Log runtime error
        st.error(f"Runtime error getting advice: {e}") # Show generic error to user
        st.session_state.push_range_details = (f"Runtime Error: {e}", None, None) # Set error state

    st.session_state.show_feedback = True


def main():
    st.set_page_config(
        page_title="Poker Push/Fold Trainer",
        layout="wide",
        initial_sidebar_state="collapsed" # Collapse sidebar if not used
    )

    # Custom CSS - BLOCK LAYOUT STYLING (incorporating previous adjustments)
    st.markdown(f"""
    <style>
        /* Base font size */
        html, body, [class*="css"] {{
            font-size: 18px;
        }}
        /* App background */
        .stApp {{
            background-color: #F0F2F6; /* Light grey background like image */
        }}

        /* Headings */
        h1 {{ /* Main Title */
             font-size: 2.5rem !important;
             color: #31333F;
             text-align: center;
             margin-bottom: 5px !important;
             font-weight: 600; /* Bolder title */
             letter-spacing: 1px; /* Add some letter spacing */
         }}
        h3 {{ /* Section Headings like 'Scenario Details' */
            font-size: 1.6rem !important;
            color: #444;
            margin-bottom: 15px !important;
            border-bottom: 1px solid #ddd; /* Subtle separator */
            padding-bottom: 5px;
            font-weight: 500;
        }}
        /* Caption below title */
        [data-testid="stCaptionContainer"] p {{
            text-align: center;
            font-size: 1.0rem;
            color: #666;
            margin-bottom: 25px; /* Space below caption */
        }}


        /* Progress Bar */
        .stProgress > div > div > div > div {{
             background-color: #2ECC71; /* Green progress */
             height: 10px !important; /* Thicker bar */
             border-radius: 5px;
        }}
         .stProgress {{ /* Container for progress bar */
             padding: 0 10px; /* Add slight padding */
         }}

        [data-testid="stText"] {{ /* Styling the text next to progress bar */
            font-size: 0.9rem;
            color: #555;
            padding-bottom: 15px; /* Space below progress bar */
            text-align: center; /* Center progress text */
        }}

        /* --- Block Styling --- */

        /* Common style for info blocks (Stack, Pos, Players) */
        .info-block {{
            background-color: #31333F; /* Dark block background */
            color: #FFFFFF;
            padding: 18px 25px; /* Adjust padding */
            border-radius: 8px;
            margin-bottom: 15px; /* Space between blocks */
            line-height: 1.2;
            text-align: left;
            box-shadow: 0 3px 6px rgba(0,0,0,0.1);
            display: flex; /* Use flexbox for label/value alignment */
            justify-content: space-between; /* Push label and value apart */
            align-items: center; /* Center items vertically */
            min-height: 70px; /* Ensure blocks have a consistent minimum height */
        }}
        .info-block .info-label {{
             font-size: 1.1rem; /* Slightly smaller label */
             opacity: 0.8;
             margin-right: 15px; /* Space between label and value */
             font-weight: 400;
        }}
        .info-block .info-value {{
            font-size: 2.2rem; /* Large value text */
            font-weight: bold;
            text-align: right; /* Keep value aligned right */
        }}
        /* Specific adjustment for stack maybe */
        .stack-block .info-value {{
             font-size: 2.5rem; /* Make stack slightly larger */
        }}


        /* Info Text (Hand Text below blocks) */
        .info-text {{ /* Style for Hand: XXX */
            font-size: 1.6rem;
            color: #333;
            margin-bottom: 12px;
            line-height: 1.4;
            font-weight: 400; /* Regular weight */
        }}
        .info-text-small {{ /* Used for Players Left and recap/examples */
             font-size: 1.1rem;
             opacity: 0.7;
             margin-bottom: 15px;
             color: #555;
             line-height: 1.5;
        }}
        .highlight-text {{
            font-weight: bold;
            color: #E67E22; /* Orange highlight */
        }}
        .hand-text {{ /* The "Your Hand: XXX" line */
            margin-top: 25px !important; /* Add space above hand text */
            padding-left: 5px; /* Align slightly with blocks */
         }}

        /* --- Card Centering & Styling (Horizontal Layout) --- */
        /* Container DIV added via markdown in display_cards */
        .card-container {{
            display: flex;
            flex-direction: row; /* Horizontal layout */
            justify-content: center; /* Center horizontally */
            align-items: center; /* Center vertically */
            padding: 0;
            margin: 0;
            gap: 5px; /* Small gap between cards */
            height: 100%;
        }}
        /* Style the columns created by st.columns(2, gap='small') inside display_cards */
        .card-container > div[data-testid="stHorizontalBlock"] {{
             width: auto;
             justify-content: center;
             gap: 5px !important;
             padding: 0;
             margin: 0;
        }}
        /* Style individual card columns */
        .card-container > div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"] {{
             flex: 0 0 auto !important;
             width: auto !important;
             padding: 0 !important;
             margin: 0 !important;
        }}

         /* Card Images */
        .stImage > img {{
             max-width: {CARD_IMG_WIDTH}px; /* Control max width */
             width: 100%; /* Allow shrinking */
             height: auto;
             box-shadow: 0 4px 8px rgba(0,0,0,0.1);
             border-radius: 6px;
             background-color: white;
             padding: 5px;
             border: 1px solid #ddd;
             margin: 0; /* Remove margin */
             display: block;
        }}
         /* Placeholder for missing card image */
         .card-placeholder {{
            width: {CARD_IMG_WIDTH}px;
            height: {int(CARD_IMG_WIDTH * 1.4)}px; /* Approximate aspect ratio */
            border: 2px dashed #ccc;
            background-color: #eee;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 2.5rem;
            font-weight: bold;
            color: #888;
            border-radius: 6px;
         }}


        /* --- Decision Prompt & Buttons --- */
        .prompt-text {{
            font-size: 1.4rem;
            color: #555;
            margin-bottom: 25px; /* More space before buttons */
            text-align: left;
            padding-left: 5px;
            font-weight: 500;
        }}
        .stButton > button {{
            width: 100%; /* Make buttons fill column width */
            padding: 20px 15px !important; /* More vertical padding */
            font-size: 1.4rem !important; /* Clear button text */
            font-weight: bold !important;
            border-radius: 8px !important; /* Less rounded */
            border: 1px solid #CCCCCC !important; /* Lighter border */
            background-color: #FFFFFF !important; /* White background */
            color: #333333 !important; /* Dark text */
            transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
            margin-top: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); /* Subtle shadow */
            line-height: 1.2; /* Adjust line height for emojis */
            display: flex; /* Help center content */
            justify-content: center;
            align-items: center;
        }}
         .stButton > button:hover {{
             background-color: #F8F8F8 !important;
             border-color: #AAAAAA !important;
             box-shadow: 0 3px 6px rgba(0,0,0,0.08); /* Slightly more shadow on hover */
         }}
         .stButton > button:active {{ /* Style for when button is clicked */
              background-color: #F0F0F0 !important;
              box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
         }}
         /* Specific styling for final button - keep it distinct */
         button:contains("TRY AGAIN") {{
             background-color: #F39C12 !important;
             color: black !important;
             border-color: #e67e22 !important;
             font-size: 1.5rem !important;
             padding: 20px 35px !important;
             box-shadow: 0 3px 6px rgba(0,0,0,0.1);
         }}
         button:contains("TRY AGAIN"):hover {{
             background-color: #e67e22 !important;
             border-color: #d35400 !important;
         }}

        /* --- Feedback Boxes, Advice Text, Final Score, Review Items --- */
        [data-testid="stAlert"] {{
             border-radius: 8px !important;
             border: none !important; /* Remove default border */
             box-shadow: 0 2px 5px rgba(0,0,0,0.1);
             margin-top: 10px; /* Add space above alerts */
        }}
        [data-testid="stAlert"] > div {{
             font-size: 1.4rem !important;
             padding: 18px !important;
             font-weight: 500;
        }}
        [data-testid="stAlert"] svg {{
            width: 28px !important; height: 28px !important;
        }}
        .advice-text {{
             font-size: 1.3rem;
             background-color: #E8F0FE; /* Light blue background */
             color: #31333F;
             padding: 15px;
             border-radius: 5px;
             margin-top: 20px; /* More space above advice */
             line-height: 1.5;
             font-weight: 400;
        }}
         .advice-text strong {{ /* Make 'Advice:' bold */
             font-weight: 600;
         }}
        .final-score-block {{
            background-color: #FFFFFF; /* White background */
            padding: 30px 40px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.08);
            margin-top: 20px; /* Space above score */
        }}
        .stContainer[border=true] {{ /* Target review containers */
             background-color: #FFFFFF;
             padding: 15px 20px;
             margin-bottom: 15px;
             box-shadow: 0 1px 3px rgba(0,0,0,0.05);
             border-radius: 8px;
        }}
        .review-question {{ font-size: 1.4rem; font-weight: 500; margin-bottom: 8px; }}
        .review-details {{ font-size: 1.2rem; margin-bottom: 8px; }}
        .review-advice {{ font-size: 1.1rem; color: #555; }}
        .review-advice.error {{ color: #C0392B; font-weight: 500; }} /* Style error advice */

        /* --- General Spacing --- */
         div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {{
             gap: 0.5rem; /* Reduce gap between elements in columns */
         }}

    </style>
    """, unsafe_allow_html=True)


    # Use suit emojis in title
    st.title("♠️ ♥️ Poker Push/Fold Trainer ♦️ ♣️")
    st.caption("Practice short-stack tournament decisions.")

    # Check logic availability after imports
    if not logic_available:
         st.error("Application cannot start due to issues loading 'poker_logic.py' or its dependencies.")
         st.info("Please ensure 'poker_logic.py' and 'push ranges.csv' are present and correct.")
         st.stop() # Halt execution

    # --- Load Assets ---
    load_card_images() # Load images early

    # --- Initialize State ---
    initialize_session_state() # Ensure state is ready

    # --- Main UI Logic ---
    if st.session_state.current_index < MAX_QUESTIONS:
        if st.session_state.show_feedback:
            # The feedback UI now handles the delay and state update internally
            show_feedback_ui()
        else:
            show_question_ui()
    else:
        # Quiz finished, show results
        show_final_score_ui()

# --- Main execution block ---
if __name__ == "__main__":
    main()
