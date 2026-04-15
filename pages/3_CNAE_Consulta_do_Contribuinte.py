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

import html as _html

import pandas as pd
import streamlit as st

from projetos_especiais.cnae.cnae_config import LOADING_MESSAGES, PRIORITY_META
from projetos_especiais.cnae.cnae_core import (
    ensure_data_available,
    get_company_detail,
    get_company_history,
    get_company_search_results,
    infer_case_summary,
)
from coate_styles import aplicar_estilos
from coate_auth import exigir_acesso
from projetos_especiais.cnae.cnae_utils import (
    format_pct,
    make_line_chart,
    prepare_download_bytes,
    render_empty_state,
    render_kpi_card,
    render_priority_badge,
    render_section_header,
    text_or_na,
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
        <div class="hero-kicker">🔎 Contribuinte</div>
        <h1>Consulta do Contribuinte</h1>
        <p>
            Busca individual por CNPJ, razão social ou fantasia —
            com leitura cadastral, histórico de snapshots e resumo analítico do caso.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    ensure_data_available()

    # ──────────────────────────────────────────────────────────
    # SEARCH BAR
    # ──────────────────────────────────────────────────────────
    busca = st.text_input(
        "🔍 Digite CNPJ, razão social ou fantasia",
        placeholder="Ex.: 07526557000100 ou Razão Social LTDA",
    )

    if not busca.strip():
        render_empty_state(
            "Informe um termo de busca para localizar a empresa.",
            "A pesquisa aceita CNPJ (parcial ou completo), razão social e nome fantasia.",
            icon="🔎",
        )
        st.stop()

    with st.spinner(LOADING_MESSAGES["consulta"]):
        matches = get_company_search_results(busca.strip(), 30)

    if matches.empty:
        render_empty_state(
            "Nenhum contribuinte encontrado para o termo informado.",
            "Tente um CNPJ parcial ou parte da razão social.",
            icon="🏢",
        )
        st.stop()

    # ──────────────────────────────────────────────────────────
    # COMPANY SELECTOR
    # ──────────────────────────────────────────────────────────
    label_map = {
        f"{row['nom_razao_social']}  |  {row['cnpj_str']}  |  {row['prioridade_revisao']}": row["cnpj_str"]
        for _, row in matches.iterrows()
    }
    selected_label = st.selectbox(
        f"Selecione a empresa ({len(matches)} resultado(s))",
        list(label_map.keys()),
    )
    cnpj = label_map[selected_label]

    company = get_company_detail(cnpj)
    history = get_company_history(cnpj)

    if company.empty:
        render_empty_state("Dados detalhados não encontrados para o CNPJ selecionado.", icon="❓")
        st.stop()

    row = company.iloc[0]
    prioridade = str(row.get("prioridade_revisao", "N/D"))
    meta = PRIORITY_META.get(prioridade, {"color": "#3b82f6", "bg": "rgba(59,130,246,0.14)", "icon": "🔵"})

    # ──────────────────────────────────────────────────────────
    # CASE HEADER — badge + razão social
    # ──────────────────────────────────────────────────────────
    razao = _html.escape(text_or_na(row.get("nom_razao_social")))
    fantasia = _html.escape(text_or_na(row.get("nom_fantasia"), ""))
    cnpj_fmt = _html.escape(text_or_na(row.get("cnpj_str")))
    sub_line = f" · {fantasia}" if fantasia and fantasia != "Não informado" else ""

    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.9rem; margin:0.6rem 0 1rem 0; flex-wrap:wrap;">
            <span class="priority-badge"
                  style="background:{meta['bg']};color:{meta['color']};border-color:{meta['color']};">
                {meta['icon']} Prioridade {_html.escape(prioridade)}
            </span>
            <div>
                <div style="color:#f1f5f9;font-size:1.1rem;font-weight:800;letter-spacing:-0.01em;">
                    {razao}
                </div>
                <div style="color:var(--text-muted);font-size:0.83rem;margin-top:0.1rem;">
                    CNPJ {cnpj_fmt}{sub_line}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ──────────────────────────────────────────────────────────
    # KPIs
    # ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card(
            "Prioridade",
            prioridade,
            icon="🚨",
            delta="Classificação do caso",
            delta_type="danger" if prioridade == "Alta" else ("warning" if prioridade == "Média" else "success"),
        )
    with c2:
        render_kpi_card(
            "Consistência",
            format_pct(row.get("taxa_consistencia_empresa", 0), 1),
            icon="📐",
            delta="Estabilidade temporal",
            delta_type="success",
            help_text="Quanto maior, mais estável a predição ao longo dos meses.",
        )
    with c3:
        render_kpi_card(
            "Divergência Subclasse",
            format_pct(row.get("taxa_divergencia_subclasse", 0), 1),
            icon="⚠️",
            delta="Recorte histórico",
            delta_type="danger",
            help_text="Proporção de snapshots onde CNAE real ≠ predito.",
        )
    with c4:
        render_kpi_card(
            "Predições distintas",
            str(int(row.get("qtd_predicoes_distintas_empresa", 0) or 0)),
            icon="🔁",
            delta="Variação observada",
            delta_type="warning" if int(row.get("qtd_predicoes_distintas_empresa", 0) or 0) > 1 else "success",
            help_text="Número de classes distintas previstas para essa empresa.",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────
    # CASE SUMMARY
    # ──────────────────────────────────────────────────────────
    render_section_header("Resumo Analítico do Caso", subtitle="Síntese", divider=True)
    summary = infer_case_summary(row)
    st.markdown(
        f'<div class="exec-summary"><p>{_html.escape(summary)}</p></div>',
        unsafe_allow_html=True,
    )

    # ──────────────────────────────────────────────────────────
    # CNAE COMPARISON TABLE
    # ──────────────────────────────────────────────────────────
    render_section_header(
        "CNAE Real × Predito por Nível",
        subtitle="Comparativo",
        desc="Último snapshot disponível para cada nível hierárquico.",
        divider=True,
    )

    def _safe(val: object) -> str:
        return text_or_na(val, "—")

    compare_rows = [
        ("Seção",     row.get("cnae_secao_real_ultimo"),     row.get("cnae_secao_pred_ultimo")),
        ("Divisão",   row.get("cnae_divisao_real_ultimo"),   row.get("cnae_divisao_pred_ultimo")),
        ("Grupo",     row.get("cnae_grupo_real_ultimo"),     row.get("cnae_grupo_pred_ultimo")),
        ("Classe",    row.get("cnae_classe_real_ultimo"),    row.get("cnae_classe_pred_ultimo")),
        ("Subclasse", row.get("cnae_subclasse_real_ultimo"), row.get("cnae_subclasse_pred_ultimo")),
    ]

    comp_data = []
    for nivel, real, pred in compare_rows:
        r = _safe(real)
        p = _safe(pred)
        match = r == p and r != "—"
        comp_data.append({"Nível": nivel, "CNAE Real": r, "CNAE Predito": p, "Status": "✅ Acerto" if match else "❌ Diverge"})

    comp_df = pd.DataFrame(comp_data)
    st.dataframe(
        comp_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Status": st.column_config.TextColumn("Status", width="small"),
            "CNAE Real": st.column_config.TextColumn("CNAE Real"),
            "CNAE Predito": st.column_config.TextColumn("CNAE Predito"),
        },
    )

    # ──────────────────────────────────────────────────────────
    # CADASTRAL DATA
    # ──────────────────────────────────────────────────────────
    render_section_header("Dados Cadastrais", subtitle="Identificação", divider=True)

    ident = {
        "Razão Social":        text_or_na(row.get("nom_razao_social")),
        "Nome fantasia":       text_or_na(row.get("nom_fantasia")),
        "CNPJ":                text_or_na(row.get("cnpj_str")),
        "CGF":                 text_or_na(row.get("cod_cgf")),
        "Início de atividade": text_or_na(row.get("dat_inicio_atividade")),
        "Primeiro snapshot":   text_or_na(row.get("primeiro_snapshot")),
        "Último snapshot":     text_or_na(row.get("ultimo_snapshot")),
        "Par reclassificação": text_or_na(row.get("par_reclassificacao")),
        "Registros":           str(int(row.get("qtd_registros_empresa", 0) or 0)),
        "Meses com snapshot":  str(int(row.get("qtd_meses_snapshot", 0) or 0)),
    }
    ident_df = pd.DataFrame({"Campo": list(ident.keys()), "Valor": list(ident.values())})
    st.dataframe(ident_df, hide_index=True, use_container_width=True)

    # ──────────────────────────────────────────────────────────
    # TIMELINE CHART
    # ──────────────────────────────────────────────────────────
    if not history.empty and "mes_snapshot" in history.columns and "flag_divergencia_subclasse" in history.columns:
        render_section_header(
            "Evolução da Divergência por Snapshot",
            subtitle="Histórico",
            desc="Sinaliza meses onde a predição diverge do CNAE real em subclasse.",
            divider=True,
        )

        history_plot = history.sort_values("mes_snapshot").copy()
        fig_timeline = make_line_chart(
            history_plot,
            x="mes_snapshot",
            y="flag_divergencia_subclasse",
            title="Timeline de divergência — Subclasse",
            yaxis_tickformat=".0f",
        )
        fig_timeline.update_layout(
            xaxis_title="Mês snapshot",
            yaxis_title="Divergência (0 = acerto, 1 = diverge)",
            yaxis=dict(tickvals=[0, 1], ticktext=["✅ Acerto", "❌ Diverge"], range=[-0.15, 1.2]),
        )
        # Annotate changes in prediction
        if "cnae_subclasse_pred_str" in history_plot.columns:
            history_plot["pred_changed"] = (
                history_plot["cnae_subclasse_pred_str"]
                .astype(str)
                .ne(history_plot["cnae_subclasse_pred_str"].astype(str).shift())
            )
            changes = history_plot[history_plot["pred_changed"] & (history_plot.index > history_plot.index[0])]
            for _, chg in changes.iterrows():
                fig_timeline.add_vline(
                    x=chg["mes_snapshot"],
                    line_dash="dot",
                    line_color="rgba(245,158,11,0.5)",
                    annotation_text="mudança",
                    annotation_font_size=10,
                    annotation_font_color="#fcd34d",
                )
        st.plotly_chart(fig_timeline, use_container_width=True)

    # ──────────────────────────────────────────────────────────
    # HISTORY TABLE
    # ──────────────────────────────────────────────────────────
    render_section_header(
        "Histórico Completo dos Snapshots",
        subtitle="Tabela",
        desc=f"{len(history)} registros mensais para o CNPJ selecionado.",
        divider=True,
    )
    st.dataframe(history, use_container_width=True, hide_index=True)

    # ──────────────────────────────────────────────────────────
    # EXPORT
    # ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        f"⬇️ Exportar caso — {cnpj} (XLSX)",
        data=prepare_download_bytes(history, "xlsx"),
        file_name=f"caso_{cnpj}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

except Exception as exc:
    st.error(f"Não foi possível carregar a Consulta do Contribuinte. Detalhe técnico: {exc}")
    st.exception(exc)
