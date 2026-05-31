# Project Roadmap: Clinical Trial Randomization Engine

**Status:** Active Development  
**Tech Stack:** Python (pandas, numpy, scipy, argparse, streamlit)

| Phase | Milestone | Core Tasks | Expected Output |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Data Simulation & Setup** | • Set up Python environment (`pandas`, `numpy`, `scipy`).<br>• Write a script to generate a synthetic patient dataset with diverse variables (Age, Sex, Comorbidities). | A `patients_raw.csv` file populated with 100-200 realistic, fake patient profiles for testing. |
| **Phase 2** | **Pre-Flight Validation** | • Code the data ingestion logic.<br>• Implement the *Strata Starvation* warning algorithm.<br>• Add age-binning logic (converting raw age to clinical categories). | A module that safely reads a CSV and approves or rejects the user's requested stratification variables based on sample size. |
| **Phase 3** | **The Randomization Core** | • Implement the deterministic seed logic (`np.random.default_rng`).<br>• Code the stratification grouping (composite keys).<br>• Program the Permuted Block sequence generator and assignment loop. | A dataframe where every patient has been assigned to "Control" or "Treatment" with strict mathematical balance. |
| **Phase 4** | **Statistical Verification** | • Write functions to run Pearson's Chi-Square tests on categorical variables (Sex, Diseases).<br>• Run an Independent T-Test on the continuous age variable.<br>• Generate a summary report to the console. | A printed validation report proving the groups are statistically identical (p > 0.05). |
| **Phase 5** | **Export & CLI Packaging** | • Export the final assigned dataframe to a new `randomized_cohort.csv`.<br>• Wrap the entire logic into a Command Line Interface (CLI) using `argparse` so it can be run from the terminal. | A fully functional, production-ready Python command-line tool. |
| **Phase 6** | **Interactive Web UI (Optional)** | • Integrate `streamlit` to build a user-friendly frontend.<br>• Create UI components for CSV file uploading and downloading.<br>• Add interactive checkboxes for clinicians to select stratification variables and input the deterministic seed.<br>• Visualize the statistical balance using simple bar charts or tables. | A local web application running via the browser, accessible to non-programmers. |

---

## Getting Started
Development will proceed sequentially. The first objective is to build a robust testing environment by generating a standardized mock clinical trial dataset (Phase 1) before building the stratification algorithms.