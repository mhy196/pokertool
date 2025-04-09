import os
import random
import customtkinter as ctk
from PIL import Image

# We assume you have this function in your code or a separate module:
# from poker_logic import get_push_fold_advice, RANKS
# For demonstration, we'll define a minimal stand-in here:
def get_push_fold_advice(stack, position, players_left):
    """
    Example placeholder logic:
    Return (advice_string, push_range), where push_range is a list of combos like 'A2s','TT', etc.
    In real code, you'd have your actual logic for short-stack push/fold.
    """
    # We'll just randomly pick some made-up push range:
    mock_push_range = ["A2s","A3s","A4s","KJo","QJs","TT","JJ","QQ","KK","AA"]
    return ("Push 20% range", mock_push_range)

RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]


class PushFoldTrainerFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Optional: set the overall background color
        self.configure(fg_color="#F4F5F7")

        # Define your possible positions & random seeds
        self.positions = ["UT", "UTG+1", "MP", "LJ", "HJ", "CO", "BTN", "SB"]
        self.stacks = range(3, 15)          # 3BB to 14BB
        self.players_left_choices = range(2, 10)  # 2 to 9 players

        self.scenarios = []     # Will store a list of (hand, stack, pos, #players)
        self.current_index = 0
        self.score = 0
        self.review_data = []   # For final review of all answers

        # Holds the loaded card images (e.g. "As" -> CTkImage).
        self.card_images = {}
        self._load_card_images()

        # ----- LAYOUT -----
        self.grid_columnconfigure(0, weight=1)

        # Title area
        self.title_frame = ctk.CTkFrame(self, fg_color="#E1E5EB", corner_radius=10)
        self.title_frame.grid(row=0, column=0, pady=(10,5), padx=10, sticky="ew")
        self.title_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.title_frame,
            text="Push/Fold Training",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#1B1B1B"
        )
        self.title_label.grid(row=0, column=0, padx=10, pady=8, sticky="n")

        # Card display frame
        self.card_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.card_frame.grid(row=1, column=0, padx=10, pady=(5,2), sticky="n")
        self.card_frame.grid_columnconfigure((0,1), weight=1)

        self.card1_label = ctk.CTkLabel(self.card_frame, text="", width=80, height=110)
        self.card1_label.grid(row=0, column=0, padx=(0,10), pady=5)
        self.card2_label = ctk.CTkLabel(self.card_frame, text="", width=80, height=110)
        self.card2_label.grid(row=0, column=1, padx=(10,0), pady=5)

        # Scenario display
        self.scenario_label = ctk.CTkLabel(
            self,
            text="(Scenario here)",
            wraplength=600,
            font=ctk.CTkFont(size=14),
            text_color="#3A3A3A"
        )
        self.scenario_label.grid(row=2, column=0, padx=10, pady=5, sticky="n")

        # Buttons Frame
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=3, column=0, padx=10, pady=5, sticky="n")

        self.push_button = ctk.CTkButton(
            self.button_frame,
            text="Push",
            corner_radius=8,
            width=80,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda: self._answer("push")
        )
        self.push_button.pack(side="left", padx=(0,5))

        self.fold_button = ctk.CTkButton(
            self.button_frame,
            text="Fold",
            corner_radius=8,
            width=80,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda: self._answer("fold")
        )
        self.fold_button.pack(side="left")

        # Feedback Label
        self.feedback_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.feedback_label.grid(row=4, column=0, padx=10, pady=5, sticky="n")

        # Start a session
        self._start_new_session()


    # ---------------------------------------------------
    # 1) LOAD CARD IMAGES (adjust to your file structure)
    # ---------------------------------------------------
    def _load_card_images(self):
        # We assume you have 52 images in assets/cards/ named like "ace_of_spades.png", "10_of_diamonds.png", etc.
        rank_map = {
            'A': 'ace', 'K': 'king', 'Q': 'queen', 'J': 'jack',
            'T': '10', '9': '9', '8': '8', '7': '7',
            '6': '6', '5': '5', '4': '4', '3': '3', '2': '2'
        }
        suit_map = {
            's': 'spades', 'h': 'hearts', 'd': 'diamonds', 'c': 'clubs'
        }

        base_path = "assets/cards"
        size = (80, 110)

        for r, rname in rank_map.items():
            for s, sname in suit_map.items():
                filename = f"{rname}_of_{sname}.png"  # e.g. "ace_of_spades.png"
                full_path = os.path.join(base_path, filename)
                if os.path.exists(full_path):
                    pil_img = Image.open(full_path)
                    pil_img = pil_img.resize(size)
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
                    short_code = f"{r}{s}"  # e.g. "As"
                    self.card_images[short_code] = ctk_img
                else:
                    # If missing, skip or log a warning
                    pass

    # ---------------------------
    # 2) START A NEW QUIZ SESSION
    # ---------------------------
    def _start_new_session(self):
        self.scenarios = [self._generate_random_scenario() for _ in range(5)]
        self.current_index = 0
        self.score = 0
        self.review_data = []

        self._show_current_scenario()
        self.feedback_label.configure(text="", text_color="black")
        self.push_button.configure(state="normal")
        self.fold_button.configure(state="normal")

    # ------------------------------
    # 3) GENERATE RANDOM SCENARIO
    # ------------------------------
    def _generate_random_scenario(self):
        r1 = random.choice(RANKS)
        r2 = random.choice(RANKS)
        suits = ["s", "o"]
        if r1 == r2:
            hand = f"{r1}{r2}"  # Pair
        else:
            s = random.choice(suits)
            # Ensure higher rank is first
            if RANKS.index(r1) < RANKS.index(r2):
                hand = f"{r1}{r2}{s}"
            else:
                hand = f"{r2}{r1}{s}"

        stack_bb = random.choice(list(self.stacks))
        pos = random.choice(self.positions)
        pls = random.choice(list(self.players_left_choices))
        return (hand, stack_bb, pos, pls)

    # ---------------------------
    # 4) SHOW CURRENT SCENARIO
    # ---------------------------
    def _show_current_scenario(self):
        if self.current_index >= len(self.scenarios):
            return

        hand, stack, pos, players = self.scenarios[self.current_index]

        # Display card images
        self._display_cards(hand)

        scenario_text = (
            f"Question {self.current_index + 1} of {len(self.scenarios)}\n\n"
            f"Stack: {stack} BB\n"
            f"Position: {pos}\n"
            f"Players Left: {players}\n\n"
            "Push or Fold?"
        )
        self.scenario_label.configure(text=scenario_text)

    # ----------------------------
    # 5) DISPLAY CARD IMAGES
    # ----------------------------
    def _display_cards(self, hand_str):
        self.card1_label.configure(image=None, text="")
        self.card2_label.configure(image=None, text="")

        # If length=2 => pair (e.g. "TT") => pick random suits
        # If length=3 => e.g. "A2s" => same suit or "A2o" => different suits
        if len(hand_str) == 2:
            # Pair
            suits_avail = ['s','h','d','c']
            s1 = random.choice(suits_avail)
            s2 = random.choice(suits_avail)
            card1_code = f"{hand_str[0]}{s1}"
            card2_code = f"{hand_str[1]}{s2}"
        else:
            rank1, rank2, typ = hand_str[0], hand_str[1], hand_str[2]
            if typ == 's':
                chosen_suit = random.choice(['s','h','d','c'])
                card1_code = f"{rank1}{chosen_suit}"
                card2_code = f"{rank2}{chosen_suit}"
            else:
                # offsuit => 2 different suits
                suits_avail = ['s','h','d','c']
                s1 = random.choice(suits_avail)
                s2 = random.choice(suits_avail)
                while s2 == s1:
                    s2 = random.choice(suits_avail)
                card1_code = f"{rank1}{s1}"
                card2_code = f"{rank2}{s2}"

        img1 = self.card_images.get(card1_code)
        img2 = self.card_images.get(card2_code)

        if img1:
            self.card1_label.configure(image=img1, text="")
        else:
            self.card1_label.configure(text=card1_code, font=ctk.CTkFont(size=16, weight="bold"))

        if img2:
            self.card2_label.configure(image=img2, text="")
        else:
            self.card2_label.configure(text=card2_code, font=ctk.CTkFont(size=16, weight="bold"))

    # ---------------------------------
    # 6) USER ANSWER: PUSH OR FOLD
    # ---------------------------------
    def _answer(self, user_action):
        if self.current_index >= len(self.scenarios):
            return

        hand, stack, pos, players = self.scenarios[self.current_index]
        advice_str, push_range = get_push_fold_advice(stack, pos, players)
        correct_action = "push" if hand in push_range else "fold"

        if user_action == correct_action:
            self.score += 1
            self.feedback_label.configure(text="Correct!", text_color="#008B00")
        else:
            self.feedback_label.configure(text=f"Incorrect! (Correct: {correct_action.upper()})",
                                          text_color="#B00020")

        # Store review info: (hand, stack, pos, players, user_action, correct_action)
        self.review_data.append((hand, stack, pos, players, user_action, correct_action))

        self.push_button.configure(state="disabled")
        self.fold_button.configure(state="disabled")

        # Auto next
        self.after(1200, self._go_next_question)

    # ---------------------------------
    # 7) NEXT QUESTION OR FINAL SCREEN
    # ---------------------------------
    def _go_next_question(self):
        self.current_index += 1
        if self.current_index < len(self.scenarios):
            self.feedback_label.configure(text="", text_color="black")
            self.push_button.configure(state="normal")
            self.fold_button.configure(state="normal")
            self._show_current_scenario()
        else:
            self._show_final_score()

    # ----------------------------
    # 8) SHOW SCORE + REVIEW
    # ----------------------------
    def _show_final_score(self):
        self.feedback_label.configure(text="", text_color="black")
        final_text = f"You scored {self.score} out of {len(self.scenarios)}.\n"
        if self.score == len(self.scenarios):
            final_text += "Excellent!"
        elif self.score >= 3:
            final_text += "Good job!"
        else:
            final_text += "Keep practicing."

        # Show score summary in the scenario_label
        self.scenario_label.configure(text=final_text)

        # Create a scrollable frame for the color-coded review
        review_frame = ctk.CTkScrollableFrame(self, label_text="Review of All Answers")
        review_frame.grid(row=5, column=0, padx=10, pady=10, sticky="nsew")
        review_frame.grid_columnconfigure(0, weight=1)

        # Loop over each question/answer from self.review_data
        for i, (hand, st, pos, pls, ua, ca) in enumerate(self.review_data):
            # Did the user get it correct?
            is_correct = (ua == ca)

            # Choose background color for correctness
            # Light green for correct, light red for incorrect
            bg_color = "#E6F4EA" if is_correct else "#FCEBEA"

            # Create a small frame to hold the question details + your answer
            line_frame = ctk.CTkFrame(review_frame, fg_color=bg_color, corner_radius=8)
            line_frame.pack(fill="x", padx=5, pady=3)

            # Build your line text
            # 1st line: scenario details
            question_text = f"Q{i+1}: {hand} ({st}BB, {pos}, {pls} left)"
            question_label = ctk.CTkLabel(
                line_frame,
                text=question_text,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
                justify="left",
                text_color="#333333"
            )
            question_label.pack(anchor="w", padx=8, pady=(4,2))

            # 2nd line: user vs. correct
            # If you want your action in green/red text specifically, you can do that,
            # but here we’re just using black text + a colored background
            answer_text = f"You: {ua.upper()}   |   Correct: {ca.upper()}"
            answer_label = ctk.CTkLabel(
                line_frame,
                text=answer_text,
                font=ctk.CTkFont(size=12),
                anchor="w",
                justify="left",
                text_color="#444444"
            )
            answer_label.pack(anchor="w", padx=8, pady=(0,4))

        # "Retry" button
        retry_btn = ctk.CTkButton(
            self,
            text="Retry",
            corner_radius=8,
            width=100,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_new_session
        )
        retry_btn.grid(row=6, column=0, padx=10, pady=(0,15), sticky="n")


# -----------------------------
# MAIN APPLICATION
# -----------------------------
class PokerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Poker Trainer Example")
        self.geometry("900x700")

        # TabView
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)

        # Create a tab for the trainer
        self.tab_view.add("Push/Fold Training")
        training_tab = self.tab_view.tab("Push/Fold Training")

        # Put the trainer frame on that tab
        self.trainer_frame = PushFoldTrainerFrame(training_tab, fg_color="transparent")
        self.trainer_frame.pack(expand=True, fill="both")


if __name__ == "__main__":
    ctk.set_appearance_mode("System")  # or "Dark" / "Light"
    ctk.set_default_color_theme("blue") 
    app = PokerApp()
    app.mainloop()
