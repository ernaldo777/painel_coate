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

import html

import plotly.express as px
import streamlit as st

from projetos_especiais.cnae.cnae_config import (
    ALERT_HIGH_PRIORITY_SHARE_THRESHOLD,
    ALERT_SUBCLASSE_DIVERGENCE_THRESHOLD,
    HEATMAP_COLOR_SCALE,
    LOADING_MESSAGES,
    PLOTLY_LEVEL_COLOR_MAP,
    PLOTLY_PAPER_BGCOLOR,
    PLOTLY_PLOT_BGCOLOR,
    PLOTLY_TEMPLATE,
    SUMMARY_TOP_PAIRS_LIMIT,
)
from projetos_especiais.cnae.cnae_core import (
    ensure_data_available,
    fetch_df,
    get_accuracy_by_level,
    get_distribution,
    get_kpis,
    get_runtime_diagnostics,
    get_top_pairs,
    monthly_base_sql,
)
from coate_styles import aplicar_estilos
from coate_auth import exigir_acesso
from projetos_especiais.cnae.cnae_utils import (
    apply_standard_figure_layout,
    format_int,
    format_pct,
    make_bar_chart,
    make_gauge,
    make_line_chart,
    render_alert,
    render_empty_state,
    render_exec_summary,
    render_kpi_card,
    render_section_header,
)

aplicar_estilos()
exigir_acesso("cnae")


def _kpi_card(label: str, value: str, delta: str, accent: str, icon: str, help_text: str) -> str:
    return f"""<div class="coate-kpi-card accent-{accent}">
        <div class="coate-kpi-top">
            <div class="coate-kpi-label">{html.escape(label)}</div>
            <div class="coate-kpi-icon">{icon}</div>
        </div>
        <div class="coate-kpi-value">{value}</div>
        <div class="coate-kpi-delta delta-{accent}">{html.escape(delta)}</div>
        <div class="coate-kpi-help">{html.escape(help_text)}</div>
    </div>"""

# ──────────────────────────────────────────────────────────────
# PAGE HEADER
# ──────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hero">
        {_cnae_img_tag}
        <div class="hero-kicker">📊 Painel Analítico</div>
        <h1>Visão Geral</h1>
        <p>
            Leitura executiva do universo analisado — acerto, divergência,
            estabilidade e potenciais carteiras de revisão.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    ensure_data_available()

    # ──────────────────────────────────────────────────────────
    # LOAD DATA
    # ──────────────────────────────────────────────────────────
    with st.spinner(LOADING_MESSAGES["kpis"]):
        diag = get_runtime_diagnostics()
        kpi = get_kpis()
        acc = get_accuracy_by_level()
        secao = get_distribution("cnae_secao_str", 12, monthly=True)
        divisao = get_distribution("cnae_divisao_str", 15, monthly=True)
        pairs = get_top_pairs(SUMMARY_TOP_PAIRS_LIMIT)

        temporal = fetch_df(
            f"WITH mensal AS ({monthly_base_sql()}) "
            "SELECT mes_snapshot, "
            "AVG(flag_divergencia_subclasse) AS taxa_divergencia_subclasse "
            "FROM mensal WHERE mes_snapshot IS NOT NULL "
            "GROUP BY 1 ORDER BY 1"
        )

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

    render_section_header(
        "Diagnóstico da Base Carregada",
        subtitle="Verificação rápida",
        desc="Confirme abaixo qual parquet está em uso e qual universo ele entrega antes de interpretar os KPIs.",
        divider=False,
    )

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.markdown(
            _kpi_card(
                "Linhas do Parquet",
                format_int(diag.get("total_linhas", 0)),
                "Arquivo realmente carregado",
                "primary",
                "🗂️",
                "Quantidade total de linhas lidas diretamente do parquet em uso.",
            ),
            unsafe_allow_html=True,
        )
    with d2:
        st.markdown(
            _kpi_card(
                "CNPJs Distintos",
                format_int(diag.get("cnpjs_normalizados_distintos", 0)),
                "Após normalização do CNPJ",
                "info",
                "🏢",
                "Total de CNPJs únicos após a mesma padronização aplicada pelo painel.",
            ),
            unsafe_allow_html=True,
        )
    with d3:
        st.markdown(
            _kpi_card(
                "Seq. Contribuintes",
                format_int(diag.get("seq_contribuinte_distintos", 0)),
                "Cardinalidade técnica",
                "warning",
                "🔢",
                "Quantidade distinta de seq_contribuinte encontrada no parquet carregado.",
            ),
            unsafe_allow_html=True,
        )
    with d4:
        intervalo = "—"
        if diag.get("menor_snapshot") and diag.get("maior_snapshot"):
            intervalo = f"{diag['menor_snapshot']} a {diag['maior_snapshot']}"
        st.markdown(
            _kpi_card(
                "Intervalo Snapshot",
                intervalo,
                "Menor e maior data",
                "success",
                "🗓️",
                "Intervalo mínimo e máximo de dt_snapshot encontrado no parquet.",
            ),
            unsafe_allow_html=True,
        )

    with st.expander("Detalhes técnicos do arquivo carregado", expanded=False):
        st.markdown(
            f"""
            **Parquet em uso:** `{diag.get('path_real', '—')}`  
            **Caminho padrão esperado:** `{diag.get('path_default', '—')}`  
            **Variável `CNAE_DATA_PATH` ativa:** {'Sim' if diag.get('usa_env_override') else 'Não'}  
            **Valor de `CNAE_DATA_PATH`:** `{diag.get('env_override') or '—'}`  
            **Tamanho do arquivo:** `{(f"{diag.get('tamanho_mb', 0):.1f} MB" if diag.get('tamanho_mb') is not None else '—')}`  
            **Última modificação:** `{diag.get('modificado_em') or '—'}`  
            **Coluna de CNPJ usada:** `{diag.get('coluna_cnpj') or '—'}`  
            **Coluna de snapshot usada:** `{diag.get('coluna_snapshot') or '—'}`  
            **Coluna de seq usada:** `{diag.get('coluna_seq') or '—'}`
            """
        )

    if int(diag.get("cnpjs_normalizados_distintos", 0)) <= 1000:
        render_alert(
            "O universo carregado está abaixo de 1.000 CNPJs distintos. Se o estudo completo deveria ter milhares de empresas, revise imediatamente o parquet em uso, a variável CNAE_DATA_PATH e reinicie a aplicação.",
            variant="warning",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────
    # ALERTS  (before KPIs so they stand out at top)
    # ──────────────────────────────────────────────────────────
    div_sub = float(kpi.get("divergencia_subclasse") or 0)
    taxa_alta = float(kpi.get("taxa_prioridade_alta") or 0)

    if div_sub > ALERT_SUBCLASSE_DIVERGENCE_THRESHOLD:
        render_alert(
            f"Divergência em subclasse ({format_pct(div_sub)}) está acima do "
            f"limiar gerencial configurado ({format_pct(ALERT_SUBCLASSE_DIVERGENCE_THRESHOLD)}).",
            variant="danger",
        )

    if taxa_alta > ALERT_HIGH_PRIORITY_SHARE_THRESHOLD:
        render_alert(
            f"Proporção de empresas em prioridade Alta ({format_pct(taxa_alta)}) "
            f"supera o limite configurado ({format_pct(ALERT_HIGH_PRIORITY_SHARE_THRESHOLD)}).",
            variant="warning",
        )

    # ──────────────────────────────────────────────────────────
    # KPI ROW
    # ──────────────────────────────────────────────────────────
    render_section_header(
        "Indicadores do Universo",
        subtitle="KPIs",
        desc="Resumo quantitativo do recorte completo da base.",
        divider=False,
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    total_emp = kpi.get("total_empresas", 0)
    total_reg = kpi.get("total_registros", 0)
    osc = kpi.get("empresas_oscilantes", 0)
    consistencia = kpi.get("consistencia_media_empresas", 0)
    pct_osc = format_pct(int(osc) / max(int(total_emp), 1))

    with c1:
        st.markdown(
            _kpi_card(
                "Empresas",
                format_int(total_emp),
                "Universo consolidado",
                "primary",
                "🏢",
                "Total de CNPJs únicos na base.",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _kpi_card(
                "Acerto Subclasse",
                format_pct(kpi.get("acerto_subclasse"), 1),
                "Quanto maior, melhor",
                "success",
                "✅",
                "Percentual de registros com predição correta no nível mais granular.",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            _kpi_card(
                "Divergência Subclasse",
                format_pct(kpi.get("divergencia_subclasse"), 1),
                "Quanto maior, mais revisão",
                "danger",
                "⚠️",
                "Proporção de registros onde CNAE real difere do predito na subclasse.",
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            _kpi_card(
                "Consistência Média",
                format_pct(consistencia, 1),
                f"{format_int(total_reg)} registros mensais",
                "info",
                "🧭",
                "Quanto maior, mais estável a predição ao longo do tempo por empresa.",
            ),
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            _kpi_card(
                "Empresas Oscilantes",
                format_int(osc),
                f"{pct_osc} do universo",
                "warning",
                "🔁",
                "Empresas com mais de uma predição distinta ao longo dos meses.",
            ),
            unsafe_allow_html=True,
        )
    with c6:
        st.markdown(
            _kpi_card(
                "Prioridade Alta",
                format_pct(kpi.get("taxa_prioridade_alta"), 1),
                "Fila crítica de revisão",
                "danger",
                "🚨",
                "Proporção de empresas classificadas como prioridade Alta para revisão.",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────
    # EXECUTIVE SUMMARY
    # ──────────────────────────────────────────────────────────
    render_section_header(
        "Síntese Automática do Recorte",
        subtitle="Resumo executivo",
        divider=True,
    )

    consistencia = kpi.get("consistencia_media_empresas", 0)
    summary_html = (
        f"De <strong>{format_int(total_emp)} empresas</strong> e "
        f"<strong>{format_int(total_reg)} registros</strong> analisados, "
        f"<strong>{format_pct(kpi.get('divergencia_subclasse'), 1)}</strong> apresentam "
        f"divergência média em subclasse. "
        f"A consistência média por empresa é de "
        f"<strong>{format_pct(consistencia, 1)}</strong>, "
        f"com <strong>{format_int(osc)}</strong> empresas oscilantes e "
        f"<strong>{format_pct(kpi.get('taxa_prioridade_alta'), 1)}</strong> em prioridade Alta."
    )
    render_exec_summary(summary_html)

    # ──────────────────────────────────────────────────────────
    # GAUGE + ACURÁCIA POR NÍVEL
    # ──────────────────────────────────────────────────────────
    render_section_header(
        "Acurácia do Modelo por Nível CNAE",
        subtitle="Qualidade preditiva",
        desc="Gauge de acerto em subclasse (nível mais granular) e barras de acerto por nível.",
        divider=True,
    )

    col_gauge, col_acc = st.columns([1, 1.5])

    with col_gauge:
        fig_gauge = make_gauge(
            float(kpi.get("acerto_subclasse") or 0),
            "Taxa de acerto — Subclasse",
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_acc:
        if not acc.empty:
            fig_acc = make_bar_chart(
                acc,
                x="nivel",
                y="taxa_acerto",
                color="nivel",
                text_auto=".1%",
                color_discrete_map=PLOTLY_LEVEL_COLOR_MAP,
                title="Taxa de acerto por nível CNAE",
            )
            fig_acc.update_layout(
                yaxis_tickformat=".0%",
                xaxis_title="Nível CNAE",
                yaxis_title="Taxa de acerto",
                showlegend=False,
                yaxis_range=[0, 1.05],
            )
            st.plotly_chart(fig_acc, use_container_width=True)
        else:
            render_empty_state("Dados de acurácia não disponíveis.", icon="📉")

    # ──────────────────────────────────────────────────────────
    # HEATMAP + TEMPORAL
    # ──────────────────────────────────────────────────────────
    render_section_header(
        "Divergência ao Longo do Tempo",
        subtitle="Análise temporal",
        desc="Heatmap de divergência por nível × mês e evolução da divergência em subclasse.",
        divider=True,
    )

    col_heat, col_time = st.columns(2)

    with col_heat:
        if not heat.empty:
            level_order = ["secao", "divisao", "grupo", "classe", "subclasse"]
            pivot = (
                heat.pivot(index="nivel", columns="mes_snapshot", values="taxa")
                .fillna(0)
                .reindex([l for l in level_order if l in heat["nivel"].unique()])
            )
            fig_heat = px.imshow(
                pivot,
                aspect="auto",
                color_continuous_scale=HEATMAP_COLOR_SCALE,
                text_auto=".0%",
                labels={"x": "Mês", "y": "Nível", "color": "Divergência"},
                title="Heatmap de divergência por nível e mês",
            )
            fig_heat.update_traces(textfont_size=11)
            fig_heat.update_layout(
                template=PLOTLY_TEMPLATE,
                paper_bgcolor=PLOTLY_PAPER_BGCOLOR,
                plot_bgcolor=PLOTLY_PLOT_BGCOLOR,
                margin={"l": 28, "r": 28, "t": 52, "b": 28},
                coloraxis_colorbar=dict(
                    title="Taxa",
                    tickformat=".0%",
                    thickness=12,
                    len=0.8,
                ),
                font=dict(size=12),
            )
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            render_empty_state(
                "Sem série temporal para heatmap.",
                "A base precisa de pelo menos um mês de snapshot válido.",
                icon="🗓️",
            )

    with col_time:
        if not temporal.empty and temporal["mes_snapshot"].nunique() > 1:
            fig_time = make_line_chart(
                temporal,
                x="mes_snapshot",
                y="taxa_divergencia_subclasse",
                title="Evolução da divergência em subclasse",
                yaxis_tickformat=".0%",
            )
            fig_time.update_layout(
                xaxis_title="Mês snapshot",
                yaxis_title="Taxa de divergência",
            )
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            render_empty_state(
                "Série temporal insuficiente.",
                "Com apenas um mês disponível, não é possível traçar evolução temporal.",
                icon="📈",
            )

    # ──────────────────────────────────────────────────────────
    # DISTRIBUIÇÃO POR SEÇÃO / DIVISÃO
    # ──────────────────────────────────────────────────────────
    render_section_header(
        "Distribuição da Base por Nível Hierárquico",
        subtitle="Composição",
        desc="Seção e divisão CNAE real — top registros mais frequentes.",
        divider=True,
    )

    col_secao, col_divisao = st.columns(2)

    with col_secao:
        if not secao.empty:
            fig_sec = make_bar_chart(
                secao.sort_values("quantidade"),
                x="quantidade",
                y="categoria",
                orientation="h",
                text_auto=True,
                title="Distribuição por seção (top 12)",
            )
            fig_sec.update_layout(
                yaxis_title="Seção real",
                xaxis_title="Quantidade de registros",
                showlegend=False,
                height=400,
            )
            st.plotly_chart(fig_sec, use_container_width=True)
        else:
            render_empty_state("Sem dados de seção.", icon="🏷️")

    with col_divisao:
        if not divisao.empty:
            fig_div = make_bar_chart(
                divisao.sort_values("quantidade"),
                x="quantidade",
                y="categoria",
                orientation="h",
                text_auto=True,
                title="Distribuição por divisão (top 15)",
            )
            fig_div.update_layout(
                yaxis_title="Divisão real",
                xaxis_title="Quantidade de registros",
                showlegend=False,
                height=400,
            )
            st.plotly_chart(fig_div, use_container_width=True)
        else:
            render_empty_state("Sem dados de divisão.", icon="🏷️")

    # ──────────────────────────────────────────────────────────
    # PARES DE RECLASSIFICAÇÃO
    # ──────────────────────────────────────────────────────────
    render_section_header(
        "Principais Pares de Reclassificação",
        subtitle="Reclassificação",
        desc=(
            f"Top {SUMMARY_TOP_PAIRS_LIMIT} pares CNAE real → predito mais frequentes "
            "entre as empresas consolidadas."
        ),
        divider=True,
    )

    if not pairs.empty:
        pairs_tree = pairs.copy()
        split = pairs_tree["par_reclassificacao"].str.split(" → ", n=1, expand=True)
        pairs_tree["origem"] = split[0].fillna("Sem CNAE real")
        pairs_tree["destino"] = split[1].fillna("Sem predição") if 1 in split.columns else "Sem predição"

        fig_tree = px.treemap(
            pairs_tree,
            path=[px.Constant("Pares"), "origem", "destino"],
            values="quantidade",
            color="quantidade",
            color_continuous_scale="Blues",
            title="Treemap — Pares de reclassificação por volume",
        )
        fig_tree.update_traces(
            textfont_size=13,
            marker=dict(line=dict(width=1.5, color="#0f172a")),
        )
        fig_tree.update_layout(
            template=PLOTLY_TEMPLATE,
            paper_bgcolor=PLOTLY_PAPER_BGCOLOR,
            plot_bgcolor=PLOTLY_PLOT_BGCOLOR,
            margin={"l": 10, "r": 10, "t": 52, "b": 10},
            coloraxis_colorbar=dict(
                title="Volume",
                thickness=12,
                len=0.7,
            ),
        )
        st.plotly_chart(fig_tree, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        render_section_header(
            "Tabela de Pares",
            subtitle="Detalhe",
            desc="Ranking dos pares por frequência de ocorrência entre empresas.",
            divider=False,
        )
        st.dataframe(
            pairs.rename(columns={
                "par_reclassificacao": "Par de Reclassificação",
                "quantidade": "Empresas",
            }),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Empresas": st.column_config.NumberColumn(
                    "Empresas",
                    help="Quantidade de empresas com esse par de reclassificação",
                    format="%d",
                ),
            },
        )
    else:
        render_empty_state(
            "Nenhum par de reclassificação encontrado.",
            "Verifique se há dados com divergência entre CNAE real e predito.",
            icon="🔄",
        )

except Exception as exc:
    st.error(f"Não foi possível carregar a Visão Geral. Detalhe técnico: {exc}")
    st.exception(exc)
