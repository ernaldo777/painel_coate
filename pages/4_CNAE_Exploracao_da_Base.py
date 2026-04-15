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

import plotly.express as px
import streamlit as st

from projetos_especiais.cnae.cnae_config import (
    DETAIL_PAGE_SIZE, HEATMAP_COLOR_SCALE, LOADING_MESSAGES,
    MAX_EXPORT_ROWS, PLOTLY_PAPER_BGCOLOR, PLOTLY_PLOT_BGCOLOR, PLOTLY_TEMPLATE,
)
from projetos_especiais.cnae.cnae_core import (
    ensure_data_available, fetch_df, get_available_snapshot_months,
    load_monthly_base, monthly_base_sql,
)
from coate_styles import aplicar_estilos
from coate_auth import exigir_acesso
from projetos_especiais.cnae.cnae_utils import (
    format_int, format_pct, make_bar_chart, prepare_download_bytes,
    render_empty_state, render_section_header,
)


def _kpi_card(label: str, value: str, delta: str, accent: str, icon: str, help_text: str = "") -> str:
    return f"""<div class="coate-kpi-card accent-{accent}">
        <div class="coate-kpi-top">
            <div class="coate-kpi-label">{label}</div>
            <div class="coate-kpi-icon">{icon}</div>
        </div>
        <div class="coate-kpi-value">{value}</div>
        <div class="coate-kpi-delta delta-{accent}">{delta}</div>
        <div class="coate-kpi-help">{help_text}</div>
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
        <div class="hero-kicker">🧪 Análise técnica</div>
        <h1>Exploração da Base</h1>
        <p>
            Leitura técnica da base mensal com filtros amplos —
            inspecione subconjuntos, visualize divergências e exporte os dados.
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
            '<div class="section-subtitle" style="padding:0 0.2rem;">Filtros</div>',
            unsafe_allow_html=True,
        )
        cnpj = st.text_input("CNPJ exato", placeholder="Ex.: 07526557000100")
        meses = get_available_snapshot_months()
        mes = st.selectbox("Mês snapshot", ["Todos"] + meses)
        somente_div = st.checkbox("Somente divergentes em subclasse")
        somente_aus = st.checkbox("Somente predição ausente")
        limite = st.number_input("Máximo de linhas", min_value=50,
                                 max_value=MAX_EXPORT_ROWS, value=DETAIL_PAGE_SIZE, step=50)

    filters: dict = {
        "cnpj_str": cnpj.strip() or None,
        "mes_snapshot": None if mes == "Todos" else mes,
        "flag_divergente": somente_div,
        "predicao_ausente": somente_aus,
    }

    # ──────────────────────────────────────────────────────────
    # LOAD
    # ──────────────────────────────────────────────────────────
    with st.spinner(LOADING_MESSAGES["exploracao"]):
        df = load_monthly_base(limit=int(limite), filters=filters)

    total = len(df)
    taxa_div = float(df["flag_divergencia_subclasse"].mean()) if total and "flag_divergencia_subclasse" in df.columns else 0.0
    taxa_aus = float(df["flag_predicao_ausente"].mean()) if total and "flag_predicao_ausente" in df.columns else 0.0

    # ──────────────────────────────────────────────────────────
    # KPIs
    # ──────────────────────────────────────────────────────────
    render_section_header("Recorte Explorado", subtitle="KPIs", divider=False)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            _kpi_card(
                "Registros no recorte",
                format_int(total),
                "Base mensal filtrada",
                "primary",
                "🗂️",
                "Quantidade de registros retornados pelos filtros atuais.",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _kpi_card(
                "Divergência Subclasse",
                format_pct(taxa_div, 1),
                "No recorte atual",
                "danger" if taxa_div > 0.3 else "warning",
                "⚠️",
                "Proporção do recorte em que CNAE real e predito divergem na subclasse.",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            _kpi_card(
                "Predição Ausente",
                format_pct(taxa_aus, 1),
                "Registros sem predição",
                "warning" if taxa_aus > 0 else "success",
                "❔",
                "Percentual de registros em que o modelo não retornou predição de subclasse.",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if df.empty:
        render_empty_state("Nenhum registro encontrado para os filtros selecionados.",
                           "Ajuste o CNPJ, mês ou remova os checkboxes.", icon="🧪")
        st.stop()

    # ──────────────────────────────────────────────────────────
    # HEATMAP de divergência por nível × mês (novo)
    # ──────────────────────────────────────────────────────────
    render_section_header("Divergência por Nível e Mês", subtitle="Heatmap",
                          desc="Taxa de divergência entre CNAE real e predito por nível hierárquico.",
                          divider=True)

    try:
        heat = fetch_df(
            f"WITH mensal AS ({monthly_base_sql()}) "
            "SELECT mes_snapshot, 'secao' AS nivel, AVG(flag_divergencia_secao) AS taxa "
            "FROM mensal WHERE mes_snapshot IS NOT NULL GROUP BY 1 "
            "UNION ALL "
            "SELECT mes_snapshot, 'divisao', AVG(flag_divergencia_divisao) FROM mensal "
            "WHERE mes_snapshot IS NOT NULL GROUP BY 1 "
            "UNION ALL "
            "SELECT mes_snapshot, 'grupo', AVG(flag_divergencia_grupo) FROM mensal "
            "WHERE mes_snapshot IS NOT NULL GROUP BY 1 "
            "UNION ALL "
            "SELECT mes_snapshot, 'classe', AVG(flag_divergencia_classe) FROM mensal "
            "WHERE mes_snapshot IS NOT NULL GROUP BY 1 "
            "UNION ALL "
            "SELECT mes_snapshot, 'subclasse', AVG(flag_divergencia_subclasse) FROM mensal "
            "WHERE mes_snapshot IS NOT NULL GROUP BY 1"
        )
        if not heat.empty and heat["mes_snapshot"].nunique() > 0:
            level_order = ["secao", "divisao", "grupo", "classe", "subclasse"]
            pivot = (
                heat.pivot(index="nivel", columns="mes_snapshot", values="taxa")
                .fillna(0)
                .reindex([l for l in level_order if l in heat["nivel"].unique()])
            )
            fig_heat = px.imshow(
                pivot, aspect="auto", color_continuous_scale=HEATMAP_COLOR_SCALE,
                text_auto=".0%", labels={"x": "Mês", "y": "Nível", "color": "Divergência"},
                title="Heatmap de divergência por nível e mês",
            )
            fig_heat.update_traces(textfont_size=11)
            fig_heat.update_layout(
                template=PLOTLY_TEMPLATE, paper_bgcolor=PLOTLY_PAPER_BGCOLOR,
                plot_bgcolor=PLOTLY_PLOT_BGCOLOR,
                margin={"l": 28, "r": 28, "t": 52, "b": 28},
                coloraxis_colorbar=dict(title="Taxa", tickformat=".0%", thickness=12, len=0.8),
            )
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            render_empty_state("Dados insuficientes para heatmap.", icon="🗓️")
    except Exception:
        render_empty_state("Heatmap indisponível para este recorte.", icon="🗓️")

    # ──────────────────────────────────────────────────────────
    # DISTRIBUIÇÃO DAS CLASSES PREVISTAS
    # ──────────────────────────────────────────────────────────
    render_section_header("Distribuição das Classes Previstas", subtitle="Composição",
                          desc="Top 15 subclasses preditas no recorte atual.", divider=True)

    if "cnae_subclasse_pred_str" in df.columns:
        dist = (
            df["cnae_subclasse_pred_str"].fillna("Sem predição")
            .value_counts().head(15).reset_index()
        )
        dist.columns = ["Subclasse prevista", "Quantidade"]
        fig_dist = make_bar_chart(
            dist.sort_values("Quantidade"), x="Quantidade", y="Subclasse prevista",
            orientation="h", text_auto=True, title="Top 15 subclasses preditas",
        )
        fig_dist.update_layout(yaxis_title="Subclasse prevista",
                               xaxis_title="Quantidade de registros",
                               showlegend=False, height=420)
        st.plotly_chart(fig_dist, use_container_width=True)
    else:
        render_empty_state("Coluna de predição não disponível.", icon="📊")

    # ──────────────────────────────────────────────────────────
    # TABELA
    # ──────────────────────────────────────────────────────────
    render_section_header("Tabela de Registros", subtitle="Dados",
                          desc=f"Exibindo até {format_int(total)} registros do recorte mensal.",
                          divider=True)

    col_config_tbl: dict = {}
    if "flag_divergencia_subclasse" in df.columns:
        col_config_tbl["flag_divergencia_subclasse"] = st.column_config.NumberColumn(
            "Diverg. Subclasse", format="%d")
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config=col_config_tbl, height=440)

    # ──────────────────────────────────────────────────────────
    # EXPORT
    # ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    render_section_header("Exportar Recorte", subtitle="Download",
                          desc=f"Exporta os {format_int(total)} registros visíveis.", divider=False)
    b1, b2 = st.columns(2)
    with b1:
        st.download_button(f"⬇️ Baixar CSV — {format_int(total)} linhas",
                           prepare_download_bytes(df, "csv"), "exploracao_base.csv",
                           "text/csv", use_container_width=True)
    with b2:
        st.download_button(f"⬇️ Baixar XLSX — {format_int(total)} linhas",
                           prepare_download_bytes(df, "xlsx"), "exploracao_base.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)

except Exception as exc:
    st.error(f"Não foi possível carregar a Exploração da Base. Detalhe técnico: {exc}")
    st.exception(exc)
