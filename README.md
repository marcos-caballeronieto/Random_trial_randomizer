# Clinical Trial Randomization Engine

A production-grade, reproducible **Stratified Permuted Block Randomization (PBR) Engine** built in Python.

## 🎯 Overview

In clinical research, the internal validity of an experiment relies heavily on the elimination of selection bias. Simple randomization introduces severe risks of imbalance when dealing with small to moderate sample sizes. 

This tool mitigates selection bias by ensuring mathematical balance across critical prognostic covariates (such as Age and Biological Sex) between treatment and control arms. It guarantees mathematical balance while preserving the strict unpredictability required for true allocation concealment.

🚀 **Try the Live Interactive Demo:** [Experience the dashboard on Hugging Face Spaces](https://huggingface.co/spaces/marcoscaballero27/clinical-trial-randomizer)

## ✨ Core Features

* **Stratified Permuted Block Randomization:** Enforces a strict 1:1 allocation ratio using configurable block sizes. It uses deterministic execution via pseudorandom seeds (MT19937) for regulatory audit reproducibility.
* **Pre-Flight Strata Validation:** Includes a "Strata Starvation Gatekeeper" that evaluates patient density and alerts the user (or halts execution) if the sample size cannot support the selected stratification matrix.
* **Post-Allocation Balance Verification:** Automatically runs Welch's Independent T-Tests for continuous variables and Pearson's Chi-Square Tests for categorical variables to statistically verify cohort equilibrium.
* **Secure Double-Blind Exporting:** Generates two files upon completion:
    * `_audit.csv`: Contains raw data and allocations for statisticians and regulatory submissions.
    * `_blinded.csv`: Masks allocations using an irreversible SHA-256 cryptographic token to prevent premature unblinding by clinical staff.
* **Dual Interface:** Features both a terminal-based Command-Line Interface (CLI) for automated pipelines and a rich Streamlit web dashboard for interactive clinical use.

## ⚙️ Installation & Setup

1. Clone the repository.
2. Setup and run automatically using the **Windows Batch File** (`run.bat`), or install dependencies manually:
   ```bash
   pip install -r requirements.txt
   ```
   *Dependencies include: `numpy>=2.0.0`, `pandas>=2.0.0`, `scipy>=1.10.0`, `streamlit>=1.30.0`.*

## 🚀 Usage Guide

### ⚡ Windows Quick Start (Recommended)
You can run the application directly by double-clicking the `run.bat` script in the root directory, or by executing it from your terminal:
```cmd
run.bat
```
This batch script will automatically:
- Detect or create a virtual environment (`venv`).
- Install/update necessary dependencies if needed.
- Provide a menu to launch either the **Interactive Web UI (Streamlit)** or the **Command-Line Interface (CLI)**.

### 🍎 macOS & Linux Quick Start
You can run the interactive shell script `run.sh` from your terminal:
1. Make the script executable (only needed the first time):
   ```bash
   chmod +x run.sh
   ```
2. Run the script:
   ```bash
   ./run.sh
   ```
This shell script provides the exact same automated setup and interactive menu options as the Windows version.

### 🛠️ Manual Setup

#### 1. Interactive Web UI (Streamlit)
Launch the interactive dashboard to upload cohorts, select variables visually, generate synthetic patients, and view statistical balance charts.

```bash
streamlit run app.py
```

#### 2. Command-Line Interface (CLI)
Run the engine directly from your terminal. 

**Standard Baseline Stratification (Recommended Run):**
```bash
python main.py --input patients_raw.csv --output randomized_cohort.csv
```

**Custom Comorbidities & Block Size:**
```bash
python main.py --input patients_raw.csv --output randomized_cohort.csv --strata "Sex,Age_Group,Diabetes,Obesity" --block-size 6 --seed 12345
```

*CLI Flags:*
* `--input`: Path to the raw patient baseline CSV (Required)
* `--output`: Base path where randomized outputs will be exported (Required)
* `--strata`: Comma-separated list of column headers (Default: `"Sex,Age_Group"`)
* `--block-size`: Permuted block size to enforce parity (Default: `4`)
* `--seed`: Pseudorandom state seed for reproducible scientific audits (Default: `42`)
* `--salt`: Cryptographic salt string for SHA-256 hashing (Default: `"trial_salt_2026"`)
* `--force`: Bypass the pre-flight gatekeeper if Strata Starvation is detected.

## 🧬 Clinical & Mathematical Architecture

### Default Stratification
By default, the engine enforces stratification on two fundamental biological covariates: **Biological Sex** and **Age Groups**. Age must be binned (e.g., Young Adult, Middle Aged, Geriatric); the engine will automatically group raw continuous age values into categories to prevent infinite strata creation.

### Strata Starvation (Over-Stratification)
Investigators should only introduce optional variables (like Diabetes or Smoking Status) if they are established, independent prognostic indicators. Adding too many variables fragments the cohort into too many strata. If the average patient density per stratum drops below the block size, the mathematical integrity of the permuted blocks degrades to simple unblocked randomization. The built-in validation gatekeeper prevents this from failing silently.
