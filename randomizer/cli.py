import argparse
import sys
import os
import logging
from randomizer.ingestion import load_and_preprocess, validate_stratification_matrix
from randomizer.core import run_randomization
from randomizer.stats import verify_balance, print_balance_report
from randomizer.export import export_dataset

def main():
    parser = argparse.ArgumentParser(
        description="Clinical Trial Randomization Engine - CLI allocation tool."
    )
    
    # Input / Output
    parser.add_argument("--input", required=True, help="Path to raw patient CSV (e.g. patients_raw.csv)")
    parser.add_argument("--output", required=True, help="Path where randomized CSVs will be saved (e.g. randomized_cohort.csv)")
    
    # Stratification Parameters (Defaults to Sex,Age_Group as baseline clinical stratification standard)
    parser.add_argument(
        "--strata", 
        default="Sex,Age_Group", 
        help="Comma-separated list of stratification columns (default: 'Sex,Age_Group')"
    )
    parser.add_argument("--block-size", type=int, default=4, help="Block size for PBR (must be even, default=4)")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed for audit reproducibility (default=42)")
    parser.add_argument("--salt", default="trial_salt_2026", help="Cryptographic salt for masking allocations (default='trial_salt_2026')")
    parser.add_argument("--force", action="store_true", help="Bypass critical strata starvation warning and proceed with allocation")

    args = parser.parse_args()
    
    # Parse stratification list
    strata_cols = [col.strip() for col in args.strata.split(",") if col.strip()]
    if not strata_cols:
        print("Error: You must specify at least one stratification variable.")
        sys.exit(1)
        
    if args.block_size % 2 != 0:
        print("Error: Block size must be an even integer (e.g., 2, 4, 6).")
        sys.exit(1)

    print("\nStarting clinical trial allocation sequence...")
    print(f"Loading input file: {args.input}")
    
    # 1. Ingestion & Preprocessing
    if not os.path.exists(args.input):
        print(f"Error: File '{args.input}' not found.")
        sys.exit(1)
        
    try:
        df = load_and_preprocess(args.input)
    except Exception as e:
        print(f"Error during data ingestion: {e}")
        sys.exit(1)
        
    # Check if selected strata columns are in the dataframe
    missing_strata = set(strata_cols) - set(df.columns)
    if missing_strata:
        print(f"Error: Stratification column(s) not found in dataset: {list(missing_strata)}")
        sys.exit(1)
        
    # 2. Pre-Flight Validation (Strata Starvation Gatekeeper)
    is_valid = validate_stratification_matrix(df, strata_cols, args.block_size)
    if not is_valid and not args.force:
        print("Randomization cancelled due to Strata Starvation risks. Use --force to proceed anyway.")
        sys.exit(1)
        
    # 3. Core Randomization
    try:
        df_randomized = run_randomization(df, strata_cols, args.block_size, args.seed)
    except Exception as e:
        print(f"Error during randomization allocation: {e}")
        sys.exit(1)
        
    # 4. Statistical Verification Parity
    continuous_candidates = ['Age', 'BMI']
    categorical_candidates = ['Sex', 'Smoking', 'Obesity', 'Diabetes', 'Cancer', 'Cancer_Stage']
    
    continuous_cols = [c for c in continuous_candidates if c in df_randomized.columns]
    categorical_cols = [c for c in categorical_candidates if c in df_randomized.columns]
    
    stats_report = verify_balance(df_randomized, continuous_cols, categorical_cols)
    print_balance_report(stats_report)
    
    # 5. Export Datasets
    try:
        audit_path, blind_path = export_dataset(df_randomized, args.output, args.salt, blind_dataset=True)
        print("\nExport completed successfully!")
        print(f"Audit Log (Full data):   {audit_path}")
        print(f"Blinded Cohort (Clinic):  {blind_path}")
    except Exception as e:
        print(f"Error exporting results: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
