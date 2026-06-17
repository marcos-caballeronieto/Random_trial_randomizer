#!/bin/bash

# Clear screen and set title if possible
clear
printf "\033]0;Clinical Trial Randomizer Engine\007"

echo "===================================================================="
echo "🧬  CLINICAL TRIAL RANDOMIZER ENGINE"
echo "===================================================================="
echo

# Navigate to the script's directory
cd "$(dirname "$0")"

# Check for virtual environment folder
if [ ! -d "venv" ]; then
    echo "[WARNING] Virtual environment 'venv' not found in this folder."
    read -p "Would you like to automatically create 'venv' and install requirements? (Y/N): " CREATE_VENV
    if [[ "$CREATE_VENV" =~ ^[Yy]$ || "$CREATE_VENV" =~ ^[Yy][Ee][Ss]$ ]]; then
        echo
        echo "[INFO] Checking if python3 is installed..."
        if ! command -v python3 &> /dev/null; then
            echo "[ERROR] python3 was not found in your system PATH."
            echo "Please install Python 3 (3.9+) and try again."
            read -p "Press Enter to exit..."
            exit 1
        fi
        echo "[INFO] Creating virtual environment..."
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            echo "[ERROR] Failed to create virtual environment."
            read -p "Press Enter to exit..."
            exit 1
        fi
        echo "[INFO] Virtual environment created successfully."
        echo "[INFO] Activating virtual environment..."
        source venv/bin/activate
        echo "[INFO] Installing required dependencies..."
        python3 -m pip install --upgrade pip
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo "[ERROR] Failed to install dependencies."
            read -p "Press Enter to exit..."
            exit 1
        fi
        echo "[SUCCESS] Dependencies installed successfully."
        echo
        read -p "Press Enter to continue..."
    else
        echo "[INFO] Proceeding without virtual environment. Using system Python."
        echo
    fi
else
    echo "[INFO] Found virtual environment 'venv'. Activating..."
    source venv/bin/activate
    echo
fi

while true; do
    clear
    echo "===================================================================="
    echo "🧬  CLINICAL TRIAL RANDOMIZER ENGINE - MAIN MENU"
    echo "===================================================================="
    echo
    echo "  [1] Launch Interactive Web Dashboard (Streamlit UI)"
    echo "  [2] Execute Command Line Engine (CLI)"
    echo "  [3] Install/Update Python Dependencies"
    echo "  [4] Exit"
    echo
    echo "===================================================================="
    read -p "Enter choice (1-4): " CHOICE

    case "$CHOICE" in
        1)
            clear
            echo "===================================================================="
            echo "🧬  LAUNCHING INTERACTIVE WEB DASHBOARD (STREAMLIT UI)"
            echo "===================================================================="
            echo
            echo "Running 'streamlit run app.py'..."
            echo "Press Ctrl+C in this window to stop the dashboard server."
            echo
            streamlit run app.py
            echo
            echo "Dashboard stopped."
            read -p "Press Enter to return to menu..."
            ;;
        2)
            clear
            echo "===================================================================="
            echo "🧬  EXECUTE COMMAND LINE ENGINE (CLI)"
            echo "===================================================================="
            echo
            echo "Press ENTER to accept the default values in brackets."
            echo

            read -p "Input CSV file [patients_raw.csv]: " INPUT_FILE
            INPUT_FILE=${INPUT_FILE:-patients_raw.csv}

            read -p "Output CSV file [randomized_cohort.csv]: " OUTPUT_FILE
            OUTPUT_FILE=${OUTPUT_FILE:-randomized_cohort.csv}

            read -p "Stratification Covariates [Sex,Age_Group]: " STRATA_COLS
            STRATA_COLS=${STRATA_COLS:-Sex,Age_Group}

            read -p "Permuted Block Size [4]: " BLOCK_SIZE
            BLOCK_SIZE=${BLOCK_SIZE:-4}

            read -p "Random Seed [42]: " RANDOM_SEED
            RANDOM_SEED=${RANDOM_SEED:-42}

            echo
            echo "Running Engine CLI..."
            echo "python3 main.py --input \"$INPUT_FILE\" --output \"$OUTPUT_FILE\" --strata \"$STRATA_COLS\" --block-size $BLOCK_SIZE --seed $RANDOM_SEED"
            echo

            python3 main.py --input "$INPUT_FILE" --output "$OUTPUT_FILE" --strata "$STRATA_COLS" --block-size "$BLOCK_SIZE" --seed "$RANDOM_SEED"

            echo
            read -p "Press Enter to return to menu..."
            ;;
        3)
            clear
            echo "===================================================================="
            echo "🧬  UPDATING PYTHON DEPENDENCIES"
            echo "===================================================================="
            echo
            echo "Upgrading pip and running 'pip install -r requirements.txt'..."
            echo
            python3 -m pip install --upgrade pip
            pip install -r requirements.txt
            echo
            echo "Dependencies update complete."
            read -p "Press Enter to return to menu..."
            ;;
        4)
            echo
            echo "Goodbye!"
            exit 0
            ;;
        *)
            ;;
    esac
done
