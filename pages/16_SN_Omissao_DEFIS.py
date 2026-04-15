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
exigir_acesso("simples")

_DATA_DIR = Path(__file__).resolve().parent.parent / "simples_nacional" / "data"
_REQUIRED_COLUMNS = {
    "dat_geracao",
    "periodo",
    "qt_cnpj_base",
    "perc_cnpj_base",
    "qt_declaracoes",
    "perc_declaracoes",
}
CORES_PERIODO = {
    "2021": "#6366f1",
    "2022": "#3b82f6",
    "2023": "#06b6d4",
    "2024": "#22c55e",
    "2025": "#f59e0b",
    "2021-2025": "#ef4444",
}
ORDEM_PERIODO = {"2021": 1, "2022": 2, "2023": 3, "2024": 4, "2025": 5, "2021-2025": 6}


def _resolver_arquivo_dados() -> Path | None:
    candidatos = [
        _DATA_DIR / "Omissão_DEFIS.xlsx",
        _DATA_DIR / "Omissao_DEFIS.xlsx",
        _DATA_DIR / "Omissão DEFIS.xlsx",
    ]
    for caminho in candidatos:
        if caminho.exists():
            return caminho
    for caminho in sorted(_DATA_DIR.glob("*.xlsx")):
        nome = caminho.name.lower()
        if "omiss" in nome and "defis" in nome:
            return caminho
    return None


_DATA_PATH = _resolver_arquivo_dados()


@st.cache_data(ttl=3600)
def _carregar_dados(path: str) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    sheet_name = "default_1" if "default_1" in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet_name)

    colunas_faltantes = _REQUIRED_COLUMNS.difference(df.columns)
    if colunas_faltantes:
        faltantes = ", ".join(sorted(colunas_faltantes))
        raise ValueError(f"A planilha não contém as colunas obrigatórias: {faltantes}.")

    df = df.copy()
    df["dat_geracao"] = pd.to_datetime(df["dat_geracao"], errors="coerce")
    df["qt_cnpj_base"] = pd.to_numeric(df["qt_cnpj_base"], errors="coerce").fillna(0)
    df["perc_cnpj_base"] = pd.to_numeric(df["perc_cnpj_base"], errors="coerce").fillna(0)
    df["qt_declaracoes"] = pd.to_numeric(df["qt_declaracoes"], errors="coerce").fillna(0)
    df["perc_declaracoes"] = pd.to_numeric(df["perc_declaracoes"], errors="coerce").fillna(0)
    df["periodo"] = df["periodo"].astype(str).str.strip()
    df["eh_total"] = df["periodo"] == "2021-2025"
    df["ordem"] = df["periodo"].map(ORDEM_PERIODO).fillna(99)
    return df.sort_values(["ordem", "periodo"])


def _fmt_int(v) -> str:
    try:
        return f"{int(v):,}".replace(",", ".")
    except Exception:
        return "0"


def _fmt_pct(v: float, digits: int = 1) -> str:
    try:
        return f"{float(v):.{digits}f}%"
    except Exception:
        return "0,0%"


def _layout_plot(base: dict, **overrides) -> dict:
    layout = dict(base)
    if "xaxis" in base:
        layout["xaxis"] = dict(base["xaxis"])
    if "yaxis" in base:
        layout["yaxis"] = dict(base["yaxis"])
    if "xaxis" in overrides:
        layout["xaxis"] = {**layout.get("xaxis", {}), **overrides.pop("xaxis")}
    if "yaxis" in overrides:
        layout["yaxis"] = {**layout.get("yaxis", {}), **overrides.pop("yaxis")}
    layout.update(overrides)
    return layout


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
        <h1>📋 Omissão DEFIS</h1>
        <p>
            Monitoramento de contribuintes e declarações com omissão na DEFIS,
            com visão consolidada do período 2021–2025 e comparativo anual.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Carga de dados ─────────────────────────────────────────────────────────────
if _DATA_PATH is None:
    arquivos_disponiveis = (
        ", ".join(sorted(p.name for p in _DATA_DIR.glob("*.xlsx")))
        or "nenhum arquivo .xlsx localizado"
    )
    st.error(
        "Não foi possível localizar a planilha da página. "
        "Arquivos encontrados em `simples_nacional/data`: " + arquivos_disponiveis + "."
    )
    st.stop()

try:
    df_full = _carregar_dados(str(_DATA_PATH))
except Exception as exc:
    st.error("Erro ao carregar a planilha `" + _DATA_PATH.name + "`: " + str(exc))
    st.stop()

if df_full.empty:
    st.warning("A planilha foi localizada, mas não contém registros para exibição.")
    st.stop()

data_ref = (
    df_full["dat_geracao"].dropna().iloc[0].strftime("%d/%m/%Y")
    if not df_full["dat_geracao"].dropna().empty
    else "N/D"
)

df_total = df_full[df_full["eh_total"]].copy()
df_anuais = df_full[~df_full["eh_total"]].copy()

# ── Alerta de fonte ────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="coate-alert alert-info" style="margin-top:0.5rem;margin-bottom:1rem;">
        <div class="coate-alert-icon">ℹ️</div>
        <div class="coate-alert-body">
            Fonte: <strong>"""
    + _DATA_PATH.name
    + """</strong> · Dados gerados em <strong>"""
    + data_ref
    + """</strong>.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── KPIs consolidados (2021-2025) ──────────────────────────────────────────────
tot_cnpj = int(df_total["qt_cnpj_base"].iloc[0]) if not df_total.empty else int(df_anuais["qt_cnpj_base"].sum())
tot_declaracoes = int(df_total["qt_declaracoes"].iloc[0]) if not df_total.empty else int(df_anuais["qt_declaracoes"].sum())
n_anos = int(df_anuais["periodo"].nunique())

# Soma anual de CNPJs (para a nota metodológica — calculada dinamicamente)
soma_cnpj_anual = int(df_anuais["qt_cnpj_base"].sum())
reincidencia = soma_cnpj_anual - tot_cnpj

periodo_top_cnpj = (
    df_anuais.loc[df_anuais["qt_cnpj_base"].idxmax()]
    if not df_anuais.empty
    else None
)
periodo_top_decl = (
    df_anuais.loc[df_anuais["qt_declaracoes"].idxmax()]
    if not df_anuais.empty
    else None
)

st.markdown(
    """
    <div class="coate-section" style="margin-top:1.2rem;">
        <div class="coate-section-super">📊 KPIs · 2021–2025 (Consolidado)</div>
        <div class="coate-section-title">Visão Geral da Omissão</div>
        <div class="coate-section-desc">Gerado em """
    + data_ref
    + """</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">CNPJs Omissos (Total)</div>
                <div class="coate-kpi-icon">🏢</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_int(tot_cnpj)
        + """</div>
            <div class="coate-kpi-delta delta-danger">Contribuintes com omissão</div>
            <div class="coate-kpi-help">CNPJs únicos omissos no período 2021–2025 (sem dupla contagem entre anos).</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        """
        <div class="coate-kpi-card accent-warning">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Declarações Omissas (Total)</div>
                <div class="coate-kpi-icon">📄</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_int(tot_declaracoes)
        + """</div>
            <div class="coate-kpi-delta delta-warning">DEFIS não entregues</div>
            <div class="coate-kpi-help">Cada declaração DEFIS não entregue conta individualmente por CNPJ e por ano.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        """
        <div class="coate-kpi-card accent-info">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Anos Monitorados</div>
                <div class="coate-kpi-icon">📆</div>
            </div>
            <div class="coate-kpi-value">"""
        + str(n_anos)
        + """</div>
            <div class="coate-kpi-delta delta-info">Série histórica</div>
            <div class="coate-kpi-help">Quantidade de anos-calendário com dados de omissão DEFIS.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Leitura rápida ─────────────────────────────────────────────────────────────
if periodo_top_cnpj is not None and periodo_top_decl is not None:
    st.markdown(
        """
        <div class="coate-panel" style="margin-top:0.9rem;">
            <p>
                <strong>Leitura rápida:</strong>
                o ano com maior número de <strong>CNPJs omissos</strong> foi
                <strong>"""
        + str(periodo_top_cnpj["periodo"])
        + """</strong>, com <strong>"""
        + _fmt_int(periodo_top_cnpj["qt_cnpj_base"])
        + """</strong> contribuintes ("""
        + _fmt_pct(periodo_top_cnpj["perc_cnpj_base"])
        + """ do total acumulado).
                O maior volume de <strong>declarações omissas</strong> também ocorreu em
                <strong>"""
        + str(periodo_top_decl["periodo"])
        + """</strong>, com <strong>"""
        + _fmt_int(periodo_top_decl["qt_declaracoes"])
        + """</strong> DEFIS não entregues ("""
        + _fmt_pct(periodo_top_decl["perc_declaracoes"])
        + """ do total).
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Gráficos comparativos por período ─────────────────────────────────────────
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📈 Comparativo Anual</div>
        <div class="coate-section-title">CNPJs e Declarações Omissas por Ano</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

_layout_base = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#cbd5e1",
    font_family="Segoe UI",
    showlegend=False,
    margin=dict(t=40, b=10, l=10, r=10),
    xaxis=dict(tickangle=0, gridcolor="rgba(148,163,184,0.08)"),
    yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
)

g1, g2 = st.columns(2)
with g1:
    fig_cnpj = go.Figure()
    for _, row in df_anuais.iterrows():
        fig_cnpj.add_trace(
            go.Bar(
                x=[str(row["periodo"])],
                y=[row["qt_cnpj_base"]],
                name=str(row["periodo"]),
                marker_color=CORES_PERIODO.get(str(row["periodo"]), "#94a3b8"),
                text=[_fmt_int(row["qt_cnpj_base"])],
                textposition="outside",
                customdata=[[_fmt_pct(row["perc_cnpj_base"])]],
                hovertemplate="Ano: %{x}<br>CNPJs: %{text}<br>% do total: %{customdata[0]}<extra></extra>",
            )
        )
    fig_cnpj.update_layout(**_layout_plot(_layout_base, title="CNPJs Omissos por Ano"))
    st.plotly_chart(fig_cnpj, use_container_width=True)

with g2:
    fig_decl = go.Figure()
    for _, row in df_anuais.iterrows():
        fig_decl.add_trace(
            go.Bar(
                x=[str(row["periodo"])],
                y=[row["qt_declaracoes"]],
                name=str(row["periodo"]),
                marker_color=CORES_PERIODO.get(str(row["periodo"]), "#94a3b8"),
                text=[_fmt_int(row["qt_declaracoes"])],
                textposition="outside",
                customdata=[[_fmt_pct(row["perc_declaracoes"])]],
                hovertemplate="Ano: %{x}<br>Declarações: %{text}<br>% do total: %{customdata[0]}<extra></extra>",
            )
        )
    fig_decl.update_layout(**_layout_plot(_layout_base, title="Declarações Omissas por Ano"))
    st.plotly_chart(fig_decl, use_container_width=True)

# ── Gráfico de linha — evolução ────────────────────────────────────────────────
g3, g4 = st.columns(2)
with g3:
    fig_line_cnpj = go.Figure()
    fig_line_cnpj.add_trace(
        go.Scatter(
            x=df_anuais["periodo"].tolist(),
            y=df_anuais["qt_cnpj_base"].tolist(),
            mode="lines+markers+text",
            marker=dict(color="#ef4444", size=9),
            line=dict(color="#ef4444", width=2),
            text=[_fmt_int(v) for v in df_anuais["qt_cnpj_base"]],
            textposition="top center",
            hovertemplate="Ano: %{x}<br>CNPJs: %{text}<extra></extra>",
        )
    )
    fig_line_cnpj.update_layout(
        **_layout_plot(
            _layout_base,
            title="Evolução — CNPJs Omissos",
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
        )
    )
    st.plotly_chart(fig_line_cnpj, use_container_width=True)

with g4:
    fig_line_decl = go.Figure()
    fig_line_decl.add_trace(
        go.Scatter(
            x=df_anuais["periodo"].tolist(),
            y=df_anuais["qt_declaracoes"].tolist(),
            mode="lines+markers+text",
            marker=dict(color="#f59e0b", size=9),
            line=dict(color="#f59e0b", width=2),
            text=[_fmt_int(v) for v in df_anuais["qt_declaracoes"]],
            textposition="top center",
            hovertemplate="Ano: %{x}<br>Declarações: %{text}<extra></extra>",
        )
    )
    fig_line_decl.update_layout(
        **_layout_plot(
            _layout_base,
            title="Evolução — Declarações Omissas",
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
        )
    )
    st.plotly_chart(fig_line_decl, use_container_width=True)

# ── Tabela detalhada ───────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📋 Detalhe</div>
        <div class="coate-section-title">Tabela por Período</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

df_exib = df_full[["periodo", "qt_cnpj_base", "perc_cnpj_base", "qt_declaracoes", "perc_declaracoes"]].copy()

st.dataframe(
    df_exib,
    use_container_width=True,
    hide_index=True,
    column_config={
        "periodo": st.column_config.TextColumn("Período"),
        "qt_cnpj_base": st.column_config.NumberColumn("CNPJs Omissos", format="%d"),
        "perc_cnpj_base": st.column_config.ProgressColumn(
            "% CNPJs", format="%.2f%%", min_value=0, max_value=100
        ),
        "qt_declaracoes": st.column_config.NumberColumn("Declarações Omissas", format="%d"),
        "perc_declaracoes": st.column_config.ProgressColumn(
            "% Declarações", format="%.2f%%", min_value=0, max_value=100
        ),
    },
)

# ── Nota metodológica ─────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-panel">
        <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.7rem;">
            <span style="font-size:1.2rem;">📌</span>
            <span style="font-size:1rem;font-weight:700;color:#f1f5f9;">Nota metodológica — Como interpretar os totais</span>
        </div>
        <p style="margin:0 0 0.6rem 0;">
            O total de <strong>"""
    + _fmt_int(tot_cnpj)
    + """ CNPJs únicos</strong> no período 2021–2025 representa contribuintes
            distintos que foram omissos na DEFIS em <em>pelo menos um ano</em> dentro da série histórica,
            <strong>sem dupla contagem</strong> entre exercícios.
        </p>
        <p style="margin:0 0 0.6rem 0;">
            Já a <strong>soma dos CNPJs anuais</strong> — """
    + " + ".join(_fmt_int(v) for v in df_anuais["qt_cnpj_base"].tolist())
    + """ —
            totaliza <strong>"""
    + _fmt_int(soma_cnpj_anual)
    + """ ocorrências</strong>, pois um mesmo CNPJ que foi omisso em mais de
            um ano é contado uma vez por ano. Isso evidencia que <strong>"""
    + _fmt_int(reincidencia)
    + """ ocorrências</strong> correspondem
            a contribuintes que reincidiram na omissão ao longo dos exercícios.
        </p>
        <p style="margin:0;">
            As <strong>"""
    + _fmt_int(tot_declaracoes)
    + """ declarações omissas</strong> correspondem à soma direta de todas as
            DEFIS não entregues no período (uma por CNPJ por ano-calendário), e batem exatamente
            com o total consolidado — não há deduplicação nessa dimensão.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="coate-footer">Simples Nacional · Omissão DEFIS · Painel COATE · SEFAZ-CE · Dados gerados em '
    + data_ref
    + "</div>",
    unsafe_allow_html=True,
)
