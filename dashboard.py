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
N8N_WEBHOOK_URL = "https://achaari.app.n8n.cloud/webhook/mytrade-dashboard"
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
        padding: 16px;
        margin: 6px 0;
        border-left: 4px solid #4CAF50;
    }
    .rec-BUY_CANDIDATE   { color: #00e676; font-weight: 700; }
    .rec-ACCUMULATE      { color: #69f0ae; font-weight: 700; }
    .rec-HOLD            { color: #ffd740; font-weight: 700; }
    .rec-REDUCE          { color: #ff6d00; font-weight: 700; }
    .rec-EXIT            { color: #ff1744; font-weight: 700; }
    .rec-AVOID           { color: #b71c1c; font-weight: 700; }
    .score-bar { height: 8px; border-radius: 4px; margin-top: 4px; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# COULEURS PAR RECOMMANDATION
# ─────────────────────────────────────────────
REC_COLORS = {
    "BUY_CANDIDATE": "#00e676",
    "ACCUMULATE":    "#69f0ae",
    "HOLD":          "#ffd740",
    "REDUCE":        "#ff6d00",
    "EXIT":          "#ff1744",
    "AVOID":         "#b71c1c",
}

SCORE_COLS = [
    "technical_score", "fundamental_score", "market_score",
    "conviction_score", "final_score",
    "risk_score", "quality_score", "growth_score", "valuation_score",
    "news_score", "regime_score", "liquidity_score", "relative_strength_score",
]

# ─────────────────────────────────────────────
# CHARGEMENT DONNÉES
# ─────────────────────────────────────────────
@st.cache_data(ttl=AUTO_REFRESH_SECONDS)
def load_data():
    """Récupère le dernier payload JSON depuis n8n."""
    try:
        resp = requests.get(N8N_WEBHOOK_URL, timeout=15)
        resp.raise_for_status()
        raw = resp.json()

        # n8n peut retourner un dict ou une liste — on normalise
        if isinstance(raw, list):
            data = raw
        elif isinstance(raw, dict):
            # Cherche la clé qui contient la liste d'assets
            for key in ["assets", "results", "data", "scores", "universe"]:
                if key in raw and isinstance(raw[key], list):
                    data = raw[key]
                    break
            else:
                data = [raw]
        else:
            return pd.DataFrame(), None, str(raw)

        df = pd.DataFrame(data)

        # Normalise les noms de colonnes en minuscules
        df.columns = [c.lower().strip() for c in df.columns]

        # Cast numérique pour les scores
        for col in SCORE_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Timestamp de récupération
        fetched_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        return df, fetched_at, None

    except Exception as e:
        return pd.DataFrame(), None, str(e)


def color_rec(val):
    """Colorise les recommandations dans le tableau."""
    c = REC_COLORS.get(str(val), "white")
    return f"color: {c}; font-weight: bold;"


def score_color(val):
    """Colorise les scores (rouge → orange → vert)."""
    try:
        v = float(val)
        if v >= 70:   return "color: #00e676"
        elif v >= 50: return "color: #ffd740"
        else:         return "color: #ff1744"
    except:
        return ""


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/stock-market.png", width=60)
    st.title("MyTradeTool")
    st.caption("V2.7 — Dashboard Streamlit")
    st.divider()

    page = st.radio(
        "Navigation",
        ["📊 Screener", "💼 Portefeuille", "🔍 Détail Asset", "🚨 Alertes / Signaux"],
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("🔄 Rafraîchir les données", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"Auto-refresh : toutes les {AUTO_REFRESH_SECONDS // 60} min")


# ─────────────────────────────────────────────
# CHARGEMENT
# ─────────────────────────────────────────────
df, fetched_at, error = load_data()

if error:
    st.error(f"❌ Erreur de connexion au webhook n8n : `{error}`")
    st.info("Vérifie que :\n1. `N8N_WEBHOOK_URL` est correct dans `dashboard.py`\n2. Le webhook n8n est actif et retourne du JSON\n3. L'engine a bien envoyé des données récemment")
    st.stop()

if df.empty:
    st.warning("⚠️ Aucune donnée reçue. Le payload est vide ou le format n'est pas reconnu.")
    st.stop()

# Colonnes disponibles pour référence
available_cols = set(df.columns)

# ─────────────────────────────────────────────
# HEADER GLOBAL
# ─────────────────────────────────────────────
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown(f"## {page}")
with col_h2:
    st.caption(f"🕐 Mis à jour : {fetched_at}")

st.divider()


# ═══════════════════════════════════════════════
# PAGE 1 — SCREENER
# ═══════════════════════════════════════════════
if page == "📊 Screener":

    # ── Filtres ──
    col_f1, col_f2, col_f3 = st.columns(3)

    rec_col = "recommendation" if "recommendation" in available_cols else None
    asset_type_col = "asset_type" if "asset_type" in available_cols else \
                     "type" if "type" in available_cols else None

    with col_f1:
        if rec_col:
            recs = ["Toutes"] + sorted(df[rec_col].dropna().unique().tolist())
            filtre_rec = st.selectbox("Recommandation", recs)
        else:
            filtre_rec = "Toutes"

    with col_f2:
        if asset_type_col:
            types = ["Tous"] + sorted(df[asset_type_col].dropna().unique().tolist())
            filtre_type = st.selectbox("Type d'asset", types)
        else:
            filtre_type = "Tous"

    with col_f3:
        score_min = st.slider("Score final minimum", 0, 100, 0)

    # ── Filtrage ──
    dff = df.copy()
    if filtre_rec != "Toutes" and rec_col:
        dff = dff[dff[rec_col] == filtre_rec]
    if filtre_type != "Tous" and asset_type_col:
        dff = dff[dff[asset_type_col] == filtre_type]
    if "final_score" in available_cols:
        dff = dff[dff["final_score"] >= score_min]

    # ── KPIs rapides ──
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total assets", len(df))
    if rec_col:
        k2.metric("BUY CANDIDATE", len(df[df[rec_col] == "BUY_CANDIDATE"]))
        k3.metric("EXIT / AVOID",  len(df[df[rec_col].isin(["EXIT", "AVOID"])]))
    if "final_score" in available_cols:
        k4.metric("Score moyen", f"{df['final_score'].mean():.1f}")

    st.divider()

    # ── Tableau principal ──
    display_cols = []
    for c in ["ticker", "name", "asset_type", "recommendation",
              "final_score", "conviction_score", "technical_score",
              "fundamental_score", "market_score", "risk_score"]:
        if c in available_cols:
            display_cols.append(c)

    if not display_cols:
        display_cols = list(df.columns)[:10]

    sort_col = "final_score" if "final_score" in available_cols else display_cols[0]
    dff_sorted = dff[display_cols].sort_values(sort_col, ascending=False) if sort_col in dff.columns else dff[display_cols]

    styled = dff_sorted.style
    if rec_col and rec_col in display_cols:
        styled = styled.applymap(color_rec, subset=[rec_col])
    for sc in [c for c in ["final_score", "conviction_score", "technical_score", "fundamental_score"] if c in display_cols]:
        styled = styled.applymap(score_color, subset=[sc])

    st.dataframe(styled, use_container_width=True, height=500)

    # ── Graphique distribution des scores ──
    if "final_score" in available_cols and rec_col:
        st.subheader("Distribution des scores finaux")
        fig = px.histogram(
            dff, x="final_score", color=rec_col if rec_col else None,
            color_discrete_map=REC_COLORS,
            nbins=20, template="plotly_dark",
            labels={"final_score": "Score final", "count": "Nb assets"},
        )
        fig.update_layout(bargap=0.1, height=300)
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════
# PAGE 2 — PORTEFEUILLE
# ═══════════════════════════════════════════════
elif page == "💼 Portefeuille":

    # Filtre les assets en portefeuille
    port_col = None
    for c in ["in_portfolio", "portfolio", "held", "position", "alignment_status"]:
        if c in available_cols:
            port_col = c
            break

    if port_col:
        if port_col == "alignment_status":
            port_df = df[df[port_col].notna() & (df[port_col] != "NOT_HELD")]
        else:
            port_df = df[df[port_col].isin([True, 1, "true", "yes", "YES", "True"])]
    else:
        st.info("ℹ️ Colonne portefeuille non détectée dans le JSON. Affichage de tous les assets.")
        port_df = df.copy()

    if port_df.empty:
        st.warning("Aucun asset en portefeuille détecté.")
    else:
        # KPIs
        k1, k2, k3 = st.columns(3)
        k1.metric("Positions", len(port_df))

        if "final_score" in available_cols:
            k2.metric("Score moyen portefeuille", f"{port_df['final_score'].mean():.1f}")

        rec_col = "recommendation" if "recommendation" in available_cols else None
        if rec_col:
            exits = port_df[port_df[rec_col].isin(["EXIT", "REDUCE"])]
            k3.metric("⚠️ À réduire / sortir", len(exits))

        st.divider()

        # Tableau portefeuille
        port_cols = []
        for c in ["ticker", "name", "recommendation", "alignment_status",
                  "final_score", "conviction_score", "risk_score",
                  "current_price", "target_price", "weight"]:
            if c in available_cols:
                port_cols.append(c)

        if not port_cols:
            port_cols = list(port_df.columns)[:8]

        styled_port = port_df[port_cols].style
        if rec_col and rec_col in port_cols:
            styled_port = styled_port.applymap(color_rec, subset=[rec_col])

        st.dataframe(styled_port, use_container_width=True)

        # Graphique radar des scores moyens
        radar_cols = [c for c in ["technical_score", "fundamental_score", "market_score",
                                   "risk_score", "quality_score", "growth_score"] if c in available_cols]
        if radar_cols:
            st.subheader("Profil moyen du portefeuille")
            means = [port_df[c].mean() for c in radar_cols]
            labels = [c.replace("_score", "").capitalize() for c in radar_cols]

            fig = go.Figure(go.Scatterpolar(
                r=means + [means[0]],
                theta=labels + [labels[0]],
                fill="toself",
                line_color="#00e676",
                fillcolor="rgba(0,230,118,0.15)",
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                template="plotly_dark", height=380,
            )
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════
# PAGE 3 — DÉTAIL ASSET
# ═══════════════════════════════════════════════
elif page == "🔍 Détail Asset":

    ticker_col = "ticker" if "ticker" in available_cols else \
                 "symbol" if "symbol" in available_cols else None

    if not ticker_col:
        st.error("Colonne 'ticker' ou 'symbol' introuvable dans le JSON.")
        st.stop()

    tickers = sorted(df[ticker_col].dropna().unique().tolist())
    selected = st.selectbox("Sélectionne un asset", tickers)

    asset = df[df[ticker_col] == selected].iloc[0]

    # ── En-tête asset ──
    col_a, col_b = st.columns([2, 1])
    with col_a:
        name = asset.get("name", selected)
        st.markdown(f"### {name} ({selected})")
        atype = asset.get("asset_type", asset.get("type", "—"))
        st.caption(f"Type : {atype}")

    with col_b:
        rec = asset.get("recommendation", "—")
        color = REC_COLORS.get(rec, "white")
        st.markdown(f"<h2 style='color:{color};text-align:right'>{rec}</h2>", unsafe_allow_html=True)

    st.divider()

    # ── Scores principaux ──
    score_display = {
        "🏆 Score Final":       "final_score",
        "💡 Conviction":        "conviction_score",
        "📈 Technique":         "technical_score",
        "🏦 Fondamental":       "fundamental_score",
        "🌍 Marché":            "market_score",
        "⚠️ Risque":            "risk_score",
        "⭐ Qualité":           "quality_score",
        "🚀 Croissance":        "growth_score",
        "💰 Valorisation":      "valuation_score",
        "📰 News":              "news_score",
        "🔮 Régime":            "regime_score",
        "💧 Liquidité":         "liquidity_score",
        "💪 Force relative":    "relative_strength_score",
    }

    scores_available = {k: v for k, v in score_display.items() if v in available_cols}

    if scores_available:
        cols = st.columns(min(4, len(scores_available)))
        for i, (label, col_name) in enumerate(scores_available.items()):
            val = asset.get(col_name, None)
            if val is not None:
                try:
                    v = float(val)
                    delta_color = "normal" if v >= 50 else "inverse"
                    cols[i % 4].metric(label, f"{v:.1f}", delta=f"{'↑' if v >= 50 else '↓'}", delta_color=delta_color)
                except:
                    cols[i % 4].metric(label, str(val))

        # Graphique barres horizontales
        st.subheader("Profil de scoring")
        chart_data = {
            k.split()[-1]: float(asset.get(v, 0) or 0)
            for k, v in scores_available.items()
        }
        fig = go.Figure(go.Bar(
            x=list(chart_data.values()),
            y=list(chart_data.keys()),
            orientation="h",
            marker=dict(
                color=[
                    "#00e676" if v >= 70 else "#ffd740" if v >= 50 else "#ff1744"
                    for v in chart_data.values()
                ]
            ),
        ))
        fig.update_layout(
            template="plotly_dark", height=400,
            xaxis=dict(range=[0, 100], title="Score"),
            yaxis=dict(title=""),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun score trouvé dans le JSON pour cet asset.")

    # ── Autres données ──
    st.subheader("Données brutes")
    exclude = list(score_display.values()) + [ticker_col, "name", "recommendation", "asset_type"]
    other_cols = {k: asset[k] for k in asset.index if k not in exclude and pd.notna(asset[k])}
    if other_cols:
        st.json(other_cols)


# ═══════════════════════════════════════════════
# PAGE 4 — ALERTES / SIGNAUX
# ═══════════════════════════════════════════════
elif page == "🚨 Alertes / Signaux":

    rec_col = "recommendation" if "recommendation" in available_cols else None
    ticker_col = "ticker" if "ticker" in available_cols else \
                 "symbol" if "symbol" in available_cols else None

    if not rec_col:
        st.error("Colonne 'recommendation' absente du JSON.")
        st.stop()

    # ── Signaux forts par catégorie ──
    categories = {
        "🟢 BUY CANDIDATE": ("BUY_CANDIDATE", "#00e676"),
        "🟡 ACCUMULATE":    ("ACCUMULATE",    "#69f0ae"),
        "🟠 REDUCE":        ("REDUCE",         "#ff6d00"),
        "🔴 EXIT":          ("EXIT",           "#ff1744"),
        "⚫ AVOID":         ("AVOID",          "#b71c1c"),
    }

    for label, (rec_val, color) in categories.items():
        subset = df[df[rec_col] == rec_val]
        if not subset.empty:
            with st.expander(f"{label}  ({len(subset)} assets)", expanded=(rec_val in ["BUY_CANDIDATE", "EXIT"])):
                disp_cols = [c for c in [ticker_col, "name", "final_score", "conviction_score",
                                          "technical_score", "risk_score"] if c and c in available_cols]
                if not disp_cols:
                    disp_cols = list(subset.columns)[:6]
                sort_c = "final_score" if "final_score" in available_cols else disp_cols[0]
                st.dataframe(
                    subset[disp_cols].sort_values(sort_c, ascending=(rec_val in ["EXIT", "AVOID"])),
                    use_container_width=True,
                )

    # ── Graphique camembert des recommandations ──
    st.divider()
    st.subheader("Répartition des recommandations")
    rec_counts = df[rec_col].value_counts().reset_index()
    rec_counts.columns = ["recommendation", "count"]
    fig = px.pie(
        rec_counts, names="recommendation", values="count",
        color="recommendation", color_discrete_map=REC_COLORS,
        template="plotly_dark", hole=0.4,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # ── Top 5 / Bottom 5 ──
    if "final_score" in available_cols and ticker_col:
        col_t, col_b = st.columns(2)
        with col_t:
            st.subheader("🏆 Top 5 scores")
            top5 = df[[ticker_col, "final_score", rec_col]].sort_values("final_score", ascending=False).head(5)
            st.dataframe(top5.style.applymap(color_rec, subset=[rec_col]).applymap(score_color, subset=["final_score"]), use_container_width=True)
        with col_b:
            st.subheader("⚠️ Bottom 5 scores")
            bot5 = df[[ticker_col, "final_score", rec_col]].sort_values("final_score").head(5)
            st.dataframe(bot5.style.applymap(color_rec, subset=[rec_col]).applymap(score_color, subset=["final_score"]), use_container_width=True)
