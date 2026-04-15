from __future__ import annotations

import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import base64 as _b64mod
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from coate_styles import aplicar_estilos
from coate_auth import exigir_acesso

aplicar_estilos()
exigir_acesso("itcd")

_itcd_icon_path = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'assets', 'itcd_icon.png'))
_itcd_img = ""
if _os.path.exists(_itcd_icon_path):
    with open(_itcd_icon_path, "rb") as _f:
        _itcd_img = (
            f'<img src="data:image/png;base64,{_b64mod.b64encode(_f.read()).decode()}" '
            f'style="height:52px;border-radius:10px;margin-bottom:0.5rem;display:block;" alt="ITCD">'
        )

try:
    from itcd.itcd_config import (
        APP_SUBTITLE, COLOR_ATRASADO, COLOR_EM_DIA, COLOR_PRIMARY,
        COLOR_PURPLE, COLOR_ALERTA, LOADING_MESSAGES,
        PLOTLY_FONT_COLOR, PLOTLY_FONT_FAMILY,
        PLOTLY_PAPER_BGCOLOR, PLOTLY_PLOT_BGCOLOR, PLOTLY_TEMPLATE,
        PRAZO_META_DIAS, STATUS_PROCESSO_COLOR_MAP, STATUS_PROCESSO_LABELS,
    )
    from itcd.itcd_core import calcular_processos_enriquecidos, get_pendencias_enriquecidas, get_spec
except ImportError:
    from itcd_config import (
        APP_SUBTITLE, COLOR_ATRASADO, COLOR_EM_DIA, COLOR_PRIMARY,
        COLOR_PURPLE, COLOR_ALERTA, LOADING_MESSAGES,
        PLOTLY_FONT_COLOR, PLOTLY_FONT_FAMILY,
        PLOTLY_PAPER_BGCOLOR, PLOTLY_PLOT_BGCOLOR, PLOTLY_TEMPLATE,
        PRAZO_META_DIAS, STATUS_PROCESSO_COLOR_MAP, STATUS_PROCESSO_LABELS,
    )
    from itcd_core import calcular_processos_enriquecidos, get_pendencias_enriquecidas, get_spec


STATUS_GERENCIAL_CORES = {
    "Concluído no Prazo": COLOR_EM_DIA,
    "Concluído em Atraso": COLOR_ATRASADO,
    "Crítico": COLOR_ATRASADO,
    "Em Risco": COLOR_ALERTA,
    "Com Pendência": COLOR_PURPLE,
    "Sem Distribuição": "#64748b",
    "Ativo Regular": COLOR_PRIMARY,
}
STATUS_OKR_CORES = {
    "Dentro do Prazo": COLOR_EM_DIA,
    "Fora do Prazo": COLOR_ATRASADO,
    "Em Risco": COLOR_ALERTA,
    "Em Andamento": COLOR_PRIMARY,
}
STATUS_ORDENADOS = [
    "Concluído no Prazo",
    "Concluído em Atraso",
    "Crítico",
    "Em Risco",
    "Com Pendência",
    "Sem Distribuição",
    "Ativo Regular",
]
FAIXA_IDADE_ORDEM = ["0–15", "16–30", "31–60", "61–90", ">90", "Sem data"]
PAGE_SIZE = 10

_LAYOUT_BASE = dict(
    template=PLOTLY_TEMPLATE,
    paper_bgcolor=PLOTLY_PAPER_BGCOLOR,
    plot_bgcolor=PLOTLY_PLOT_BGCOLOR,
    font=dict(color=PLOTLY_FONT_COLOR, family=PLOTLY_FONT_FAMILY),
    margin=dict(t=48, b=16, l=16, r=16),
)


def _fmt_int(v) -> str:
    try:
        return f"{int(v):,}".replace(",", ".")
    except Exception:
        return "—"


def _fmt_pct(v, digits: int = 1) -> str:
    try:
        return f"{float(v) * 100:.{digits}f}%"
    except Exception:
        return "—"


def _fmt_dias(v, digits: int = 1) -> str:
    try:
        if pd.isna(v):
            return "—"
        return f"{float(v):.{digits}f} dias"
    except Exception:
        return "—"


def _num(v, default: float = 0.0) -> float:
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def _int(v, default: int = 0) -> int:
    try:
        if pd.isna(v):
            return default
        return int(float(v))
    except Exception:
        return default


def _to_int(v, default=0):
    try:
        if pd.isna(v):
            return default
        return int(float(v))
    except Exception:
        return default


def _fmt_date_short(v) -> str:
    try:
        ts = pd.to_datetime(v)
        return ts.strftime("%d/%m/%Y") if pd.notna(ts) else "—"
    except Exception:
        return "—"


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


def _badge_status_prazo(valor: str) -> str:
    texto = str(valor or "—").strip().upper()
    if texto == "EM DIA":
        cls = "itcd-badge-em-dia"
    elif texto == "ATRASADO":
        cls = "itcd-badge-atrasado"
    else:
        cls = "itcd-badge-neutro"
    return f'<span class="itcd-badge {cls}">{texto.title() if texto not in ["—", ""] else "—"}</span>'


def _badge_status_okr(valor: str) -> str:
    texto = str(valor or "—").strip()
    chave = texto.lower()
    if chave == "dentro do prazo":
        cls = "itcd-badge-ok"
    elif chave == "fora do prazo":
        cls = "itcd-badge-atrasado"
    elif chave == "em risco":
        cls = "itcd-badge-risco"
    elif chave == "em andamento":
        cls = "itcd-badge-andamento"
    else:
        cls = "itcd-badge-neutro"
    return f'<span class="itcd-badge {cls}">{texto or "—"}</span>'


def _badge_status_gerencial(valor: str) -> str:
    texto = str(valor or "—").strip()
    chave = texto.lower()
    if chave == "concluído no prazo":
        cls = "itcd-badge-ok"
    elif chave in {"concluído em atraso", "crítico"}:
        cls = "itcd-badge-atrasado"
    elif chave in {"em risco", "sem distribuição"}:
        cls = "itcd-badge-risco"
    elif chave == "com pendência":
        cls = "itcd-badge-andamento"
    else:
        cls = "itcd-badge-neutro"
    return f'<span class="itcd-badge {cls}">{texto or "—"}</span>'


def _badge_status_processo(valor: str) -> str:
    texto = str(valor or "—").strip()
    if texto == "CONCLUÍDO":
        cls = "itcd-badge-concluido"
    elif texto == "A TRABALHAR":
        cls = "itcd-badge-a-trabalhar"
    else:
        cls = "itcd-badge-neutro"
    return f'<span class="itcd-badge {cls}">{texto}</span>'


def _abrir_consulta_processo(seq_processo: int):
    st.session_state["itcd_seq_consultado"] = int(seq_processo)
    st.switch_page("pages/10_ITCD_Consulta_do_Processo.py")


def _aplicar_estilo_grade_itcd():
    st.markdown(
        """
        <style>
        .itcd-grid-wrap {
            border: 1px solid rgba(148,163,184,0.14);
            border-radius: 18px;
            overflow: hidden;
            background: linear-gradient(180deg, rgba(15,23,42,0.16), rgba(2,6,23,0.08));
        }
        .itcd-grid-head {
            color: #93a4c3;
            font-size: 0.76rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .05em;
            padding-bottom: 0.15rem;
        }
        .itcd-grid-line {
            border-top: 1px solid rgba(148,163,184,0.10);
            margin: 0.25rem 0 0.45rem 0;
        }
        .itcd-proc-main {
            color: #f8fafc;
            font-weight: 800;
            font-size: 1.02rem;
            line-height: 1.15;
            margin-bottom: 0.18rem;
        }
        .itcd-proc-sub {
            color: #94a3b8;
            font-size: 0.86rem;
            line-height: 1.2;
        }
        .itcd-cell-strong {
            color: #e2e8f0;
            font-weight: 700;
            font-size: 0.96rem;
            line-height: 1.25;
            word-break: break-word;
        }
        .itcd-cell-soft {
            color: #cbd5e1;
            font-weight: 600;
            font-size: 0.93rem;
            line-height: 1.25;
            word-break: break-word;
        }
        .itcd-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            white-space: nowrap;
            border-radius: 999px;
            padding: 0.38rem 0.82rem;
            font-size: 0.84rem;
            font-weight: 800;
            border: 1px solid transparent;
        }
        .itcd-badge-em-dia {
            background: rgba(16, 185, 129, 0.14);
            color: #d1fae5;
            border-color: rgba(16, 185, 129, 0.24);
        }
        .itcd-badge-atrasado {
            background: rgba(127, 29, 29, 0.50);
            color: #fecaca;
            border-color: rgba(248, 113, 113, 0.28);
        }
        .itcd-badge-risco {
            background: rgba(245, 158, 11, 0.18);
            color: #fde68a;
            border-color: rgba(245, 158, 11, 0.26);
        }
        .itcd-badge-andamento {
            background: rgba(59, 130, 246, 0.14);
            color: #dbeafe;
            border-color: rgba(59, 130, 246, 0.24);
        }
        .itcd-badge-ok {
            background: rgba(34, 197, 94, 0.14);
            color: #dcfce7;
            border-color: rgba(34, 197, 94, 0.24);
        }
        .itcd-badge-neutro {
            background: rgba(148, 163, 184, 0.12);
            color: #e2e8f0;
            border-color: rgba(148, 163, 184, 0.20);
        }
        .itcd-badge-concluido {
            background: rgba(34, 197, 94, 0.14);
            color: #dcfce7;
            border-color: rgba(34, 197, 94, 0.24);
        }
        .itcd-badge-a-trabalhar {
            background: rgba(59, 130, 246, 0.14);
            color: #dbeafe;
            border-color: rgba(59, 130, 246, 0.24);
        }
        .itcd-grid-wrap button[kind="secondary"] {
            min-height: 2.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _renderizar_grade_operacional(df_view: pd.DataFrame):
    if df_view is None or df_view.empty:
        st.info("Sem processos para exibir no recorte atual.")
        return

    cabecalhos = [
        "Ação", "Processo", "Tipo", "Órgão", "Status Processo",
        "Status Gerencial", "Prazo", "Fase Atual",
        "Dias Líquidos", "Bloqueados", "Guias"
    ]
    larguras = [1.02, 2.20, 1.45, 1.05, 1.10, 1.25, 1.02, 1.55, 1.00, 1.00, 0.70]

    st.markdown('<div class="itcd-grid-wrap">', unsafe_allow_html=True)
    cols = st.columns(larguras)
    for c, h in zip(cols, cabecalhos):
        c.markdown(f'<div class="itcd-grid-head">{h}</div>', unsafe_allow_html=True)

    for idx, (_, row) in enumerate(df_view.iterrows(), start=1):
        st.markdown('<div class="itcd-grid-line"></div>', unsafe_allow_html=True)
        cols = st.columns(larguras)

        seq = _to_int(row.get("SEQ_PROCESSO_ITCD"), 0)
        num_proc = str(row.get("NUM_PROCESSO_ITCD", "") or "—")
        tipo = str(row.get("DSC_TIP_TRANSMISSAO", "") or "—")
        orgao = str(row.get("DSC_SIGLA_ORGAO_LOCAL", "") or "—")
        fase = str(row.get("DSC_TIP_FASE_GUIA", "") or "—")
        status_proc = row.get("status_processo", "A TRABALHAR")
        status_g = row.get("status_gerencial", "—")
        prazo = row.get("Prazo", "—")
        dias_liq = row.get("dias_liquidos_fiscal", 0)
        dias_bloq = row.get("dias_pendencias", 0)
        guias = row.get("Guias", 0)

        if cols[0].button("Consultar", key=f"itcd_consultar_{idx}_{seq}", use_container_width=True):
            _abrir_consulta_processo(seq)
        cols[1].markdown(
            f'<div class="itcd-proc-main">{num_proc}</div>'
            f'<div class="itcd-proc-sub">Seq. {seq}</div>',
            unsafe_allow_html=True,
        )
        cols[2].markdown(f'<div class="itcd-cell-strong">{tipo}</div>', unsafe_allow_html=True)
        cols[3].markdown(f'<div class="itcd-cell-strong">{orgao}</div>', unsafe_allow_html=True)
        cols[4].markdown(_badge_status_processo(status_proc), unsafe_allow_html=True)
        cols[5].markdown(_badge_status_gerencial(status_g), unsafe_allow_html=True)
        cols[6].markdown(_badge_status_prazo(prazo), unsafe_allow_html=True)
        cols[7].markdown(f'<div class="itcd-cell-soft">{fase}</div>', unsafe_allow_html=True)
        cols[8].markdown(f'<div class="itcd-cell-strong">{_to_int(dias_liq)} d</div>', unsafe_allow_html=True)
        cols[9].markdown(f'<div class="itcd-cell-soft">{_to_int(dias_bloq)} d</div>', unsafe_allow_html=True)
        cols[10].markdown(f'<div class="itcd-cell-soft">{_fmt_int(guias)}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def _preparar_periodo(series: pd.Series) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    serie = pd.to_datetime(series, errors="coerce").dropna()
    if serie.empty:
        return None, None
    return serie.min().normalize(), serie.max().normalize()


def _aplicar_periodo(df_view: pd.DataFrame, col: str, ativo: bool, dt_ini, dt_fim) -> pd.DataFrame:
    if not ativo or col not in df_view.columns:
        return df_view
    serie = pd.to_datetime(df_view[col], errors="coerce")
    ini = pd.Timestamp(dt_ini).normalize() if dt_ini else None
    fim = pd.Timestamp(dt_fim).normalize() if dt_fim else None
    mask = serie.notna()
    if ini is not None:
        mask &= serie.dt.normalize() >= ini
    if fim is not None:
        mask &= serie.dt.normalize() <= fim
    return df_view[mask]


def _resumo_geral(df_view: pd.DataFrame) -> dict[str, float | int]:
    ativos = df_view[df_view["ativo"]].copy()
    encerrados = df_view[df_view["encerrado"]].copy()
    total = len(df_view)
    ativos_n = len(ativos)
    encerrados_n = len(encerrados)
    concluidos_prazo = int((encerrados["dentro_do_prazo"]).sum()) if not encerrados.empty else 0
    return {
        "total": total,
        "ativos_n": ativos_n,
        "encerrados_n": encerrados_n,
        "ativos_com_pendencia": int(ativos["tem_pendencia_aberta"].sum()) if not ativos.empty else 0,
        "ativos_sem_distribuicao": int(ativos["sem_distribuicao"].sum()) if not ativos.empty else 0,
        "taxa_okr": _num(concluidos_prazo / max(encerrados_n, 1), 0.0),
        "media_liq_enc": _num(encerrados["dias_liquidos_fiscal"].mean() if not encerrados.empty else 0, 0.0),
        "mediana_liq_enc": _num(encerrados["dias_liquidos_fiscal"].median() if not encerrados.empty else 0, 0.0),
        "dias_bloq_med": _num(df_view["dias_pendencias"].mean() if not df_view.empty else 0, 0.0),
        "concluido_prazo": concluidos_prazo,
        "concluido_atraso": int((~encerrados["dentro_do_prazo"]).sum()) if not encerrados.empty else 0,
        "prazo_bruto_med": _num(encerrados["dias_brutos_fiscal"].mean() if not encerrados.empty else 0, 0.0),
        "prazo_bloq_med": _num(encerrados["dias_pendencias"].mean() if not encerrados.empty else 0, 0.0),
    }


def _distribuicao_status(df_view: pd.DataFrame) -> pd.DataFrame:
    grp = df_view.groupby("status_gerencial", dropna=False).size().reset_index(name="quantidade")
    grp["status_gerencial"] = pd.Categorical(grp["status_gerencial"], categories=STATUS_ORDENADOS, ordered=True)
    return grp.sort_values("status_gerencial")


def _por_orgao(df_view: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    grp = (
        df_view.groupby("DSC_SIGLA_ORGAO_LOCAL", dropna=False)
        .agg(
            total=("SEQ_PROCESSO_ITCD", "count"),
            ativos=("ativo", "sum"),
            encerrados=("encerrado", "sum"),
            com_pendencia_aberta=("tem_pendencia_aberta", "sum"),
            sem_distribuicao=("sem_distribuicao", "sum"),
            media_liq=("dias_liquidos_fiscal", "mean"),
            mediana_liq=("dias_liquidos_fiscal", "median"),
        )
        .reset_index()
    )
    encerrados = df_view[df_view["encerrado"]].copy()
    if not encerrados.empty:
        desempenho = (
            encerrados.groupby("DSC_SIGLA_ORGAO_LOCAL", dropna=False)
            .agg(
                dentro=("dentro_do_prazo", "sum"),
                media_liq_enc=("dias_liquidos_fiscal", "mean"),
            )
            .reset_index()
        )
        grp = grp.merge(desempenho, on="DSC_SIGLA_ORGAO_LOCAL", how="left")
    else:
        grp["dentro"] = 0
        grp["media_liq_enc"] = 0.0
    grp["dentro"] = grp["dentro"].fillna(0)
    grp["taxa_okr"] = grp["dentro"] / grp["encerrados"].replace(0, pd.NA)
    grp["taxa_okr"] = grp["taxa_okr"].fillna(0.0)
    grp["media_liq_enc"] = grp["media_liq_enc"].fillna(0.0)
    return grp.sort_values("total", ascending=False).head(top_n)


def _evolucao_mensal(df_view: pd.DataFrame) -> pd.DataFrame:
    encerrados = df_view[df_view["encerrado"] & df_view["mes_encerramento"].notna()].copy()
    if encerrados.empty:
        return pd.DataFrame()
    grp = (
        encerrados.groupby("mes_encerramento", dropna=False)
        .agg(
            total=("SEQ_PROCESSO_ITCD", "count"),
            dentro=("dentro_do_prazo", "sum"),
            media_liq=("dias_liquidos_fiscal", "mean"),
        )
        .reset_index()
    )
    grp["fora"] = grp["total"] - grp["dentro"]
    grp["taxa_okr"] = grp["dentro"] / grp["total"].clip(lower=1)
    return grp.sort_values("mes_encerramento")


def _serie_entrada_distribuicao(df_view: pd.DataFrame) -> pd.DataFrame:
    criado = (
        df_view[df_view["DAT_CRIACAO"].notna()]
        .assign(periodo=lambda x: pd.to_datetime(x["DAT_CRIACAO"]).dt.to_period("M").astype(str), tipo="Criação")
        .groupby(["periodo", "tipo"], dropna=False)
        .size().reset_index(name="quantidade")
    )
    distribuido = (
        df_view[df_view["DAT_DISTRIBUICAO"].notna()]
        .assign(periodo=lambda x: pd.to_datetime(x["DAT_DISTRIBUICAO"]).dt.to_period("M").astype(str), tipo="Distribuição")
        .groupby(["periodo", "tipo"], dropna=False)
        .size().reset_index(name="quantidade")
    )
    serie = pd.concat([criado, distribuido], ignore_index=True)
    return serie.sort_values(["periodo", "tipo"]) if not serie.empty else serie


st.markdown(
    f"""
    <div class="hero">
        {_itcd_img}
        <div class="hero-kicker">⚖️ ITCD · SEFAZ-CE</div>
        <h1>Painel de Processos</h1>
        <p>{APP_SUBTITLE}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

spec = get_spec()
if not spec.existe:
    st.error(
        f"Arquivo de dados não encontrado: `{spec.path}`\n\n"
        "Coloque o arquivo **ITCD.xlsx** em `itcd/data/`."
    )
    st.stop()

with st.spinner(LOADING_MESSAGES["okr"]):
    df_base = calcular_processos_enriquecidos()
    pend_df_base = get_pendencias_enriquecidas()

for col in [
    "DSC_SIGLA_ORGAO_LOCAL", "DSC_TIP_TRANSMISSAO", "DSC_TIP_FASE_GUIA",
    "Prazo", "DSC_ORIGEM_PROCESSO", "DSC_DIST_AUTOMATICA", "status_okr", "status_gerencial"
]:
    if col in df_base.columns:
        df_base[col] = df_base[col].astype(str).str.strip()

_aplicar_estilo_grade_itcd()

st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">🧭 Leitura recomendada</div>
        <div class="coate-section-title">Status gerencial como leitura principal da carteira</div>
        <div class="coate-section-desc">
            Nesta versão, o <strong>Status Gerencial</strong> vira a leitura principal do módulo.
            <strong>Ativo/Encerrado</strong> permanece como indicador de estoque e o <strong>Status OKR</strong>
            segue como apoio para prazo e produtividade.
        </div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

with st.expander("Entenda os indicadores e filtros deste painel"):
    st.markdown(
        f"""
        - **Status Gerencial**: situação operacional principal do processo. É o indicador mestre da carteira.
        - **Ativo / Encerrado**: leitura de estoque. Ativo = ainda não concluído nem cancelado.
        - **Status OKR**: leitura de prazo e produtividade.
        - **Prazo**: situação de prazo do processo.
        - **Dias Líquidos do Fiscal**: dias brutos menos dias bloqueados por pendências.
        - **Períodos**: você pode aplicar janelas separadas de **criação** e **distribuição**.
          Quando o filtro de distribuição estiver desligado, processos sem distribuição continuam no recorte.
        - **Meta de referência do prazo líquido**: ≤ **{PRAZO_META_DIAS} dias**.
        """
    )

st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">🔎 Filtros gerenciais e operacionais</div>
        <div class="coate-section-title">Recorte único para gráficos, KPIs e lista operacional</div>
        <div class="coate-section-desc">
            Os filtros abaixo controlam toda a página. A lista operacional passou a fazer parte do próprio painel.
        </div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

f1, f2, f3, f4, f5 = st.columns(5)
with f1:
    busca = st.text_input(
        "🔍 Nº Processo / Seq.",
        placeholder="Ex.: 202502001417",
        help="Busca pelo número do processo ou pelo sequencial interno.",
    )
with f2:
    filtro_orgao = st.selectbox(
        "Órgão",
        ["Todos"] + sorted(df_base["DSC_SIGLA_ORGAO_LOCAL"].dropna().unique().tolist()),
        help="Filtra pelo órgão local responsável pelo processo.",
    )
with f3:
    filtro_tipo = st.selectbox(
        "Tipo de Transmissão",
        ["Todos"] + sorted(df_base["DSC_TIP_TRANSMISSAO"].dropna().unique().tolist()),
        help="Separa processos Inter Vivos e Causa Mortis.",
    )
with f4:
    filtro_fase = st.selectbox(
        "Fase Atual",
        ["Todas"] + sorted(df_base["DSC_TIP_FASE_GUIA"].dropna().unique().tolist()),
        help="Mostra apenas processos que hoje estão na fase selecionada.",
    )
with f5:
    filtro_status_gerencial = st.selectbox(
        "Status Gerencial",
        ["Todos"] + STATUS_ORDENADOS,
        help="Indicador principal da carteira. Resume estoque, pendência, atraso e encerramento.",
    )

f6, f7, f8, f9, f10 = st.columns(5)
with f6:
    filtro_status_processo = st.selectbox(
        "Status do Processo",
        ["Todos"] + STATUS_PROCESSO_LABELS,
        help="Baseado em Fase Mínima e Fase Máxima: CONCLUÍDO se ambas estiverem entre 5 e 11, caso contrário A TRABALHAR.",
    )
with f7:
    filtro_prazo = st.selectbox(
        "Prazo",
        ["Todos"] + sorted(df_base["Prazo"].dropna().unique().tolist()),
        help="Situação de prazo do processo.",
    )
with f8:
    filtro_origem = st.selectbox(
        "Origem",
        ["Todos"] + sorted(df_base["DSC_ORIGEM_PROCESSO"].dropna().unique().tolist()),
        help="Origem do processo conforme a base.",
    )
with f9:
    dias_max = max(_to_int(df_base["dias_liquidos_fiscal"].max(), PRAZO_META_DIAS * 3), 1)
    filtro_dias = st.slider(
        "Dias Líquidos",
        0,
        dias_max,
        (0, dias_max),
        help="Faixa do tempo líquido do fiscal no processo.",
    )
with f10:
    filtro_pend = st.selectbox(
        "Pendências",
        ["Todos", "Com pendências", "Sem pendências", "Com pendência aberta"],
        help="Recorta processos com histórico de pendência ou com pendência ainda aberta.",
    )

f11, f12, f13, f14 = st.columns(4)
with f11:
    filtro_distrib = st.selectbox(
        "Distribuição",
        ["Todos", "Com distribuição", "Sem distribuição"],
        help="Permite separar processos já distribuídos dos ainda não distribuídos.",
    )
with f12:
    filtrar_criacao = st.checkbox(
        "Filtrar por criação",
        value=False,
        help="Ativa o período inicial/final de criação do processo.",
    )
with f13:
    filtrar_distribuicao = st.checkbox(
        "Filtrar por distribuição",
        value=False,
        help="Ativa o período inicial/final de distribuição. Quando desligado, processos sem distribuição continuam no recorte.",
    )
with f14:
    mostrar_somente_ativos = st.selectbox(
        "Estoque",
        ["Todos", "Somente ativos", "Somente encerrados"],
        help="Ativo = processo ainda não concluído nem cancelado.",
    )

cri_min, cri_max = _preparar_periodo(df_base["DAT_CRIACAO"])
dist_min, dist_max = _preparar_periodo(df_base["DAT_DISTRIBUICAO"])

c_ini, c_fim, d_ini, d_fim = st.columns(4)
with c_ini:
    criacao_ini = st.date_input(
        "Criação inicial",
        value=cri_min.date() if cri_min is not None else None,
        disabled=not filtrar_criacao,
        help="Limite inferior da data de criação.",
    )
with c_fim:
    criacao_fim = st.date_input(
        "Criação final",
        value=cri_max.date() if cri_max is not None else None,
        disabled=not filtrar_criacao,
        help="Limite superior da data de criação.",
    )
with d_ini:
    distribuicao_ini = st.date_input(
        "Distribuição inicial",
        value=dist_min.date() if dist_min is not None else None,
        disabled=not filtrar_distribuicao or dist_min is None,
        help="Limite inferior da data de distribuição.",
    )
with d_fim:
    distribuicao_fim = st.date_input(
        "Distribuição final",
        value=dist_max.date() if dist_max is not None else None,
        disabled=not filtrar_distribuicao or dist_max is None,
        help="Limite superior da data de distribuição.",
    )

st.markdown("<br>", unsafe_allow_html=True)

_df = df_base.copy()
if busca.strip():
    termo = busca.strip()
    _df = _df[
        _df["NUM_PROCESSO_ITCD"].astype(str).str.contains(termo, na=False)
        | _df["SEQ_PROCESSO_ITCD"].astype(str).str.contains(termo, na=False)
    ]
if filtro_orgao != "Todos":
    _df = _df[_df["DSC_SIGLA_ORGAO_LOCAL"] == filtro_orgao]
if filtro_tipo != "Todos":
    _df = _df[_df["DSC_TIP_TRANSMISSAO"] == filtro_tipo]
if filtro_fase != "Todas":
    _df = _df[_df["DSC_TIP_FASE_GUIA"] == filtro_fase]
if filtro_status_gerencial != "Todos":
    _df = _df[_df["status_gerencial"] == filtro_status_gerencial]
if filtro_prazo != "Todos":
    _df = _df[_df["Prazo"] == filtro_prazo]
if filtro_status_processo != "Todos":
    _df = _df[_df["status_processo"] == filtro_status_processo]
if filtro_origem != "Todos":
    _df = _df[_df["DSC_ORIGEM_PROCESSO"] == filtro_origem]

_df = _df[
    (_df["dias_liquidos_fiscal"] >= filtro_dias[0])
    & (_df["dias_liquidos_fiscal"] <= filtro_dias[1])
]

if filtro_pend == "Com pendências":
    _df = _df[_df["dias_pendencias"] > 0]
elif filtro_pend == "Sem pendências":
    _df = _df[_df["dias_pendencias"] == 0]
elif filtro_pend == "Com pendência aberta":
    _df = _df[_df["tem_pendencia_aberta"]]

if filtro_distrib == "Com distribuição":
    _df = _df[_df["DAT_DISTRIBUICAO"].notna()]
elif filtro_distrib == "Sem distribuição":
    _df = _df[_df["DAT_DISTRIBUICAO"].isna()]

if mostrar_somente_ativos == "Somente ativos":
    _df = _df[_df["ativo"]]
elif mostrar_somente_ativos == "Somente encerrados":
    _df = _df[_df["encerrado"]]

_df = _aplicar_periodo(_df, "DAT_CRIACAO", filtrar_criacao, criacao_ini, criacao_fim)
_df = _aplicar_periodo(_df, "DAT_DISTRIBUICAO", filtrar_distribuicao, distribuicao_ini, distribuicao_fim)

_df = _df.sort_values(["dias_liquidos_fiscal", "dias_pendencias"], ascending=[False, False]).reset_index(drop=True)
seqs_filtrados = _df["SEQ_PROCESSO_ITCD"].dropna().astype(int).tolist() if not _df.empty else []
pend_df = pend_df_base[pend_df_base["SEQ_PROCESSO_ITCD"].isin(seqs_filtrados)].copy() if seqs_filtrados else pend_df_base.iloc[0:0].copy()
resumo = _resumo_geral(_df)
ativos = _df[_df["ativo"]].copy()
encerrados = _df[_df["encerrado"]].copy()
dist_gerencial = _distribuicao_status(_df) if not _df.empty else pd.DataFrame(columns=["status_gerencial", "quantidade"])
por_orgao = _por_orgao(_df, 20) if not _df.empty else pd.DataFrame()
evol = _evolucao_mensal(_df)
serie_fluxo = _serie_entrada_distribuicao(_df)

_texto_resumo_recorte = (
    f"O recorte atual contém <strong>{_fmt_int(resumo['total'])}</strong> processos. "
    "A leitura principal é o <strong>Status Gerencial</strong>; estoque e prazo seguem como apoio. "
    f"{'Filtros temporais ativos. ' if (filtrar_criacao or filtrar_distribuicao) else ''}"
)

st.markdown(
    f"""
    <div class="exec-summary" style="margin-bottom:0.75rem;">
        {_texto_resumo_recorte}
    </div>
    """,
    unsafe_allow_html=True,
)

st.info("Para localizar, filtrar e abrir um processo específico, use a aba Lista Operacional.")

r1, r2, r3, r4 = st.columns(4)
with r1:
    st.markdown(_kpi_card("Processos no Recorte", _fmt_int(resumo["total"]), "Base filtrada", "primary", "📋", "Todos os processos após aplicação dos filtros."), unsafe_allow_html=True)
with r2:
    st.markdown(_kpi_card("Processos Ativos", _fmt_int(resumo["ativos_n"]), f"{_fmt_pct(resumo['ativos_n'] / max(resumo['total'], 1))} do recorte", "info", "📂", "Processos ainda não concluídos nem cancelados."), unsafe_allow_html=True)
with r3:
    st.markdown(_kpi_card("Concluídos", _fmt_int(resumo["encerrados_n"]), f"{_fmt_pct(resumo['encerrados_n'] / max(resumo['total'], 1))} do recorte", "success", "✅", "Processos encerrados para leitura de produtividade."), unsafe_allow_html=True)
with r4:
    st.markdown(_kpi_card("Taxa OKR", _fmt_pct(resumo["taxa_okr"]), "Concluídos no prazo", "warning", "🎯", "Concluídos com Prazo = EM DIA / concluídos."), unsafe_allow_html=True)

r5, r6, r7, r8 = st.columns(4)
with r5:
    st.markdown(_kpi_card("Ativos com Pendência", _fmt_int(resumo["ativos_com_pendencia"]), f"{_fmt_pct(resumo['ativos_com_pendencia'] / max(resumo['ativos_n'], 1))} dos ativos", "warning", "⏸️", "Ativos com pendência aberta bloqueando o fluxo."), unsafe_allow_html=True)
with r6:
    st.markdown(_kpi_card("Ativos sem Distribuição", _fmt_int(resumo["ativos_sem_distribuicao"]), f"{_fmt_pct(resumo['ativos_sem_distribuicao'] / max(resumo['ativos_n'], 1))} dos ativos", "danger", "📭", "Ativos ainda não distribuídos."), unsafe_allow_html=True)
with r7:
    st.markdown(_kpi_card("Prazo Líquido Médio", _fmt_dias(resumo["media_liq_enc"]), f"Mediana: {_fmt_dias(resumo['mediana_liq_enc'])}", "primary", "⏱️", "Tempo efetivo do fiscal nos processos encerrados."), unsafe_allow_html=True)
with r8:
    st.markdown(_kpi_card("Dias Bloqueados Médios", _fmt_dias(resumo["dias_bloq_med"]), "Média sobre o recorte", "warning", "🧱", "Tempo impactado por pendências do contribuinte."), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tabs = st.tabs(["Visão Geral", "Estoque e Fluxo", "Produtividade e Prazo", "Pendências e Órgãos", "Lista Operacional"])

with tabs[0]:
    st.markdown(
        """
        <div class="coate-section">
            <div class="coate-section-super">📊 Visão Executiva</div>
            <div class="coate-section-title">Retrato geral da carteira e do desempenho</div>
        </div>
        <hr class="coate-section-divider"/>
        """,
        unsafe_allow_html=True,
    )

    if _df.empty:
        st.info("Não há processos no recorte atual.")
    else:
        c1, c2 = st.columns([1.12, 1.08])

        with c1:
            fig = px.bar(
                dist_gerencial,
                x="status_gerencial",
                y="quantidade",
                color="status_gerencial",
                text="quantidade",
                color_discrete_map=STATUS_GERENCIAL_CORES,
                title="Distribuição por status gerencial",
                labels={"status_gerencial": "Status", "quantidade": "Processos"},
            )
            fig.update_traces(textposition="outside", marker_line_width=0)
            fig.update_layout(**{**_LAYOUT_BASE, "showlegend": False, "height": 360},
                              xaxis={"title": "", "tickangle": -20, "showgrid": False},
                              yaxis={"gridcolor": "rgba(148,163,184,0.10)"})
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("ℹ️ Entenda os status gerenciais"):
                st.markdown(
                    f"""
                    O **Status Gerencial** é calculado em sequência — cada processo recebe o **primeiro** status cuja condição for verdadeira:

                    | Status | Condição |
                    |---|---|
                    | ✅ **Concluído no Prazo** | Processo encerrado (Fase Mínima e Fase Máxima ∈ {{5…11}}) **e** coluna `Prazo` = `EM DIA` |
                    | ⚠️ **Concluído em Atraso** | Processo encerrado pelas mesmas fases, mas `Prazo` = `ATRASADO` |
                    | 📭 **Sem Distribuição** | Ativo e sem data de distribuição registrada — avaliado antes de pendência e prazo |
                    | ⏸️ **Com Pendência** | Ativo, já distribuído, com pelo menos uma pendência em aberto aguardando o contribuinte |
                    | 🔴 **Crítico** | Ativo, distribuído, sem pendência aberta, `Prazo` = `ATRASADO` **e** dias líquidos ≥ {max(PRAZO_META_DIAS * 2, 30)} dias (dobro da meta) |
                    | 🟠 **Em Risco** | Mesmas condições do Crítico, mas dias líquidos < {max(PRAZO_META_DIAS * 2, 30)} — atrasado, ainda abaixo do limiar crítico |
                    | 🟢 **Ativo Regular** | Ativo, distribuído, sem pendência aberta e dentro do prazo |
                    """
                )

        with c2:
            tipo = (
                _df.groupby(["DSC_TIP_TRANSMISSAO", "encerrado"], dropna=False)
                .size().reset_index(name="quantidade")
            )
            tipo["sit"] = tipo["encerrado"].map({True: "Encerrados", False: "Ativos"})
            fig = px.bar(
                tipo,
                x="DSC_TIP_TRANSMISSAO",
                y="quantidade",
                color="sit",
                barmode="group",
                text="quantidade",
                color_discrete_map={"Ativos": COLOR_PRIMARY, "Encerrados": COLOR_EM_DIA},
                title="Ativos e encerrados por tipo de transmissão",
                labels={"DSC_TIP_TRANSMISSAO": "Tipo de transmissão", "quantidade": "Processos", "sit": "Situação"},
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**{**_LAYOUT_BASE, "height": 360},
                              xaxis={"title": "", "showgrid": False},
                              yaxis={"gridcolor": "rgba(148,163,184,0.10)"})
            st.plotly_chart(fig, use_container_width=True)

        # Gráfico status_processo
        dist_status_proc = (
            _df.groupby("status_processo", dropna=False)
            .size().reset_index(name="quantidade")
        ) if not _df.empty else pd.DataFrame(columns=["status_processo", "quantidade"])
        if not dist_status_proc.empty:
            fig_sp = px.bar(
                dist_status_proc,
                x="status_processo",
                y="quantidade",
                color="status_processo",
                text="quantidade",
                color_discrete_map=STATUS_PROCESSO_COLOR_MAP,
                title="Distribuição por Status do Processo",
                labels={"status_processo": "Status", "quantidade": "Processos"},
            )
            fig_sp.update_traces(textposition="outside", marker_line_width=0)
            fig_sp.update_layout(**{**_LAYOUT_BASE, "showlegend": False, "height": 280},
                                 xaxis={"title": "", "showgrid": False},
                                 yaxis={"gridcolor": "rgba(148,163,184,0.10)"})
            st.plotly_chart(fig_sp, use_container_width=True)

        st.markdown(
            f"""
            <div class="exec-summary">
                <p>
                    O recorte atual tem <strong>{_fmt_int(resumo['ativos_n'])} processos ativos</strong> e
                    <strong>{_fmt_int(resumo['encerrados_n'])} encerrados</strong>. Entre os ativos, há
                    <strong>{_fmt_int(resumo['ativos_sem_distribuicao'])}</strong> sem distribuição e
                    <strong>{_fmt_int(resumo['ativos_com_pendencia'])}</strong> com pendência aberta.
                    Na ótica de produtividade, a taxa OKR está em <strong>{_fmt_pct(resumo['taxa_okr'])}</strong>,
                    com prazo líquido médio de <strong>{_fmt_dias(resumo['media_liq_enc'])}</strong> nos processos concluídos.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

with tabs[1]:
    st.markdown(
        """
        <div class="coate-section">
            <div class="coate-section-super">📦 Estoque e Fluxo</div>
            <div class="coate-section-title">Acúmulo operacional, entrada e distribuição</div>
        </div>
        <hr class="coate-section-divider"/>
        """,
        unsafe_allow_html=True,
    )

    e1, e2, e3, e4 = st.columns(4)
    with e1:
        st.markdown(_kpi_card("Estoque Ativo", _fmt_int(resumo["ativos_n"]), "Processos em andamento", "primary", "📂", "Carteira ativa no recorte atual."), unsafe_allow_html=True)
    with e2:
        st.markdown(_kpi_card("Sem Distribuição", _fmt_int(resumo["ativos_sem_distribuicao"]), f"{_fmt_pct(resumo['ativos_sem_distribuicao'] / max(resumo['ativos_n'],1))} do ativo", "danger", "📭", "Ativos ainda não distribuídos."), unsafe_allow_html=True)
    with e3:
        idade_media = _num(ativos["idade_processo_dias"].mean() if not ativos.empty else 0, 0.0)
        st.markdown(_kpi_card("Idade Média do Estoque", _fmt_dias(idade_media, 0), "Desde a criação", "warning", "🗂️", "Tempo médio desde a criação dos processos ativos."), unsafe_allow_html=True)
    with e4:
        st.markdown(_kpi_card("Ativos com Pendência", _fmt_int(resumo["ativos_com_pendencia"]), f"{_fmt_pct(resumo['ativos_com_pendencia'] / max(resumo['ativos_n'],1))} do ativo", "warning", "⏸️", "Ativos hoje bloqueados por pendência aberta."), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        fase_estoque = (
            ativos.groupby("DSC_TIP_FASE_GUIA", dropna=False)
            .size().reset_index(name="quantidade")
            .sort_values("quantidade", ascending=False)
            .head(12)
        ) if not ativos.empty else pd.DataFrame(columns=["DSC_TIP_FASE_GUIA", "quantidade"])
        if fase_estoque.empty:
            st.info("Sem estoque ativo para distribuir por fase.")
        else:
            fig = px.bar(
                fase_estoque,
                x="quantidade",
                y="DSC_TIP_FASE_GUIA",
                orientation="h",
                text="quantidade",
                title="Estoque ativo por fase atual",
                labels={"DSC_TIP_FASE_GUIA": "Fase", "quantidade": "Processos"},
                color="quantidade",
                color_continuous_scale=[[0, COLOR_PRIMARY], [1, COLOR_PURPLE]],
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**{**_LAYOUT_BASE, "height": 380, "showlegend": False},
                              yaxis={"categoryorder": "total ascending"},
                              xaxis={"gridcolor": "rgba(148,163,184,0.10)"})
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        idade = (
            ativos.groupby("faixa_idade_estoque", dropna=False)
            .size().reset_index(name="quantidade")
        ) if not ativos.empty else pd.DataFrame(columns=["faixa_idade_estoque", "quantidade"])
        if idade.empty:
            st.info("Sem estoque ativo para distribuir por faixa etária.")
        else:
            idade["faixa_idade_estoque"] = pd.Categorical(idade["faixa_idade_estoque"], categories=FAIXA_IDADE_ORDEM, ordered=True)
            idade = idade.sort_values("faixa_idade_estoque")
            fig = px.bar(
                idade,
                x="faixa_idade_estoque",
                y="quantidade",
                text="quantidade",
                color="faixa_idade_estoque",
                title="Idade do estoque ativo",
                labels={"faixa_idade_estoque": "Faixa de idade", "quantidade": "Processos"},
                color_discrete_sequence=[COLOR_EM_DIA, COLOR_PRIMARY, COLOR_ALERTA, COLOR_PURPLE, COLOR_ATRASADO, "#64748b"],
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**{**_LAYOUT_BASE, "height": 380, "showlegend": False},
                              xaxis={"title": "", "showgrid": False},
                              yaxis={"gridcolor": "rgba(148,163,184,0.10)"})
            st.plotly_chart(fig, use_container_width=True)

    if not serie_fluxo.empty:
        fig = px.line(
            serie_fluxo,
            x="periodo",
            y="quantidade",
            color="tipo",
            markers=True,
            title="Entrada e distribuição por mês",
            labels={"periodo": "Período", "quantidade": "Processos", "tipo": "Evento"},
            color_discrete_map={"Criação": COLOR_PRIMARY, "Distribuição": COLOR_ALERTA},
        )
        fig.update_layout(**{**_LAYOUT_BASE, "height": 360},
                          xaxis={"title": "", "showgrid": False},
                          yaxis={"gridcolor": "rgba(148,163,184,0.10)"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem datas suficientes para construir a série de criação/distribuição.")

    estoque_orgao = (
        ativos.groupby("DSC_SIGLA_ORGAO_LOCAL", dropna=False)
        .agg(
            ativos=("SEQ_PROCESSO_ITCD", "count"),
            pend_abertas=("tem_pendencia_aberta", "sum"),
            sem_distribuicao=("sem_distribuicao", "sum"),
        )
        .reset_index()
        .sort_values("ativos", ascending=False)
        .head(15)
    ) if not ativos.empty else pd.DataFrame(columns=["DSC_SIGLA_ORGAO_LOCAL", "ativos", "pend_abertas", "sem_distribuicao"])
    st.dataframe(
        estoque_orgao.rename(columns={
            "DSC_SIGLA_ORGAO_LOCAL": "Órgão",
            "ativos": "Ativos",
            "pend_abertas": "Com pendência aberta",
            "sem_distribuicao": "Sem distribuição",
        }),
        hide_index=True,
        use_container_width=True,
        height=320,
    )

with tabs[2]:
    st.markdown(
        """
        <div class="coate-section">
            <div class="coate-section-super">🎯 Produtividade e Prazo</div>
            <div class="coate-section-title">Prazo e prazo líquido do fiscal</div>
        </div>
        <hr class="coate-section-divider"/>
        """,
        unsafe_allow_html=True,
    )

    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown(_kpi_card("Concluídos no Prazo", _fmt_int(resumo["concluido_prazo"]), f"{_fmt_pct(resumo['concluido_prazo'] / max(resumo['encerrados_n'],1))} dos concluídos", "success", "✅", "Encerrados com Prazo = EM DIA."), unsafe_allow_html=True)
    with p2:
        st.markdown(_kpi_card("Concluídos em Atraso", _fmt_int(resumo["concluido_atraso"]), f"{_fmt_pct(resumo['concluido_atraso'] / max(resumo['encerrados_n'],1))} dos concluídos", "danger", "⚠️", "Encerrados com Prazo = ATRASADO."), unsafe_allow_html=True)
    with p3:
        st.markdown(_kpi_card("Prazo Bruto Médio", _fmt_dias(resumo["prazo_bruto_med"]), "Sobre processos encerrados", "primary", "📅", "Soma do tempo do fiscal nas fases de trabalho."), unsafe_allow_html=True)
    with p4:
        st.markdown(_kpi_card("Bloqueio Médio", _fmt_dias(resumo["prazo_bloq_med"]), "Sobre processos encerrados", "warning", "⏸️", "Tempo médio bloqueado por pendências."), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if not evol.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=evol["mes_encerramento"],
                y=evol["total"],
                name="Encerrados",
                yaxis="y2",
                marker_color="rgba(59,130,246,0.25)",
            ))
            fig.add_trace(go.Scatter(
                x=evol["mes_encerramento"],
                y=evol["taxa_okr"] * 100,
                name="Taxa OKR (%)",
                mode="lines+markers",
                line=dict(color=COLOR_EM_DIA, width=2.5),
                marker=dict(size=7, color=COLOR_EM_DIA),
            ))
            fig.add_hline(
                y=70,
                line_dash="dot",
                line_color=COLOR_ALERTA,
                annotation_text="Meta 70%",
                annotation_font_color=COLOR_ALERTA,
                annotation_position="top right",
            )
            fig.update_layout(
                **{**_LAYOUT_BASE, "height": 360},
                yaxis=dict(title="Taxa OKR (%)", range=[0, 110], ticksuffix="%", gridcolor="rgba(148,163,184,0.10)"),
                yaxis2=dict(title="Encerrados", overlaying="y", side="right", showgrid=False),
                xaxis=dict(title="", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ainda não há processos encerrados suficientes para medir o desempenho mensal.")

    with c2:
        desempenho_org = por_orgao.copy() if not por_orgao.empty else pd.DataFrame()
        if desempenho_org.empty:
            st.info("Sem dados suficientes por órgão para calcular taxa OKR.")
        else:
            desempenho_org = desempenho_org[desempenho_org["encerrados"] > 0].sort_values("taxa_okr", ascending=False)
            if desempenho_org.empty:
                st.info("Não há órgãos com processos encerrados no recorte atual.")
            else:
                fig = px.bar(
                    desempenho_org,
                    x="taxa_okr",
                    y="DSC_SIGLA_ORGAO_LOCAL",
                    orientation="h",
                    text=desempenho_org["taxa_okr"].map(lambda x: f"{x*100:.1f}%"),
                    color="taxa_okr",
                    color_continuous_scale=[[0, COLOR_ATRASADO], [0.5, COLOR_ALERTA], [1, COLOR_EM_DIA]],
                    title="Taxa OKR por órgão local",
                    labels={"taxa_okr": "Taxa OKR", "DSC_SIGLA_ORGAO_LOCAL": "Órgão"},
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(**{**_LAYOUT_BASE, "height": 360, "showlegend": False},
                                  xaxis={"tickformat": ".0%", "gridcolor": "rgba(148,163,184,0.10)"},
                                  yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)

with tabs[3]:
    st.markdown(
        """
        <div class="coate-section">
            <div class="coate-section-super">🧱 Pendências e Órgãos</div>
            <div class="coate-section-title">Bloqueios do contribuinte e comparativo entre unidades</div>
        </div>
        <hr class="coate-section-divider"/>
        """,
        unsafe_allow_html=True,
    )

    processos_com_pend = int(_df["tem_pendencia"].sum()) if not _df.empty else 0
    processos_com_pend_aberta = int(_df["tem_pendencia_aberta"].sum()) if not _df.empty else 0
    qtd_pendencias_total = int(pend_df["SEQ_PENDENCIA"].nunique()) if not pend_df.empty else 0
    dias_bloq_total = int(pend_df["dias_bloqueados"].sum()) if not pend_df.empty else 0
    dias_bloq_med_proc = _num(_df.loc[_df["tem_pendencia"], "dias_pendencias"].mean() if processos_com_pend > 0 else 0, 0.0)

    q1, q2, q3, q4 = st.columns(4)
    with q1:
        st.markdown(_kpi_card("Processos com Pendência", _fmt_int(processos_com_pend), f"{_fmt_pct(processos_com_pend / max(resumo['total'],1))} do recorte", "warning", "📌", "Processos que tiveram pelo menos uma pendência."), unsafe_allow_html=True)
    with q2:
        st.markdown(_kpi_card("Com Pendência Aberta", _fmt_int(processos_com_pend_aberta), f"{_fmt_pct(processos_com_pend_aberta / max(resumo['total'],1))} do recorte", "danger", "⏳", "Há pendência ainda aberta no processo."), unsafe_allow_html=True)
    with q3:
        st.markdown(_kpi_card("Qtd. de Pendências", _fmt_int(qtd_pendencias_total), "Todas as ocorrências do recorte", "primary", "🧾", "Total de pendências registradas no recorte atual."), unsafe_allow_html=True)
    with q4:
        st.markdown(_kpi_card("Dias Bloqueados Totais", _fmt_int(dias_bloq_total), f"Média: {_fmt_dias(dias_bloq_med_proc)}", "warning", "🧱", "Tempo total bloqueado por pendências."), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if pend_df.empty:
            st.info("Sem pendências no recorte atual.")
        else:
            status_pend = (
                pend_df.groupby("DSC_STA_PENDENCIA", dropna=False)
                .size().reset_index(name="quantidade")
                .sort_values("quantidade", ascending=False)
            )
            fig = px.bar(
                status_pend,
                x="DSC_STA_PENDENCIA",
                y="quantidade",
                text="quantidade",
                color="DSC_STA_PENDENCIA",
                title="Pendências por status",
                labels={"DSC_STA_PENDENCIA": "Status da pendência", "quantidade": "Quantidade"},
                color_discrete_sequence=[COLOR_ALERTA, COLOR_EM_DIA, COLOR_ATRASADO, COLOR_PURPLE, "#64748b"],
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**{**_LAYOUT_BASE, "height": 360, "showlegend": False},
                              xaxis={"title": "", "tickangle": -20, "showgrid": False},
                              yaxis={"gridcolor": "rgba(148,163,184,0.10)"})
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        if _df.empty:
            st.info("Sem processos no recorte atual.")
        else:
            pend_org = (
                _df.groupby("DSC_SIGLA_ORGAO_LOCAL", dropna=False)
                .agg(
                    processos_com_pendencia=("tem_pendencia", "sum"),
                    processos_com_pend_aberta=("tem_pendencia_aberta", "sum"),
                    dias_bloqueados=("dias_pendencias", "sum"),
                )
                .reset_index()
                .sort_values("dias_bloqueados", ascending=False)
                .head(15)
            )
            fig = px.bar(
                pend_org,
                x="dias_bloqueados",
                y="DSC_SIGLA_ORGAO_LOCAL",
                orientation="h",
                text="dias_bloqueados",
                color="processos_com_pend_aberta",
                title="Dias bloqueados por órgão",
                labels={"dias_bloqueados": "Dias bloqueados", "DSC_SIGLA_ORGAO_LOCAL": "Órgão", "processos_com_pend_aberta": "Com pendência aberta"},
                color_continuous_scale=[[0, COLOR_PRIMARY], [1, COLOR_ATRASADO]],
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**{**_LAYOUT_BASE, "height": 360},
                              yaxis={"categoryorder": "total ascending"},
                              xaxis={"gridcolor": "rgba(148,163,184,0.10)"})
            st.plotly_chart(fig, use_container_width=True)

    if not por_orgao.empty:
        org = por_orgao.copy()
        org["perc_pend_aberta_ativos"] = org["com_pendencia_aberta"] / org["ativos"].replace(0, pd.NA)
        org["perc_pend_aberta_ativos"] = org["perc_pend_aberta_ativos"].fillna(0.0)
        org["perc_sem_dist_ativos"] = org["sem_distribuicao"] / org["ativos"].replace(0, pd.NA)
        org["perc_sem_dist_ativos"] = org["perc_sem_dist_ativos"].fillna(0.0)

        def _alerta(row: pd.Series) -> str:
            if row["ativos"] >= 100:
                return "Pressão Operacional"
            if row["perc_sem_dist_ativos"] >= 0.25 and row["ativos"] >= 20:
                return "Fila sem Distribuição"
            if row["perc_pend_aberta_ativos"] >= 0.20 and row["ativos"] >= 20:
                return "Pendência Alta"
            if row["encerrados"] >= 30 and row["taxa_okr"] < 0.60:
                return "Desempenho Baixo"
            return "Equilibrado"

        org["alerta"] = org.apply(_alerta, axis=1)

        c3, c4 = st.columns(2)
        with c3:
            fig = px.bar(
                org.sort_values("ativos"),
                x="ativos",
                y="DSC_SIGLA_ORGAO_LOCAL",
                orientation="h",
                text="ativos",
                color="alerta",
                title="Estoque ativo por órgão",
                labels={"ativos": "Ativos", "DSC_SIGLA_ORGAO_LOCAL": "Órgão", "alerta": "Leitura gerencial"},
                color_discrete_map={
                    "Equilibrado": COLOR_EM_DIA,
                    "Desempenho Baixo": COLOR_ATRASADO,
                    "Pendência Alta": COLOR_PURPLE,
                    "Fila sem Distribuição": COLOR_ALERTA,
                    "Pressão Operacional": COLOR_PRIMARY,
                },
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**{**_LAYOUT_BASE, "height": 420},
                              yaxis={"categoryorder": "total ascending"},
                              xaxis={"gridcolor": "rgba(148,163,184,0.10)"})
            st.plotly_chart(fig, use_container_width=True)

        with c4:
            fig = px.scatter(
                org,
                x="taxa_okr",
                y="media_liq_enc",
                size="encerrados",
                color="alerta",
                hover_name="DSC_SIGLA_ORGAO_LOCAL",
                title="Taxa OKR × prazo líquido médio",
                labels={"taxa_okr": "Taxa OKR", "media_liq_enc": "Prazo líquido médio (encerrados)", "encerrados": "Encerrados"},
                color_discrete_map={
                    "Equilibrado": COLOR_EM_DIA,
                    "Desempenho Baixo": COLOR_ATRASADO,
                    "Pendência Alta": COLOR_PURPLE,
                    "Fila sem Distribuição": COLOR_ALERTA,
                    "Pressão Operacional": COLOR_PRIMARY,
                },
            )
            fig.add_vline(x=0.70, line_dash="dot", line_color=COLOR_ALERTA)
            fig.add_hline(y=PRAZO_META_DIAS, line_dash="dot", line_color=COLOR_ALERTA)
            fig.update_layout(**{**_LAYOUT_BASE, "height": 420},
                              xaxis={"tickformat": ".0%", "gridcolor": "rgba(148,163,184,0.10)"},
                              yaxis={"gridcolor": "rgba(148,163,184,0.10)"})
            st.plotly_chart(fig, use_container_width=True)

        tabela_org = org[[
            "DSC_SIGLA_ORGAO_LOCAL", "total", "ativos", "encerrados", "taxa_okr",
            "media_liq_enc", "mediana_liq", "com_pendencia_aberta", "sem_distribuicao", "alerta"
        ]].copy()
        tabela_org["taxa_okr"] = tabela_org["taxa_okr"] * 100
        st.dataframe(
            tabela_org.rename(columns={
                "DSC_SIGLA_ORGAO_LOCAL": "Órgão",
                "total": "Total",
                "ativos": "Ativos",
                "encerrados": "Encerrados",
                "taxa_okr": "Taxa OKR (%)",
                "media_liq_enc": "Prazo médio encerrados",
                "mediana_liq": "Mediana prazo líquido",
                "com_pendencia_aberta": "Com pendência aberta",
                "sem_distribuicao": "Sem distribuição",
                "alerta": "Alerta",
            }),
            hide_index=True,
            use_container_width=True,
            height=360,
            column_config={
                "Taxa OKR (%)": st.column_config.NumberColumn(format="%.1f"),
                "Prazo médio encerrados": st.column_config.NumberColumn(format="%.1f"),
                "Mediana prazo líquido": st.column_config.NumberColumn(format="%.1f"),
            },
        )

    if not pend_df.empty:
        colunas_pend = [
            "SEQ_PENDENCIA", "SEQ_PROCESSO_ITCD", "SEQ_GUIA_ITCD", "DAT_INCLUSAO", "DAT_RESPOSTA",
            "DAT_CANCELAMENTO", "DSC_STA_PENDENCIA", "dias_bloqueados", "DSC_MOTIVO"
        ]
        pend_view = pend_df[[c for c in colunas_pend if c in pend_df.columns]].copy()
        st.dataframe(
            pend_view.rename(columns={
                "SEQ_PENDENCIA": "Pendência",
                "SEQ_PROCESSO_ITCD": "Seq. Processo",
                "SEQ_GUIA_ITCD": "Seq. Guia",
                "DAT_INCLUSAO": "Dt. Inclusão",
                "DAT_RESPOSTA": "Dt. Resposta",
                "DAT_CANCELAMENTO": "Dt. Cancelamento",
                "DSC_STA_PENDENCIA": "Status",
                "dias_bloqueados": "Dias bloqueados",
                "DSC_MOTIVO": "Motivo",
            }),
            hide_index=True,
            use_container_width=True,
            height=280,
        )

with tabs[4]:
    st.markdown(
        """
        <div class="coate-section">
            <div class="coate-section-super">🧾 Lista Operacional</div>
            <div class="coate-section-title">Lista operacional dos processos</div>
            <div class="coate-section-desc">
                Aqui você localiza, exporta e abre a consulta do processo.
            </div>
        </div>
        <hr class="coate-section-divider"/>
        """,
        unsafe_allow_html=True,
    )

    total = len(_df)
    st.caption(
        f"{_fmt_int(total)} processo(s) no recorte · "
        f"Leitura principal: Status Gerencial · "
        f"Prazo líquido meta: ≤ {PRAZO_META_DIAS} dias"
    )

    if total == 0:
        st.info("Nenhum processo encontrado com os filtros atuais.")
    else:
        n_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = st.number_input("Página", min_value=1, max_value=n_pages, value=1, step=1, help="Navegue pela lista operacional paginada.")
        inicio = (page - 1) * PAGE_SIZE
        fim = inicio + PAGE_SIZE
        df_page = _df.iloc[inicio:fim].copy()

        st.markdown(
            f"""
            <div class="exec-summary">
                <p>
                    Página <strong>{page}</strong> de <strong>{n_pages}</strong> ·
                    exibindo <strong>{inicio + 1}</strong>–<strong>{min(page * PAGE_SIZE, total)}</strong>
                    de <strong>{_fmt_int(total)}</strong> processos.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        _renderizar_grade_operacional(df_page)

        st.markdown("<br>", unsafe_allow_html=True)

        COLS_EXPORT = [
            "SEQ_PROCESSO_ITCD", "NUM_PROCESSO_ITCD", "DSC_TIP_TRANSMISSAO", "DSC_SIGLA_ORGAO_LOCAL",
            "DSC_TIP_FASE_GUIA", "status_processo", "status_gerencial", "Prazo",
            "dias_brutos_fiscal", "dias_pendencias", "dias_liquidos_fiscal", "tem_pendencia_aberta",
            "sem_distribuicao", "DAT_CRIACAO", "DAT_DISTRIBUICAO", "Guias"
        ]
        RENAME_EXPORT = {
            "SEQ_PROCESSO_ITCD": "Seq. Processo",
            "NUM_PROCESSO_ITCD": "Número do Processo",
            "DSC_TIP_TRANSMISSAO": "Tipo de Transmissão",
            "DSC_SIGLA_ORGAO_LOCAL": "Órgão",
            "DSC_TIP_FASE_GUIA": "Fase Atual",
            "status_processo": "Status do Processo",
            "status_gerencial": "Status Gerencial",
            "Prazo": "Prazo",
            "dias_brutos_fiscal": "Dias Brutos",
            "dias_pendencias": "Dias Bloqueados",
            "dias_liquidos_fiscal": "Dias Líquidos",
            "tem_pendencia_aberta": "Pendência Aberta",
            "sem_distribuicao": "Sem Distribuição",
            "DAT_CRIACAO": "Data de Criação",
            "DAT_DISTRIBUICAO": "Data de Distribuição",
            "Guias": "Guias",
        }
        cols_export = [c for c in COLS_EXPORT if c in _df.columns]
        df_export = _df[cols_export].rename(columns=RENAME_EXPORT)

        x1, x2, x3 = st.columns([1.2, 1.2, 2.2])
        with x1:
            st.download_button(
                f"⬇️ Exportar CSV — {_fmt_int(total)} processos",
                data=df_export.to_csv(index=False).encode("utf-8-sig"),
                file_name="itcd_painel_processos_filtrado.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with x2:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_export.to_excel(writer, index=False)
            st.download_button(
                f"⬇️ Exportar XLSX — {_fmt_int(total)} processos",
                data=buf.getvalue(),
                file_name="itcd_painel_processos_filtrado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with x3:
            opcoes = [
                f"{int(row['SEQ_PROCESSO_ITCD'])} — {row['NUM_PROCESSO_ITCD']} | {row['DSC_TIP_TRANSMISSAO']} | {row['DSC_SIGLA_ORGAO_LOCAL']} | {row['status_gerencial']}"
                for _, row in _df.head(300).iterrows()
            ]
            col_sel, col_btn = st.columns([4, 1])
            with col_sel:
                selecao = st.selectbox(
                    "Abrir consulta do processo",
                    opcoes,
                    label_visibility="collapsed",
                    help="Abre a página de detalhe do processo selecionado.",
                )
            with col_btn:
                if st.button("🔎 Consultar", use_container_width=True, type="primary", key="itcd_open_go"):
                    seq_sel = int(selecao.split(" — ")[0])
                    _abrir_consulta_processo(seq_sel)

st.markdown(
    f"""
    <div class="coate-footer">
        ITCD · Painel de Processos · Painel COATE · SEFAZ-CE ·
        Leitura principal: Status Gerencial ·
        Prazo líquido meta: ≤ {PRAZO_META_DIAS} dias ·
        Pendências vinculadas por processo e por guia
    </div>
    """,
    unsafe_allow_html=True,
)
