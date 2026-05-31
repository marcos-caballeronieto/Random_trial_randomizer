import pandas as pd
import numpy as np
import logging
import os

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def bin_age(age_series: pd.Series) -> pd.Series:
    """
    Transforms continuous Age values into discrete clinical categories:
    - Young Adult: < 40 (0 to 39.9)
    - Middle Aged: 40 - 65 (40.0 to 65.0)
    - Geriatric: > 65 (65.0+)
    """
    # Cut defines right-closed bins by default, so right=True handles <= boundary
    bins = [0, 39.9, 65.0, np.inf]
    labels = ['Young Adult', 'Middle Aged', 'Geriatric']
    return pd.cut(age_series, bins=bins, labels=labels, right=True)

def load_and_preprocess(filepath: str) -> pd.DataFrame:
    """
    Loads raw CSV patient cohort data, standardizes column headers and string values,
    verifies presence of critical variables (Patient_ID, Age, Sex), and bins Age.
    
    Raises:
        FileNotFoundError: If filepath does not point to a valid file.
        ValueError: If mandatory columns are missing or contain missing/invalid data.
    """
    if not os.path.exists(filepath):
        logging.error(f"Target dataset file not found at: {filepath}")
        raise FileNotFoundError(f"File not found: {filepath}")
        
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        logging.error(f"Failed to read CSV file {filepath}: {e}")
        raise ValueError(f"Failed to read CSV: {e}")
        
    # 1. Standardize column headers (strip whitespaces)
    df.columns = [col.strip() for col in df.columns]
    
    # 2. Check for presence of mandatory variables
    mandatory_cols = {'Patient_ID', 'Age', 'Sex'}
    missing_cols = mandatory_cols - set(df.columns)
    if missing_cols:
        logging.error(f"Data ingestion failed. Missing required columns: {missing_cols}")
        raise ValueError(f"Missing mandatory clinical variables: {list(missing_cols)}")
        
    # 3. Clean up categorical/text columns (strip trailing/leading whitespace)
    for col in df.select_dtypes(include=['object', 'category']).columns:
        df[col] = df[col].astype(str).str.strip()
        
    # 4. Check for null values in mandatory variables
    for col in mandatory_cols:
        if df[col].isnull().any():
            logging.error(f"Missing values (NaN) found in mandatory column: {col}")
            raise ValueError(f"Mandatory variable '{col}' cannot contain missing values.")
            
    # 5. Type checking and validation of Age
    if not pd.api.types.is_numeric_dtype(df['Age']):
        logging.error("Age column contains non-numeric values.")
        raise ValueError("Age column must contain numeric values only.")
        
    if (df['Age'] <= 0).any():
        logging.error("Age column contains zero or negative values.")
        raise ValueError("Age values must be strictly positive numbers.")
        
    # 6. Apply Age Binning
    df['Age_Group'] = bin_age(df['Age'])
    
    logging.info(f"Ingested {len(df)} patient profiles successfully from {filepath}.")
    return df

def validate_stratification_matrix(df: pd.DataFrame, strata_columns: list, block_size: int = 4) -> bool:
    """
    Evaluates the structural viability of the requested stratification variables to prevent
    Strata Starvation.
    
    Returns:
        bool: True if safe (or warnings only), False if critical starvation (density < block_size).
    """
    total_patients = len(df)
    
    # Check if the requested columns are present in the dataframe
    missing_strata = set(strata_columns) - set(df.columns)
    if missing_strata:
        logging.error(f"Selected stratification variables not present in data: {missing_strata}")
        raise ValueError(f"Stratification variables missing from dataset: {list(missing_strata)}")
        
    # Calculate observed combinations (active strata)
    # drop_duplicates gives unique active combinations in the dataset
    unique_strata_combinations = df[strata_columns].drop_duplicates()
    k_strata = len(unique_strata_combinations)
    
    # Calculate theoretical maximum combinations
    theoretical_k = 1
    for col in strata_columns:
        theoretical_k *= df[col].nunique()
        
    avg_patients_per_stratum = total_patients / k_strata
    
    print("\n" + "="*60)
    print("CLINICAL TRIAL RANDOMIZATION ENGINE - PRE-FLIGHT VALIDATION")
    print("="*60)
    print(f"Total Enrolled Patients (N): {total_patients}")
    print(f"Selected Stratification Variables: {strata_columns}")
    print(f"Theoretical Max Strata Combinations: {theoretical_k}")
    print(f"Active Strata Observed in Dataset (K): {k_strata}")
    print(f"Configured Block Size (B): {block_size}")
    print(f"Average Patient Density per Stratum: {avg_patients_per_stratum:.2f}")
    print("-"*60)
    
    # Evaluation Logic
    critical_threshold = block_size * 1.5
    
    if avg_patients_per_stratum < block_size:
        print("CRITICAL WARNING: STRATA STARVATION DETECTED!")
        print(f"The average patient density ({avg_patients_per_stratum:.2f}) is lower than the block size ({block_size}).")
        print("Mathematical balance CANNOT be guaranteed. The algorithm will degrade to simple randomization.")
        print("RECOMMENDATION: Reduce stratification variables or expand cohort sample size.")
        print("="*60 + "\n")
        return False
    elif avg_patients_per_stratum < critical_threshold:
        print("BORDERLINE WARNING: High risk of incomplete blocks at recruitment close.")
        print(f"Density ({avg_patients_per_stratum:.2f}) is close to minimum limits.")
        print("Proceed with caution. Minor imbalances may occur in rare strata.")
        print("="*60 + "\n")
        return True
    else:
        print("VALIDATION SUCCESSFUL: Stratification matrix is structurally sound and balanced.")
        print("="*60 + "\n")
        return True
