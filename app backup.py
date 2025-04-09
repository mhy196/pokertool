# poker_tool_app.py
import customtkinter as ctk
from poker_logic import (
    calculate_pot_odds,
    calculate_required_equity,
    calculate_equity_from_outs,
    get_hand_combos,
    calculate_range_percentage,
    calculate_mdf,
    calculate_bluff_break_even,
    calculate_spr,
    calculate_bet_size,
    calculate_icm,
    get_push_fold_advice,
    get_hand_strength,        # <-- Import new Hand Strength function
    calculate_hand_vs_range_equity,
    # parse_card_input,
    RANKS,
    get_all_hands # Need this for parsing ranges
)
from push_fold_trainer_frame import PushFoldTrainerFrame
import pyperclip # Import pyperclip for clipboard functionality

# --- Helper Functions for Range Text ---

def format_range_to_text(selected_hands_set):
    """
    Formats a set of selected hands into a standard text string.
    Implements condensed range notation for better readability.
    """
    if not selected_hands_set:
        return ""

    # Convert to list and sort
    hands = sorted(list(selected_hands_set))
    result = []
    
    # Group hands by type (pairs, suited, offsuit)
    pairs = []
    suited = {}  # key: first card, value: list of second cards
    offsuit = {} # key: first card, value: list of second cards
    
    for hand in hands:
        if len(hand) == 2:  # Pair
            pairs.append(hand[0])  # Just need one card since it's a pair
        elif hand.endswith('s'):  # Suited
            first, second = hand[0], hand[1]
            if first not in suited:
                suited[first] = []
            suited[first].append(second)
        elif hand.endswith('o'):  # Offsuit
            first, second = hand[0], hand[1]
            if first not in offsuit:
                offsuit[first] = []
            offsuit[first].append(second)
    
    # Process pairs
    if pairs:
        current_range = [pairs[0]]
        for i in range(1, len(pairs)):
            if RANKS.index(pairs[i]) != RANKS.index(pairs[i-1]) - 1:
                # Gap in sequence, end current range
                if len(current_range) > 2:
                    result.append(f"{current_range[-1]}{current_range[-1]}-{current_range[0]}{current_range[0]}")
                elif len(current_range) == 2:
                    result.extend([f"{c}{c}" for c in reversed(current_range)])
                else:
                    result.append(f"{current_range[0]}{current_range[0]}")
                current_range = [pairs[i]]
            else:
                current_range.append(pairs[i])
        # Handle last range
        if len(current_range) > 2:
            result.append(f"{current_range[-1]}{current_range[-1]}-{current_range[0]}{current_range[0]}")
        elif len(current_range) == 2:
            result.extend([f"{c}{c}" for c in reversed(current_range)])
        else:
            result.append(f"{current_range[0]}{current_range[0]}")
    
    # Process suited hands
    for first_card in sorted(suited.keys()):
        second_cards = sorted(suited[first_card], key=lambda x: RANKS.index(x))
        if len(second_cards) > 2:
            result.append(f"{first_card}{second_cards[-1]}s-{first_card}{second_cards[0]}s")
        else:
            for second in reversed(second_cards):
                result.append(f"{first_card}{second}s")
    
    # Process offsuit hands
    for first_card in sorted(offsuit.keys()):
        second_cards = sorted(offsuit[first_card], key=lambda x: RANKS.index(x))
        if len(second_cards) > 2:
            result.append(f"{first_card}{second_cards[-1]}o-{first_card}{second_cards[0]}o")
        else:
            for second in reversed(second_cards):
                result.append(f"{first_card}{second}o")
    
    return ",".join(result)

def parse_range_text(range_text):
    """
    Parses a standard range text string into a set of hands.
    Handles:
      - Single combos like "AKs", "A2o", "QQ"
      - 2-char combos like "AK" => automatically "AKs" + "AKo"
      - Pairs "77", "KK+", "TT-JJ"
      - Plus notation "AJs+", "KK+"
      - Dashed combos (pairs OR suited/off-suit) e.g. "A2s-AKs", "K2o-KQo"
         * Currently only supports same first rank on both sides for suited/off-suit combos.
    """
    hands = set()
    all_hands_list = get_all_hands()  # e.g. ["AA","KK","AKs","A2o","K2s",...]
    parts = [h.strip() for h in range_text.split(',') if h.strip()]

    for raw_part in parts:
        # 1) Normalize (e.g. "A2O" => "A2o", "A2s" => "A2s", "99" => "99")
        part = _normalize_card_notation(raw_part)

        # 2) Direct match?
        if part in all_hands_list:
            hands.add(part)
            continue

        # 3) 2-char hand => e.g. "AK" => add "AKs" + "AKo"
        if len(part) == 2 and part[0] != part[1]:
            suited = part + "s"
            offsuit = part + "o"
            if suited in all_hands_list:
                hands.add(suited)
            if offsuit in all_hands_list:
                hands.add(offsuit)
            continue

        # 4) 2-char pair => e.g. "77"
        if len(part) == 2 and part[0] == part[1]:
            if part in all_hands_list:
                hands.add(part)
            continue

        # 5) Dashed range (e.g. "99-22", "A2s-AKs", "K2o-KQo")
        if '-' in part:
            start_str, end_str = part.split('-', 1)
            start_str = _normalize_card_notation(start_str)
            end_str   = _normalize_card_notation(end_str)

            # a) Pairs range? e.g. "99-22" or "77-JJ"
            if _is_pair_str(start_str) and _is_pair_str(end_str):
                parse_dashed_pairs_range(hands, start_str, end_str, all_hands_list)
                continue

            # b) If it's not pairs, check if both sides are 3-chars like "A2s" / "AKs" or "K2o" / "KQo"
            if _is_suited_offsuit_str(start_str) and _is_suited_offsuit_str(end_str):
                parse_dashed_combo_range(hands, start_str, end_str, all_hands_list)
                continue

            # (If neither pairs nor valid combos, skip or handle error)
            continue

        # 6) Plus notation (e.g. "QQ+", "AJs+", "A2o+")
        if part.endswith('+'):
            base = part[:-1]  # e.g. "QQ", "AJs", "A2o"
            base = _normalize_card_notation(base)
            if _is_pair_str(base):
                # e.g. "TT+" => add TT, JJ, QQ, KK, AA
                parse_pairs_plus(hands, base, all_hands_list)
            elif _is_suited_offsuit_str(base):
                # e.g. "A9s+" => A9s, A8s, A7s, ... A2s
                parse_suited_offsuit_plus(hands, base, all_hands_list)
            # else skip unrecognized
            continue

    return hands


def _normalize_card_notation(raw_card_str):
    """
    Ensures the last char is 's' or 'o' if present, and uppercase for ranks.
      e.g. "a2O" => "A2o",  "qJs" => "QJs"
      e.g. "qq" => "QQ"
    """
    raw_card_str = raw_card_str.strip()
    # If the last char is 's' or 'o', preserve that as lowercase, uppercase the rest
    if len(raw_card_str) >= 3 and raw_card_str[-1].lower() in ('s', 'o'):
        return raw_card_str[:-1].upper() + raw_card_str[-1].lower()
    else:
        return raw_card_str.upper()


def _is_pair_str(s):
    """Return True if s is exactly 2 chars and both ranks are same (e.g. '77','QQ')."""
    return len(s) == 2 and s[0] == s[1]


def _is_suited_offsuit_str(s):
    """Return True if s is 3 chars with last in ['s','o'], e.g. 'A2s', 'K9o'."""
    if len(s) == 3:
        return s[-1] in ('s', 'o')
    return False


def parse_dashed_pairs_range(hands_set, start_pair, end_pair, all_hands_list):
    """
    Expand something like "99-22" or "77-JJ".
      - E.g. start_pair='99' => first rank='9', end_pair='22' => rank='2'
    """
    try:
        start_idx = RANKS.index(start_pair[0])
        end_idx   = RANKS.index(end_pair[0])
        # If reversed, swap
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
        for i in range(start_idx, end_idx + 1):
            pair_str = f"{RANKS[i]}{RANKS[i]}"
            if pair_str in all_hands_list:
                hands_set.add(pair_str)
    except (ValueError, IndexError):
        pass


def parse_dashed_combo_range(hands_set, start_str, end_str, all_hands_list):
    """
    Expand dashed combos like "A2s-AKs", "K2o-KQo", "J4s-JTs".
    We'll assume the first char (the 'primary rank') is the same on both sides 
    or else we skip. Example:
      start_str="A2s" => 'A','2','s'
      end_str  ="AKs" => 'A','K','s'
    We'll expand from '2' up to 'K' for the second rank.

    For "J4s-JTs", we expand rank2 from '4' up to 'T' 
    (both remain 'J' as the first rank, and 's' for suited).

    If the first rank differs (like "A2s-KQs"), we ignore it or treat it as separate entries.
    """
    sr1, sr2, stype = start_str[0], start_str[1], start_str[2]   # e.g. 'A','2','s'
    er1, er2, etype = end_str[0], end_str[1], end_str[2]         # e.g. 'A','K','s'

    # Must be same 'primary rank' (or skip)
    if sr1 != er1 or stype != etype:
        return  # skip or handle differently

    try:
        start_idx = RANKS.index(sr2)
        end_idx   = RANKS.index(er2)
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
        for i in range(start_idx, end_idx + 1):
            candidate = f"{sr1}{RANKS[i]}{stype}"  # e.g. 'A2s', 'A3s', ... 'AKs'
            if candidate in all_hands_list:
                hands_set.add(candidate)
    except (ValueError, IndexError):
        pass


def parse_pairs_plus(hands_set, pair_str, all_hands_list):
    """
    e.g. "TT+" => TT, JJ, QQ, KK, AA
    """
    try:
        base_idx = RANKS.index(pair_str[0])  # 'T'
        for i in range(base_idx, -1, -1):    # down to 'A'
            candidate = f"{RANKS[i]}{RANKS[i]}"
            if candidate in all_hands_list:
                hands_set.add(candidate)
    except (ValueError, IndexError):
        pass


def parse_suited_offsuit_plus(hands_set, base_str, all_hands_list):
    """
    e.g. "A9s+" => A9s, A8s, A7s, ... A2s
         "A2o+" => A2o, A3o, A4o, ... AKo  (descending ranks)
    base_str = 'A9s' => base_str[0]='A', base_str[1]='9', base_str[2]='s'
    We'll iterate from that second rank down to '2'.
    """
    rank1, rank2, ctype = base_str[0], base_str[1], base_str[2]  # e.g. 'A','9','s'
    try:
        idx_start = RANKS.index(rank2)
        idx_end   = len(RANKS) - 1  # '2' is last in RANKS
        for i in range(idx_start, idx_end + 1):
            candidate = f"{rank1}{RANKS[i]}{ctype}"
            if candidate in all_hands_list:
                hands_set.add(candidate)
    except (ValueError, IndexError):
        pass




# --- Modern Color Scheme ---
# Primary colors
PRIMARY_COLOR = "#4A6FA5"  # Deep blue
SECONDARY_COLOR = "#6B8CBE"  # Lighter blue
ACCENT_COLOR = "#FF7E5F"  # Coral accent

# Card type colors
DEFAULT_COLOR_PAIR = "#E76F51"  # Warm red
DEFAULT_COLOR_SUITED = "#2A9D8F"  # Teal
DEFAULT_COLOR_OFFSUIT = "#E9C46A"  # Gold
SELECTED_COLOR = "#4A6FA5"  # Primary blue

# Card suit colors
CARD_SPADE_COLOR = "#2B2D42"  # Dark slate
CARD_HEART_COLOR = "#D90429"  # Rich red 
CARD_DIAMOND_COLOR = "#4A6FA5"  # Primary blue
CARD_CLUB_COLOR = "#2A9D8F"  # Teal

# Backgrounds
CARD_RANK_BG = "#F8F9FA"  # Off-white
CARD_SUIT_BG = "#E9ECEF"  # Light gray
CARD_SELECTED_BG = "#E2EAF7"  # Light blue tint
CARD_DISPLAY_BG = "#FFFFFF"  # Pure white
APP_BG = "#F8F9FA"  # Off-white background

# Text colors
TEXT_PRIMARY = "#212529"  # Dark gray
TEXT_SECONDARY = "#495057"  # Medium gray

# Button styling
BUTTON_WIDTH = 42
BUTTON_HEIGHT = 32
BUTTON_CORNER_RADIUS = 6

# --- GraphicalCardSelector Class ---
class GraphicalCardSelector(ctk.CTkFrame):
    """A graphical card selector that displays ranks and suits as buttons."""
    def __init__(self, master, placeholder="Select a card", width=80, height=40, command=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.placeholder = placeholder
        self.command = command
        self.selected_card = None
        self.selecting_state = False
        self.selected_rank = None
        
        # Main display - improved styling
        self.display_frame = ctk.CTkFrame(
            self, 
            fg_color=CARD_DISPLAY_BG, 
            corner_radius=8,
            border_width=1,
            border_color="#DEE2E6"
        )
        self.display_frame.pack(side="top", fill="both", expand=True, padx=4, pady=4)
        
        self.display_label = ctk.CTkLabel(
            self.display_frame,
            text=placeholder,
            width=width,
            height=height,
            fg_color="transparent",
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=14)
        )
        self.display_label.pack(expand=True, fill="both")
        
        # Popup for rank/suit selection
        self.popup = None
        
        # Click on the display to start selection
        self.display_frame.bind("<Button-1>", self._show_selector)
        self.display_label.bind("<Button-1>", self._show_selector)
    
    def _show_selector(self, event=None):
        """Show the rank/suit selector popup."""
        if self.popup:
            self.popup.destroy()
        
        # Create modern popup window
        self.popup = ctk.CTkToplevel(self)
        self.popup.title("Select Card")
        self.popup.geometry("300x200")
        self.popup.resizable(False, False)
        self.popup.attributes("-topmost", True)
        self.popup.configure(fg_color=APP_BG)
        
        # Position popup centered below selector
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 150
        y = self.winfo_rooty() + self.winfo_height() + 5
        self.popup.geometry(f"+{x}+{y}")
        
        # Create frames with improved styling
        self.popup.grid_columnconfigure(0, weight=1)
        self.popup.grid_rowconfigure(0, weight=1)
        self.popup.grid_rowconfigure(1, weight=1)
        
        rank_frame = ctk.CTkFrame(self.popup, fg_color="transparent")
        rank_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nsew")
        
        suit_frame = ctk.CTkFrame(self.popup, fg_color="transparent")
        suit_frame.grid(row=1, column=0, padx=10, pady=(5,10), sticky="nsew")
        
        # Create rank buttons with improved styling
        rank_frame.grid_columnconfigure(tuple(range(13)), weight=1)
        rank_frame.grid_rowconfigure(0, weight=1)
        
        for i, rank in enumerate(RANKS):
            btn = ctk.CTkButton(
                rank_frame,
                text=rank,
                width=24,
                height=32,
                fg_color=CARD_RANK_BG,
                hover_color="#E2E6EA",
                text_color=TEXT_PRIMARY,
                font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
                corner_radius=BUTTON_CORNER_RADIUS,
                command=lambda r=rank: self._select_rank(r)
            )
            btn.grid(row=0, column=i, padx=2, pady=2)
        
        # Create suit buttons with improved styling
        suit_frame.grid_columnconfigure(tuple(range(4)), weight=1)
        suit_frame.grid_rowconfigure(0, weight=1)
        
        suits = [
            ("♠", "s", CARD_SPADE_COLOR),
            ("♥", "h", CARD_HEART_COLOR),
            ("♦", "d", CARD_DIAMOND_COLOR),
            ("♣", "c", CARD_CLUB_COLOR)
        ]
        
        for i, (symbol, code, color) in enumerate(suits):
            btn = ctk.CTkButton(
                suit_frame,
                text=symbol,
                width=64,
                height=44,
                fg_color=CARD_SUIT_BG,
                hover_color="#E2E6EA",
                text_color=color,
                font=ctk.CTkFont(family="Arial", size=18),
                corner_radius=BUTTON_CORNER_RADIUS,
                command=lambda c=code: self._select_suit(c)
            )
            btn.grid(row=0, column=i, padx=6, pady=6)
        
        # Clear button with improved styling
        clear_btn = ctk.CTkButton(
            self.popup,
            text="Clear Selection",
            width=80,
            height=28,
            fg_color="#E9ECEF",
            hover_color="#DEE2E6",
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="Arial", size=12),
            corner_radius=BUTTON_CORNER_RADIUS,
            command=self._clear_selection
        )
        clear_btn.grid(row=2, column=0, padx=10, pady=(0,10))
        
        self.selecting_state = False
        self.selected_rank = None
    
    def _select_rank(self, rank):
        """Handle rank selection."""
        self.selected_rank = rank
        self.selecting_state = True
    
    def _select_suit(self, suit):
        """Handle suit selection and complete the card selection."""
        if not self.selecting_state or self.selected_rank is None:
            return
        
        # Form the card string (e.g., "As")
        card = f"{self.selected_rank}{suit}"
        self.set_card(card)
        
        # Close the popup
        if self.popup:
            self.popup.destroy()
            self.popup = None
        
        # Call the callback if provided
        if self.command:
            self.command(card)
    
    def _clear_selection(self):
        """Clear the current selection."""
        self.selected_card = None
        self.display_label.configure(text=self.placeholder, text_color="gray")
        
        # Close the popup
        if self.popup:
            self.popup.destroy()
            self.popup = None
        
        # Call the callback if provided
        if self.command:
            self.command(None)
    
    def set_card(self, card):
        """Set the selected card programmatically."""
        if card is None:
            self._clear_selection()
            return
        
        self.selected_card = card
        
        # Determine text color based on suit
        suit = card[1].lower()
        if suit == 's':
            color = CARD_SPADE_COLOR
            symbol = "♠"
        elif suit == 'h':
            color = CARD_HEART_COLOR
            symbol = "♥"
        elif suit == 'd':
            color = CARD_DIAMOND_COLOR
            symbol = "♦"
        elif suit == 'c':
            color = CARD_CLUB_COLOR
            symbol = "♣"
        else:
            color = "black"
            symbol = ""
        
        # Update display
        self.display_label.configure(
            text=f"{card[0]}{symbol}",
            text_color=color
        )
    
    def get_card(self):
        """Get the currently selected card."""
        return self.selected_card

# --- GraphicalBoardSelector Class ---
class GraphicalBoardSelector(ctk.CTkFrame):
    """A board selector with graphical card selectors for flop, turn, and river."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure((1, 2, 3, 5, 7), weight=1)
        
        ctk.CTkLabel(self, text="Board Cards").grid(row=0, column=0, columnspan=8, pady=(5, 5), sticky="w")
        
        # Flop
        ctk.CTkLabel(self, text="Flop:").grid(row=1, column=0, padx=(5, 2), pady=2, sticky="w")
        self.flop1_selector = GraphicalCardSelector(self, placeholder="Card 1", width=45, height=30)
        self.flop1_selector.grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        self.flop2_selector = GraphicalCardSelector(self, placeholder="Card 2", width=45, height=30)
        self.flop2_selector.grid(row=1, column=2, padx=2, pady=2, sticky="ew")
        self.flop3_selector = GraphicalCardSelector(self, placeholder="Card 3", width=45, height=30)
        self.flop3_selector.grid(row=1, column=3, padx=2, pady=2, sticky="ew")
        
        # Turn
        ctk.CTkLabel(self, text="Turn:").grid(row=1, column=4, padx=(10, 2), pady=2, sticky="w")
        self.turn_selector = GraphicalCardSelector(self, placeholder="Card 4", width=45, height=30)
        self.turn_selector.grid(row=1, column=5, padx=2, pady=2, sticky="ew")
        
        # River
        ctk.CTkLabel(self, text="River:").grid(row=1, column=6, padx=(10, 2), pady=2, sticky="w")
        self.river_selector = GraphicalCardSelector(self, placeholder="Card 5", width=45, height=30)
        self.river_selector.grid(row=1, column=7, padx=5, pady=2, sticky="ew")
    
    def get_board_cards(self):
        """Returns the currently selected board cards."""
        cards = []
        for selector in [self.flop1_selector, self.flop2_selector, self.flop3_selector, 
                         self.turn_selector, self.river_selector]:
            card = selector.get_card()
            if card:
                cards.append(card)
        return cards
    
    def clear_board(self):
        """Clear all board cards."""
        for selector in [self.flop1_selector, self.flop2_selector, self.flop3_selector, 
                         self.turn_selector, self.river_selector]:
            selector.set_card(None)

# --- HandRangeSelector Class --- (Keep existing class)
# ... (no changes needed here for now) ...

class HandRangeSelector(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(tuple(range(13)), weight=1)
        self.grid_rowconfigure(tuple(range(13)), weight=1)

        self.hand_buttons = {} # Store buttons by hand string e.g., "AKs": button
        self.selected_hands = set() # Store selected hand strings e.g., {"AA", "KQs"}
        self.on_change_callback = None # Callback function when selection changes

        self._create_grid()

    def _create_grid(self):
        for r_idx, rank1 in enumerate(RANKS):
            for c_idx, rank2 in enumerate(RANKS):
                is_pair = (r_idx == c_idx)
                is_suited = (r_idx < c_idx)
                is_offsuit = (r_idx > c_idx)

                if is_pair:
                    hand_str = f"{rank1}{rank2}"
                    text_color = TEXT_PRIMARY
                    fg_color = DEFAULT_COLOR_PAIR
                elif is_suited:
                    hand_str = f"{rank1}{rank2}s"
                    text_color = "black"
                    fg_color = DEFAULT_COLOR_SUITED
                else: # is_offsuit
                    # Use standard notation (higher rank first)
                    hand_str = f"{rank2}{rank1}o"
                    text_color = "black"
                    fg_color = DEFAULT_COLOR_OFFSUIT

                # Determine correct grid position (pairs on diagonal, suited upper right, offsuit lower left)
                grid_row = r_idx
                grid_col = c_idx

                button = ctk.CTkButton(
                    self,
                    text=hand_str,
                    width=BUTTON_WIDTH,
                    height=BUTTON_HEIGHT,
                    fg_color=fg_color,
                    hover_color=SECONDARY_COLOR,
                    text_color=text_color,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    corner_radius=BUTTON_CORNER_RADIUS,
                    command=lambda hs=hand_str: self._toggle_hand(hs)
                )
                button.grid(row=grid_row, column=grid_col, padx=2, pady=2, sticky="nsew")
                self.hand_buttons[hand_str] = button

    def _toggle_hand(self, hand_str):
        button = self.hand_buttons[hand_str]
        if hand_str in self.selected_hands:
            self.selected_hands.remove(hand_str)
            # Restore default color based on type
            if len(hand_str) == 2: fg_color = DEFAULT_COLOR_PAIR
            elif hand_str.endswith('s'): fg_color = DEFAULT_COLOR_SUITED
            else: fg_color = DEFAULT_COLOR_OFFSUIT
            button.configure(fg_color=fg_color)
        else:
            self.selected_hands.add(hand_str)
            button.configure(fg_color=SELECTED_COLOR)

        # Notify parent/caller about the change
        if self.on_change_callback:
            self.on_change_callback(self.selected_hands)

    def get_selected_hands(self):
        return self.selected_hands

    def set_selection_change_callback(self, callback):
        self.on_change_callback = callback


# --- Board Input Frame --- (New Class)
class BoardInputFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure((1, 2, 3, 5, 7), weight=1) # Give entry fields space

        ctk.CTkLabel(self, text="Board Cards").grid(row=0, column=0, columnspan=8, pady=(5, 5), sticky="w")

        # Flop
        ctk.CTkLabel(self, text="Flop:").grid(row=1, column=0, padx=(5, 2), pady=2, sticky="w")
        self.flop1_entry = ctk.CTkEntry(self, placeholder_text="e.g., Ah", width=45)
        self.flop1_entry.grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        self.flop2_entry = ctk.CTkEntry(self, placeholder_text="Kd", width=45)
        self.flop2_entry.grid(row=1, column=2, padx=2, pady=2, sticky="ew")
        self.flop3_entry = ctk.CTkEntry(self, placeholder_text="Tc", width=45)
        self.flop3_entry.grid(row=1, column=3, padx=2, pady=2, sticky="ew")

        # Turn
        ctk.CTkLabel(self, text="Turn:").grid(row=1, column=4, padx=(10, 2), pady=2, sticky="w")
        self.turn_entry = ctk.CTkEntry(self, placeholder_text="7s", width=45)
        self.turn_entry.grid(row=1, column=5, padx=2, pady=2, sticky="ew")

        # River
        ctk.CTkLabel(self, text="River:").grid(row=1, column=6, padx=(10, 2), pady=2, sticky="w")
        self.river_entry = ctk.CTkEntry(self, placeholder_text="2d", width=45)
        self.river_entry.grid(row=1, column=7, padx=5, pady=2, sticky="ew")

        # Store card strings (we can add validation/parsing later)
        self.flop1_entry.bind("<KeyRelease>", self._update_board_state)
        self.flop2_entry.bind("<KeyRelease>", self._update_board_state)
        self.flop3_entry.bind("<KeyRelease>", self._update_board_state)
        self.turn_entry.bind("<KeyRelease>", self._update_board_state)
        self.river_entry.bind("<KeyRelease>", self._update_board_state)

        self.board = [] # List to store validated card strings ["Ah", "Kd", "Tc", "7s", "2d"]
        # TODO: Add callback mechanism if other parts need to react to board changes

    def _update_board_state(self, event=None):
        # Basic update - just stores text for now.
        # Later: add validation using parse_card_input and update self.board list
        # print(f"Board Input Changed: F1={self.flop1_entry.get()}, T={self.turn_entry.get()}, R={self.river_entry.get()}")
        # Example of how you *would* use validation (but not implemented fully yet)
        # f1 = parse_card_input(self.flop1_entry.get())
        # f2 = parse_card_input(self.flop2_entry.get())
        # ... etc ...
        # self.board = [c for c in [f1, f2, f3, t, r] if c is not None]
        pass # No action needed yet
        # TODO: Implement validation using parse_card_input and update self.board
        # TODO: Trigger callback if implemented

    def get_board_cards(self):
        """Returns the currently entered board cards as raw strings."""
        # In future, this would return the validated self.board list
        return [
            self.flop1_entry.get(),
            self.flop2_entry.get(),
            self.flop3_entry.get(),
            self.turn_entry.get(),
            self.river_entry.get()
        ]

# --- Individual Calculator Modules ---

class BaseCalculatorModule(ctk.CTkFrame):
    """Base class for calculator modules to handle common input parsing."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

    def _get_float_from_entry(self, entry_widget):
        """Safely converts entry text to float, returns None on failure."""
        try:
            val = float(entry_widget.get())
            return val
        except ValueError:
            return None

    def _get_int_from_entry(self, entry_widget):
        """Safely converts entry text to int, returns None on failure."""
        try:
            val = int(entry_widget.get())
            return val
        except ValueError:
            return None

class PotOddsModule(BaseCalculatorModule):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Pot Odds Calculator").grid(row=0, column=0, columnspan=3, pady=(10, 5), sticky="w")
        ctk.CTkLabel(self, text="Amount to Call:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.call_entry = ctk.CTkEntry(self, placeholder_text="e.g., 50")
        self.call_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.result_label = ctk.CTkLabel(self, text="Pot Odds: - %")
        self.result_label.grid(row=1, column=2, rowspan=2, padx=10, pady=2, sticky="w")
        ctk.CTkLabel(self, text="Pot Before Call:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.pot_entry = ctk.CTkEntry(self, placeholder_text="e.g., 150")
        self.pot_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        self.call_entry.bind("<KeyRelease>", self._calculate)
        self.pot_entry.bind("<KeyRelease>", self._calculate)
        self._calculate() # Initial calculation

    def _calculate(self, event=None):
        call = self._get_float_from_entry(self.call_entry)
        pot = self._get_float_from_entry(self.pot_entry)
        if call is not None and pot is not None:
            result = calculate_pot_odds(call, pot)
            if isinstance(result, (int, float)):
                self.result_label.configure(text=f"Pot Odds: {result:.2f}%")
            else:
                 self.result_label.configure(text=f"Pot Odds: {result}")
        else:
             self.result_label.configure(text="Pot Odds: - %")

class RequiredEquityModule(BaseCalculatorModule):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Required Equity Calculator").grid(row=0, column=0, columnspan=3, pady=(10, 5), sticky="w")
        ctk.CTkLabel(self, text="Amount to Call:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.call_entry = ctk.CTkEntry(self, placeholder_text="e.g., 36")
        self.call_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.result_label = ctk.CTkLabel(self, text="Req. Equity: - %")
        self.result_label.grid(row=1, column=2, rowspan=2, padx=10, pady=2, sticky="w")
        ctk.CTkLabel(self, text="Pot Before Call:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.pot_entry = ctk.CTkEntry(self, placeholder_text="e.g., 81")
        self.pot_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        self.call_entry.bind("<KeyRelease>", self._calculate)
        self.pot_entry.bind("<KeyRelease>", self._calculate)
        self._calculate()

    def _calculate(self, event=None):
        call = self._get_float_from_entry(self.call_entry)
        pot = self._get_float_from_entry(self.pot_entry)
        if call is not None and pot is not None:
            result = calculate_required_equity(call, pot)
            if isinstance(result, (int, float)):
                self.result_label.configure(text=f"Req. Equity: {result:.2f}%")
            else:
                 self.result_label.configure(text=f"Req. Equity: {result}")
        else:
             self.result_label.configure(text="Req. Equity: - %")

class OutsEquityModule(BaseCalculatorModule):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Outs to Equity (Rule 2/4)").grid(row=0, column=0, columnspan=3, pady=(10, 5), sticky="w")
        ctk.CTkLabel(self, text="Number of Outs:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.outs_entry = ctk.CTkEntry(self, placeholder_text="e.g., 9")
        self.outs_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.result_label = ctk.CTkLabel(self, text="Approx. Equity: - %")
        self.result_label.grid(row=1, column=2, rowspan=2, padx=10, pady=2, sticky="w")
        ctk.CTkLabel(self, text="Street:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.street_var = ctk.StringVar(value="Flop")
        self.street_menu = ctk.CTkOptionMenu(self, values=["Flop", "Turn"], variable=self.street_var, command=self._calculate)
        self.street_menu.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        self.outs_entry.bind("<KeyRelease>", self._calculate)
        self._calculate()

    def _calculate(self, event=None):
        outs = self._get_int_from_entry(self.outs_entry)
        street = self.street_var.get()
        if outs is not None:
            result = calculate_equity_from_outs(outs, street)
            if isinstance(result, (int, float)):
                # TODO: Later, adjust 'outs' based on board cards if available
                self.result_label.configure(text=f"Approx. Equity: {result:.1f}%")
            else:
                 self.result_label.configure(text=f"Approx. Equity: {result}")
        else:
            self.result_label.configure(text="Approx. Equity: - %")

class MdfModule(BaseCalculatorModule):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Minimum Defense Freq. (MDF)").grid(row=0, column=0, columnspan=3, pady=(10, 5), sticky="w")
        ctk.CTkLabel(self, text="Opponent Bet Size:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.bet_entry = ctk.CTkEntry(self, placeholder_text="e.g., 50")
        self.bet_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.result_label = ctk.CTkLabel(self, text="MDF: - %")
        self.result_label.grid(row=1, column=2, rowspan=2, padx=10, pady=2, sticky="w")
        ctk.CTkLabel(self, text="Pot Before Bet:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.pot_entry = ctk.CTkEntry(self, placeholder_text="e.g., 100")
        self.pot_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        self.bet_entry.bind("<KeyRelease>", self._calculate)
        self.pot_entry.bind("<KeyRelease>", self._calculate)
        self._calculate()

    def _calculate(self, event=None):
        bet = self._get_float_from_entry(self.bet_entry)
        pot = self._get_float_from_entry(self.pot_entry)
        if bet is not None and pot is not None:
            result = calculate_mdf(bet, pot)
            if isinstance(result, (int, float)):
                self.result_label.configure(text=f"MDF: {result:.2f}%")
            else:
                 self.result_label.configure(text=f"MDF: {result}")
        else:
            self.result_label.configure(text="MDF: - %")

class BluffBreakEvenModule(BaseCalculatorModule):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Bluff Break-Even %").grid(row=0, column=0, columnspan=3, pady=(10, 5), sticky="w")
        ctk.CTkLabel(self, text="Your Bet Size:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.bet_entry = ctk.CTkEntry(self, placeholder_text="e.g., 50")
        self.bet_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.result_label = ctk.CTkLabel(self, text="Break-Even: - %")
        self.result_label.grid(row=1, column=2, rowspan=2, padx=10, pady=2, sticky="w")
        ctk.CTkLabel(self, text="Pot Before Bet:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.pot_entry = ctk.CTkEntry(self, placeholder_text="e.g., 100")
        self.pot_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        self.bet_entry.bind("<KeyRelease>", self._calculate)
        self.pot_entry.bind("<KeyRelease>", self._calculate)
        self._calculate()

    def _calculate(self, event=None):
        bet = self._get_float_from_entry(self.bet_entry)
        pot = self._get_float_from_entry(self.pot_entry)
        if bet is not None and pot is not None:
            result = calculate_bluff_break_even(bet, pot)
            if isinstance(result, (int, float)):
                self.result_label.configure(text=f"Break-Even: {result:.2f}%")
            else:
                 self.result_label.configure(text=f"Break-Even: {result}")
        else:
            self.result_label.configure(text="Break-Even: - %")


# --- CalculatorFrame --- (Refactored to use modules)
class CalculatorsGridFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # Pot Odds Calculator
        self.pot_odds_module = PotOddsModule(self, corner_radius=10, border_width=1, border_color="#DEE2E6")
        self.pot_odds_module.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Required Equity Calculator
        self.req_equity_module = RequiredEquityModule(self, corner_radius=10, border_width=1, border_color="#DEE2E6")
        self.req_equity_module.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        # Outs Equity Calculator
        self.outs_equity_module = OutsEquityModule(self, corner_radius=10, border_width=1, border_color="#DEE2E6")
        self.outs_equity_module.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # MDF Calculator
        self.mdf_module = MdfModule(self, corner_radius=10, border_width=1, border_color="#DEE2E6")
        self.mdf_module.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        # Bluff Break-Even Calculator
        self.bbe_module = BluffBreakEvenModule(self, corner_radius=10, border_width=1, border_color="#DEE2E6")
        self.bbe_module.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

        # SPR Calculator
        self.spr_module = SprModule(self, corner_radius=10, border_width=1, border_color="#DEE2E6")
        self.spr_module.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")

        # Add more calculator modules here as needed

class SprModule(BaseCalculatorModule):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Stack-to-Pot Ratio (SPR)").grid(row=0, column=0, columnspan=3, pady=(10, 5), sticky="w")
        ctk.CTkLabel(self, text="Effective Stack:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.stack_entry = ctk.CTkEntry(self, placeholder_text="e.g., 200")
        self.stack_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.result_label = ctk.CTkLabel(self, text="SPR: -")
        self.result_label.grid(row=1, column=2, rowspan=2, padx=10, pady=2, sticky="w")
        ctk.CTkLabel(self, text="Pot Size (on flop):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.pot_entry = ctk.CTkEntry(self, placeholder_text="e.g., 50")
        self.pot_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        self.stack_entry.bind("<KeyRelease>", self._calculate)
        self.pot_entry.bind("<KeyRelease>", self._calculate)
        self._calculate()

    def _calculate(self, event=None):
        stack = self._get_float_from_entry(self.stack_entry)
        pot = self._get_float_from_entry(self.pot_entry)
        if stack is not None and pot is not None:
            result = calculate_spr(stack, pot)
            if isinstance(result, (int, float)):
                self.result_label.configure(text=f"SPR: {result:.2f}")
            else:
                 self.result_label.configure(text=f"SPR: {result}")
        else:
            self.result_label.configure(text="SPR: -")

# --- PostFlopFrame --- (New frame to hold post-flop tools)
class PostFlopFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        # Instantiate and grid post-flop modules
        self.spr_module = SprModule(self, fg_color="transparent")
        self.spr_module.grid(row=0, column=0, padx=5, pady=(0, 10), sticky="new")

        # Add more post-flop modules here later

class BetSizingModule(BaseCalculatorModule):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0) # Buttons column

        ctk.CTkLabel(self, text="Bet Sizing Helper").grid(row=0, column=0, columnspan=3, pady=(10, 5), sticky="w")
        
        ctk.CTkLabel(self, text="Pot Size:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.pot_entry = ctk.CTkEntry(self, placeholder_text="e.g., 100")
        self.pot_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        
        # Frame for preset buttons
        preset_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        preset_button_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        preset_button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Preset buttons
        presets = {"1/3 Pot": 1/3, "1/2 Pot": 0.5, "2/3 Pot": 2/3, "Pot": 1.0}
        col = 0
        for text, fraction in presets.items():
            btn = ctk.CTkButton(
                preset_button_frame,
                text=text,
                command=lambda f=fraction: self._apply_preset(f)
            )
            btn.grid(row=0, column=col, padx=2, pady=2, sticky="ew")
            col += 1
            
        # Custom fraction input
        ctk.CTkLabel(self, text="Custom Fraction:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.fraction_entry = ctk.CTkEntry(self, placeholder_text="e.g., 0.75")
        self.fraction_entry.grid(row=3, column=1, padx=5, pady=2, sticky="ew")
        
        # Result display
        self.result_label = ctk.CTkLabel(self, text="Bet Size: -")
        self.result_label.grid(row=1, column=2, rowspan=3, padx=10, pady=2, sticky="w")

        self.pot_entry.bind("<KeyRelease>", self._calculate)
        self.fraction_entry.bind("<KeyRelease>", self._calculate)
        self._calculate()

    def _apply_preset(self, fraction):
        """Apply a preset fraction and calculate."""
        self.fraction_entry.delete(0, "end")
        self.fraction_entry.insert(0, f"{fraction:.2f}") # Show fraction used
        self._calculate()

    def _calculate(self, event=None):
        pot = self._get_float_from_entry(self.pot_entry)
        fraction = self._get_float_from_entry(self.fraction_entry)
        
        if pot is not None and fraction is not None:
            result = calculate_bet_size(pot, fraction)
            if isinstance(result, (int, float)):
                self.result_label.configure(text=f"Bet Size: {result:.2f}")
            else:
                 self.result_label.configure(text=f"Bet Size: {result}")
        else:
            self.result_label.configure(text="Bet Size: -")


# --- PostFlopFrame --- (New frame to hold post-flop tools)
class PostFlopFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        # Instantiate and grid post-flop modules
        self.spr_module = SprModule(self, fg_color="transparent")
        self.spr_module.grid(row=0, column=0, padx=5, pady=(0, 10), sticky="new")
        
        self.bet_sizing_module = BetSizingModule(self, fg_color="transparent")
        self.bet_sizing_module.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="new")

        # Add more post-flop modules here later

class IcmModule(BaseCalculatorModule):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1) # Stacks column
        self.grid_columnconfigure(1, weight=1) # Payouts column
        self.grid_columnconfigure(2, weight=1) # Results column

        ctk.CTkLabel(self, text="ICM Calculator (Simplified)").grid(row=0, column=0, columnspan=3, pady=(10, 5), sticky="w")

        # Input Frame
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_columnconfigure(1, weight=1)

        # Stacks Input
        ctk.CTkLabel(input_frame, text="Chip Stacks (comma-separated):").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.stacks_entry = ctk.CTkEntry(input_frame, placeholder_text="e.g., 1000, 500, 200")
        self.stacks_entry.grid(row=1, column=0, padx=5, pady=2, sticky="ew")

        # Payouts Input
        ctk.CTkLabel(input_frame, text="Payouts (comma-separated):").grid(row=0, column=1, padx=5, pady=2, sticky="w")
        self.payouts_entry = ctk.CTkEntry(input_frame, placeholder_text="e.g., 100, 60, 40")
        self.payouts_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        # Calculate Button
        self.calculate_button = ctk.CTkButton(self, text="Calculate ICM Equity", command=self._calculate)
        self.calculate_button.grid(row=2, column=0, columnspan=3, padx=5, pady=10, sticky="ew")

        # Results Frame (Scrollable)
        ctk.CTkLabel(self, text="Results ($EV):").grid(row=3, column=0, columnspan=3, padx=5, pady=(5, 0), sticky="w")
        self.results_frame = ctk.CTkScrollableFrame(self, label_text="")
        self.results_frame.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.result_labels = [] # To store labels for each player

        # Bind KeyRelease to recalculate automatically (optional)
        # self.stacks_entry.bind("<KeyRelease>", self._calculate)
        # self.payouts_entry.bind("<KeyRelease>", self._calculate)

    def _parse_entry(self, entry_widget):
        """Parses comma-separated numbers from an entry widget."""
        try:
            values = [float(x.strip()) for x in entry_widget.get().split(',') if x.strip()]
            return values
        except ValueError:
            return None

    def _calculate(self, event=None):
        # Clear previous results
        for label in self.result_labels:
            label.destroy()
        self.result_labels = []

        stacks = self._parse_entry(self.stacks_entry)
        payouts = self._parse_entry(self.payouts_entry)

        if stacks is None or payouts is None:
            error_label = ctk.CTkLabel(self.results_frame, text="Invalid input format. Use comma-separated numbers.", text_color="red")
            error_label.grid(row=0, column=0, sticky="w")
            self.result_labels.append(error_label)
            return

        if len(payouts) < len(stacks):
             error_label = ctk.CTkLabel(self.results_frame, text="Error: Not enough payouts for the number of players.", text_color="red")
             error_label.grid(row=0, column=0, sticky="w")
             self.result_labels.append(error_label)
             return

        results = calculate_icm(stacks, payouts)

        for i, res in enumerate(results):
            if isinstance(res, str): # Handle error messages from logic
                text = f"Player {i+1} (Stack: {stacks[i]}): {res}"
                color = "red"
            else:
                text = f"Player {i+1} (Stack: {stacks[i]}): ${res:.2f}"
                color = TEXT_PRIMARY # Use primary text color for better visibility

            label = ctk.CTkLabel(self.results_frame, text=text, text_color=color)
            label.grid(row=i, column=0, padx=5, pady=2, sticky="w")
            self.result_labels.append(label)

# --- TournamentFrame --- (New frame to hold tournament tools)
class TournamentFrame(ctk.CTkScrollableFrame):
     def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        # Instantiate and grid tournament modules
        self.icm_module = IcmModule(self, fg_color="transparent")
        self.icm_module.grid(row=0, column=0, padx=5, pady=(0, 10), sticky="new")

        # Add Push/Fold calculator here later

class PushFoldModule(BaseCalculatorModule):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # Configure columns and rows for proper expansion
        self.grid_columnconfigure(0, weight=1) # Allow column 0 to expand
        self.grid_columnconfigure(1, weight=1) # Allow column 1 to expand (needed for columnspan=2 widgets)
        self.grid_rowconfigure(3, weight=1)    # Allow the HandRangeSelector row (row 3) to expand vertically

        ctk.CTkLabel(self, text="Push/Fold Advisor").grid(row=0, column=0, columnspan=2, pady=(10, 5), sticky="w")

        # Inputs Frame
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        input_frame.grid_columnconfigure((1, 3), weight=1)

        # Stack Input
        ctk.CTkLabel(input_frame, text="Stack (BB):").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.stack_entry = ctk.CTkEntry(input_frame, placeholder_text="e.g., 10")
        self.stack_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        # Position Input
        ctk.CTkLabel(input_frame, text="Position:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.position_var = ctk.StringVar(value="BTN")
        positions = ["UTG", "UTG+1", "MP", "LJ", "HJ", "CO", "BTN", "SB"]
        self.position_menu = ctk.CTkOptionMenu(input_frame, values=positions, variable=self.position_var)
        self.position_menu.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        # Players Left Input
        ctk.CTkLabel(input_frame, text="Players Left:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.players_entry = ctk.CTkEntry(input_frame, placeholder_text="e.g., 6")
        self.players_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        # Get Advice Button
        self.get_advice_button = ctk.CTkButton(self, text="Get Advice", command=self._get_advice)
        self.get_advice_button.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky="ew")

        self.range_selector = HandRangeSelector(self, fg_color="transparent")
        self.range_selector.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        self.info_label = ctk.CTkLabel(self, text="Select stack, position, and players to get push/fold range")
        self.info_label.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        self.copy_range_button = ctk.CTkButton(self, text="Copy Range", command=self._copy_range)
        self.copy_range_button.grid(row=5, column=0, columnspan=2, padx=5, pady=(5, 10), sticky="ew")

        self.stack_entry.bind("<KeyRelease>", self._get_advice)
        self.players_entry.bind("<KeyRelease>", self._get_advice)
        self.position_menu.configure(command=self._get_advice)

    def _get_advice(self, event=None, position=None):
        stack = self._get_float_from_entry(self.stack_entry)
        players = self._get_int_from_entry(self.players_entry)
        position = position or self.position_var.get()

        if stack is None or players is None:
            self.info_label.configure(text="Invalid number format.", text_color="red")
            for hand in list(self.range_selector.selected_hands):
                self.range_selector._toggle_hand(hand)
            return
        if players < 2:
             self.info_label.configure(text="Need at least 2 players.", text_color="red")
             for hand in list(self.range_selector.selected_hands):
                 self.range_selector._toggle_hand(hand)
             return

        recommendation, range_list = get_push_fold_advice(stack, position, players)
        
        # Clear previous selection
        for hand in list(self.range_selector.selected_hands):
            self.range_selector._toggle_hand(hand)
        
        # Select new range
        for hand in range_list:
            if hand in self.range_selector.hand_buttons:
                self.range_selector._toggle_hand(hand)
        
        combos = sum(get_hand_combos(hand) for hand in range_list)
        percentage = calculate_range_percentage(set(range_list))
        
        self.info_label.configure(
            text=f"{recommendation} ({combos} combos, {percentage:.1f}%)",
            text_color="white" # Use default text color
        )

    def _copy_range(self):
        """Copies the currently selected range in the grid to the clipboard."""
        selected_hands = self.range_selector.get_selected_hands()
        if not selected_hands:
            self.info_label.configure(text="No range selected to copy.", text_color="orange")
            return

        range_text = format_range_to_text(selected_hands)
        try:
            pyperclip.copy(range_text)
            self.info_label.configure(text=f"Range copied to clipboard ({len(selected_hands)} types).", text_color="green")
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            self.info_label.configure(text="Error copying range.", text_color="red")


# --- TournamentFrame --- (New frame to hold tournament tools)
class TournamentFrame(ctk.CTkScrollableFrame):
     def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        # Instantiate and grid tournament modules
        self.icm_module = IcmModule(self, fg_color="transparent")
        self.icm_module.grid(row=0, column=0, padx=5, pady=(0, 10), sticky="new")

        self.push_fold_module = PushFoldModule(self, fg_color="transparent")
        self.push_fold_module.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="new")

        # Add Push/Fold calculator here later

class HandStrengthModule(BaseCalculatorModule):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Hand Strength Evaluator").grid(row=0, column=0, columnspan=2, pady=(10, 5), sticky="w")

        # Hand Input (Graphical)
        hand_frame = ctk.CTkFrame(self, fg_color="transparent")
        hand_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        hand_frame.grid_columnconfigure((1, 2), weight=1)
        ctk.CTkLabel(hand_frame, text="Hand:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.hand1_selector = GraphicalCardSelector(hand_frame, placeholder="Card 1", width=45, height=30)
        self.hand1_selector.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        self.hand2_selector = GraphicalCardSelector(hand_frame, placeholder="Card 2", width=45, height=30)
        self.hand2_selector.grid(row=0, column=2, padx=2, pady=2, sticky="ew")

        # Board Input (Graphical)
        self.board_input = GraphicalBoardSelector(self, fg_color="transparent")
        self.board_input.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        # Evaluate Button
        self.evaluate_button = ctk.CTkButton(self, text="Evaluate Hand", command=self._evaluate)
        self.evaluate_button.grid(row=3, column=0, columnspan=2, padx=5, pady=10, sticky="ew")

        # Result Display
        self.result_label = ctk.CTkLabel(self, text="Result: -")
        self.result_label.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

    def _evaluate(self):
        hand_c1 = self.hand1_selector.get_card()
        hand_c2 = self.hand2_selector.get_card()
        board_cards = self.board_input.get_board_cards()

        if not hand_c1 or not hand_c2:
            self.result_label.configure(text="Result: Please select both hand cards.", text_color="red")
            return
        if len(board_cards) < 3:
             self.result_label.configure(text="Result: Please select at least 3 board cards.", text_color="red")
             return

        hand_list = [hand_c1, hand_c2]
        score, rank_str = get_hand_strength(hand_list, board_cards)

        if score is not None:
            self.result_label.configure(text=f"Result: {rank_str}", text_color="white")
        else:
            self.result_label.configure(text=f"Result: {rank_str}", text_color="red") # Display error message

# --- AnalysisFrame --- (New frame to hold analysis tools)
class AnalysisFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        # Instantiate and grid analysis modules
        self.hand_strength_module = HandStrengthModule(self, fg_color="transparent")
        self.hand_strength_module.grid(row=0, column=0, padx=5, pady=(0, 10), sticky="new")

        # Add Range Analyzer module here later

# --- Hand vs Range Equity Tab ---
class HandVsRangeFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1) # Left column (Inputs/Results)
        self.grid_columnconfigure(1, weight=1) # Right column (Range Selector)
        self.grid_rowconfigure(2, weight=1)    # Range selector row expands

        # --- Hero Hand Input (Graphical) ---
        hero_frame = ctk.CTkFrame(self, fg_color="transparent")
        hero_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        hero_frame.grid_columnconfigure((1, 2), weight=1)
        
        ctk.CTkLabel(hero_frame, text="Hero Hand:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.hero_card1_selector = GraphicalCardSelector(hero_frame, placeholder="Card 1", width=45, height=30)
        self.hero_card1_selector.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        self.hero_card2_selector = GraphicalCardSelector(hero_frame, placeholder="Card 2", width=45, height=30)
        self.hero_card2_selector.grid(row=0, column=2, padx=2, pady=2, sticky="ew")

        # --- Board Input (Graphical) ---
        self.board_input_frame = GraphicalBoardSelector(self, fg_color="transparent")
        self.board_input_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        # --- Villain Range Selector ---
        villain_range_frame = ctk.CTkFrame(self, fg_color="transparent")
        villain_range_frame.grid(row=0, column=1, rowspan=3, padx=10, pady=10, sticky="nsew") # Span rows
        villain_range_frame.grid_columnconfigure(0, weight=1)
        villain_range_frame.grid_rowconfigure(1, weight=1) # Grid takes most space

        # Range header with presets
        range_header = ctk.CTkFrame(villain_range_frame, fg_color="transparent")
        range_header.grid(row=0, column=0, padx=5, pady=(0,2), sticky="ew")
        range_header.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(range_header, text="Villain Range:").grid(row=0, column=0, padx=0, pady=0, sticky="w")
        
        # Presets dropdown
        preset_frame = ctk.CTkFrame(range_header, fg_color="transparent")
        preset_frame.grid(row=0, column=1, padx=0, pady=0, sticky="e")
        
        ctk.CTkLabel(preset_frame, text="Presets:").pack(side="left", padx=(0, 5))
        self.preset_var = ctk.StringVar(value="Custom")
        self.preset_menu = ctk.CTkOptionMenu(
            preset_frame, 
            values=["Custom", "Top 5%", "Top 10%", "Top 20%", "Top 30%", "Top 40%", "Pairs", "Broadways", "Suited Connectors"],
            variable=self.preset_var,
            command=self._apply_preset,
            width=120
        )
        self.preset_menu.pack(side="left")
        
        # Range selector
        # Range selector
        self.villain_range_selector = HandRangeSelector(villain_range_frame)
        self.villain_range_selector.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # Range Info and Import/Export Frame
        range_io_frame = ctk.CTkFrame(villain_range_frame, fg_color="transparent")
        range_io_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        range_io_frame.grid_columnconfigure(0, weight=1) # Text entry takes space
        
        self.villain_range_info_label = ctk.CTkLabel(range_io_frame, text="Selected: 0 combos (0.00%)")
        self.villain_range_info_label.grid(row=0, column=0, columnspan=2, padx=0, pady=(0, 5), sticky="ew")
        
        self.range_text_entry = ctk.CTkEntry(range_io_frame, placeholder_text="Paste range text (e.g., AA,KK,AQs+)...")
        self.range_text_entry.grid(row=1, column=0, padx=(0, 5), pady=2, sticky="ew")
        
        import_button = ctk.CTkButton(range_io_frame, text="Import", width=60, command=self._import_range)
        import_button.grid(row=1, column=1, padx=(0, 5), pady=2)
        
        copy_button = ctk.CTkButton(range_io_frame, text="Copy", width=60, command=self._copy_range)
        copy_button.grid(row=1, column=2, padx=0, pady=2)
        
        self.villain_range_selector.set_selection_change_callback(self._update_villain_range_info)

        # --- Action Buttons ---
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        self.clear_button = ctk.CTkButton(
            button_frame, 
            text="Clear All", 
            command=self._clear_all,
            fg_color="#E74C3C",  # Red color for clear button
            hover_color="#C0392B"  # Darker red on hover
        )
        self.clear_button.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="ew")
        
        self.calculate_button = ctk.CTkButton(
            button_frame, 
            text="Calculate Equity", 
            command=self._calculate_equity
        )
        self.calculate_button.grid(row=0, column=1, padx=(5, 0), pady=0, sticky="ew")

        # --- Results Display ---
        results_frame = ctk.CTkFrame(self, fg_color="transparent")
        results_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="nsew") # Span both columns
        results_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(results_frame, text="Equity Results:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="w")
        self.preflop_equity_label = ctk.CTkLabel(results_frame, text="Preflop: --.-- %")
        self.preflop_equity_label.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.flop_equity_label = ctk.CTkLabel(results_frame, text="Flop:    --.-- %")
        self.flop_equity_label.grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.turn_equity_label = ctk.CTkLabel(results_frame, text="Turn:    --.-- %")
        self.turn_equity_label.grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.river_equity_label = ctk.CTkLabel(results_frame, text="River:   --.-- %")
        self.river_equity_label.grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.status_label = ctk.CTkLabel(results_frame, text="", text_color="gray") # For errors or status
        self.status_label.grid(row=5, column=0, columnspan=2, padx=5, pady=(5,0), sticky="w")

        self._update_villain_range_info(set()) # Initialize range info

    # --- Range Preset Definitions ---
    def _get_preset_hands(self, preset_name):
        """Return a set of hands for the given preset."""
        if preset_name == "Top 5%":
            return {
                "AA", "KK", "QQ", "JJ", "TT", 
                "AKs", "AQs", "AKo"
            }
        elif preset_name == "Top 10%":
            return {
                "AA", "KK", "QQ", "JJ", "TT", "99", 
                "AKs", "AQs", "AJs", "ATs", "KQs", 
                "AKo", "AQo"
            }
        elif preset_name == "Top 20%":
            return {
                "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", 
                "AKs", "AQs", "AJs", "ATs", "KQs", "KJs", "KTs", "QJs", "QTs", "JTs", 
                "AKo", "AQo", "AJo", "KQo"
            }
        elif preset_name == "Top 30%":
            return {
                "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55",
                "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
                "KQs", "KJs", "KTs", "K9s", "QJs", "QTs", "JTs", "T9s", "98s", "87s", "76s",
                "AKo", "AQo", "AJo", "ATo", "KQo", "KJo", "QJo"
            }
        elif preset_name == "Top 40%":
            return {
                "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
                "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
                "KQs", "KJs", "KTs", "K9s", "K8s", "K7s", "K6s", "QJs", "QTs", "Q9s", "JTs", "J9s",
                "T9s", "98s", "87s", "76s", "65s", "54s",
                "AKo", "AQo", "AJo", "ATo", "A9o", "KQo", "KJo", "KTo", "QJo", "QTo", "JTo"
            }
        elif preset_name == "Pairs":
            return {"AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22"}
        elif preset_name == "Broadways":
            return {
                "AKs", "AQs", "AJs", "ATs", "KQs", "KJs", "KTs", "QJs", "QTs", "JTs",
                "AKo", "AQo", "AJo", "ATo", "KQo", "KJo", "KTo", "QJo", "QTo", "JTo"
            }
        elif preset_name == "Suited Connectors":
            return {"JTs", "T9s", "98s", "87s", "76s", "65s", "54s", "43s", "32s"}
        else:  # Custom or unknown preset
            return set()
    
    def _apply_preset(self, preset_name):
        """Apply the selected preset to the range selector."""
        if preset_name == "Custom":
            return  # Don't change anything for custom
            
        # Get the hands for this preset
        preset_hands = self._get_preset_hands(preset_name)
        
        # First clear the current selection
        current_hands = list(self.villain_range_selector.selected_hands)
        for hand in current_hands:
            self.villain_range_selector._toggle_hand(hand)
            
        # Then select the preset hands
        for hand in preset_hands:
            if hand in self.villain_range_selector.hand_buttons:
                self.villain_range_selector._toggle_hand(hand)
        
        # Update the status label and clear text entry
        self.status_label.configure(text=f"Applied {preset_name} range preset", text_color="green")
        self.range_text_entry.delete(0, "end")
        
    def _import_range(self):
        """Import range from the text entry."""
        range_text = self.range_text_entry.get()
        if not range_text:
            self.status_label.configure(text="Error: Range text entry is empty.", text_color="red")
            return
            
        # Parse the text (using the basic parser for now)
        parsed_hands = parse_range_text(range_text)
        
        if not parsed_hands:
             self.status_label.configure(text="Error: Could not parse range text (basic parsing only).", text_color="red")
             return
             
        # Clear current selection
        current_hands = list(self.villain_range_selector.selected_hands)
        for hand in current_hands:
            self.villain_range_selector._toggle_hand(hand)
            
        # Select parsed hands
        imported_count = 0
        for hand in parsed_hands:
            if hand in self.villain_range_selector.hand_buttons:
                self.villain_range_selector._toggle_hand(hand)
                imported_count += 1
                
        self.status_label.configure(text=f"Imported {imported_count} hand types.", text_color="green")
        self.preset_var.set("Custom") # Imported range is custom
        
    def _copy_range(self):
        """Copy the current range selection to the clipboard as text."""
        selected_hands = self.villain_range_selector.get_selected_hands()
        if not selected_hands:
            self.status_label.configure(text="No range selected to copy.", text_color="orange")
            return
            
        range_text = format_range_to_text(selected_hands)
        
        # Copy to clipboard
        self.clipboard_clear()
        self.clipboard_append(range_text)
        self.update() # Required on some systems
        
        self.status_label.configure(text="Range copied to clipboard.", text_color="green")
        # Optionally display in the text entry
        self.range_text_entry.delete(0, "end")
        self.range_text_entry.insert(0, range_text)

    def _clear_all(self):
        """Clear all selections: hero hand, board, and villain range."""
        # Clear hero cards
        self.hero_card1_selector.set_card(None)
        self.hero_card2_selector.set_card(None)
        
        # Clear board cards
        self.board_input_frame.clear_board()
        
        # Clear villain range
        for hand in list(self.villain_range_selector.selected_hands):
            self.villain_range_selector._toggle_hand(hand)
        
        # Reset preset dropdown and text entry
        self.preset_var.set("Custom")
        self.range_text_entry.delete(0, "end")
        
        # Reset results
        self.preflop_equity_label.configure(text="Preflop: --.-- %")
        self.flop_equity_label.configure(text="Flop:    --.-- %")
        self.turn_equity_label.configure(text="Turn:    --.-- %")
        self.river_equity_label.configure(text="River:   --.-- %")
        self.status_label.configure(text="", text_color="gray")
    
    def _update_villain_range_info(self, selected_hands):
        """Callback function called by Villain's HandRangeSelector."""
        combos = sum(get_hand_combos(hand) for hand in selected_hands)
        percentage = calculate_range_percentage(selected_hands)
        self.villain_range_info_label.configure(text=f"Selected: {combos} combos ({percentage:.2f}%)")

    def _calculate_equity(self):
        """Get inputs, call logic function, display results."""
        self.status_label.configure(text="Calculating...", text_color="gray")
        self.preflop_equity_label.configure(text="Preflop: --.-- %")
        self.flop_equity_label.configure(text="Flop:    --.-- %")
        self.turn_equity_label.configure(text="Turn:    --.-- %")
        self.river_equity_label.configure(text="River:   --.-- %")
        self.update_idletasks() # Force UI update to show "Calculating..."

        hero_c1 = self.hero_card1_selector.get_card()
        hero_c2 = self.hero_card2_selector.get_card()
        
        # Check if both cards are selected
        if not hero_c1 or not hero_c2:
            self.status_label.configure(text="Error: Please select both hero cards", text_color="red")
            return
            
        hero_hand_str = hero_c1 + hero_c2 # Combine like "As" + "Kh" -> "AsKh"

        villain_range = list(self.villain_range_selector.get_selected_hands())
        board_cards_raw = self.board_input_frame.get_board_cards()
        # Filter out empty strings from board input
        board_cards = [card for card in board_cards_raw if card]

        # Basic Input Validation
        if len(hero_hand_str) != 4:
            self.status_label.configure(text="Error: Invalid Hero Hand format (e.g., AsKh)", text_color="red")
            return
        if not villain_range:
            self.status_label.configure(text="Error: Villain Range cannot be empty", text_color="red")
            return
        # Further validation happens within calculate_hand_vs_range_equity

        try:
            # Run calculation (can take time)
            equity_results = calculate_hand_vs_range_equity(hero_hand_str, villain_range, board_cards)

            if equity_results:
                pf = equity_results.get('preflop')
                fl = equity_results.get('flop')
                tn = equity_results.get('turn')
                rv = equity_results.get('river')

                self.preflop_equity_label.configure(text=f"Preflop: {pf:.2f} %" if pf is not None else "Preflop: N/A")
                self.flop_equity_label.configure(text=f"Flop:    {fl:.2f} %" if fl is not None else "Flop:    N/A")
                self.turn_equity_label.configure(text=f"Turn:    {tn:.2f} %" if tn is not None else "Turn:    N/A")
                self.river_equity_label.configure(text=f"River:   {rv:.2f} %" if rv is not None else "River:   N/A")
                self.status_label.configure(text="Calculation complete.", text_color="green")
            else:
                # Error message likely printed by logic function
                self.status_label.configure(text="Error during calculation. Check console.", text_color="red")

        except Exception as e:
            print(f"GUI Error during equity calculation: {e}")
            self.status_label.configure(text=f"Error: {e}", text_color="red")


# --- Main Application Class --- (MODIFIED to add new tab)
class PokerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Poker Tool v0.5") # Version bump for UI update
        self.geometry("850x750") # Slightly larger for better spacing
        self.configure(fg_color=APP_BG)

        # Configure main grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- REMOVED: Top Row Board Input ---
        # The redundant board input frame at the top of the app has been removed
        # Each tab that needs board input should have its own board input frame

        # Modernized tab view
        self.tab_view = ctk.CTkTabview(
            self,
            fg_color="transparent",
            segmented_button_selected_color=PRIMARY_COLOR,
            segmented_button_selected_hover_color=SECONDARY_COLOR,
            segmented_button_unselected_hover_color="#E9ECEF"
        )
        self.tab_view.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        # Add tabs in the desired order
        self.tab_view.add("Hand vs Range")
        self.tab_view.add("Push/Fold Advisor")
        self.tab_view.add("ICM Calculator")
        self.tab_view.add("Calculators")
        self.tab_view.add("Training")  # <-- Add new tab

        # --- Hand vs Range Tab ---
        hvrange_tab = self.tab_view.tab("Hand vs Range")
        self.hvrange_frame = HandVsRangeFrame(hvrange_tab, fg_color="transparent")
        self.hvrange_frame.pack(expand=True, fill="both")

        # --- Push/Fold Advisor Tab ---
        push_fold_tab = self.tab_view.tab("Push/Fold Advisor")
        self.push_fold_frame = PushFoldModule(push_fold_tab, fg_color="transparent")
        self.push_fold_frame.pack(expand=True, fill="both")

        # --- ICM Calculator Tab ---
        icm_tab = self.tab_view.tab("ICM Calculator")
        self.icm_frame = IcmModule(icm_tab, fg_color="transparent")
        self.icm_frame.pack(expand=True, fill="both")

        # --- Calculators Tab ---
        calculators_tab = self.tab_view.tab("Calculators")
        self.calculators_frame = CalculatorsGridFrame(calculators_tab, fg_color="transparent")
        self.calculators_frame.pack(expand=True, fill="both")

        # --- Training Tab ---
        training_tab = self.tab_view.tab("Training")
        self.training_frame = PushFoldTrainerFrame(training_tab, fg_color="transparent")
        self.training_frame.pack(expand=True, fill="both")

        # Remove the Hand Strength Evaluator from the Analysis tab
        # --- Analysis Tab ---
        # analysis_tab = self.tab_view.tab("Analysis")
        # self.analysis_frame = AnalysisFrame(analysis_tab, fg_color="transparent")
        # self.analysis_frame.pack(expand=True, fill="both")


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    # Use our custom color scheme instead of default theme
    app = PokerApp()
    # Set window icon if available
    try:
        app.iconbitmap("poker_icon.ico")  # Fallback if icon not found
    except:
        pass
    app.mainloop()
