import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from coate_styles import aplicar_estilos
from coate_auth import exigir_acesso

aplicar_estilos()
exigir_acesso("simples")

_DATA_PATH = Path(__file__).resolve().parent.parent / "simples_nacional" / "data" / "Eventos a notificar.xlsx"

@st.cache_data(ttl=3600)
def _carregar_dados(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="default_1")
    df["dat_geracao"]        = pd.to_datetime(df["dat_geracao"], errors="coerce")
    df["vlr_min_regularizar"]= pd.to_numeric(df["vlr_min_regularizar"], errors="coerce")
    df["qt_contribuintes"]   = pd.to_numeric(df["qt_contribuintes"], errors="coerce")
    df["perc_contribuintes"] = pd.to_numeric(df["perc_contribuintes"], errors="coerce")
    df["perc_valor"]         = pd.to_numeric(df["perc_valor"], errors="coerce")
    df["eh_total"]           = df["faixa"].str.strip().str.lower() == "total geral"
    return df

def _fmt_moeda(v: float) -> str:
    if v >= 1_000_000_000:
        return f"R$ {v/1_000_000_000:.2f} Bi"
    if v >= 1_000_000:
        return f"R$ {v/1_000_000:.1f} Mi"
    return f"R$ {v:,.0f}".replace(",", ".")

def _fmt_int(v) -> str:
    return f"{int(v):,}".replace(",", ".")

CORES_PERIODO = {"2024": "#3b82f6", "2025": "#22c55e", "2024-2025": "#f59e0b"}

# Ícone PNG
import base64 as _b64mod
_sn_icon_path = _os.path.join(_os.path.dirname(__file__), '..', 'assets', 'simples_nacional_icon.png')
_sn_img = ""
if _os.path.exists(_sn_icon_path):
    with open(_sn_icon_path, "rb") as _f:
        _sn_img = f'<img src="data:image/png;base64,{_b64mod.b64encode(_f.read()).decode()}" style="height:56px;border-radius:10px;margin-bottom:0.6rem;display:block;" alt="Simples Nacional">'

# HERO
st.markdown(
    f"""
    <div class="coate-hero">
        <div class="coate-hero-kicker">🗂️ Simples Nacional · SEFAZ-CE</div>
        {_sn_img}
        <h1>🔔 Notificação de Eventos</h1>
        <p>Monitoramento de contribuintes com pendências de regularização —
        distribuição por faixa de receita bruta, valor mínimo a regularizar e potencial de notificação.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not _DATA_PATH.exists():
    st.error(f"Arquivo não encontrado: `{_DATA_PATH}`")
    st.stop()

df_full = _carregar_dados(str(_DATA_PATH))
data_ref = df_full["dat_geracao"].dropna().iloc[0].strftime("%d/%m/%Y") if not df_full["dat_geracao"].dropna().empty else "N/D"
periodos_disp = sorted(df_full["periodo"].unique())

# FILTRO
col_f, _ = st.columns([2, 4])
with col_f:
    periodo_sel = st.selectbox(
        "Período de referência",
        options=periodos_disp,
        index=periodos_disp.index("2024-2025") if "2024-2025" in periodos_disp else 0,
    )

df        = df_full[df_full["periodo"] == periodo_sel].copy()
df_faixas = df[~df["eh_total"]].copy()
df_total  = df[df["eh_total"]].copy()

tot_contribuintes = int(df_total["qt_contribuintes"].iloc[0]) if not df_total.empty else int(df_faixas["qt_contribuintes"].sum())
tot_valor         = float(df_total["vlr_min_regularizar"].iloc[0]) if not df_total.empty else float(df_faixas["vlr_min_regularizar"].sum())
n_faixas          = df_faixas["faixa"].nunique()

# KPIs
st.markdown(
    f"""
    <div class="coate-section" style="margin-top:1.2rem;">
        <div class="coate-section-super">📊 KPIs · {periodo_sel}</div>
        <div class="coate-section-title">Visão Consolidada</div>
        <div class="coate-section-desc">Gerado em {data_ref}</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f"""
    <div class="coate-kpi-card accent-danger">
        <div class="coate-kpi-top">
            <div class="coate-kpi-label">Contribuintes a Notificar</div>
            <div class="coate-kpi-icon">🏢</div>
        </div>
        <div class="coate-kpi-value">{_fmt_int(tot_contribuintes)}</div>
        <div class="coate-kpi-delta delta-danger">⚠ Pendentes de regularização</div>
        <div class="coate-kpi-help">Total de CNPJs com eventos pendentes no período {periodo_sel}.</div>
    </div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="coate-kpi-card accent-warning">
        <div class="coate-kpi-top">
            <div class="coate-kpi-label">Valor Mínimo a Regularizar</div>
            <div class="coate-kpi-icon">💰</div>
        </div>
        <div class="coate-kpi-value">{_fmt_moeda(tot_valor)}</div>
        <div class="coate-kpi-delta delta-warning">Estimativa de débitos</div>
        <div class="coate-kpi-help">Soma do valor mínimo de regularização em todas as faixas.</div>
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="coate-kpi-card accent-info">
        <div class="coate-kpi-top">
            <div class="coate-kpi-label">Faixas de Receita</div>
            <div class="coate-kpi-icon">📊</div>
        </div>
        <div class="coate-kpi-value">{n_faixas}</div>
        <div class="coate-kpi-delta delta-info">Segmentos monitorados</div>
        <div class="coate-kpi-help">Faixas de receita bruta anual com contribuintes pendentes.</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# GRÁFICOS
st.markdown("""
<div class="coate-section">
    <div class="coate-section-super">📈 Distribuição</div>
    <div class="coate-section-title">Contribuintes e Valor por Faixa</div>
</div>
<hr class="coate-section-divider"/>
""", unsafe_allow_html=True)

df_faixas["faixa_curta"] = "F" + df_faixas["faixa"].str.extract(r"^(\d+)")[0].fillna("?")
_cor = CORES_PERIODO.get(str(periodo_sel), "#3b82f6")

_layout_base = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#cbd5e1", font_family="Segoe UI", showlegend=False,
    margin=dict(t=40, b=10, l=10, r=10),
    xaxis=dict(tickangle=-20, gridcolor="rgba(148,163,184,0.08)"),
    yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
)

g1, g2 = st.columns(2)

with g1:
    fig_qt = px.bar(df_faixas, x="faixa_curta", y="qt_contribuintes",
                    text="qt_contribuintes", title="Contribuintes por Faixa",
                    color_discrete_sequence=[_cor], template="plotly_dark")
    fig_qt.update_traces(texttemplate="%{text:,}", textposition="outside", marker_line_width=0)
    fig_qt.update_layout(**_layout_base)
    st.plotly_chart(fig_qt, use_container_width=True)

with g2:
    fig_vl = px.bar(df_faixas, x="faixa_curta", y="vlr_min_regularizar",
                    text="perc_valor", title="Valor a Regularizar por Faixa (% do total)",
                    color_discrete_sequence=["#f59e0b"], template="plotly_dark")
    fig_vl.update_traces(texttemplate="%{text:.1f}%", textposition="outside", marker_line_width=0)
    fig_vl.update_layout(**{**_layout_base, "yaxis": dict(tickformat=",.0f", gridcolor="rgba(148,163,184,0.08)")})
    st.plotly_chart(fig_vl, use_container_width=True)

# TABELA
st.markdown("""
<div class="coate-section">
    <div class="coate-section-super">📋 Detalhe</div>
    <div class="coate-section-title">Tabela por Faixa de Receita</div>
</div>
<hr class="coate-section-divider"/>
""", unsafe_allow_html=True)

df_exib = df_faixas[["faixa", "qt_contribuintes", "perc_contribuintes", "vlr_min_regularizar", "perc_valor"]].copy()
if not df_total.empty:
    df_exib = pd.concat([df_exib, df_total[df_exib.columns]], ignore_index=True)

st.dataframe(
    df_exib, use_container_width=True, hide_index=True,
    column_config={
        "faixa":               st.column_config.TextColumn("Faixa de Receita Bruta"),
        "qt_contribuintes":    st.column_config.NumberColumn("Contribuintes", format="%d"),
        "perc_contribuintes":  st.column_config.NumberColumn("% Contribuintes", format="%.2f%%"),
        "vlr_min_regularizar": st.column_config.NumberColumn("Valor Mín. a Regularizar (R$)", format="R$ %,.2f"),
        "perc_valor":          st.column_config.ProgressColumn("% do Valor Total", format="%.1f%%", min_value=0, max_value=100),
    },
)

# COMPARATIVO ENTRE PERÍODOS
if len(periodos_disp) > 1:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="coate-section">
        <div class="coate-section-super">🔄 Comparativo</div>
        <div class="coate-section-title">Contribuintes e Valor por Período</div>
    </div>
    <hr class="coate-section-divider"/>
    """, unsafe_allow_html=True)

    df_comp = (
        df_full[df_full["eh_total"]]
        .groupby("periodo", as_index=False)
        .agg(qt=("qt_contribuintes", "sum"), vlr=("vlr_min_regularizar", "sum"))
        .sort_values("periodo")
    )

    c1, c2 = st.columns(2)
    with c1:
        fig_c1 = go.Figure()
        for _, row in df_comp.iterrows():
            fig_c1.add_trace(go.Bar(
                x=[str(row["periodo"])], y=[row["qt"]],
                name=str(row["periodo"]),
                marker_color=CORES_PERIODO.get(str(row["periodo"]), "#94a3b8"),
                text=[_fmt_int(row["qt"])], textposition="outside",
            ))
        fig_c1.update_layout(**{**_layout_base, "title": "Contribuintes por Período"})
        st.plotly_chart(fig_c1, use_container_width=True)

    with c2:
        fig_c2 = go.Figure()
        for _, row in df_comp.iterrows():
            fig_c2.add_trace(go.Bar(
                x=[str(row["periodo"])], y=[row["vlr"]],
                name=str(row["periodo"]),
                marker_color=CORES_PERIODO.get(str(row["periodo"]), "#94a3b8"),
                text=[_fmt_moeda(row["vlr"])], textposition="outside",
            ))
        fig_c2.update_layout(**{**_layout_base, "title": "Valor a Regularizar por Período",
                                "yaxis": dict(tickformat=",.0f", gridcolor="rgba(148,163,184,0.08)")})
        st.plotly_chart(fig_c2, use_container_width=True)

st.markdown(
    f'<div class="coate-footer">Simples Nacional · Notificação de Eventos · Painel COATE · SEFAZ-CE · Dados gerados em {data_ref}</div>',
    unsafe_allow_html=True,
)
