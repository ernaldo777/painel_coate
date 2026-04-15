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
_DATA_PATH = _DATA_DIR / "PGDAS.xlsx"

# ── Paletas ────────────────────────────────────────────────────────────────────
CORES_ANO = {
    2021: "#6366f1", 2022: "#3b82f6", 2023: "#06b6d4",
    2024: "#22c55e", 2025: "#f59e0b", 2026: "#ef4444",
}
CORES_TIPO = {
    "Comércio":  "#3b82f6",
    "Indústria": "#22c55e",
    "Serviços":  "#f59e0b",
}
CORES_ICMS = {
    "0":  "#94a3b8",
    "1":  "#6366f1",
    "2":  "#a855f7",
    "3":  "#f97316",
    "8":  "#ef4444",
    "10": "#f59e0b",
    "45": "#06b6d4",
    "67": "#22c55e",
}
MESES_ABREV = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
               7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}

# ── Layout Plotly dark ─────────────────────────────────────────────────────────
_LB = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#cbd5e1", family="sans-serif"),
    margin=dict(t=50, b=30, l=20, r=20),
    hoverlabel=dict(bgcolor="#1e293b", font_color="#f1f5f9", bordercolor="#334155"),
)

def _lb(**extra):
    d = dict(_LB)
    d.update(extra)
    return d

# ── Helpers ────────────────────────────────────────────────────────────────────
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
        return f"R$ {v/1_000_000_000:.2f} Bi"
    if abs(v) >= 1_000_000:
        return f"R$ {v/1_000_000:.2f} Mi"
    if abs(v) >= 1_000:
        return f"R$ {v/1_000:.1f} K"
    return f"R$ {v:,.2f}".replace(",",".")

def _fmt_pct(v, d=1) -> str:
    try:
        return f"{float(v):.{d}f}%"
    except Exception:
        return "0%"

# ── Carga ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def _carregar(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, dtype=str)
    str_cols = ["atividade", "anexo", "tipo", "desc_cod_icms"]
    for c in str_cols:
        if c in df.columns:
            df[c] = (
                df[c].astype(str)
                .str.encode("latin1", errors="ignore")
                .str.decode("utf-8", errors="ignore")
                .str.strip()
            )
    num_cols = [c for c in df.columns if c.startswith("qtd_") or c.startswith("soma_")]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["ano_apuracao"] = df["ano_apuracao"].astype(int)
    df["mes_apuracao"] = df["mes_apuracao"].astype(int)
    df["cod_icms"] = df["cod_icms"].astype(str).str.strip()
    df["mes_label"] = df["mes_apuracao"].map(MESES_ABREV)
    df["ano_mes"] = df["ano_apuracao"].astype(str) + "/" + df["mes_apuracao"].astype(str).str.zfill(2)
    return df

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
    + _sn_img +
    """
        <h1>📋 Declarações PGDAS</h1>
        <p>
            Análise agregada das declarações do PGDAS por período, atividade econômica e
            código de segregação (tributação). Série histórica de 2021 a 2026 com visões
            de receita declarada, ICMS apurado e total de declarantes.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Verificação ────────────────────────────────────────────────────────────────
if not _DATA_PATH.exists():
    st.error("Arquivo não encontrado: " + str(_DATA_PATH))
    st.stop()

df_full = _carregar(str(_DATA_PATH))

# ── Filtros ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.8, 1.8])

with f1:
    anos_disp = sorted(df_full["ano_apuracao"].unique().tolist())
    anos_sel = st.multiselect("Ano", anos_disp, default=anos_disp, placeholder="Todos os anos")

with f2:
    tipos_disp = sorted(df_full["tipo"].dropna().unique().tolist())
    tipo_sel = st.multiselect("Tipo (Anexo)", tipos_disp, placeholder="Todos os tipos")

with f3:
    icms_opts = df_full[["cod_icms","desc_cod_icms"]].drop_duplicates().sort_values("cod_icms")
    icms_map = {row["cod_icms"]: row["cod_icms"] + " — " + row["desc_cod_icms"]
                for _, row in icms_opts.iterrows()}
    icms_sel = st.multiselect(
        "Segregação (cód. ICMS)",
        options=list(icms_map.keys()),
        format_func=lambda x: icms_map.get(x, x),
        placeholder="Todas as segregações",
    )

with f4:
    ativ_disp = sorted(df_full["atividade"].dropna().unique().tolist())
    ativ_sel = st.multiselect("Atividade", ativ_disp, placeholder="Todas as atividades")

# ── Aplicar filtros ────────────────────────────────────────────────────────────
df = df_full.copy()
if anos_sel:
    df = df[df["ano_apuracao"].isin(anos_sel)]
if tipo_sel:
    df = df[df["tipo"].isin(tipo_sel)]
if icms_sel:
    df = df[df["cod_icms"].isin(icms_sel)]
if ativ_sel:
    df = df[df["atividade"].isin(ativ_sel)]

if df.empty:
    st.warning("Nenhum registro para os filtros selecionados.")
    st.stop()

# ── Agregados base ─────────────────────────────────────────────────────────────
# Declarações mensais: MAX por ano/mês (nunca somar qtd_declaracoes_distintas_ano_mes)
dec_mensal = (
    df.groupby(["ano_apuracao", "mes_apuracao"])["qtd_declaracoes_distintas_ano_mes"]
    .max()
    .reset_index()
)
total_declaracoes = dec_mensal["qtd_declaracoes_distintas_ano_mes"].sum()

total_receita  = df["soma_vlr_receita_atividade"].sum()
total_icms     = df["soma_vlr_apu_icms"].sum()
total_imposto  = df["soma_vlr_imposto"].sum()
aliq_efetiva   = total_icms / total_receita * 100 if total_receita else 0

# Full para comparação de % do total
total_receita_full = df_full["soma_vlr_receita_atividade"].sum()
pct_receita = total_receita / total_receita_full * 100 if total_receita_full else 0

# ── KPIs ───────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(
        '<div class="coate-kpi-card accent-primary">'
        '<div class="coate-kpi-label">Declarações (período)</div>'
        '<div class="coate-kpi-value">' + _fmt_int(total_declaracoes) + '</div>'
        '<div class="coate-kpi-help">soma dos máximos mensais</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        '<div class="coate-kpi-card accent-info">'
        '<div class="coate-kpi-label">Receita Declarada</div>'
        '<div class="coate-kpi-value">' + _fmt_moeda(total_receita) + '</div>'
        '<div class="coate-kpi-help">' + _fmt_pct(pct_receita) + ' do total histórico</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        '<div class="coate-kpi-card accent-warning">'
        '<div class="coate-kpi-label">ICMS Apurado</div>'
        '<div class="coate-kpi-value">' + _fmt_moeda(total_icms) + '</div>'
        '<div class="coate-kpi-help">alíquota efetiva: ' + _fmt_pct(aliq_efetiva, 2) + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        '<div class="coate-kpi-card accent-danger">'
        '<div class="coate-kpi-label">Total de Tributos</div>'
        '<div class="coate-kpi-value">' + _fmt_moeda(total_imposto) + '</div>'
        '<div class="coate-kpi-help">todos os tributos do Simples</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with k5:
    meses_com_dados = len(dec_mensal)
    media_dec = int(dec_mensal["qtd_declaracoes_distintas_ano_mes"].mean()) if meses_com_dados else 0
    st.markdown(
        '<div class="coate-kpi-card">'
        '<div class="coate-kpi-label">Média de Declarantes/mês</div>'
        '<div class="coate-kpi-value">' + _fmt_int(media_dec) + '</div>'
        '<div class="coate-kpi-help">' + str(meses_com_dados) + ' meses no filtro</div>'
        '</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 1 — Série temporal de declarações e receita
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📅 Série Temporal</div>
        <div class="coate-section-title">Evolução Mensal de Declarações e Receita</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

# Receita mensal (pode somar — é agregada por atividade/icms, soma faz sentido)
rec_mensal = (
    df.groupby(["ano_apuracao", "mes_apuracao"])
    .agg(receita=("soma_vlr_receita_atividade","sum"),
         icms=("soma_vlr_apu_icms","sum"))
    .reset_index()
    .sort_values(["ano_apuracao","mes_apuracao"])
)
rec_mensal = rec_mensal.merge(dec_mensal, on=["ano_apuracao","mes_apuracao"], how="left")
rec_mensal["mes_label"] = rec_mensal["mes_apuracao"].map(MESES_ABREV)
rec_mensal["label"] = rec_mensal["mes_label"] + "/" + rec_mensal["ano_apuracao"].astype(str).str[-2:]

_xaxis_mes = dict(
    tickvals=list(range(1,13)),
    ticktext=list(MESES_ABREV.values()),
    gridcolor="rgba(148,163,184,0.08)",
)
_leg_bottom = dict(orientation="h", y=-0.22, x=0)

g1a, g1b, g1c_mes = st.columns(3)

with g1a:
    fig_dec = go.Figure()
    for ano in sorted(rec_mensal["ano_apuracao"].unique()):
        sub = rec_mensal[rec_mensal["ano_apuracao"] == ano]
        fig_dec.add_trace(go.Scatter(
            x=sub["mes_apuracao"],
            y=sub["qtd_declaracoes_distintas_ano_mes"],
            mode="lines+markers",
            name=str(ano),
            line=dict(color=CORES_ANO.get(ano, "#94a3b8"), width=2),
            marker=dict(size=5),
            hovertemplate="<b>" + str(ano) + " — %{x}º mês</b><br>%{y:,} declarantes<extra></extra>",
        ))
    fig_dec.update_layout(
        **_lb(
            title="Declarantes por Mês — série por ano",
            height=380,
            xaxis=_xaxis_mes,
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
            legend=_leg_bottom,
        )
    )
    st.plotly_chart(fig_dec, use_container_width=True)

with g1b:
    fig_rec = go.Figure()
    for ano in sorted(rec_mensal["ano_apuracao"].unique()):
        sub = rec_mensal[rec_mensal["ano_apuracao"] == ano]
        fig_rec.add_trace(go.Scatter(
            x=sub["mes_apuracao"],
            y=sub["receita"],
            mode="lines+markers",
            name=str(ano),
            line=dict(color=CORES_ANO.get(ano, "#94a3b8"), width=2),
            marker=dict(size=5),
            hovertemplate="<b>" + str(ano) + " — %{x}º mês</b><br>R$ %{y:,.0f}<extra></extra>",
        ))
    fig_rec.update_layout(
        **_lb(
            title="Receita Declarada por Mês — série por ano",
            height=380,
            xaxis=_xaxis_mes,
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickprefix="R$ ", tickformat=",.0f"),
            legend=_leg_bottom,
        )
    )
    st.plotly_chart(fig_rec, use_container_width=True)

with g1c_mes:
    fig_icms_mes = go.Figure()
    for ano in sorted(rec_mensal["ano_apuracao"].unique()):
        sub = rec_mensal[rec_mensal["ano_apuracao"] == ano]
        fig_icms_mes.add_trace(go.Scatter(
            x=sub["mes_apuracao"],
            y=sub["icms"],
            mode="lines+markers",
            name=str(ano),
            line=dict(color=CORES_ANO.get(ano, "#94a3b8"), width=2),
            marker=dict(size=5),
            hovertemplate="<b>" + str(ano) + " — %{x}º mês</b><br>R$ %{y:,.0f}<extra></extra>",
        ))
    fig_icms_mes.update_layout(
        **_lb(
            title="ICMS Apurado por Mês — série por ano",
            height=380,
            xaxis=_xaxis_mes,
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickprefix="R$ ", tickformat=",.0f"),
            legend=_leg_bottom,
        )
    )
    st.plotly_chart(fig_icms_mes, use_container_width=True)

# Barras agrupadas: receita e ICMS por ano (totais)
rec_ano = (
    df.groupby("ano_apuracao")
    .agg(receita=("soma_vlr_receita_atividade","sum"),
         icms=("soma_vlr_apu_icms","sum"),
         imposto=("soma_vlr_imposto","sum"))
    .reset_index()
)
dec_ano = (
    dec_mensal.groupby("ano_apuracao")["qtd_declaracoes_distintas_ano_mes"]
    .sum()
    .reset_index()
    .rename(columns={"qtd_declaracoes_distintas_ano_mes": "declaracoes"})
)
rec_ano = rec_ano.merge(dec_ano, on="ano_apuracao", how="left")

g1c, g1d = st.columns(2)

with g1c:
    fig_ano_rec = go.Figure()
    fig_ano_rec.add_trace(go.Bar(
        x=rec_ano["ano_apuracao"].astype(str),
        y=rec_ano["receita"],
        name="Receita",
        marker_color=[CORES_ANO.get(a, "#94a3b8") for a in rec_ano["ano_apuracao"]],
        hovertemplate="<b>%{x}</b><br>Receita: R$ %{y:,.0f}<extra></extra>",
    ))
    fig_ano_rec.update_layout(
        **_lb(
            title="Receita Declarada por Ano",
            height=320,
            showlegend=False,
            xaxis=dict(type="category", gridcolor="rgba(148,163,184,0.08)"),
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickprefix="R$ ", tickformat=",.0f"),
        )
    )
    st.plotly_chart(fig_ano_rec, use_container_width=True)

with g1d:
    fig_ano_icms = go.Figure()
    fig_ano_icms.add_trace(go.Bar(
        x=rec_ano["ano_apuracao"].astype(str),
        y=rec_ano["icms"],
        name="ICMS Apurado",
        marker_color=[CORES_ANO.get(a, "#94a3b8") for a in rec_ano["ano_apuracao"]],
        hovertemplate="<b>%{x}</b><br>ICMS Apurado: R$ %{y:,.0f}<extra></extra>",
    ))
    fig_ano_icms.update_layout(
        **_lb(
            title="ICMS Apurado por Ano",
            height=320,
            showlegend=False,
            xaxis=dict(type="category", gridcolor="rgba(148,163,184,0.08)"),
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickprefix="R$ ", tickformat=",.0f"),
        )
    )
    st.plotly_chart(fig_ano_icms, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 2 — Por Atividade
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">🏭 Atividade Econômica</div>
        <div class="coate-section-title">Receita e ICMS por Atividade e Anexo</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

g2a, g2b = st.columns(2)

with g2a:
    df_ativ = (
        df.groupby("atividade")
        .agg(receita=("soma_vlr_receita_atividade","sum"),
             icms=("soma_vlr_apu_icms","sum"),
             decl=("qtd_declaracoes_distintas_grupo","sum"))
        .reset_index()
        .sort_values("receita", ascending=True)
    )
    df_ativ["atividade_curta"] = df_ativ["atividade"].str[:55]

    fig_ativ = go.Figure()
    fig_ativ.add_trace(go.Bar(
        x=df_ativ["receita"],
        y=df_ativ["atividade_curta"],
        orientation="h",
        name="Receita",
        marker_color="#3b82f6",
        hovertemplate="<b>%{y}</b><br>Receita: R$ %{x:,.0f}<extra></extra>",
    ))
    fig_ativ.add_trace(go.Bar(
        x=df_ativ["icms"],
        y=df_ativ["atividade_curta"],
        orientation="h",
        name="ICMS Apurado",
        marker_color="#f59e0b",
        hovertemplate="<b>%{y}</b><br>ICMS: R$ %{x:,.0f}<extra></extra>",
    ))
    fig_ativ.update_layout(
        **_lb(
            title="Receita × ICMS por Atividade",
            barmode="group",
            height=520,
            margin=dict(t=50, b=80, l=370, r=20),
            xaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickprefix="R$ ", tickformat="~s"),
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=9)),
            legend=dict(orientation="h", y=-0.14, x=0, font=dict(size=11)),
        )
    )
    st.plotly_chart(fig_ativ, use_container_width=True)

with g2b:
    # Donut por Anexo (I / II / III)
    df_anexo = (
        df.groupby("anexo")["soma_vlr_receita_atividade"]
        .sum()
        .reset_index()
        .sort_values("soma_vlr_receita_atividade", ascending=False)
    )
    CORES_ANEXO = {"I": "#3b82f6", "II": "#22c55e", "III": "#f59e0b"}
    DESC_ANEXO  = {"I": "Anexo I — Comércio", "II": "Anexo II — Indústria", "III": "Anexo III — Serviços"}
    df_anexo["label"] = df_anexo["anexo"].map(DESC_ANEXO).fillna("Anexo " + df_anexo["anexo"])
    fig_anexo = go.Figure(go.Pie(
        labels=df_anexo["label"].tolist(),
        values=df_anexo["soma_vlr_receita_atividade"].tolist(),
        hole=0.52,
        marker_colors=[CORES_ANEXO.get(a, "#94a3b8") for a in df_anexo["anexo"]],
        textinfo="label+percent",
        textfont=dict(size=11),
        hovertemplate="%{label}<br>R$ %{value:,.0f}<br>%{percent}<extra></extra>",
    ))
    fig_anexo.update_layout(
        **_lb(
            title="Participação por Anexo (Receita)",
            showlegend=False,
            height=280,
        )
    )
    st.plotly_chart(fig_anexo, use_container_width=True)

    # Barras: receita por Anexo × Ano
    df_anexo_ano = (
        df.groupby(["ano_apuracao","anexo"])["soma_vlr_receita_atividade"]
        .sum()
        .reset_index()
    )
    fig_anexo_ano = go.Figure()
    for anexo in ["I", "II", "III"]:
        sub = df_anexo_ano[df_anexo_ano["anexo"] == anexo]
        label_anexo = DESC_ANEXO.get(anexo, "Anexo " + anexo)
        fig_anexo_ano.add_trace(go.Bar(
            x=sub["ano_apuracao"].astype(str),
            y=sub["soma_vlr_receita_atividade"],
            name=label_anexo,
            marker_color=CORES_ANEXO.get(anexo, "#94a3b8"),
            hovertemplate="<b>" + label_anexo + " — %{x}</b><br>R$ %{y:,.0f}<extra></extra>",
        ))
    fig_anexo_ano.update_layout(
        **_lb(
            title="Receita por Anexo e Ano",
            barmode="group",
            height=240,
            margin=dict(t=50, b=60, l=20, r=20),
            xaxis=dict(type="category", gridcolor="rgba(148,163,184,0.08)"),
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickprefix="R$ ", tickformat=",.0f"),
            legend=dict(orientation="h", y=-0.28, x=0, font=dict(size=10)),
        )
    )
    st.plotly_chart(fig_anexo_ano, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 3 — Por Segregação (cod_icms)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">🔀 Segregação Tributária</div>
        <div class="coate-section-title">Distribuição por Código de ICMS</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

df_icms = (
    df.groupby(["cod_icms","desc_cod_icms"])
    .agg(receita=("soma_vlr_receita_atividade","sum"),
         icms=("soma_vlr_apu_icms","sum"),
         decl=("qtd_declaracoes_distintas_grupo","sum"))
    .reset_index()
    .sort_values("receita", ascending=False)
)
df_icms["icms_label"] = df_icms["cod_icms"] + " — " + df_icms["desc_cod_icms"]
df_icms["aliq"] = df_icms["icms"] / df_icms["receita"] * 100

# Barras full-width com valores formatados no hover — sem texto externo que cobre
df_icms_bar = df_icms.sort_values("receita", ascending=True)
fig_icms_bar = go.Figure()
fig_icms_bar.add_trace(go.Bar(
    x=df_icms_bar["receita"],
    y=df_icms_bar["icms_label"],
    orientation="h",
    marker_color=[CORES_ICMS.get(c, "#94a3b8") for c in df_icms_bar["cod_icms"]],
    customdata=df_icms_bar["receita"].apply(_fmt_moeda).tolist(),
    hovertemplate="<b>%{y}</b><br>Receita: %{customdata}<extra></extra>",
    text=df_icms_bar["receita"].apply(_fmt_moeda),
    textposition="inside",
    insidetextanchor="end",
    textfont=dict(size=11, color="#f1f5f9"),
))
fig_icms_bar.update_layout(
    **_lb(
        title="Receita Declarada por Segregação (cód. ICMS)",
        height=420,
        showlegend=False,
        margin=dict(t=50, b=20, l=320, r=20),
        xaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickformat="~s"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickfont=dict(size=10)),
    )
)
st.plotly_chart(fig_icms_bar, use_container_width=True)

# Pizza separada abaixo, full-width, só as 2 maiores com label, restante no hover
g3a, g3b = st.columns([1, 1])
with g3a:
    # Donut: mostrar só label+percent nas fatias grandes, evitar sobreposição
    fig_icms_pizza = go.Figure(go.Pie(
        labels=df_icms["icms_label"].tolist(),
        values=df_icms["receita"].tolist(),
        hole=0.50,
        marker_colors=[CORES_ICMS.get(c, "#94a3b8") for c in df_icms["cod_icms"]],
        textinfo="percent",
        textposition="inside",
        insidetextorientation="radial",
        textfont=dict(size=12),
        hovertemplate="<b>%{label}</b><br>R$ %{value:,.0f}<br>%{percent}<extra></extra>",
        pull=[0.04 if i < 2 else 0 for i in range(len(df_icms))],
    ))
    fig_icms_pizza.update_layout(
        **_lb(
            title="Participação % por Segregação",
            showlegend=False,
            height=380,
            margin=dict(t=50, b=20, l=20, r=20),
        )
    )
    st.plotly_chart(fig_icms_pizza, use_container_width=True)

with g3b:
    # Tabela-legenda limpa com cor + label + valor
    df_icms_leg = df_icms.sort_values("receita", ascending=False)[["cod_icms","icms_label","receita"]].copy()
    df_icms_leg["Receita"] = df_icms_leg["receita"].apply(_fmt_moeda)
    df_icms_leg["pct"] = (df_icms_leg["receita"] / df_icms_leg["receita"].sum() * 100).apply(lambda v: f"{v:.2f}%")
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.dataframe(
        df_icms_leg[["icms_label","Receita","pct"]].rename(columns={
            "icms_label": "Segregação",
            "pct": "% do total",
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Segregação": st.column_config.TextColumn("Segregação", width="large"),
            "Receita": st.column_config.TextColumn("Receita"),
            "% do total": st.column_config.TextColumn("% do total"),
        },
    )

# Evolução por segregação — barras agrupadas por ano (muito mais legível)
df_icms_ano = (
    df.groupby(["ano_apuracao","cod_icms","desc_cod_icms"])["soma_vlr_receita_atividade"]
    .sum()
    .reset_index()
)
df_icms_ano["icms_label"] = df_icms_ano["cod_icms"] + " — " + df_icms_ano["desc_cod_icms"]

fig_icms_barras = go.Figure()
for _, row in df_icms[["cod_icms","icms_label"]].iterrows():
    sub = df_icms_ano[df_icms_ano["cod_icms"] == row["cod_icms"]]
    if sub.empty:
        continue
    fig_icms_barras.add_trace(go.Bar(
        x=sub["ano_apuracao"].astype(str),
        y=sub["soma_vlr_receita_atividade"],
        name=row["icms_label"],
        marker_color=CORES_ICMS.get(row["cod_icms"], "#94a3b8"),
        hovertemplate="<b>" + row["icms_label"] + "</b><br>%{x}<br>R$ %{y:,.0f}<extra></extra>",
    ))
fig_icms_barras.update_layout(
    **_lb(
        title="Receita por Segregação — comparativo anual",
        barmode="group",
        height=400,
        xaxis=dict(type="category", gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)", tickprefix="R$ ", tickformat=",.0f"),
        legend=dict(font=dict(size=9), orientation="h", y=-0.28, x=0),
        margin=dict(t=50, b=100, l=20, r=20),
    )
)
st.plotly_chart(fig_icms_barras, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 4 — Tabela agregada
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-section">
        <div class="coate-section-super">📋 Detalhe</div>
        <div class="coate-section-title">Tabela Agregada por Período, Atividade e Segregação</div>
    </div>
    <hr class="coate-section-divider"/>
    """,
    unsafe_allow_html=True,
)

# Escolha de granularidade
gran = st.radio(
    "Granularidade da tabela",
    ["Ano × Mês", "Ano × Mês × Atividade", "Ano × Mês × Segregação", "Ano × Mês × Atividade × Segregação"],
    horizontal=True,
)

if gran == "Ano × Mês":
    df_tab = (
        df.groupby(["ano_apuracao","mes_apuracao"])
        .agg(
            decl_grupo=("qtd_declaracoes_distintas_grupo","sum"),
            receita=("soma_vlr_receita_atividade","sum"),
            icms=("soma_vlr_apu_icms","sum"),
            imposto=("soma_vlr_imposto","sum"),
        )
        .reset_index()
    )
    # Adiciona declarações corretas por mês via MAX
    df_tab = df_tab.merge(dec_mensal, on=["ano_apuracao","mes_apuracao"], how="left")
    df_tab = df_tab.rename(columns={
        "ano_apuracao":"Ano","mes_apuracao":"Mês",
        "qtd_declaracoes_distintas_ano_mes":"Declarantes/mês",
        "decl_grupo":"Decl. Grupo","receita":"Receita (R$)",
        "icms":"ICMS Apurado (R$)","imposto":"Total Tributos (R$)",
    })
    col_cfg = {
        "Ano": st.column_config.NumberColumn("Ano", format="%d"),
        "Mês": st.column_config.NumberColumn("Mês", format="%d"),
        "Declarantes/mês": st.column_config.NumberColumn("Declarantes/mês", format="%d"),
        "Decl. Grupo": st.column_config.NumberColumn("Decl. Grupo", format="%d"),
        "Receita (R$)": st.column_config.NumberColumn("Receita (R$)", format="R$ %,.2f"),
        "ICMS Apurado (R$)": st.column_config.NumberColumn("ICMS Apurado (R$)", format="R$ %,.2f"),
        "Total Tributos (R$)": st.column_config.NumberColumn("Total Tributos (R$)", format="R$ %,.2f"),
    }

elif gran == "Ano × Mês × Atividade":
    df_tab = (
        df.groupby(["ano_apuracao","mes_apuracao","tipo","atividade"])
        .agg(
            decl=("qtd_declaracoes_distintas_grupo","sum"),
            receita=("soma_vlr_receita_atividade","sum"),
            icms=("soma_vlr_apu_icms","sum"),
        )
        .reset_index()
        .rename(columns={
            "ano_apuracao":"Ano","mes_apuracao":"Mês","tipo":"Tipo","atividade":"Atividade",
            "decl":"Declarações","receita":"Receita (R$)","icms":"ICMS Apurado (R$)",
        })
    )
    col_cfg = {
        "Ano": st.column_config.NumberColumn("Ano", format="%d"),
        "Mês": st.column_config.NumberColumn("Mês", format="%d"),
        "Tipo": st.column_config.TextColumn("Tipo"),
        "Atividade": st.column_config.TextColumn("Atividade", width="large"),
        "Declarações": st.column_config.NumberColumn("Declarações", format="%d"),
        "Receita (R$)": st.column_config.NumberColumn("Receita (R$)", format="R$ %,.2f"),
        "ICMS Apurado (R$)": st.column_config.NumberColumn("ICMS Apurado (R$)", format="R$ %,.2f"),
    }

elif gran == "Ano × Mês × Segregação":
    df_tab = (
        df.groupby(["ano_apuracao","mes_apuracao","cod_icms","desc_cod_icms"])
        .agg(
            decl=("qtd_declaracoes_distintas_grupo","sum"),
            receita=("soma_vlr_receita_atividade","sum"),
            icms=("soma_vlr_apu_icms","sum"),
        )
        .reset_index()
        .rename(columns={
            "ano_apuracao":"Ano","mes_apuracao":"Mês",
            "cod_icms":"Cód. ICMS","desc_cod_icms":"Segregação",
            "decl":"Declarações","receita":"Receita (R$)","icms":"ICMS Apurado (R$)",
        })
    )
    col_cfg = {
        "Ano": st.column_config.NumberColumn("Ano", format="%d"),
        "Mês": st.column_config.NumberColumn("Mês", format="%d"),
        "Cód. ICMS": st.column_config.TextColumn("Cód. ICMS"),
        "Segregação": st.column_config.TextColumn("Segregação", width="large"),
        "Declarações": st.column_config.NumberColumn("Declarações", format="%d"),
        "Receita (R$)": st.column_config.NumberColumn("Receita (R$)", format="R$ %,.2f"),
        "ICMS Apurado (R$)": st.column_config.NumberColumn("ICMS Apurado (R$)", format="R$ %,.2f"),
    }

else:  # Ano × Mês × Atividade × Segregação — granularidade máxima
    df_tab = (
        df.groupby(["ano_apuracao","mes_apuracao","tipo","atividade","cod_icms","desc_cod_icms"])
        .agg(
            decl=("qtd_declaracoes_distintas_grupo","sum"),
            receita=("soma_vlr_receita_atividade","sum"),
            icms=("soma_vlr_apu_icms","sum"),
        )
        .reset_index()
        .rename(columns={
            "ano_apuracao":"Ano","mes_apuracao":"Mês","tipo":"Tipo","atividade":"Atividade",
            "cod_icms":"Cód. ICMS","desc_cod_icms":"Segregação",
            "decl":"Declarações","receita":"Receita (R$)","icms":"ICMS Apurado (R$)",
        })
    )
    col_cfg = {
        "Ano": st.column_config.NumberColumn("Ano", format="%d"),
        "Mês": st.column_config.NumberColumn("Mês", format="%d"),
        "Tipo": st.column_config.TextColumn("Tipo"),
        "Atividade": st.column_config.TextColumn("Atividade", width="large"),
        "Cód. ICMS": st.column_config.TextColumn("Cód. ICMS"),
        "Segregação": st.column_config.TextColumn("Segregação", width="large"),
        "Declarações": st.column_config.NumberColumn("Declarações", format="%d"),
        "Receita (R$)": st.column_config.NumberColumn("Receita (R$)", format="R$ %,.2f"),
        "ICMS Apurado (R$)": st.column_config.NumberColumn("ICMS Apurado (R$)", format="R$ %,.2f"),
    }

LINHAS_POR_PAG = 20
total_linhas = len(df_tab)
total_pags = max(1, (total_linhas + LINHAS_POR_PAG - 1) // LINHAS_POR_PAG)
c_info, c_pag = st.columns([3,1])
with c_info:
    st.caption(f"{_fmt_int(total_linhas)} registros · {total_pags} página(s)")
with c_pag:
    pag_atual = st.number_input("Página", min_value=1, max_value=total_pags, value=1, step=1, key="pag_tab")

inicio = (pag_atual - 1) * LINHAS_POR_PAG
fim = inicio + LINHAS_POR_PAG

st.dataframe(
    df_tab.iloc[inicio:fim],
    use_container_width=True,
    hide_index=True,
    column_config=col_cfg,
)

# ── Nota metodológica ──────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="coate-panel">
        <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.7rem;">
            <span style="font-size:1.2rem;">📌</span>
            <span style="font-size:1rem;font-weight:700;color:#f1f5f9;">Nota metodológica — Declarações PGDAS</span>
        </div>
        <p style="margin:0 0 0.5rem 0;">
            A base é detalhada por <strong>ano/mês × atividade × código ICMS</strong>. Dois campos de contagem
            coexistem com semânticas distintas:
        </p>
        <p style="margin:0 0 0.4rem 0;">
            <strong>qtd_declaracoes_distintas_grupo:</strong> declarações distintas na granularidade da linha
            (ano + mês + atividade + cód. ICMS). Pode ser somado para totais dentro da mesma granularidade.
        </p>
        <p style="margin:0 0 0.6rem 0;">
            <strong>qtd_declaracoes_distintas_ano_mes:</strong> declarações distintas considerando apenas
            ano + mês — o número mais fiel de declarantes no período. Este campo se repete em várias linhas
            do mesmo mês, portanto <strong>nunca deve ser somado diretamente</strong>. Os cards e gráficos
            desta página utilizam <strong>MAX por ano/mês</strong> para garantir a contagem correta.
        </p>
        <p style="margin:0;">
            Os dados de 2026 estão parciais (apenas Jan–Abr). Anos incompletos podem apresentar totais
            inferiores aos anos completos anteriores.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="coate-footer">Simples Nacional · Declarações PGDAS · Painel COATE · SEFAZ-CE</div>',
    unsafe_allow_html=True,
)
