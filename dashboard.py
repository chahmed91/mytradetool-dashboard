"""
MyTradeTool — Dashboard Streamlit V1.0
Architecture : Hetzner VPS (engine.py) → n8n webhook → Streamlit Cloud (ce fichier)
Auteur : Ahmed | Stack : Streamlit + Plotly + Pandas
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
N8N_WEBHOOK_URL = "https://achaari.app.n8n.cloud/webhook/mytrade-serve"
AUTO_REFRESH_SECONDS = 600  # 10 minutes (même cadence que l'engine)

st.set_page_config(
    page_title="MyTradeTool",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# STYLES CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background: #1c2333;
        border-radius: 10px;
