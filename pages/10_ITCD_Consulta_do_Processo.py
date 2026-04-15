from __future__ import annotations

import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import base64 as _b64mod
import html as _html
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from coate_styles import aplicar_estilos
from coate_auth import exigir_acesso

aplicar_estilos()
exigir_acesso("itcd")

# ── Ícone ────────────────────────────────────────────────────
_icon_path = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'assets', 'itcd_icon.png'))
_itcd_img = ""
if _os.path.exists(_icon_path):
    with open(_icon_path, "rb") as _f:
        _itcd_img = (f'<img src="data:image/png;base64,{_b64mod.b64encode(_f.read()).decode()}" '
                     f'style="height:52px;border-radius:10px;margin-bottom:0.5rem;display:block;" alt="ITCD">')

# ── Imports do módulo ────────────────────────────────────────
try:
    from itcd.itcd_config import (
        COLOR_ATRASADO, COLOR_EM_DIA, COLOR_ALERTA, COLOR_PRIMARY, COLOR_PURPLE,
        FASES_FISCAL, FASES_NOMES, LOADING_MESSAGES, PRAZO_META_DIAS,
        PLOTLY_PAPER_BGCOLOR, PLOTLY_PLOT_BGCOLOR, PLOTLY_TEMPLATE, PLOTLY_FONT_COLOR,
        STATUS_PROCESSO_COLOR_MAP,
    )
    from itcd.itcd_core import (
        calcular_processos_enriquecidos, get_processo_detalhe, get_spec,
    )
except ImportError:
    from itcd_config import (
        COLOR_ATRASADO, COLOR_EM_DIA, COLOR_ALERTA, COLOR_PRIMARY, COLOR_PURPLE,
        FASES_FISCAL, FASES_NOMES, LOADING_MESSAGES, PRAZO_META_DIAS,
        PLOTLY_PAPER_BGCOLOR, PLOTLY_PLOT_BGCOLOR, PLOTLY_TEMPLATE, PLOTLY_FONT_COLOR,
        STATUS_PROCESSO_COLOR_MAP,
    )
    from itcd_core import (
        calcular_processos_enriquecidos, get_processo_detalhe, get_spec,
    )

def _fmt_int(v) -> str:
    try: return f"{int(v):,}".replace(",", ".")
    except: return "—"

def _safe(v, default="—") -> str:
    try:
        if pd.isna(v):
            return default
    except Exception:
        pass
    if v is None:
        return default
    return str(v)

def _to_int(v, default=0) -> int:
    try:
        if pd.isna(v):
            return default
        return int(float(v))
    except Exception:
        return default

def _fmt_date(v) -> str:
    try:
        ts = pd.to_datetime(v)
        return ts.strftime("%d/%m/%Y %H:%M") if pd.notna(ts) else "—"
    except: return "—"

FASE_COLORS = {
    "DISTRIBUIDO":    "#3b82f6",
    "REDISTRIBUIDO":  "#6366f1",
    "REDIRECIONADO":  "#8b5cf6",
    "REABERTO":       "#f59e0b",
    "REENVIADO":      "#f97316",
    "EM INSTRUÇÃO":   "#06b6d4",
    "CONCLUIDO":      "#22c55e",
    "CANCELADO":      "#ef4444",
    "ABERTO":         "#64748b",
    "ENVIADO":        "#94a3b8",
    "TRANSMITIDO":    "#cbd5e1",
}

# =============================================================
# HERO
# =============================================================
st.markdown(
    f"""
    <div class="hero">
        {_itcd_img}
        <div class="hero-kicker">⚖️ ITCD · Consulta</div>
        <h1>Consulta do Processo</h1>
        <p>Detalhamento completo de um processo ITCD — fases, pendências, guias e
        leitura do prazo com apoio do tempo líquido do fiscal.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Como interpretar os indicadores deste processo"):
    st.markdown(
        """
        - **Status Gerencial**: leitura principal do caso na ótica operacional.
        - **Prazo**: situação de prazo do processo.
        - **Dias Líquidos do Fiscal**: dias brutos menos dias bloqueados por pendências.
        """
    )

spec = get_spec()
if not spec.existe:
    st.error(f"Arquivo de dados não encontrado: `{spec.path}`")
    st.stop()

# =============================================================
# BUSCA DO PROCESSO
# =============================================================
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">🔍 Localizar</div>
        <div class="coate-section-title">Selecionar Processo</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

# Verificar se veio da página de exploração via session_state
seq_presel = st.session_state.get("itcd_seq_consultado", None)

col_busca, col_btn = st.columns([4, 1])
with col_busca:
    busca = st.text_input(
        "Sequencial ou Nº do Processo",
        value=str(seq_presel) if seq_presel else "",
        placeholder="Ex.: 25521  ou  202602001550",
        label_visibility="collapsed",
    )
with col_btn:
    buscar = st.button("🔎 Buscar", use_container_width=True, type="primary")

if not busca.strip():
    st.info("Digite o número sequencial ou o número do processo e clique em **Buscar**. "
            "Ou acesse pela página **Exploração de Processos** e clique em **Abrir Consulta**.")
    st.stop()

# Localizar o processo
df_todos = calcular_processos_enriquecidos()
termo = busca.strip()
mask = (
    df_todos["SEQ_PROCESSO_ITCD"].astype(str).str.contains(termo, na=False) |
    df_todos["NUM_PROCESSO_ITCD"].astype(str).str.contains(termo, na=False)
)
matches = df_todos[mask]

if matches.empty:
    st.error(f"Nenhum processo encontrado para `{termo}`.")
    st.stop()

if len(matches) > 1:
    opcoes = [
        f"{row['SEQ_PROCESSO_ITCD']} — {row['NUM_PROCESSO_ITCD']} | {row['DSC_TIP_TRANSMISSAO']} | {row['DSC_SIGLA_ORGAO_LOCAL']}"
        for _, row in matches.iterrows()
    ]
    selecao = st.selectbox(f"{len(matches)} processos encontrados — selecione:", opcoes)
    seq = int(selecao.split(" — ")[0])
else:
    seq = int(matches.iloc[0]["SEQ_PROCESSO_ITCD"])

proc_row = df_todos[df_todos["SEQ_PROCESSO_ITCD"] == seq].iloc[0]

with st.spinner(LOADING_MESSAGES["detalhe"]):
    detalhe = get_processo_detalhe(seq)

fases_proc = detalhe["fases"]
pend_proc  = detalhe["pendencias"]
guias_proc = detalhe["guias"]

# =============================================================
# CABEÇALHO DO PROCESSO
# =============================================================
status_gerencial = _safe(proc_row.get("status_gerencial"))
if status_gerencial == "Concluído no Prazo":
    cor_status_gerencial = COLOR_EM_DIA
elif status_gerencial in {"Concluído em Atraso", "Crítico"}:
    cor_status_gerencial = COLOR_ATRASADO
elif status_gerencial in {"Em Risco", "Sem Distribuição"}:
    cor_status_gerencial = COLOR_ALERTA
elif status_gerencial == "Com Pendência":
    cor_status_gerencial = COLOR_PURPLE
else:
    cor_status_gerencial = COLOR_PRIMARY
prazo_status = _safe(proc_row.get("Prazo"))
cor_prazo   = COLOR_EM_DIA if prazo_status == "EM DIA" else COLOR_ATRASADO
status_processo = _safe(proc_row.get("status_processo", "A TRABALHAR"))
cor_status_processo = STATUS_PROCESSO_COLOR_MAP.get(status_processo, COLOR_PRIMARY)

dias_liq   = _to_int(proc_row.get("dias_liquidos_fiscal", 0), 0)
dias_bruto = _to_int(proc_row.get("dias_brutos_fiscal", 0), 0)
dias_pend  = _to_int(proc_row.get("dias_pendencias", 0), 0)

st.markdown(
    f"""
    <div class="panel" style="margin-bottom:1rem;">
        <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap;margin-bottom:0.8rem;">
            <span style="font-size:1.3rem;font-weight:800;color:#f8fafc;">
                Processo {_safe(proc_row.get('NUM_PROCESSO_ITCD'))}
            </span>
            <span style="background:{cor_status_gerencial}22;color:{cor_status_gerencial};border:1px solid {cor_status_gerencial}44;
                         padding:0.25rem 0.75rem;border-radius:999px;font-size:0.8rem;font-weight:700;">
                Status Gerencial: {status_gerencial}
            </span>
            <span style="background:{cor_prazo}22;color:{cor_prazo};border:1px solid {cor_prazo}44;
                         padding:0.25rem 0.75rem;border-radius:999px;font-size:0.8rem;font-weight:700;">
                Prazo: {prazo_status}
            </span>
            <span style="background:{cor_status_processo}22;color:{cor_status_processo};border:1px solid {cor_status_processo}44;
                         padding:0.25rem 0.75rem;border-radius:999px;font-size:0.8rem;font-weight:700;">
                Status do Processo: {status_processo}
            </span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;">
            <div><div style="color:#64748b;font-size:0.75rem;font-weight:700;text-transform:uppercase;">Tipo</div>
                 <div style="color:#f1f5f9;font-size:0.95rem;">{_safe(proc_row.get('DSC_TIP_TRANSMISSAO'))}</div></div>
            <div><div style="color:#64748b;font-size:0.75rem;font-weight:700;text-transform:uppercase;">Órgão</div>
                 <div style="color:#f1f5f9;font-size:0.95rem;">{_safe(proc_row.get('DSC_SIGLA_ORGAO_LOCAL'))}</div></div>
            <div><div style="color:#64748b;font-size:0.75rem;font-weight:700;text-transform:uppercase;">Fase Atual</div>
                 <div style="color:#f1f5f9;font-size:0.95rem;">{_safe(proc_row.get('DSC_TIP_FASE_GUIA'))}</div></div>
            <div><div style="color:#64748b;font-size:0.75rem;font-weight:700;text-transform:uppercase;">Origem</div>
                 <div style="color:#f1f5f9;font-size:0.95rem;">{_safe(proc_row.get('DSC_ORIGEM_PROCESSO'))}</div></div>
            <div><div style="color:#64748b;font-size:0.75rem;font-weight:700;text-transform:uppercase;">Criação</div>
                 <div style="color:#f1f5f9;font-size:0.95rem;">{_fmt_date(proc_row.get('DAT_CRIACAO'))}</div></div>
            <div><div style="color:#64748b;font-size:0.75rem;font-weight:700;text-transform:uppercase;">Distribuição</div>
                 <div style="color:#f1f5f9;font-size:0.95rem;">{_fmt_date(proc_row.get('DAT_DISTRIBUICAO'))}</div></div>
            <div><div style="color:#64748b;font-size:0.75rem;font-weight:700;text-transform:uppercase;">Dist. Automática</div>
                 <div style="color:#f1f5f9;font-size:0.95rem;">{_safe(proc_row.get('DSC_DIST_AUTOMATICA'))}</div></div>
            <div><div style="color:#64748b;font-size:0.75rem;font-weight:700;text-transform:uppercase;">Guias</div>
                 <div style="color:#f1f5f9;font-size:0.95rem;">{_safe(proc_row.get('Guias'))}</div></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =============================================================
# KPIs DE TEMPO
# =============================================================
k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f"""<div class="coate-kpi-card accent-primary">
        <div class="coate-kpi-top"><div class="coate-kpi-label">Dias Brutos (Fiscal)</div><div class="coate-kpi-icon">📅</div></div>
        <div class="coate-kpi-value">{dias_bruto}</div>
        <div class="coate-kpi-delta delta-primary">Fases: DIST · REDIST · EM INST</div>
        <div class="coate-kpi-help">Soma de todos os dias nas fases de trabalho do fiscal.</div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class="coate-kpi-card accent-warning">
        <div class="coate-kpi-top"><div class="coate-kpi-label">Dias Bloqueados</div><div class="coate-kpi-icon">⏸️</div></div>
        <div class="coate-kpi-value">{dias_pend}</div>
        <div class="coate-kpi-delta delta-warning">Aguardando contribuinte</div>
        <div class="coate-kpi-help">Período em que o processo ficou parado por pendências do contribuinte.</div>
    </div>""", unsafe_allow_html=True)
with k3:
    cor_liq = "success" if dias_liq <= PRAZO_META_DIAS else "danger"
    st.markdown(f"""<div class="coate-kpi-card accent-{'success' if dias_liq <= PRAZO_META_DIAS else 'danger'}">
        <div class="coate-kpi-top"><div class="coate-kpi-label">Dias Líquidos do Fiscal</div><div class="coate-kpi-icon">⚖️</div></div>
        <div class="coate-kpi-value">{dias_liq}</div>
        <div class="coate-kpi-delta delta-{cor_liq}">Meta: ≤ {PRAZO_META_DIAS} dias</div>
        <div class="coate-kpi-help">Brutos − Bloqueados. Tempo efetivo de trabalho do fiscal.</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =============================================================
# TIMELINE DE FASES
# =============================================================
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📅 Histórico</div>
        <div class="coate-section-title">Linha do Tempo das Fases</div>
        <div class="coate-section-desc">Todas as fases que o processo percorreu, com duração e marcação das fases do fiscal.</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

if not fases_proc.empty:
    # Gráfico de Gantt das fases
    fases_plot = fases_proc.copy()
    fases_plot["DAT_FASE"] = pd.to_datetime(fases_plot["DAT_FASE"], errors="coerce")
    fases_plot["DAT_FASE_PROX"] = pd.to_datetime(fases_plot["DAT_FASE_PROX"], errors="coerce")
    fases_plot["fim"] = fases_plot["DAT_FASE_PROX"].fillna(pd.Timestamp.now())
    fases_plot["eh_fiscal"] = fases_plot["TIP_FASE"].isin(FASES_FISCAL)
    fases_plot["cor"] = fases_plot["DSC_TIP_FASE_GUIA"].map(
        lambda x: FASE_COLORS.get(str(x).upper(), "#475569")
    )
    fases_plot["label"] = fases_plot.apply(
        lambda r: f"{r['DSC_TIP_FASE_GUIA']} ({r['DIAS']}d)"
                  + (" ⭐" if r["eh_fiscal"] else ""), axis=1
    )

    if fases_plot["DAT_FASE"].notna().any():
        fig_gantt = go.Figure()
        for _, row in fases_plot.iterrows():
            if pd.isna(row["DAT_FASE"]):
                continue
            cor = row["cor"]
            if row["eh_fiscal"]:
                cor = "#3b82f6"
            fig_gantt.add_trace(go.Bar(
                name=row["DSC_TIP_FASE_GUIA"],
                x=[row["DIAS"]],
                y=[f"Fase {int(row['TIP_FASE'])} — {row['DSC_TIP_FASE_GUIA']}"],
                orientation="h",
                marker_color=cor,
                marker_line_width=0,
                hovertemplate=(
                    f"<b>{row['DSC_TIP_FASE_GUIA']}</b><br>"
                    f"Início: {_fmt_date(row['DAT_FASE'])}<br>"
                    f"Fim: {_fmt_date(row['DAT_FASE_PROX'])}<br>"
                    f"Duração: {row['DIAS']} dias<br>"
                    f"Após instrução: {'Sim' if row.get('FLG_APOS_INSTRUCAO') else 'Não'}<br>"
                    f"Fiscal: {'⭐ Sim' if row['eh_fiscal'] else 'Não'}"
                    "<extra></extra>"
                ),
            ))

        fig_gantt.update_layout(
            template=PLOTLY_TEMPLATE,
            paper_bgcolor=PLOTLY_PAPER_BGCOLOR,
            plot_bgcolor=PLOTLY_PLOT_BGCOLOR,
            font=dict(color=PLOTLY_FONT_COLOR, family="'Segoe UI', sans-serif"),
            barmode="stack",
            showlegend=False,
            height=max(220, len(fases_plot) * 36),
            margin=dict(t=20, b=20, l=20, r=20),
            xaxis=dict(title="Dias", gridcolor="rgba(148,163,184,0.10)"),
            yaxis=dict(showgrid=False),
            title="⭐ = fases do fiscal | Azul = conta para o OKR",
        )
        st.plotly_chart(fig_gantt, use_container_width=True)

    # Tabela detalhada de fases
    fases_exib = fases_proc[[c for c in [
        "TIP_FASE", "DSC_TIP_FASE_GUIA", "DAT_FASE", "HORA_FASE",
        "DAT_FASE_PROX", "DIAS", "FLG_APOS_INSTRUCAO",
        "DIAS_ACUMULADOS", "DIAS_ACUMULADOS_EM_INSTRUCAO",
        "DSC_TIP_USUARIO", "DSC_OBSERVACAO",
    ] if c in fases_proc.columns]].copy()

    fases_exib = fases_exib.rename(columns={
        "TIP_FASE": "Cod. Fase", "DSC_TIP_FASE_GUIA": "Fase",
        "DAT_FASE": "Data Início", "HORA_FASE": "Hora",
        "DAT_FASE_PROX": "Próxima Fase", "DIAS": "Dias",
        "FLG_APOS_INSTRUCAO": "Após Instrução",
        "DIAS_ACUMULADOS": "Dias Acum.", "DIAS_ACUMULADOS_EM_INSTRUCAO": "Dias Inst. Acum.",
        "DSC_TIP_USUARIO": "Tipo Usuário", "DSC_OBSERVACAO": "Observação",
    })

    # Destacar fases do fiscal
    fases_exib["★ Fiscal"] = fases_proc["TIP_FASE"].isin(FASES_FISCAL).map({True: "✅ Sim", False: "—"})

    st.dataframe(
        fases_exib, use_container_width=True, hide_index=True,
        column_config={
            "Dias": st.column_config.NumberColumn("Dias", format="%d"),
            "Dias Acum.": st.column_config.NumberColumn("Dias Acum.", format="%d"),
            "Dias Inst. Acum.": st.column_config.NumberColumn("Dias Inst. Acum.", format="%d"),
        },
        height=320,
    )
else:
    st.info("Nenhuma fase registrada para este processo.")

# =============================================================
# PENDÊNCIAS
# =============================================================
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">⏸️ Pendências</div>
        <div class="coate-section-title">Pendências do Contribuinte</div>
        <div class="coate-section-desc">
            Períodos em que o processo ficou aguardando ação do contribuinte —
            esses dias são descontados do tempo líquido do fiscal.
        </div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

if not pend_proc.empty and len(pend_proc) > 0:
    # KPIs de pendências
    n_pend       = len(pend_proc)
    n_canceladas = (pend_proc["DSC_STA_PENDENCIA"] == "CANCELADA").sum()
    n_resolvidas = (pend_proc["DSC_STA_PENDENCIA"] == "RESOLVIDA").sum()
    n_abertas    = n_pend - n_canceladas - n_resolvidas

    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.metric("Total de Pendências", n_pend)
    with p2:
        st.metric("Canceladas", n_canceladas, help="Motivo cancelado pela SEFAZ")
    with p3:
        st.metric("Resolvidas", n_resolvidas, help="Contribuinte respondeu")
    with p4:
        st.metric("Abertas / Não Resolvidas", n_abertas,
                  delta=f"−{dias_pend} dias bloqueados" if dias_pend else None,
                  delta_color="inverse")

    st.markdown("<br>", unsafe_allow_html=True)

    pend_exib = pend_proc[[c for c in [
        "SEQ_PENDENCIA", "DAT_INCLUSAO", "DAT_VISUALIZACAO",
        "DAT_RESPOSTA", "DAT_CANCELAMENTO",
        "DSC_STA_PENDENCIA", "DSC_MOTIVO", "DSC_TIP_TRANSMISSAO",
        "SEQ_GUIA_ITCD",
    ] if c in pend_proc.columns]].copy()

    pend_exib = pend_exib.rename(columns={
        "SEQ_PENDENCIA": "Seq. Pendência",
        "DAT_INCLUSAO": "Inclusão", "DAT_VISUALIZACAO": "Visualização",
        "DAT_RESPOSTA": "Resposta", "DAT_CANCELAMENTO": "Cancelamento",
        "DSC_STA_PENDENCIA": "Status", "DSC_MOTIVO": "Motivo",
        "DSC_TIP_TRANSMISSAO": "Tipo", "SEQ_GUIA_ITCD": "Seq. Guia",
    })

    # Limpar HTML tags do motivo
    if "Motivo" in pend_exib.columns:
        import re
        pend_exib["Motivo"] = pend_exib["Motivo"].astype(str).apply(
            lambda x: re.sub(r'<[^>]+>', '', x).strip()
        )

    st.dataframe(pend_exib, use_container_width=True, hide_index=True, height=280)
else:
    st.markdown(
        """<div class="coate-empty">
            <div class="coate-empty-icon">✅</div>
            <div class="coate-empty-title">Nenhuma pendência registrada</div>
            <div class="coate-empty-help">Este processo não possui pendências do contribuinte.</div>
        </div>""",
        unsafe_allow_html=True,
    )

# =============================================================
# GUIAS
# =============================================================
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📄 Guias</div>
        <div class="coate-section-title">Guias Vinculadas ao Processo</div>
        <div class="coate-section-desc">Todas as guias geradas para este processo e seus respectivos status.</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

if not guias_proc.empty:
    g_n       = len(guias_proc)
    g_fases   = guias_proc["DSC_TIP_FASE_GUIA"].value_counts().to_dict() if "DSC_TIP_FASE_GUIA" in guias_proc.columns else {}

    st.caption(f"{g_n} guia(s) — " + " · ".join(f"{k}: {v}" for k, v in g_fases.items()))

    guias_exib = guias_proc[[c for c in [
        "SEQ_GUIA_ITCD", "DAT_CRIACAO", "TIP_TRANSMISSAO",
        "DSC_TIP_TRANSMISSAO", "TIP_FASE_GUIA",
        "DSC_TIP_FASE_GUIA", "DSC_OBSERVACAO",
    ] if c in guias_proc.columns]].copy()

    guias_exib = guias_exib.rename(columns={
        "SEQ_GUIA_ITCD": "Seq. Guia",
        "DAT_CRIACAO": "Data de Criação",
        "TIP_TRANSMISSAO": "Cód. Tipo",
        "DSC_TIP_TRANSMISSAO": "Tipo de Transmissão",
        "TIP_FASE_GUIA": "Cód. Fase",
        "DSC_TIP_FASE_GUIA": "Fase da Guia",
        "DSC_OBSERVACAO": "Observação",
    })

    st.dataframe(guias_exib, use_container_width=True, hide_index=True, height=280)
else:
    st.markdown(
        """<div class="coate-empty">
            <div class="coate-empty-icon">📭</div>
            <div class="coate-empty-title">Nenhuma guia vinculada</div>
            <div class="coate-empty-help">Não foram encontradas guias para este processo.</div>
        </div>""",
        unsafe_allow_html=True,
    )

# =============================================================
# ANÁLISE CONSOLIDADA
# =============================================================
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📋 Síntese</div>
        <div class="coate-section-title">Análise Consolidada do Processo</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

n_fases_fiscal = len(fases_proc[fases_proc["TIP_FASE"].isin(FASES_FISCAL)]) if not fases_proc.empty else 0
n_fases_total  = len(fases_proc)

cor_liq_res = COLOR_EM_DIA if dias_liq <= PRAZO_META_DIAS else COLOR_ATRASADO
veredicto = "dentro da meta" if dias_liq <= PRAZO_META_DIAS else f"acima da meta de {PRAZO_META_DIAS} dias"

st.markdown(
    f"""
    <div class="exec-summary">
        <p>
            O processo <strong>{_safe(proc_row.get('NUM_PROCESSO_ITCD'))}</strong>
            ({_safe(proc_row.get('DSC_TIP_TRANSMISSAO'))}) está em
            <strong>{_safe(proc_row.get('DSC_TIP_FASE_GUIA'))}</strong>
            no órgão <strong>{_safe(proc_row.get('DSC_SIGLA_ORGAO_LOCAL'))}</strong>.
            Passou por <strong>{n_fases_total} fases</strong>, das quais
            <strong>{n_fases_fiscal} são fases do fiscal</strong>.
            O tempo bruto de trabalho foi <strong>{dias_bruto} dias</strong>,
            com <strong>{dias_pend} dias bloqueados</strong> por pendências do contribuinte,
            resultando em <strong style="color:{cor_liq_res};">{dias_liq} dias líquidos</strong> —
            <strong>{veredicto}</strong> (≤ {PRAZO_META_DIAS}d).
            Possui <strong>{len(guias_proc)} guia(s)</strong> e
            <strong>{len(pend_proc)} pendência(s)</strong> registradas.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="coate-footer">ITCD · Consulta do Processo · Painel COATE · SEFAZ-CE</div>',
    unsafe_allow_html=True,
)
