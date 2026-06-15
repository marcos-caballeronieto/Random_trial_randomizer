import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import altair as alt
from randomizer.ingestion import load_and_preprocess, generate_synthetic_data, validate_stratification_matrix
from randomizer.core import run_randomization
from randomizer.stats import verify_balance
from randomizer.export import generate_allocation_token

# Configure streamlit page
st.set_page_config(
    page_title="Clinical Trial Randomization Engine",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium design (responsive to both dark and light themes)
def inject_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
        
        /* Apply fonts */
        html, body, [class*="css"], .stMarkdown {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Outfit', sans-serif;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }
        
        /* Premium Header */
        .main-header {
            background: linear-gradient(135deg, #4f46e5 0%, #0d9488 100%);
            padding: 35px 25px;
            border-radius: 16px;
            color: white;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.15), 0 8px 10px -6px rgba(13, 148, 136, 0.1);
        }
        
        .main-header h1 {
            color: white !important;
            font-size: 2.5rem !important;
            margin: 0 0 10px 0 !important;
            padding: 0 !important;
        }
        
        .main-header p {
            font-size: 1.1rem;
            margin: 0;
            opacity: 0.95;
            font-weight: 300;
        }
        
        /* Cards */
        .dashboard-card {
            background-color: var(--background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            background-image: linear-gradient(rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0.02));
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }
        
        .dashboard-card h3 {
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 1.3rem;
            border-bottom: 1px solid rgba(128, 128, 128, 0.15);
            padding-bottom: 10px;
        }
        
        /* Custom Table Styling */
        .custom-table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 0.95rem;
        }
        
        .custom-table th {
            background-color: rgba(128, 128, 128, 0.1);
            text-align: left;
            padding: 10px 15px;
            font-weight: 600;
            border-bottom: 2px solid rgba(128, 128, 128, 0.2);
        }
        
        .custom-table td {
            padding: 10px 15px;
            border-bottom: 1px solid rgba(128, 128, 128, 0.1);
        }
        
        /* Badges */
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            text-align: center;
        }
        
        .badge-success {
            background-color: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        
        .badge-danger {
            background-color: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        .badge-warning {
            background-color: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }
        </style>
    """, unsafe_allow_html=True)

def main():
    inject_custom_css()
    
    # Render Main Header
    st.markdown("""
        <div class="main-header">
            <h1>🧬 Clinical Trial Randomization Engine</h1>
            <p>Stratified Permuted Block Randomization (PBR) and Statistical Balance Verification</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state variables
    if 'active_df' not in st.session_state:
        st.session_state.active_df = None
    if 'data_source_name' not in st.session_state:
        st.session_state.data_source_name = "None"
    if 'df_randomized' not in st.session_state:
        st.session_state.df_randomized = None
    if 'last_randomization_params' not in st.session_state:
        st.session_state.last_randomization_params = {}
        
    # --- SIDEBAR: COHORT DATA SOURCE SETUP ---
    st.sidebar.markdown("### 1. Data Ingestion")
    
    # Info note visible to user explaining demo/fallback behavior
    st.sidebar.info(
        "💡 **Notice:** If no custom CSV file is uploaded, the engine automatically defaults to using "
        "`patients_raw.csv`. You can also generate a fresh synthetic cohort below."
    )
    
    data_option = st.sidebar.radio(
        "Select Dataset Source:",
        ["📝 Use Default Cohort (patients_raw.csv)", "📁 Upload Custom CSV File", "🧬 Generate Synthetic Cohort"]
    )
    
    # Handle option 1: Default dataset
    if data_option == "📝 Use Default Cohort (patients_raw.csv)":
        default_path = "patients_raw.csv"
        if os.path.exists(default_path):
            try:
                st.session_state.active_df = load_and_preprocess(default_path)
                st.session_state.data_source_name = "Default Cohort (patients_raw.csv)"
            except Exception as e:
                st.sidebar.error(f"Error loading patients_raw.csv: {e}")
                st.session_state.active_df = None
        else:
            st.sidebar.warning("Default `patients_raw.csv` not found. Please upload a file or generate one.")
            st.session_state.active_df = None
            
    # Handle option 2: Custom CSV file upload
    elif data_option == "📁 Upload Custom CSV File":
        uploaded_file = st.sidebar.file_uploader("Upload Patient Cohort CSV", type=["csv"])
        if uploaded_file is not None:
            try:
                # Read buffer
                st.session_state.active_df = load_and_preprocess(uploaded_file)
                st.session_state.data_source_name = f"Uploaded File ({uploaded_file.name})"
            except Exception as e:
                st.sidebar.error(f"Ingestion failed: {e}")
                st.session_state.active_df = None
        else:
            # Fallback to default CSV if file uploader is empty
            default_path = "patients_raw.csv"
            if os.path.exists(default_path):
                try:
                    st.session_state.active_df = load_and_preprocess(default_path)
                    st.session_state.data_source_name = "Default Cohort (patients_raw.csv - Fallback)"
                except Exception as e:
                    st.session_state.active_df = None
            else:
                st.session_state.active_df = None
                
    # Handle option 3: Synthetic data generation
    elif data_option == "🧬 Generate Synthetic Cohort":
        st.sidebar.markdown("**Generator Configuration**")
        synth_n = st.sidebar.slider("Number of Patients (N):", min_value=50, max_value=500, value=150, step=10)
        synth_seed = st.sidebar.number_input("Generator Seed:", min_value=1, value=42)
        save_disk = st.sidebar.checkbox("Save generated cohort to disk (`patients_raw.csv`)", value=False)
        
        if st.sidebar.button("Generate & Load Synthetic Data", use_container_width=True):
            try:
                synth_df = generate_synthetic_data(n_patients=synth_n, seed=synth_seed)
                # Apply load_and_preprocess processing (e.g., bin age)
                # We can write to a buffer to let load_and_preprocess run, or apply it directly
                # Writing to StringIO buffer is cleanest
                csv_buffer = io.StringIO()
                synth_df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                
                st.session_state.active_df = load_and_preprocess(csv_buffer)
                st.session_state.data_source_name = f"Generated Synthetic Cohort (N={synth_n}, Seed={synth_seed})"
                st.sidebar.success("Synthetic dataset generated successfully!")
                
                if save_disk:
                    synth_df.to_csv("patients_raw.csv", index=False)
                    st.sidebar.info("Saved to `patients_raw.csv` at project root.")
            except Exception as e:
                st.sidebar.error(f"Failed to generate synthetic data: {e}")
                st.session_state.active_df = None
                
    # Check if we successfully loaded a dataframe
    if st.session_state.active_df is None:
        st.warning("⚠️ Please load or generate a patient dataset to begin.")
        return
        
    df = st.session_state.active_df
    
    # --- SIDEBAR: RANDOMIZATION PARAMETERS ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 2. Randomization Config")
    
    # Filter columns to list potential stratification variables
    # Exclude unique identifiers like Patient_ID
    potential_strata = [col for col in df.columns if col not in ['Patient_ID', 'Allocation', 'stratum_key', 'Masked_Allocation_Token']]
    
    # Default selection: Choose Sex and Age_Group if they exist
    default_selected = []
    if 'Sex' in potential_strata:
        default_selected.append('Sex')
    if 'Age_Group' in potential_strata:
        default_selected.append('Age_Group')
    if not default_selected and len(potential_strata) >= 2:
        default_selected = potential_strata[:2]
        
    strata_cols = st.sidebar.multiselect(
        "Stratification Covariates:",
        options=potential_strata,
        default=default_selected
    )
    
    block_size = st.sidebar.slider(
        "Permuted Block Size (B):",
        min_value=2,
        max_value=10,
        value=4,
        step=2,
        help="Must be an even integer to distribute assignments equally."
    )
    
    seed = st.sidebar.number_input(
        "Random Seed (for replication):",
        min_value=1,
        value=42
    )
    
    salt = st.sidebar.text_input(
        "Cryptographic Blinding Salt:",
        value="trial_salt_2026",
        help="Salt string for one-way SHA-256 allocation hashing."
    )
    
    force_randomization = st.sidebar.checkbox(
        "Force allocation (Bypass Strata Starvation warning)",
        value=False,
        help="Check this to force randomization if average density is less than the block size."
    )

    # --- MAIN VIEW LAYOUT ---
    
    # Display details of active cohort
    st.markdown(f"#### Active Dataset: `{st.session_state.data_source_name}`")
    
    # Create Tabs for layout
    tab_overview, tab_allocation, tab_audit, tab_viz = st.tabs([
        "📋 Cohort Overview & Pre-flight", 
        "⚡ Randomization Assignment", 
        "📊 Statistical Balance Audit", 
        "📈 Covariate Distribution Charts"
    ])
    
    # Tab 1: Cohort Overview & Pre-flight
    with tab_overview:
        col_summary1, col_summary2 = st.columns([1, 1])
        
        with col_summary1:
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            st.markdown("### 📋 Cohort Dataset Profile")
            st.write(f"**Total Records:** {len(df)} patients")
            st.write(f"**Available Attributes:** {', '.join(df.columns.tolist())}")
            st.dataframe(df.head(10), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_summary2:
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            st.markdown("### 🛡️ Pre-Flight Strata Validation")
            
            if not strata_cols:
                st.warning("⚠️ Please select at least one stratification variable to evaluate.")
            else:
                # Calculate validation metrics
                total_patients = len(df)
                unique_strata_combinations = df[strata_cols].drop_duplicates()
                k_strata = len(unique_strata_combinations)
                
                theoretical_k = 1
                for col in strata_cols:
                    theoretical_k *= df[col].nunique()
                    
                avg_patients_per_stratum = total_patients / k_strata if k_strata > 0 else 0
                
                st.write(f"**Selected Stratifiers:** {', '.join(strata_cols)}")
                st.write(f"**Observed Active Strata (K):** {k_strata}")
                st.write(f"**Theoretical Max Combinations:** {theoretical_k}")
                st.write(f"**Configured Block Size (B):** {block_size}")
                st.write(f"**Average Stratum Density:** `{avg_patients_per_stratum:.2f}` patients / stratum")
                
                st.markdown("#### Strata Density Evaluation:")
                critical_threshold = block_size * 1.5
                
                is_safe = True
                if avg_patients_per_stratum < block_size:
                    st.markdown(
                        f'<span class="badge badge-danger">CRITICAL WARNING</span> '
                        f'Average density ({avg_patients_per_stratum:.2f}) is lower than the block size ({block_size}).',
                        unsafe_allow_html=True
                    )
                    st.error(
                        "🚨 **Strata Starvation Risk!** There are too few patients per stratum combination. "
                        "Randomization will degrade to simple random allocation. It is highly recommended to "
                        "reduce the number of stratification variables or expand your cohort."
                    )
                    is_safe = False
                elif avg_patients_per_stratum < critical_threshold:
                    st.markdown(
                        f'<span class="badge badge-warning">BORDERLINE DENSITY</span> '
                        f'Density ({avg_patients_per_stratum:.2f}) is close to minimum limits.',
                        unsafe_allow_html=True
                    )
                    st.warning(
                        "⚠️ **Borderline Density.** Incomplete blocks at recruitment closure might cause "
                        "minor imbalances in rare strata. Proceed with caution."
                    )
                else:
                    st.markdown(
                        f'<span class="badge badge-success">VALIDATION SUCCESSFUL</span> '
                        f'Density ({avg_patients_per_stratum:.2f}) is robust.',
                        unsafe_allow_html=True
                    )
                    st.success("✅ **Stratification matrix is structurally sound and balanced!**")
            st.markdown('</div>', unsafe_allow_html=True)
            
    # Tab 2: Randomization Assignment
    with tab_allocation:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("### ⚙️ Execute Randomization")
        st.write("Clicking below will partition the cohort using stratified permuted block randomization.")
        
        # Determine button state based on pre-flight validation
        run_allowed = True
        if strata_cols:
            avg_patients_per_stratum = len(df) / len(df[strata_cols].drop_duplicates())
            if avg_patients_per_stratum < block_size and not force_randomization:
                run_allowed = False
                st.info("🔒 Randomization is locked due to Strata Starvation risks. Use the sidebar bypass check to proceed.")
                
        run_btn = st.button("🚀 Run Randomization Allocation", disabled=not run_allowed or not strata_cols, type="primary")
        
        if run_btn:
            with st.spinner("Executing sequence allocation..."):
                try:
                    df_randomized = run_randomization(
                        df=df,
                        strata_columns=strata_cols,
                        block_size=block_size,
                        seed=seed
                    )
                    st.session_state.df_randomized = df_randomized
                    st.session_state.last_randomization_params = {
                        'strata': strata_cols,
                        'block_size': block_size,
                        'seed': seed,
                        'salt': salt
                    }
                    st.success("🎉 Randomization sequence completed successfully!")
                except Exception as e:
                    st.error(f"Randomization error: {e}")
                    
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Display results and downloads if generated
        if st.session_state.df_randomized is not None:
            df_rand = st.session_state.df_randomized
            last_params = st.session_state.last_randomization_params
            
            # Export dataframes in memory
            df_export = df_rand.copy()
            df_export['Masked_Allocation_Token'] = df_export.apply(
                lambda row: generate_allocation_token(row['Patient_ID'], row['Allocation'], last_params['salt']), axis=1
            )
            
            # Blinded dataset
            cols_to_drop = ['Allocation', 'stratum_key']
            df_blinded = df_export.drop(columns=[col for col in cols_to_drop if col in df_export.columns])
            blinded_csv = df_blinded.to_csv(index=False).encode('utf-8')
            
            # Audit dataset
            audit_csv = df_export.to_csv(index=False).encode('utf-8')
            
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    label="⬇️ Download Blinded Dataset (Clinicians)",
                    data=blinded_csv,
                    file_name="randomized_cohort_blinded.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.caption("Contains demographic variables and the masked cryptographic token. Hides raw allocation ('C'/'T') and stratum keys.")
                
            with col_dl2:
                st.download_button(
                    label="⬇️ Download Audit-Trail Dataset (Data Managers)",
                    data=audit_csv,
                    file_name="randomized_cohort_audit.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.caption("Contains all raw data, stratum composite keys, raw allocations ('C'/'T'), and masked tokens for audit reproducibility.")
                
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            st.markdown("### 🔍 Allocation Summary Metrics")
            
            # Show summary stats of the allocation
            n_tot = len(df_rand)
            n_treat = len(df_rand[df_rand['Allocation'] == 'T'])
            n_ctrl = len(df_rand[df_rand['Allocation'] == 'C'])
            bal_ratio = (n_treat / n_ctrl) if n_ctrl > 0 else 0
            
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.markdown(f'**Allocated Cohort (N)**<br><span class="metric-value">{n_tot}</span>', unsafe_allow_html=True)
            with col_m2:
                st.markdown(f'**Treatment Arm (T)**<br><span class="metric-value">{n_treat}</span>', unsafe_allow_html=True)
            with col_m3:
                st.markdown(f'**Control Arm (C)**<br><span class="metric-value">{n_ctrl}</span>', unsafe_allow_html=True)
            with col_m4:
                st.markdown(f'**Balance Ratio (T/C)**<br><span class="metric-value">{bal_ratio:.3f}</span>', unsafe_allow_html=True)
                
            st.markdown("### 📋 Randomized Dataset Preview")
            st.dataframe(df_export.head(15), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
    # Tab 3: Statistical Balance Audit
    with tab_audit:
        if st.session_state.df_randomized is None:
            st.info("ℹ️ Run the randomization assignment on Tab 2 to view statistical balance audits.")
        else:
            df_rand = st.session_state.df_randomized
            
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            st.markdown("### 📊 Statistical Verification Parity Report")
            st.write(
                "Welch's Independent T-Test is performed on continuous variables, and Pearson's Chi-Square Test "
                "is conducted on categorical covariates to verify balance. A p-value > 0.05 indicates no statistically "
                "significant difference between the Control and Treatment groups (i.e. successful balance)."
            )
            
            # Automatically classify continuous and categorical variables
            continuous_candidates = ['Age', 'BMI']
            categorical_candidates = ['Sex', 'Smoking', 'Obesity', 'Diabetes', 'Cancer', 'Cancer_Stage']
            
            # Check which exist in df
            continuous_cols = [c for c in continuous_candidates if c in df_rand.columns]
            categorical_cols = [c for c in categorical_candidates if c in df_rand.columns]
            
            # If not matching candidates, classify dynamically
            if not continuous_cols and not categorical_cols:
                for col in df_rand.columns:
                    if col in ['Patient_ID', 'Allocation', 'stratum_key', 'Masked_Allocation_Token']:
                        continue
                    if pd.api.types.is_numeric_dtype(df_rand[col]) and df_rand[col].nunique() > 10:
                        continuous_cols.append(col)
                    else:
                        categorical_cols.append(col)
            
            # Run test
            report = verify_balance(df_rand, continuous_cols, categorical_cols)
            
            # Render continuous table
            st.markdown("#### 📐 Continuous Covariates (Welch's Independent T-Test)")
            if not report.get('continuous'):
                st.write("*No continuous variables identified.*")
            else:
                html_table = """
                <table class="custom-table">
                    <thead>
                        <tr>
                            <th>Variable</th>
                            <th>Mean (Treatment)</th>
                            <th>Mean (Control)</th>
                            <th>T-Statistic</th>
                            <th>p-value</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for col, metrics in report['continuous'].items():
                    p_val = metrics['p_value']
                    p_str = f"{p_val:.4f}" if p_val is not None else "N/A"
                    t_str = f"{metrics['t_statistic']:.4f}" if metrics['t_statistic'] is not None else "N/A"
                    mean_t = f"{metrics['mean_treatment']:.2f}" if metrics['mean_treatment'] is not None else "N/A"
                    mean_c = f"{metrics['mean_control']:.2f}" if metrics['mean_control'] is not None else "N/A"
                    
                    if p_val is None:
                        badge = '<span class="badge badge-warning">N/A</span>'
                    elif p_val > 0.05:
                        badge = '<span class="badge badge-success">BALANCED</span>'
                    else:
                        badge = '<span class="badge badge-danger">IMBALANCED</span>'
                        
                    html_table += f"""
                        <tr>
                            <td><strong>{col}</strong></td>
                            <td>{mean_t}</td>
                            <td>{mean_c}</td>
                            <td>{t_str}</td>
                            <td>{p_str}</td>
                            <td>{badge}</td>
                        </tr>
                    """
                html_table += "</tbody></table>"
                st.markdown(html_table, unsafe_allow_html=True)
                
            # Render categorical table
            st.markdown("#### 📊 Categorical Covariates (Pearson's Chi-Square Test)")
            if not report.get('categorical'):
                st.write("*No categorical variables identified.*")
            else:
                html_table = """
                <table class="custom-table">
                    <thead>
                        <tr>
                            <th>Variable</th>
                            <th>Chi-Square Statistic</th>
                            <th>p-value</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for col, metrics in report['categorical'].items():
                    p_val = metrics['p_value']
                    p_str = f"{p_val:.4f}" if p_val is not None else "N/A"
                    chi_str = f"{metrics['chi2_statistic']:.4f}" if metrics['chi2_statistic'] is not None else "N/A"
                    
                    if p_val is None:
                        badge = '<span class="badge badge-warning">N/A</span>'
                    elif p_val > 0.05:
                        badge = '<span class="badge badge-success">BALANCED</span>'
                    else:
                        badge = '<span class="badge badge-danger">IMBALANCED</span>'
                        
                    html_table += f"""
                        <tr>
                            <td><strong>{col}</strong></td>
                            <td>{chi_str}</td>
                            <td>{p_str}</td>
                            <td>{badge}</td>
                        </tr>
                    """
                html_table += "</tbody></table>"
                st.markdown(html_table, unsafe_allow_html=True)
                
            st.markdown('</div>', unsafe_allow_html=True)
            
    # Tab 4: Visualizations
    with tab_viz:
        if st.session_state.df_randomized is None:
            st.info("ℹ️ Run the randomization assignment on Tab 2 to view balance charts.")
        else:
            df_rand = st.session_state.df_randomized
            
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            st.markdown("### 📊 Distribution of Covariates by Allocation Arm")
            
            # Select column to visualize
            plottable_cols = [c for c in df_rand.columns if c not in ['Patient_ID', 'Allocation', 'stratum_key', 'Masked_Allocation_Token']]
            
            selected_var = st.selectbox(
                "Select a variable to inspect:",
                options=plottable_cols
            )
            
            if selected_var:
                if pd.api.types.is_numeric_dtype(df_rand[selected_var]) and df_rand[selected_var].nunique() > 10:
                    # Continuous variable: Render side-by-side boxplots
                    st.markdown(f"#### Boxplot of `{selected_var}` per Treatment Arm")
                    
                    boxplot = alt.Chart(df_rand).mark_boxplot(extent='min-max', size=50).encode(
                        x=alt.X('Allocation:N', title='Allocation Arm', axis=alt.Axis(labelAngle=0)),
                        y=alt.Y(f'{selected_var}:Q', title=selected_var),
                        color=alt.Color('Allocation:N', scale=alt.Scale(domain=['C', 'T'], range=['#0d9488', '#6366f1']), title='Arm')
                    ).properties(
                        width=350,
                        height=400
                    ).configure_view(
                        stroke='transparent'
                    )
                    
                    st.altair_chart(boxplot, use_container_width=False)
                    
                else:
                    # Categorical variable: Render grouped column chart
                    st.markdown(f"#### Distribution of `{selected_var}` per Treatment Arm")
                    
                    # Prepare counts and percentages
                    chart_data = df_rand.groupby([selected_var, 'Allocation']).size().reset_index(name='Count')
                    total_by_allocation = df_rand.groupby('Allocation').size().to_dict()
                    chart_data['Percentage'] = chart_data.apply(
                        lambda row: (row['Count'] / total_by_allocation[row['Allocation']]) * 100, axis=1
                    )
                    
                    bar_chart = alt.Chart(chart_data).mark_bar().encode(
                        x=alt.X('Allocation:N', title='Allocation Arm', axis=alt.Axis(labelAngle=0)),
                        y=alt.Y('Percentage:Q', title='Percentage (%)'),
                        color=alt.Color('Allocation:N', scale=alt.Scale(domain=['C', 'T'], range=['#0d9488', '#6366f1']), title='Arm'),
                        column=alt.Column(f'{selected_var}:N', title=selected_var)
                    ).properties(
                        width=120,
                        height=350
                    ).configure_view(
                        stroke='transparent'
                    )
                    
                    st.altair_chart(bar_chart, use_container_width=True)
                    
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
