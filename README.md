# Poker Push/Fold Trainer

A Streamlit application for practicing poker tournament push/fold decisions. This trainer helps players improve their short-stack decision making by providing immediate feedback based on optimal push/fold ranges.

## Features

- Interactive push/fold decision training
- Visual card representation
- Immediate feedback on decisions
- Score tracking and performance review
- Comprehensive push/fold ranges for different stack sizes and positions

## Installation

1. Clone the repository:
```bash
git clone https://github.com/mhy196/pokertool.git
cd pokertool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running Locally

To run the application locally:
```bash
streamlit run trainer_app.py
```

## Deploying to Streamlit Cloud

1. Go to [Streamlit Cloud](https://streamlit.io/cloud)
2. Sign in with your GitHub account
3. Click "New app"
4. Select this repository (pokertool)
5. Select trainer_app.py as the main file
6. Click "Deploy"

## Project Structure

- `trainer_app.py`: Main Streamlit application
- `poker_logic.py`: Core game logic and calculations
- `push ranges.csv`: Data file containing push/fold ranges
- `assets/cards/`: Directory containing card images
- `requirements.txt`: Project dependencies

## Dependencies

- streamlit
- treys
- Pillow (PIL)
