import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

from pathlib import Path
import base64 as _b64mod

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from coate_auth import exigir_acesso
from coate_styles import aplicar_estilos

aplicar_estilos()
exigir_acesso("simples")

_DATA_DIR = Path(__file__).resolve().parent.parent / "simples_nacional" / "data"
_DATA_PATH = _DATA_DIR / "Contribuintes.xlsx"

# ── Paletas ────────────────────────────────────────────────────────────────────
CORES_REGIME = {
    "MEI":          "#f59e0b",
    "MICROEMPRESA": "#3b82f6",
    "EPP":          "#22c55e",
}
CORES_SEGMENTO = {
    "COMERCIO VAREJISTA":       "#3b82f6",
    "INDUSTRIA":                "#22c55e",
    "OUTROS SEGMENTOS":         "#94a3b8",
    "SERVICOS DE TRANSPORTE":   "#06b6d4",
    "COMERCIO ATACADISTA":      "#f59e0b",
    "PRODUTOR AGROPECUARIO":    "#84cc16",
    "SERVICOS DE COMUNICACAO":  "#a855f7",
    "CONSTRUCAO CIVIL":         "#f97316",
    "COMBUSTIVEL":              "#ec4899",
}
_PALETTE = ["#3b82f6","#22c55e","#f59e0b","#ef4444","#8b5cf6",
            "#06b6d4","#f97316","#84cc16","#ec4899","#94a3b8"]

# ── Base layout Plotly dark ────────────────────────────────────────────────────
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


# ── Helpers ────────────────────────────────────────────────────────────────────
def _fmt_int(v) -> str:
    try:
        return f"{int(v):,}".replace(",", ".")
    except Exception:
        return "0"


def _fmt_pct(v, d=1) -> str:
    try:
        return f"{float(v):.{d}f}%"
    except Exception:
        return "0%"


# ── Carga ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def _carregar(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, dtype=str)
    str_cols = [
        "dsc_orgao_local", "dsc_municipio", "dsc_cnae_princ_contribuinte",
        "dsc_regime_rec_contribuinte", "dsc_sit_atu_contribuinte",
        "dsc_segmento", "dsc_orgao_monitoramento",
    ]
    for col in str_cols:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.encode("latin1", errors="ignore")
                .str.decode("utf-8", errors="ignore")
                .str.strip()
            )
    df["qtd_contribuintes"] = pd.to_numeric(df["qtd_contribuintes"], errors="coerce").fillna(0).astype(int)
    df["cod_cnae_princ_contribuinte"] = df["cod_cnae_princ_contribuinte"].astype(str).str.strip()
    return df


# ── Ícone ──────────────────────────────────────────────────────────────────────
_sn_icon_path = _os.path.join(_os.path.dirname(__file__), "..", "assets", "simples_nacional_icon.png")
_sn_img = ""
if _os.path.exists(_sn_icon_path):
    with open(_sn_icon_path, "rb") as _f:
        _sn_img = (
            '<img src="data:image/png;base64,' + _b64mod.b64encode(_f.read()).decode() + '" '
            'style="height:56px;border-radius:10px;margin-bottom:0.6rem;display:block;" '
            'alt="Simples Nacional">'
        )

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="coate-hero">
        <div class="coate-hero-kicker">🗂️ Simples Nacional · SEFAZ-CE</div>
    """
    + _sn_img
    + """
        <h1>🏪 Contribuintes do Simples Nacional</h1>
        <p>
            Visão analítica da base de contribuintes ativos no Simples Nacional no Ceará.
            Explore a distribuição por regime, segmento econômico, município, órgão local
            e atividade econômica (CNAE).
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Verificação do arquivo ─────────────────────────────────────────────────────
if not _DATA_PATH.exists():
    st.error(
        "Arquivo de dados não encontrado. Esperado em: "
        + str(_DATA_PATH)
    )
    st.stop()

df_full = _carregar(str(_DATA_PATH))

# ── Filtros ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
f1, f2, f3, f4, f5 = st.columns([1.4, 1.4, 1.8, 1.8, 1.8])

with f1:
    opcoes_regime = ["Todos", "MEI", "ME + EPP", "MICROEMPRESA", "EPP"]
    regime_sel = st.selectbox("Regime", opcoes_regime, index=0)

with f2:
    opcoes_sit = ["Todos", "ATIVO", "ATIVO (EM EDITAL)"]
    sit_sel = st.selectbox("Situação", opcoes_sit, index=0)

with f3:
    segmentos_disp = sorted(df_full["dsc_segmento"].dropna().unique().tolist())
    seg_sel = st.multiselect("Segmento", segmentos_disp, placeholder="Todos os segmentos")

with f4:
    orgaos_disp = ["Todos"] + sorted(df_full["dsc_orgao_local"].dropna().unique().tolist())
    orgao_sel = st.selectbox("Órgão Local", orgaos_disp, index=0)

with f5:
    municipios_disp = ["Todos"] + sorted(df_full["dsc_municipio"].dropna().unique().tolist())
    mun_sel = st.selectbox("Município", municipios_disp, index=0)

# ── Aplicar filtros ────────────────────────────────────────────────────────────
df = df_full.copy()

if regime_sel == "MEI":
    df = df[df["dsc_regime_rec_contribuinte"] == "MEI"]
elif regime_sel == "ME + EPP":
    df = df[df["dsc_regime_rec_contribuinte"].isin(["MICROEMPRESA", "EPP"])]
elif regime_sel == "MICROEMPRESA":
    df = df[df["dsc_regime_rec_contribuinte"] == "MICROEMPRESA"]
elif regime_sel == "EPP":
    df = df[df["dsc_regime_rec_contribuinte"] == "EPP"]

if sit_sel != "Todos":
    df = df[df["dsc_sit_atu_contribuinte"] == sit_sel]

if seg_sel:
    df = df[df["dsc_segmento"].isin(seg_sel)]

if orgao_sel != "Todos":
    df = df[df["dsc_orgao_local"] == orgao_sel]

if mun_sel != "Todos":
    df = df[df["dsc_municipio"] == mun_sel]

if df.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados.")
    st.stop()

# ── KPIs ───────────────────────────────────────────────────────────────────────
total_contrib  = df["qtd_contribuintes"].sum()
total_full     = df_full["qtd_contribuintes"].sum()
pct_total      = total_contrib / total_full * 100 if total_full else 0
total_mun      = df["dsc_municipio"].nunique()
total_cnaes    = df["cod_cnae_princ_contribuinte"].nunique()
em_edital      = df[df["dsc_sit_atu_contribuinte"] == "ATIVO (EM EDITAL)"]["qtd_contribuintes"].sum()
pct_edital     = em_edital / total_contrib * 100 if total_contrib else 0

mei_qtd    = df[df["dsc_regime_rec_contribuinte"] == "MEI"]["qtd_contribuintes"].sum()
me_qtd     = df[df["dsc_regime_rec_contribuinte"] == "MICROEMPRESA"]["qtd_contribuintes"].sum()
epp_qtd    = df[df["dsc_regime_rec_contribuinte"] == "EPP"]["qtd_contribuintes"].sum()
pct_mei    = mei_qtd / total_contrib * 100 if total_contrib else 0
pct_me     = me_qtd  / total_contrib * 100 if total_contrib else 0
pct_epp    = epp_qtd / total_contrib * 100 if total_contrib else 0

st.markdown("<br>", unsafe_allow_html=True)
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(
        '<div class="coate-kpi-card accent-primary">'
        '<div class="coate-kpi-label">Contribuintes</div>'
        '<div class="coate-kpi-value">' + _fmt_int(total_contrib) + '</div>'
        '<div class="coate-kpi-help">' + _fmt_pct(pct_total) + ' do total estadual</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        '<div class="coate-kpi-card accent-warning">'
        '<div class="coate-kpi-label">MEI</div>'
        '<div class="coate-kpi-value">' + _fmt_int(mei_qtd) + '</div>'
        '<div class="coate-kpi-help">' + _fmt_pct(pct_mei) + ' do filtro atual</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        '<div class="coate-kpi-card accent-info">'
        '<div class="coate-kpi-label">Microempresa</div>'
        '<div class="coate-kpi-value">' + _fmt_int(me_qtd) + '</div>'
        '<div class="coate-kpi-help">' + _fmt_pct(pct_me) + ' do filtro atual</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        '<div class="coate-kpi-card" style="border-left:3px solid #22c55e;">'
        '<div class="coate-kpi-label">EPP</div>'
        '<div class="coate-kpi-value">' + _fmt_int(epp_qtd) + '</div>'
        '<div class="coate-kpi-help">' + _fmt_pct(pct_epp) + ' do filtro atual</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with k5:
    st.markdown(
        '<div class="coate-kpi-card accent-danger">'
        '<div class="coate-kpi-label">Em Edital</div>'
        '<div class="coate-kpi-value">' + _fmt_int(em_edital) + '</div>'
        '<div class="coate-kpi-help">' + _fmt_pct(pct_edital) + ' do filtro atual</div>'
        '</div>',
        unsafe_allow_html=True,
    )

# ── Seção 1 — Regime e Segmento ────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📊 Composição</div>
        <div class="coate-section-title">Regime e Segmento Econômico</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

g1a, g1b = st.columns([2, 1])

with g1a:
    # Barras empilhadas: segmento × regime
    df_seg_reg = (
        df.groupby(["dsc_segmento", "dsc_regime_rec_contribuinte"])["qtd_contribuintes"]
        .sum()
        .reset_index()
    )
    df_seg_total = df_seg_reg.groupby("dsc_segmento")["qtd_contribuintes"].sum().sort_values(ascending=True)
    ordem_seg = df_seg_total.index.tolist()

    fig_seg = go.Figure()
    for regime in ["MEI", "MICROEMPRESA", "EPP"]:
        sub = df_seg_reg[df_seg_reg["dsc_regime_rec_contribuinte"] == regime]
        sub = sub.set_index("dsc_segmento").reindex(ordem_seg).fillna(0).reset_index()
        fig_seg.add_trace(go.Bar(
            name=regime,
            y=sub["dsc_segmento"],
            x=sub["qtd_contribuintes"],
            orientation="h",
            marker_color=CORES_REGIME.get(regime, "#94a3b8"),
            hovertemplate="<b>%{y}</b><br>" + regime + ": %{x:,}<extra></extra>",
        ))
    fig_seg.update_layout(
        **_lb(
            title="Contribuintes por Segmento e Regime",
            barmode="stack",
            height=400,
            margin=dict(t=50, b=20, l=220, r=60),
            legend=dict(orientation="h", y=-0.08, x=0),
            xaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=10)),
        )
    )
    st.plotly_chart(fig_seg, use_container_width=True)

with g1b:
    # Donut: participação por regime
    df_regime = df.groupby("dsc_regime_rec_contribuinte")["qtd_contribuintes"].sum().reset_index()
    fig_donut = go.Figure(go.Pie(
        labels=df_regime["dsc_regime_rec_contribuinte"].tolist(),
        values=df_regime["qtd_contribuintes"].tolist(),
        hole=0.52,
        marker_colors=[CORES_REGIME.get(r, "#94a3b8") for r in df_regime["dsc_regime_rec_contribuinte"]],
        textinfo="label+percent",
        hovertemplate="%{label}<br>%{value:,} contribuintes<br>%{percent}<extra></extra>",
    ))
    fig_donut.update_layout(
        **_lb(
            title="Participação por Regime",
            showlegend=False,
            height=400,
        )
    )
    st.plotly_chart(fig_donut, use_container_width=True)

# ── Seção 2 — Distribuição Geográfica ─────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">🗺️ Geografia</div>
        <div class="coate-section-title">Distribuição Geográfica e por Órgão</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

g2a, g2b = st.columns(2)

with g2a:
    df_mun = (
        df.groupby("dsc_municipio")["qtd_contribuintes"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
        .reset_index()
    )
    df_mun = df_mun.sort_values("qtd_contribuintes", ascending=True)
    max_mun = df_mun["qtd_contribuintes"].max()

    fig_mun = go.Figure(go.Bar(
        x=df_mun["qtd_contribuintes"],
        y=df_mun["dsc_municipio"],
        orientation="h",
        marker=dict(
            color=df_mun["qtd_contribuintes"],
            colorscale=[[0, "#1e3a5f"], [1, "#3b82f6"]],
            showscale=False,
        ),
        text=df_mun["qtd_contribuintes"].apply(_fmt_int),
        textposition="outside",
        textfont=dict(size=10, color="#94a3b8"),
        hovertemplate="<b>%{y}</b><br>%{x:,} contribuintes<extra></extra>",
    ))
    fig_mun.update_layout(
        **_lb(
            title="Top 20 Municípios por Contribuintes",
            height=520,
            margin=dict(t=50, b=20, l=160, r=80),
            xaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=10)),
        )
    )
    st.plotly_chart(fig_mun, use_container_width=True)

with g2b:
    df_org = (
        df.groupby("dsc_orgao_local")["qtd_contribuintes"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    df_org = df_org.sort_values("qtd_contribuintes", ascending=True)

    fig_org = go.Figure(go.Bar(
        x=df_org["qtd_contribuintes"],
        y=df_org["dsc_orgao_local"],
        orientation="h",
        marker=dict(
            color=df_org["qtd_contribuintes"],
            colorscale=[[0, "#1c3b2a"], [1, "#22c55e"]],
            showscale=False,
        ),
        text=df_org["qtd_contribuintes"].apply(_fmt_int),
        textposition="outside",
        textfont=dict(size=10, color="#94a3b8"),
        hovertemplate="<b>%{y}</b><br>%{x:,} contribuintes<extra></extra>",
    ))
    fig_org.update_layout(
        **_lb(
            title="Contribuintes por Órgão Local",
            height=520,
            margin=dict(t=50, b=20, l=260, r=80),
            xaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=9)),
        )
    )
    st.plotly_chart(fig_org, use_container_width=True)

# ── Seção 3 — Análise por CNAE ─────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">🏭 Atividade Econômica</div>
        <div class="coate-section-title">Análise por CNAE</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

# Treemap
df_cnae_tree = (
    df.groupby(["dsc_segmento", "cod_cnae_princ_contribuinte", "dsc_cnae_princ_contribuinte"])["qtd_contribuintes"]
    .sum()
    .reset_index()
    .sort_values("qtd_contribuintes", ascending=False)
    .head(50)
)
df_cnae_tree["cnae_label"] = df_cnae_tree["cod_cnae_princ_contribuinte"] + " — " + df_cnae_tree["dsc_cnae_princ_contribuinte"].str[:40]

# px.treemap monta a hierarquia corretamente — sem risco de nós pai ausentes
fig_tree = px.treemap(
    df_cnae_tree,
    path=["dsc_segmento", "cnae_label"],
    values="qtd_contribuintes",
    color="dsc_segmento",
    color_discrete_map=CORES_SEGMENTO,
    custom_data=["qtd_contribuintes", "dsc_segmento"],
)
fig_tree.update_traces(
    textinfo="label+value",
    textfont=dict(size=11, color="#f1f5f9"),
    hovertemplate="<b>%{label}</b><br>%{value:,} contribuintes<br>%{percentParent:.1%} do segmento<extra></extra>",
    marker=dict(line=dict(width=1, color="#0f172a")),
)
fig_tree.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#cbd5e1", family="sans-serif"),
    hoverlabel=dict(bgcolor="#1e293b", font_color="#f1f5f9", bordercolor="#334155"),
    title="Top 50 CNAEs por Contribuintes — agrupados por Segmento",
    height=560,
    margin=dict(t=50, b=10, l=10, r=10),
)
st.plotly_chart(fig_tree, use_container_width=True)

# Barras: top 15 CNAEs com breakdown regime
df_cnae_bar = (
    df.groupby(["cod_cnae_princ_contribuinte", "dsc_cnae_princ_contribuinte", "dsc_regime_rec_contribuinte"])["qtd_contribuintes"]
    .sum()
    .reset_index()
)
df_cnae_total = (
    df_cnae_bar.groupby("cod_cnae_princ_contribuinte")["qtd_contribuintes"]
    .sum()
    .sort_values(ascending=False)
    .head(15)
)
top15_cnaes = df_cnae_total.index.tolist()
df_cnae_bar = df_cnae_bar[df_cnae_bar["cod_cnae_princ_contribuinte"].isin(top15_cnaes)].copy()

# Monta label CNAE
df_labels = df_cnae_bar[["cod_cnae_princ_contribuinte","dsc_cnae_princ_contribuinte"]].drop_duplicates()
df_labels["label"] = df_labels["cod_cnae_princ_contribuinte"] + " — " + df_labels["dsc_cnae_princ_contribuinte"].str[:40]
label_map = df_labels.set_index("cod_cnae_princ_contribuinte")["label"].to_dict()
df_cnae_bar["cnae_label"] = df_cnae_bar["cod_cnae_princ_contribuinte"].map(label_map)

ordem_cnae = (
    df_cnae_bar.groupby("cnae_label")["qtd_contribuintes"]
    .sum()
    .sort_values(ascending=True)
    .index.tolist()
)

fig_cnae = go.Figure()
for regime in ["MEI", "MICROEMPRESA", "EPP"]:
    sub = df_cnae_bar[df_cnae_bar["dsc_regime_rec_contribuinte"] == regime]
    sub = sub.set_index("cnae_label").reindex(ordem_cnae).fillna(0).reset_index()
    fig_cnae.add_trace(go.Bar(
        name=regime,
        y=sub["cnae_label"],
        x=sub["qtd_contribuintes"],
        orientation="h",
        marker_color=CORES_REGIME.get(regime, "#94a3b8"),
        hovertemplate="<b>%{y}</b><br>" + regime + ": %{x:,}<extra></extra>",
    ))
fig_cnae.update_layout(
    **_lb(
        title="Top 15 CNAEs — Breakdown por Regime",
        barmode="stack",
        height=500,
        margin=dict(t=50, b=20, l=340, r=60),
        legend=dict(orientation="h", y=-0.08, x=0),
        xaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=10)),
    )
)
st.plotly_chart(fig_cnae, use_container_width=True)

# ── Seção 4 — Órgão Local × Monitoramento ─────────────────────────────────────
if "dsc_orgao_monitoramento" in df.columns:
    df_div = df[df["dsc_orgao_local"] != df["dsc_orgao_monitoramento"]].copy()
    if not df_div.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="coate-section">
                <div class="coate-section-super">🔀 Redistribuição</div>
                <div class="coate-section-title">Órgão Local × Órgão de Monitoramento</div>
                <div class="coate-section-desc">
                    Contribuintes cujo órgão de monitoramento difere do órgão local —
                    indica redistribuição de carga entre núcleos.
                </div>
            </div>
            <hr class="coate-section-divider"/>
            """,
            unsafe_allow_html=True,
        )

        df_cross = (
            df_div.groupby(["dsc_orgao_local", "dsc_orgao_monitoramento"])["qtd_contribuintes"]
            .sum()
            .reset_index()
            .sort_values("qtd_contribuintes", ascending=False)
            .head(30)
        )

        # Heatmap
        pivot = df_cross.pivot_table(
            index="dsc_orgao_local",
            columns="dsc_orgao_monitoramento",
            values="qtd_contribuintes",
            fill_value=0,
        )

        fig_heat = go.Figure(go.Heatmap(
            z=pivot.values.tolist(),
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[[0, "#0f172a"], [0.5, "#1e40af"], [1, "#3b82f6"]],
            hovertemplate="Local: <b>%{y}</b><br>Monitoramento: <b>%{x}</b><br>%{z:,} contribuintes<extra></extra>",
            text=[[str(int(v)) if v > 0 else "" for v in row] for row in pivot.values],
            texttemplate="%{text}",
            textfont=dict(size=9),
        ))
        fig_heat.update_layout(
            **_lb(
                title="Redistribuição: Órgão Local → Órgão de Monitoramento (contribuintes divergentes)",
                height=max(350, len(pivot) * 40 + 100),
                margin=dict(t=60, b=120, l=260, r=20),
                xaxis=dict(tickangle=-40, tickfont=dict(size=9)),
                yaxis=dict(tickfont=dict(size=9)),
            )
        )
        st.plotly_chart(fig_heat, use_container_width=True)

# ── Seção 5 — Tabela detalhada ─────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📋 Detalhe</div>
        <div class="coate-section-title">Tabela de Contribuintes</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

busca = st.text_input(
    "🔎 Buscar por município, CNAE ou órgão",
    placeholder="Digite parte do nome...",
)

df_tab = df.copy()
if busca.strip():
    t = busca.strip().lower()
    df_tab = df_tab[
        df_tab["dsc_municipio"].str.lower().str.contains(t, na=False)
        | df_tab["dsc_cnae_princ_contribuinte"].str.lower().str.contains(t, na=False)
        | df_tab["cod_cnae_princ_contribuinte"].str.lower().str.contains(t, na=False)
        | df_tab["dsc_orgao_local"].str.lower().str.contains(t, na=False)
    ]

df_tab = df_tab.sort_values("qtd_contribuintes", ascending=False)

LINHAS_POR_PAG = 20
total_linhas = len(df_tab)
total_pags = max(1, (total_linhas + LINHAS_POR_PAG - 1) // LINHAS_POR_PAG)

col_info, col_pag = st.columns([3, 1])
with col_info:
    st.caption(f"{_fmt_int(total_linhas)} registros · {total_pags} página(s)")
with col_pag:
    pag_atual = st.number_input("Página", min_value=1, max_value=total_pags, value=1, step=1)

inicio = (pag_atual - 1) * LINHAS_POR_PAG
fim = inicio + LINHAS_POR_PAG

colunas_exib = [c for c in [
    "dsc_orgao_local", "dsc_municipio",
    "cod_cnae_princ_contribuinte", "dsc_cnae_princ_contribuinte",
    "dsc_regime_rec_contribuinte", "dsc_sit_atu_contribuinte",
    "dsc_segmento", "dsc_orgao_monitoramento", "qtd_contribuintes",
] if c in df_tab.columns]

st.dataframe(
    df_tab[colunas_exib].iloc[inicio:fim],
    use_container_width=True,
    hide_index=True,
    column_config={
        "dsc_orgao_local":               st.column_config.TextColumn("Órgão Local", width="medium"),
        "dsc_municipio":                 st.column_config.TextColumn("Município"),
        "cod_cnae_princ_contribuinte":   st.column_config.TextColumn("Cód. CNAE"),
        "dsc_cnae_princ_contribuinte":   st.column_config.TextColumn("Descrição CNAE", width="large"),
        "dsc_regime_rec_contribuinte":   st.column_config.TextColumn("Regime"),
        "dsc_sit_atu_contribuinte":      st.column_config.TextColumn("Situação"),
        "dsc_segmento":                  st.column_config.TextColumn("Segmento"),
        "dsc_orgao_monitoramento":       st.column_config.TextColumn("Órgão Monitoramento", width="medium"),
        "qtd_contribuintes":             st.column_config.NumberColumn("Contribuintes", format="%d"),
    },
)

# ── Nota metodológica ──────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-panel">
        <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.7rem;">
            <span style="font-size:1.2rem;">📌</span>
            <span style="font-size:1rem;font-weight:700;color:#f1f5f9;">Nota metodológica — Base de Contribuintes</span>
        </div>
        <p style="margin:0 0 0.5rem 0;">
            A base contempla contribuintes optantes pelo <strong>Simples Nacional</strong> com situação
            cadastral ativa no Ceará, agrupados por órgão local, município, CNAE principal,
            regime de recolhimento e segmento econômico.
        </p>
        <p style="margin:0 0 0.5rem 0;">
            O filtro <strong>ME + EPP</strong> agrupa Microempresa (ME) e Empresa de Pequeno Porte (EPP),
            permitindo comparar esse conjunto com o segmento MEI de forma direta.
        </p>
        <p style="margin:0;">
            Contribuintes classificados como <strong>Ativo em Edital</strong> estão sujeitos a processo
            de exclusão do Simples Nacional por inadimplência ou irregularidade cadastral.
            O heatmap de redistribuição exibe apenas os registros onde o órgão de monitoramento
            difere do órgão local, sinalizando delegação de acompanhamento entre núcleos.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="coate-footer">Simples Nacional · Contribuintes · Painel COATE · SEFAZ-CE</div>',
    unsafe_allow_html=True,
)
