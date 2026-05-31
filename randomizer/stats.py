import pandas as pd
import numpy as np
from scipy import stats
import logging

def verify_balance(df: pd.DataFrame, continuous_cols: list, categorical_cols: list, allocation_col: str = 'Allocation') -> dict:
    """
    Computes statistical tests to check if clinical characteristics are balanced
    between Treatment ('T') and Control ('C') arms.
    
    Returns:
        dict: A dictionary containing p-values, means, standard deviations, and test statistics.
    """
    report = {
        'continuous': {},
        'categorical': {}
    }
    
    # 1. Validation check for allocation column presence
    if allocation_col not in df.columns:
        logging.error(f"Allocation column '{allocation_col}' not found in dataframe.")
        raise ValueError(f"Missing allocation column: {allocation_col}")
        
    # Check if we have exactly two allocation groups to run t-tests/chi-square
    groups = df[allocation_col].dropna().unique()
    if len(groups) != 2:
        logging.warning(f"Statistical checks require exactly 2 groups. Found: {list(groups)}")
        return report
        
    df_t = df[df[allocation_col] == 'T']
    df_c = df[df[allocation_col] == 'C']
    
    # 2. Independent T-test on continuous variables (Welch's t-test)
    for col in continuous_cols:
        if col in df.columns:
            val_t = df_t[col].dropna()
            val_c = df_c[col].dropna()
            
            mean_t = val_t.mean() if len(val_t) > 0 else np.nan
            mean_c = val_c.mean() if len(val_c) > 0 else np.nan
            std_t = val_t.std() if len(val_t) > 1 else np.nan
            std_c = val_c.std() if len(val_c) > 1 else np.nan
            
            # Welch's T-test: equal_var=False (standard in clinical trials to prevent bias from unequal variances)
            if len(val_t) > 1 and len(val_c) > 1:
                t_stat, p_val = stats.ttest_ind(val_t, val_c, equal_var=False)
            else:
                t_stat, p_val = np.nan, np.nan
                
            report['continuous'][col] = {
                'mean_treatment': round(mean_t, 2) if not np.isnan(mean_t) else None,
                'mean_control': round(mean_c, 2) if not np.isnan(mean_c) else None,
                'std_treatment': round(std_t, 2) if not np.isnan(std_t) else None,
                'std_control': round(std_c, 2) if not np.isnan(std_c) else None,
                't_statistic': round(t_stat, 4) if not np.isnan(t_stat) else None,
                'p_value': round(p_val, 4) if not np.isnan(p_val) else None
            }

    # 3. Pearson's Chi-Square Test on categorical variables
    for col in categorical_cols:
        if col in df.columns:
            contingency_table = pd.crosstab(df[col], df[allocation_col])
            
            # Stable calculation: Chi-Square requires a non-zero contingency table size
            # and all elements > 0 to maintain distribution assumptions.
            if contingency_table.size > 1 and (contingency_table > 0).all(axis=None):
                chi2, p_val, dof, expected = stats.chi2_contingency(contingency_table)
            else:
                logging.warning(f"Skipped Chi-Square for '{col}': contains zero cells or invalid dimensions.")
                chi2, p_val = np.nan, np.nan
                
            counts = contingency_table.to_dict()
            
            report['categorical'][col] = {
                'counts': counts,
                'chi2_statistic': round(chi2, 4) if not np.isnan(chi2) else None,
                'p_value': round(p_val, 4) if not np.isnan(p_val) else None
            }
            
    return report

def print_balance_report(report: dict):
    """
    Pretty-prints the balance verification report to the console.
    """
    print("\n" + "="*75)
    print("                POST-ALLOCATION COHORT BALANCE AUDIT REPORT")
    print("="*75)
    
    print("\n--- Continuous Variables (Welch's Independent T-Test) ---")
    print(f"{'Variable':<15} | {'Mean (T)':<10} | {'Mean (C)':<10} | {'T-Stat':<10} | {'p-value':<10} | {'Status':<10}")
    print("-"*75)
    for col, metrics in report.get('continuous', {}).items():
        p_val = metrics['p_value']
        # p > 0.05 fails to reject H0, meaning groups are statistically identical (balanced)
        status = "BALANCED" if (p_val is not None and p_val > 0.05) else "IMBALANCED"
        p_str = f"{p_val:.4f}" if p_val is not None else "N/A"
        t_str = f"{metrics['t_statistic']:.4f}" if metrics['t_statistic'] is not None else "N/A"
        mean_t = f"{metrics['mean_treatment']:.2f}" if metrics['mean_treatment'] is not None else "N/A"
        mean_c = f"{metrics['mean_control']:.2f}" if metrics['mean_control'] is not None else "N/A"
        print(f"{col:<15} | {mean_t:<10} | {mean_c:<10} | {t_str:<10} | {p_str:<10} | {status:<10}")
        
    print("\n--- Categorical Variables (Pearson's Chi-Square Test) ---")
    print(f"{'Variable':<15} | {'Chi2':<10} | {'p-value':<10} | {'Status':<10}")
    print("-"*55)
    for col, metrics in report.get('categorical', {}).items():
        p_val = metrics['p_value']
        status = "BALANCED" if (p_val is not None and p_val > 0.05) else "IMBALANCED"
        p_str = f"{p_val:.4f}" if p_val is not None else "N/A"
        chi_str = f"{metrics['chi2_statistic']:.4f}" if metrics['chi2_statistic'] is not None else "N/A"
        print(f"{col:<15} | {chi_str:<10} | {p_str:<10} | {status:<10}")
    print("="*75)
    print("Note: p-value > 0.05 indicates no statistically significant difference between arms.")
    print("="*75 + "\n")
