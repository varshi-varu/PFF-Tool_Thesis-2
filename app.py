import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Import your v11 engine functions
from pfff_engine import compute_scn, run_mcs, simulate_mode, spearman_tornado, MODES, HURDLES, fi_color, verdict, PROJECTS

# ─── PAGE CONFIGURATION ────────────────────────────────────────────────────────
st.set_page_config(page_title="PFFF Auditor", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main {background-color: #ffffff;}
    .metric-container {text-align: center; padding: 10px; border-radius: 8px; background: #f8f9fa; margin-bottom: 15px;}
    .fi-title {font-size: 14px; color: #6c757d; margin-bottom: 0px;}
    .fi-value {font-size: 32px; font-weight: bold; margin-top: 0px; margin-bottom: 0px;}
    .hurdle-badge {background-color: #e9ecef; color: #495057; padding: 2px 8px; border-radius: 12px; font-size: 12px;}
    </style>
""", unsafe_allow_html=True)

# ─── STATE MANAGEMENT ──────────────────────────────────────────────────────────
if "p_custom" not in st.session_state:
    st.session_state.p_custom = PROJECTS["P7"].copy() # Let's default to Samruddhi for the Wow factor

def load_template():
    st.session_state.p_custom = PROJECTS[st.session_state.template_selector].copy()

# ─── SIDEBAR: MANUAL INPUT FORM ────────────────────────────────────────────────
with st.sidebar:
    st.title("1. Project Parameters")
    
    st.selectbox("Load DPR Template:", list(PROJECTS.keys()), 
                 format_func=lambda x: PROJECTS[x]["name"], 
                 key="template_selector", on_change=load_template)
    
    p = st.session_state.p_custom

    with st.expander("📝 Basic Details", expanded=False):
        p["name"] = st.text_input("Project Name", p["name"])
        p["dpr_mode"] = st.selectbox("DPR Procurement Mode", ["EPC", "HAM", "BOT"], index=["EPC", "HAM", "BOT"].index(p.get("dpr_mode", "EPC")))
        p["civil_cr"] = st.number_input("Civil Cost Component (Cr)", value=float(p["civil_cr"]))
        p["la_cr"] = st.number_input("LA Cost Component (Cr)", value=float(p["la_cr"]))
        p["scale_cr"] = p["civil_cr"] + p["la_cr"]
        p["build_mo"] = st.number_input("Construction Time (Months)", value=int(p["build_mo"]))
        
    with st.expander("💰 Financial & Economic Data", expanded=False):
        p["dpr_eirr"] = st.number_input("Stated Economic IRR (%)", value=float(p["dpr_eirr"]))
        p["dpr_firr"] = st.number_input("Stated Financial IRR (%)", value=float(p["dpr_firr"] if p["dpr_firr"] else 0.0))
        p["yr1_aadt"] = st.number_input("Year 1 AADT (Forecast)", value=int(p["yr1_aadt"]))
        p["base_aadt"] = st.number_input("Base Year AADT", value=int(p["base_aadt"]))
        
        # Adding actual AADT field for validation projects
        actual_val = int(p.get("actual_aadt", 0))
        new_actual = st.number_input("Actual Realized AADT (If Known/Validation)", value=actual_val)
        if new_actual > 0:
            p["actual_aadt"] = new_actual
        elif "actual_aadt" in p:
            del p["actual_aadt"]

    with st.expander("🏗️ SCN Override (Stress Test)", expanded=True):
        p["la_pct"] = st.slider("Land Acquisition Complete (%)", 0, 100, int(p["la_pct"]))
        p["dpr_yr"] = st.number_input("DPR Submission Year", value=int(p.get("dpr_yr", 2022)))
        p["survey_yr"] = st.number_input("Traffic Survey Year", value=int(p["survey_yr"]))
        p["geotech"] = st.select_slider("Geotech Quality", ["DESKTOP", "PARTIAL", "COMPLETE"], value=p["geotech"])
        p["contractor"] = st.select_slider("Contractor Capability", ["STRESSED", "ADEQUATE", "STRONG"], value=p["contractor"])
    
    # Hidden defaults to prevent crashes
    p["om_cr"] = p.get("om_cr", 50.0); p["growth"] = p.get("growth", 0.06)
    p["cost_sens"] = p.get("cost_sens", 0.15); p["traf_sens"] = p.get("traf_sens", 0.20)
    p["terrain"] = p.get("terrain", "PLAIN"); p["community"] = p.get("community", "MEDIUM")
    p["forest_clr"] = p.get("forest_clr", "CLEARED"); p["crossings"] = p.get("crossings", "MODERATE")
    p["proj_type"] = p.get("proj_type", "GREENFIELD"); p["network"] = p.get("network", "CORRIDOR_LINK")

    run_btn = st.button("🚀 Execute 10,000 Iterations", type="primary", use_container_width=True)

# ─── MAIN DASHBOARD ────────────────────────────────────────────────────────────

st.markdown("<h1>🏛️ Probabilistic Feasibility Fragility Framework (PFFF)</h1>", unsafe_allow_html=True)

if run_btn or True: # Runs automatically on load
    with st.spinner("Simulating SCN distributions..."):
        scn = compute_scn(p)
        samp = run_mcs(p, scn, n=10000)
        res_dpr = simulate_mode(p, scn, samp, p["dpr_mode"], n=10000)
        tornado = spearman_tornado(p, scn, samp, res_dpr["eirr_arr"])
        
        st.success(f"Audit Complete for **{p['name']}** under **{p['dpr_mode']}** structure.")
        
        # TOP METRICS
        col1, col2, col3, col4 = st.columns(4)
        ep = res_dpr["eirr_arr"] * 100
        p10, p50, p90 = np.percentile(ep, 10), np.percentile(ep, 50), np.percentile(ep, 90)
        margin = p50 - (HURDLES['EIRR']*100)
        
        with col1:
            st.markdown(f"""<div class="metric-container" style="border-top: 4px solid {fi_color(res_dpr['fi_p'])[1]}">
                <p class="fi-title">Primary Fragility Index</p>
                <p class="fi-value" style="color: {fi_color(res_dpr['fi_p'])[1]}">{res_dpr['fi_p']:.1f}%</p>
                <span class="hurdle-badge">{verdict(res_dpr['fi_p']).split('—')[0]}</span></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="metric-container">
                <p class="fi-title">Simulated Median (P50)</p>
                <p class="fi-value" style="color: #212529">{p50:.1f}%</p>
                <span class="hurdle-badge">Margin: {margin:+.1f}pp vs 12%</span></div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="metric-container">
                <p class="fi-title">Adverse Scenario (P10)</p>
                <p class="fi-value" style="color: #dc3545">{p10:.1f}%</p>
                <span class="hurdle-badge">Worst 10% of outcomes</span></div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class="metric-container">
                <p class="fi-title">Primary Threat Driver</p>
                <p class="fi-value" style="color: #0d6efd; font-size: 24px; padding-top: 8px;">{tornado[0][0]}</p>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")
        
        # ─── TABS ──────────────────────────────────────────────────────────────
        tab1, tab2, tab3 = st.tabs(["📊 Forensic Distributions", "🔬 Advanced Analytics", "🛡️ Procurement Matrix"])
        
        # TAB 1: HISTOGRAMS
        with tab1:
            colA, colB = st.columns([3, 2])
            with colA:
                fig1 = go.Figure()
                fig1.add_trace(go.Histogram(x=ep, nbinsx=60, marker_color='#0D6EFD', opacity=0.8))
                fig1.add_vline(x=12.0, line_dash="dash", line_color="red", annotation_text="12% Hurdle")
                fig1.add_vline(x=p["dpr_eirr"], line_color="black", annotation_text="DPR Stated")
                fig1.update_layout(title="Economic Viability (EIRR) Stress Test", xaxis_title="EIRR (%)", plot_bgcolor="white", showlegend=False)
                st.plotly_chart(fig1, use_container_width=True)
            with colB:
                names = [t[0] for t in tornado[:5]][::-1]
                rhos = [t[1] for t in tornado[:5]][::-1]
                fig2 = go.Figure(go.Bar(x=rhos, y=names, orientation='h', marker_color=['#DC3545' if r<0 else '#0D6EFD' for r in rhos]))
                fig2.update_layout(title="Fragility Drivers (Spearman Rank)", plot_bgcolor="white")
                st.plotly_chart(fig2, use_container_width=True)

        # TAB 2: ADVANCED ANALYTICS (Brought Back!)
        with tab2:
            colC, colD = st.columns(2)
            
            with colC:
                # TRAFFIC DISTRIBUTION & ACTUAL SCATTER
                v01 = samp["v01"]
                fig3 = go.Figure()
                fig3.add_trace(go.Histogram(x=v01, nbinsx=50, marker_color='#17a2b8', opacity=0.7, name="Simulated Demand"))
                fig3.add_vline(x=p["yr1_aadt"], line_color="black", line_dash="dash", annotation_text="DPR Forecast")
                if "actual_aadt" in p:
                    act = p["actual_aadt"]
                    color = "green" if act > p["yr1_aadt"] else "red"
                    label = "Traffic Beat" if act > p["yr1_aadt"] else "Optimism Bias"
                    fig3.add_vline(x=act, line_color=color, line_width=3, annotation_text=f"Actual: {label}")
                
                fig3.update_layout(title=f"Traffic Demand Forecast Drift (JDR: {scn['jdr']:.2f})", xaxis_title="AADT (PCU)", plot_bgcolor="white", showlegend=False)
                st.plotly_chart(fig3, use_container_width=True)
                
            with colD:
                # SAFETY MARGIN (P10 to P90 Range)
                fig4 = go.Figure()
                fig4.add_trace(go.Scatter(x=[p10, p90], y=["EIRR Range"], mode="lines", line=dict(color="#0D6EFD", width=10), name="P10-P90 Bound"))
                fig4.add_trace(go.Scatter(x=[p50], y=["EIRR Range"], mode="markers", marker=dict(color="#0D6EFD", size=15), name="P50 Median"))
                fig4.add_trace(go.Scatter(x=[p["dpr_eirr"]], y=["EIRR Range"], mode="markers", marker=dict(symbol="diamond", color="black", size=12), name="DPR Stated"))
                fig4.add_vline(x=12.0, line_dash="dash", line_color="red", annotation_text="Hurdle")
                
                fig4.update_layout(title="Safety Margin Bound (P10 vs P50 vs DPR)", xaxis_title="Economic IRR (%)", yaxis=dict(showticklabels=False), height=300, plot_bgcolor="white")
                st.plotly_chart(fig4, use_container_width=True)

        # TAB 3: PROCUREMENT PIVOT
        with tab3:
            st.markdown("Instantly compare financial survival across delivery modes.")
            res_all = {m: simulate_mode(p, scn, samp, m) for m in MODES}
            modes = MODES
            fis = [res_all[m]["fi_p"] for m in modes]
            
            fig5 = go.Figure(go.Bar(x=modes, y=fis, marker_color=[fi_color(f)[1] for f in fis], text=[f"{f:.1f}%" for f in fis], textposition='auto'))
            fig5.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="RED Threshold")
            fig5.update_layout(yaxis_title="Fragility Index (%)", yaxis_range=[0, 105], plot_bgcolor="white", height=400)
            st.plotly_chart(fig5, use_container_width=True)

        # ─── DATA AUDIT & DOWNLOAD ─────────────────────────────────────────────
        st.markdown("---")
        with st.expander("📋 Data Audit & Export", expanded=False):
            st.write("SCN Conditioning Weights Engine:")
            st.json(scn)