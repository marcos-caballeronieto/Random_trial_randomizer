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

def generate_synthetic_data(n_patients: int = 150, seed: int = 42) -> pd.DataFrame:
    """
    Generates a synthetic but realistic clinical trial dataset using statistical models.
    """
    rng = np.random.default_rng(seed=seed)
    
    # 1. Age and Biological Sex
    ages = 18 + 67 * rng.beta(a=3, b=2, size=n_patients)
    ages = np.round(ages, 1)
    
    sex_choices = ['Male', 'Female']
    sex = rng.choice(sex_choices, size=n_patients, p=[0.5, 0.5])
    
    # 2. Body Mass Index (BMI) and Obesity
    bmi_base_ln = rng.normal(loc=2.3, scale=0.3, size=n_patients)
    bmi_base = np.exp(bmi_base_ln) + 15
    
    age_effect = 0.1 * (ages - 18) - 0.0015 * (ages - 18)**2
    bmi = np.round(bmi_base + age_effect, 1)
    bmi = np.clip(bmi, 16.0, 65.0)
    obesity = np.where(bmi >= 30.0, 'Yes', 'No')
    
    # 3. Smoking Status
    smoking = []
    for i in range(n_patients):
        s = sex[i]
        a = ages[i]
        
        logit_never = 0.8
        logit_former = 0.2 + 0.02 * (a - 40) + (0.1 if s == 'Male' else -0.1)
        logit_current = -0.2 - 0.03 * (a - 40) + (0.2 if s == 'Male' else -0.2)
        
        logits = np.array([logit_never, logit_former, logit_current])
        probs = np.exp(logits) / np.sum(np.exp(logits))
        
        status = rng.choice(['Never', 'Former', 'Current'], p=probs)
        smoking.append(status)
    smoking = np.array(smoking)
    
    # 4. Diabetes
    z_diabetes = -4.0 + 0.04 * (ages - 40) + 0.15 * (bmi - 25)
    p_diabetes = 1 / (1 + np.exp(-z_diabetes))
    diabetes = rng.binomial(1, p_diabetes)
    diabetes = np.where(diabetes == 1, 'Yes', 'No')
    
    # 5. Cancer and Tumor Stage
    is_current = (smoking == 'Current').astype(int)
    is_former = (smoking == 'Former').astype(int)
    is_obese = (obesity == 'Yes').astype(int)
    
    z_cancer = -3.5 + 0.06 * (ages - 45) + 1.2 * is_current + 0.6 * is_former + 0.5 * is_obese
    p_cancer = 1 / (1 + np.exp(-z_cancer))
    cancer_bin = rng.binomial(1, p_cancer)
    cancer = np.where(cancer_bin == 1, 'Yes', 'No')
    
    cancer_stage = []
    stage_choices = ['I', 'II', 'III', 'IV']
    stage_probs = [0.35, 0.30, 0.20, 0.15]
    for c in cancer_bin:
        if c == 1:
            cancer_stage.append(rng.choice(stage_choices, p=stage_probs))
        else:
            cancer_stage.append('None')
            
    # 6. Assembly
    patient_ids = [f"PAC-{i:03d}" for i in range(1, n_patients + 1)]
    
    df = pd.DataFrame({
        'Patient_ID': patient_ids,
        'Age': ages,
        'Sex': sex,
        'BMI': bmi,
        'Obesity': obesity,
        'Smoking': smoking,
        'Diabetes': diabetes,
        'Cancer': cancer,
        'Cancer_Stage': cancer_stage
    })
    
    return df

def load_and_preprocess(filepath_or_buffer) -> pd.DataFrame:
    """
    Loads raw CSV patient cohort data, standardizes column headers and string values,
    verifies presence of critical variables (Patient_ID, Age, Sex), and bins Age.
    
    Raises:
        FileNotFoundError: If filepath does not point to a valid file.
        ValueError: If mandatory columns are missing or contain missing/invalid data.
    """
    if isinstance(filepath_or_buffer, str):
        if not os.path.exists(filepath_or_buffer):
            logging.error(f"Target dataset file not found at: {filepath_or_buffer}")
            raise FileNotFoundError(f"File not found: {filepath_or_buffer}")
        
    try:
        df = pd.read_csv(filepath_or_buffer)
    except Exception as e:
        logging.error(f"Failed to read CSV source: {e}")
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
    
    logging.info(f"Ingested {len(df)} patient profiles successfully.")
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
