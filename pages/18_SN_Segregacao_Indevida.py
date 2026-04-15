import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

from pathlib import Path
import base64 as _b64mod

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from coate_auth import exigir_acesso
from coate_styles import aplicar_estilos

aplicar_estilos()
exigir_acesso("simples")

_DATA_DIR = Path(__file__).resolve().parent.parent / "simples_nacional" / "data"
_REQUIRED_COLUMNS = {
    "ano_apuracao", "mes_apuracao", "cod_cnpj_matriz", "dsc_razao_social",
    "dsc_orgao_local", "dsc_municipio", "dsc_regime_rec_contribuinte",
    "dsc_sit_atu_contribuinte", "dsc_segmento", "cod_icms", "desc_cod_icms",
    "vlr_receita_atividade", "vlr_diferenca_icms", "vlr_esperado_icms", "vlr_imposto",
}

CORES_ANO = {
    "2021": "#6366f1", "2022": "#3b82f6", "2023": "#06b6d4",
    "2024": "#22c55e", "2025": "#f59e0b",
}
CORES_ICMS = {
    45: "#f59e0b",
    10: "#ef4444",
    67: "#a855f7",
}
CORES_SEGMENTO = {
    "COMERCIO VAREJISTA": "#3b82f6",
    "INDUSTRIA": "#22c55e",
    "COMERCIO ATACADISTA": "#f59e0b",
    "OUTROS SEGMENTOS": "#94a3b8",
    "SERVICOS DE TRANSPORTE": "#06b6d4",
    "PRODUTOR AGROPECUARIO": "#84cc16",
    "SERVICOS DE COMUNICACAO": "#a855f7",
    "CONSTRUCAO CIVIL": "#f97316",
    "COMBUSTIVEL": "#ec4899",
}
MESES_ABREV = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
               7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}

OPCOES_SEGREGACAO = {
    "Todos": None,
    "45 — Isenção/Redução": [45],
    "10+67 — Isenções (Antecipação + Cesta Básica)": [10, 67],
    "45+67 — Isenções (Isenção/Redução + Cesta Básica)": [45, 67],
    "10 — Antecipação com encerramento de tributação": [10],
    "67 — Isenção de cesta básica/redução de cesta básica": [67],
}


def _resolver_arquivo_dados() -> Path | None:
    candidatos = [
        _DATA_DIR / "Segregação_Indevida.xlsx",
        _DATA_DIR / "Segregacao_Indevida.xlsx",
        _DATA_DIR / "Segregação Indevida.xlsx",
    ]
    for c in candidatos:
        if c.exists():
            return c
    for c in sorted(_DATA_DIR.glob("*.xlsx")):
        if "segrega" in c.name.lower():
            return c
    return None


_DATA_PATH = _resolver_arquivo_dados()


@st.cache_data(ttl=3600)
def _carregar_dados(path: str) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    sheet = "default_1" if "default_1" in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet)

    faltantes = _REQUIRED_COLUMNS.difference(df.columns)
    if faltantes:
        raise ValueError("Colunas ausentes: " + ", ".join(sorted(faltantes)))

    df = df.copy()

    # Fix encoding latin1 → utf-8
    str_cols = [
        "dsc_razao_social", "dsc_cnae_princ_contribuinte", "desc_cod_icms",
        "atividade", "tipo", "dsc_orgao_local", "dsc_municipio",
        "dsc_segmento", "dsc_regime_rec_contribuinte", "dsc_sit_atu_contribuinte",
    ]
    for col in str_cols:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.encode("latin1", errors="ignore")
                .str.decode("utf-8", errors="ignore")
                .str.strip()
            )

    df["vlr_diferenca_icms"] = pd.to_numeric(df["vlr_diferenca_icms"], errors="coerce").fillna(0)
    df["vlr_esperado_icms"]  = pd.to_numeric(df["vlr_esperado_icms"],  errors="coerce").fillna(0)
    df["vlr_receita_atividade"] = pd.to_numeric(df["vlr_receita_atividade"], errors="coerce").fillna(0)
    df["vlr_imposto"] = pd.to_numeric(df["vlr_imposto"], errors="coerce").fillna(0)
    df["ano_apuracao"]  = df["ano_apuracao"].astype(int)
    df["mes_apuracao"]  = df["mes_apuracao"].astype(int)
    df["cod_icms"]      = df["cod_icms"].astype(int)
    df["cod_cnpj_matriz"] = df["cod_cnpj_matriz"].astype(str).str.zfill(14)
    df["ano_mes"] = df["ano_apuracao"].astype(str) + "/" + df["mes_apuracao"].astype(str).str.zfill(2)
    df["mes_label"] = df["mes_apuracao"].map(MESES_ABREV)
    return df


def _fmt_int(v) -> str:
    try:
        return f"{int(v):,}".replace(",", ".")
    except Exception:
        return "0"


def _fmt_moeda(v: float) -> str:
    try:
        v = float(v)
    except Exception:
        return "R$ 0"
    if abs(v) >= 1_000_000_000:
        return f"R$ {v / 1_000_000_000:.2f} Bi"
    if abs(v) >= 1_000_000:
        return f"R$ {v / 1_000_000:.2f} Mi"
    if abs(v) >= 1_000:
        return f"R$ {v / 1_000:.1f} K"
    return f"R$ {v:,.2f}".replace(",", ".")


def _fmt_moeda_full(v: float) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _fmt_pct(v: float, digits: int = 1) -> str:
    try:
        return f"{float(v):.{digits}f}%"
    except Exception:
        return "0,0%"


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


# ── Ícone ──────────────────────────────────────────────────────────────────────
_sn_icon_path = _os.path.join(_os.path.dirname(__file__), "..", "assets", "simples_nacional_icon.png")
_sn_img = ""
if _os.path.exists(_sn_icon_path):
    with open(_sn_icon_path, "rb") as _f:
        _sn_img = (
            '<img src="data:image/png;base64,' + _b64mod.b64encode(_f.read()).decode() + '" '
            'style="height:56px;border-radius:10px;margin-bottom:0.6rem;display:block;" '
            'alt="Simples Nacional">'
        )

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="coate-hero">
        <div class="coate-hero-kicker">🗂️ Simples Nacional · SEFAZ-CE</div>
        """
    + _sn_img
    + """
        <h1>🔍 Segregação Indevida</h1>
        <p>
            Monitoramento de contribuintes do Simples Nacional que utilizaram códigos de
            segregação não permitidos no Ceará: <strong>Isenção/Redução (45)</strong>,
            <strong>Antecipação com encerramento de tributação (10)</strong> e
            <strong>Isenção de cesta básica (67)</strong>. Análise de receita declarada
            indevidamente e diferença de ICMS apurada.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Carga ──────────────────────────────────────────────────────────────────────
if _DATA_PATH is None:
    st.markdown(
        """
        <div class="coate-alert alert-danger" style="margin-top:1rem;">
            <div class="coate-alert-icon">❌</div>
            <div class="coate-alert-body">
                <strong>Planilha não encontrada.</strong><br>
                Coloque o arquivo <code>Segregação_Indevida.xlsx</code> na pasta
                <code>simples_nacional/data/</code> e recarregue a página.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

with st.spinner("⏳ Carregando os dados de segregação indevida... isso pode levar alguns segundos."):
    try:
        df_full = _carregar_dados(str(_DATA_PATH))
    except Exception as exc:
        st.markdown(
            """
            <div class="coate-alert alert-danger" style="margin-top:1rem;">
                <div class="coate-alert-icon">❌</div>
                <div class="coate-alert-body">
                    <strong>Erro ao processar a planilha.</strong><br>
                    """ + str(exc) + """
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

if df_full.empty:
    st.markdown(
        """
        <div class="coate-alert alert-warning" style="margin-top:1rem;">
            <div class="coate-alert-icon">⚠️</div>
            <div class="coate-alert-body">
                <strong>Planilha sem registros.</strong>
                Verifique se o arquivo está preenchido corretamente.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ── Filtros ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="coate-section" style="margin-top:0.5rem;">
        <div class="coate-section-super">🔧 Filtros</div>
        <div class="coate-section-title">Segmentação da Análise</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

anos_disp = ["Todos"] + sorted(df_full["ano_apuracao"].unique().tolist(), reverse=False)
regimes_disp = ["Todos", "MICROEMPRESA + EPP"] + sorted(
    [r for r in df_full["dsc_regime_rec_contribuinte"].unique().tolist()
     if r not in ("MICROEMPRESA", "EPP")],
) + ["MICROEMPRESA", "EPP"]
segmentos_disp = ["Todos"] + sorted(df_full["dsc_segmento"].unique().tolist())
situacoes_disp = ["Todas"] + sorted(df_full["dsc_sit_atu_contribuinte"].unique().tolist())

f1, f2, f3 = st.columns(3)
with f1:
    ano_sel = st.selectbox("Ano de apuração", options=anos_disp, index=0)
with f2:
    segreg_sel = st.selectbox("Tipo de segregação", options=list(OPCOES_SEGREGACAO.keys()), index=0)
with f3:
    regime_sel = st.selectbox("Regime de recolhimento", options=regimes_disp, index=0)

# Montar opções de CNAE: "Todos" + "cod — descrição"
_cnaes_raw = (
    df_full[["cod_cnae_princ_contribuinte", "dsc_cnae_princ_contribuinte"]]
    .drop_duplicates()
    .dropna()
    .sort_values("cod_cnae_princ_contribuinte")
)
cnaes_disp = ["Todos"] + [
    str(int(row["cod_cnae_princ_contribuinte"])) + " — " + str(row["dsc_cnae_princ_contribuinte"])
    for _, row in _cnaes_raw.iterrows()
]

f4, f5, f6, f7 = st.columns(4)
with f4:
    meses_disp = ["Todos"] + list(range(1, 13))
    meses_labels = ["Todos"] + [MESES_ABREV[m] for m in range(1, 13)]
    mes_idx = st.selectbox(
        "Mês de apuração",
        options=list(range(len(meses_disp))),
        format_func=lambda i: meses_labels[i],
        index=0,
        disabled=(ano_sel == "Todos"),
    )
    mes_sel = meses_disp[mes_idx]
with f5:
    segmento_sel = st.selectbox("Segmento", options=segmentos_disp, index=0)
with f6:
    situacao_sel = st.selectbox("Situação cadastral", options=situacoes_disp, index=0)
with f7:
    cnae_sel = st.selectbox("CNAE Principal", options=cnaes_disp, index=0)

# ── Aplicar filtros ────────────────────────────────────────────────────────────
df = df_full.copy()

if ano_sel != "Todos":
    df = df[df["ano_apuracao"] == int(ano_sel)]
    if mes_sel != "Todos":
        df = df[df["mes_apuracao"] == int(mes_sel)]

codigos_icms = OPCOES_SEGREGACAO[segreg_sel]
if codigos_icms is not None:
    df = df[df["cod_icms"].isin(codigos_icms)]

if regime_sel == "MICROEMPRESA + EPP":
    df = df[df["dsc_regime_rec_contribuinte"].isin(["MICROEMPRESA", "EPP"])]
elif regime_sel != "Todos":
    df = df[df["dsc_regime_rec_contribuinte"] == regime_sel]

if segmento_sel != "Todos":
    df = df[df["dsc_segmento"] == segmento_sel]
if situacao_sel != "Todas":
    df = df[df["dsc_sit_atu_contribuinte"] == situacao_sel]
if cnae_sel != "Todos":
    _cod_cnae_sel = int(cnae_sel.split(" — ")[0])
    df = df[df["cod_cnae_princ_contribuinte"] == _cod_cnae_sel]

# ── Fonte ──────────────────────────────────────────────────────────────────────
_periodo_label = str(ano_sel)
if ano_sel != "Todos" and mes_sel != "Todos":
    _periodo_label = MESES_ABREV[int(mes_sel)] + "/" + str(ano_sel)

st.markdown(
    """
    <div class="coate-alert alert-info" style="margin-top:0.5rem;margin-bottom:1rem;">
        <div class="coate-alert-icon">ℹ️</div>
        <div class="coate-alert-body">
            Fonte: <strong>"""
    + _DATA_PATH.name
    + """</strong> · Recorte: <strong>"""
    + _periodo_label
    + """ · """
    + segreg_sel
    + """ · """
    + regime_sel
    + """</strong> · """
    + _fmt_int(len(df))
    + """ registros exibidos.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados.")
    st.stop()

# ── KPIs ───────────────────────────────────────────────────────────────────────
tot_cnpjs       = df["cod_cnpj_matriz"].nunique()
tot_ocorrencias = len(df)
tot_receita     = df["vlr_receita_atividade"].sum()
tot_diferenca   = df["vlr_diferenca_icms"].sum()
tot_esperado    = df["vlr_esperado_icms"].sum()
tot_apu_icms    = df["vlr_apu_icms"].sum()
# % do ICMS que deixou de ser recolhido pela segregação indevida
pct_nao_recolhido = tot_diferenca / tot_esperado * 100 if tot_esperado > 0 else 0
# Receita média por ocorrência (contexto)
receita_media_ocorr = tot_receita / tot_ocorrencias if tot_ocorrencias > 0 else 0
# Impacto médio por contribuinte
impacto_medio = tot_diferenca / tot_cnpjs if tot_cnpjs > 0 else 0

st.markdown(
    """
    <div class="coate-section" style="margin-top:1.2rem;">
        <div class="coate-section-super">📊 KPIs · """
    + _periodo_label
    + """</div>
        <div class="coate-section-title">Visão Consolidada da Segregação Indevida</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">CNPJs Envolvidos</div>
                <div class="coate-kpi-icon">🏢</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_int(tot_cnpjs)
        + """</div>
            <div class="coate-kpi-delta delta-danger">Contribuintes com segregação indevida</div>
            <div class="coate-kpi-help">CNPJs únicos com ao menos uma ocorrência no recorte selecionado.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        """
        <div class="coate-kpi-card accent-warning">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Ocorrências</div>
                <div class="coate-kpi-icon">📄</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_int(tot_ocorrencias)
        + """</div>
            <div class="coate-kpi-delta delta-warning">Declarações com segregação indevida</div>
            <div class="coate-kpi-help">Cada ocorrência representa uma atividade declarada com código irregular
                em um determinado mês/ano por um CNPJ. Um mesmo contribuinte pode gerar múltiplas ocorrências
                ao longo dos anos — por exemplo, segregando indevidamente em 12 meses × 5 anos = 60 ocorrências.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Receita Segregada Indevidamente</div>
                <div class="coate-kpi-icon">💼</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_moeda(tot_receita)
        + """</div>
            <div class="coate-kpi-delta delta-danger">Base de cálculo com código irregular</div>
            <div class="coate-kpi-help">
                Soma da receita declarada pelos contribuintes utilizando códigos de segregação
                não reconhecidos pelo Ceará (cód. 10, 45 ou 67). É a base sobre a qual o ICMS
                deveria ter incidido normalmente, mas foi indevidamente excluída do cálculo.
                Receita média por ocorrência: """
        + _fmt_moeda(receita_media_ocorr)
        + """.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

k4, k5, k6, k7 = st.columns(4)
with k4:
    st.markdown(
        """
        <div class="coate-kpi-card accent-warning">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">ICMS Declarado (Apurado)</div>
                <div class="coate-kpi-icon">🧾</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_moeda(tot_apu_icms)
        + """</div>
            <div class="coate-kpi-delta delta-warning">O que foi efetivamente declarado</div>
            <div class="coate-kpi-help">ICMS que o contribuinte efetivamente apurou e declarou no PGDAS,
                utilizando os códigos de segregação indevida. É o valor real recolhido — muito abaixo
                do que deveria ser pela legislação do Ceará.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k5:
    st.markdown(
        """
        <div class="coate-kpi-card accent-info">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">ICMS Esperado (Correto)</div>
                <div class="coate-kpi-icon">✅</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_moeda(tot_esperado)
        + """</div>
            <div class="coate-kpi-delta delta-info">O que deveria ter sido recolhido</div>
            <div class="coate-kpi-help">ICMS calculado pela alíquota efetiva do contribuinte sobre a receita
                segregada indevidamente, como se os códigos irregulares não tivessem sido utilizados.
                Representa a obrigação tributária correta perante o Estado do Ceará.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k6:
    _cor_pct = "#ef4444"
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger" style="border-left:4px solid #ef4444;">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">ICMS Não Recolhido</div>
                <div class="coate-kpi-icon">🚨</div>
            </div>
            <div class="coate-kpi-value" style="color:#ef4444;">"""
        + _fmt_moeda(tot_diferenca)
        + """</div>
            <div class="coate-kpi-delta delta-danger">"""
        + _fmt_pct(pct_nao_recolhido, 1)
        + """ do ICMS esperado deixou de ser recolhido</div>
            <div class="coate-kpi-help">Diferença entre o ICMS esperado e o efetivamente declarado.
                Representa o potencial de recuperação fiscal: de cada R$ 100 de ICMS que deveria
                ter sido recolhido, apenas R$ """
        + f"{100 - pct_nao_recolhido:.0f}"
        + """ foram pagos — os outros R$ """
        + f"{pct_nao_recolhido:.0f}"
        + """ ficaram fora da arrecadação.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k7:
    st.markdown(
        """
        <div class="coate-kpi-card accent-info">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Impacto Médio por Contribuinte</div>
                <div class="coate-kpi-icon">📐</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_moeda(impacto_medio)
        + """</div>
            <div class="coate-kpi-delta delta-info">ICMS não recolhido por CNPJ</div>
            <div class="coate-kpi-help">Valor médio de ICMS não recolhido por cada contribuinte
                envolvido na segregação indevida. Útil para priorizar a fiscalização:
                contribuintes com impacto muito acima desta média merecem atenção prioritária.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Leitura rápida ─────────────────────────────────────────────────────────────
top_seg = df.groupby("dsc_segmento")["vlr_diferenca_icms"].sum().idxmax() if not df.empty else "—"
top_seg_val = df.groupby("dsc_segmento")["vlr_diferenca_icms"].sum().max() if not df.empty else 0
top_icms_row = df.groupby(["cod_icms","desc_cod_icms"])["vlr_diferenca_icms"].sum()
top_icms_label = top_icms_row.idxmax()[1] if not top_icms_row.empty else "—"
top_icms_val = top_icms_row.max() if not top_icms_row.empty else 0
pct_top_icms = _fmt_pct(top_icms_val / tot_diferenca * 100) if tot_diferenca > 0 else "0%"

st.markdown(
    """
    <div class="coate-panel" style="margin-top:0.9rem;">
        <p>
            <strong>Leitura rápida:</strong>
            no recorte selecionado, o segmento com maior <strong>diferença de ICMS</strong> é
            <strong>"""
    + top_seg
    + """</strong> ("""
    + _fmt_moeda(top_seg_val)
    + """). O tipo de segregação que mais concentra irregularidade é
            <strong>"""
    + top_icms_label
    + """</strong>, representando <strong>"""
    + pct_top_icms
    + """</strong> do total da diferença apurada
            em <strong>"""
    + _fmt_int(tot_cnpjs)
    + """</strong> CNPJs e <strong>"""
    + _fmt_int(tot_ocorrencias)
    + """</strong> ocorrências.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

# ── Layout base dos gráficos ───────────────────────────────────────────────────
_lb = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#cbd5e1",
    font_family="Segoe UI",
    showlegend=False,
    margin=dict(t=50, b=10, l=10, r=10),
    xaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
    yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
)

# ── Seção 1 — Distribuição por tipo de segregação e evolução ──────────────────
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📊 Distribuição</div>
        <div class="coate-section-title">Por Tipo de Segregação e Evolução Anual</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

g1, g2 = st.columns(2)

with g1:
    # Barras por tipo de segregação
    grp_icms = (
        df.groupby(["cod_icms", "desc_cod_icms"])
        .agg(cnpjs=("cod_cnpj_matriz", "nunique"), diferenca=("vlr_diferenca_icms", "sum"))
        .reset_index()
        .sort_values("diferenca", ascending=False)
    )
    fig_icms = go.Figure()
    fig_icms.add_trace(go.Bar(
        x=grp_icms["desc_cod_icms"].tolist(),
        y=grp_icms["diferenca"].tolist(),
        marker_color=[CORES_ICMS.get(c, "#94a3b8") for c in grp_icms["cod_icms"]],
        text=[_fmt_moeda(v) for v in grp_icms["diferenca"]],
        textposition="outside",
        customdata=grp_icms[["cnpjs"]].to_numpy(),
        hovertemplate="Tipo: %{x}<br>Diferença: %{text}<br>CNPJs: %{customdata[0]}<extra></extra>",
    ))
    fig_icms.update_layout(**_layout_plot(_lb, title="Diferença ICMS por Tipo de Segregação",
                                          xaxis=dict(tickangle=-15, gridcolor="rgba(148,163,184,0.08)")))
    st.plotly_chart(fig_icms, use_container_width=True)

with g2:
    # Evolução anual da diferença ICMS
    grp_ano = (
        df_full.groupby("ano_apuracao")
        .agg(diferenca=("vlr_diferenca_icms", "sum"), cnpjs=("cod_cnpj_matriz", "nunique"))
        .reset_index()
    )
    # Aplicar filtros de segregação/regime/segmento/situação mas não de ano
    df_evol = df_full.copy()
    if codigos_icms is not None:
        df_evol = df_evol[df_evol["cod_icms"].isin(codigos_icms)]
    if regime_sel == "MICROEMPRESA + EPP":
        df_evol = df_evol[df_evol["dsc_regime_rec_contribuinte"].isin(["MICROEMPRESA", "EPP"])]
    elif regime_sel != "Todos":
        df_evol = df_evol[df_evol["dsc_regime_rec_contribuinte"] == regime_sel]
    if segmento_sel != "Todos":
        df_evol = df_evol[df_evol["dsc_segmento"] == segmento_sel]
    if situacao_sel != "Todas":
        df_evol = df_evol[df_evol["dsc_sit_atu_contribuinte"] == situacao_sel]
    if cnae_sel != "Todos":
        _cod_cnae_evol = int(cnae_sel.split(" — ")[0])
        df_evol = df_evol[df_evol["cod_cnae_princ_contribuinte"] == _cod_cnae_evol]

    grp_evol = (
        df_evol.groupby("ano_apuracao")
        .agg(diferenca=("vlr_diferenca_icms", "sum"), cnpjs=("cod_cnpj_matriz", "nunique"))
        .reset_index()
    )
    fig_evol = go.Figure()
    fig_evol.add_trace(go.Bar(
        x=[str(a) for a in grp_evol["ano_apuracao"]],
        y=grp_evol["diferenca"].tolist(),
        marker_color=[CORES_ANO.get(str(a), "#94a3b8") for a in grp_evol["ano_apuracao"]],
        text=[_fmt_moeda(v) for v in grp_evol["diferenca"]],
        textposition="outside",
        customdata=grp_evol[["cnpjs"]].to_numpy(),
        hovertemplate="Ano: %{x}<br>Diferença: %{text}<br>CNPJs: %{customdata[0]}<extra></extra>",
    ))
    fig_evol.update_layout(**_layout_plot(_lb, title="Diferença ICMS por Ano"))
    st.plotly_chart(fig_evol, use_container_width=True)

# ── Seção 2 — Segmento e evolução mensal ──────────────────────────────────────
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📈 Segmento e Sazonalidade</div>
        <div class="coate-section-title">Participação por Segmento e Evolução Mensal</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

g3, g4 = st.columns(2)

with g3:
    grp_seg = (
        df.groupby("dsc_segmento")
        .agg(diferenca=("vlr_diferenca_icms", "sum"), cnpjs=("cod_cnpj_matriz", "nunique"))
        .reset_index()
        .sort_values("diferenca", ascending=False)
    )
    fig_seg = go.Figure(go.Pie(
        labels=grp_seg["dsc_segmento"].tolist(),
        values=grp_seg["diferenca"].tolist(),
        marker_colors=[CORES_SEGMENTO.get(s, "#94a3b8") for s in grp_seg["dsc_segmento"]],
        hole=0.42,
        textinfo="label+percent",
        hovertemplate="%{label}<br>Diferença: R$ %{value:,.2f}<br>%{percent}<extra></extra>",
    ))
    fig_seg.update_layout(**_layout_plot(_lb, title="Diferença ICMS por Segmento", showlegend=False))
    st.plotly_chart(fig_seg, use_container_width=True)

with g4:
    # Evolução mensal — agrupado pelo ano selecionado (ou todos os anos em linhas)
    if ano_sel != "Todos":
        grp_mes = (
            df.groupby("mes_apuracao")
            .agg(diferenca=("vlr_diferenca_icms", "sum"), cnpjs=("cod_cnpj_matriz", "nunique"))
            .reset_index()
            .sort_values("mes_apuracao")
        )
        fig_mensal = go.Figure()
        fig_mensal.add_trace(go.Scatter(
            x=[MESES_ABREV[m] for m in grp_mes["mes_apuracao"]],
            y=grp_mes["diferenca"].tolist(),
            mode="lines+markers+text",
            marker=dict(color=CORES_ANO.get(str(ano_sel), "#3b82f6"), size=8),
            line=dict(color=CORES_ANO.get(str(ano_sel), "#3b82f6"), width=2),
            text=[_fmt_moeda(v) for v in grp_mes["diferenca"]],
            textposition="top center",
            hovertemplate="Mês: %{x}<br>Diferença: %{text}<extra></extra>",
        ))
        fig_mensal.update_layout(**_layout_plot(_lb, title="Evolução Mensal — " + str(ano_sel),
                                                yaxis=dict(gridcolor="rgba(148,163,184,0.08)")))
    else:
        # Múltiplas linhas por ano
        fig_mensal = go.Figure()
        for ano in sorted(df_evol["ano_apuracao"].unique()):
            sub = (
                df_evol[df_evol["ano_apuracao"] == ano]
                .groupby("mes_apuracao")["vlr_diferenca_icms"].sum()
                .reindex(range(1, 13), fill_value=0)
            )
            fig_mensal.add_trace(go.Scatter(
                x=[MESES_ABREV[m] for m in range(1, 13)],
                y=sub.values.tolist(),
                mode="lines+markers",
                name=str(ano),
                marker=dict(color=CORES_ANO.get(str(ano), "#94a3b8"), size=6),
                line=dict(color=CORES_ANO.get(str(ano), "#94a3b8"), width=2),
                hovertemplate=str(ano) + " · %{x}: " + "R$ %{y:,.2f}<extra></extra>",
            ))
        fig_mensal.update_layout(**_layout_plot(_lb, title="Evolução Mensal por Ano",
                                                showlegend=True,
                                                legend=dict(orientation="h", y=1.08, x=0),
                                                yaxis=dict(gridcolor="rgba(148,163,184,0.08)")))
    st.plotly_chart(fig_mensal, use_container_width=True)

# ── Seção 3 — Top 10 CNPJs ────────────────────────────────────────────────────
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">🏆 Ranking</div>
        <div class="coate-section-title">Top 10 Contribuintes por Diferença de ICMS</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

grp_top = (
    df.groupby(["cod_cnpj_matriz", "dsc_razao_social", "dsc_municipio"])
    .agg(
        diferenca=("vlr_diferenca_icms", "sum"),
        receita=("vlr_receita_atividade", "sum"),
        ocorrencias=("cod_cnpj_matriz", "count"),
    )
    .reset_index()
    .sort_values("diferenca", ascending=False)
    .head(10)
)

g5, g6 = st.columns([3, 2])
with g5:
    _cores_top10 = [
        "#ef4444","#f97316","#f59e0b","#eab308","#84cc16",
        "#22c55e","#06b6d4","#3b82f6","#8b5cf6","#ec4899",
    ]
    _top_rev = grp_top.iloc[::-1].reset_index(drop=True)
    fig_top = go.Figure()
    for i, row in _top_rev.iterrows():
        fig_top.add_trace(go.Bar(
            x=[row["diferenca"]],
            y=[(row["dsc_razao_social"][:35] + "…") if len(row["dsc_razao_social"]) > 35 else row["dsc_razao_social"]],
            orientation="h",
            marker_color=_cores_top10[i % len(_cores_top10)],
            text=[_fmt_moeda(row["diferenca"])],
            textposition="outside",
            customdata=[[row["dsc_municipio"], row["ocorrencias"]]],
            hovertemplate="%{y}<br>Município: %{customdata[0]}<br>Diferença ICMS: %{text}<br>Ocorrências: %{customdata[1]}<extra></extra>",
            showlegend=False,
        ))
    fig_top.update_layout(**_layout_plot(
        _lb,
        title="Top 10 por Diferença ICMS",
        height=420,
        margin=dict(t=50, b=10, l=200, r=120),
        xaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=11)),
    ))
    st.plotly_chart(fig_top, use_container_width=True)

with g6:
    # Tabela resumida top 10
    df_top_exib = grp_top[["dsc_razao_social", "dsc_municipio", "ocorrencias", "diferenca"]].copy()
    df_top_exib.columns = ["Razão Social", "Município", "Ocorrências", "Diferença ICMS (R$)"]
    st.dataframe(
        df_top_exib,
        use_container_width=True,
        hide_index=True,
        height=380,
        column_config={
            "Razão Social": st.column_config.TextColumn("Razão Social", width="large"),
            "Município": st.column_config.TextColumn("Município"),
            "Ocorrências": st.column_config.NumberColumn("Ocorr.", format="%d"),
            "Diferença ICMS (R$)": st.column_config.NumberColumn("Diferença ICMS", format="R$ %,.2f"),
        },
    )

# ── Seção 3B — Análise por CNAE ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">🏭 Por Atividade Econômica</div>
        <div class="coate-section-title">Segregação Indevida por CNAE Principal</div>
        <div class="coate-section-desc">
            CNAEs com maior volume de irregularidade — código e descrição da atividade principal
            do contribuinte, com CNPJs envolvidos, ocorrências e diferença de ICMS apurada.
        </div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

df_cnae = (
    df.groupby(["cod_cnae_princ_contribuinte", "dsc_cnae_princ_contribuinte"])
    .agg(
        cnpjs=("cod_cnpj_matriz", "nunique"),
        ocorrencias=("cod_cnpj_matriz", "count"),
        receita=("vlr_receita_atividade", "sum"),
        icms_apurado=("vlr_apu_icms", "sum"),
        icms_esperado=("vlr_esperado_icms", "sum"),
        diferenca=("vlr_diferenca_icms", "sum"),
    )
    .reset_index()
    .sort_values("diferenca", ascending=False)
    .head(15)
)
df_cnae["cnae_label"] = df_cnae["cod_cnae_princ_contribuinte"].astype(str) + " — " + df_cnae["dsc_cnae_princ_contribuinte"].str[:40]
df_cnae["pct_nao_recol"] = (df_cnae["diferenca"] / df_cnae["icms_esperado"] * 100).round(1)

gc1, gc2 = st.columns(2)
with gc1:
    _cores_cnae = ["#ef4444","#f97316","#f59e0b","#eab308","#84cc16",
                   "#22c55e","#06b6d4","#3b82f6","#8b5cf6","#ec4899",
                   "#ef4444","#f97316","#f59e0b","#eab308","#84cc16"]
    fig_cnae_bar = go.Figure()
    _cnae_rev = df_cnae.iloc[::-1].reset_index(drop=True)
    for i, row in _cnae_rev.iterrows():
        fig_cnae_bar.add_trace(go.Bar(
            x=[row["diferenca"]],
            y=[str(int(row["cod_cnae_princ_contribuinte"])) + " — " + row["dsc_cnae_princ_contribuinte"][:30]],
            orientation="h",
            marker_color=_cores_cnae[i % len(_cores_cnae)],
            text=[_fmt_moeda(row["diferenca"])],
            textposition="outside",
            customdata=[[row["cnpjs"], row["ocorrencias"], row["pct_nao_recol"]]],
            hovertemplate=(
                "%{y}<br>"
                "Diferença ICMS: %{text}<br>"
                "CNPJs: %{customdata[0]}<br>"
                "Ocorrências: %{customdata[1]}<br>"
                "% não recolhido: %{customdata[2]:.1f}%<extra></extra>"
            ),
            showlegend=False,
        ))
    fig_cnae_bar.update_layout(**_layout_plot(
        _lb,
        title="Top 15 CNAEs por Diferença ICMS",
        height=500,
        margin=dict(t=50, b=10, l=260, r=120),
        xaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=10)),
    ))
    st.plotly_chart(fig_cnae_bar, use_container_width=True)

with gc2:
    # Pizza: participação dos top 5 CNAEs no total da diferença
    df_cnae_pizza = df_cnae.head(5).copy()
    outros = df["vlr_diferenca_icms"].sum() - df_cnae_pizza["diferenca"].sum()
    import pandas as _pd_tmp
    df_outros = _pd_tmp.DataFrame([{
        "cnae_label": "Demais CNAEs",
        "diferenca": outros,
    }])
    df_pizza_cnae = _pd_tmp.concat([df_cnae_pizza[["cnae_label","diferenca"]], df_outros], ignore_index=True)
    fig_cnae_pizza = go.Figure(go.Pie(
        labels=[str(int(r["cod_cnae_princ_contribuinte"])) + " — " + r["dsc_cnae_princ_contribuinte"][:25]
                if "cod_cnae_princ_contribuinte" in r.index else r["cnae_label"]
                for _, r in df_pizza_cnae.iterrows()],
        values=df_pizza_cnae["diferenca"].tolist(),
        hole=0.42,
        textinfo="label+percent",
        marker_colors=["#ef4444","#f97316","#f59e0b","#3b82f6","#8b5cf6","#94a3b8"],
        hovertemplate="%{label}<br>Diferença: R$ %{value:,.0f}<br>%{percent}<extra></extra>",
    ))
    fig_cnae_pizza.update_layout(**_layout_plot(
        _lb,
        title="Participação dos Top 5 CNAEs na Diferença Total",
        showlegend=False,
        height=500,
    ))
    st.plotly_chart(fig_cnae_pizza, use_container_width=True)

# Tabela resumo por CNAE
st.dataframe(
    df_cnae[[
        "cod_cnae_princ_contribuinte", "dsc_cnae_princ_contribuinte",
        "cnpjs", "ocorrencias", "receita", "icms_apurado", "icms_esperado", "diferenca", "pct_nao_recol"
    ]].rename(columns={
        "cod_cnae_princ_contribuinte": "Cód. CNAE",
        "dsc_cnae_princ_contribuinte": "Descrição CNAE",
        "cnpjs": "CNPJs",
        "ocorrencias": "Ocorrências",
        "receita": "Receita (R$)",
        "icms_apurado": "ICMS Apurado/Recolhido (R$)",
        "icms_esperado": "ICMS Esperado (R$)",
        "diferenca": "Diferença ICMS (R$)",
        "pct_nao_recol": "% Não Recolhido",
    }),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Cód. CNAE": st.column_config.NumberColumn("Cód. CNAE", format="%d"),
        "Descrição CNAE": st.column_config.TextColumn("Descrição CNAE", width="large"),
        "CNPJs": st.column_config.NumberColumn("CNPJs", format="%d"),
        "Ocorrências": st.column_config.NumberColumn("Ocorrências", format="%d"),
        "Receita (R$)": st.column_config.NumberColumn("Receita (R$)", format="R$ %,.2f"),
        "ICMS Apurado/Recolhido (R$)": st.column_config.NumberColumn("ICMS Apurado/Recolhido (R$)", format="R$ %,.2f"),
        "ICMS Esperado (R$)": st.column_config.NumberColumn("ICMS Esperado (R$)", format="R$ %,.2f"),
        "Diferença ICMS (R$)": st.column_config.NumberColumn("Diferença ICMS (R$)", format="R$ %,.2f"),
        "% Não Recolhido": st.column_config.ProgressColumn("% Não Recolhido", format="%.1f%%", min_value=0, max_value=100),
    },
)

# ── Seção 4 — Tabela de contribuintes ─────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📋 Detalhe</div>
        <div class="coate-section-title">Tabela de Contribuintes e Declarações</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

# Busca por CNPJ/razão social
busca = st.text_input(
    "🔎 Buscar por CNPJ ou Razão Social",
    placeholder="Digite parte do CNPJ ou nome...",
)

df_tabela = df.copy()
if busca.strip():
    termo = busca.strip().lower()
    df_tabela = df_tabela[
        df_tabela["cod_cnpj_matriz"].str.contains(termo, na=False)
        | df_tabela["dsc_razao_social"].str.lower().str.contains(termo, na=False)
    ]

# Paginação
LINHAS_POR_PAG = 15
total_linhas = len(df_tabela)
total_pags = max(1, (total_linhas + LINHAS_POR_PAG - 1) // LINHAS_POR_PAG)

col_info, col_pag = st.columns([3, 1])
with col_info:
    st.caption(f"{_fmt_int(total_linhas)} registros encontrados · {total_pags} página(s)")
with col_pag:
    pag_atual = st.number_input("Página", min_value=1, max_value=total_pags, value=1, step=1)

inicio = (pag_atual - 1) * LINHAS_POR_PAG
fim = inicio + LINHAS_POR_PAG
df_exib = df_tabela.iloc[inicio:fim][[
    "ano_apuracao", "mes_apuracao",
    "cod_cnpj_matriz", "dsc_razao_social",
    "dsc_municipio", "dsc_regime_rec_contribuinte", "dsc_sit_atu_contribuinte",
    "cod_cnae_princ_contribuinte", "dsc_cnae_princ_contribuinte",
    "dsc_segmento", "desc_cod_icms",
    "vlr_receita_atividade", "vlr_apu_icms", "vlr_esperado_icms", "vlr_diferenca_icms",
]].copy()
df_exib["cod_icms_desc"] = df_exib["desc_cod_icms"]
df_exib["cnae_completo"] = (
    df_exib["cod_cnae_princ_contribuinte"].astype(str).str.split(".").str[0]
    + " — " + df_exib["dsc_cnae_princ_contribuinte"]
)

st.dataframe(
    df_exib[[
        "ano_apuracao", "mes_apuracao",
        "cod_cnpj_matriz", "dsc_razao_social",
        "dsc_municipio", "dsc_regime_rec_contribuinte", "dsc_sit_atu_contribuinte",
        "cnae_completo",
        "dsc_segmento", "cod_icms_desc",
        "vlr_receita_atividade", "vlr_apu_icms", "vlr_esperado_icms", "vlr_diferenca_icms",
    ]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "ano_apuracao":               st.column_config.NumberColumn("Ano", format="%d"),
        "mes_apuracao":               st.column_config.NumberColumn("Mês", format="%d"),
        "cod_cnpj_matriz":            st.column_config.TextColumn("CNPJ"),
        "dsc_razao_social":           st.column_config.TextColumn("Razão Social", width="large"),
        "dsc_municipio":              st.column_config.TextColumn("Município"),
        "dsc_regime_rec_contribuinte":st.column_config.TextColumn("Regime"),
        "dsc_sit_atu_contribuinte":   st.column_config.TextColumn("Situação"),
        "cnae_completo":              st.column_config.TextColumn("CNAE (Cód — Descrição)", width="large"),
        "dsc_segmento":               st.column_config.TextColumn("Segmento"),
        "cod_icms_desc":              st.column_config.TextColumn("Tipo de Segregação"),
        "vlr_receita_atividade":      st.column_config.NumberColumn("Receita Segregada (R$)", format="R$ %,.2f"),
        "vlr_apu_icms":               st.column_config.NumberColumn("ICMS Declarado (R$)", format="R$ %,.2f"),
        "vlr_esperado_icms":          st.column_config.NumberColumn("ICMS Esperado (R$)", format="R$ %,.2f"),
        "vlr_diferenca_icms":         st.column_config.NumberColumn("Diferença ICMS (R$)", format="R$ %,.2f"),
    },
)

# ── Nota metodológica ─────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-panel">
        <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.7rem;">
            <span style="font-size:1.2rem;">📌</span>
            <span style="font-size:1rem;font-weight:700;color:#f1f5f9;">Nota metodológica — Segregação Indevida no PGDAS</span>
        </div>
        <p style="margin:0 0 0.6rem 0;">
            No PGDAS, os contribuintes do Simples Nacional segregam suas receitas por atividade e
            tipo de tributação. O Estado do Ceará <strong>não reconhece três códigos de segregação</strong>
            utilizados por alguns contribuintes:
        </p>
        <p style="margin:0 0 0.4rem 0;">
            <strong>Cód. 45 — Isenção/Redução:</strong> aplicado indevidamente a mercadorias que não
            possuem isenção ou redução de ICMS reconhecida pelo Ceará, gerando subcoleta do imposto.
        </p>
        <p style="margin:0 0 0.4rem 0;">
            <strong>Cód. 10 — Antecipação com encerramento de tributação:</strong> utilizado para
            operações com mercadorias sujeitas à substituição tributária, onde o contribuinte declara
            o ICMS como já encerrado, mas sem respaldo na legislação estadual.
        </p>
        <p style="margin:0 0 0.6rem 0;">
            <strong>Cód. 67 — Isenção de cesta básica/redução de cesta básica:</strong> aplicado a
            produtos que não se enquadram na lista de cesta básica do Ceará ou cuja isenção não é
            reconhecida pelo Estado.
        </p>
        <p style="margin:0;">
            A <strong>diferença de ICMS</strong> representa o valor que deveria ter sido recolhido
            caso a segregação correta tivesse sido utilizada, calculada com base na alíquota efetiva
            do contribuinte aplicada sobre a receita declarada indevidamente.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="coate-footer">Simples Nacional · Segregação Indevida · Painel COATE · SEFAZ-CE</div>',
    unsafe_allow_html=True,
)
