import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

from pathlib import Path
import base64 as _b64mod

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from coate_auth import exigir_acesso
from coate_styles import aplicar_estilos

aplicar_estilos()
exigir_acesso("farol")

_DATA_PATH = Path(__file__).resolve().parent.parent / "projetos_especiais" / "farol" / "dados" / "Bares.xlsx"

# ── Paletas ────────────────────────────────────────────────────────────────────
CORES_REGIME = {"NORMAL": "#f59e0b", "MICROEMPRESA": "#3b82f6", "EPP": "#22c55e"}
CORES_CNAE = {
    "5611201": "#3b82f6",
    "5611202": "#94a3b8",
    "5611203": "#f59e0b",
    "5611204": "#ef4444",
    "5611205": "#a855f7",
}
LABEL_CNAE = {
    "5611201": "5611201 — Restaurantes e similares",
    "5611202": "5611202 — Bares (outros)",
    "5611203": "5611203 — Lanchonetes / Casas de suco",
    "5611204": "5611204 — Bares especializados (c/ alim.)",
    "5611205": "5611205 — Bares especializados (s/ alim.)",
}

_LB = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#cbd5e1", family="sans-serif"),
    margin=dict(t=50, b=30, l=20, r=20),
    hoverlabel=dict(bgcolor="#1e293b", font_color="#f1f5f9", bordercolor="#334155"),
)

def _lb(**extra):
    d = dict(_LB)
    d.update(extra)
    return d

def _fmt_int(v) -> str:
    try: return f"{int(v):,}".replace(",", ".")
    except: return "0"

def _fmt_moeda(v) -> str:
    try:
        v = float(v)
        if abs(v) >= 1_000_000_000: return f"R$ {v/1_000_000_000:.2f} Bi"
        if abs(v) >= 1_000_000: return f"R$ {v/1_000_000:.2f} Mi"
        if abs(v) >= 1_000: return f"R$ {v/1_000:.1f} K"
        return f"R$ {v:,.2f}".replace(",",".")
    except: return "R$ 0"

def _fmt_moeda_full(v) -> str:
    try: return f"R$ {float(v):,.2f}".replace(",","X").replace(".","_").replace("X","_").replace("_",".")
    except: return "R$ 0,00"

def _fmt_pct(v, d=1) -> str:
    try: return f"{float(v):.{d}f}%"
    except: return "0%"

# ── Carga ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def _carregar(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, dtype=str)
    str_cols = ["dsc_orgao_local","dsc_municipio","dsc_cnae_princ_contribuinte",
                "dsc_regime_rec_contribuinte","dsc_sit_atu_contribuinte",
                "dsc_segmento","dsc_orgao_monitoramento","cod_cnae_princ_contribuinte"]
    for c in str_cols:
        if c in df.columns:
            df[c] = (df[c].astype(str)
                     .str.encode("latin1",errors="ignore")
                     .str.decode("utf-8",errors="ignore")
                     .str.strip())
    num_cols = ["qtd_contribuintes","vlr_arrecadacao_2025","nfe","nfce","cfe","DIMP_IP","dimp_if"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

# ── Hero ───────────────────────────────────────────────────────────────────────
# ── Verificação ────────────────────────────────────────────────────────────────
if not _DATA_PATH.exists():
    st.error("Arquivo não encontrado: " + str(_DATA_PATH))
    st.caption("Coloque o arquivo Bares.xlsx em: projetos_especiais/farol/dados/")
    st.stop()

df_full = _carregar(str(_DATA_PATH))
_total_base = int(df_full["qtd_contribuintes"].sum())

st.markdown(
    """
    <div class="coate-hero">
        <div class="coate-hero-kicker">🚦 FAROL · SEFAZ-CE</div>
        <h1>🍺 Bares e Restaurantes</h1>
        <p>
            Painel analítico do setor de bares, restaurantes e lanchonetes no Ceará.
            Abrange <strong>""" + f"{_total_base:,}".replace(",",".") + """ estabelecimentos</strong> com CNAEs do grupo 5611,
            com visões de arrecadação, DFe, DIMP e potencial de autuação fiscal.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Filtros ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
f1, f2, f3, f4, f5 = st.columns([1.3, 1.3, 1.5, 1.8, 1.8])

with f1:
    regime_opts = ["Todos", "MICROEMPRESA", "EPP", "NORMAL", "ME + EPP"]
    regime_sel = st.selectbox("Regime", regime_opts)

with f2:
    sit_opts = ["Todos", "ATIVO", "ATIVO (EM EDITAL)"]
    sit_sel = st.selectbox("Situação", sit_opts)

with f3:
    cnae_map = {
        "Todos": "Todos",
        "5611201 — Restaurantes e similares": "5611201",
        "5611203 — Lanchonetes, casas de chá e sucos": "5611203",
        "5611204 — Bares especializados (com alimentação)": "5611204",
        "5611205 — Bares especializados (sem alimentação)": "5611205",
        "5611202 — Bares e estabelecimentos (outros)": "5611202",
    }
    cnae_label = st.selectbox("CNAE", list(cnae_map.keys()))
    cnae_sel = cnae_map[cnae_label]

with f4:
    orgaos = ["Todos"] + sorted(df_full["dsc_orgao_local"].dropna().unique().tolist())
    orgao_sel = st.selectbox("Órgão Local", orgaos)

with f5:
    municipios = ["Todos"] + sorted(df_full["dsc_municipio"].dropna().unique().tolist())
    mun_sel = st.selectbox("Município", municipios)

# ── Aplicar filtros ────────────────────────────────────────────────────────────
df = df_full.copy()
if regime_sel == "NORMAL":
    df = df[df["dsc_regime_rec_contribuinte"] == "NORMAL"]
elif regime_sel == "ME + EPP":
    df = df[df["dsc_regime_rec_contribuinte"].isin(["MICROEMPRESA","EPP"])]
elif regime_sel in ("MICROEMPRESA","EPP"):
    df = df[df["dsc_regime_rec_contribuinte"] == regime_sel]

if sit_sel != "Todos":
    df = df[df["dsc_sit_atu_contribuinte"] == sit_sel]
if cnae_sel != "Todos":
    df = df[df["cod_cnae_princ_contribuinte"] == cnae_sel]
if orgao_sel != "Todos":
    df = df[df["dsc_orgao_local"] == orgao_sel]
if mun_sel != "Todos":
    df = df[df["dsc_municipio"] == mun_sel]

if df.empty:
    st.warning("Nenhum registro para os filtros selecionados.")
    st.stop()

# ── Métricas base ──────────────────────────────────────────────────────────────
total_contrib  = df["qtd_contribuintes"].sum()
total_arrec    = df["vlr_arrecadacao_2025"].sum()
total_nfce     = df["nfce"].sum()
total_cfe      = df["cfe"].sum()
total_dimp_ip  = df["DIMP_IP"].sum()
total_dimp_if  = df["dimp_if"].sum()
dif_dimp       = total_dimp_ip - total_dimp_if
em_edital      = df[df["dsc_sit_atu_contribuinte"] == "ATIVO (EM EDITAL)"]["qtd_contribuintes"].sum()
pct_edital     = em_edital / total_contrib * 100 if total_contrib else 0
pct_total      = total_contrib / df_full["qtd_contribuintes"].sum() * 100 if df_full["qtd_contribuintes"].sum() else 0
arrec_medio    = total_arrec / total_contrib if total_contrib else 0

# ── Campos derivados ───────────────────────────────────────────────────────────
total_nfe_doc  = df["nfe"].sum()
total_dfe      = total_nfe_doc + total_nfce + total_cfe          # DFe = NFe + NFCe + CFe
total_dimp     = total_dimp_ip + total_dimp_if                   # DIMP total
omissao             = max(total_dimp - total_dfe, 0)
potencial_icms      = omissao * 0.20
potencial_multa     = omissao * 0.30
taxa_recolhimento     = total_arrec / total_dfe if total_dfe > 0 else 0
icms_autorregularizado = omissao * taxa_recolhimento
_pot_total            = potencial_icms + potencial_multa
pct_economia          = (icms_autorregularizado / _pot_total * 100) if _pot_total > 0 else 0

# ── KPIs — Linha 1: visão geral ───────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
k1,k2,k3 = st.columns(3)

with k1:
    st.markdown(
        '<div class="coate-kpi-card accent-primary">'
        '<div class="coate-kpi-label">Estabelecimentos</div>'
        '<div class="coate-kpi-value">' + _fmt_int(total_contrib) + '</div>'
        '<div class="coate-kpi-help">' + _fmt_pct(pct_total) + ' do filtro total</div>'
        '</div>', unsafe_allow_html=True)
with k2:
    st.markdown(
        '<div class="coate-kpi-card accent-info">'
        '<div class="coate-kpi-label">Arrecadação 2025</div>'
        '<div class="coate-kpi-value">' + _fmt_moeda(total_arrec) + '</div>'
        '<div class="coate-kpi-help">R$ ' + f"{arrec_medio:,.0f}".replace(",",".") + ' / estabelec.</div>'
        '</div>', unsafe_allow_html=True)
with k3:
    st.markdown(
        '<div class="coate-kpi-card accent-warning">'
        '<div class="coate-kpi-label">DFe (NFe + NFCe + CFe)</div>'
        '<div class="coate-kpi-value">' + _fmt_moeda(total_dfe) + '</div>'
        '<div class="coate-kpi-help">NFe: ' + _fmt_int(total_nfe_doc) + ' · NFCe: ' + _fmt_int(total_nfce) + ' · CFe: ' + _fmt_int(total_cfe) + '</div>'
        '</div>', unsafe_allow_html=True)

# ── KPIs — Linha 2: fiscal ─────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
k5,k6,k7,k8 = st.columns(4)

with k5:
    st.markdown(
        '<div class="coate-kpi-card accent-info">'
        '<div class="coate-kpi-label">DIMP (Inst. Pag. + Inst. Fin.)</div>'
        '<div class="coate-kpi-value">' + _fmt_moeda(total_dimp) + '</div>'
        '<div class="coate-kpi-help">IP: ' + _fmt_moeda(total_dimp_ip) + ' · IF: ' + _fmt_moeda(total_dimp_if) + '</div>'
        '</div>', unsafe_allow_html=True)
with k6:
    cor_om = "accent-danger" if omissao > 0 else "accent-primary"
    st.markdown(
        '<div class="coate-kpi-card ' + cor_om + '">'
        '<div class="coate-kpi-label">Omissão de Receitas (DIMP − DFe)</div>'
        '<div class="coate-kpi-value">' + _fmt_moeda(omissao) + '</div>'
        '<div class="coate-kpi-help">DIMP: ' + _fmt_moeda(total_dimp) + ' · DFe: ' + _fmt_moeda(total_dfe) + '</div>'
        '</div>', unsafe_allow_html=True)
with k7:
    st.markdown(
        '<div class="coate-kpi-card accent-warning">'
        '<div class="coate-kpi-label">Potencial Autuação — ICMS (20%)</div>'
        '<div class="coate-kpi-value">' + _fmt_moeda(potencial_icms) + '</div>'
        '<div class="coate-kpi-help">Omissão × 20%</div>'
        '</div>', unsafe_allow_html=True)
with k8:
    st.markdown(
        '<div class="coate-kpi-card" style="border-left:3px solid #a855f7;">'
        '<div class="coate-kpi-label">Potencial Autuação — Multa (30%)</div>'
        '<div class="coate-kpi-value">' + _fmt_moeda(potencial_multa) + '</div>'
        '<div class="coate-kpi-help">Omissão × 30%</div>'
        '</div>', unsafe_allow_html=True)

# KPIs — Linha 3: efetividade tributária
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
k9, k10 = st.columns(2)
_pct_arrec_dfe  = total_arrec / total_dfe  * 100 if total_dfe  > 0 else 0
_pct_arrec_dimp = total_arrec / total_dimp * 100 if total_dimp > 0 else 0
with k9:
    st.markdown(
        '<div class="coate-kpi-card accent-primary">'
        '<div class="coate-kpi-label">Arrecadação / DFe</div>'
        '<div class="coate-kpi-value">' + _fmt_pct(_pct_arrec_dfe, 2) + '</div>'
        '<div class="coate-kpi-help">% do DFe emitido efetivamente recolhido</div>'
        '</div>', unsafe_allow_html=True)
with k10:
    st.markdown(
        '<div class="coate-kpi-card accent-info">'
        '<div class="coate-kpi-label">Arrecadação / DIMP</div>'
        '<div class="coate-kpi-value">' + _fmt_pct(_pct_arrec_dimp, 2) + '</div>'
        '<div class="coate-kpi-help">% do DIMP declarado efetivamente recolhido</div>'
        '</div>', unsafe_allow_html=True)

# ── KPIs — Linha 4: autorregularização ───────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
k_auto1, k_auto2 = st.columns(2)

with k_auto1:
    st.markdown(
        '<div class="coate-kpi-card" style="border-left:3px solid #22c55e;">'
        '<div class="coate-kpi-label">💡 ICMS se Autorregularizado</div>'
        '<div class="coate-kpi-value">' + _fmt_moeda(icms_autorregularizado) + '</div>'
        '<div class="coate-kpi-help">Omissão × ' + _fmt_pct(taxa_recolhimento * 100, 2) + ' (taxa efetiva Arrec./DFe)</div>'
        '</div>', unsafe_allow_html=True)
with k_auto2:
    st.markdown(
        '<div class="coate-kpi-card" style="border-left:3px solid #22c55e;background:rgba(34,197,94,0.07)">'
        '<div class="coate-kpi-label">✅ Autorregularizado ÷ (ICMS 20% + Multa 30%)</div>'
        '<div class="coate-kpi-value">' + _fmt_pct(pct_economia, 1) + '</div>'
        '<div class="coate-kpi-help">'
        'Autorregularizado: ' + _fmt_moeda(icms_autorregularizado) +
        ' · Potencial autuação: ' + _fmt_moeda(_pot_total) +
        ' — Autorregularizar custa ' + _fmt_pct(pct_economia, 1) + ' do valor da autuação'
        '</div>'
        '</div>', unsafe_allow_html=True)

# SEÇÃO 1 — Distribuição por Regime e CNAE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">🏷️ Perfil</div>
        <div class="coate-section-title">Composição por Regime e Atividade</div>
    </div>
    <hr class="coate-section-divider"/>
    """, unsafe_allow_html=True)

g1a, g1b, g1c = st.columns(3)

with g1a:
    df_reg = df.groupby("dsc_regime_rec_contribuinte")["qtd_contribuintes"].sum().reset_index()
    fig_reg = go.Figure(go.Pie(
        labels=df_reg["dsc_regime_rec_contribuinte"].tolist(),
        values=df_reg["qtd_contribuintes"].tolist(),
        hole=0.52,
        marker_colors=[CORES_REGIME.get(r,"#94a3b8") for r in df_reg["dsc_regime_rec_contribuinte"]],
        textinfo="label+percent",
        hovertemplate="%{label}<br>%{value:,} estabelec.<br>%{percent}<extra></extra>",
    ))
    fig_reg.update_layout(**_lb(title="Estabelecimentos por Regime", showlegend=False, height=300))
    st.plotly_chart(fig_reg, use_container_width=True)

with g1b:
    df_cnae_pie = df.groupby("cod_cnae_princ_contribuinte")["qtd_contribuintes"].sum().reset_index()
    df_cnae_pie["label"] = df_cnae_pie["cod_cnae_princ_contribuinte"].map(LABEL_CNAE).fillna(df_cnae_pie["cod_cnae_princ_contribuinte"])
    fig_cnae_pie = go.Figure(go.Pie(
        labels=df_cnae_pie["label"].tolist(),
        values=df_cnae_pie["qtd_contribuintes"].tolist(),
        hole=0.52,
        marker_colors=[CORES_CNAE.get(c,"#94a3b8") for c in df_cnae_pie["cod_cnae_princ_contribuinte"]],
        textinfo="percent",
        hovertemplate="%{label}<br>%{value:,} estabelec.<br>%{percent}<extra></extra>",
    ))
    fig_cnae_pie.update_layout(**_lb(title="Estabelecimentos por CNAE", showlegend=False, height=300))
    st.plotly_chart(fig_cnae_pie, use_container_width=True)

with g1c:
    # Barras: CNAE × Regime empilhado
    df_cr = df.groupby(["cod_cnae_princ_contribuinte","dsc_regime_rec_contribuinte"])["qtd_contribuintes"].sum().reset_index()
    df_cr["cnae_label"] = df_cr["cod_cnae_princ_contribuinte"].map({
        "5611201":"Restaurantes e similares","5611203":"Lanchonetes / Casa de suco",
        "5611204":"Bares c/ alimentação","5611205":"Bares s/ alimentação","5611202":"Bares (outros)"})
    ordem = df_cr.groupby("cnae_label")["qtd_contribuintes"].sum().sort_values(ascending=True).index.tolist()
    fig_cr = go.Figure()
    for reg in ["NORMAL","MICROEMPRESA","EPP"]:
        sub = df_cr[df_cr["dsc_regime_rec_contribuinte"]==reg]
        sub = sub.set_index("cnae_label").reindex(ordem).fillna(0).reset_index()
        fig_cr.add_trace(go.Bar(
            x=sub["qtd_contribuintes"], y=sub["cnae_label"],
            name=reg, orientation="h",
            marker_color=CORES_REGIME.get(reg,"#94a3b8"),
            hovertemplate="<b>%{y}</b><br>" + reg + ": %{x:,}<extra></extra>",
        ))
    fig_cr.update_layout(**_lb(
        title="CNAE × Regime", barmode="stack", height=300,
        margin=dict(t=50,b=20,l=110,r=20),
        legend=dict(orientation="h",y=-0.18,x=0),
        xaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=10)),
    ))
    st.plotly_chart(fig_cr, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 2 — Arrecadação
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">💰 Arrecadação</div>
        <div class="coate-section-title">Arrecadação 2025 por Território e Regime</div>
    </div>
    <hr class="coate-section-divider"/>
    """, unsafe_allow_html=True)

g2a, g2b = st.columns([1.6, 1])

with g2a:
    df_mun = (df.groupby("dsc_municipio")
              .agg(arrec=("vlr_arrecadacao_2025","sum"), contrib=("qtd_contribuintes","sum"))
              .reset_index()
              .sort_values("arrec", ascending=False).head(20))
    df_mun = df_mun.sort_values("arrec", ascending=True)
    df_mun["arrec_per"] = df_mun["arrec"] / df_mun["contrib"].replace(0,1)

    fig_mun = go.Figure(go.Bar(
        x=df_mun["arrec"], y=df_mun["dsc_municipio"],
        orientation="h",
        marker=dict(color=df_mun["arrec"], colorscale=[[0,"#1e3a5f"],[1,"#3b82f6"]], showscale=False),
        customdata=list(zip(df_mun["contrib"], df_mun["arrec_per"])),
        hovertemplate="<b>%{y}</b><br>Arrecadação: R$ %{x:,.0f}<br>%{customdata[0]:,} estabelec.<br>R$ %{customdata[1]:,.0f}/estabelec.<extra></extra>",
        text=df_mun["arrec"].apply(_fmt_moeda),
        textposition="inside", insidetextanchor="end",
        textfont=dict(size=10, color="#f1f5f9"),
    ))
    fig_mun.update_layout(**_lb(
        title="Top 20 Municípios — Arrecadação 2025", height=520,
        margin=dict(t=50,b=20,l=160,r=20),
        xaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat="~s"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=10)),
    ))
    st.plotly_chart(fig_mun, use_container_width=True)

with g2b:
    # Arrecadação por regime
    df_reg_arr = df.groupby("dsc_regime_rec_contribuinte").agg(
        arrec=("vlr_arrecadacao_2025","sum"), contrib=("qtd_contribuintes","sum")
    ).reset_index()
    df_reg_arr["arrec_per"] = df_reg_arr["arrec"] / df_reg_arr["contrib"].replace(0,1)

    fig_reg_arr = go.Figure(go.Bar(
        x=df_reg_arr["dsc_regime_rec_contribuinte"],
        y=df_reg_arr["arrec"],
        marker_color=[CORES_REGIME.get(r,"#94a3b8") for r in df_reg_arr["dsc_regime_rec_contribuinte"]],
        customdata=list(zip(df_reg_arr["contrib"], df_reg_arr["arrec_per"])),
        hovertemplate="<b>%{x}</b><br>R$ %{y:,.0f}<br>%{customdata[0]:,} estabelec.<br>R$ %{customdata[1]:,.0f}/estabelec.<extra></extra>",
    ))
    fig_reg_arr.update_layout(**_lb(
        title="Arrecadação por Regime", height=260,
        showlegend=False,
        xaxis=dict(type="category", gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickprefix="R$ ", tickformat="~s"),
    ))
    st.plotly_chart(fig_reg_arr, use_container_width=True)

    # Arrecadação por CNAE
    df_cnae_arr = df.groupby("cod_cnae_princ_contribuinte").agg(
        arrec=("vlr_arrecadacao_2025","sum"), contrib=("qtd_contribuintes","sum")
    ).reset_index().sort_values("arrec", ascending=True)
    df_cnae_arr["label"] = df_cnae_arr["cod_cnae_princ_contribuinte"].map({
        "5611201":"Restaurantes e similares","5611203":"Lanchonetes / Casa de suco",
        "5611204":"Bares c/ alimentação","5611205":"Bares s/ alimentação","5611202":"Bares (outros)"})

    fig_cnae_arr = go.Figure(go.Bar(
        x=df_cnae_arr["arrec"], y=df_cnae_arr["label"],
        orientation="h",
        marker_color=[CORES_CNAE.get(c,"#94a3b8") for c in df_cnae_arr["cod_cnae_princ_contribuinte"]],
        hovertemplate="<b>%{y}</b><br>R$ %{x:,.0f}<extra></extra>",
    ))
    fig_cnae_arr.update_layout(**_lb(
        title="Arrecadação por CNAE", height=240,
        showlegend=False,
        margin=dict(t=50,b=20,l=110,r=20),
        xaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat="~s"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=10)),
    ))
    st.plotly_chart(fig_cnae_arr, use_container_width=True)

# Arrecadação por órgão local
df_org = df.groupby("dsc_orgao_local").agg(
    arrec=("vlr_arrecadacao_2025","sum"), contrib=("qtd_contribuintes","sum")
).reset_index().sort_values("arrec", ascending=True)

fig_org = go.Figure(go.Bar(
    x=df_org["arrec"], y=df_org["dsc_orgao_local"], orientation="h",
    marker=dict(color=df_org["arrec"], colorscale=[[0,"#1c3b2a"],[1,"#22c55e"]], showscale=False),
    customdata=df_org["contrib"].tolist(),
    text=df_org["arrec"].apply(_fmt_moeda),
    textposition="inside", insidetextanchor="end",
    textfont=dict(size=10, color="#f1f5f9"),
    hovertemplate="<b>%{y}</b><br>R$ %{x:,.0f}<br>%{customdata:,} estabelec.<extra></extra>",
))
fig_org.update_layout(**_lb(
    title="Arrecadação 2025 por Órgão Local", height=420,
    showlegend=False,
    margin=dict(t=50,b=20,l=300,r=20),
    xaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat="~s"),
    yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=9)),
))
st.plotly_chart(fig_org, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 3 — Documentos Fiscais
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">🧾 Documentos Fiscais</div>
        <div class="coate-section-title">NFCe, CF-e e Intensidade de Emissão</div>
    </div>
    <hr class="coate-section-divider"/>
    """, unsafe_allow_html=True)

g3a, = [st.container()]
with g3a:
    # Documentos por CNAE — barras agrupadas
    df_doc_cnae = df.groupby("cod_cnae_princ_contribuinte").agg(
        nfce=("nfce","sum"), cfe=("cfe","sum"), nfe=("nfe","sum"),
        contrib=("qtd_contribuintes","sum")
    ).reset_index()
    df_doc_cnae["label"] = df_doc_cnae["cod_cnae_princ_contribuinte"].map({
        "5611201":"Restaurantes e similares","5611203":"Lanchonetes / Casa de suco",
        "5611204":"Bares c/ alimentação","5611205":"Bares s/ alimentação","5611202":"Bares (outros)"})
    df_doc_cnae = df_doc_cnae.sort_values("nfce", ascending=True)

    fig_doc = go.Figure()
    for doc, cor, nome in [("nfce","#3b82f6","NFCe"),("cfe","#22c55e","CF-e"),("nfe","#f59e0b","NF-e")]:
        fig_doc.add_trace(go.Bar(
            x=df_doc_cnae[doc], y=df_doc_cnae["label"],
            name=nome, orientation="h",
            marker_color=cor,
            hovertemplate="<b>%{y}</b><br>" + nome + ": %{x:,}<extra></extra>",
        ))
    fig_doc.update_layout(**_lb(
        title="Volume de Documentos Fiscais por CNAE",
        barmode="group", height=350,
        margin=dict(t=50,b=20,l=110,r=20),
        legend=dict(orientation="h", y=-0.15, x=0),
        xaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat="~s"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=10)),
    ))
    st.plotly_chart(fig_doc, use_container_width=True)



# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 4 — DIMP: Imposto Próprio vs Imposto Final
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">⚖️ DIMP</div>
        <div class="coate-section-title">Inst. Pagadora × Inst. Financeira — Divergência DIMP</div>
    </div>
    <hr class="coate-section-divider"/>
    """, unsafe_allow_html=True)

g4a, = [st.container()]
with g4a:
    # DIMP por CNAE — IP vs IF
    df_dimp_cnae = df.groupby("cod_cnae_princ_contribuinte").agg(
        ip=("DIMP_IP","sum"), if_=("dimp_if","sum")
    ).reset_index()
    df_dimp_cnae["label"] = df_dimp_cnae["cod_cnae_princ_contribuinte"].map({
        "5611201":"Restaurantes e similares","5611203":"Lanchonetes / Casa de suco",
        "5611204":"Bares c/ alimentação","5611205":"Bares s/ alimentação","5611202":"Bares (outros)"})
    df_dimp_cnae["dif"] = df_dimp_cnae["ip"] - df_dimp_cnae["if_"]
    df_dimp_cnae = df_dimp_cnae.sort_values("ip", ascending=True)

    fig_dimp = go.Figure()
    fig_dimp.add_trace(go.Bar(
        x=df_dimp_cnae["ip"], y=df_dimp_cnae["label"],
        name="Inst. Pagadora (IP)", orientation="h",
        marker_color="#f59e0b",
        hovertemplate="<b>%{y}</b><br>Inst. Pagadora: R$ %{x:,.0f}<extra></extra>",
    ))
    fig_dimp.add_trace(go.Bar(
        x=df_dimp_cnae["if_"], y=df_dimp_cnae["label"],
        name="Inst. Financeira (IF)", orientation="h",
        marker_color="#3b82f6",
        hovertemplate="<b>%{y}</b><br>Inst. Financeira: R$ %{x:,.0f}<extra></extra>",
    ))
    fig_dimp.update_layout(**_lb(
        title="DIMP — Inst. Pagadora × Inst. Financeira por CNAE",
        barmode="group", height=320,
        margin=dict(t=50,b=20,l=110,r=20),
        legend=dict(orientation="h", y=-0.18, x=0),
        xaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickprefix="R$ ", tickformat="~s"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=10)),
    ))
    st.plotly_chart(fig_dimp, use_container_width=True)



# SEÇÃO 5 — Tabela detalhada
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📋 Detalhe</div>
        <div class="coate-section-title">Tabela Completa</div>
        <div class="coate-section-desc">Os filtros do topo já estão aplicados. Use os filtros abaixo para refinar ainda mais.</div>
    </div>
    <hr class="coate-section-divider"/>
    """, unsafe_allow_html=True)

tb1, tb2, tb3, tb4, tb5 = st.columns([1.3, 1.3, 1.5, 1.8, 1.8])
with tb1:
    tab_regime_opts = ["Todos"] + sorted(df["dsc_regime_rec_contribuinte"].dropna().unique().tolist())
    tab_regime = st.selectbox("Regime", tab_regime_opts, key="tab_regime")
with tb2:
    tab_sit_opts = ["Todos"] + sorted(df["dsc_sit_atu_contribuinte"].dropna().unique().tolist())
    tab_sit = st.selectbox("Situação", tab_sit_opts, key="tab_sit")
with tb3:
    tab_cnae_opts = {"Todos": "Todos"}
    for _cod, _desc in sorted(df[["cod_cnae_princ_contribuinte","dsc_cnae_princ_contribuinte"]].drop_duplicates().values.tolist()):
        tab_cnae_opts[str(_cod) + " — " + str(_desc)[:40]] = str(_cod)
    tab_cnae_label = st.selectbox("CNAE", list(tab_cnae_opts.keys()), key="tab_cnae")
    tab_cnae = tab_cnae_opts[tab_cnae_label]
with tb4:
    tab_orgao_opts = ["Todos"] + sorted(df["dsc_orgao_local"].dropna().unique().tolist())
    tab_orgao = st.selectbox("Órgão Local", tab_orgao_opts, key="tab_orgao")
with tb5:
    tab_mun_opts = ["Todos"] + sorted(df["dsc_municipio"].dropna().unique().tolist())
    tab_mun = st.selectbox("Município", tab_mun_opts, key="tab_mun")

busca = st.text_input("🔎 Buscar por município, CNAE, órgão ou regime", placeholder="Digite parte do nome...")

df_tab = df.copy()
if tab_regime != "Todos":
    df_tab = df_tab[df_tab["dsc_regime_rec_contribuinte"] == tab_regime]
if tab_sit != "Todos":
    df_tab = df_tab[df_tab["dsc_sit_atu_contribuinte"] == tab_sit]
if tab_cnae != "Todos":
    df_tab = df_tab[df_tab["cod_cnae_princ_contribuinte"] == tab_cnae]
if tab_orgao != "Todos":
    df_tab = df_tab[df_tab["dsc_orgao_local"] == tab_orgao]
if tab_mun != "Todos":
    df_tab = df_tab[df_tab["dsc_municipio"] == tab_mun]
if busca.strip():
    t = busca.strip().lower()
    df_tab = df_tab[
        df_tab["dsc_municipio"].str.lower().str.contains(t, na=False)
        | df_tab["dsc_cnae_princ_contribuinte"].str.lower().str.contains(t, na=False)
        | df_tab["cod_cnae_princ_contribuinte"].str.lower().str.contains(t, na=False)
        | df_tab["dsc_orgao_local"].str.lower().str.contains(t, na=False)
        | df_tab["dsc_regime_rec_contribuinte"].str.lower().str.contains(t, na=False)
    ]

df_tab = df_tab.copy()
df_tab["dfe"]             = df_tab["nfe"] + df_tab["nfce"] + df_tab["cfe"]
df_tab["dimp_total"]      = df_tab["DIMP_IP"] + df_tab["dimp_if"]
df_tab["omissao_tab"]     = (df_tab["dimp_total"] - df_tab["dfe"]).clip(lower=0)
_taxa_reg = (total_arrec / total_dfe) if total_dfe > 0 else 0
df_tab["vlr_regularizado"] = df_tab["omissao_tab"] * _taxa_reg
df_tab["pot_icms_tab"]    = df_tab["omissao_tab"] * 0.20
df_tab["pot_multa_tab"]   = df_tab["omissao_tab"] * 0.30
_pot_tab = df_tab["pot_icms_tab"] + df_tab["pot_multa_tab"]
df_tab["pct_eco_tab"]     = (df_tab["vlr_regularizado"] / _pot_tab.replace(0, float("nan")) * 100).fillna(0)
df_tab = df_tab.sort_values("vlr_arrecadacao_2025", ascending=False)

LINHAS = 20
total_l = len(df_tab)
total_p = max(1,(total_l+LINHAS-1)//LINHAS)
ci, cp = st.columns([3,1])
with ci: st.caption(f"{_fmt_int(total_l)} registros · {total_p} página(s)")
with cp: pag = st.number_input("Página", min_value=1, max_value=total_p, value=1, step=1)

cols_exib = [c for c in [
    "dsc_orgao_local","dsc_municipio","cod_cnae_princ_contribuinte","dsc_cnae_princ_contribuinte",
    "dsc_regime_rec_contribuinte","dsc_sit_atu_contribuinte",
    "qtd_contribuintes","vlr_arrecadacao_2025",
    "nfe","nfce","cfe","dfe",
    "DIMP_IP","dimp_if","dimp_total",
    "omissao_tab","vlr_regularizado","pot_icms_tab","pot_multa_tab","pct_eco_tab",
] if c in df_tab.columns]

st.dataframe(
    df_tab[cols_exib].iloc[(pag-1)*LINHAS : pag*LINHAS],
    use_container_width=True, hide_index=True,
    column_config={
        "dsc_orgao_local":             st.column_config.TextColumn("Órgão Local", width="medium"),
        "dsc_municipio":               st.column_config.TextColumn("Município"),
        "cod_cnae_princ_contribuinte": st.column_config.TextColumn("CNAE"),
        "dsc_cnae_princ_contribuinte": st.column_config.TextColumn("Descrição CNAE", width="large"),
        "dsc_regime_rec_contribuinte": st.column_config.TextColumn("Regime"),
        "dsc_sit_atu_contribuinte":    st.column_config.TextColumn("Situação"),
        "qtd_contribuintes":           st.column_config.NumberColumn("Estabelecimentos", format="%d"),
        "vlr_arrecadacao_2025":        st.column_config.NumberColumn("Arrecadação 2025 (R$)", format="R$ %,.2f"),
        "nfe":                         st.column_config.NumberColumn("NF-e (R$)", format="R$ %,.2f"),
        "nfce":                        st.column_config.NumberColumn("NFCe (R$)", format="R$ %,.2f"),
        "cfe":                         st.column_config.NumberColumn("CF-e (R$)", format="R$ %,.2f"),
        "dfe":                         st.column_config.NumberColumn("DFe Total (R$)", format="R$ %,.2f"),
        "DIMP_IP":                     st.column_config.NumberColumn("DIMP Inst. Pagadora (R$)", format="R$ %,.2f"),
        "dimp_if":                     st.column_config.NumberColumn("DIMP Inst. Financeira (R$)", format="R$ %,.2f"),
        "dimp_total":                  st.column_config.NumberColumn("DIMP Total (R$)", format="R$ %,.2f"),
        "omissao_tab":                 st.column_config.NumberColumn("Omissão (R$)", format="R$ %,.2f"),
        "vlr_regularizado":            st.column_config.NumberColumn("ICMS se Autorregularizado (R$)", format="R$ %,.2f"),
        "pct_eco_tab":                 st.column_config.NumberColumn("Autoreg. ÷ Pot. Autuação (%)", format="%.1f%%"),
        "pot_icms_tab":                st.column_config.NumberColumn("Pot. ICMS 20% (R$)", format="R$ %,.2f"),
        "pot_multa_tab":               st.column_config.NumberColumn("Pot. Multa 30% (R$)", format="R$ %,.2f"),
    },
)

# ── Nota ──────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-panel">
        <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.7rem;">
            <span style="font-size:1.2rem;">📌</span>
            <span style="font-size:1rem;font-weight:700;color:#f1f5f9;">Nota — Setor de Bares e Restaurantes</span>
        </div>
        <p style="margin:0 0 0.5rem 0;">
            Base composta pelos CNAEs do grupo <strong>5611</strong> — Restaurantes e outros estabelecimentos
            de serviços de alimentação e bebidas — monitorados pelo FAROL no Ceará.
        </p>
        <p style="margin:0 0 0.5rem 0;">
            <strong>DIMP_IP</strong> = valor declarado pela Instituição Pagadora.
            <strong>dimp_if</strong> = valor declarado pela Instituição Financeira.
            A divergência entre os dois campos pode indicar omissão de receitas.
        </p>
        <p style="margin:0;">
            Estabelecimentos <strong>Ativos em Edital</strong> estão sujeitos a processo de exclusão
            por inadimplência ou irregularidade cadastral.
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown(
    '<div class="coate-footer">FAROL · Bares e Restaurantes · Painel COATE · SEFAZ-CE</div>',
    unsafe_allow_html=True)
