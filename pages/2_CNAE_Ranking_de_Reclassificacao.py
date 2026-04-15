from __future__ import annotations

import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

# Ícone CNAE
import base64 as _b64cnae
_cnae_icon_path = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'assets', 'cnae_icon.png'))
_cnae_img_tag = ""
if _os.path.exists(_cnae_icon_path):
    with open(_cnae_icon_path, "rb") as _f:
        _cnae_img_tag = (f'<img src="data:image/png;base64,{_b64cnae.b64encode(_f.read()).decode()}" '
                         f'style="height:52px;border-radius:10px;margin-bottom:0.5rem;display:block;" alt="CNAE">')

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from projetos_especiais.cnae.cnae_config import (
    LOADING_MESSAGES,
    MAX_EXPORT_ROWS,
    PLOTLY_PAPER_BGCOLOR,
    PLOTLY_PLOT_BGCOLOR,
    PLOTLY_PRIORITY_COLOR_MAP,
    PLOTLY_TEMPLATE,
    PRIORITY_LABELS,
    PRIORITY_META,
    RANKING_PAGE_SIZE,
    SIDEBAR_HELP,
)
from projetos_especiais.cnae.cnae_core import ensure_data_available, load_company_base
from coate_styles import aplicar_estilos
from coate_auth import exigir_acesso
from projetos_especiais.cnae.cnae_utils import (
    format_int,
    format_pct,
    prepare_download_bytes,
    render_alert,
    render_empty_state,
    render_exec_summary,
    render_kpi_card,
    render_section_header,
)



def _kpi_card(label: str, value: str, delta: str, accent: str, icon: str, help_text: str = "") -> str:
    help_html = f'<div class="coate-kpi-help">{help_text}</div>' if help_text else ''
    return f"""<div class="coate-kpi-card accent-{accent}">
        <div class="coate-kpi-top">
            <div class="coate-kpi-label">{label}</div>
            <div class="coate-kpi-icon">{icon}</div>
        </div>
        <div class="coate-kpi-value">{value}</div>
        <div class="coate-kpi-delta delta-{accent}">{delta}</div>
        {help_html}
    </div>"""

aplicar_estilos()
exigir_acesso("cnae")

# ──────────────────────────────────────────────────────────────
# HERO
# ──────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hero">
        {_cnae_img_tag}
        <div class="hero-kicker">🏁 Priorização</div>
        <h1>Ranking de Reclassificação</h1>
        <p>
            Carteira consolidada por empresa, ordenada por score de prioridade auditável —
            com filtros, distribuição e exportação.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    ensure_data_available()

    # ──────────────────────────────────────────────────────────
    # SIDEBAR FILTERS
    # ──────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-subtitle" style="padding:0 0.2rem;">Filtros do ranking</div>',
            unsafe_allow_html=True,
        )
        busca = st.text_input(
            "🔍 Empresa, fantasia ou CNPJ",
            help=SIDEBAR_HELP["busca"],
            placeholder="Ex.: 07526557000100",
        )
        prioridade = st.selectbox(
            "Prioridade de revisão",
            ["Todas"] + PRIORITY_LABELS,
            help=SIDEBAR_HELP["prioridade"],
        )
        instabilidade = st.selectbox(
            "Estabilidade preditiva",
            ["Todas", "Oscilante", "Estável"],
            help=SIDEBAR_HELP["estabilidade"],
        )
        somente_divergentes = st.checkbox(
            "Somente divergentes em subclasse",
            value=False,
            help=SIDEBAR_HELP["divergencia"],
        )
        score_range = st.slider(
            "Faixa de score",
            0, 100, (0, 100),
            help=SIDEBAR_HELP["score"],
        )
        limite = st.number_input(
            "Máximo de linhas",
            min_value=50,
            max_value=MAX_EXPORT_ROWS,
            value=min(RANKING_PAGE_SIZE, 1000),
            step=50,
        )

    filters: dict = {
        "busca": busca.strip() or None,
        "prioridade_revisao": None if prioridade == "Todas" else prioridade,
        "instabilidade": None if instabilidade == "Todas" else instabilidade,
        "somente_divergentes": somente_divergentes,
    }

    # ──────────────────────────────────────────────────────────
    # LOAD
    # ──────────────────────────────────────────────────────────
    with st.spinner(LOADING_MESSAGES["ranking"]):
        df = load_company_base(limit=int(limite), filters=filters)

    if not df.empty and "score_prioridade" in df.columns:
        df = df[
            (df["score_prioridade"].fillna(0) >= score_range[0])
            & (df["score_prioridade"].fillna(0) <= score_range[1])
        ].copy()

    total = len(df)

    # ──────────────────────────────────────────────────────────
    # ALERTAS
    # ──────────────────────────────────────────────────────────
    if total > 0 and "prioridade_revisao" in df.columns:
        n_alta = int((df["prioridade_revisao"] == "Alta").sum())
        pct_alta = n_alta / max(total, 1)
        if pct_alta > 0.30:
            render_alert(
                f"Alta concentração de prioridade Alta ({format_pct(pct_alta)}) no recorte atual — "
                "considere refinar os filtros ou priorizar este subconjunto.",
                variant="danger",
            )

    # ──────────────────────────────────────────────────────────
    # KPIs
    # ──────────────────────────────────────────────────────────
    render_section_header("Recorte Atual", subtitle="KPIs", divider=False)

    alta = int((df.get("prioridade_revisao", pd.Series(dtype=str)) == "Alta").sum()) if total else 0
    media_score = float(df["score_prioridade"].mean()) if total and "score_prioridade" in df.columns else 0.0
    pct_alta_str = format_pct(alta / max(total, 1))
    osc = int((df.get("flag_instabilidade_predicao", pd.Series(dtype=float)) == 1).sum()) if total else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            _kpi_card(
                "Empresas no recorte",
                format_int(total),
                "Carteira filtrada",
                "primary",
                "🏢",
                "Total de empresas após aplicação dos filtros do ranking.",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _kpi_card(
                "Prioridade Alta",
                format_int(alta),
                f"{pct_alta_str} do recorte",
                "danger",
                "🚨",
                "Empresas que já compõem a fila mais crítica de revisão no recorte atual.",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            _kpi_card(
                "Score médio",
                f"{media_score:.1f}",
                "Escala 0–100",
                "warning",
                "📈",
                "Média do score de prioridade no recorte atual.",
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            _kpi_card(
                "Oscilantes",
                format_int(osc),
                format_pct(osc / max(total, 1)),
                "warning",
                "🔁",
                "Empresas com variação de predição ao longo do tempo dentro do recorte filtrado.",
            ),
            unsafe_allow_html=True,
        )

    # Resumo executivo
    if total > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        render_exec_summary(
            f"Recorte com <strong>{format_int(total)} empresas</strong>. "
            f"<strong>{format_int(alta)}</strong> em prioridade Alta ({pct_alta_str}), "
            f"score médio de <strong>{media_score:.1f}</strong> e "
            f"<strong>{format_int(osc)}</strong> empresas com predição oscilante."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if df.empty:
        render_empty_state("Nenhuma empresa encontrada para os filtros selecionados.",
                           "Ajuste os filtros ou limpe a busca para visualizar dados.", icon="🏁")
        st.stop()

    # ──────────────────────────────────────────────────────────
    # GRÁFICOS — distribuição prioridade + score
    # ──────────────────────────────────────────────────────────
    render_section_header("Análise Visual do Recorte", subtitle="Composição",
                          desc="Distribuição por prioridade e dispersão do score.", divider=True)

    col_chart, col_score = st.columns(2)

    with col_chart:
        if "prioridade_revisao" in df.columns:
            dist = (
                df["prioridade_revisao"]
                .value_counts()
                .reindex(PRIORITY_LABELS, fill_value=0)
                .reset_index()
            )
            dist.columns = ["Prioridade", "Empresas"]
            color_map = {k: v["color"] for k, v in PRIORITY_META.items()}
            fig_dist = px.bar(
                dist, x="Prioridade", y="Empresas", color="Prioridade",
                text="Empresas", color_discrete_map=color_map,
                title="Empresas por prioridade",
            )
            fig_dist.update_traces(textposition="outside", marker_line_width=0)
            fig_dist.update_layout(
                template=PLOTLY_TEMPLATE, paper_bgcolor=PLOTLY_PAPER_BGCOLOR,
                plot_bgcolor=PLOTLY_PLOT_BGCOLOR, showlegend=False,
                margin={"l": 20, "r": 20, "t": 48, "b": 20}, height=280,
                xaxis={"showgrid": False}, yaxis={"gridcolor": "rgba(148,163,184,0.12)"},
            )
            st.plotly_chart(fig_dist, use_container_width=True)

    with col_score:
        if "score_prioridade" in df.columns and "prioridade_revisao" in df.columns:
            color_map2 = {k: v["color"] for k, v in PRIORITY_META.items()}
            fig_box = px.box(
                df, x="prioridade_revisao", y="score_prioridade",
                color="prioridade_revisao", color_discrete_map=color_map2,
                category_orders={"prioridade_revisao": PRIORITY_LABELS},
                title="Distribuição do score por prioridade",
                labels={"prioridade_revisao": "Prioridade", "score_prioridade": "Score"},
            )
            fig_box.update_traces(marker_line_width=0)
            fig_box.update_layout(
                template=PLOTLY_TEMPLATE, paper_bgcolor=PLOTLY_PAPER_BGCOLOR,
                plot_bgcolor=PLOTLY_PLOT_BGCOLOR, showlegend=False,
                margin={"l": 20, "r": 20, "t": 48, "b": 20}, height=280,
                xaxis={"showgrid": False}, yaxis={"gridcolor": "rgba(148,163,184,0.12)"},
            )
            st.plotly_chart(fig_box, use_container_width=True)

    # ──────────────────────────────────────────────────────────
    # TABELA
    # ──────────────────────────────────────────────────────────
    render_section_header("Carteira Priorizada", subtitle="Ranking",
                          desc=f"Ordenada por score decrescente — {format_int(total)} empresas.",
                          divider=True)

    display_cols = [c for c in [
        "cnpj_str", "nom_razao_social", "nom_fantasia",
        "prioridade_revisao", "score_prioridade",
        "taxa_divergencia_subclasse", "taxa_consistencia_empresa",
        "qtd_predicoes_distintas_empresa", "par_reclassificacao",
    ] if c in df.columns]
    display_df = df[display_cols].copy().rename(columns={
        "cnpj_str": "CNPJ", "nom_razao_social": "Razão Social",
        "nom_fantasia": "Fantasia", "prioridade_revisao": "Prioridade",
        "score_prioridade": "Score", "taxa_divergencia_subclasse": "Diverg. Subclasse",
        "taxa_consistencia_empresa": "Consistência",
        "qtd_predicoes_distintas_empresa": "Predições distintas",
        "par_reclassificacao": "Par reclassificação",
    })

    col_config: dict = {}
    if "Score" in display_df.columns:
        col_config["Score"] = st.column_config.ProgressColumn(
            "Score", help="Score de prioridade 0–100", min_value=0, max_value=100, format="%.0f")
    if "Diverg. Subclasse" in display_df.columns:
        col_config["Diverg. Subclasse"] = st.column_config.NumberColumn(
            "Diverg. Subclasse", format="%.1f%%")
    if "Consistência" in display_df.columns:
        col_config["Consistência"] = st.column_config.NumberColumn(
            "Consistência", format="%.1f%%")

    st.dataframe(display_df, use_container_width=True, hide_index=True,
                 column_config=col_config, height=480)

    # ──────────────────────────────────────────────────────────
    # EXPORT
    # ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    render_section_header("Exportar Carteira", subtitle="Download",
                          desc=f"Exporta o recorte atual com {format_int(total)} empresas.",
                          divider=False)
    ec1, ec2 = st.columns(2)
    with ec1:
        st.download_button(f"⬇️ Baixar CSV — {format_int(total)} linhas",
                           prepare_download_bytes(df, "csv"),
                           "ranking_reclassificacao.csv", "text/csv",
                           use_container_width=True)
    with ec2:
        st.download_button(f"⬇️ Baixar XLSX — {format_int(total)} linhas",
                           prepare_download_bytes(df, "xlsx"),
                           "ranking_reclassificacao.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)

except Exception as exc:
    st.error(f"Não foi possível carregar o Ranking. Detalhe técnico: {exc}")
    st.exception(exc)
