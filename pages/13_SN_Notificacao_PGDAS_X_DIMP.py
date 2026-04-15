import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

from pathlib import Path
import base64 as _b64mod

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from coate_auth import exigir_acesso
from coate_styles import aplicar_estilos

aplicar_estilos()
exigir_acesso("simples")

_DATA_DIR = Path(__file__).resolve().parent.parent / "simples_nacional" / "data"
_REQUIRED_COLUMNS = {
    "dat_geracao",
    "faixa",
    "perc_valor",
    "periodo",
    "qt_cnpj_base",
    "perc_cnpj_base",
    "qt_declaracoes",
    "perc_declaracoes",
    "vlr_ajuste_a_regularizar_icms",
}
CORES_PERIODO = {"2024": "#3b82f6", "2025": "#22c55e", "2024-2025": "#f59e0b"}


def _resolver_arquivo_dados() -> Path | None:
    candidatos = [
        _DATA_DIR / "Diferença PGDAS DIMP a notificar.xlsx",
        _DATA_DIR / "Diferen#U00e7a PGDAS DIMP a notificar.xlsx",
    ]
    for caminho in candidatos:
        if caminho.exists():
            return caminho

    for caminho in sorted(_DATA_DIR.glob("*.xlsx")):
        nome = caminho.name.lower()
        if "pgdas" in nome and "dimp" in nome and "notificar" in nome:
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
    df["vlr_ajuste_a_regularizar_icms"] = pd.to_numeric(df["vlr_ajuste_a_regularizar_icms"], errors="coerce").fillna(0)
    df["qt_cnpj_base"] = pd.to_numeric(df["qt_cnpj_base"], errors="coerce").fillna(0)
    df["perc_cnpj_base"] = pd.to_numeric(df["perc_cnpj_base"], errors="coerce").fillna(0)
    df["qt_declaracoes"] = pd.to_numeric(df["qt_declaracoes"], errors="coerce").fillna(0)
    df["perc_declaracoes"] = pd.to_numeric(df["perc_declaracoes"], errors="coerce").fillna(0)
    df["perc_valor"] = pd.to_numeric(df["perc_valor"], errors="coerce").fillna(0)
    df["faixa"] = df["faixa"].astype(str).str.strip()
    df["periodo"] = df["periodo"].astype(str).str.strip()
    df["eh_total"] = df["faixa"].str.lower() == "total geral"
    df["faixa_ordem"] = pd.to_numeric(df["faixa"].str.extract(r"^(\d+)")[0], errors="coerce")
    df["faixa_ordem"] = df["faixa_ordem"].fillna(999)
    df["faixa_curta"] = "F" + df["faixa_ordem"].astype(int).astype(str)
    df.loc[df["eh_total"], "faixa_curta"] = "Total"
    return df



def _fmt_moeda(v: float) -> str:
    try:
        v = float(v)
    except Exception:
        return "R$ 0"
    if abs(v) >= 1_000_000_000:
        return f"R$ {v / 1_000_000_000:.2f} Bi"
    if abs(v) >= 1_000_000:
        return f"R$ {v / 1_000_000:.1f} Mi"
    return f"R$ {v:,.0f}".replace(",", ".")



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



def _ordenar_periodos(periodos: list[str]) -> list[str]:
    ordem_base = {"2024": 1, "2025": 2, "2024-2025": 3}
    return sorted(periodos, key=lambda p: (ordem_base.get(str(p), 99), str(p)))



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


_sn_icon_path = _os.path.join(_os.path.dirname(__file__), "..", "assets", "simples_nacional_icon.png")
_sn_img = ""
if _os.path.exists(_sn_icon_path):
    with open(_sn_icon_path, "rb") as _f:
        _sn_img = (
            f'<img src="data:image/png;base64,{_b64mod.b64encode(_f.read()).decode()}" '
            'style="height:56px;border-radius:10px;margin-bottom:0.6rem;display:block;" '
            'alt="Simples Nacional">'
        )

st.markdown(
    f"""
    <div class="coate-hero">
        <div class="coate-hero-kicker">🗂️ Simples Nacional · SEFAZ-CE</div>
        {_sn_img}
        <h1>🧮 Notificação PGDAS X DIMP</h1>
        <p>
            Monitoramento de diferenças entre PGDAS e DIMP com foco em contribuintes,
            declarações e valor do ajuste de ICMS a regularizar por faixa de receita.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if _DATA_PATH is None:
    arquivos_disponiveis = ", ".join(sorted(p.name for p in _DATA_DIR.glob("*.xlsx"))) or "nenhum arquivo .xlsx localizado"
    st.error(
        "Não foi possível localizar a planilha da página. "
        f"Arquivos encontrados em `simples_nacional/data`: {arquivos_disponiveis}."
    )
    st.stop()

try:
    df_full = _carregar_dados(str(_DATA_PATH))
except Exception as exc:
    st.error(f"Erro ao carregar a planilha `{_DATA_PATH.name}`: {exc}")
    st.stop()

if df_full.empty:
    st.warning("A planilha foi localizada, mas não contém registros para exibição.")
    st.stop()

data_ref = df_full["dat_geracao"].dropna().iloc[0].strftime("%d/%m/%Y") if not df_full["dat_geracao"].dropna().empty else "N/D"
periodos_disp = _ordenar_periodos(df_full["periodo"].dropna().astype(str).unique().tolist())

if not periodos_disp:
    st.warning("A planilha não possui períodos disponíveis para consulta.")
    st.stop()

col_f, col_info = st.columns([2, 4])
with col_f:
    periodo_sel = st.selectbox(
        "Período de referência",
        options=periodos_disp,
        index=periodos_disp.index("2024-2025") if "2024-2025" in periodos_disp else 0,
    )
with col_info:
    st.markdown(
        f"""
        <div class="coate-alert alert-info" style="margin-top:1.75rem;">
            <div class="coate-alert-icon">ℹ️</div>
            <div class="coate-alert-body">
                Fonte: <strong>{_DATA_PATH.name}</strong> · Dados gerados em <strong>{data_ref}</strong>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

df = df_full[df_full["periodo"] == str(periodo_sel)].copy()
df_faixas = df[~df["eh_total"]].copy().sort_values(["faixa_ordem", "faixa"])
df_total = df[df["eh_total"]].copy()

if df_faixas.empty and df_total.empty:
    st.warning(f"Não há dados para o período selecionado: {periodo_sel}.")
    st.stop()

tot_cnpj = int(df_total["qt_cnpj_base"].iloc[0]) if not df_total.empty else int(df_faixas["qt_cnpj_base"].sum())
tot_declaracoes = int(df_total["qt_declaracoes"].iloc[0]) if not df_total.empty else int(df_faixas["qt_declaracoes"].sum())
tot_valor = float(df_total["vlr_ajuste_a_regularizar_icms"].iloc[0]) if not df_total.empty else float(df_faixas["vlr_ajuste_a_regularizar_icms"].sum())
n_faixas = int(df_faixas["faixa"].nunique())

faixa_top_cnpj = df_faixas.loc[df_faixas["qt_cnpj_base"].idxmax()] if not df_faixas.empty else None
faixa_top_valor = df_faixas.loc[df_faixas["vlr_ajuste_a_regularizar_icms"].idxmax()] if not df_faixas.empty else None

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

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        f"""
        <div class="coate-kpi-card accent-danger">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">CNPJs na Notificação</div>
                <div class="coate-kpi-icon">🏢</div>
            </div>
            <div class="coate-kpi-value">{_fmt_int(tot_cnpj)}</div>
            <div class="coate-kpi-delta delta-danger">Diferenças PGDAS × DIMP</div>
            <div class="coate-kpi-help">Total de CNPJs base no período selecionado.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f"""
        <div class="coate-kpi-card accent-warning">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Declarações Envolvidas</div>
                <div class="coate-kpi-icon">🧾</div>
            </div>
            <div class="coate-kpi-value">{_fmt_int(tot_declaracoes)}</div>
            <div class="coate-kpi-delta delta-warning">Volume declaratório</div>
            <div class="coate-kpi-help">Quantidade total de declarações no recorte.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f"""
        <div class="coate-kpi-card accent-danger">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Ajuste de ICMS a Regularizar</div>
                <div class="coate-kpi-icon">💰</div>
            </div>
            <div class="coate-kpi-value">{_fmt_moeda(tot_valor)}</div>
            <div class="coate-kpi-delta delta-danger">Potencial de regularização</div>
            <div class="coate-kpi-help">Soma do valor de ajuste a regularizar no período.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k4:
    st.markdown(
        f"""
        <div class="coate-kpi-card accent-info">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Faixas de Receita</div>
                <div class="coate-kpi-icon">📊</div>
            </div>
            <div class="coate-kpi-value">{n_faixas}</div>
            <div class="coate-kpi-delta delta-info">Segmentos monitorados</div>
            <div class="coate-kpi-help">Faixas de receita com diferenças PGDAS × DIMP.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if faixa_top_cnpj is not None and faixa_top_valor is not None:
    st.markdown(
        f"""
        <div class="coate-panel" style="margin-top:0.9rem;">
            <p>
                <strong>Leitura rápida:</strong>
                a maior concentração de <strong>CNPJs</strong> está na faixa
                <strong>{faixa_top_cnpj['faixa_curta']}</strong> ({faixa_top_cnpj['faixa']}), com
                <strong>{_fmt_int(faixa_top_cnpj['qt_cnpj_base'])}</strong> CNPJs.
                Já o maior <strong>valor potencial de regularização</strong> está em
                <strong>{faixa_top_valor['faixa_curta']}</strong> ({faixa_top_valor['faixa']}),
                somando <strong>{_fmt_moeda(faixa_top_valor['vlr_ajuste_a_regularizar_icms'])}</strong>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.expander("Ver legenda das faixas exibidas nos gráficos"):
    legenda_faixas = (
        df_faixas[["faixa_ordem", "faixa_curta", "faixa"]]
        .drop_duplicates()
        .sort_values(["faixa_ordem", "faixa"])
        .drop(columns=["faixa_ordem"])
        .rename(columns={"faixa_curta": "Código", "faixa": "Faixa de Receita Bruta"})
    )
    st.dataframe(legenda_faixas, use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📈 Distribuição</div>
        <div class="coate-section-title">CNPJs, Declarações e Valor por Faixa</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

_cor = CORES_PERIODO.get(str(periodo_sel), "#3b82f6")
_layout_base = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#cbd5e1",
    font_family="Segoe UI",
    showlegend=False,
    margin=dict(t=40, b=10, l=10, r=10),
    xaxis=dict(tickangle=-20, gridcolor="rgba(148,163,184,0.08)"),
    yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
)

g1, g2 = st.columns(2)
with g1:
    fig_qt = px.bar(
        df_faixas,
        x="faixa_curta",
        y="qt_cnpj_base",
        text="qt_cnpj_base",
        title="CNPJs por Faixa",
        color_discrete_sequence=[_cor],
        template="plotly_dark",
        hover_data={"faixa": True, "faixa_curta": False},
    )
    fig_qt.update_traces(texttemplate="%{text:,}", textposition="outside", marker_line_width=0)
    fig_qt.update_layout(**_layout_plot(_layout_base))
    st.plotly_chart(fig_qt, use_container_width=True)

with g2:
    fig_decl = px.bar(
        df_faixas,
        x="faixa_curta",
        y="qt_declaracoes",
        text="perc_declaracoes",
        title="Declarações por Faixa (% do total)",
        color_discrete_sequence=["#22c55e"],
        template="plotly_dark",
        hover_data={"faixa": True, "faixa_curta": False},
    )
    fig_decl.update_traces(texttemplate="%{text:.1f}%", textposition="outside", marker_line_width=0)
    fig_decl.update_layout(**_layout_plot(_layout_base))
    st.plotly_chart(fig_decl, use_container_width=True)

g3, g4 = st.columns(2)
with g3:
    fig_vl = px.bar(
        df_faixas,
        x="faixa_curta",
        y="vlr_ajuste_a_regularizar_icms",
        text="perc_valor",
        title="Valor do Ajuste por Faixa (% do total)",
        color_discrete_sequence=["#f59e0b"],
        template="plotly_dark",
        hover_data={"faixa": True, "faixa_curta": False},
    )
    fig_vl.update_traces(texttemplate="%{text:.1f}%", textposition="outside", marker_line_width=0)
    fig_vl.update_layout(
        **_layout_plot(
            _layout_base,
            yaxis=dict(tickformat=",.0f", gridcolor="rgba(148,163,184,0.08)"),
        )
    )
    st.plotly_chart(fig_vl, use_container_width=True)

with g4:
    fig_mix = go.Figure()
    fig_mix.add_trace(
        go.Scatter(
            x=df_faixas["faixa_curta"],
            y=df_faixas["perc_cnpj_base"],
            mode="lines+markers+text",
            name="% CNPJs",
            marker=dict(color="#3b82f6", size=8),
            line=dict(color="#3b82f6", width=2),
            text=[_fmt_pct(v, 1) for v in df_faixas["perc_cnpj_base"].fillna(0)],
            textposition="top center",
            customdata=df_faixas[["faixa"]].to_numpy(),
            hovertemplate="Faixa: %{customdata[0]}<br>% CNPJs: %{y:.1f}%<extra></extra>",
        )
    )
    fig_mix.add_trace(
        go.Scatter(
            x=df_faixas["faixa_curta"],
            y=df_faixas["perc_valor"],
            mode="lines+markers+text",
            name="% Valor",
            marker=dict(color="#f59e0b", size=8),
            line=dict(color="#f59e0b", width=2),
            text=[_fmt_pct(v, 1) for v in df_faixas["perc_valor"].fillna(0)],
            textposition="bottom center",
            customdata=df_faixas[["faixa"]].to_numpy(),
            hovertemplate="Faixa: %{customdata[0]}<br>% Valor: %{y:.1f}%<extra></extra>",
        )
    )
    fig_mix.update_layout(
        **_layout_plot(
            _layout_base,
            showlegend=True,
            title="Participação por Faixa: CNPJs × Valor",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            yaxis=dict(title="Percentual", ticksuffix="%", gridcolor="rgba(148,163,184,0.08)"),
        )
    )
    st.plotly_chart(fig_mix, use_container_width=True)

st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📋 Detalhe</div>
        <div class="coate-section-title">Tabela por Faixa de Receita</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

df_exib = df_faixas[
    [
        "faixa",
        "qt_cnpj_base",
        "perc_cnpj_base",
        "qt_declaracoes",
        "perc_declaracoes",
        "vlr_ajuste_a_regularizar_icms",
        "perc_valor",
    ]
].copy()

if not df_total.empty:
    df_exib = pd.concat([df_exib, df_total[df_exib.columns]], ignore_index=True)

st.dataframe(
    df_exib,
    use_container_width=True,
    hide_index=True,
    column_config={
        "faixa": st.column_config.TextColumn("Faixa de Receita Bruta"),
        "qt_cnpj_base": st.column_config.NumberColumn("CNPJs Base", format="%d"),
        "perc_cnpj_base": st.column_config.NumberColumn("% CNPJs", format="%.2f%%"),
        "qt_declaracoes": st.column_config.NumberColumn("Declarações", format="%d"),
        "perc_declaracoes": st.column_config.NumberColumn("% Declarações", format="%.2f%%"),
        "vlr_ajuste_a_regularizar_icms": st.column_config.NumberColumn("Ajuste a Regularizar (R$)", format="R$ %,.2f"),
        "perc_valor": st.column_config.ProgressColumn("% do Valor Total", format="%.1f%%", min_value=0, max_value=100),
    },
)

if len(periodos_disp) > 1:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="coate-section">
            <div class="coate-section-super">🔄 Comparativo</div>
            <div class="coate-section-title">CNPJs, Declarações e Valor por Período</div>
        </div>
        <hr class="coate-section-divider"/>
        """,
        unsafe_allow_html=True,
    )

    df_comp = (
        df_full[df_full["eh_total"]]
        .groupby("periodo", as_index=False)
        .agg(
            cnpjs=("qt_cnpj_base", "sum"),
            declaracoes=("qt_declaracoes", "sum"),
            valor=("vlr_ajuste_a_regularizar_icms", "sum"),
        )
    )
    df_comp["ordem"] = df_comp["periodo"].astype(str).map({"2024": 1, "2025": 2, "2024-2025": 3}).fillna(99)
    df_comp = df_comp.sort_values(["ordem", "periodo"]).drop(columns=["ordem"])

    c1, c2, c3 = st.columns(3)
    with c1:
        fig_c1 = go.Figure()
        for _, row in df_comp.iterrows():
            fig_c1.add_trace(
                go.Bar(
                    x=[str(row["periodo"])],
                    y=[row["cnpjs"]],
                    name=str(row["periodo"]),
                    marker_color=CORES_PERIODO.get(str(row["periodo"]), "#94a3b8"),
                    text=[_fmt_int(row["cnpjs"])],
                    textposition="outside",
                )
            )
        fig_c1.update_layout(**_layout_plot(_layout_base, title="CNPJs por Período"))
        st.plotly_chart(fig_c1, use_container_width=True)

    with c2:
        fig_c2 = go.Figure()
        for _, row in df_comp.iterrows():
            fig_c2.add_trace(
                go.Bar(
                    x=[str(row["periodo"])],
                    y=[row["declaracoes"]],
                    name=str(row["periodo"]),
                    marker_color=CORES_PERIODO.get(str(row["periodo"]), "#94a3b8"),
                    text=[_fmt_int(row["declaracoes"])],
                    textposition="outside",
                )
            )
        fig_c2.update_layout(**_layout_plot(_layout_base, title="Declarações por Período"))
        st.plotly_chart(fig_c2, use_container_width=True)

    with c3:
        fig_c3 = go.Figure()
        for _, row in df_comp.iterrows():
            fig_c3.add_trace(
                go.Bar(
                    x=[str(row["periodo"])],
                    y=[row["valor"]],
                    name=str(row["periodo"]),
                    marker_color=CORES_PERIODO.get(str(row["periodo"]), "#94a3b8"),
                    text=[_fmt_moeda(row["valor"])],
                    textposition="outside",
                )
            )
        fig_c3.update_layout(
            **_layout_plot(
                _layout_base,
                title="Valor do Ajuste por Período",
                yaxis=dict(tickformat=",.0f", gridcolor="rgba(148,163,184,0.08)"),
            )
        )
        st.plotly_chart(fig_c3, use_container_width=True)

st.markdown(
    f'<div class="coate-footer">Simples Nacional · Notificação PGDAS X DIMP · Painel COATE · SEFAZ-CE · Dados gerados em {data_ref}</div>',
    unsafe_allow_html=True,
)
