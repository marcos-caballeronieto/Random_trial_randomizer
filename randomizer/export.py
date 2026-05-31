import pandas as pd
import hashlib
import os
import logging

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def generate_allocation_token(patient_id: str, allocation: str, salt: str) -> str:
    """
    Generates a patient-specific, one-way cryptographically masked allocation token
    using SHA-256 to prevent premature unblinding by clinical staff.
    """
    message = f"{patient_id}:{allocation}:{salt}".encode('utf-8')
    # Generate SHA-256 and truncate to first 12 characters, uppercase
    return hashlib.sha256(message).hexdigest()[:12].upper()

def export_dataset(df: pd.DataFrame, base_path: str, salt: str = "trial_salt_2026", blind_dataset: bool = True) -> tuple[str, str]:
    """
    Exports the randomized patient cohort to disk.
    
    Generates two outputs:
    1. An audit-trail CSV containing raw allocations and strata keys (suffixed with '_audit').
    2. A blinded CSV replacing raw allocations with hashed tokens (suffixed with '_blinded').
    
    Raises:
        ValueError: If required columns ('Patient_ID', 'Allocation') are missing.
        IOError: If files cannot be written to disk.
    """
    # 1. Validation check for required columns
    required_cols = {'Patient_ID', 'Allocation'}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        logging.error(f"Export failed. Missing required columns: {missing_cols}")
        raise ValueError(f"Required columns for export missing: {list(missing_cols)}")
        
    df_export = df.copy()
    
    # 2. Append masked cryptographic allocation token
    df_export['Masked_Allocation_Token'] = df_export.apply(
        lambda row: generate_allocation_token(row['Patient_ID'], row['Allocation'], salt), axis=1
    )
    
    # 3. Resolve file naming
    directory = os.path.dirname(base_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        
    base, ext = os.path.splitext(base_path)
    if not ext:
        ext = ".csv"
        
    audit_filepath = f"{base}_audit{ext}"
    blind_filepath = f"{base}_blinded{ext}"
    
    # 4. Save Audit Dataset (Full Key)
    try:
        df_export.to_csv(audit_filepath, index=False)
        logging.info(f"Audit-trail dataset exported successfully: {audit_filepath}")
    except Exception as e:
        logging.error(f"Failed to write audit CSV to {audit_filepath}: {e}")
        raise IOError(f"Failed to export audit CSV: {e}")
        
    # 5. Save Blinded Dataset (Clinical Sites)
    if blind_dataset:
        try:
            # Strip allocation and stratum key columns to maintain blinding integrity
            cols_to_drop = ['Allocation', 'stratum_key']
            df_blinded = df_export.drop(columns=[col for col in cols_to_drop if col in df_export.columns])
            df_blinded.to_csv(blind_filepath, index=False)
            logging.info(f"Blinded clinical dataset exported successfully: {blind_filepath}")
        except Exception as e:
            logging.error(f"Failed to write blinded CSV to {blind_filepath}: {e}")
            raise IOError(f"Failed to export blinded CSV: {e}")
            
    return audit_filepath, blind_filepath
