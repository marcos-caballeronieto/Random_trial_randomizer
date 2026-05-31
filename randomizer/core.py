import pandas as pd
import numpy as np
import logging

def generate_block(block_size: int, rng: np.random.Generator) -> list:
    """
    Generates a single permuted block of size B containing equal allocations of 
    Treatment ('T') and Control ('C') arms.
    
    Raises:
        ValueError: If block_size is not even.
    """
    if block_size % 2 != 0:
        raise ValueError(f"Block size must be an even integer to maintain equal treatment allocation. Got: {block_size}")
        
    half_size = block_size // 2
    block = ['T'] * half_size + ['C'] * half_size
    # Shuffling using numpy's Generator.permutation
    return list(rng.permutation(block))

def allocate_stratum(n_patients: int, block_size: int, rng: np.random.Generator) -> list:
    """
    Generates a sequence of allocations for a specific stratum by concatenating 
    permuted blocks until all patients in the stratum are allocated, then slicing 
    to the exact length.
    """
    allocations = []
    while len(allocations) < n_patients:
        allocations.extend(generate_block(block_size, rng))
    return allocations[:n_patients]

def run_randomization(df: pd.DataFrame, strata_columns: list, block_size: int = 4, seed: int = 42) -> pd.DataFrame:
    """
    Performs stratified permuted block randomization on the input dataset.
    Appends the stratum composite keys and final treatment allocations to the dataframe, 
    preserving original patient row order.
    
    Raises:
        ValueError: If any stratification column is missing.
    """
    # 1. Input Validation
    missing_cols = set(strata_columns) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Selected stratification variable(s) not found in dataset: {list(missing_cols)}")
        
    # Prevent modifying input dataframe in-place
    df_result = df.copy()
    
    # 2. Establish deterministic pseudorandom state (decoupled from global random state)
    rng = np.random.default_rng(seed=seed)
    
    # 3. Construct composite key for stratification
    # E.g., 'Male_Middle Aged'
    df_result['stratum_key'] = df_result[strata_columns].astype(str).agg('_'.join, axis=1)
    
    # Cache the original order using a temporary index sequence
    df_result['original_order'] = np.arange(len(df_result))
    
    allocated_subgroups = []
    
    # 4. Allocation within each stratum
    for key, group in df_result.groupby('stratum_key'):
        group_copy = group.copy()
        n_group = len(group_copy)
        
        # Generate allocations for this subgroup size
        allocs = allocate_stratum(n_group, block_size, rng)
        group_copy['Allocation'] = allocs
        
        allocated_subgroups.append(group_copy)
        
    # 5. Reassemble and restore original sort order
    df_randomized = pd.concat(allocated_subgroups)
    df_randomized = df_randomized.sort_values('original_order').drop(columns=['original_order'])
    
    logging.info(f"Successfully allocated {len(df_randomized)} patients across {df_result['stratum_key'].nunique()} unique strata.")
    
    return df_randomized
