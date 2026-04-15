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
    "periodo",
    "qt_cnpj_base",
    "cod_regime_recolhimento",
    "dsc_regime_recolhimento",
    "sta_extrapolacao",
    "dsc_sta_extrapolacao",
}
CORES_PERIODO = {
    "2021": "#6366f1",
    "2022": "#3b82f6",
    "2023": "#06b6d4",
    "2024": "#22c55e",
    "2025": "#f59e0b",
    "2021-2025": "#ef4444",
}
CORES_REGIME = {
    "MEI": "#3b82f6",
    "MICROEMPRESA": "#22c55e",
    "EPP": "#f59e0b",
    "ME + EPP": "#a855f7",
}
CORES_EXTRAPOL = {
    "Extrapolou em ate 20%": "#f59e0b",
    "Extrapolou em mais de 20%": "#ef4444",
}
ORDEM_PERIODO = {"2021": 1, "2022": 2, "2023": 3, "2024": 4, "2025": 5, "2021-2025": 6}


def _resolver_arquivo_dados() -> Path | None:
    candidatos = [
        _DATA_DIR / "Sublimites_e_Limites.xlsx",
        _DATA_DIR / "Sublimites e Limites.xlsx",
    ]
    for caminho in candidatos:
        if caminho.exists():
            return caminho
    for caminho in sorted(_DATA_DIR.glob("*.xlsx")):
        nome = caminho.name.lower()
        if "sublimite" in nome or ("limite" in nome and "sublimite" in nome):
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
    df["qt_cnpj_base"] = pd.to_numeric(df["qt_cnpj_base"], errors="coerce").fillna(0)
    df["periodo"] = df["periodo"].astype(str).str.strip()
    df["dsc_regime_recolhimento"] = df["dsc_regime_recolhimento"].astype(str).str.strip()
    df["dsc_sta_extrapolacao"] = df["dsc_sta_extrapolacao"].astype(str).str.strip()
    df["eh_total"] = df["periodo"] == "2021-2025"
    df["ordem_periodo"] = df["periodo"].map(ORDEM_PERIODO).fillna(99)
    df["ordem_regime"] = df["dsc_regime_recolhimento"].map({"MEI": 1, "MICROEMPRESA": 2, "EPP": 3}).fillna(9)
    return df.sort_values(["ordem_periodo", "ordem_regime", "sta_extrapolacao"])


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
        <h1>⚠️ Sublimites e Limites</h1>
        <p>
            Monitoramento de contribuintes do Simples Nacional que extrapolaram os limites
            e sublimites de receita bruta do seu regime (MEI, Microempresa e EPP),
            classificados pela gravidade da extrapolação e pelo período de ocorrência.
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

# ── Filtros ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="coate-section" style="margin-top:0.5rem;">
        <div class="coate-section-super">🔧 Filtros</div>
        <div class="coate-section-title">Segmentação da Análise</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

periodos_disp = sorted(
    df_full["periodo"].unique().tolist(),
    key=lambda p: ORDEM_PERIODO.get(str(p), 99),
)

f1, f2, f3 = st.columns(3)

with f1:
    periodo_sel = st.selectbox(
        "Período",
        options=periodos_disp,
        index=periodos_disp.index("2021-2025") if "2021-2025" in periodos_disp else 0,
    )

with f2:
    opcoes_regime = ["Todos", "MEI", "MICROEMPRESA", "EPP", "ME + EPP"]
    regime_sel = st.selectbox("Regime de Recolhimento", options=opcoes_regime, index=0)

with f3:
    opcoes_extrapol = ["Todas", "Extrapolou em ate 20%", "Extrapolou em mais de 20%"]
    extrapol_sel = st.selectbox("Motivo da Extrapolação", options=opcoes_extrapol, index=0)

# ── Fonte ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="coate-alert alert-info" style="margin-top:0.5rem;margin-bottom:1rem;">
        <div class="coate-alert-icon">ℹ️</div>
        <div class="coate-alert-body">
            Fonte: <strong>"""
    + _DATA_PATH.name
    + """</strong> · Período selecionado: <strong>"""
    + str(periodo_sel)
    + """</strong>.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Aplicar filtros ────────────────────────────────────────────────────────────
df_periodo = df_full[df_full["periodo"] == str(periodo_sel)].copy()

# Filtro regime — ME + EPP agrupa os dois
if regime_sel == "ME + EPP":
    df_filtrado = df_periodo[df_periodo["dsc_regime_recolhimento"].isin(["MICROEMPRESA", "EPP"])].copy()
    # Colapsar em um único regime para somas
    df_filtrado = (
        df_filtrado.groupby(["periodo", "dsc_sta_extrapolacao", "sta_extrapolacao"], as_index=False)
        .agg(qt_cnpj_base=("qt_cnpj_base", "sum"))
    )
    df_filtrado["dsc_regime_recolhimento"] = "ME + EPP"
    df_filtrado["eh_total"] = df_filtrado["periodo"] == "2021-2025"
elif regime_sel != "Todos":
    df_filtrado = df_periodo[df_periodo["dsc_regime_recolhimento"] == regime_sel].copy()
else:
    df_filtrado = df_periodo.copy()

# Filtro extrapolação
if extrapol_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["dsc_sta_extrapolacao"] == extrapol_sel].copy()

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

# ── KPIs ───────────────────────────────────────────────────────────────────────
tot_geral = int(df_filtrado["qt_cnpj_base"].sum())
n_regimes = df_filtrado["dsc_regime_recolhimento"].nunique() if regime_sel == "Todos" else 1

# Breakdown por extrapolação (no filtro atual)
df_ate20 = df_filtrado[df_filtrado["dsc_sta_extrapolacao"] == "Extrapolou em ate 20%"]
df_mais20 = df_filtrado[df_filtrado["dsc_sta_extrapolacao"] == "Extrapolou em mais de 20%"]
tot_ate20 = int(df_ate20["qt_cnpj_base"].sum())
tot_mais20 = int(df_mais20["qt_cnpj_base"].sum())

st.markdown(
    """
    <div class="coate-section" style="margin-top:1.2rem;">
        <div class="coate-section-super">📊 KPIs · """
    + str(periodo_sel)
    + ((" · " + regime_sel) if regime_sel != "Todos" else "")
    + ((" · " + extrapol_sel) if extrapol_sel != "Todas" else "")
    + """</div>
        <div class="coate-section-title">Visão Consolidada</div>
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
                <div class="coate-kpi-label">CNPJs com Extrapolação</div>
                <div class="coate-kpi-icon">⚠️</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_int(tot_geral)
        + """</div>
            <div class="coate-kpi-delta delta-danger">Total no recorte selecionado</div>
            <div class="coate-kpi-help">CNPJs que ultrapassaram o limite/sublimite do seu regime no período.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        """
        <div class="coate-kpi-card accent-warning">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Extrapolação até 20%</div>
                <div class="coate-kpi-icon">🟡</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_int(tot_ate20)
        + """</div>
            <div class="coate-kpi-delta delta-warning">"""
        + (_fmt_pct(tot_ate20 / tot_geral * 100) if tot_geral > 0 else "0%")
        + """ do total</div>
            <div class="coate-kpi-help">Extrapolaram o limite em até 20% acima — situação de atenção.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Extrapolação acima de 20%</div>
                <div class="coate-kpi-icon">🔴</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_int(tot_mais20)
        + """</div>
            <div class="coate-kpi-delta delta-danger">"""
        + (_fmt_pct(tot_mais20 / tot_geral * 100) if tot_geral > 0 else "0%")
        + """ do total</div>
            <div class="coate-kpi-help">Extrapolaram o limite em mais de 20% — situação crítica de enquadramento.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Leitura rápida ─────────────────────────────────────────────────────────────
if regime_sel == "Todos" and extrapol_sel == "Todas":
    # Regime com mais CNPJs no período
    top_regime = (
        df_filtrado.groupby("dsc_regime_recolhimento")["qt_cnpj_base"].sum().idxmax()
    )
    top_regime_val = int(df_filtrado.groupby("dsc_regime_recolhimento")["qt_cnpj_base"].sum().max())
    pct_mais20_geral = _fmt_pct(tot_mais20 / tot_geral * 100) if tot_geral > 0 else "0%"

    st.markdown(
        """
        <div class="coate-panel" style="margin-top:0.9rem;">
            <p>
                <strong>Leitura rápida:</strong>
                no período <strong>"""
        + str(periodo_sel)
        + """</strong>, o regime com maior número de contribuintes que extrapolaram foi
                <strong>"""
        + top_regime
        + """</strong>, com <strong>"""
        + _fmt_int(top_regime_val)
        + """</strong> CNPJs.
                Do total de extrapolações, <strong>"""
        + _fmt_int(tot_mais20)
        + """</strong> ("""
        + pct_mais20_geral
        + """) superaram o limite em mais de 20%, configurando situação crítica de desenquadramento.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Gráficos ───────────────────────────────────────────────────────────────────
_layout_base = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#cbd5e1",
    font_family="Segoe UI",
    showlegend=True,
    margin=dict(t=50, b=10, l=10, r=10),
    xaxis=dict(tickangle=0, gridcolor="rgba(148,163,184,0.08)"),
    yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)

# Gráfico 1 — Barras agrupadas por regime e tipo de extrapolação (período selecionado)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📊 Distribuição</div>
        <div class="coate-section-title">CNPJs por Regime e Tipo de Extrapolação</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

g1, g2 = st.columns(2)

with g1:
    # Barras agrupadas: regime × tipo de extrapolação
    fig_bar = go.Figure()
    regimes_disp = (
        ["MEI", "MICROEMPRESA", "EPP"]
        if regime_sel == "Todos"
        else (["MICROEMPRESA", "EPP"] if regime_sel == "ME + EPP" else [regime_sel])
    )
    for extrapol_label, sta_val in [("Até 20%", "Extrapolou em ate 20%"), ("Mais de 20%", "Extrapolou em mais de 20%")]:
        if extrapol_sel != "Todas" and extrapol_sel != sta_val:
            continue
        y_vals = []
        x_labels = []
        for regime in regimes_disp:
            sub = df_filtrado[
                (df_filtrado["dsc_regime_recolhimento"].isin([regime] if regime_sel != "ME + EPP" else ["MICROEMPRESA", "EPP"]))
                & (df_filtrado["dsc_sta_extrapolacao"] == sta_val)
            ]
            # Para ME+EPP, já está colapsado
            if regime_sel == "ME + EPP":
                sub = df_filtrado[df_filtrado["dsc_sta_extrapolacao"] == sta_val]
                y_vals.append(int(sub["qt_cnpj_base"].sum()))
                x_labels.append("ME + EPP")
                break
            y_vals.append(int(sub["qt_cnpj_base"].sum()))
            x_labels.append(regime)

        fig_bar.add_trace(
            go.Bar(
                x=x_labels,
                y=y_vals,
                name=extrapol_label,
                marker_color=CORES_EXTRAPOL.get(sta_val, "#94a3b8"),
                text=[_fmt_int(v) for v in y_vals],
                textposition="outside",
            )
        )
    fig_bar.update_layout(
        **_layout_plot(
            _layout_base,
            title="Por Regime e Tipo de Extrapolação",
            barmode="group",
        )
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with g2:
    # Pizza por regime
    df_pizza_regime = df_filtrado.groupby("dsc_regime_recolhimento")["qt_cnpj_base"].sum().reset_index()
    fig_pizza = go.Figure(
        go.Pie(
            labels=df_pizza_regime["dsc_regime_recolhimento"].tolist(),
            values=df_pizza_regime["qt_cnpj_base"].tolist(),
            marker_colors=[CORES_REGIME.get(r, "#94a3b8") for r in df_pizza_regime["dsc_regime_recolhimento"]],
            hole=0.45,
            textinfo="label+percent",
            hovertemplate="%{label}<br>CNPJs: %{value:,}<br>%{percent}<extra></extra>",
        )
    )
    fig_pizza.update_layout(
        **_layout_plot(
            _layout_base,
            title="Participação por Regime",
            showlegend=False,
        )
    )
    st.plotly_chart(fig_pizza, use_container_width=True)

# Gráfico 2 — Evolução anual (apenas anos, sem o consolidado)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📈 Evolução</div>
        <div class="coate-section-title">CNPJs com Extrapolação por Ano</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

df_evolucao = df_full[df_full["periodo"] != "2021-2025"].copy()

# Aplicar mesmo filtro de regime na evolução
if regime_sel == "ME + EPP":
    df_evolucao = (
        df_evolucao[df_evolucao["dsc_regime_recolhimento"].isin(["MICROEMPRESA", "EPP"])]
        .groupby(["periodo", "dsc_sta_extrapolacao", "sta_extrapolacao", "ordem_periodo"], as_index=False)
        .agg(qt_cnpj_base=("qt_cnpj_base", "sum"))
    )
    df_evolucao["dsc_regime_recolhimento"] = "ME + EPP"
elif regime_sel != "Todos":
    df_evolucao = df_evolucao[df_evolucao["dsc_regime_recolhimento"] == regime_sel].copy()

if extrapol_sel != "Todas":
    df_evolucao = df_evolucao[df_evolucao["dsc_sta_extrapolacao"] == extrapol_sel].copy()

df_evolucao = df_evolucao.sort_values("ordem_periodo")

g3, g4 = st.columns(2)

with g3:
    # Linhas por regime ao longo dos anos
    fig_linha = go.Figure()
    regimes_evol = df_evolucao["dsc_regime_recolhimento"].unique().tolist()
    df_evol_agrupado = (
        df_evolucao.groupby(["periodo", "dsc_regime_recolhimento", "ordem_periodo"], as_index=False)
        ["qt_cnpj_base"].sum()
        .sort_values("ordem_periodo")
    )
    for regime in regimes_evol:
        sub = df_evol_agrupado[df_evol_agrupado["dsc_regime_recolhimento"] == regime]
        fig_linha.add_trace(
            go.Scatter(
                x=sub["periodo"].tolist(),
                y=sub["qt_cnpj_base"].tolist(),
                mode="lines+markers+text",
                name=regime,
                marker=dict(color=CORES_REGIME.get(regime, "#94a3b8"), size=8),
                line=dict(color=CORES_REGIME.get(regime, "#94a3b8"), width=2),
                text=[_fmt_int(v) for v in sub["qt_cnpj_base"]],
                textposition="top center",
                hovertemplate="Ano: %{x}<br>" + regime + ": %{text}<extra></extra>",
            )
        )
    fig_linha.update_layout(
        **_layout_plot(
            _layout_base,
            title="Evolução por Regime",
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
        )
    )
    st.plotly_chart(fig_linha, use_container_width=True)

with g4:
    # Barras empilhadas: ano × tipo de extrapolação
    fig_stack = go.Figure()
    periodos_anuais = sorted(
        df_evolucao["periodo"].unique().tolist(),
        key=lambda p: ORDEM_PERIODO.get(str(p), 99),
    )
    for extrapol_label, sta_val in [("Até 20%", "Extrapolou em ate 20%"), ("Mais de 20%", "Extrapolou em mais de 20%")]:
        if extrapol_sel != "Todas" and extrapol_sel != sta_val:
            continue
        sub = (
            df_evolucao[df_evolucao["dsc_sta_extrapolacao"] == sta_val]
            .groupby("periodo")["qt_cnpj_base"].sum()
            .reindex(periodos_anuais, fill_value=0)
        )
        fig_stack.add_trace(
            go.Bar(
                x=periodos_anuais,
                y=sub.values.tolist(),
                name=extrapol_label,
                marker_color=CORES_EXTRAPOL.get(sta_val, "#94a3b8"),
                text=[_fmt_int(v) for v in sub.values],
                textposition="inside",
            )
        )
    fig_stack.update_layout(
        **_layout_plot(
            _layout_base,
            title="Extrapolação por Ano (Empilhado)",
            barmode="stack",
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
        )
    )
    st.plotly_chart(fig_stack, use_container_width=True)

# ── Tabela detalhada ───────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📋 Detalhe</div>
        <div class="coate-section-title">Tabela por Regime e Tipo de Extrapolação</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

# Montar tabela pivotada: regime × tipo de extrapolação
df_tabela_src = df_full[df_full["periodo"] == str(periodo_sel)].copy()

if regime_sel == "ME + EPP":
    df_me_epp = (
        df_tabela_src[df_tabela_src["dsc_regime_recolhimento"].isin(["MICROEMPRESA", "EPP"])]
        .groupby(["dsc_sta_extrapolacao"], as_index=False)
        .agg(qt_cnpj_base=("qt_cnpj_base", "sum"))
    )
    df_me_epp["dsc_regime_recolhimento"] = "ME + EPP"
    df_tabela_src = df_me_epp
elif regime_sel != "Todos":
    df_tabela_src = df_tabela_src[df_tabela_src["dsc_regime_recolhimento"] == regime_sel].copy()

if extrapol_sel != "Todas":
    df_tabela_src = df_tabela_src[df_tabela_src["dsc_sta_extrapolacao"] == extrapol_sel].copy()

# Pivot
try:
    df_pivot = df_tabela_src.pivot_table(
        index="dsc_regime_recolhimento",
        columns="dsc_sta_extrapolacao",
        values="qt_cnpj_base",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    df_pivot.columns.name = None
    df_pivot["Total"] = df_pivot.select_dtypes("number").sum(axis=1)
    df_pivot = df_pivot.rename(columns={"dsc_regime_recolhimento": "Regime"})

    col_config = {"Regime": st.column_config.TextColumn("Regime")}
    for col in df_pivot.columns:
        if col != "Regime":
            col_config[col] = st.column_config.NumberColumn(col, format="%d")

    st.dataframe(df_pivot, use_container_width=True, hide_index=True, column_config=col_config)
except Exception:
    # Fallback: tabela simples
    df_exib = df_tabela_src[["dsc_regime_recolhimento", "dsc_sta_extrapolacao", "qt_cnpj_base"]].copy()
    df_exib = df_exib.rename(columns={
        "dsc_regime_recolhimento": "Regime",
        "dsc_sta_extrapolacao": "Tipo de Extrapolação",
        "qt_cnpj_base": "CNPJs",
    })
    st.dataframe(df_exib, use_container_width=True, hide_index=True)

# ── Nota metodológica ─────────────────────────────────────────────────────────
# Calcular somas dinâmicas para a nota
df_anuais_full = df_full[df_full["periodo"] != "2021-2025"]
df_total_full  = df_full[df_full["periodo"] == "2021-2025"]

soma_mei_anual  = int(df_anuais_full[df_anuais_full["dsc_regime_recolhimento"] == "MEI"]["qt_cnpj_base"].sum())
soma_me_anual   = int(df_anuais_full[df_anuais_full["dsc_regime_recolhimento"] == "MICROEMPRESA"]["qt_cnpj_base"].sum())
soma_epp_anual  = int(df_anuais_full[df_anuais_full["dsc_regime_recolhimento"] == "EPP"]["qt_cnpj_base"].sum())
soma_total_anual = soma_mei_anual + soma_me_anual + soma_epp_anual

unicos_mei  = int(df_total_full[df_total_full["dsc_regime_recolhimento"] == "MEI"]["qt_cnpj_base"].sum())
unicos_me   = int(df_total_full[df_total_full["dsc_regime_recolhimento"] == "MICROEMPRESA"]["qt_cnpj_base"].sum())
unicos_epp  = int(df_total_full[df_total_full["dsc_regime_recolhimento"] == "EPP"]["qt_cnpj_base"].sum())
unicos_total = int(df_total_full["qt_cnpj_base"].sum())

reincid_mei  = soma_mei_anual  - unicos_mei
reincid_me   = soma_me_anual   - unicos_me
reincid_epp  = soma_epp_anual  - unicos_epp
reincid_total = soma_total_anual - unicos_total

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-panel">
        <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.7rem;">
            <span style="font-size:1.2rem;">📌</span>
            <span style="font-size:1rem;font-weight:700;color:#f1f5f9;">Nota metodológica — Como interpretar os totais</span>
        </div>
        <p style="margin:0 0 0.6rem 0;">
            Os totais do período <strong>2021–2025</strong> representam <strong>CNPJs únicos</strong>
            que extrapolaram o limite do seu regime em <em>pelo menos um ano</em> da série histórica,
            sem dupla contagem entre exercícios:
            <strong>"""
    + _fmt_int(unicos_mei)
    + """ MEIs</strong>, <strong>"""
    + _fmt_int(unicos_me)
    + """ Microempresas</strong> e <strong>"""
    + _fmt_int(unicos_epp)
    + """ EPPs</strong> — totalizando <strong>"""
    + _fmt_int(unicos_total)
    + """ CNPJs únicos</strong>.
        </p>
        <p style="margin:0 0 0.6rem 0;">
            Já a <strong>soma das ocorrências anuais</strong> chega a <strong>"""
    + _fmt_int(soma_total_anual)
    + """</strong>
            (MEI: """
    + _fmt_int(soma_mei_anual)
    + """ · ME: """
    + _fmt_int(soma_me_anual)
    + """ · EPP: """
    + _fmt_int(soma_epp_anual)
    + """),
            evidenciando <strong>"""
    + _fmt_int(reincid_total)
    + """ ocorrências de reincidência</strong> — contribuintes que extrapolaram em mais de um exercício.
        </p>
        <p style="margin:0 0 0.6rem 0;">
            A <strong>extrapolação de até 20%</strong> indica que o contribuinte ultrapassou o teto do
            seu regime dentro da margem tolerada pela legislação, podendo ainda regularizar a situação
            no ano seguinte. A <strong>extrapolação acima de 20%</strong> configura situação crítica,
            com necessidade de exclusão imediata do Simples Nacional.
        </p>
        <p style="margin:0;">
            O agrupamento <strong>ME + EPP</strong> consolida os dois regimes por compartilharem
            estrutura de limite de receita bruta anual diferente do MEI, sendo relevante para
            análises comparativas entre os segmentos empresariais não-MEI.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="coate-footer">Simples Nacional · Sublimites e Limites · Painel COATE · SEFAZ-CE</div>',
    unsafe_allow_html=True,
)
