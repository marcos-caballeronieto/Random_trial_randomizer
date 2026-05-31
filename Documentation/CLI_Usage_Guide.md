# Clinical Trial Randomization Engine: CLI Usage Guide

This guide describes how to run and automate the **Clinical Trial Randomization Engine** from the terminal using the command-line interface.

---

## 1. CLI Reference & Flag Arguments

The command-line interface is triggered by running the `main.py` entrypoint. The tool requires an input cohort file and an output path.

### Syntactical Command Structure
```bash
python main.py --input <path_to_raw_csv> --output <path_to_export_csv> [optional_flags]
```

### Argument Flags Reference

| Flag | Type | Required | Default | Description |
| :--- | :---: | :---: | :---: | :--- |
| `--input` | String | **Yes** | — | Path to the raw, unrandomized patient baseline CSV (e.g. `patients_raw.csv`). |
| `--output` | String | **Yes** | — | Base path where randomized outputs will be exported. Files will automatically be split into `{output}_audit.csv` and `{output}_blinded.csv`. |
| `--strata` | String | No | `"Sex,Age_Group"` | Comma-separated list of column headers to stratify allocation on. **Defaults to baseline clinical standard (Sex & Age_Group)**. |
| `--block-size` | Integer | No | `4` | Permuted block size ($B$) to enforce treatment/control parity (must be an even integer). |
| `--seed` | Integer | No | `42` | Pseudorandom state seed. Vital for scientific audits to enable identical reruns of the random allocation stream. |
| `--salt` | String | No | `"trial_salt_2026"` | Custom salt string used to generate irreversibly hashed unblinding tokens for clinical staff. |
| `--force` | Flag | No | — | Bypasses the pre-flight gatekeeper if Strata Starvation is detected and forces the engine to execute the allocation loop. |

---

## 2. Command Examples & Scenarios

### Scenario A: Standard Baseline Stratification (Recommended Run)
To run a randomization sequence stratifying strictly on the clinical defaults (`Sex` and binned `Age_Group`) with block size 4 and seed 42:
```bash
python main.py --input patients_raw.csv --output randomized_cohort.csv
```
**Expected Output Files**:
- `randomized_cohort_audit.csv` (Full dataset with allocation keys)
- `randomized_cohort_blinded.csv` (Blinded dataset with cryptographic tokens)

### Scenario B: Custom Comorbidities Stratification
To run a randomization sequence stratifying on `Sex`, `Age_Group`, and custom comorbidities like `Diabetes` and `Obesity`:
```bash
python main.py --input patients_raw.csv --output randomized_cohort.csv --strata "Sex,Age_Group,Diabetes,Obesity" --block-size 6 --seed 12345
```

### Scenario C: Starvation Override (Bypass Validation Gate)
If you attempt to stratify on too many variables relative to your sample size, the **Strata Starvation Gatekeeper** will halt the execution:
```bash
python main.py --input patients_raw.csv --output randomized_cohort.csv --strata "Sex,Age_Group,Diabetes,Obesity,Smoking,Cancer,Cancer_Stage"
```
*Console error response:*
> `Randomization cancelled due to Strata Starvation risks. Use --force to proceed anyway.`

To bypass this check and force allocation (acknowledging that mathematical 1:1 parity cannot be guaranteed in rare strata):
```bash
python main.py --input patients_raw.csv --output randomized_cohort.csv --strata "Sex,Age_Group,Diabetes,Obesity,Smoking,Cancer,Cancer_Stage" --force
```

---

## 3. Interpreting Terminal Reports

Upon running, the engine outputs two audits directly to the console:

### Part 1: Pre-Flight Strata Validation
The engine calculates density metrics before randomizing:
```text
============================================================
CLINICAL TRIAL RANDOMIZATION ENGINE - PRE-FLIGHT VALIDATION
============================================================
Total Enrolled Patients (N): 150
Selected Stratification Variables: ['Sex', 'Age_Group']
Theoretical Max Strata Combinations: 6
Active Strata Observed in Dataset (K): 6
Configured Block Size (B): 4
Average Patient Density per Stratum: 25.00
------------------------------------------------------------
VALIDATION SUCCESSFUL: Stratification matrix is structurally sound and balanced.
============================================================
```
- **Average Patient Density**: If this is $\ge 1.5 \times B$, the matrix is safe. If it is $< B$, execution will halt (unless `--force` is specified).

### Part 2: Post-Allocation Cohort Balance Audit
To verify that demographic parity was achieved between the Treatment ('T') and Control ('C') arms, the CLI runs hypothesis testing:
```text
===========================================================================
                POST-ALLOCATION COHORT BALANCE AUDIT REPORT
===========================================================================

--- Continuous Variables (Welch's Independent T-Test) ---
Variable        | Mean (T)   | Mean (C)   | T-Stat     | p-value    | Status    
---------------------------------------------------------------------------
Age             | 58.62      | 58.74      | -0.0520    | 0.9587     | BALANCED  
BMI             | 27.53      | 27.24      |  0.3705    | 0.7115     | BALANCED  

--- Categorical Variables (Pearson's Chi-Square Test) ---
Variable        | Chi2       | p-value    | Status    
-------------------------------------------------------
Sex             | 0.1105     | 0.7396     | BALANCED  
Diabetes        | 0.0000     | 1.0000     | BALANCED  
Smoking         | 0.5487     | 0.7601     | BALANCED  
Obesity         | 0.1293     | 0.7192     | BALANCED  
===========================================================================
Note: p-value > 0.05 indicates no statistically significant difference between arms.
===========================================================================
```
- **Status (BALANCED / IMBALANCED)**: The null hypothesis states there is no difference in distributions between groups. Therefore, a **high p-value ($p > 0.05$)** indicates successful balance (no significant differences), rendering the cohort balanced.

---

## 4. Understanding Output Files

The tool generates two CSV files to secure double-blind protocols:

### 1. Blinded clinical dataset (`_blinded.csv`)
Distribute this file to the clinics, recruiters, and investigators. It strips out the raw `Allocation` ('T'/'C') column and `stratum_key`, replacing them with an alphanumeric cryptographic token (e.g. `1FEA38B29C0D`). This prevents selection bias during patient care.

### 2. Audit trail dataset (`_audit.csv`)
Retain this file strictly for statisticians and regulatory submissions. It contains the raw `Allocation` ('T' or 'C') alongside the composite `stratum_key` and cryptographic tokens, enabling the study to be unblinded and verified upon completion.
