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
from projetos_especiais.cnae.cnae_core import load_cnaes_por_decreto
from projetos_especiais.cnae.cnae_utils import (
    format_int,
    prepare_download_bytes,
    render_empty_state,
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
        <div class="hero-kicker">📚 Decretos e segmentos</div>
        <h1>CNAEs por Decreto</h1>
        <p>
            Consulta da lista de CNAEs mapeados por decreto, com resumo por segmento
            e detalhamento do texto tributário associado a cada enquadramento.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    with st.spinner(LOADING_MESSAGES.get("decretos", "Carregando decretos...")):
        pacote = load_cnaes_por_decreto()

    resumo = pacote["resumo"].copy()
    lista = pacote["lista"].copy()
    detalhes = pacote["detalhes"].copy()

    with st.sidebar:
        st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle" style="padding:0 0.2rem;">Filtros dos decretos</div>', unsafe_allow_html=True)
        decreto = st.selectbox(
            "Decreto",
            ["Todos"] + sorted(lista["Decreto Principal"].dropna().astype(str).unique().tolist()),
            help=SIDEBAR_HELP.get("decreto"),
        )
        busca = st.text_input("🔍 Buscar CNAE ou descrição", placeholder="Ex.: 4644301 ou farmacêuticos")

    if decreto != "Todos":
        lista = lista[lista["Decreto Principal"].astype(str) == decreto].copy()
        if not resumo.empty and "Decreto" in resumo.columns:
            resumo = resumo[resumo["Decreto"].astype(str) == decreto].copy()
        if not detalhes.empty and "Decreto(s) na Planilha" in detalhes.columns:
            detalhes = detalhes[detalhes["Decreto(s) na Planilha"].astype(str).str.contains(decreto, na=False)].copy()

    if busca.strip():
        termo = busca.strip().lower()
        mask = (
            lista["CNAE"].astype(str).str.contains(termo, na=False)
            | lista["Descrição"].astype(str).str.lower().str.contains(termo, na=False)
            | lista["Segmento"].astype(str).str.lower().str.contains(termo, na=False)
        )
        lista = lista[mask].copy()
        if not detalhes.empty:
            mask2 = (
                detalhes["CNAE"].astype(str).str.contains(termo, na=False)
                | detalhes["Descrição"].astype(str).str.lower().str.contains(termo, na=False)
                | detalhes["Texto Tributação Completo"].astype(str).str.lower().str.contains(termo, na=False)
            )
            detalhes = detalhes[mask2].copy()

    total_cnaes = len(lista)
    total_decretos = resumo["Decreto"].nunique() if not resumo.empty and "Decreto" in resumo.columns else 0
    multi = int(lista["Todos os Decretos"].astype(str).str.contains(",", na=False).sum()) if not lista.empty else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_kpi_card("CNAEs no recorte", format_int(total_cnaes), "Lista filtrada", "primary", "🏷️", "Quantidade de CNAEs exibidos após os filtros."), unsafe_allow_html=True)
    with c2:
        st.markdown(_kpi_card("Decretos", format_int(total_decretos), "Cobertura do recorte", "info", "📘", "Quantidade de decretos presentes no recorte atual."), unsafe_allow_html=True)
    with c3:
        st.markdown(_kpi_card("CNAEs em múltiplos decretos", format_int(multi), "Sobreposição relevante", "warning", "🔁", "CNAEs que aparecem vinculados a mais de um decreto na planilha."), unsafe_allow_html=True)

    if not resumo.empty and "Qtd CNAEs" in resumo.columns:
        fig = px.bar(
            resumo.sort_values("Qtd CNAEs"),
            x="Qtd CNAEs",
            y="Segmento",
            orientation="h",
            text="Qtd CNAEs",
            color="Decreto",
            title="Quantidade de CNAEs por segmento/decreto",
        )
        fig.update_layout(height=360, showlegend=False)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    tabs = st.tabs(["Resumo", "Lista completa", "Texto por decreto"])

    with tabs[0]:
        render_section_header(
            "Resumo por Decreto",
            subtitle="Cobertura",
            desc="Quantidade de CNAEs e base de cálculo associada a cada decreto.",
            divider=False,
        )
        if resumo.empty:
            render_empty_state("Nenhum decreto encontrado para o recorte.", icon="📘")
        else:
            st.dataframe(resumo, use_container_width=True, hide_index=True)

    with tabs[1]:
        render_section_header(
            "Lista Completa",
            subtitle="CNAEs mapeados",
            desc="Lista consolidada de CNAEs, segmento e decreto principal.",
            divider=False,
        )
        if lista.empty:
            render_empty_state("Nenhum CNAE encontrado para o recorte.", icon="🏷️")
        else:
            st.dataframe(lista, use_container_width=True, hide_index=True)
            d1, d2 = st.columns(2)
            with d1:
                st.download_button("Baixar CSV", data=prepare_download_bytes(lista, fmt="csv"), file_name="cnaes_por_decreto.csv", mime="text/csv", use_container_width=True)
            with d2:
                st.download_button("Baixar XLSX", data=prepare_download_bytes(lista, fmt="xlsx"), file_name="cnaes_por_decreto.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    with tabs[2]:
        render_section_header(
            "Texto Tributário por Decreto",
            subtitle="Detalhamento",
            desc="Trechos textuais que acompanham os CNAEs em cada planilha de decreto.",
            divider=False,
        )
        if detalhes.empty:
            render_empty_state("Detalhamento não encontrado.", icon="📄")
        else:
            st.dataframe(detalhes, use_container_width=True, hide_index=True)

except Exception as exc:
    st.error(f"Não foi possível carregar a lista de CNAEs por decreto. Detalhe técnico: {exc}")
    st.exception(exc)
