from __future__ import annotations

import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import base64 as _b64cnae
_cnae_icon_path = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'assets', 'cnae_icon.png'))
_cnae_img_tag = ""
if _os.path.exists(_cnae_icon_path):
    with open(_cnae_icon_path, "rb") as _f:
        _cnae_img_tag = (f'<img src="data:image/png;base64,{_b64cnae.b64encode(_f.read()).decode()}" '
                         f'style="height:52px;border-radius:10px;margin-bottom:0.5rem;display:block;" alt="CNAE">')

import pandas as pd
import plotly.express as px
import streamlit as st

from coate_auth import exigir_acesso
from coate_styles import aplicar_estilos
from projetos_especiais.cnae.cnae_config import LOADING_MESSAGES, SIDEBAR_HELP
from projetos_especiais.cnae.cnae_core import (
    ensure_data_available,
    get_model_pairs_with_impact,
    load_matriz_impacto,
)
from projetos_especiais.cnae.cnae_utils import (
    format_int,
    prepare_download_bytes,
    render_empty_state,
    render_exec_summary,
    render_section_header,
)

aplicar_estilos()
exigir_acesso("cnae")

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

st.markdown(
    f"""
    <div class="hero">
        {_cnae_img_tag}
        <div class="hero-kicker">🧮 Impacto arrecadatório</div>
        <h1>Matriz de Impacto</h1>
        <p>
            Relação entre pares de CNAE do modelo e a matriz de impacto tributário,
            incluindo casos em que a origem ou o destino ficam fora dos decretos.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    ensure_data_available()

    with st.sidebar:
        st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle" style="padding:0 0.2rem;">Filtros da matriz</div>', unsafe_allow_html=True)
        filtro_impacto = st.selectbox(
            "Impacto",
            ["Todos", "AUMENTO", "DIMINUI", "INDIFERENTE", "NÃO MAPEADO"],
            help=SIDEBAR_HELP.get("impacto"),
        )
        somente_mapeados = st.checkbox("Somente pares mapeados", value=True)
        busca = st.text_input("🔍 CNAE, decreto ou segmento", placeholder="Ex.: 4639701 ou 29.560/08")
        limite = st.number_input("Máximo de linhas", min_value=50, max_value=5000, value=500, step=50)

    with st.spinner(LOADING_MESSAGES.get("impacto", "Relacionando matriz de impacto...")):
        matriz = load_matriz_impacto()
        pares = get_model_pairs_with_impact(
            limit=None,
            impact_filter=None if filtro_impacto == "Todos" else filtro_impacto,
            only_mapped=somente_mapeados,
        )

    detalhe = matriz["detalhe"].copy()
    resumo = matriz["resumo"].copy()
    legenda = matriz["legenda"].copy()

    if busca.strip():
        termo = busca.strip().lower()
        alvo_cols = [
            "par_reclassificacao", "cnae_origem_modelo", "cnae_destino_modelo",
            "Decreto Origem", "Decreto Destino", "Segmento Origem", "Segmento Destino",
            "Descrição Origem", "Descrição Destino", "IMPACTO"
        ]
        if not pares.empty:
            mask = pd.Series(False, index=pares.index)
            for col in [c for c in alvo_cols if c in pares.columns]:
                mask = mask | pares[col].astype(str).str.lower().str.contains(termo, na=False)
            pares = pares[mask].copy()

        if not detalhe.empty:
            mask2 = pd.Series(False, index=detalhe.index)
            for col in [c for c in ["CNAE Origem", "CNAE Destino", "Descrição Origem", "Descrição Destino", "Decreto Origem", "Decreto Destino", "Segmento Origem", "Segmento Destino", "IMPACTO"] if c in detalhe.columns]:
                mask2 = mask2 | detalhe[col].astype(str).str.lower().str.contains(termo, na=False)
            detalhe = detalhe[mask2].copy()

    pares_filtrados = pares.copy()
    total_pares = len(pares_filtrados)
    aumento = int((pares_filtrados["IMPACTO"] == "AUMENTO").sum()) if not pares_filtrados.empty else 0
    diminui = int((pares_filtrados["IMPACTO"] == "DIMINUI").sum()) if not pares_filtrados.empty else 0
    empresas = int(pd.to_numeric(pares_filtrados.get("empresas", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not pares_filtrados.empty else 0

    pares = pares_filtrados.head(int(limite)).copy()
    exibidos = len(pares)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(_kpi_card("Pares distintos", format_int(total_pares), f"Exibindo {format_int(exibidos)}", "primary", "🔗", "Quantidade de pares distintos do modelo após os filtros aplicados."), unsafe_allow_html=True)
    with c2:
        st.markdown(_kpi_card("Empresas nos pares", format_int(empresas), "Cobertura do recorte filtrado", "info", "🏢", "Soma de empresas dos pares filtrados, sem duplicação por linhas da matriz."), unsafe_allow_html=True)
    with c3:
        st.markdown(_kpi_card("Impacto Aumento", format_int(aumento), "Pares com efeito positivo", "danger", "📈", "Pares em que a reclassificação tende a elevar a carga."), unsafe_allow_html=True)
    with c4:
        st.markdown(_kpi_card("Impacto Diminui", format_int(diminui), "Pares com redução", "warning", "📉", "Pares em que a reclassificação tende a reduzir a carga."), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if not pares.empty:
        st.caption(f"Exibindo {format_int(exibidos)} de {format_int(total_pares)} pares distintos após os filtros.")
        top_empresas = pares.sort_values("empresas", ascending=False).head(12).copy()
        fig = px.bar(
            top_empresas.sort_values("empresas"),
            x="empresas",
            y="par_reclassificacao",
            orientation="h",
            color="IMPACTO",
            text="empresas",
            title="Pares do modelo com maior volume de empresas",
            color_discrete_map={
                "AUMENTO": "#ef4444",
                "DIMINUI": "#f59e0b",
                "INDIFERENTE": "#3b82f6",
                "NÃO MAPEADO": "#64748b",
            },
        )
        fig.update_layout(height=420, showlegend=True)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

        render_exec_summary(
            f"Após os filtros, há <strong>{format_int(total_pares)} pares distintos</strong> do modelo relacionados à matriz de impacto, cobrindo <strong>{format_int(empresas)} empresas</strong>. "
            f"Dentre esses pares, <strong>{format_int(aumento)}</strong> sinalizam <strong>aumento</strong> esperado de carga e "
            f"<strong>{format_int(diminui)}</strong> sinalizam <strong>diminuição</strong>. "
            f"Quando o CNAE fica fora do universo dos decretos, a chave de comparação usada é <strong>FORA_DO_DECRETO</strong>."
        )
    else:
        render_empty_state("Nenhum par encontrado para os filtros atuais.", "Ajuste os filtros para visualizar a relação entre o modelo e a matriz.", icon="🧮")

    tabs = st.tabs(["Pares do modelo × impacto", "Matriz detalhada", "Resumo decreto × decreto", "Legenda"])

    with tabs[0]:
        render_section_header(
            "Pares do Modelo × Impacto",
            subtitle="Detalhe",
            desc="Cada linha representa um par distinto do modelo, com o respectivo enquadramento consolidado na matriz de impacto.",
            divider=False,
        )
        if pares.empty:
            render_empty_state("Nenhum par disponível.", icon="🔎")
        else:
            exibir = pares.rename(columns={
                "par_reclassificacao": "Par de Reclassificação",
                "cnae_origem_modelo": "CNAE Origem Modelo",
                "cnae_destino_modelo": "CNAE Destino Modelo",
                "CNAE Origem Impacto": "Chave Origem Impacto",
                "CNAE Destino Impacto": "Chave Destino Impacto",
                "empresas": "Empresas",
                "score_medio": "Score Médio",
                "taxa_prioridade_alta": "Taxa Prioridade Alta",
                "IMPACTO": "Impacto",
                "Delta %": "Delta %",
                "Decreto Origem": "Decreto Origem",
                "Decreto Destino": "Decreto Destino",
                "Segmento Origem": "Segmento Origem",
                "Segmento Destino": "Segmento Destino",
                "Descrição Origem": "Descrição Origem",
                "Descrição Destino": "Descrição Destino",
                "Observação": "Observação",
            })
            st.dataframe(
                exibir,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Empresas": st.column_config.NumberColumn("Empresas", format="%d"),
                    "Score Médio": st.column_config.NumberColumn("Score Médio", format="%.1f"),
                    "Taxa Prioridade Alta": st.column_config.NumberColumn("Taxa Prioridade Alta", format="%.1f%%"),
                    "Delta %": st.column_config.NumberColumn("Delta %", format="%.2f"),
                },
            )
            csv_bytes = prepare_download_bytes(exibir, fmt="csv")
            xlsx_bytes = prepare_download_bytes(exibir, fmt="xlsx")
            d1, d2 = st.columns(2)
            with d1:
                st.download_button("Baixar CSV", data=csv_bytes, file_name="pares_modelo_x_impacto.csv", mime="text/csv", use_container_width=True)
            with d2:
                st.download_button("Baixar XLSX", data=xlsx_bytes, file_name="pares_modelo_x_impacto.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    with tabs[1]:
        render_section_header(
            "Matriz Detalhada",
            subtitle="Base de impacto",
            desc="Tabela completa da matriz de impacto por par de CNAE origem → destino.",
            divider=False,
        )
        if detalhe.empty:
            render_empty_state("Matriz detalhada indisponível.", icon="📋")
        else:
            st.dataframe(detalhe, use_container_width=True, hide_index=True)

    with tabs[2]:
        render_section_header(
            "Resumo Decreto × Decreto",
            subtitle="Agregado",
            desc="Síntese por decreto de origem e decreto de destino.",
            divider=False,
        )
        if resumo.empty:
            render_empty_state("Resumo não disponível.", icon="📘")
        else:
            st.dataframe(resumo, use_container_width=True, hide_index=True)

    with tabs[3]:
        render_section_header(
            "Legenda da Matriz",
            subtitle="Interpretação",
            desc="Significado dos campos e do impacto tributário utilizado na matriz.",
            divider=False,
        )
        if legenda.empty:
            render_empty_state("Legenda não encontrada.", icon="ℹ️")
        else:
            st.dataframe(legenda, use_container_width=True, hide_index=True)

except Exception as exc:
    st.error(f"Não foi possível carregar a Matriz de Impacto. Detalhe técnico: {exc}")
    st.exception(exc)
