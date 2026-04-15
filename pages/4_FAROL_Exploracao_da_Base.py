import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from projetos_especiais.farol.farol_config import APP_TITLE, PAGE_TITLES
from coate_styles import aplicar_estilos, loading
from coate_auth import exigir_acesso

from projetos_especiais.farol.farol_core import load_data, filtrar_base
from projetos_especiais.farol.farol_rules_catalog import REGRAS_ATIVAS, REGRAS_NOMES, REGRAS_DESC
from projetos_especiais.farol.farol_metadata import banner_atualizacao


# =========================
# CONFIGURAÇÕES
# =========================
REGRAS_OFICIAIS = list(REGRAS_ATIVAS)
DESCRICOES_REGRAS = {codigo: REGRAS_DESC.get(codigo, "") for codigo in REGRAS_OFICIAIS}
NOMES_REGRAS = {codigo: REGRAS_NOMES.get(codigo, codigo) for codigo in REGRAS_OFICIAIS}

CORES_RISCO = {
    "Baixo": "#22c55e",
    "Médio": "#f59e0b",
    "Medio": "#f59e0b",
    "Moderado": "#14b8a6",
    "Alto": "#f97316",
    "Muito Alto": "#dc2626",
    "Crítico": "#ef4444",
    "Critico": "#ef4444",
}

PALETA_SITUACAO = ["#2563eb", "#0ea5e9", "#06b6d4", "#0891b2", "#3b82f6", "#0284c7", "#38bdf8", "#60a5fa"]
PALETA_CNAE = ["#2563eb", "#7c3aed", "#9333ea", "#c026d3", "#db2777", "#ec4899", "#8b5cf6", "#6366f1"]
PALETA_ORGAO = ["#2563eb", "#0ea5e9", "#0284c7", "#38bdf8", "#1d4ed8", "#0369a1", "#60a5fa", "#22d3ee"]
PALETA_SEGMENTO = ["#16a34a", "#22c55e", "#10b981", "#14b8a6", "#84cc16", "#65a30d", "#34d399", "#4ade80"]
PALETA_REGRAS = ["#f97316", "#f59e0b", "#eab308", "#ef4444", "#f43f5e", "#fb7185", "#dc2626", "#ea580c"]


# =========================
# ESTILO
# =========================


# =========================
# AUXILIARES
# =========================
def formatar_inteiro(valor):
    try:
        return f"{int(valor):,}".replace(",", ".")
    except Exception:
        return "0"



def formatar_decimal(valor, casas=2):
    try:
        return f"{float(valor):.{casas}f}".replace(".", ",")
    except Exception:
        return "0,00"

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



def _percentual(parte, total):
    try:
        parte = float(parte)
        total = float(total)
        return (parte / total) if total else 0.0
    except Exception:
        return 0.0




def renderizar_tabela_html(df: pd.DataFrame):
    if df.empty:
        st.info("Sem dados para exibir.")
        return
    html = df.to_html(index=False, classes="farol-table", border=0, escape=False)
    st.markdown(f'<div class="farol-table-wrap">{html}</div>', unsafe_allow_html=True)



def truncar_texto(texto, limite=95):
    texto = "" if pd.isna(texto) else str(texto)
    if len(texto) <= limite:
        return texto
    return texto[:limite].rstrip() + "..."



def badge_risco(valor: str) -> str:
    v = str(valor).strip().lower()
    mapa_classes = {
        "baixo": ("#86efac", "Baixo"),
        "médio": ("#facc15", "Médio"),
        "medio": ("#facc15", "Médio"),
        "moderado": ("#14b8a6", "Moderado"),
        "alto": ("#fb923c", "Alto"),
        "muito alto": ("#f87171", "Muito Alto"),
        "crítico": ("#dc2626", "Crítico"),
        "critico": ("#dc2626", "Crítico"),
    }
    cor, texto = mapa_classes.get(v, (None, str(valor)))
    if cor is None:
        return str(valor)
    return f'<span style="display:inline-flex;align-items:center;gap:.45rem;padding:.22rem .54rem;border-radius:999px;font-weight:600;white-space:nowrap;border:1px solid rgba(148,163,184,.18);background:rgba(15,23,42,.72);"><span style="width:10px;height:10px;border-radius:50%;display:inline-block;background:{cor};box-shadow:0 0 8px {cor};"></span>{texto}</span>'



def badge_prioridade_por_rank(rank):
    try:
        rank = int(rank)
    except Exception:
        return '<span style="display:inline-flex;align-items:center;padding:.22rem .54rem;border-radius:999px;font-weight:700;white-space:nowrap;border:1px solid rgba(148,163,184,.18);background:rgba(30,41,59,.72);color:#cbd5e1;">Monitoramento</span>'
    if rank <= 10:
        return '<span style="display:inline-flex;align-items:center;padding:.22rem .54rem;border-radius:999px;font-weight:700;white-space:nowrap;border:1px solid rgba(148,163,184,.18);background:rgba(127,29,29,.52);color:#fecaca;">Prioridade Máxima</span>'
    if rank <= 50:
        return '<span style="display:inline-flex;align-items:center;padding:.22rem .54rem;border-radius:999px;font-weight:700;white-space:nowrap;border:1px solid rgba(148,163,184,.18);background:rgba(120,53,15,.42);color:#fed7aa;">Prioridade Alta</span>'
    return '<span style="display:inline-flex;align-items:center;padding:.22rem .54rem;border-radius:999px;font-weight:700;white-space:nowrap;border:1px solid rgba(148,163,184,.18);background:rgba(30,41,59,.72);color:#cbd5e1;">Monitoramento</span>'



def badge_dias_para_saida(valor):
    try:
        dias = int(pd.to_numeric(valor, errors="coerce"))
    except Exception:
        return '<span style="display:inline-flex;align-items:center;padding:.22rem .54rem;border-radius:999px;font-weight:700;white-space:nowrap;border:1px solid rgba(148,163,184,.18);background:rgba(30,41,59,.72);color:#cbd5e1;">N/D</span>'
    if dias <= 30:
        bg, fg = 'rgba(127,29,29,.52)', '#fecaca'
    elif dias <= 90:
        bg, fg = 'rgba(120,53,15,.42)', '#fed7aa'
    else:
        bg, fg = 'rgba(6,78,59,.42)', '#d1fae5'
    sufixo = 'dia' if dias == 1 else 'dias'
    return f'<span style="display:inline-flex;align-items:center;padding:.22rem .54rem;border-radius:999px;font-weight:700;white-space:nowrap;border:1px solid rgba(148,163,184,.18);background:{bg};color:{fg};">{dias} {sufixo}</span>'



def abrir_consulta_cnpj(cnpj: str):
    cnpj = ''.join(ch for ch in str(cnpj) if ch.isdigit())
    if not cnpj:
        st.warning('CNPJ inválido para navegação à consulta.')
        return
    st.session_state['cnpj_consulta_preselecionado'] = cnpj
    st.session_state['cnpj_consulta'] = cnpj
    st.session_state['farol_cnpj_inicial'] = cnpj
    st.session_state['consulta_cnpj_input'] = cnpj
    st.session_state['consulta_modo_busca'] = 'Digitar CNPJ'
    try:
        st.query_params['cnpj'] = cnpj
    except Exception:
        pass
    try:
        st.switch_page('pages/3_FAROL_Consulta_de_Contribuinte.py')
    except Exception:
        st.success(f'CNPJ {cnpj} preparado. Abra a página Consulta do Contribuinte para continuar.')



def renderizar_grade_operacional_exploracao(df: pd.DataFrame):
    if df is None or df.empty:
        st.info('Sem dados para exibir.')
        return
    cabecalhos = [
        'Ação',
        'Ranking',
        'Faixa',
        'CNPJ',
        'Razão Social',
        'Regime',
        'Segmento',
        'Situação Atual',
        'Dias para\nSaída',
        'Nível de Risco',
        'Índice\nFAROL',
    ]
    larguras = [0.90, 0.70, 1.80, 1.85, 2.60, 1.30, 1.50, 1.45, 1.15, 1.20, 1.00]
    st.markdown('<div class="farol-table-wrap">', unsafe_allow_html=True)
    cols = st.columns(larguras)
    for c, h in zip(cols, cabecalhos):
        c.markdown(f"**{h.replace(chr(10), '<br>')}**", unsafe_allow_html=True)
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        st.markdown("<hr style='border-color: rgba(148,163,184,0.10); margin: 0.35rem 0 0.55rem 0;'>", unsafe_allow_html=True)
        cols = st.columns(larguras)
        cnpj = str(row.get('COD_CNPJ', '')).replace('.0', '').strip()
        if cols[0].button('Consultar', key=f'explorar_consultar_{idx}_{cnpj}', use_container_width=True):
            abrir_consulta_cnpj(cnpj)
        cols[1].markdown(f"**{idx}**")
        cols[2].markdown(badge_prioridade_por_rank(idx), unsafe_allow_html=True)
        cols[3].markdown(f'<span style="color:#e2e8f0;font-weight:600;letter-spacing:.02em;font-family:Inter,Segoe UI,sans-serif;">{cnpj}</span>', unsafe_allow_html=True)
        cols[4].markdown(str(row.get('DSC_RAZAO_SOCIAL', '')))
        regime = row.get('DSC_REGIME_REC_CONTRIBUINTE', '')
        cols[5].markdown(truncar_texto('' if pd.isna(regime) else str(regime), 22))
        cols[6].markdown(str(row.get('DSC_SEGMENTO', '')))
        situacao = row.get('SITUAÇÃO ATUAL', row.get('DSC_SIT_ATU_CONTRIBUINTE', ''))
        cols[7].markdown(truncar_texto('' if pd.isna(situacao) else str(situacao), 32))
        cols[8].markdown(badge_dias_para_saida(row.get('DIAS_PARA_SAIDA', '')), unsafe_allow_html=True)
        cols[9].markdown(badge_risco(row.get('nivel_risco', '')), unsafe_allow_html=True)
        idx_farol = pd.to_numeric(row.get('indice_geral_farol', 0), errors='coerce')
        cols[10].markdown(formatar_decimal(0 if pd.isna(idx_farol) else idx_farol))
    st.markdown('</div>', unsafe_allow_html=True)



def mapa_cores_categorias(valores, paleta):
    unicos = [str(v) for v in pd.Series(valores).fillna("Não informado").astype(str).tolist()]
    unicos = list(dict.fromkeys(unicos))
    return {valor: paleta[i % len(paleta)] for i, valor in enumerate(unicos)}


def estilizar_figura(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.18)",
        font=dict(color="#e5e7eb"),
        margin=dict(l=20, r=20, t=25, b=20),
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.10)", zeroline=False)
    return fig



def extrair_regras_acionadas(texto):
    if texto is None or pd.isna(texto):
        return []
    bruto = str(texto).replace(";", ",").replace("|", ",")
    partes = [p.strip() for p in bruto.split(",") if p.strip()]
    regras = []
    vistos = set()
    for p in partes:
        codigo = p.upper().strip()
        if codigo and codigo not in vistos:
            vistos.add(codigo)
            regras.append(codigo)
    return regras



def calcular_top_regras(df: pd.DataFrame, n=10):
    if "regras_acionadas" not in df.columns or df.empty:
        return pd.DataFrame(columns=["Regra", "Nome", "Descrição", "Quantidade"])

    contagem = {}
    for texto in df["regras_acionadas"]:
        for regra in extrair_regras_acionadas(texto):
            if regra in REGRAS_OFICIAIS:
                contagem[regra] = contagem.get(regra, 0) + 1

    if not contagem:
        return pd.DataFrame(columns=["Regra", "Nome", "Descrição", "Quantidade"])

    out = pd.DataFrame(
        [
            {
                "Regra": regra,
                "Nome": NOMES_REGRAS.get(regra, regra),
                "Descrição": DESCRICOES_REGRAS.get(regra, "Descrição não informada"),
                "Quantidade": qtd,
            }
            for regra, qtd in contagem.items()
        ]
    ).sort_values("Quantidade", ascending=False).head(n).reset_index(drop=True)

    return out



def obter_dominante(df: pd.DataFrame, coluna: str, padrao="Não identificado"):
    if coluna not in df.columns or df.empty:
        return padrao
    serie = df[coluna].fillna("Não informado").astype(str)
    if serie.empty:
        return padrao
    return serie.value_counts().idxmax()

def _categoria_predominante_info(df: pd.DataFrame, coluna: str, padrao="Não identificado"):
    if coluna not in df.columns or df.empty:
        return padrao, 0.0
    serie = df[coluna].fillna("Não informado").astype(str)
    if serie.empty:
        return padrao, 0.0
    dominante = serie.value_counts().idxmax()
    qtd = int((serie == dominante).sum())
    return dominante, _percentual(qtd, len(serie))




def montar_resumo_filtros(municipio, orgao, risco, situacao_atual, regra, segmento, cnae, faixa_indice, faixa_regras, faixa_entradas, faixa_saidas, faixa_dimp, faixa_nao_seladas, modo, top_n):
    tags = [
        f'<span class="farol-filter-tag"><b>Município:</b> {municipio}</span>',
        f'<span class="farol-filter-tag"><b>Órgão local:</b> {orgao}</span>',
        f'<span class="farol-filter-tag"><b>Risco:</b> {risco}</span>',
        f'<span class="farol-filter-tag"><b>Situação Atual:</b> {situacao_atual}</span>',
        f'<span class="farol-filter-tag"><b>Regra:</b> {regra}</span>',
        f'<span class="farol-filter-tag"><b>Segmento:</b> {segmento}</span>',
        f'<span class="farol-filter-tag"><b>CNAE:</b> {cnae}</span>',
        f'<span class="farol-filter-tag"><b>Índice FAROL:</b> {formatar_decimal(faixa_indice[0])} – {formatar_decimal(faixa_indice[1])}</span>',
        f'<span class="farol-filter-tag"><b>Qtd. regras:</b> {faixa_regras[0]} – {faixa_regras[1]}</span>',
        f'<span class="farol-filter-tag"><b>Entradas:</b> {formatar_decimal(faixa_entradas[0])} – {formatar_decimal(faixa_entradas[1])}</span>',
        f'<span class="farol-filter-tag"><b>Saídas:</b> {formatar_decimal(faixa_saidas[0])} – {formatar_decimal(faixa_saidas[1])}</span>',
        f'<span class="farol-filter-tag"><b>VR_DIMP:</b> {formatar_decimal(faixa_dimp[0])} – {formatar_decimal(faixa_dimp[1])}</span>',
        f'<span class="farol-filter-tag"><b>Entradas não seladas:</b> {formatar_decimal(faixa_nao_seladas[0])} – {formatar_decimal(faixa_nao_seladas[1])}</span>',
        f'<span class="farol-filter-tag"><b>Modo:</b> {modo}</span>',
        f'<span class="farol-filter-tag"><b>Top N:</b> {top_n}</span>',
    ]
    return f'<div class="farol-filter-summary">{"".join(tags)}</div>'


def gerar_leitura_executiva(df: pd.DataFrame, risco_top, situacao_top, regra_top, media_indice, media_regras):
    total = len(df)
    muito_alto_critico = 0
    if "nivel_risco" in df.columns:
        muito_alto_critico = int(df["nivel_risco"].astype(str).isin(["Muito Alto", "Crítico", "Critico"]).sum())

    regra_top_txt = "Não identificada"
    if not regra_top.empty:
        primeira = regra_top.iloc[0]
        regra_top_txt = f"{primeira['Regra']} — {primeira['Nome']}"

    return f"""
<div class="farol-reading-card">
    <div class="farol-section-title">Leitura executiva do recorte</div>
    <div class="farol-section-subtitle">Síntese do subconjunto filtrado para apoiar exploração temática e aprofundamento operacional.</div>

<ul>
    <li><b>Recorte ativo:</b> {formatar_inteiro(total)} contribuintes, com {formatar_inteiro(muito_alto_critico)} em faixas Muito Alto / Crítico.</li>
    <li><b>Padrão dominante:</b> risco predominante <b>{risco_top}</b> e situação atual predominante <b>{situacao_top}</b>.</li>
    <li><b>Sinal mais recorrente:</b> {regra_top_txt}.</li>
</ul>

<div class="farol-reading-small">
<b>Leitura analítica:</b> o recorte apresenta índice FAROL médio de <b>{formatar_decimal(media_indice)}</b> e média de <b>{formatar_decimal(media_regras)}</b> regras acionadas por contribuinte. Isso ajuda a distinguir subconjuntos com maior densidade de risco e maior concentração temática.<br><br>
<b>Uso sugerido:</b> utilizar esta página para comparar padrões por risco, situação atual, regra, CNAE, segmento e órgão local, direcionando depois a análise individual para a Consulta do Contribuinte ou a fila da página Ranking de Análise.
</div>
</div>
""".strip()


def preparar_tabela(df: pd.DataFrame, modo: str, top_n: int):
    if df.empty:
        return pd.DataFrame()

    # Detectar colunas de saídas (nomes variam)
    saidas_col = next((c for c in ["Saidas Totais", "saidas_v6", "Saidas", "SAIDAS"] if c in df.columns), None)

    # Colunas comuns a ambos os modos
    colunas_base = [
        "COD_CNPJ",
        "DSC_RAZAO_SOCIAL",
        "DSC_SIT_ATU_CONTRIBUINTE",  # Situação
        "SITUAÇÃO ATUAL",             # Situação (nome alternativo)
        "C_DSC_MUNICIPIO",
        "DSC_ORGAO_LOCAL",
        "DSC_SEGMENTO",
        "DSC_REGIME_REC_CONTRIBUINTE",
        "COD_CNAE_PRINC_CONTRIBUINTE",
        "DSC_CNAE_PRINC_CONTRIBUINTE",
        "DECRETO",
        "DILIGENCIA",
        "NOM_CONTADOR",
        "ENTRADAS",
        saidas_col,
        "VR_DIMP",
        "ARRECADACAO",
        "DIAS_PARA_SAIDA",
        "nivel_risco",
        "indice_geral_farol",
        "qtd_regras_acionadas",
        "tipologia_principal",
        "regras_acionadas",
        "justificativa_resumida",
    ]

    if modo == "Executivo":
        # Executivo: dimensões principais + risco + índice
        colunas = [
            "COD_CNPJ",
            "DSC_RAZAO_SOCIAL",
            "DSC_SIT_ATU_CONTRIBUINTE",
            "SITUAÇÃO ATUAL",
            "C_DSC_MUNICIPIO",
            "DSC_ORGAO_LOCAL",
            "DSC_SEGMENTO",
            "DSC_REGIME_REC_CONTRIBUINTE",
            "DIAS_PARA_SAIDA",
            "nivel_risco",
            "indice_geral_farol",
            "qtd_regras_acionadas",
            "tipologia_principal",
        ]
    else:
        colunas = [c for c in colunas_base if c is not None]

    colunas = [c for c in colunas if c and c in df.columns]
    # Evitar duplicatas mantendo ordem
    vistos = set()
    colunas_unicas = []
    for c in colunas:
        if c not in vistos:
            vistos.add(c)
            colunas_unicas.append(c)

    out = df[colunas_unicas].head(top_n).copy()

    renomear = {
        "COD_CNPJ": "CNPJ",
        "DSC_RAZAO_SOCIAL": "Razão Social",
        "DSC_SIT_ATU_CONTRIBUINTE": "Situação",
        "SITUAÇÃO ATUAL": "Situação",
        "C_DSC_MUNICIPIO": "Município",
        "DSC_ORGAO_LOCAL": "Órgão Local",
        "DSC_SEGMENTO": "Segmento",
        "DSC_REGIME_REC_CONTRIBUINTE": "Regime",
        "COD_CNAE_PRINC_CONTRIBUINTE": "CNAE",
        "DSC_CNAE_PRINC_CONTRIBUINTE": "Descrição CNAE",
        "DECRETO": "Decreto",
        "DILIGENCIA": "Diligência",
        "NOM_CONTADOR": "Contador",
        "ENTRADAS": "Entradas",
        "VR_DIMP": "VR DIMP",
        "ARRECADACAO": "Arrecadação",
        "DIAS_PARA_SAIDA": "Dias p/ Saída",
        "nivel_risco": "Nível de Risco",
        "indice_geral_farol": "Índice FAROL",
        "qtd_regras_acionadas": "Qtd Regras",
        "tipologia_principal": "Tipologia",
        "regras_acionadas": "Regras Acionadas",
        "justificativa_resumida": "Justificativa",
    }
    if saidas_col:
        renomear[saidas_col] = "Saídas"

    out = out.rename(columns=renomear)

    # Formatar numéricos
    if "Índice FAROL" in out.columns:
        out["Índice FAROL"] = pd.to_numeric(out["Índice FAROL"], errors="coerce").fillna(0).map(lambda x: f"{x:.2f}")
    for col_num in ["Entradas", "Saídas", "VR DIMP", "Arrecadação"]:
        if col_num in out.columns:
            out[col_num] = pd.to_numeric(out[col_num], errors="coerce").fillna(0).map(lambda x: f"{x:,.2f}")
    if "Dias p/ Saída" in out.columns:
        out["Dias p/ Saída"] = pd.to_numeric(out["Dias p/ Saída"], errors="coerce").fillna(0).astype(int)
    if "CNPJ" in out.columns:
        def _fmt_cnpj(v):
            d = ''.join(c for c in str(v) if c.isdigit())
            if 11 <= len(d) <= 13: d = d.zfill(14)
            if len(d) == 14: return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
            return str(v)
        out["CNPJ"] = out["CNPJ"].apply(_fmt_cnpj)

    # Remover coluna duplicada de Situação se ambas existirem
    if out.columns.tolist().count("Situação") > 1:
        out = out.loc[:, ~out.columns.duplicated()]

    return out


# =========================
# APP
# =========================
aplicar_estilos()
exigir_acesso("farol")

_banner_farol = banner_atualizacao()
if _banner_farol:
    st.markdown(_banner_farol, unsafe_allow_html=True)

st.markdown(
    """
    <div class="farol-page-hero">
        <h1>🧭 Exploração da Base</h1>
        <p>
            Laboratório analítico do FAROL para investigar recortes temáticos da base,
            comparar padrões de risco e identificar concentrações por tipologia, CNAE, segmento e órgão local.
        </p>
        <div class="farol-chip-row">
            <span class="farol-chip">Exploração temática</span>
            <span class="farol-chip">Recorte filtrável</span>
            <span class="farol-chip">Leitura executiva</span>
            <span class="farol-chip">Exportação CSV</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with loading():
    data = load_data()
semaforo = data["semaforo"]

if semaforo is None or semaforo.empty:
    st.warning("A base do semáforo não foi carregada ou está vazia.")
    st.stop()

with st.sidebar:
    st.header("Apoio")
    st.caption("Use esta página para investigar padrões do recorte e exportar o subconjunto atual.")



def _serie_numerica(df: pd.DataFrame, coluna: str) -> pd.Series:
    if coluna not in df.columns:
        return pd.Series([0.0], dtype="float64")
    s = pd.to_numeric(df[coluna], errors="coerce").fillna(0.0)
    if s.empty:
        return pd.Series([0.0], dtype="float64")
    return s


def _faixa_padrao(df: pd.DataFrame, coluna: str):
    s = _serie_numerica(df, coluna)
    minimo = float(s.min())
    maximo = float(s.max())
    if maximo <= minimo:
        maximo = minimo + 0.01
    return minimo, maximo



def _ajustar_faixa(valor_inicial, valor_final, minimo, maximo, inteiro=False):
    try:
        ini = int(valor_inicial) if inteiro else float(valor_inicial)
    except Exception:
        ini = int(minimo) if inteiro else float(minimo)
    try:
        fim = int(valor_final) if inteiro else float(valor_final)
    except Exception:
        fim = int(maximo) if inteiro else float(maximo)

    lim_inf = int(minimo) if inteiro else float(minimo)
    lim_sup = int(maximo) if inteiro else float(maximo)

    ini = max(lim_inf, min(ini, lim_sup))
    fim = max(lim_inf, min(fim, lim_sup))

    if ini > fim:
        ini, fim = fim, ini

    return (ini, fim)



def _sync_slider_para_campos(prefixo: str, minimo, maximo, inteiro=False):
    valor = st.session_state.get(f"{prefixo}_slider", (minimo, maximo))
    ini, fim = _ajustar_faixa(valor[0], valor[1], minimo, maximo, inteiro=inteiro)
    st.session_state[f"{prefixo}_ini"] = ini
    st.session_state[f"{prefixo}_fim"] = fim
    st.session_state[f"{prefixo}_slider"] = (ini, fim)



def _sync_campos_para_slider(prefixo: str, minimo, maximo, inteiro=False):
    ini = st.session_state.get(f"{prefixo}_ini", minimo)
    fim = st.session_state.get(f"{prefixo}_fim", maximo)
    faixa = _ajustar_faixa(ini, fim, minimo, maximo, inteiro=inteiro)
    st.session_state[f"{prefixo}_ini"] = faixa[0]
    st.session_state[f"{prefixo}_fim"] = faixa[1]
    st.session_state[f"{prefixo}_slider"] = faixa



def renderizar_filtro_faixa(label: str, prefixo: str, minimo, maximo, *, inteiro=False, step=None):
    if f"{prefixo}_slider" not in st.session_state:
        faixa_inicial = _ajustar_faixa(minimo, maximo, minimo, maximo, inteiro=inteiro)
        st.session_state[f"{prefixo}_slider"] = faixa_inicial
        st.session_state[f"{prefixo}_ini"] = faixa_inicial[0]
        st.session_state[f"{prefixo}_fim"] = faixa_inicial[1]

    faixa_atual = _ajustar_faixa(
        st.session_state.get(f"{prefixo}_ini", minimo),
        st.session_state.get(f"{prefixo}_fim", maximo),
        minimo,
        maximo,
        inteiro=inteiro,
    )
    st.session_state[f"{prefixo}_slider"] = faixa_atual
    st.session_state[f"{prefixo}_ini"] = faixa_atual[0]
    st.session_state[f"{prefixo}_fim"] = faixa_atual[1]

    st.slider(
        label,
        min_value=int(minimo) if inteiro else float(minimo),
        max_value=int(maximo) if inteiro else float(maximo),
        step=(1 if inteiro else float(step if step is not None else 0.1)),
        key=f"{prefixo}_slider",
        on_change=_sync_slider_para_campos,
        args=(prefixo, minimo, maximo, inteiro),
    )

    c_ini, c_fim = st.columns(2)
    c_ini.number_input(
        "Valor inicial",
        min_value=int(minimo) if inteiro else float(minimo),
        max_value=int(maximo) if inteiro else float(maximo),
        step=(1 if inteiro else float(step if step is not None else 0.1)),
        key=f"{prefixo}_ini",
        on_change=_sync_campos_para_slider,
        args=(prefixo, minimo, maximo, inteiro),
    )
    c_fim.number_input(
        "Valor final",
        min_value=int(minimo) if inteiro else float(minimo),
        max_value=int(maximo) if inteiro else float(maximo),
        step=(1 if inteiro else float(step if step is not None else 0.1)),
        key=f"{prefixo}_fim",
        on_change=_sync_campos_para_slider,
        args=(prefixo, minimo, maximo, inteiro),
    )

    return st.session_state[f"{prefixo}_slider"]


# =========================
# FILTROS VISÍVEIS
# =========================
municipios = ["Todos"]
if "C_DSC_MUNICIPIO" in semaforo.columns:
    municipios += sorted(semaforo["C_DSC_MUNICIPIO"].dropna().astype(str).unique().tolist())

orgaos = ["Todos"]
if "DSC_ORGAO_LOCAL" in semaforo.columns:
    orgaos += sorted(semaforo["DSC_ORGAO_LOCAL"].dropna().astype(str).unique().tolist())

riscos = ["Todos"]
if "nivel_risco" in semaforo.columns:
    riscos += sorted(semaforo["nivel_risco"].dropna().astype(str).unique().tolist())

situacoes_atuais = ["Todos"]
col_situacao = "SITUAÇÃO ATUAL" if "SITUAÇÃO ATUAL" in semaforo.columns else ("DSC_SIT_ATU_CONTRIBUINTE" if "DSC_SIT_ATU_CONTRIBUINTE" in semaforo.columns else None)
if col_situacao:
    situacoes_atuais += sorted(semaforo[col_situacao].dropna().astype(str).unique().tolist())

# Labels do dropdown: "R01 — Saída Sem Entrada" etc.
regras_labels = ["Todas"] + [
    f"{codigo} — {NOMES_REGRAS.get(codigo, codigo)}"
    for codigo in REGRAS_OFICIAIS
]
# Mapa label → código para uso no filtro
_label_para_codigo = {
    f"{codigo} — {NOMES_REGRAS.get(codigo, codigo)}": codigo
    for codigo in REGRAS_OFICIAIS
}

segmentos = ["Todos"]
if "DSC_SEGMENTO" in semaforo.columns:
    segmentos += sorted(semaforo["DSC_SEGMENTO"].dropna().astype(str).unique().tolist())

cnaes = ["Todos"]
if "COD_CNAE_PRINC_CONTRIBUINTE" in semaforo.columns:
    cnaes += sorted(
        semaforo["COD_CNAE_PRINC_CONTRIBUINTE"]
        .dropna()
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .unique()
        .tolist()
    )

indice_min, indice_max = _faixa_padrao(semaforo, "indice_geral_farol")
regras_min = int(pd.to_numeric(semaforo.get("qtd_regras_acionadas", 0), errors="coerce").fillna(0).min())
regras_max = int(max(pd.to_numeric(semaforo.get("qtd_regras_acionadas", 0), errors="coerce").fillna(0).max(), regras_min + 1))

entradas_min, entradas_max = _faixa_padrao(semaforo, "ENTRADAS")
saidas_coluna = "Saidas Totais" if "Saidas Totais" in semaforo.columns else ("Saidas" if "Saidas" in semaforo.columns else "")
saidas_min, saidas_max = _faixa_padrao(semaforo, saidas_coluna if saidas_coluna else "indice_geral_farol")
dimp_min, dimp_max = _faixa_padrao(semaforo, "VR_DIMP")
nao_seladas_min, nao_seladas_max = _faixa_padrao(semaforo, "ENTRADAS_NAO_SELADAS")

st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Comando do laboratório analítico</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="farol-section-subtitle">Defina o recorte principal da base e aplique os filtros para atualizar os indicadores, gráficos, grade operacional e tabela.</div>',
    unsafe_allow_html=True,
)

f1, f2, f3, f4 = st.columns(4)
municipio = f1.selectbox("Município", municipios, index=0)
orgao_local = f2.selectbox("Órgão local", orgaos, index=0)
risco = f3.selectbox("Nível de risco", riscos, index=0)
situacao_atual = f4.selectbox("Situação Atual", situacoes_atuais, index=0)

f5, f6, f7, f8 = st.columns(4)
regra_label_selecionada = f5.selectbox("Regra homologada", regras_labels, index=0)
regra_filtro = _label_para_codigo.get(regra_label_selecionada, "Todas") if regra_label_selecionada != "Todas" else "Todas"
segmento = f6.selectbox("Segmento", segmentos, index=0)
cnae = f7.selectbox("CNAE", cnaes, index=0)
modo = f8.radio("Modo da tabela", ["Executivo", "Analítico"], index=0, horizontal=True)

f9, f10, f11, f12 = st.columns(4)
if hasattr(st, "segmented_control"):
    top_n = f9.segmented_control(
        "Top N da tabela",
        options=[20, 50, 100, 200, 500, 1000],
        default=50,
        key="top_n_exploracao",
    )
else:
    top_n = f9.selectbox("Top N da tabela", [20, 50, 100, 200, 500, 1000], index=1)

with f10:
    faixa_indice = renderizar_filtro_faixa(
        "Faixa do Índice FAROL",
        "exploracao_indice_farol",
        float(indice_min),
        float(indice_max),
        inteiro=False,
        step=0.1,
    )

with f11:
    faixa_regras = renderizar_filtro_faixa(
        "Qtd. de regras acionadas",
        "exploracao_qtd_regras",
        int(regras_min),
        int(regras_max),
        inteiro=True,
        step=1,
    )

with f12:
    aplicar = st.button("Aplicar filtros", use_container_width=True)

f13, f14 = st.columns(2)
with f13:
    faixa_entradas = renderizar_filtro_faixa(
        "Faixa de Entradas",
        "exploracao_entradas",
        float(entradas_min),
        float(entradas_max),
        inteiro=False,
        step=max((entradas_max - entradas_min) / 200, 0.01),
    )
with f14:
    faixa_saidas = renderizar_filtro_faixa(
        "Faixa de Saídas",
        "exploracao_saidas",
        float(saidas_min),
        float(saidas_max),
        inteiro=False,
        step=max((saidas_max - saidas_min) / 200, 0.01),
    )

f15, f16 = st.columns(2)
with f15:
    faixa_dimp = renderizar_filtro_faixa(
        "Faixa de VR_DIMP",
        "exploracao_vr_dimp",
        float(dimp_min),
        float(dimp_max),
        inteiro=False,
        step=max((dimp_max - dimp_min) / 200, 0.01),
    )
with f16:
    faixa_nao_seladas = renderizar_filtro_faixa(
        "Faixa de Entradas Não Seladas",
        "exploracao_entradas_nao_seladas",
        float(nao_seladas_min),
        float(nao_seladas_max),
        inteiro=False,
        step=max((nao_seladas_max - nao_seladas_min) / 200, 0.01),
    )

if "exploracao_filtros_aplicados" not in st.session_state:
    st.session_state["exploracao_filtros_aplicados"] = True

if aplicar:
    st.session_state["exploracao_filtros_aplicados"] = True

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# BASE FILTRADA
# =========================
base_filtrada = filtrar_base(
    semaforo,
    municipio=municipio,
    nivel_risco=risco,
    orgao_local=orgao_local,
    segmento=segmento,
    cnae=cnae,
).copy()

if col_situacao and situacao_atual != "Todos":
    base_filtrada = base_filtrada[base_filtrada[col_situacao].astype(str) == str(situacao_atual)]

if regra_filtro != "Todas" and "regras_acionadas" in base_filtrada.columns:
    base_filtrada = base_filtrada[
        base_filtrada["regras_acionadas"].fillna("").astype(str).str.contains(fr"\b{re.escape(regra_filtro)}\b", regex=True)
    ]

if "indice_geral_farol" in base_filtrada.columns:
    base_filtrada["indice_geral_farol"] = pd.to_numeric(base_filtrada["indice_geral_farol"], errors="coerce").fillna(0)
    base_filtrada = base_filtrada[
        (base_filtrada["indice_geral_farol"] >= faixa_indice[0]) &
        (base_filtrada["indice_geral_farol"] <= faixa_indice[1])
    ]

if "qtd_regras_acionadas" in base_filtrada.columns:
    base_filtrada["qtd_regras_acionadas"] = pd.to_numeric(base_filtrada["qtd_regras_acionadas"], errors="coerce").fillna(0)
    base_filtrada = base_filtrada[
        (base_filtrada["qtd_regras_acionadas"] >= faixa_regras[0]) &
        (base_filtrada["qtd_regras_acionadas"] <= faixa_regras[1])
    ]

if "ENTRADAS" in base_filtrada.columns:
    base_filtrada["ENTRADAS"] = pd.to_numeric(base_filtrada["ENTRADAS"], errors="coerce").fillna(0)
    base_filtrada = base_filtrada[
        (base_filtrada["ENTRADAS"] >= faixa_entradas[0]) &
        (base_filtrada["ENTRADAS"] <= faixa_entradas[1])
    ]

if saidas_coluna and saidas_coluna in base_filtrada.columns:
    base_filtrada[saidas_coluna] = pd.to_numeric(base_filtrada[saidas_coluna], errors="coerce").fillna(0)
    base_filtrada = base_filtrada[
        (base_filtrada[saidas_coluna] >= faixa_saidas[0]) &
        (base_filtrada[saidas_coluna] <= faixa_saidas[1])
    ]

if "VR_DIMP" in base_filtrada.columns:
    base_filtrada["VR_DIMP"] = pd.to_numeric(base_filtrada["VR_DIMP"], errors="coerce").fillna(0)
    base_filtrada = base_filtrada[
        (base_filtrada["VR_DIMP"] >= faixa_dimp[0]) &
        (base_filtrada["VR_DIMP"] <= faixa_dimp[1])
    ]

if "ENTRADAS_NAO_SELADAS" in base_filtrada.columns:
    base_filtrada["ENTRADAS_NAO_SELADAS"] = pd.to_numeric(base_filtrada["ENTRADAS_NAO_SELADAS"], errors="coerce").fillna(0)
    base_filtrada = base_filtrada[
        (base_filtrada["ENTRADAS_NAO_SELADAS"] >= faixa_nao_seladas[0]) &
        (base_filtrada["ENTRADAS_NAO_SELADAS"] <= faixa_nao_seladas[1])
    ]

st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Resumo do recorte aplicado</div>', unsafe_allow_html=True)
st.markdown(
    montar_resumo_filtros(
        municipio, orgao_local, risco, situacao_atual, regra_filtro, segmento, cnae,
        faixa_indice, faixa_regras, faixa_entradas, faixa_saidas, faixa_dimp, faixa_nao_seladas, modo, top_n
    ),
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# MÉTRICAS
# =========================
total = len(base_filtrada)
alto_critico = 0
if "nivel_risco" in base_filtrada.columns:
    alto_critico = int(
        base_filtrada["nivel_risco"].astype(str).isin(["Alto", "Muito Alto", "Crítico", "Critico"]).sum()
    )

risco_top, perc_risco_top = _categoria_predominante_info(base_filtrada, "nivel_risco")
situacao_top, perc_situacao_top = _categoria_predominante_info(base_filtrada, col_situacao, "Não identificada") if col_situacao else ("Não identificada", 0.0)
media_indice = float(pd.to_numeric(base_filtrada.get("indice_geral_farol", 0), errors="coerce").fillna(0).mean()) if total else 0.0
media_regras = float(pd.to_numeric(base_filtrada.get("qtd_regras_acionadas", 0), errors="coerce").fillna(0).mean()) if total else 0.0
media_dias_saida = float(pd.to_numeric(base_filtrada.get("DIAS_PARA_SAIDA", 0), errors="coerce").fillna(0).mean()) if total else 0.0

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    st.markdown(
        _kpi_card(
            "Contribuintes",
            formatar_inteiro(total),
            f"Top N visível: {formatar_inteiro(min(total, int(top_n)))}",
            "primary",
            "📋",
            "Quantidade de contribuintes no recorte atual da exploração.",
        ),
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        _kpi_card(
            "Alto / Crítico",
            formatar_inteiro(alto_critico),
            f"{formatar_decimal(_percentual(alto_critico, total) * 100, 1)}% do recorte",
            "danger",
            "🚨",
            "Contribuintes em faixas Alto, Muito Alto ou Crítico dentro do recorte filtrado.",
        ),
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        _kpi_card(
            "Risco Predominante",
            str(risco_top),
            f"{formatar_decimal(perc_risco_top * 100, 1)}% do recorte",
            "warning",
            "🎯",
            "Faixa de risco mais frequente entre os contribuintes atualmente exibidos.",
        ),
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        _kpi_card(
            "Situação Dominante",
            str(situacao_top),
            f"{formatar_decimal(perc_situacao_top * 100, 1)}% do recorte",
            "info",
            "🧭",
            "Situação cadastral/operacional mais recorrente no subconjunto analisado.",
        ),
        unsafe_allow_html=True,
    )
with k5:
    st.markdown(
        _kpi_card(
            "Índice FAROL Médio",
            formatar_decimal(media_indice),
            f"Dias p/ saída médios: {formatar_decimal(media_dias_saida, 1)}",
            "primary",
            "📈",
            "Intensidade média de risco do recorte atual, combinada ao tempo médio até a saída.",
        ),
        unsafe_allow_html=True,
    )
with k6:
    st.markdown(
        _kpi_card(
            "Média de Regras",
            formatar_decimal(media_regras),
            f"Sinal recorrente: {regra_filtro if regra_filtro != 'Todas' else 'todas as regras'}",
            "warning",
            "🧩",
            "Quantidade média de regras acionadas por contribuinte no subconjunto filtrado.",
        ),
        unsafe_allow_html=True,
    )

# =========================
# DESTAQUES DO RECORTE
# =========================
top_regras = calcular_top_regras(base_filtrada, n=10)
regra_top_txt = "Não identificada"
if not top_regras.empty:
    regra_top_txt = f"{top_regras.iloc[0]['Regra']} — {top_regras.iloc[0]['Nome']}"

st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Destaques do recorte</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="farol-section-subtitle">Leitura rápida antes do aprofundamento por gráficos e tabela detalhada.</div>',
    unsafe_allow_html=True,
)

d1, d2, d3 = st.columns(3)
with d1:
    st.markdown(
        f"""
        <div class="farol-insight">
            <div class="farol-insight-kicker">Pressão do recorte</div>
            <div class="farol-insight-title">{formatar_inteiro(total)} contribuintes filtrados</div>
            <div class="farol-insight-text">
                O subconjunto atual concentra {formatar_inteiro(alto_critico)} contribuintes em faixas Alto / Muito Alto / Crítico,
                servindo como base para análise comparativa e triagem temática.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with d2:
    st.markdown(
        f"""
        <div class="farol-insight">
            <div class="farol-insight-kicker">Padrão dominante</div>
            <div class="farol-insight-title">{risco_top} / {situacao_top}</div>
            <div class="farol-insight-text">
                O recorte apresenta predominância de risco <b>{risco_top}</b> e situação atual <b>{situacao_top}</b>,
                indicando o foco temático mais forte da seleção atual.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with d3:
    st.markdown(
        f"""
        <div class="farol-insight">
            <div class="farol-insight-kicker">Sinal recorrente</div>
            <div class="farol-insight-title">{regra_top_txt}</div>
            <div class="farol-insight-text">
                A regra mais recorrente do recorte ajuda a identificar a anomalia mais frequente e a orientar
                o aprofundamento analítico subsequente.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# GRÁFICOS
# =========================
st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Concentrações analíticas</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="farol-section-subtitle">Distribuições e concentrações do recorte por risco, situação atual, CNAE, segmento, órgão local e regras.</div>',
    unsafe_allow_html=True,
)

g1, g2 = st.columns(2)

with g1:
    if "nivel_risco" in base_filtrada.columns and not base_filtrada.empty:
        dist_risco = (
            base_filtrada["nivel_risco"]
            .fillna("Não informado")
            .value_counts()
            .reset_index()
        )
        dist_risco.columns = ["nivel_risco", "quantidade"]
        total_risco = dist_risco["quantidade"].sum()
        dist_risco["percentual"] = dist_risco["quantidade"].apply(lambda x: round((x / total_risco) * 100, 2) if total_risco else 0)
        dist_risco = dist_risco.sort_values(["percentual", "quantidade"], ascending=[False, False]).reset_index(drop=True)

        fig_risco = px.bar(
            dist_risco,
            x="quantidade",
            y="nivel_risco",
            orientation="h",
            text="percentual",
            color="nivel_risco",
            color_discrete_map=CORES_RISCO,
        )
        fig_risco.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Quantidade: %{x}<br>Percentual: %{text:.2f}%<extra></extra>",
        )
        fig_risco.update_layout(xaxis_title="Quantidade", yaxis_title="")
        fig_risco = estilizar_figura(fig_risco)
        st.markdown('<div class="farol-section-title">Distribuição de risco</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_risco, use_container_width=True)
    else:
        st.info("Sem dados suficientes para distribuição de risco.")

with g2:
    if col_situacao and not base_filtrada.empty:
        top_situacoes = (
            base_filtrada[col_situacao]
            .fillna("Não informada")
            .astype(str)
            .value_counts()
            .head(8)
            .reset_index()
        )
        top_situacoes.columns = ["situacao", "quantidade"]
        top_situacoes = top_situacoes.sort_values("quantidade", ascending=False).reset_index(drop=True)

        mapa_cores_situacao = mapa_cores_categorias(top_situacoes["situacao"], PALETA_SITUACAO)
        fig_sit = px.bar(
            top_situacoes,
            x="quantidade",
            y="situacao",
            orientation="h",
            text="quantidade",
            color="situacao",
            color_discrete_map=mapa_cores_situacao,
        )
        fig_sit.update_traces(textposition="outside")
        fig_sit.update_layout(xaxis_title="Quantidade", yaxis_title="")
        fig_sit = estilizar_figura(fig_sit)
        st.markdown('<div class="farol-section-title">Top situações atuais</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_sit, use_container_width=True)
    else:
        st.info("Sem dados suficientes para situações atuais.")

g3, g4 = st.columns(2)

with g3:
    if "COD_CNAE_PRINC_CONTRIBUINTE" in base_filtrada.columns and not base_filtrada.empty:
        base_cnae = base_filtrada.copy()

        base_cnae["CNAE_TXT"] = (
            base_cnae["COD_CNAE_PRINC_CONTRIBUINTE"]
            .fillna("Não informado")
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.strip()
        )

        if "DSC_CNAE_PRINC_CONTRIBUINTE" in base_cnae.columns:
            base_cnae["CNAE_ROTULO"] = base_cnae.apply(
                lambda row: (
                    f"{row['CNAE_TXT']} — {row['DSC_CNAE_PRINC_CONTRIBUINTE']}"
                    if pd.notna(row["DSC_CNAE_PRINC_CONTRIBUINTE"]) and str(row["DSC_CNAE_PRINC_CONTRIBUINTE"]).strip() != ""
                    else row["CNAE_TXT"]
                ),
                axis=1,
            )
        else:
            base_cnae["CNAE_ROTULO"] = base_cnae["CNAE_TXT"]

        top_cnaes = (
            base_cnae["CNAE_ROTULO"]
            .value_counts()
            .head(8)
            .reset_index()
        )
        top_cnaes.columns = ["cnae", "quantidade"]
        top_cnaes = top_cnaes.sort_values("quantidade", ascending=False).reset_index(drop=True)

        mapa_cores_cnae = mapa_cores_categorias(top_cnaes["cnae"], PALETA_CNAE)
        fig_cnae = px.bar(
            top_cnaes,
            x="quantidade",
            y="cnae",
            orientation="h",
            text="quantidade",
            color="cnae",
            color_discrete_map=mapa_cores_cnae,
        )
        fig_cnae.update_traces(textposition="outside")
        fig_cnae.update_layout(
            xaxis_title="Quantidade",
            yaxis_title="CNAE",
        )
        fig_cnae = estilizar_figura(fig_cnae)
        st.markdown('<div class="farol-section-title">Top CNAEs</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_cnae, use_container_width=True)
    else:
        st.info("Sem dados suficientes para CNAEs.")

with g4:
    if "DSC_ORGAO_LOCAL" in base_filtrada.columns and not base_filtrada.empty:
        top_orgaos = (
            base_filtrada["DSC_ORGAO_LOCAL"]
            .fillna("Não informado")
            .astype(str)
            .value_counts()
            .head(8)
            .reset_index()
        )
        top_orgaos.columns = ["orgao", "quantidade"]
        top_orgaos = top_orgaos.sort_values("quantidade", ascending=False).reset_index(drop=True)

        mapa_cores_orgao = mapa_cores_categorias(top_orgaos["orgao"], PALETA_ORGAO)
        fig_org = px.bar(
            top_orgaos,
            x="quantidade",
            y="orgao",
            orientation="h",
            text="quantidade",
            color="orgao",
            color_discrete_map=mapa_cores_orgao,
        )
        fig_org.update_traces(textposition="outside")
        fig_org.update_layout(xaxis_title="Quantidade", yaxis_title="")
        fig_org = estilizar_figura(fig_org)
        st.markdown('<div class="farol-section-title">Top órgãos locais</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_org, use_container_width=True)
    else:
        st.info("Sem dados suficientes para órgãos locais.")

g5, g6 = st.columns(2)

with g5:
    if "DSC_SEGMENTO" in base_filtrada.columns and not base_filtrada.empty:
        top_segmentos = (
            base_filtrada["DSC_SEGMENTO"]
            .fillna("Não informado")
            .astype(str)
            .value_counts()
            .head(8)
            .reset_index()
        )
        top_segmentos.columns = ["segmento", "quantidade"]
        top_segmentos = top_segmentos.sort_values("quantidade", ascending=False).reset_index(drop=True)

        mapa_cores_segmento = mapa_cores_categorias(top_segmentos["segmento"], PALETA_SEGMENTO)
        fig_seg = px.bar(
            top_segmentos,
            x="quantidade",
            y="segmento",
            orientation="h",
            text="quantidade",
            color="segmento",
            color_discrete_map=mapa_cores_segmento,
        )
        fig_seg.update_traces(textposition="outside")
        fig_seg.update_layout(xaxis_title="Quantidade", yaxis_title="")
        fig_seg = estilizar_figura(fig_seg)
        st.markdown('<div class="farol-section-title">Top segmentos</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_seg, use_container_width=True)
    else:
        st.info("Sem dados suficientes para segmentos.")

with g6:
    if not top_regras.empty:
        regras_plot = top_regras.sort_values("Quantidade", ascending=False).copy()
        regras_plot["rotulo"] = regras_plot["Regra"] + " — " + regras_plot["Nome"]

        fig_reg = go.Figure()
        mapa_cores_regras = mapa_cores_categorias(regras_plot["rotulo"], PALETA_REGRAS)
        fig_reg.add_trace(
            go.Bar(
                x=regras_plot["Quantidade"],
                y=regras_plot["rotulo"],
                orientation="h",
                text=regras_plot["Quantidade"],
                textposition="outside",
                marker=dict(color=[mapa_cores_regras.get(rotulo, "#f97316") for rotulo in regras_plot["rotulo"]]),
                customdata=regras_plot[["Descrição"]],
                hovertemplate="<b>%{y}</b><br>Quantidade: %{x}<br>Descrição: %{customdata[0]}<extra></extra>",
            )
        )
        fig_reg.update_layout(xaxis_title="Quantidade", yaxis_title="", yaxis=dict(autorange="reversed"))
        fig_reg = estilizar_figura(fig_reg)
        st.markdown('<div class="farol-section-title">Top regras homologadas</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_reg, use_container_width=True)
    else:
        st.info("Sem dados suficientes para regras homologadas.")

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# TABELA
# =========================
st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Tabela detalhada do recorte</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="farol-section-subtitle">Visualização detalhada do subconjunto filtrado, com nível de detalhe ajustado pelo modo selecionado.</div>',
    unsafe_allow_html=True,
)

# Ordenação: índice FAROL decrescente (maior risco primeiro).
# Desempate por DIAS_PARA_SAIDA ascendente — quem está mais perto de sair
# da base (menos dias restantes) é mais urgente e aparece antes.
if "indice_geral_farol" in base_filtrada.columns:
    _base_sort = base_filtrada.copy()
    _base_sort["indice_geral_farol"] = pd.to_numeric(_base_sort["indice_geral_farol"], errors="coerce").fillna(0)
    if "DIAS_PARA_SAIDA" in _base_sort.columns:
        _base_sort["DIAS_PARA_SAIDA"] = pd.to_numeric(_base_sort["DIAS_PARA_SAIDA"], errors="coerce").fillna(9999)
        base_ordenada_exibicao = _base_sort.sort_values(
            ["indice_geral_farol", "DIAS_PARA_SAIDA"],
            ascending=[False, True],
        )
    else:
        base_ordenada_exibicao = _base_sort.sort_values("indice_geral_farol", ascending=False)
else:
    base_ordenada_exibicao = base_filtrada.copy()
base_ordenada_exibicao = base_ordenada_exibicao.head(int(top_n)).copy()

tabela_exibicao = preparar_tabela(
    base_ordenada_exibicao,
    modo=modo,
    top_n=int(top_n),
)

if base_ordenada_exibicao.empty:
    st.info("Nenhum contribuinte foi encontrado para o recorte aplicado.")
else:
    renderizar_grade_operacional_exploracao(base_ordenada_exibicao)

    cexp1, cexp2 = st.columns([1.2, 0.8])
    with cexp1:
        st.caption("Cada linha permite abrir diretamente a Consulta do Contribuinte com o CNPJ preenchido. A grade mantém CNPJ, Segmento, Situação Atual, Dias para Saída e Índice FAROL.")
    with cexp2:
        csv = base_filtrada.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Exportar recorte atual (CSV)",
            csv,
            "exploracao_base_recorte.csv",
            "text/csv",
        )

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# LEITURA EXECUTIVA
# =========================
st.markdown(
    gerar_leitura_executiva(
        base_filtrada,
        risco_top=risco_top,
        situacao_top=situacao_top,
        regra_top=top_regras,
        media_indice=media_indice,
        media_regras=media_regras,
    ),
    unsafe_allow_html=True,
)
