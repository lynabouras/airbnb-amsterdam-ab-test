import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from pipeline import load_and_clean, run_sql, run_stats, apply_psm, GROUP_COLORS


st.set_page_config(
    page_title="Airbnb Amsterdam : L'Instant Booking améliore-t-il les réservations ?",

    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown("""
<style>
  /* KPI cards */
  .kpi-card {
    background: #f8f9fa;
    border-left: 5px solid #B06470;
    padding: 18px 20px 14px;
    border-radius: 10px;
  }
  .kpi-card.teal  { border-left-color:#EFD705; }
  .kpi-card.slate { border-left-color: #808080; }
  .kpi-label { font-size: 11px; color: #999; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 4px; }
  .kpi-value { font-size: 34px; font-weight: 700; color: #222; line-height: 1.1; }
  .kpi-sub   { font-size: 12px; color: #777; margin-top: 4px; }

  /* Hypothesis banner */
  .hypo-box {
    background: linear-gradient(135deg, #B06470 0%, #EFD705 100%);
    color: white;
    padding: 22px 28px;
    border-radius: 12px;
    margin: 8px 0 16px;
  }
  .hypo-box h3 { margin: 0 0 10px; font-size: 18px; }
  .hypo-box p  { margin: 4px 0; font-size: 14px; line-height: 1.6; }

  /* Significance badge */
  .badge {
    display: inline-block;
    padding: 5px 14px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 13px;
    margin-top: 6px;
  }
  .badge-yes { background: #d4edda; color: #155724; }
  .badge-no  { background: #f8d7da; color: #721c24; }

  /* Stat result card */
  .stat-card {
    background: #fff;
    border: 1px solid #e9ecef;
    border-radius: 10px;
    padding: 16px 18px;
  }
  .stat-row { display: flex; justify-content: space-between; margin: 5px 0; font-size: 13px; }
  .stat-key { color: #888; }
  .stat-val { font-weight: 600; color: #222; }
  .stat-val-sig { color: #1a8a43; }
  .stat-val-nsig { color: #c0392b; }

  /* Conclusion */
  .conclusion {
    background: linear-gradient(135deg, #B06470 0%, #EFD705 100%);
    color: white;
    padding: 26px 30px;
    border-radius: 12px;
    margin-top: 20px;
  }
  .conclusion h2 { margin: 0 0 14px; }
  .conclusion p  { margin: 6px 0; font-size: 15px; line-height: 1.6; }
  .conclusion .note { font-size: 12px; opacity: 0.8; margin-top: 14px; }

  /* Section title */
  .section-title {
    font-size: 20px;
    font-weight: 700;
    color: #333;
    margin: 28px 0 10px;
    border-bottom: 2px solid #2ECC71;
    padding-bottom: 6px;
  }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Chargement des données…")
def load():
    return load_and_clean()


df_full = load()

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Airbnb_Logo_Bélo.svg/320px-Airbnb_Logo_Bélo.svg.png", width=120)
    st.markdown("## Filtres")

    room_types = sorted(df_full["room_type"].dropna().unique())
    selected_rooms = st.multiselect(
        "Type de logement",
        room_types,
        default=room_types,
    )

    neighbourhoods = sorted(df_full["neighbourhood_cleansed"].dropna().unique())
    selected_neigh = st.multiselect(
        "Quartier",
        neighbourhoods,
        default=neighbourhoods,
        placeholder="Tous les quartiers",
    )

    st.divider()
    show_raw = st.checkbox("Afficher les données brutes")

    st.markdown("""
    <div style="margin-top:20px;font-size:12px;color:#999">
      <b>Source :</b> Inside Airbnb<br>
      <b>Date :</b> Septembre 2025<br>
      <b>Ville :</b> Amsterdam
    </div>
    """, unsafe_allow_html=True)



mask = df_full["room_type"].isin(selected_rooms) & df_full["neighbourhood_cleansed"].isin(selected_neigh)
df = df_full[mask].copy()
df = apply_psm(df)
sql = run_sql(df)
stat_res = run_stats(df)



st.markdown("# AB Test Dashboard — Amsterdam, North Holland, The Netherlands")
st.markdown(
    "**Question :** L'activation de l'**Instant Booking** augmente-t-elle les réservations ? "
    "Analyse statistique sur les données du 11 septembre 2025."
)
st.divider()



n_total = len(df)
n_a = (df["group"] == "Groupe A").sum()
n_b = (df["group"] == "Groupe B").sum()

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""
    <div class="kpi-card slate">
      <div class="kpi-label">Annonces analysées</div>
      <div class="kpi-value">{n_total:,}</div>
      <div class="kpi-sub">Amsterdam, sept. 2025</div>
    </div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Groupe A — Instant Book</div>
      <div class="kpi-value">{n_a:,}</div>
      <div class="kpi-sub">{n_a/n_total*100:.1f}% des annonces</div>
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="kpi-card teal">
      <div class="kpi-label">Groupe B — Standard</div>
      <div class="kpi-value">{n_b:,}</div>
      <div class="kpi-sub">{n_b/n_total*100:.1f}% des annonces</div>
    </div>""", unsafe_allow_html=True)

with k4:
    main = stat_res["number_of_reviews_ltm"]
    badge_cls = "badge-yes" if main["significant"] else "badge-no"
    badge_txt = "p ≥ 0.05 ✓" if main["significant"] else "p ≥ 0.05 ✗"
    st.markdown(f"""
    <div class="kpi-card slate">
      <div class="kpi-label">Résultat principal</div>
      <div class="kpi-value" style="font-size:22px">Mann-Whitney U</div>
      <div><span class="badge {badge_cls}">{badge_txt}</span></div>
    </div>""", unsafe_allow_html=True)



st.markdown("""
<div class="hypo-box">
  <h3>Hypothèses du test</h3>
  <p><b>H₀ (hypothèse nulle) :</b> L'Instant Booking n'a <em>pas</em> d'effet significatif sur le nombre de réservations.</p>
  <p><b>H₁ (hypothèse alternative) :</b> Les annonces Instant Booking obtiennent <em>significativement plus</em> de réservations.</p>
  <p><b>Airbnb ne donne pas le nombre de réservations.</p>
</div>
""", unsafe_allow_html=True)



st.markdown('<div class="section-title">Résultats Statistiques : le test non paramétrique de Mann-Whitney</div>', unsafe_allow_html=True)

metric_cols = st.columns(3)
metric_keys = [
    ("number_of_reviews_ltm",     "Avis (12 mois)",         ""),
    ("estimated_occupancy_l365d", "Occupation (jours/an)",   ""),
    ("estimated_revenue_l365d",   "Revenu estimé (€/an)",    ""),
]

for col_st, (key, title, _) in zip(metric_cols, metric_keys):
    res = stat_res[key]
    p   = res["p_value"]
    delta_pct = ((res["mean_a"] - res["mean_b"]) / res["mean_b"] * 100) if res["mean_b"] else 0
    sig = res["significant"]
    badge_cls = "badge-yes" if sig else "badge-no"
    badge_txt = "SIGNIFICATIF"  if sig else "NON SIGNIFICATIF"
    p_cls     = "stat-val-sig"     if sig else "stat-val-nsig"

    with col_st:
        st.markdown(f"**{title}**")
        m1, m2 = st.columns(2)
        m1.metric("Groupe A (moy.)", f"{res['mean_a']:.1f}", f"{delta_pct:+.1f}%")
        m2.metric("Groupe B (moy.)", f"{res['mean_b']:.1f}")

        st.markdown(f"""
        <div class="stat-card">
          <div class="stat-row">
            <span class="stat-key">p-value</span>
            <span class="stat-val {p_cls}">{"< 0.0001" if p < 0.0001 else f"{p:.4f}"}</span>
          </div>
          <div class="stat-row">
            <span class="stat-key">Statistique U</span>
            <span class="stat-val">{res['u_stat']:,.0f}</span>
          </div>
          <div class="stat-row" style="font-size:11px;color:#888;margin-bottom:4px">
            <span>A obtient une valeur plus élevée que B dans {res['u_stat']:,.0f} duels sur {int(res['n_a'] * res['n_b']):,} comparaisons possibles</span>
          </div>
          <div class="stat-row">
            <span class="stat-key">Effect size r</span>
            <span class="stat-val">{res['effect_r']:.3f} ({res['effect_label']})</span>
          </div>
          <div><span class="badge {badge_cls}">{badge_txt}</span></div>
        </div>
        """, unsafe_allow_html=True)


st.markdown('<div class="section-title">Distributions</div>', unsafe_allow_html=True)

c_l, c_m, c_r = st.columns(3)

with c_l:
    fig = px.box(
        df, x="group", y="number_of_reviews_ltm",
        color="group", color_discrete_map=GROUP_COLORS,
        title="Avis (12 mois) par groupe",
        labels={"group": "", "number_of_reviews_ltm": "Nombre d'avis"},
        points=False, log_y=True,
    )
    fig.update_layout(showlegend=False, height=360, title_font_size=14)
    st.plotly_chart(fig, use_container_width=True)

with c_m:
    fig = px.box(
        df, x="group", y="estimated_occupancy_l365d",
        color="group", color_discrete_map=GROUP_COLORS,
        title="Occupation (jours/an) par groupe",
        labels={"group": "", "estimated_occupancy_l365d": "Jours"},
        points=False, log_y=True,
    )
    fig.update_layout(showlegend=False, height=360, title_font_size=14)
    st.plotly_chart(fig, use_container_width=True)

with c_r:
    fig = px.box(
        df, x="group", y="estimated_revenue_l365d",
        color="group", color_discrete_map=GROUP_COLORS,
        title="Revenu estimé (€/an) par groupe",
        labels={"group": "", "estimated_revenue_l365d": "Revenu (€)"},
        points=False, log_y=True,
    )
    fig.update_layout(showlegend=False, height=360, title_font_size=14)
    st.plotly_chart(fig, use_container_width=True)

df_hist = df[df["number_of_reviews_ltm"].between(1, 100)]
fig = px.histogram(
    df_hist, x="number_of_reviews_ltm",
    color="group", color_discrete_map=GROUP_COLORS,
    barmode="overlay", opacity=0.72, nbins=50,
    title="Histogramme des avis (zoom 1–100) — superposition des deux groupes",
    labels={"number_of_reviews_ltm": "Nombre d'avis", "group": "Groupe"},
)
fig.update_layout(height=300, title_font_size=14, bargap=0.05)
st.plotly_chart(fig, use_container_width=True)



st.markdown('<div class="section-title">Comparaison des moyennes (SQL)</div>', unsafe_allow_html=True)

summary_filt = sql["summary"].copy()

metrics_bar = [
    ("avg_reviews",   "Avis moy. (12 mois)"),
    ("avg_occupancy", "Occupation moy. (jours/an)"),
    ("pct_superhost", "% Superhost"),
]

bar_cols = st.columns(3)
for col_st, (metric, label) in zip(bar_cols, metrics_bar):
    with col_st:
        fig = go.Figure(go.Bar(
            x=summary_filt["group"],
            y=summary_filt[metric],
            marker_color=[GROUP_COLORS[g] for g in summary_filt["group"]],
            text=summary_filt[metric].round(1),
            textposition="outside",
        ))
        fig.update_layout(
            title=label,
            height=280,
            showlegend=False,
            title_font_size=13,
            margin=dict(t=40, b=20),
            yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)



st.markdown('<div class="section-title">Carte des annonces — Amsterdam</div>', unsafe_allow_html=True)

df_map = df[["latitude", "longitude", "group", "number_of_reviews_ltm", "price",
             "neighbourhood_cleansed"]].dropna(subset=["latitude", "longitude"])
df_map = df_map.sample(min(4000, len(df_map)), random_state=42)

fig = px.scatter_mapbox(
    df_map,
    lat="latitude", lon="longitude",
    color="group", color_discrete_map=GROUP_COLORS,
    hover_data={
        "latitude": False, "longitude": False,
        "number_of_reviews_ltm": True,
        "price": True,
        "neighbourhood_cleansed": True,
    },
    zoom=11.5, height=520,
    mapbox_style="open-street-map",
    opacity=0.55,
    title="Répartition géographique — Groupe A (violet) vs Groupe B (jaune)",
)
fig.update_layout(
    legend_title="Groupe",
    margin=dict(l=0, r=0, t=40, b=0),
    title_font_size=14,
)
st.plotly_chart(fig, use_container_width=True)


st.markdown('<div class="section-title">Analyse par Quartier (Top 15)</div>', unsafe_allow_html=True)

neigh_data = sql["by_neighbourhood"]
top_neigh = (
    neigh_data.groupby("neighbourhood")["n"].sum()
    .nlargest(15).index
)
neigh_top = neigh_data[neigh_data["neighbourhood"].isin(top_neigh)]

n_l, n_r = st.columns(2)

with n_l:
    fig = px.bar(
        neigh_top, x="neighbourhood", y="avg_reviews",
        color="group", color_discrete_map=GROUP_COLORS,
        barmode="group",
        title="Avis moyens par quartier",
        labels={"avg_reviews": "Avis moy.", "neighbourhood": "", "group": ""},
    )
    fig.update_layout(height=420, xaxis_tickangle=-35, title_font_size=14)
    st.plotly_chart(fig, use_container_width=True)

with n_r:
    fig = px.bar(
        neigh_top, x="neighbourhood", y="avg_revenue",
        color="group", color_discrete_map=GROUP_COLORS,
        barmode="group",
        title="Revenu moyen estimé par quartier (€/an)",
        labels={"avg_revenue": "Revenu moy. (€)", "neighbourhood": "", "group": ""},
    )
    fig.update_layout(height=420, xaxis_tickangle=-35, title_font_size=14)
    st.plotly_chart(fig, use_container_width=True)



st.markdown('<div class="section-title">Analyse par Type de Logement</div>', unsafe_allow_html=True)

room_data = sql["by_room_type"]
r_l, r_r = st.columns(2)

with r_l:
    fig = px.bar(
        room_data, x="room_type", y="avg_reviews",
        color="group", color_discrete_map=GROUP_COLORS,
        barmode="group",
        title="Avis moyens (12 mois) par type",
        labels={"avg_reviews": "Avis moy.", "room_type": "", "group": ""},
    )
    fig.update_layout(height=360, title_font_size=14)
    st.plotly_chart(fig, use_container_width=True)

with r_r:
    fig = px.bar(
        room_data, x="room_type", y="avg_price",
        color="group", color_discrete_map=GROUP_COLORS,
        barmode="group",
        title="Prix moyen (€/nuit) par type",
        labels={"avg_price": "Prix (€/nuit)", "room_type": "", "group": ""},
    )
    fig.update_layout(height=360, title_font_size=14)
    st.plotly_chart(fig, use_container_width=True)



st.markdown('<div class="section-title">Récapitulatif SQL </div>', unsafe_allow_html=True)

st.dataframe(
    sql["summary"].rename(columns={
        "group":        "Groupe",
        "n":            "effectif",
        "avg_reviews":  "Avis moy.",
        "med_reviews":  "Avis méd.",
        "avg_occupancy":"Occupation (j)",
        "avg_revenue":  "Revenu moy. (€)",
        "med_revenue":  "Revenu méd. (€)",
        "avg_price":    "Prix moy. (€)",
        "pct_superhost":"% Superhost",
    }),
    use_container_width=True,
    hide_index=True,
)


if show_raw:
    st.markdown('<div class="section-title">Données brutes</div>', unsafe_allow_html=True)
    cols_show = [
        "id", "group", "neighbourhood_cleansed", "room_type",
        "price", "number_of_reviews_ltm", "estimated_occupancy_l365d",
        "estimated_revenue_l365d", "host_is_superhost", "instant_bookable",
    ]
    st.dataframe(df[cols_show].sort_values("number_of_reviews_ltm", ascending=False),
                 use_container_width=True, height=400)



main   = stat_res["number_of_reviews_ltm"]
occ    = stat_res["estimated_occupancy_l365d"]
rev    = stat_res["estimated_revenue_l365d"]

def delta(r):
    return (r["mean_a"] - r["mean_b"]) / r["mean_b"] * 100 if r["mean_b"] else 0

verdict_txt = "On <b>rejette H₀</b>" if main["significant"] else "On <b>ne peut pas rejeter H₀</b>"
sig_txt     = "statistiquement significative" if main["significant"] else "non significative"
p_fmt       = "< 0.0001" if main["p_value"] < 0.0001 else f"{main['p_value']:.4f}"

st.markdown(f"""
<div class="conclusion">
  <h2>Conclusion</h2>
  <p>{verdict_txt} — Après appariement PSM (Propensity Score Matching) sur {main['n_a']} paires de logements comparables
     (même quartier, type, prix, niveau d'hôte), la différence entre les deux groupes est <b>{sig_txt}</b>
     sur les 3 métriques (seuil α = 0.05).</p>

  <p><b>Avis (12 mois) :</b> Groupe A = {main['mean_a']:.1f} vs Groupe B = {main['mean_b']:.1f}
     ({delta(main):+.1f}%) — p = {p_fmt}, r = {main['effect_r']:.3f} ({main['effect_label']})</p>

  <p><b>Occupation (jours/an) :</b> Groupe A = {occ['mean_a']:.1f} vs Groupe B = {occ['mean_b']:.1f}
     ({delta(occ):+.1f}%) — p = {"< 0.0001" if occ["p_value"] < 0.0001 else f"{occ['p_value']:.4f}"},
     r = {occ['effect_r']:.3f} ({occ['effect_label']})</p>

  <p><b>Revenu estimé (€/an) :</b> Groupe A = {rev['mean_a']:,.0f} € vs Groupe B = {rev['mean_b']:,.0f} €
     ({delta(rev):+.1f}%) — p = {"< 0.0001" if rev["p_value"] < 0.0001 else f"{rev['p_value']:.4f}"},
     r = {rev['effect_r']:.3f} ({rev['effect_label']})</p>

  <p>L'effet de taille r est négligeable sur les 3 métriques (|r| < 0.1).
    </p>

  <p class="note">Le biais de sélection sur les variables observables
     est corrigé, mais des variables non observées (qualité des photos, réactivité de l'hôte...)
     peuvent encore influencer les résultats. Une expérience randomisée contrôlée reste
     la seule façon de conclure sur l'effet causal de l'Instant Booking.</p>
</div>
""", unsafe_allow_html=True)
