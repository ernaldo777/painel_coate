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
    "ANO_APURACAO", "MES_APURACAO", "HOUVE_RETIFICACAO", "FOI_NOTIFICADO",
    "NOMES_TIPOS_NOTIFICACAO", "QTD_DECLARACOES_NO_MES",
    "VLR_TOT_REC_ATIVIDADE_PRIMEIRA", "VLR_TOT_REC_ATIVIDADE_ULTIMA", "DIF_VLR_TOT_REC_ATIVIDADE",
    "VLR_APU_ICMS_PRIMEIRA", "VLR_APU_ICMS_ULTIMA", "DIF_VLR_APU_ICMS",
    "DIF_VLR_IMPOSTO",
}

CORES_ANO = {"2021": "#6366f1", "2022": "#3b82f6", "2023": "#06b6d4", "2024": "#22c55e", "2025": "#f59e0b"}
CORES_TIPO = {"EVENTO 379": "#6366f1", "EVENTO 380": "#3b82f6", "PGDAS X DIMP": "#f59e0b", "nan": "#94a3b8"}
MESES_ABREV = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
               7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}


def _resolver_arquivo() -> Path | None:
    candidatos = [
        _DATA_DIR / "Base_PGDAS_Detalhada.xlsx",
        _DATA_DIR / "Base PGDAS Detalhada.xlsx",
    ]
    for c in candidatos:
        if c.exists():
            return c
    for c in sorted(_DATA_DIR.glob("*.xlsx")):
        if "pgdas" in c.name.lower() and "detalh" in c.name.lower():
            return c
    return None


_DATA_PATH = _resolver_arquivo()


@st.cache_data(ttl=3600)
def _carregar_dados(path: str) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    sheet = "default_1" if "default_1" in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet)

    faltantes = _REQUIRED_COLUMNS.difference(df.columns)
    if faltantes:
        raise ValueError("Colunas ausentes: " + ", ".join(sorted(faltantes)))

    df = df.copy()
    num_cols = [c for c in df.columns if c.startswith(("VLR_", "DIF_", "QTD_"))]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["ANO_APURACAO"]  = df["ANO_APURACAO"].astype(int)
    df["MES_APURACAO"]  = df["MES_APURACAO"].astype(int)
    df["HOUVE_RETIFICACAO"] = df["HOUVE_RETIFICACAO"].astype(str).str.strip().str.upper()
    df["FOI_NOTIFICADO"]    = df["FOI_NOTIFICADO"].astype(str).str.strip().str.upper()
    df["NOMES_TIPOS_NOTIFICACAO"] = df["NOMES_TIPOS_NOTIFICACAO"].astype(str).str.strip()

    # Tipo principal (primeiro da lista pipe-separada)
    df["TIPO_PRINCIPAL"] = (
        df["NOMES_TIPOS_NOTIFICACAO"]
        .str.split("|")
        .str[0]
        .str.strip()
    )
    df.loc[df["TIPO_PRINCIPAL"].isin(["nan", "NAN", ""]), "TIPO_PRINCIPAL"] = "Não notificado"

    df["MES_LABEL"] = df["MES_APURACAO"].map(MESES_ABREV)
    df["ANO_MES"]   = df["ANO_APURACAO"].astype(str) + "/" + df["MES_APURACAO"].astype(str).str.zfill(2)
    df["NOTIFICADO_LABEL"] = df["FOI_NOTIFICADO"].map({"S": "Notificado", "N": "Não notificado"}).fillna("Não notificado")
    return df


def _fmt_moeda(v: float) -> str:
    try:
        v = float(v)
    except Exception:
        return "R$ 0"
    if abs(v) >= 1_000_000_000:
        return f"R$ {v/1_000_000_000:.2f} Bi"
    if abs(v) >= 1_000_000:
        return f"R$ {v/1_000_000:.1f} Mi"
    if abs(v) >= 1_000:
        return f"R$ {v/1_000:.1f} K"
    return f"R$ {v:,.2f}".replace(",", ".")


def _fmt_int(v) -> str:
    try:
        return f"{int(v):,}".replace(",", ".")
    except Exception:
        return "0"


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
        <h1>📈 Efetividade das Notificações PGDAS</h1>
        <p>
            Painel de efetividade das ações de monitoramento do Simples Nacional.
            Mede o impacto das notificações sobre a <strong>retificação de receita</strong>
            e o consequente <strong>aumento do ICMS apurado</strong> pelos contribuintes notificados.
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
                <strong>Base não encontrada.</strong><br>
                Coloque o arquivo <code>Base_PGDAS_Detalhada.xlsx</code>
                em <code>simples_nacional/data/</code> e recarregue a página.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

with st.spinner("⏳ Carregando a base de efetividade do PGDAS... aguarde um instante."):
    try:
        df_full = _carregar_dados(str(_DATA_PATH))
    except Exception as exc:
        st.markdown(
            """
            <div class="coate-alert alert-danger" style="margin-top:1rem;">
                <div class="coate-alert-icon">❌</div>
                <div class="coate-alert-body">
                    <strong>Erro ao processar a base.</strong><br>"""
            + str(exc)
            + """
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

if df_full.empty:
    st.warning("Base carregada sem registros.")
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

anos_disp = ["Todos"] + sorted(df_full["ANO_APURACAO"].unique().tolist())
tipos_notif_raw = sorted(
    [t for t in df_full["TIPO_PRINCIPAL"].unique() if t != "Não notificado"]
)
tipos_notif_disp = ["Todos"] + tipos_notif_raw

f1, f2, f3, f4 = st.columns(4)
with f1:
    ano_sel = st.selectbox("Ano de apuração", options=anos_disp, index=0)
with f2:
    meses_labels = ["Todos"] + [MESES_ABREV[m] for m in range(1, 13)]
    mes_idx = st.selectbox(
        "Mês de apuração",
        options=list(range(len(meses_labels))),
        format_func=lambda i: meses_labels[i],
        index=0,
        disabled=(ano_sel == "Todos"),
    )
    mes_sel = mes_idx  # 0 = Todos, 1..12 = jan..dez
with f3:
    notif_sel = st.selectbox(
        "Foi notificado",
        options=["Todos", "Notificado", "Não notificado"],
        index=0,
    )
with f4:
    tipo_notif_sel = st.selectbox("Tipo de notificação", options=tipos_notif_disp, index=0)

f5, f6 = st.columns([2, 4])
with f5:
    retr_sel = st.selectbox(
        "Houve retificação",
        options=["Todas", "Sim", "Não"],
        index=0,
    )

# ── Aplicar filtros ────────────────────────────────────────────────────────────
df = df_full.copy()

if ano_sel != "Todos":
    df = df[df["ANO_APURACAO"] == int(ano_sel)]
    if mes_sel > 0:
        df = df[df["MES_APURACAO"] == mes_sel]

if notif_sel == "Notificado":
    df = df[df["FOI_NOTIFICADO"] == "S"]
elif notif_sel == "Não notificado":
    df = df[df["FOI_NOTIFICADO"] != "S"]

if tipo_notif_sel != "Todos":
    df = df[df["TIPO_PRINCIPAL"] == tipo_notif_sel]

if retr_sel == "Sim":
    df = df[df["HOUVE_RETIFICACAO"] == "S"]
elif retr_sel == "Não":
    df = df[df["HOUVE_RETIFICACAO"] == "N"]

# ── Alerta de fonte ────────────────────────────────────────────────────────────
_periodo_label = str(ano_sel)
if ano_sel != "Todos" and mes_sel > 0:
    _periodo_label = MESES_ABREV[mes_sel] + "/" + str(ano_sel)

st.markdown(
    """
    <div class="coate-alert alert-info" style="margin-top:0.5rem;margin-bottom:1rem;">
        <div class="coate-alert-icon">ℹ️</div>
        <div class="coate-alert-body">
            Fonte: <strong>"""
    + _DATA_PATH.name
    + """</strong> · Recorte: <strong>"""
    + _periodo_label
    + " · " + notif_sel + " · " + tipo_notif_sel + " · Retificação: " + retr_sel
    + """</strong> · """
    + _fmt_int(len(df))
    + """ registros.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("Nenhum registro para os filtros selecionados.")
    st.stop()

# ── Calcular KPIs ──────────────────────────────────────────────────────────────
# Cada linha da base representa um GRUPO de contribuintes com mesmo perfil.
# Os totais reais estão nas colunas QTD_NOTIFICACOES e QTD_DECLARACOES.
tot_linhas = len(df)

# Notificações emitidas = soma de QTD_NOTIFICACOES_NO_MES onde FOI_NOTIFICADO=S
tot_notificacoes = int(df[df["FOI_NOTIFICADO"] == "S"]["QTD_NOTIFICACOES_NO_MES"].sum())

# Declarações de notificados que retificaram (numerador da taxa)
decl_notif_retr = int(
    df[(df["FOI_NOTIFICADO"] == "S") & (df["HOUVE_RETIFICACAO"] == "S")]["QTD_DECLARACOES_NO_MES"].sum()
)
# Declarações de notificados (denominador da taxa)
decl_notif_total = int(df[df["FOI_NOTIFICADO"] == "S"]["QTD_DECLARACOES_NO_MES"].sum())

# Taxa de retificação = declarações de notificados que retificaram / total declarações de notificados
taxa_retr_notif = decl_notif_retr / decl_notif_total * 100 if decl_notif_total > 0 else 0

# Totais para pizzas (por QTD_DECLARACOES para refletir volume real)
decl_notif_sim = decl_notif_total
decl_notif_nao = int(df[df["FOI_NOTIFICADO"] != "S"]["QTD_DECLARACOES_NO_MES"].sum())
decl_retr_sim  = int(df[df["HOUVE_RETIFICACAO"] == "S"]["QTD_DECLARACOES_NO_MES"].sum())
decl_retr_nao  = int(df[df["HOUVE_RETIFICACAO"] == "N"]["QTD_DECLARACOES_NO_MES"].sum())

# ── FOCO PRINCIPAL: Receita Total de Atividade ─────────────────────────────────
saldo_receita   = df["DIF_VLR_TOT_REC_ATIVIDADE"].sum()
aumento_receita = df[df["DIF_VLR_TOT_REC_ATIVIDADE"] > 0]["DIF_VLR_TOT_REC_ATIVIDADE"].sum()
reducao_receita = abs(df[df["DIF_VLR_TOT_REC_ATIVIDADE"] < 0]["DIF_VLR_TOT_REC_ATIVIDADE"].sum())
rec_primeira    = df["VLR_TOT_REC_ATIVIDADE_PRIMEIRA"].sum()
rec_ultima      = df["VLR_TOT_REC_ATIVIDADE_ULTIMA"].sum()

# ── FOCO PRINCIPAL: ICMS Apurado ───────────────────────────────────────────────
saldo_icms      = df["DIF_VLR_APU_ICMS"].sum()
aumento_icms    = df[df["DIF_VLR_APU_ICMS"] > 0]["DIF_VLR_APU_ICMS"].sum()
reducao_icms    = abs(df[df["DIF_VLR_APU_ICMS"] < 0]["DIF_VLR_APU_ICMS"].sum())
icms_primeira   = df["VLR_APU_ICMS_PRIMEIRA"].sum()
icms_ultima     = df["VLR_APU_ICMS_ULTIMA"].sum()

# ── IMPOSTO TOTAL (cesta Simples Nacional) ────────────────────────────────────
saldo_imposto   = df["DIF_VLR_IMPOSTO"].sum()
aumento_imposto = df[df["DIF_VLR_IMPOSTO"] > 0]["DIF_VLR_IMPOSTO"].sum()
reducao_imposto = abs(df[df["DIF_VLR_IMPOSTO"] < 0]["DIF_VLR_IMPOSTO"].sum())
imp_primeira    = df["VLR_IMPOSTO_PRIMEIRA"].sum()
imp_ultima      = df["VLR_IMPOSTO_ULTIMA"].sum()

# Índices comparativos
_ganho_rec_idx  = df[df["DIF_VLR_TOT_REC_ATIVIDADE"] > 0]["DIF_VLR_TOT_REC_ATIVIDADE"].sum()
idx_icms_rec    = (df[df["DIF_VLR_APU_ICMS"] > 0]["DIF_VLR_APU_ICMS"].sum()) / _ganho_rec_idx * 100 if _ganho_rec_idx > 0 else 0
idx_imp_rec     = aumento_imposto / _ganho_rec_idx * 100 if _ganho_rec_idx > 0 else 0
multiplicador   = idx_imp_rec / idx_icms_rec if idx_icms_rec > 0 else 0

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

# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 1 — RECEITA TOTAL DE ATIVIDADE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="coate-section" style="margin-top:1.2rem;">
        <div class="coate-section-super">💼 Indicador Principal · Receita Total de Atividade</div>
        <div class="coate-section-title">Impacto das Retificações na Receita Declarada</div>
        <div class="coate-section-desc">
            Diferença entre a <strong>última</strong> e a <strong>primeira</strong> declaração
            do mesmo contribuinte no mês. Valores positivos indicam aumento de receita
            após retificação — sinal direto de efetividade da notificação.
        </div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

r1, r2, r3, r4 = st.columns(4)
with r1:
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger" style="border-left:4px solid #22c55e;">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Ganho de Receita (Saldo)</div>
                <div class="coate-kpi-icon">📈</div>
            </div>
            <div class="coate-kpi-value" style="color:#22c55e;">"""
        + _fmt_moeda(saldo_receita)
        + """</div>
            <div class="coate-kpi-delta" style="color:#22c55e;">Última − Primeira declaração</div>
            <div class="coate-kpi-help">Saldo líquido de receita entre primeira e última declaração no recorte.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with r2:
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Aumento de Receita</div>
                <div class="coate-kpi-icon">⬆️</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_moeda(aumento_receita)
        + """</div>
            <div class="coate-kpi-delta delta-danger">Somente retificações positivas</div>
            <div class="coate-kpi-help">Soma dos casos em que a última declaração superou a primeira.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with r3:
    st.markdown(
        """
        <div class="coate-kpi-card accent-info">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Receita — 1ª Declaração</div>
                <div class="coate-kpi-icon">📄</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_moeda(rec_primeira)
        + """</div>
            <div class="coate-kpi-delta delta-info">Base de comparação</div>
            <div class="coate-kpi-help">Soma da receita declarada na primeira versão do PGDAS.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with r4:
    st.markdown(
        """
        <div class="coate-kpi-card accent-info">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Receita — Última Declaração</div>
                <div class="coate-kpi-icon">✅</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_moeda(rec_ultima)
        + """</div>
            <div class="coate-kpi-delta delta-info">Posição final</div>
            <div class="coate-kpi-help">Soma da receita declarada na última versão do PGDAS.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Gráficos de receita
gr1, gr2 = st.columns(2)

with gr1:
    # Evolução mensal do saldo de receita por ano (multilinhas) ou por mês
    df_evol = df_full.copy()
    if notif_sel == "Notificado":
        df_evol = df_evol[df_evol["FOI_NOTIFICADO"] == "S"]
    elif notif_sel == "Não notificado":
        df_evol = df_evol[df_evol["FOI_NOTIFICADO"] != "S"]
    if tipo_notif_sel != "Todos":
        df_evol = df_evol[df_evol["TIPO_PRINCIPAL"] == tipo_notif_sel]
    if retr_sel == "Sim":
        df_evol = df_evol[df_evol["HOUVE_RETIFICACAO"] == "S"]
    elif retr_sel == "Não":
        df_evol = df_evol[df_evol["HOUVE_RETIFICACAO"] == "N"]

    fig_rec_linha = go.Figure()
    anos_evol = sorted(df_evol["ANO_APURACAO"].unique())
    for ano in anos_evol:
        sub = (
            df_evol[df_evol["ANO_APURACAO"] == ano]
            .groupby("MES_APURACAO")["DIF_VLR_TOT_REC_ATIVIDADE"].sum()
            .reindex(range(1, 13), fill_value=0)
        )
        fig_rec_linha.add_trace(go.Scatter(
            x=[MESES_ABREV[m] for m in range(1, 13)],
            y=sub.values.tolist(),
            mode="lines+markers",
            name=str(ano),
            marker=dict(color=CORES_ANO.get(str(ano), "#94a3b8"), size=7),
            line=dict(color=CORES_ANO.get(str(ano), "#94a3b8"), width=2),
            hovertemplate=str(ano) + " · %{x}: R$ %{y:,.0f}<extra></extra>",
        ))
    fig_rec_linha.update_layout(**_layout_plot(
        _lb,
        title="Ganho de Receita por Mês (R$)",
        showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat=",.0f"),
    ))
    st.plotly_chart(fig_rec_linha, use_container_width=True)

with gr2:
    # Barras: aumento × redução de receita por ano
    grp_ano_rec = (
        df_evol.groupby("ANO_APURACAO").agg(
            aumento=("DIF_VLR_TOT_REC_ATIVIDADE", lambda x: x[x > 0].sum()),
            reducao=("DIF_VLR_TOT_REC_ATIVIDADE", lambda x: abs(x[x < 0].sum())),
        ).reset_index()
    )
    fig_rec_bar = go.Figure()
    fig_rec_bar.add_trace(go.Bar(
        x=[str(a) for a in grp_ano_rec["ANO_APURACAO"]],
        y=grp_ano_rec["aumento"].tolist(),
        name="Aumento",
        marker_color="#22c55e",
        text=[_fmt_moeda(v) for v in grp_ano_rec["aumento"]],
        textposition="outside",
    ))
    fig_rec_bar.add_trace(go.Bar(
        x=[str(a) for a in grp_ano_rec["ANO_APURACAO"]],
        y=grp_ano_rec["reducao"].tolist(),
        name="Redução",
        marker_color="#ef4444",
        text=[_fmt_moeda(v) for v in grp_ano_rec["reducao"]],
        textposition="outside",
    ))
    fig_rec_bar.update_layout(**_layout_plot(
        _lb,
        title="Aumento × Redução de Receita por Ano",
        barmode="group",
        showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat=",.0f"),
    ))
    st.plotly_chart(fig_rec_bar, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 2 — ICMS APURADO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="coate-section" style="margin-top:1.5rem;">
        <div class="coate-section-super">🏦 Indicador Principal · ICMS Apurado</div>
        <div class="coate-section-title">Ganho de ICMS após Retificações</div>
        <div class="coate-section-desc">
            Aumento do ICMS efetivamente apurado entre a primeira e a última declaração.
            Este é o principal indicador de <strong>recuperação fiscal</strong> resultante
            das notificações emitidas pela COATE.
        </div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

i1, i2, i3, i4 = st.columns(4)
with i1:
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger" style="border-left:4px solid #f59e0b;">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Ganho de ICMS (Saldo)</div>
                <div class="coate-kpi-icon">🏦</div>
            </div>
            <div class="coate-kpi-value" style="color:#f59e0b;">"""
        + _fmt_moeda(saldo_icms)
        + """</div>
            <div class="coate-kpi-delta" style="color:#f59e0b;">Última − Primeira declaração</div>
            <div class="coate-kpi-help">Saldo líquido de ICMS entre primeira e última declaração no recorte.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with i2:
    st.markdown(
        """
        <div class="coate-kpi-card accent-warning">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Aumento de ICMS</div>
                <div class="coate-kpi-icon">⬆️</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_moeda(aumento_icms)
        + """</div>
            <div class="coate-kpi-delta delta-warning">Somente retificações positivas</div>
            <div class="coate-kpi-help">Soma dos casos em que o ICMS final superou o inicial.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with i3:
    st.markdown(
        """
        <div class="coate-kpi-card accent-info">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">ICMS — 1ª Declaração</div>
                <div class="coate-kpi-icon">📄</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_moeda(icms_primeira)
        + """</div>
            <div class="coate-kpi-delta delta-info">Base de comparação</div>
            <div class="coate-kpi-help">ICMS apurado na primeira versão do PGDAS.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with i4:
    st.markdown(
        """
        <div class="coate-kpi-card accent-info">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">ICMS — Última Declaração</div>
                <div class="coate-kpi-icon">✅</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_moeda(icms_ultima)
        + """</div>
            <div class="coate-kpi-delta delta-info">Posição final</div>
            <div class="coate-kpi-help">ICMS apurado na última versão do PGDAS.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

gi1, gi2 = st.columns(2)

with gi1:
    fig_icms_linha = go.Figure()
    for ano in anos_evol:
        sub = (
            df_evol[df_evol["ANO_APURACAO"] == ano]
            .groupby("MES_APURACAO")["DIF_VLR_APU_ICMS"].sum()
            .reindex(range(1, 13), fill_value=0)
        )
        fig_icms_linha.add_trace(go.Scatter(
            x=[MESES_ABREV[m] for m in range(1, 13)],
            y=sub.values.tolist(),
            mode="lines+markers",
            name=str(ano),
            marker=dict(color=CORES_ANO.get(str(ano), "#94a3b8"), size=7),
            line=dict(color=CORES_ANO.get(str(ano), "#94a3b8"), width=2),
            hovertemplate=str(ano) + " · %{x}: R$ %{y:,.0f}<extra></extra>",
        ))
    fig_icms_linha.update_layout(**_layout_plot(
        _lb,
        title="Ganho de ICMS por Mês (R$)",
        showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat=",.0f"),
    ))
    st.plotly_chart(fig_icms_linha, use_container_width=True)

with gi2:
    # ICMS por tipo de notificação
    grp_tipo_icms = (
        df_evol[df_evol["FOI_NOTIFICADO"] == "S"]
        .groupby("TIPO_PRINCIPAL").agg(
            aumento_icms=("DIF_VLR_APU_ICMS", lambda x: x[x > 0].sum()),
            saldo_icms=("DIF_VLR_APU_ICMS", "sum"),
            retificacoes=("HOUVE_RETIFICACAO", lambda x: (x == "S").sum()),
            linhas=("ANO_APURACAO", "count"),
        ).reset_index().sort_values("aumento_icms", ascending=False)
    )
    fig_tipo_icms = go.Figure(go.Bar(
        x=grp_tipo_icms["TIPO_PRINCIPAL"].tolist(),
        y=grp_tipo_icms["aumento_icms"].tolist(),
        marker_color=[CORES_TIPO.get(t, "#94a3b8") for t in grp_tipo_icms["TIPO_PRINCIPAL"]],
        text=[_fmt_moeda(v) for v in grp_tipo_icms["aumento_icms"]],
        textposition="outside",
        customdata=grp_tipo_icms[["saldo_icms", "retificacoes", "linhas"]].to_numpy(),
        hovertemplate=(
            "%{x}<br>"
            "Aumento ICMS: %{text}<br>"
            "Saldo líquido: R$ %{customdata[0]:,.0f}<br>"
            "Retificações: %{customdata[1]}<br>"
            "Ocorrências: %{customdata[2]}<extra></extra>"
        ),
    ))
    fig_tipo_icms.update_layout(**_layout_plot(
        _lb,
        title="Aumento de ICMS por Tipo de Notificação",
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat=",.0f"),
    ))
    st.plotly_chart(fig_tipo_icms, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 3 — ÍNDICE DE CONVERSÃO · RECEITA × ICMS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="coate-section" style="margin-top:1.5rem;">
        <div class="coate-section-super">📐 Índice de Conversão · Receita × ICMS</div>
        <div class="coate-section-title">Quanto do Ganho de Receita se Converte em ICMS?</div>
        <div class="coate-section-desc">
            Quando a receita cresce após retificação mas o ICMS não acompanha na mesma
            proporção, pode indicar que os contribuintes estão <strong>reclassificando
            receita para atividades não tributadas</strong>, reduzindo a base do ICMS.
            O índice de conversão mede exatamente isso.
        </div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

# Calcular indicadores de conversão para o recorte atual
_rec_prim  = df["VLR_TOT_REC_ATIVIDADE_PRIMEIRA"].sum()
_rec_ult   = df["VLR_TOT_REC_ATIVIDADE_ULTIMA"].sum()
_icms_prim = df["VLR_APU_ICMS_PRIMEIRA"].sum()
_icms_ult  = df["VLR_APU_ICMS_ULTIMA"].sum()
_ganho_rec_conv  = df[df["DIF_VLR_TOT_REC_ATIVIDADE"] > 0]["DIF_VLR_TOT_REC_ATIVIDADE"].sum()
_ganho_icms_conv = df[df["DIF_VLR_APU_ICMS"] > 0]["DIF_VLR_APU_ICMS"].sum()
_pct_rec_conv  = _ganho_rec_conv  / _rec_prim  * 100 if _rec_prim  > 0 else 0
_pct_icms_conv = _ganho_icms_conv / _icms_prim * 100 if _icms_prim > 0 else 0
_indice_conv   = _ganho_icms_conv / _ganho_rec_conv * 100 if _ganho_rec_conv > 0 else 0
_diff_pct      = _pct_icms_conv - _pct_rec_conv  # positivo = ICMS cresce mais

ci1, ci2, ci3, ci4 = st.columns(4)
with ci1:
    st.markdown(
        """
        <div class="coate-kpi-card accent-info">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">% Crescimento Receita</div>
                <div class="coate-kpi-icon">💼</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_pct(_pct_rec_conv, 2)
        + """</div>
            <div class="coate-kpi-delta delta-info">Ganho ÷ Receita da 1ª declaração</div>
            <div class="coate-kpi-help">Quanto a receita cresceu entre a primeira e última declaração no recorte.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with ci2:
    st.markdown(
        """
        <div class="coate-kpi-card accent-warning">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">% Crescimento ICMS</div>
                <div class="coate-kpi-icon">🏦</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_pct(_pct_icms_conv, 2)
        + """</div>
            <div class="coate-kpi-delta delta-warning">Ganho ÷ ICMS da 1ª declaração</div>
            <div class="coate-kpi-help">Quanto o ICMS apurado cresceu entre a primeira e última declaração.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with ci3:
    _cor_indice = "#22c55e" if _indice_conv >= 1.0 else "#f59e0b"
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger" style="border-left:4px solid """
        + _cor_indice
        + """;">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Índice de Conversão</div>
                <div class="coate-kpi-icon">📐</div>
            </div>
            <div class="coate-kpi-value" style="color:"""
        + _cor_indice
        + """;">"""
        + _fmt_pct(_indice_conv, 2)
        + """</div>
            <div class="coate-kpi-delta" style="color:"""
        + _cor_indice
        + """;">Ganho ICMS ÷ Ganho Receita</div>
            <div class="coate-kpi-help">
                A cada R$ 100 de receita recuperada, R$ """
        + f"{_indice_conv:.2f}"
        + """ são convertidos em ICMS.
                Abaixo de 1% pode indicar reclassificação para atividades não tributadas.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with ci4:
    _sinal = "▲" if _diff_pct >= 0 else "▼"
    _cor_diff = "#22c55e" if _diff_pct >= 0 else "#ef4444"
    _msg_diff = "ICMS cresce mais que a receita" if _diff_pct >= 0 else "Receita cresce mais que o ICMS — atenção"
    st.markdown(
        """
        <div class="coate-kpi-card accent-info" style="border-left:4px solid """
        + _cor_diff
        + """;">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Diferença % (ICMS − Receita)</div>
                <div class="coate-kpi-icon">"""
        + _sinal
        + """</div>
            </div>
            <div class="coate-kpi-value" style="color:"""
        + _cor_diff
        + """;">"""
        + (("+" if _diff_pct >= 0 else "") + _fmt_pct(_diff_pct, 2))
        + """</div>
            <div class="coate-kpi-delta" style="color:"""
        + _cor_diff
        + """;">"""
        + _msg_diff
        + """</div>
            <div class="coate-kpi-help">Diferença entre o % de crescimento do ICMS e o % de crescimento da receita.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Gráfico duplo: evolução mensal dos dois percentuais
_df_conv = df_full.copy()
if notif_sel == "Notificado":
    _df_conv = _df_conv[_df_conv["FOI_NOTIFICADO"] == "S"]
elif notif_sel == "Não notificado":
    _df_conv = _df_conv[_df_conv["FOI_NOTIFICADO"] != "S"]
if tipo_notif_sel != "Todos":
    _df_conv = _df_conv[_df_conv["TIPO_PRINCIPAL"] == tipo_notif_sel]

_grp_conv = _df_conv.groupby(["ANO_APURACAO", "MES_APURACAO"]).agg(
    rec_prim=("VLR_TOT_REC_ATIVIDADE_PRIMEIRA", "sum"),
    ganho_rec=("DIF_VLR_TOT_REC_ATIVIDADE", lambda x: x[x > 0].sum()),
    icms_prim=("VLR_APU_ICMS_PRIMEIRA", "sum"),
    ganho_icms=("DIF_VLR_APU_ICMS", lambda x: x[x > 0].sum()),
).reset_index().sort_values(["ANO_APURACAO", "MES_APURACAO"])
_grp_conv["pct_rec"]  = (_grp_conv["ganho_rec"]  / _grp_conv["rec_prim"].replace(0, 1)  * 100).round(3)
_grp_conv["pct_icms"] = (_grp_conv["ganho_icms"] / _grp_conv["icms_prim"].replace(0, 1) * 100).round(3)
_grp_conv["indice"]   = (_grp_conv["ganho_icms"] / _grp_conv["ganho_rec"].replace(0, 1)  * 100).round(3)
_grp_conv["x_label"]  = _grp_conv["ANO_APURACAO"].astype(str) + "/" + _grp_conv["MES_APURACAO"].astype(str).str.zfill(2)

gc1, gc2 = st.columns(2)
with gc1:
    fig_conv = go.Figure()
    fig_conv.add_trace(go.Scatter(
        x=_grp_conv["x_label"].tolist(),
        y=_grp_conv["pct_rec"].tolist(),
        mode="lines+markers",
        name="% Receita",
        marker=dict(color="#22c55e", size=6),
        line=dict(color="#22c55e", width=2),
        hovertemplate="Período: %{x}<br>% Crescimento Receita: %{y:.3f}%<extra></extra>",
    ))
    fig_conv.add_trace(go.Scatter(
        x=_grp_conv["x_label"].tolist(),
        y=_grp_conv["pct_icms"].tolist(),
        mode="lines+markers",
        name="% ICMS",
        marker=dict(color="#f59e0b", size=6),
        line=dict(color="#f59e0b", width=2, dash="dot"),
        hovertemplate="Período: %{x}<br>% Crescimento ICMS: %{y:.3f}%<extra></extra>",
    ))
    fig_conv.update_layout(**_layout_plot(
        _lb,
        title="% Crescimento Receita × ICMS por Mês",
        showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0),
        xaxis=dict(tickangle=-45, gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", ticksuffix="%"),
    ))
    st.plotly_chart(fig_conv, use_container_width=True)

with gc2:
    # Índice de conversão por mês — linha com área de referência em 1%
    fig_indice = go.Figure()
    fig_indice.add_hline(
        y=1.0, line_dash="dash", line_color="#ef4444",
        annotation_text="Linha de paridade (1%)",
        annotation_position="top right",
    )
    fig_indice.add_trace(go.Scatter(
        x=_grp_conv["x_label"].tolist(),
        y=_grp_conv["indice"].tolist(),
        mode="lines+markers",
        name="Índice",
        marker=dict(
            color=["#22c55e" if v >= 1.0 else "#f59e0b" for v in _grp_conv["indice"]],
            size=8,
        ),
        line=dict(color="#3b82f6", width=2),
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.08)",
        hovertemplate="Período: %{x}<br>Índice: %{y:.3f}%<br>(R$ %{y:.3f} de ICMS por R$100 de receita)<extra></extra>",
    ))
    fig_indice.update_layout(**_layout_plot(
        _lb,
        title="Índice de Conversão ICMS/Receita por Mês",
        showlegend=False,
        xaxis=dict(tickangle=-45, gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", ticksuffix="%"),
    ))
    st.plotly_chart(fig_indice, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 4 — IMPOSTO TOTAL DA CESTA SIMPLES NACIONAL
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="coate-section" style="margin-top:1.5rem;">
        <div class="coate-section-super">💎 Indicador Ampliado · Imposto Total do Simples Nacional</div>
        <div class="coate-section-title">Ganho Total da Cesta Tributária após Retificações</div>
        <div class="coate-section-desc">
            O Simples Nacional unifica 8 tributos em uma única guia: IRPJ, CSLL, COFINS,
            PIS, CPP (INSS patronal), ICMS, IPI e ISS. O <strong>Imposto Total</strong>
            representa a soma de todos eles sobre a receita declarada. Quando o contribuinte
            retifica e aumenta sua receita, a cesta inteira cresce — não apenas o ICMS.
            Isso significa que o ganho fiscal real é <strong>muito maior</strong> do que o
            ganho de ICMS isolado, beneficiando tanto o Estado (ICMS) quanto a União
            (IRPJ, CSLL, COFINS, PIS, CPP, IPI) e os Municípios (ISS).
        </div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

it1, it2, it3, it4 = st.columns(4)
with it1:
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger" style="border-left:4px solid #22c55e;">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Ganho Total de Imposto (Saldo)</div>
                <div class="coate-kpi-icon">💎</div>
            </div>
            <div class="coate-kpi-value" style="color:#22c55e;">"""
    + _fmt_moeda(saldo_imposto)
    + """</div>
            <div class="coate-kpi-delta" style="color:#22c55e;">IRPJ + CSLL + COFINS + PIS + CPP + ICMS + IPI + ISS</div>
            <div class="coate-kpi-help">Saldo líquido da cesta tributária completa do Simples Nacional entre primeira e última declaração.
                Inclui tributos federais, estaduais e municipais — é o ganho fiscal total para todos os entes.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with it2:
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Aumento Total de Imposto</div>
                <div class="coate-kpi-icon">⬆️</div>
            </div>
            <div class="coate-kpi-value">"""
    + _fmt_moeda(aumento_imposto)
    + """</div>
            <div class="coate-kpi-delta delta-danger">Somente retificações positivas</div>
            <div class="coate-kpi-help">Soma dos casos em que o imposto total cresceu após retificação.
                Este valor representa o ganho bruto de arrecadação gerado pelas retificações,
                distribuído entre União, Estado e Municípios conforme as alíquotas do Simples.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with it3:
    st.markdown(
        """
        <div class="coate-kpi-card accent-info">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Imposto Total — 1ª Declaração</div>
                <div class="coate-kpi-icon">📄</div>
            </div>
            <div class="coate-kpi-value">"""
    + _fmt_moeda(imp_primeira)
    + """</div>
            <div class="coate-kpi-delta delta-info">Base de comparação</div>
            <div class="coate-kpi-help">Soma de todos os tributos do Simples Nacional apurados na
                primeira declaração entregue — antes de qualquer retificação motivada pela notificação.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with it4:
    st.markdown(
        """
        <div class="coate-kpi-card accent-info">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Imposto Total — Última Declaração</div>
                <div class="coate-kpi-icon">✅</div>
            </div>
            <div class="coate-kpi-value">"""
    + _fmt_moeda(imp_ultima)
    + """</div>
            <div class="coate-kpi-delta delta-info">Posição final</div>
            <div class="coate-kpi-help">Soma de todos os tributos após a última retificação.
                A diferença em relação à primeira declaração é o ganho fiscal total gerado
                pelas ações de monitoramento da COATE.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Comparativo ICMS × Imposto Total ──────────────────────────────────────────
st.markdown(
    """
    <div class="coate-section" style="margin-top:1.2rem;">
        <div class="coate-section-super">📊 Comparativo de Índices</div>
        <div class="coate-section-title">ICMS × Imposto Total: Quanto Cada R$ 100 de Receita Gera?</div>
        <div class="coate-section-desc">
            O índice de conversão mostra quantos reais de tributo são gerados a cada
            R$ 100 de receita recuperada pelas retificações. Comparar o ICMS isolado
            com o imposto total revela o quanto a União e os Municípios também ganham
            — ganho que costuma ser invisível quando se analisa apenas o ICMS estadual.
        </div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

cmp1, cmp2, cmp3 = st.columns(3)
with cmp1:
    st.markdown(
        """
        <div class="coate-kpi-card accent-warning" style="border-left:4px solid #f59e0b;">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Índice ICMS / Receita</div>
                <div class="coate-kpi-icon">🏦</div>
            </div>
            <div class="coate-kpi-value" style="color:#f59e0b;">"""
    + _fmt_pct(idx_icms_rec, 4)
    + """</div>
            <div class="coate-kpi-delta" style="color:#f59e0b;">R$ """
    + f"{idx_icms_rec:.4f}"
    + """ de ICMS por R$ 100 de receita</div>
            <div class="coate-kpi-help">A cada R$ 100 de receita recuperada pelas retificações,
                apenas R$ """
    + f"{idx_icms_rec:.2f}"
    + """ chegam ao Estado como ICMS — pois parte da receita pode ser de
                atividades não sujeitas ao ICMS ou com alíquota reduzida.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with cmp2:
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger" style="border-left:4px solid #22c55e;">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Índice Imposto Total / Receita</div>
                <div class="coate-kpi-icon">💎</div>
            </div>
            <div class="coate-kpi-value" style="color:#22c55e;">"""
    + _fmt_pct(idx_imp_rec, 4)
    + """</div>
            <div class="coate-kpi-delta" style="color:#22c55e;">R$ """
    + f"{idx_imp_rec:.4f}"
    + """ de imposto total por R$ 100 de receita</div>
            <div class="coate-kpi-help">A cada R$ 100 de receita recuperada, R$ """
    + f"{idx_imp_rec:.2f}"
    + """ são gerados como arrecadação total do Simples Nacional —
                somando ICMS, IRPJ, CSLL, COFINS, PIS, CPP, IPI e ISS.
                Este é o retorno fiscal real e completo das ações de monitoramento.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with cmp3:
    st.markdown(
        """
        <div class="coate-kpi-card accent-info" style="border-left:4px solid #3b82f6;">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Multiplicador (Imposto ÷ ICMS)</div>
                <div class="coate-kpi-icon">✖️</div>
            </div>
            <div class="coate-kpi-value" style="color:#3b82f6;">"""
    + f"{multiplicador:.1f}x"
    + """</div>
            <div class="coate-kpi-delta" style="color:#3b82f6;">O ganho total é """
    + f"{multiplicador:.1f}x"
    + """ maior que o ICMS isolado</div>
            <div class="coate-kpi-help">Para cada R$ 1 de ICMS gerado pelas retificações,
                R$ """
    + f"{multiplicador:.1f}"
    + """ são gerados em arrecadação total do Simples Nacional.
                Este multiplicador evidencia que a atuação da COATE gera um retorno fiscal
                muito maior para o conjunto dos entes federativos do que o ICMS indica sozinho.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Gráfico comparativo: evolução mensal ICMS × Imposto Total
gci1, gci2 = st.columns(2)

with gci1:
    # Linha: ganho ICMS vs ganho imposto total por mês
    _df_cmp = df_full.copy()
    if notif_sel == "Notificado":
        _df_cmp = _df_cmp[_df_cmp["FOI_NOTIFICADO"] == "S"]
    elif notif_sel == "Não notificado":
        _df_cmp = _df_cmp[_df_cmp["FOI_NOTIFICADO"] != "S"]
    if tipo_notif_sel != "Todos":
        _df_cmp = _df_cmp[_df_cmp["TIPO_PRINCIPAL"] == tipo_notif_sel]

    _grp_cmp = _df_cmp.groupby(["ANO_APURACAO","MES_APURACAO"]).agg(
        g_icms=("DIF_VLR_APU_ICMS",   lambda x: x[x>0].sum()),
        g_imp =("DIF_VLR_IMPOSTO",     lambda x: x[x>0].sum()),
    ).reset_index().sort_values(["ANO_APURACAO","MES_APURACAO"])
    _grp_cmp["x_label"] = _grp_cmp["ANO_APURACAO"].astype(str) + "/" + _grp_cmp["MES_APURACAO"].astype(str).str.zfill(2)

    fig_cmp_linha = go.Figure()
    fig_cmp_linha.add_trace(go.Scatter(
        x=_grp_cmp["x_label"].tolist(),
        y=_grp_cmp["g_imp"].tolist(),
        mode="lines+markers",
        name="Imposto Total",
        marker=dict(color="#22c55e", size=7),
        line=dict(color="#22c55e", width=2),
        hovertemplate="Período: %{x}<br>Imposto Total: R$ %{y:,.0f}<extra></extra>",
    ))
    fig_cmp_linha.add_trace(go.Scatter(
        x=_grp_cmp["x_label"].tolist(),
        y=_grp_cmp["g_icms"].tolist(),
        mode="lines+markers",
        name="ICMS",
        marker=dict(color="#f59e0b", size=7),
        line=dict(color="#f59e0b", width=2, dash="dot"),
        hovertemplate="Período: %{x}<br>ICMS: R$ %{y:,.0f}<extra></extra>",
    ))
    fig_cmp_linha.update_layout(**_layout_plot(
        _lb,
        title="Ganho: Imposto Total × ICMS por Mês (R$)",
        showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0),
        xaxis=dict(tickangle=-45, gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat=",.0f"),
    ))
    st.plotly_chart(fig_cmp_linha, use_container_width=True)

with gci2:
    # Barras agrupadas por ano: ICMS vs Imposto Total
    _grp_ano_cmp = _df_cmp.groupby("ANO_APURACAO").agg(
        g_icms=("DIF_VLR_APU_ICMS",   lambda x: x[x>0].sum()),
        g_imp =("DIF_VLR_IMPOSTO",     lambda x: x[x>0].sum()),
    ).reset_index()
    fig_cmp_bar = go.Figure()
    fig_cmp_bar.add_trace(go.Bar(
        x=[str(a) for a in _grp_ano_cmp["ANO_APURACAO"]],
        y=_grp_ano_cmp["g_imp"].tolist(),
        name="Imposto Total (8 tributos)",
        marker_color="#22c55e",
        text=[_fmt_moeda(v) for v in _grp_ano_cmp["g_imp"]],
        textposition="outside",
    ))
    fig_cmp_bar.add_trace(go.Bar(
        x=[str(a) for a in _grp_ano_cmp["ANO_APURACAO"]],
        y=_grp_ano_cmp["g_icms"].tolist(),
        name="Apenas ICMS",
        marker_color="#f59e0b",
        text=[_fmt_moeda(v) for v in _grp_ano_cmp["g_icms"]],
        textposition="outside",
    ))
    fig_cmp_bar.update_layout(**_layout_plot(
        _lb,
        title="Imposto Total × ICMS por Ano (R$)",
        barmode="group",
        showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat=",.0f"),
    ))
    st.plotly_chart(fig_cmp_bar, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 5 — EFETIVIDADE: NOTIFICAÇÃO × RETIFICAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="coate-section" style="margin-top:1.5rem;">
        <div class="coate-section-super">🎯 Efetividade · Notificação × Retificação</div>
        <div class="coate-section-title">Resultados das Ações de Monitoramento</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

e1, e2, e3 = st.columns(3)
with e1:
    st.markdown(
        """
        <div class="coate-kpi-card accent-danger">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Notificações Emitidas</div>
                <div class="coate-kpi-icon">🔔</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_int(tot_notificacoes)
        + """</div>
            <div class="coate-kpi-delta delta-danger">Total de notificações no período</div>
            <div class="coate-kpi-help">Soma das notificações emitidas (QTD_NOTIFICACOES_NO_MES) para contribuintes notificados.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with e2:
    st.markdown(
        """
        <div class="coate-kpi-card accent-warning">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Declarações Retificadas</div>
                <div class="coate-kpi-icon">✏️</div>
            </div>
            <div class="coate-kpi-value">"""
        + _fmt_int(decl_notif_retr)
        + """</div>
            <div class="coate-kpi-delta delta-warning">Entre contribuintes notificados</div>
            <div class="coate-kpi-help">Soma das declarações (QTD_DECLARACOES_NO_MES) de notificados que retificaram o PGDAS.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with e3:
    _cor_taxa = "#22c55e" if taxa_retr_notif >= 50 else "#f59e0b"
    st.markdown(
        """
        <div class="coate-kpi-card accent-info" style="border-left:4px solid """
        + _cor_taxa
        + """;">
            <div class="coate-kpi-top">
                <div class="coate-kpi-label">Taxa de Retificação</div>
                <div class="coate-kpi-icon">📊</div>
            </div>
            <div class="coate-kpi-value" style="color:"""
        + _cor_taxa
        + """;">"""
        + _fmt_pct(taxa_retr_notif)
        + """</div>
            <div class="coate-kpi-delta" style="color:"""
        + _cor_taxa
        + """;">Entre notificados</div>
            <div class="coate-kpi-help">Declarações de notificados que retificaram ÷ total de declarações de notificados.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

ge1, ge2, ge3 = st.columns(3)

with ge1:
    # Pizza: declarações notificados × não notificados (volume real)
    fig_pizza = go.Figure(go.Pie(
        labels=["Notificados", "Não notificados"],
        values=[decl_notif_sim, decl_notif_nao],
        marker_colors=["#3b82f6", "#94a3b8"],
        hole=0.45,
        textinfo="label+percent",
        hovertemplate="%{label}<br>Declarações: %{value:,}<br>%{percent}<extra></extra>",
    ))
    fig_pizza.update_layout(**_layout_plot(_lb, title="Declarações: Notificados × Não Notificados", showlegend=False))
    st.plotly_chart(fig_pizza, use_container_width=True)

with ge2:
    # Pizza: declarações retificadas × não retificadas (volume real)
    fig_pizza2 = go.Figure(go.Pie(
        labels=["Retificou", "Não retificou"],
        values=[decl_retr_sim, decl_retr_nao],
        marker_colors=["#22c55e", "#ef4444"],
        hole=0.45,
        textinfo="label+percent",
        hovertemplate="%{label}<br>Declarações: %{value:,}<br>%{percent}<extra></extra>",
    ))
    fig_pizza2.update_layout(**_layout_plot(_lb, title="Declarações: Retificou × Não Retificou", showlegend=False))
    st.plotly_chart(fig_pizza2, use_container_width=True)

with ge3:
    # Barras: taxa de retificação por tipo — usando QTD_DECLARACOES (volume real)
    _df_tipo = df_full[df_full["FOI_NOTIFICADO"] == "S"].copy()
    grp_taxa = (
        _df_tipo.groupby("TIPO_PRINCIPAL").apply(
            lambda g: pd.Series({
                "decl_total": g["QTD_DECLARACOES_NO_MES"].sum(),
                "decl_retr":  g.loc[g["HOUVE_RETIFICACAO"] == "S", "QTD_DECLARACOES_NO_MES"].sum(),
            })
        ).reset_index()
    )
    grp_taxa["taxa"] = grp_taxa["decl_retr"] / grp_taxa["decl_total"].replace(0, 1) * 100
    fig_taxa = go.Figure(go.Bar(
        x=grp_taxa["TIPO_PRINCIPAL"].tolist(),
        y=grp_taxa["taxa"].tolist(),
        marker_color=[CORES_TIPO.get(t, "#94a3b8") for t in grp_taxa["TIPO_PRINCIPAL"]],
        text=[_fmt_pct(v) for v in grp_taxa["taxa"]],
        textposition="outside",
        customdata=grp_taxa[["decl_retr","decl_total"]].to_numpy(),
        hovertemplate=(
            "%{x}<br>Taxa: %{text}<br>"
            "Decl. retificadas: %{customdata[0]:,.0f}<br>"
            "Total declarações: %{customdata[1]:,.0f}<extra></extra>"
        ),
    ))
    fig_taxa.update_layout(**_layout_plot(
        _lb,
        title="Taxa de Retificação por Tipo (% declarações)",
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", ticksuffix="%", range=[0, 100]),
    ))
    st.plotly_chart(fig_taxa, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 6 — GANHO DIRETO vs GANHO REFLEXO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="coate-section" style="margin-top:1.5rem;">
        <div class="coate-section-super">🎯 Atribuição do Ganho</div>
        <div class="coate-section-title">Ganho Direto × Ganho Reflexo</div>
        <div class="coate-section-desc">
            Separação do ganho fiscal entre o resultado <strong>direto</strong> da atuação
            do NUSIN, CESIN e COATE (contribuintes notificados que retificaram) e o ganho
            <strong>reflexo</strong> (contribuintes que se autorregularizaram sem notificação,
            por efeito indireto do monitoramento).
        </div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

# Calcular segmentos para o recorte atual
_df_direto  = df[(df["FOI_NOTIFICADO"] == "S") & (df["HOUVE_RETIFICACAO"] == "S")]
_df_reflexo = df[(df["FOI_NOTIFICADO"] != "S") & (df["HOUVE_RETIFICACAO"] == "S")]
_df_notif   = df[df["FOI_NOTIFICADO"] == "S"]
_df_nao_notif = df[df["FOI_NOTIFICADO"] != "S"]

_decl_notif_total = int(_df_notif["QTD_DECLARACOES_NO_MES"].sum())
_decl_direto_retr = int(_df_direto["QTD_DECLARACOES_NO_MES"].sum())
_taxa_direto      = _decl_direto_retr / _decl_notif_total * 100 if _decl_notif_total > 0 else 0
_ganho_rec_dir    = float(_df_direto[_df_direto["DIF_VLR_TOT_REC_ATIVIDADE"] > 0]["DIF_VLR_TOT_REC_ATIVIDADE"].sum())
_ganho_icms_dir   = float(_df_direto[_df_direto["DIF_VLR_APU_ICMS"] > 0]["DIF_VLR_APU_ICMS"].sum())

_decl_nao_notif_total = int(_df_nao_notif["QTD_DECLARACOES_NO_MES"].sum())
_decl_reflexo_retr    = int(_df_reflexo["QTD_DECLARACOES_NO_MES"].sum())
_taxa_reflexo         = _decl_reflexo_retr / _decl_nao_notif_total * 100 if _decl_nao_notif_total > 0 else 0
_ganho_rec_refl       = float(_df_reflexo[_df_reflexo["DIF_VLR_TOT_REC_ATIVIDADE"] > 0]["DIF_VLR_TOT_REC_ATIVIDADE"].sum())
_ganho_icms_refl      = float(_df_reflexo[_df_reflexo["DIF_VLR_APU_ICMS"] > 0]["DIF_VLR_APU_ICMS"].sum())

gd1, gd2 = st.columns(2)

with gd1:
    st.markdown(
        """
        <div class="coate-panel" style="border-left:4px solid #3b82f6;padding:1.2rem;">
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:1rem;">
                <span style="font-size:1.4rem;">🎯</span>
                <div>
                    <div style="font-size:1rem;font-weight:700;color:#f1f5f9;">Ganho Direto</div>
                    <div style="font-size:0.78rem;color:#94a3b8;">Notificados que retificaram · NUSIN → CESIN → COATE</div>
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;">
                <div style="background:rgba(59,130,246,0.08);border-radius:8px;padding:0.8rem;">
                    <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Declarações retificadas</div>
                    <div style="font-size:1.4rem;font-weight:700;color:#3b82f6;">"""
        + _fmt_int(_decl_direto_retr)
        + """</div>
                </div>
                <div style="background:rgba(59,130,246,0.08);border-radius:8px;padding:0.8rem;">
                    <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Taxa de retificação</div>
                    <div style="font-size:1.4rem;font-weight:700;color:#22c55e;">"""
        + _fmt_pct(_taxa_direto, 1)
        + """</div>
                </div>
                <div style="background:rgba(59,130,246,0.08);border-radius:8px;padding:0.8rem;">
                    <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Ganho de Receita</div>
                    <div style="font-size:1.3rem;font-weight:700;color:#f1f5f9;">"""
        + _fmt_moeda(_ganho_rec_dir)
        + """</div>
                </div>
                <div style="background:rgba(59,130,246,0.08);border-radius:8px;padding:0.8rem;">
                    <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Ganho de ICMS</div>
                    <div style="font-size:1.3rem;font-weight:700;color:#f59e0b;">"""
        + _fmt_moeda(_ganho_icms_dir)
        + """</div>
                </div>
            </div>
            <p style="margin:0.8rem 0 0 0;font-size:0.82rem;color:#94a3b8;">
                Resultado direto das notificações emitidas pelo NUSIN, CESIN e COATE.
                Contribuintes que receberam notificação e corrigiram sua declaração.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with gd2:
    st.markdown(
        """
        <div class="coate-panel" style="border-left:4px solid #a855f7;padding:1.2rem;">
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:1rem;">
                <span style="font-size:1.4rem;">🔁</span>
                <div>
                    <div style="font-size:1rem;font-weight:700;color:#f1f5f9;">Ganho Reflexo</div>
                    <div style="font-size:0.78rem;color:#94a3b8;">Não notificados que se autorregularizaram</div>
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;">
                <div style="background:rgba(168,85,247,0.08);border-radius:8px;padding:0.8rem;">
                    <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Declarações retificadas</div>
                    <div style="font-size:1.4rem;font-weight:700;color:#a855f7;">"""
        + _fmt_int(_decl_reflexo_retr)
        + """</div>
                </div>
                <div style="background:rgba(168,85,247,0.08);border-radius:8px;padding:0.8rem;">
                    <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Taxa de retificação espontânea</div>
                    <div style="font-size:1.4rem;font-weight:700;color:#22c55e;">"""
        + _fmt_pct(_taxa_reflexo, 1)
        + """</div>
                </div>
                <div style="background:rgba(168,85,247,0.08);border-radius:8px;padding:0.8rem;">
                    <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Ganho de Receita</div>
                    <div style="font-size:1.3rem;font-weight:700;color:#f1f5f9;">"""
        + _fmt_moeda(_ganho_rec_refl)
        + """</div>
                </div>
                <div style="background:rgba(168,85,247,0.08);border-radius:8px;padding:0.8rem;">
                    <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Ganho de ICMS</div>
                    <div style="font-size:1.3rem;font-weight:700;color:#f59e0b;">"""
        + _fmt_moeda(_ganho_icms_refl)
        + """</div>
                </div>
            </div>
            <p style="margin:0.8rem 0 0 0;font-size:0.82rem;color:#94a3b8;">
                Ganho indireto do monitoramento. Contribuintes que, sem receber notificação,
                consultaram os painéis da COATE e realizaram correções espontaneamente.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Gráfico: evolução mensal ganho direto × reflexo (receita)
_grp_dir_refl = df_full.groupby(["ANO_APURACAO", "MES_APURACAO"]).apply(
    lambda g: pd.Series({
        "ganho_rec_dir":  g.loc[(g["FOI_NOTIFICADO"]=="S") & (g["HOUVE_RETIFICACAO"]=="S") & (g["DIF_VLR_TOT_REC_ATIVIDADE"]>0), "DIF_VLR_TOT_REC_ATIVIDADE"].sum(),
        "ganho_rec_refl": g.loc[(g["FOI_NOTIFICADO"]!="S") & (g["HOUVE_RETIFICACAO"]=="S") & (g["DIF_VLR_TOT_REC_ATIVIDADE"]>0), "DIF_VLR_TOT_REC_ATIVIDADE"].sum(),
        "ganho_icms_dir":  g.loc[(g["FOI_NOTIFICADO"]=="S") & (g["HOUVE_RETIFICACAO"]=="S") & (g["DIF_VLR_APU_ICMS"]>0), "DIF_VLR_APU_ICMS"].sum(),
        "ganho_icms_refl": g.loc[(g["FOI_NOTIFICADO"]!="S") & (g["HOUVE_RETIFICACAO"]=="S") & (g["DIF_VLR_APU_ICMS"]>0), "DIF_VLR_APU_ICMS"].sum(),
    })
).reset_index().sort_values(["ANO_APURACAO", "MES_APURACAO"])
_grp_dir_refl["x_label"] = _grp_dir_refl["ANO_APURACAO"].astype(str) + "/" + _grp_dir_refl["MES_APURACAO"].astype(str).str.zfill(2)

gdr1, gdr2 = st.columns(2)
with gdr1:
    fig_dir_refl_rec = go.Figure()
    fig_dir_refl_rec.add_trace(go.Bar(
        x=_grp_dir_refl["x_label"].tolist(),
        y=_grp_dir_refl["ganho_rec_dir"].tolist(),
        name="Direto",
        marker_color="#3b82f6",
        hovertemplate="Período: %{x}<br>Direto: R$ %{y:,.0f}<extra></extra>",
    ))
    fig_dir_refl_rec.add_trace(go.Bar(
        x=_grp_dir_refl["x_label"].tolist(),
        y=_grp_dir_refl["ganho_rec_refl"].tolist(),
        name="Reflexo",
        marker_color="#a855f7",
        hovertemplate="Período: %{x}<br>Reflexo: R$ %{y:,.0f}<extra></extra>",
    ))
    fig_dir_refl_rec.update_layout(**_layout_plot(
        _lb,
        title="Ganho de Receita: Direto × Reflexo",
        barmode="stack",
        showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0),
        xaxis=dict(tickangle=-45, gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat=",.0f"),
    ))
    st.plotly_chart(fig_dir_refl_rec, use_container_width=True)

with gdr2:
    fig_dir_refl_icms = go.Figure()
    fig_dir_refl_icms.add_trace(go.Bar(
        x=_grp_dir_refl["x_label"].tolist(),
        y=_grp_dir_refl["ganho_icms_dir"].tolist(),
        name="Direto",
        marker_color="#3b82f6",
        hovertemplate="Período: %{x}<br>Direto: R$ %{y:,.0f}<extra></extra>",
    ))
    fig_dir_refl_icms.add_trace(go.Bar(
        x=_grp_dir_refl["x_label"].tolist(),
        y=_grp_dir_refl["ganho_icms_refl"].tolist(),
        name="Reflexo",
        marker_color="#a855f7",
        hovertemplate="Período: %{x}<br>Reflexo: R$ %{y:,.0f}<extra></extra>",
    ))
    fig_dir_refl_icms.update_layout(**_layout_plot(
        _lb,
        title="Ganho de ICMS: Direto × Reflexo",
        barmode="stack",
        showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0),
        xaxis=dict(tickangle=-45, gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat=",.0f"),
    ))
    st.plotly_chart(fig_dir_refl_icms, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 7 — PAINEL MENSAL CONSOLIDADO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="coate-section" style="margin-top:1.5rem;">
        <div class="coate-section-super">📋 Painel Gerencial</div>
        <div class="coate-section-title">Resumo Mensal Consolidado</div>
        <div class="coate-section-desc">
            Cada linha representa um mês de apuração. Os volumes de notificações e
            declarações são as quantidades reais (somas de QTD_NOTIFICACOES e
            QTD_DECLARACOES). Os ganhos direto e reflexo refletem a atribuição do
            resultado por tipo de retificação.
        </div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

import pandas as _pd_mensal

def _agg_mensal(g):
    notif_s  = g[g["FOI_NOTIFICADO"] == "S"]
    dir_g    = g[(g["FOI_NOTIFICADO"] == "S") & (g["HOUVE_RETIFICACAO"] == "S")]
    refl_g   = g[(g["FOI_NOTIFICADO"] != "S") & (g["HOUVE_RETIFICACAO"] == "S")]
    nao_notif = g[g["FOI_NOTIFICADO"] != "S"]

    decl_notif = notif_s["QTD_DECLARACOES_NO_MES"].sum()
    decl_dir   = dir_g["QTD_DECLARACOES_NO_MES"].sum()
    decl_refl  = refl_g["QTD_DECLARACOES_NO_MES"].sum()

    ganho_rec_prim  = g["VLR_TOT_REC_ATIVIDADE_PRIMEIRA"].sum()
    ganho_icms_prim = g["VLR_APU_ICMS_PRIMEIRA"].sum()
    g_rec  = g[g["DIF_VLR_TOT_REC_ATIVIDADE"] > 0]["DIF_VLR_TOT_REC_ATIVIDADE"].sum()
    g_icms = g[g["DIF_VLR_APU_ICMS"] > 0]["DIF_VLR_APU_ICMS"].sum()

    return _pd_mensal.Series({
        "notificacoes":   int(g["QTD_NOTIFICACOES_NO_MES"].sum()),
        "decl_notif":     int(decl_notif),
        "decl_dir_retr":  int(decl_dir),
        "taxa_dir":       round(decl_dir / decl_notif * 100, 1) if decl_notif > 0 else 0,
        "decl_refl_retr": int(decl_refl),
        "taxa_refl":      round(decl_refl / nao_notif["QTD_DECLARACOES_NO_MES"].sum() * 100, 1) if nao_notif["QTD_DECLARACOES_NO_MES"].sum() > 0 else 0,
        "ganho_rec_dir":  float(dir_g[dir_g["DIF_VLR_TOT_REC_ATIVIDADE"]>0]["DIF_VLR_TOT_REC_ATIVIDADE"].sum()),
        "ganho_rec_refl": float(refl_g[refl_g["DIF_VLR_TOT_REC_ATIVIDADE"]>0]["DIF_VLR_TOT_REC_ATIVIDADE"].sum()),
        "ganho_icms_dir":  float(dir_g[dir_g["DIF_VLR_APU_ICMS"]>0]["DIF_VLR_APU_ICMS"].sum()),
        "ganho_icms_refl": float(refl_g[refl_g["DIF_VLR_APU_ICMS"]>0]["DIF_VLR_APU_ICMS"].sum()),
        "ganho_imp_dir":   float(dir_g[dir_g["DIF_VLR_IMPOSTO"]>0]["DIF_VLR_IMPOSTO"].sum()),
        "ganho_imp_refl":  float(refl_g[refl_g["DIF_VLR_IMPOSTO"]>0]["DIF_VLR_IMPOSTO"].sum()),
        "pct_rec":  round(g_rec / ganho_rec_prim * 100, 3) if ganho_rec_prim > 0 else 0,
        "pct_icms": round(g_icms / ganho_icms_prim * 100, 3) if ganho_icms_prim > 0 else 0,
        "indice":   round(g_icms / g_rec * 100, 3) if g_rec > 0 else 0,
    })

df_mensal = (
    df.groupby(["ANO_APURACAO", "MES_APURACAO"])
    .apply(_agg_mensal)
    .reset_index()
    .sort_values(["ANO_APURACAO", "MES_APURACAO"])
)
df_mensal["MES_NOME"] = df_mensal["MES_APURACAO"].map(MESES_ABREV)

st.dataframe(
    df_mensal[[
        "ANO_APURACAO", "MES_NOME",
        "notificacoes", "decl_notif",
        "decl_dir_retr", "taxa_dir",
        "decl_refl_retr", "taxa_refl",
        "ganho_rec_dir", "ganho_rec_refl",
        "ganho_icms_dir", "ganho_icms_refl",
        "ganho_imp_dir", "ganho_imp_refl",
        "pct_rec", "pct_icms", "indice",
    ]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "ANO_APURACAO":    st.column_config.NumberColumn("Ano", format="%d"),
        "MES_NOME":        st.column_config.TextColumn("Mês"),
        "notificacoes":    st.column_config.NumberColumn("Notificações", format="%d"),
        "decl_notif":      st.column_config.NumberColumn("Decl. Notificados", format="%d"),
        "decl_dir_retr":   st.column_config.NumberColumn("Retr. Diretas", format="%d"),
        "taxa_dir":        st.column_config.ProgressColumn("Taxa Direta (%)", format="%.1f%%", min_value=0, max_value=100),
        "decl_refl_retr":  st.column_config.NumberColumn("Retr. Reflexas", format="%d"),
        "taxa_refl":       st.column_config.ProgressColumn("Taxa Reflexa (%)", format="%.1f%%", min_value=0, max_value=100),
        "ganho_rec_dir":   st.column_config.NumberColumn("Receita Direta (R$)", format="R$ %,.0f"),
        "ganho_rec_refl":  st.column_config.NumberColumn("Receita Reflexa (R$)", format="R$ %,.0f"),
        "ganho_icms_dir":  st.column_config.NumberColumn("ICMS Direto (R$)", format="R$ %,.0f"),
        "ganho_icms_refl": st.column_config.NumberColumn("ICMS Reflexo (R$)", format="R$ %,.0f"),
        "pct_rec":         st.column_config.NumberColumn("% Cresc. Receita", format="%.3f%%"),
        "pct_icms":        st.column_config.NumberColumn("% Cresc. ICMS", format="%.3f%%"),
        "ganho_imp_dir":   st.column_config.NumberColumn("Imposto Total Direto (R$)", format="R$ %,.0f"),
        "ganho_imp_refl":  st.column_config.NumberColumn("Imposto Total Reflexo (R$)", format="R$ %,.0f"),
        "indice":          st.column_config.NumberColumn("Índice Conv. ICMS (%)", format="%.3f%%"),
    },
)

# ── Nota metodológica ─────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-panel">
        <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.7rem;">
            <span style="font-size:1.2rem;">📌</span>
            <span style="font-size:1rem;font-weight:700;color:#f1f5f9;">Nota metodológica — Como interpretar os indicadores</span>
        </div>
        <p style="margin:0 0 0.5rem 0;">
            Todos os indicadores de <strong>ganho</strong> são calculados como
            <strong>ÚLTIMA − PRIMEIRA declaração</strong> do mesmo contribuinte no mês.
            Valor positivo = aumento após retificação.
        </p>
        <p style="margin:0 0 0.5rem 0;">
            O <strong>Ganho Direto</strong> é o resultado da atuação do <strong>NUSIN → CESIN → COATE</strong>:
            contribuintes que receberam notificação e corrigiram a declaração.
            O <strong>Ganho Reflexo</strong> é o efeito indireto do monitoramento:
            contribuintes que, sem notificação, se autorregularizaram — possivelmente
            após consultar os painéis da COATE.
        </p>
        <p style="margin:0 0 0.5rem 0;">
            O <strong>Índice de Conversão ICMS/Receita</strong> mede quanto de cada R$ 100
            de receita recuperada se converte em ICMS. Valores abaixo de 1% indicam
            que os contribuintes podem estar reclassificando receita para
            <strong>atividades não tributadas pelo ICMS</strong> — aumentando a receita total
            mas reduzindo a base do imposto estadual.
        </p>
        <p style="margin:0 0 0.5rem 0;">
            O <strong>Imposto Total</strong> representa a cesta completa do Simples Nacional:
            IRPJ, CSLL, COFINS, PIS, CPP, ICMS, IPI e ISS. O índice Imposto/Receita é cerca
            de <strong>7x maior</strong> que o índice ICMS/Receita, revelando que as ações
            de monitoramento da COATE geram um retorno fiscal muito superior ao que o ICMS
            isolado indica — beneficiando União, Estado e Municípios simultaneamente.
        </p>
        <p style="margin:0;">
            Os volumes usam <code>QTD_DECLARACOES_NO_MES</code> e
            <code>QTD_NOTIFICACOES_NO_MES</code> — quantidades reais, não contagem de linhas da base.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="coate-footer">Simples Nacional · Efetividade das Notificações PGDAS · Painel COATE · SEFAZ-CE</div>',
    unsafe_allow_html=True,
)
