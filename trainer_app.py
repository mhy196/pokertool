##########################################
# trainer_app.py (Real Tips Version)
##########################################
import streamlit as st
import os
import random
import time
from PIL import Image

######################
# Import from poker_logic
######################
try:
    from poker_logic import (
        get_push_fold_advice,  # Must return (advice_str, push_range, percentage, tips_str)
        RANKS,
    )
    logic_available = True
except ImportError as e:
    st.error(f"Critical Error: Could not import 'poker_logic.py'. Ensure it's in the same directory. Details: {e}")
    logic_available = False
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during poker_logic import: {e}")
    logic_available = False
    st.stop()

######################
# Configuration & Constants
######################
POSITIONS = ["SB", "BTN", "CO", "HJ", "LJ", "UTG+3", "UTG+2", "UTG+1"]
MAX_QUESTIONS = 5
CARD_IMG_WIDTH = 170
FEEDBACK_DELAY_SECONDS = 2.0  # 2 seconds delay after user answers

######################
# Load Card Images
######################
def load_card_images():
    """Loads card images into session_state.card_images."""
    if "card_images" not in st.session_state:
        st.session_state.card_images = {}

        rank_map = {
            'A': 'ace', 'K': 'king', 'Q': 'queen', 'J': 'jack', 'T': '10',
            '9': '9', '8': '8', '7': '7', '6': '6', '5': '5', '4': '4', '3': '3', '2': '2'
        }
        suit_map = {'s': 'spades', 'h': 'hearts', 'd': 'diamonds', 'c': 'clubs'}

        base_path = "assets/cards"
        if not os.path.isdir(base_path):
            st.error(f"Error: Card image directory not found at '{base_path}'.")
            st.stop()

        loaded_count = 0
        for r, rname in rank_map.items():
            for s, sname in suit_map.items():
                filename = f"{rname}_of_{sname}.png"
                full_path = os.path.join(base_path, filename)
                short_code = f"{r}{s}"
                if os.path.exists(full_path):
                    st.session_state.card_images[short_code] = full_path
                    loaded_count += 1

        if loaded_count < 52:
            st.warning(f"Only loaded {loaded_count}/52 card images. Some cards may be missing.")

######################
# Generate Card Codes
######################
def generate_specific_card_codes(hand_str):
    """
    From a canonical hand notation like 'A2s' or 'TT',
    generate the specific card codes (e.g. 'As','2s').
    """
    if len(hand_str) == 2:  # Pair
        rank = hand_str[0]
        suits_avail = ['s', 'h', 'd', 'c']
        s1 = random.choice(suits_avail)
        suits_avail.remove(s1)
        s2 = random.choice(suits_avail)
        card1_code = f"{rank}{s1}"
        card2_code = f"{rank}{s2}"
    else:
        rank1, rank2, type = hand_str[0], hand_str[1], hand_str[2]
        if type == 's':
            chosen_suit = random.choice(['s', 'h', 'd', 'c'])
            card1_code = f"{rank1}{chosen_suit}"
            card2_code = f"{rank2}{chosen_suit}"
        else:  # 'o'
            suits_avail = ['s', 'h', 'd', 'c']
            s1 = random.choice(suits_avail)
            suits_avail.remove(s1)
            s2 = random.choice(suits_avail)
            if RANKS.index(rank1) < RANKS.index(rank2):
                card1_code = f"{rank1}{s1}"
                card2_code = f"{rank2}{s2}"
            else:
                card1_code = f"{rank2}{s1}"
                card2_code = f"{rank1}{s2}"
    return card1_code, card2_code

######################
# Generate a scenario
######################
def generate_random_scenario():
    """
    Returns (hand, stack, pos, players, card1_code, card2_code).
    """
    r1 = random.choice(RANKS)
    r2 = random.choice(RANKS)
    suits = ["s", "o"]
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

    card1_code, card2_code = generate_specific_card_codes(hand)
    return (hand, stack_bb, pos, players_left, card1_code, card2_code)

######################
# Initialize
######################
def initialize_session_state():
    """Initialize or reset the quiz session."""
    if "quiz_started" not in st.session_state or not st.session_state.quiz_started:
        _reset_quiz_state()
    elif "scenarios" not in st.session_state or not st.session_state.scenarios:
        _reset_quiz_state()
    elif st.session_state.scenarios and len(st.session_state.scenarios[0]) != 6:
        _reset_quiz_state()

def _reset_quiz_state():
    st.session_state.scenarios = [generate_random_scenario() for _ in range(MAX_QUESTIONS)]
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.review_data = []
    st.session_state.show_feedback = False
    st.session_state.user_choice = None
    st.session_state.correct_action = None
    st.session_state.push_range_details = None
    st.session_state.quiz_started = True
    st.session_state.feedback_processed = False

######################
# Display Cards
######################
def display_cards(card1_code, card2_code, container):
    """
    Displays two card images in a container.
    """
    img1_path = st.session_state.card_images.get(card1_code)
    img2_path = st.session_state.card_images.get(card2_code)
    with container:
        st.markdown('<div class="card-container">', unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="small")
        with c1:
            if img1_path:
                st.image(Image.open(img1_path), width=CARD_IMG_WIDTH)
            else:
                st.error(f"Missing: {card1_code}")
        with c2:
            if img2_path:
                st.image(Image.open(img2_path), width=CARD_IMG_WIDTH)
            else:
                st.error(f"Missing: {card2_code}")
        st.markdown('</div>', unsafe_allow_html=True)

######################
# Show question
######################
def show_question_ui():
    index = st.session_state.current_index
    hand, stack, pos, players, c1, c2 = st.session_state.scenarios[index]

    st.markdown("---")
    progress = (index + 1) / MAX_QUESTIONS
    st.progress(progress, text=f"Question {index + 1} / {MAX_QUESTIONS}")
    st.markdown("<br>", unsafe_allow_html=True)

    col_info, col_cards, col_action = st.columns([0.35, 0.3, 0.35])
    with col_info:
        st.markdown("### Scenario Details")
        st.markdown(f"""
        <div class="info-block stack-block">
            <span class="info-label">Stack</span>
            <span class="info-value">{stack} BB</span>
        </div>
        <div class="info-block position-block">
            <span class="info-label">Position</span>
            <span class="info-value">{pos}</span>
        </div>
        <div class="info-block players-block">
            <span class="info-label">Players</span>
            <span class="info-value">{players}</span>
        </div>
        <p class='info-text hand-text'>Your Hand: <strong class='highlight-text'>{hand}</strong></p>
        """, unsafe_allow_html=True)

    with col_cards:
        display_cards(c1, c2, col_cards)

    with col_action:
        st.markdown("### Your Decision")
        st.markdown("<p class='prompt-text'>Push All-In or Fold?</p>", unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        with b1:
            if st.button("PUSH ALL-IN 🚀", key=f"push_{index}", use_container_width=True):
                handle_user_action("push")
                st.rerun()
        with b2:
            if st.button("FOLD ✋", key=f"fold_{index}", use_container_width=True):
                handle_user_action("fold")
                st.rerun()

######################
# Handle user action
######################
def handle_user_action(user_action):
    st.session_state.user_choice = user_action
    st.session_state.show_feedback = True

######################
# Show feedback
######################
def show_feedback_ui():
    """
    Displays only a feedback message + real tips, then auto-advances after 2s.
    """
    idx = st.session_state.current_index
    hand, stack, pos, players, c1, c2 = st.session_state.scenarios[idx]
    user_action = st.session_state.user_choice

    if not logic_available:
        st.error("Poker logic not available.")
        st.session_state.push_range_details = ("Error: Logic Unavailable", None, None, "No tips found.")
    else:
        # In your poker_logic, ensure we return a 4th item: tips_str
        # e.g.: (advice_str, push_range, percentage, tips_str)
        try:
            advice_str, push_range, percentage, tips_str = get_push_fold_advice(stack, pos, players)
            if isinstance(advice_str, str) and "Error:" in advice_str:
                push_range = None
                percentage = None
                # tips_str can still be shown if it was included
        except Exception as e:
            advice_str = f"Error: {e}"
            push_range = None
            percentage = None
            tips_str = "No tips - error occurred."

    # Evaluate correctness
    if push_range and hand in push_range:
        correct_action = "push"
    else:
        correct_action = "fold"

    is_correct = None
    if push_range is not None:
        is_correct = (user_action == correct_action)
    # Show immediate feedback
    st.markdown("---")
    st.markdown("## Feedback")

    if is_correct is True:
        st.session_state.score += 1
        st.success(f"✅ Correct! You chose {user_action.upper()}.", icon="👍")
    elif is_correct is False:
        st.error(f"❌ Incorrect. Correct: {correct_action.upper()}.", icon="👎")
    else:
        st.error(f"⚠️ {advice_str}", icon="🚨")

    # If no error, show advice & tips
    if is_correct is not None:
        disp = advice_str
        if percentage is not None:
            disp += f" (~{percentage:.1f}%)"
        st.markdown(f"**Advice:** {disp}")
        st.markdown(f"**Tips:** {tips_str}")

    # Add to review_data
    st.session_state.review_data.append({
        "hand": hand,
        "stack": stack,
        "pos": pos,
        "players": players,
        "card1": c1,
        "card2": c2,
        "user_action": user_action,
        "correct_action": correct_action if is_correct is not None else "Unknown",
        "is_correct": is_correct,
        "advice": advice_str,
        "percentage": percentage,
        "logic_error": (is_correct is None),
        "tips": tips_str
    })

    st.markdown(f"<div style='text-align:center;margin-top:25px;font-size:0.9rem;opacity:0.7;'>Next question in {FEEDBACK_DELAY_SECONDS:.1f} seconds...</div>", unsafe_allow_html=True)
    time.sleep(FEEDBACK_DELAY_SECONDS)

    st.session_state.current_index += 1
    st.session_state.show_feedback = False
    st.session_state.user_choice = None
    st.rerun()

######################
# Final score
######################
def show_final_score_ui():
    st.subheader("🏁 Quiz Completed!")
    score = st.session_state.score
    total = MAX_QUESTIONS
    pct = (score / total * 100) if total else 0

    col_spacer1, col_score, col_spacer2 = st.columns([0.2, 0.6, 0.2])
    with col_score:
        st.markdown(f"""
        <div class="final-score-block">
          <p style='font-size:1.6rem;margin-bottom:8px;opacity:0.9;'>Your Final Score</p>
          <p style='font-size:4.0rem;font-weight:bold;color:#2ECC71;margin-bottom:8px;'>{score} / {total}</p>
          <p style='font-size:1.6rem;opacity:0.9;'>({pct:.0f}% Correct)</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### Review Your Answers:")
    review_data = st.session_state.review_data
    if not review_data:
        st.warning("No review data found.")
        return

    for i, row in enumerate(review_data):
        with st.container():
            cL, cR = st.columns([0.75, 0.25])
            with cL:
                st.markdown(
                    f"<p class='review-question'><strong>Q{i+1}: {row['hand']}</strong> ({row['stack']}BB, {row['pos']}, {row['players']} left)</p>",
                    unsafe_allow_html=True
                )
                ua = row['user_action'].upper()
                ca = row['correct_action'].upper()
                st.markdown(
                    f"<p class='review-details'>Your Choice: <strong>{ua}</strong> | Correct: <strong>{ca}</strong></p>",
                    unsafe_allow_html=True
                )

                advice_disp = row['advice']
                if not row['logic_error'] and row['percentage'] is not None:
                    advice_disp += f" (~{row['percentage']:.1f}%)"

                if row['logic_error']:
                    st.markdown(f"<p class='review-advice error'>⚠️ {advice_disp}</p>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<p class='review-advice'>ℹ️ Advice: {advice_disp}</p>", unsafe_allow_html=True)

                if row.get("tips"):
                    st.markdown(f"<p style='font-size:1.1rem; color:#555;'><strong>Tip:</strong> {row['tips']}</p>", unsafe_allow_html=True)

            with cR:
                if row["logic_error"]:
                    st.warning("Data Error", icon="⚠️")
                elif row["is_correct"]:
                    st.success("✅ Correct")
                else:
                    st.error("❌ Incorrect")

    st.markdown("---")
    c1, c2, c3 = st.columns([0.3, 0.4, 0.3])
    with c2:
        if st.button("🔄 TRY AGAIN", key="retry_final", use_container_width=True):
            st.session_state.quiz_started = False
            st.rerun()

######################
# main
######################
def main():
    st.set_page_config(
        page_title="Poker Push/Fold Trainer",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Minimal extra CSS
    st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-size: 18px;
        }
        .info-block {
            background-color: rgba(49,51,63,0.1);
        }
        .info-label {
            font-size: 1.1rem;
            opacity: 0.85;
        }
        .info-value {
            font-size: 2.0rem;
            font-weight: bold;
        }
        .highlight-text { color: #E67E22; }
        .card-container {
            display: flex; flex-direction: row; justify-content: center; align-items: center;
            gap: 5px; margin: 0; padding: 0;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("♠️ ♥️ Poker Push/Fold Trainer ♦️ ♣️")
    st.caption("Practice short-stack tournament decisions.")

    if not logic_available:
        st.error("poker_logic.py unavailable.")
        st.stop()

    load_card_images()
    initialize_session_state()

    if st.session_state.current_index < MAX_QUESTIONS:
        if st.session_state.show_feedback:
            show_feedback_ui()
        else:
            show_question_ui()
    else:
        show_final_score_ui()

if __name__ == "__main__":
    main()
