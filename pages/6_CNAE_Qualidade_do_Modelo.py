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
    LOADING_MESSAGES, PLOTLY_LEVEL_COLOR_MAP, PLOTLY_PAPER_BGCOLOR,
    PLOTLY_PLOT_BGCOLOR, PLOTLY_TEMPLATE, QUALITY_PAGE_SUMMARY,
)
from projetos_especiais.cnae.cnae_core import ensure_data_available, get_model_quality_metrics
from coate_styles import aplicar_estilos
from coate_auth import exigir_acesso
from projetos_especiais.cnae.cnae_utils import (
    format_int, format_pct, make_bar_chart, make_gauge,
    render_empty_state, render_exec_summary, render_kpi_card, render_section_header,
)

aplicar_estilos()
exigir_acesso("cnae")

# ──────────────────────────────────────────────────────────────
# HERO
# ──────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hero">
        {_cnae_img_tag}
        <div class="hero-kicker">🧠 Monitoramento</div>
        <h1>Qualidade do Modelo</h1>
        <p>{QUALITY_PAGE_SUMMARY}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

def _kpi_card(label: str, value: str, delta: str, accent: str, icon: str, help_text: str) -> str:
    return f"""<div class="coate-kpi-card accent-{accent}">
        <div class="coate-kpi-top">
            <div class="coate-kpi-label">{label}</div>
            <div class="coate-kpi-icon">{icon}</div>
        </div>
        <div class="coate-kpi-value">{value}</div>
        <div class="coate-kpi-delta delta-{accent}">{delta}</div>
        <div class="coate-kpi-help">{help_text}</div>
    </div>"""


try:
    ensure_data_available()

    with st.spinner(LOADING_MESSAGES["qualidade"]):
        quality = get_model_quality_metrics()

    acc  = quality["acuracia"]
    conf = quality["confusoes"]
    pred = quality["distribuicao_prevista"]
    aus  = quality["predicao_ausente"].iloc[0]
    cons = quality["consistencia_empresa"]

    # ──────────────────────────────────────────────────────────
    # KPIs
    # ──────────────────────────────────────────────────────────
    render_section_header("Indicadores de Cobertura", subtitle="KPIs", divider=False)

    taxa_aus = float(aus["taxa_predicao_ausente"] or 0)
    qtd_aus = int(aus["qtd_predicao_ausente"] or 0)
    total_reg = int(aus["total_registros"] or 0)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            _kpi_card(
                "Predição Ausente",
                format_pct(taxa_aus, 1),
                "Quanto menor, melhor",
                "warning" if taxa_aus > 0.05 else "success",
                "❔",
                "Proporção de registros sem predição final válida.",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _kpi_card(
                "Qtd. sem Predição",
                format_int(qtd_aus),
                "Registros ausentes",
                "danger",
                "🧩",
                "Total absoluto de registros com predição ausente.",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            _kpi_card(
                "Total Avaliado",
                format_int(total_reg),
                "Base completa",
                "primary",
                "🗂️",
                "Total de registros na base avaliada.",
            ),
            unsafe_allow_html=True,
        )

    # Resumo executivo
    if not acc.empty:
        sub_row = acc[acc["nivel"].str.lower() == "subclasse"]
        sub_acc = float(sub_row["taxa_acerto"].values[0]) if not sub_row.empty else 0.0
        st.markdown("<br>", unsafe_allow_html=True)
        render_exec_summary(
            f"O modelo apresenta acerto de <strong>{format_pct(sub_acc, 1)}</strong> no nível mais "
            f"granular (subclasse), com <strong>{format_pct(aus['taxa_predicao_ausente'], 1)}</strong> "
            f"de predições ausentes em um universo de <strong>{format_int(aus['total_registros'])}</strong> registros."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────
    # GAUGE + ACURÁCIA POR NÍVEL
    # ──────────────────────────────────────────────────────────
    render_section_header("Acurácia por Nível CNAE", subtitle="Precisão",
                          desc="Gauge para subclasse (mais granular) e barras para todos os níveis.",
                          divider=True)

    col_gauge, col_acc = st.columns([1, 1.5])

    with col_gauge:
        if not acc.empty:
            sub_row = acc[acc["nivel"].str.lower() == "subclasse"]
            sub_acc = float(sub_row["taxa_acerto"].values[0]) if not sub_row.empty else 0.0
            fig_gauge = make_gauge(sub_acc, "Acerto — Subclasse")
            st.plotly_chart(fig_gauge, use_container_width=True)
        else:
            render_empty_state("Dados de acurácia indisponíveis.", icon="📉")

    with col_acc:
        if not acc.empty:
            fig_acc = make_bar_chart(acc, x="nivel", y="taxa_acerto", color="nivel",
                                     text_auto=".1%", color_discrete_map=PLOTLY_LEVEL_COLOR_MAP,
                                     title="Taxa de acerto por nível CNAE")
            fig_acc.update_layout(yaxis_tickformat=".0%", yaxis_title="Taxa de acerto",
                                  xaxis_title="Nível CNAE", showlegend=False, yaxis_range=[0, 1.05])
            st.plotly_chart(fig_acc, use_container_width=True)
        else:
            render_empty_state("Dados de acurácia indisponíveis.", icon="📉")

    # ──────────────────────────────────────────────────────────
    # CONSISTÊNCIA + DISTRIBUIÇÃO PREVISTA
    # ──────────────────────────────────────────────────────────
    render_section_header("Consistência e Distribuição Prevista", subtitle="Análise",
                          desc="Consistência média por faixa de prioridade e top classes previstas.",
                          divider=True)

    col3, col4 = st.columns(2)

    with col3:
        if not cons.empty:
            fig_cons = make_bar_chart(cons, x="prioridade_revisao", y="consistencia_media",
                                      color="prioridade_revisao", text_auto=".1%",
                                      color_discrete_map={"Alta": "#ef4444", "Média": "#f59e0b", "Baixa": "#22c55e"},
                                      title="Consistência média por prioridade")
            fig_cons.update_layout(yaxis_tickformat=".0%", yaxis_title="Consistência média",
                                   xaxis_title="Prioridade", showlegend=False, yaxis_range=[0, 1.05])
            st.plotly_chart(fig_cons, use_container_width=True)
        else:
            render_empty_state("Dados de consistência indisponíveis.", icon="📐")

    with col4:
        if not pred.empty:
            fig_pred = make_bar_chart(pred.sort_values("quantidade"), x="quantidade",
                                      y="classe_prevista", orientation="h", text_auto=True,
                                      title="Top 25 — distribuição das classes previstas")
            fig_pred.update_layout(yaxis_title="Classe prevista", xaxis_title="Quantidade",
                                   showlegend=False, height=440)
            st.plotly_chart(fig_pred, use_container_width=True)
        else:
            render_empty_state("Distribuição prevista indisponível.", icon="📊")

    # ──────────────────────────────────────────────────────────
    # HEATMAP DE CONFUSÕES (novo)
    # ──────────────────────────────────────────────────────────
    render_section_header("Mapa de Calor de Confusões", subtitle="Heatmap",
                          desc="Intensidade das confusões entre classes reais e preditas.",
                          divider=True)

    if not conf.empty:
        top_reais = conf["cnae_real"].value_counts().head(12).index.tolist()
        top_pred  = conf["cnae_predito"].value_counts().head(12).index.tolist()
        conf_filt = conf[conf["cnae_real"].isin(top_reais) & conf["cnae_predito"].isin(top_pred)]

        if not conf_filt.empty:
            pivot_conf = conf_filt.pivot_table(
                index="cnae_real", columns="cnae_predito", values="quantidade", fill_value=0
            )
            fig_hm = px.imshow(
                pivot_conf, aspect="auto", text_auto=True,
                color_continuous_scale=[[0, "#0f172a"], [0.3, "#1d4ed8"],
                                        [0.7, "#f59e0b"], [1.0, "#ef4444"]],
                title="Heatmap — classes reais × preditas (top 12 cada)",
                labels={"x": "Predito", "y": "Real", "color": "Ocorrências"},
            )
            fig_hm.update_traces(textfont_size=10)
            fig_hm.update_layout(
                template=PLOTLY_TEMPLATE, paper_bgcolor=PLOTLY_PAPER_BGCOLOR,
                plot_bgcolor=PLOTLY_PLOT_BGCOLOR,
                margin={"l": 20, "r": 20, "t": 52, "b": 20},
                coloraxis_colorbar=dict(title="Qtd.", thickness=12, len=0.8),
                xaxis=dict(tickangle=-35),
            )
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            render_empty_state("Dados insuficientes para o heatmap.", icon="🗓️")
    else:
        render_empty_state("Nenhuma confusão encontrada.", icon="✅")

    # ──────────────────────────────────────────────────────────
    # PARES DE CONFUSÃO — GRÁFICOS
    # ──────────────────────────────────────────────────────────
    render_section_header("Pares de Confusão Mais Frequentes", subtitle="Confusões",
                          desc="Classes reais mais confundidas pelo modelo.",
                          divider=True)

    col5, col6 = st.columns(2)

    with col5:
        if not conf.empty:
            fig_conf = make_bar_chart(conf.sort_values("quantidade"), x="quantidade",
                                      y="cnae_real", orientation="h", text_auto=True,
                                      title="Classes reais mais confusas")
            fig_conf.update_layout(yaxis_title="CNAE real", xaxis_title="Quantidade",
                                   showlegend=False, height=400)
            st.plotly_chart(fig_conf, use_container_width=True)
        else:
            render_empty_state("Sem pares de confusão.", "Nenhum erro real × predito encontrado.", icon="✅")

    with col6:
        if not conf.empty:
            fig_conf2 = make_bar_chart(conf.sort_values("quantidade"), x="quantidade",
                                       y="cnae_predito", orientation="h", text_auto=True,
                                       title="Classes mais previstas erroneamente")
            fig_conf2.update_layout(yaxis_title="CNAE predito (incorreto)", xaxis_title="Quantidade",
                                    showlegend=False, height=400)
            st.plotly_chart(fig_conf2, use_container_width=True)
        else:
            render_empty_state("Dados insuficientes.", icon="📉")

    # ──────────────────────────────────────────────────────────
    # TABELA DE CONFUSÕES
    # ──────────────────────────────────────────────────────────
    render_section_header("Tabela Detalhada de Confusões", subtitle="Detalhe",
                          desc="Pares real × predito ordenados por frequência decrescente.",
                          divider=True)

    if not conf.empty:
        st.dataframe(
            conf.rename(columns={"cnae_real": "CNAE Real", "cnae_predito": "CNAE Predito",
                                  "quantidade": "Ocorrências"}),
            use_container_width=True, hide_index=True,
            column_config={
                "Ocorrências": st.column_config.NumberColumn(
                    "Ocorrências", format="%d",
                    help="Número de registros onde essa confusão ocorreu.")
            },
        )
    else:
        render_empty_state("Tabela de confusões vazia.", icon="📋")

except Exception as exc:
    st.error(f"Não foi possível carregar a Qualidade do Modelo. Detalhe técnico: {exc}")
    st.exception(exc)
