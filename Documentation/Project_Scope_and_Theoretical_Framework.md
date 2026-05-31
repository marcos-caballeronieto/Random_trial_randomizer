# Clinical Trial Randomization Engine: Scope and Theoretical Framework

**Author:** Research Software Initiative  
**Status:** Pre-Project Proposal & Documentation  
**Target Language:** Python 3.x  

## 1. Project Scope & Objectives

### 1.1 Problem Statement
In clinical research, the internal validity of an experiment relies heavily on the elimination of selection bias. Simple randomization—akin to flipping a coin for each participant—introduces severe risks of imbalance when dealing with small to moderate sample sizes. For instance, an unequal distribution of confounding variables such as age, biological sex, BMI, or baseline disease severity between the control and treatment arms can severely confound the treatment effect, leading to Type I or Type II errors. 

To mitigate this, clinical trialists employ advanced allocation techniques. This project seeks to build a production-grade, reproducible, and verifiable **Stratified Permuted Block Randomization Engine** in Python. The tool will guarantee mathematical balance across critical covariates while preserving the strict unpredictability required for true allocation concealment.

### 1.2 Functional Requirements
The application must satisfy the following algorithmic and functional parameters:

* **Data Ingestion:** Seamless parsing of participant baseline characteristics from comma-separated values (CSV) format.
* **Covariate Binning:** Dynamic transformation of continuous variables (e.g., age) into categorical strata.
* **Deterministic Execution:** Integration of cryptographic or pseudo-random seed architectures to enable identical rerun capabilities for external regulatory auditing.
* **Statistical Verification Report:** Computational verification of post-allocation cohort equilibrium using independence testing (Chi-Square and independent T-tests).
* **Secure Export:** Generation of a modified CSV appended with encrypted/masked allocation strings to prevent premature unblinding by clinical staff.

## 2. Theoretical & Mathematical Foundations

### 2.1 The Mathematics of Stratification
Stratification partitions the entire sample space $\Omega$ into $K$ mutually exclusive and collectively exhaustive subsets called *strata* ($S_1, S_2, \dots, S_K$). If we select $m$ prognostic factors, where factor $i$ has $c_i$ distinct categorical levels, the total number of strata $K$ is defined by the product:

$$K = \prod_{i=1}^{m} c_i$$

For example, if we stratify by Sex (Male, Female), Age Group (18-39, 40-59, 60+), and Diabetic Status (Yes, No), the total number of distinct strata will be:

$$K = 2 \times 3 \times 2 = 12 \text{ unique strata}$$

Participants entering the trial are instantly funneled into their respective stratum based on their baseline vector. Randomization happens strictly *within* each stratum to prevent global imbalances.

### 2.2 Permuted Block Randomization (PBR) Mechanics
Pure randomization within a small stratum can still yield an imbalance (e.g., 8 patients assigned to Treatment and 2 to Control). To enforce a strict 1:1 ratio throughout the recruitment lifecycle, we introduce **Permuted Blocks**.

Let a block size be denoted as $B$. To maintain equal allocation between two groups (Control $C$ and Treatment $T$), $B$ must be an even integer multiple of the number of arms. For a block size of $B = 4$, each block must contain exactly 2 $C$ allocations and 2 $T$ allocations. The total number of unique permutations $P$ for a block of size $B$ with two equal groups is given by the binomial coefficient:

$$P = \frac{B!}{(B/2)! \times (B/2)!} = \frac{4!}{2! \times 2!} = 6 \text{ permutations}$$

| Permutation ID | Sequence Allocation Layout |
| :---: | :--- |
| **1** | Control, Control, Treatment, Treatment (C, C, T, T) |
| **2** | Control, Treatment, Control, Treatment (C, T, C, T) |
| **3** | Control, Treatment, Treatment, Control (C, T, T, C) |
| **4** | Treatment, Control, Control, Treatment (T, C, C, T) |
| **5** | Treatment, Control, Treatment, Control (T, C, T, C) |
| **6** | Treatment, Treatment, Control, Control (T, T, C, C) |

The engine will randomly select one of these six sequences whenever a new block is initiated within a specific stratum. This ensures that even if recruitment stops prematurely, the numerical discrepancy between treatment arms will never exceed $B/2$.

### 2.3 Determinism and Pseudorandom Number Generation (PRNG)
True randomness cannot be reproduced. In scientific audits, regulatory bodies (such as the FDA or EMA) must be capable of feeding the exact same dataset into the software and obtaining identical group mappings. 

We will achieve reproducibility by utilizing the **Mersenne Twister algorithm (MT19937)** natively embedded within Python's `numpy.random` infrastructure. By instantiating a localized pseudorandom state using a specific integer seed:

```python
import numpy as np
rng = np.random.default_rng(seed=424242)
```

The generated stream of permutations is entirely decoupled from the system's global state, establishing a highly secure and verifiable execution path.

### 2.4 Post-Allocation Balance Verification
To prove that our algorithm successfully eliminated selection bias, the engine will run real-time automated statistical checks:

* **Categorical Covariates (e.g., Sex, Comorbidities):** Evaluated via Pearson's Chi-Square Test for Independence. We test the null hypothesis (H0) that group assignment is independent of the covariate. A successful stratification should yield a high p-value (p > 0.05), showing no statistically significant difference in distribution.
* **Continuous Covariates (e.g., Raw Age):** Evaluated using a two-sample independent Student's t-test to ensure the mean values across both arms are statistically indistinguishable.

## 3. Preliminary Algorithmic Architecture
The code execution pathway will follow a modular paradigm:

1. **Data Standardization:** Read the CSV file via `pandas`, strip white spaces, and run an integrity check for missing values (NaN).
2. **Strata Mapping:** Append a composite key column combining categorical flags (e.g., `M_36-55_Diabetic_Yes`).
3. **Block-by-Block Allocation:** Group the master dataframe by the composite key, iterate over each subgroup, construct full permuted blocks matching the subgroup length, and assign the allocations.
4. **Export and Validation:** Run `scipy.stats` routines, output the statistical balance metrics directly to the console terminal, and save the randomized dataset into a timestamped file.