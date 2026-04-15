import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from projetos_especiais.farol.farol_config import APP_TITLE, PAGE_TITLES
from coate_styles import aplicar_estilos, loading
from coate_auth import exigir_acesso

from projetos_especiais.farol.farol_core import load_data, buscar_contribuinte
from projetos_especiais.farol.farol_rules_catalog import REGRAS_ATIVAS, REGRAS_NOMES, REGRAS_DESC
from projetos_especiais.farol.farol_metadata import banner_atualizacao

# =========================
# ESTILO GLOBAL
# =========================

# =========================
# AUXILIARES
# =========================
REGRAS_EVIDENCIAS = {
    "R01": [("Saídas Totais", "Saidas Totais"), ("Entradas", "ENTRADAS")],
    "R02": [("Saídas Totais", "Saidas Totais"), ("Entradas", "ENTRADAS")],
    "R05": [("Entradas", "ENTRADAS"), ("Saídas Totais", "Saidas Totais")],
    "R06": [("Entradas", "ENTRADAS"), ("Saídas Totais", "Saidas Totais")],
    "R08": [("VR DIMP", "VR_DIMP"), ("Vendas Totais", "Vendas Totais")],
    "R09": [("VR DIMP", "VR_DIMP"), ("Vendas Totais", "Vendas Totais")],
    "R12": [("Vendas Totais", "Vendas Totais"), ("VR DIMP", "VR_DIMP")],
    "R13": [("Vendas Totais", "Vendas Totais"), ("VR DIMP", "VR_DIMP")],
    "R14": [("SPED Saídas", "SPED_Saídas"), ("SPED Entradas", "SPED_Entradas")],
    "R15": [("Entradas Interestaduais", "ENTRADAS_FORA_CE"), ("Entradas Não Seladas", "ENTRADAS_NAO_SELADAS")],
    "R16": [("Entradas Interestaduais", "ENTRADAS_FORA_CE"), ("Entradas Não Seladas", "ENTRADAS_NAO_SELADAS")],
    "R17": [("Arrecadação", "ARRECADACAO"), ("VR DIMP", "VR_DIMP"), ("Vendas Totais", "Vendas Totais")],
}

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

def formatar_numero_analitico(valor):
    try:
        if valor is None or pd.isna(valor):
            return "Não disponível"
        num = float(valor)
        if abs(num) >= 1000:
            return f"{num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{num:.2f}".replace(".", ",")
    except Exception:
        txt = str(valor)
        return txt if txt.strip() else "Não disponível"

def formatar_dias_para_saida(valor):
    try:
        if valor is None or pd.isna(valor):
            return "Não informado"
        return f"{int(float(valor))} dias"
    except Exception:
        txt = str(valor).strip()
        return txt if txt else "Não informado"

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

def obter_bases_operacionais(linha: pd.Series):
    entradas_brutas = pd.to_numeric(valor_linha(linha, "ENTRADAS", None), errors="coerce")
    compras = pd.to_numeric(valor_linha(linha, "COMPRAS", None), errors="coerce")
    saidas_totais = pd.to_numeric(valor_linha(linha, "Saidas Totais", None), errors="coerce")
    saidas = pd.to_numeric(valor_linha(linha, "Saidas", None), errors="coerce")

    entradas_base = entradas_brutas if pd.notna(entradas_brutas) and entradas_brutas > 0 else compras
    saidas_base = saidas_totais if pd.notna(saidas_totais) and saidas_totais > 0 else saidas
    return entradas_base, saidas_base

def classificar_faixa_adicionamento(razao):
    try:
        if razao is None or pd.isna(razao) or razao <= 0:
            return "Não classificado"
        if razao <= 0.5:
            return "Faixa 1 (0 a 0,5) — peso 1"
        if razao <= 1:
            return "Faixa 2 (0,5 a 1) — peso 2"
        if razao <= 2:
            return "Faixa 3 (1 a 2) — peso 3"
        if razao <= 5:
            return "Faixa 4 (2 a 5) — peso 4"
        if razao <= 10:
            return "Faixa 5 (5 a 10) — peso 5"
        return "Faixa 6 (> 10) — peso 6"
    except Exception:
        return "Não classificado"

def construir_evidencias_regra(regra: str, linha: pd.Series) -> str:
    if regra == "R03":
        entradas = pd.to_numeric(valor_linha(linha, "ENTRADAS", None), errors="coerce")
        qtd_emit = pd.to_numeric(valor_linha(linha, "Qtd_Emitentes_Distintos_Entrada", None), errors="coerce")
        cnpj_emit = valor_linha(linha, "R03_cnpj_emitente_unico", None)
        partes = []
        partes.append(f"<b>Entradas (NF-e):</b> {formatar_numero_analitico(entradas)}" if pd.notna(entradas) else "<b>Entradas (NF-e):</b> não disponível")
        partes.append(f"<b>Qtd. emitentes distintos:</b> {int(qtd_emit)}" if pd.notna(qtd_emit) else "<b>Qtd. emitentes distintos:</b> não disponível")
        if cnpj_emit is not None and str(cnpj_emit).strip() not in ("", "nan", "None"):
            try:
                cnpj_emit = str(int(float(cnpj_emit)))
            except (ValueError, TypeError):
                cnpj_emit = str(cnpj_emit)
            cnpj_fmt = formatar_cnpj(cnpj_emit)
            partes.append(f"<b>CNPJ do emitente único:</b> {cnpj_fmt}")
        else:
            partes.append("<b>CNPJ do emitente único:</b> não disponível")
        return "<br>".join(partes)

    if regra == "R04":
        saidas = pd.to_numeric(valor_linha(linha, "Saidas Totais", None), errors="coerce")
        if pd.isna(saidas) or saidas == 0:
            saidas = pd.to_numeric(valor_linha(linha, "Saidas", None), errors="coerce")
        qtd_dest = pd.to_numeric(valor_linha(linha, "Qtd_Destinatarios_Distintos_Saidas", None), errors="coerce")
        cnpj_dest = valor_linha(linha, "R04_cnpj_destinatario_unico", None)
        partes = []
        partes.append(f"<b>Saídas (NF-e):</b> {formatar_numero_analitico(saidas)}" if pd.notna(saidas) else "<b>Saídas (NF-e):</b> não disponível")
        partes.append(f"<b>Qtd. destinatários distintos:</b> {int(qtd_dest)}" if pd.notna(qtd_dest) else "<b>Qtd. destinatários distintos:</b> não disponível")
        if cnpj_dest is not None and str(cnpj_dest).strip() not in ("", "nan", "None"):
            try:
                cnpj_dest = str(int(float(cnpj_dest)))
            except (ValueError, TypeError):
                cnpj_dest = str(cnpj_dest)
            cnpj_fmt = formatar_cnpj(cnpj_dest)
            partes.append(f"<b>CNPJ do destinatário único:</b> {cnpj_fmt}")
        else:
            partes.append("<b>CNPJ do destinatário único:</b> não disponível")
        return "<br>".join(partes)

    if regra in {"R01", "R02", "R05", "R06"}:
        entradas_base, saidas_base = obter_bases_operacionais(linha)
        partes = [
            f"<b>Entradas base:</b> {formatar_numero_analitico(entradas_base)}" if entradas_base is not None and pd.notna(entradas_base) else "<b>Entradas base:</b> não disponível",
            f"<b>Saídas base:</b> {formatar_numero_analitico(saidas_base)}" if saidas_base is not None and pd.notna(saidas_base) else "<b>Saídas base:</b> não disponível",
        ]

        if regra == "R02" and entradas_base is not None and pd.notna(entradas_base) and entradas_base > 0 and saidas_base is not None and pd.notna(saidas_base) and saidas_base > 0:
            razao = float(saidas_base) / float(entradas_base)
            partes.append(f"<b>Razão saídas/entradas:</b> {formatar_numero_analitico(razao)}")
            partes.append(f"<b>Faixa operacional:</b> {classificar_faixa_adicionamento(razao)}")
        elif regra == "R06" and saidas_base is not None and pd.notna(saidas_base) and saidas_base > 0 and entradas_base is not None and pd.notna(entradas_base) and entradas_base > 0:
            razao = float(entradas_base) / float(saidas_base)
            partes.append(f"<b>Razão entradas/saídas:</b> {formatar_numero_analitico(razao)}")
            partes.append(f"<b>Faixa operacional:</b> {classificar_faixa_adicionamento(razao)}")

        return "<br>".join(partes)

    evidencias = REGRAS_EVIDENCIAS.get(regra, [])
    partes = []
    for rotulo, coluna in evidencias:
        valor = valor_linha(linha, coluna, None)
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            partes.append(f"<b>{rotulo}:</b> não disponível")
        else:
            partes.append(f"<b>{rotulo}:</b> {formatar_numero_analitico(valor)}")

    if regra in {"R15", "R16"}:
        entradas_interestaduais = pd.to_numeric(valor_linha(linha, "ENTRADAS_FORA_CE", None), errors="coerce")
        entradas_nao_seladas = pd.to_numeric(valor_linha(linha, "ENTRADAS_NAO_SELADAS", None), errors="coerce")
        if pd.notna(entradas_interestaduais) and entradas_interestaduais > 0 and pd.notna(entradas_nao_seladas):
            razao = float(entradas_nao_seladas) / float(entradas_interestaduais)
            partes.append(f"<b>Razão não seladas / interestaduais:</b> {formatar_numero_analitico(razao)}")
            if regra == "R15":
                if razao <= 0.10:
                    faixa = "Faixa 1 (> 0 e <= 0,10) — peso 1"
                elif razao <= 0.25:
                    faixa = "Faixa 2 (> 0,10 e <= 0,25) — peso 2"
                elif razao <= 0.50:
                    faixa = "Faixa 3 (> 0,25 e <= 0,50) — peso 3"
                elif razao <= 0.75:
                    faixa = "Faixa 4 (> 0,50 e <= 0,75) — peso 4"
                elif razao < 0.90:
                    faixa = "Faixa 5 (> 0,75 e < 0,90) — peso 5"
                elif razao < 1:
                    faixa = "Faixa 6 (>= 0,90 e < 1) — peso 6"
                else:
                    faixa = "Limite superior da regra parcial"
                partes.append(f"<b>Faixa de selagem:</b> {faixa}")
            elif regra == "R16":
                partes.append("<b>Faixa de selagem:</b> Integralmente não seladas — peso 7")

    if not partes:
        return "Sem evidência mapeada na saída atual."
    return "<br>".join(partes)

def normalizar_cnpj_texto(valor: str) -> str:
    if valor is None:
        return ""
    # Elimina ".0" espúrio de floats e preserva zeros à esquerda com zfill(14)
    try:
        digitos = "".join(ch for ch in str(valor) if ch.isdigit() or ch == ".")
        digitos = "".join(ch for ch in str(int(float(digitos))) if ch.isdigit())
    except (ValueError, TypeError):
        digitos = "".join(ch for ch in str(valor) if ch.isdigit())
    return digitos.zfill(14) if 11 <= len(digitos) <= 13 else digitos

def formatar_cnpj(valor) -> str:
    c = normalizar_cnpj_texto(valor)
    if len(c) != 14:
        return str(valor) if valor is not None else ""
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"

def valor_linha(linha, coluna, default="Não informado"):
    try:
        if coluna in linha.index:
            valor = linha[coluna]
            if pd.isna(valor):
                return default
            return valor
        return default
    except Exception:
        return default

def badge_risco(valor: str) -> str:
    v = str(valor).strip().lower()
    mapa_classes = {
        "baixo": ("risco-baixo", "Baixo"),
        "médio": ("risco-medio", "Médio"),
        "medio": ("risco-medio", "Médio"),
        "moderado": ("risco-moderado", "Moderado"),
        "alto": ("risco-alto", "Alto"),
        "muito alto": ("risco-muito-alto", "Muito Alto"),
        "crítico": ("risco-critico", "Crítico"),
        "critico": ("risco-critico", "Crítico"),
    }
    classe, texto = mapa_classes.get(v, ("", str(valor)))
    if not classe:
        return str(valor)
    return f'<span class="farol-badge-risk {classe}"><span class="dot"></span>{texto}</span>'

def extrair_regras_acionadas(texto):
    if texto is None or pd.isna(texto):
        return []
    bruto = str(texto).replace(";", ",").replace("|", ",")
    partes = [p.strip() for p in bruto.split(",") if p.strip()]
    regras = []
    vistos = set()
    regras_validas = set(REGRAS_ATIVAS)
    for p in partes:
        codigo = p.upper().strip()
        if codigo and codigo in regras_validas and codigo not in vistos:
            vistos.add(codigo)
            regras.append(codigo)
    return regras

def renderizar_tabela_html(df: pd.DataFrame):
    if df.empty:
        st.info("Sem dados para exibir.")
        return
    html = df.to_html(index=False, classes="farol-table", border=0, escape=False)
    st.markdown(f'<div class="farol-table-wrap">{html}</div>', unsafe_allow_html=True)

def construir_resumo_estruturado(linha: pd.Series) -> str:
    razao = valor_linha(linha, "DSC_RAZAO_SOCIAL")
    cnpj = formatar_cnpj(valor_linha(linha, "COD_CNPJ", ""))
    risco = valor_linha(linha, "nivel_risco")
    tipologia = valor_linha(linha, "tipologia_principal")
    qtd_regras = formatar_inteiro(valor_linha(linha, "qtd_regras_acionadas", 0))
    idx_farol = formatar_decimal(valor_linha(linha, "indice_geral_farol", 0))
    idx_op = formatar_decimal(valor_linha(linha, "indice_operacional", 0))
    idx_fin = formatar_decimal(valor_linha(linha, "indice_financeiro", 0))
    idx_fis = formatar_decimal(valor_linha(linha, "indice_fiscal", 0))
    municipio = valor_linha(linha, "C_DSC_MUNICIPIO")
    orgao = valor_linha(linha, "DSC_ORGAO_LOCAL")
    justificativa = valor_linha(linha, "justificativa_resumida", "")

    return f"""
<div class="farol-reading-card">
    <div class="farol-section-title">Resumo executivo do contribuinte</div>
    <div class="farol-section-subtitle">Leitura sintética do caso com foco em risco, tipologia e direcionamento operacional.</div>

<ul>
    <li><b>Contribuinte analisado:</b> {razao} — CNPJ {cnpj}.</li>
    <li><b>Diagnóstico geral:</b> nível de risco <b>{risco}</b>, tipologia principal <b>{tipologia}</b> e índice FAROL de <b>{idx_farol}</b>.</li>
    <li><b>Pressão por regras:</b> {qtd_regras} regras acionadas no recorte individual.</li>
    <li><b>Leitura dimensional:</b> operacional {idx_op}, financeiro {idx_fin} e fiscal {idx_fis}.</li>
    <li><b>Localização operacional:</b> município <b>{municipio}</b> e órgão local <b>{orgao}</b>.</li>
</ul>

<div class="farol-reading-small">
<b>Leitura do caso:</b> a combinação entre risco, tipologia e índices dimensionais indica onde a análise deve se concentrar primeiro. Em especial, a justificativa resumida do motor ajuda a orientar a abertura inicial do caso.<br><br>
<b>Justificativa sintetizada:</b> {justificativa if str(justificativa).strip() else "Não informada."}
</div>
</div>
""".strip()

def construir_leitura_radar(linha: pd.Series):
    op = float(pd.to_numeric(valor_linha(linha, "indice_operacional", 0), errors="coerce"))
    fin = float(pd.to_numeric(valor_linha(linha, "indice_financeiro", 0), errors="coerce"))
    fis = float(pd.to_numeric(valor_linha(linha, "indice_fiscal", 0), errors="coerce"))

    mapa = {
        "Operacional": op,
        "Financeiro": fin,
        "Fiscal": fis,
    }
    maior_eixo = max(mapa, key=mapa.get)
    menor_eixo = min(mapa, key=mapa.get)
    amplitude = max(mapa.values()) - min(mapa.values())

    if amplitude >= 3:
        perfil = "Perfil concentrado, com assimetria relevante entre as dimensões"
    elif amplitude >= 1.5:
        perfil = "Perfil moderadamente desequilibrado entre os eixos"
    else:
        perfil = "Perfil relativamente equilibrado entre as dimensões"

    return maior_eixo, menor_eixo, perfil

def construir_grafico_radar(linha: pd.Series):
    categorias = ["Operacional", "Financeiro", "Fiscal"]
    valores = [
        float(pd.to_numeric(valor_linha(linha, "indice_operacional", 0), errors="coerce")),
        float(pd.to_numeric(valor_linha(linha, "indice_financeiro", 0), errors="coerce")),
        float(pd.to_numeric(valor_linha(linha, "indice_fiscal", 0), errors="coerce")),
    ]

    categorias_fechadas = categorias + [categorias[0]]
    valores_fechados = valores + [valores[0]]

    maximo = max(5, math.ceil(max(valores_fechados) if valores_fechados else 5))

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=valores_fechados,
            theta=categorias_fechadas,
            fill="toself",
            line=dict(color="#60a5fa", width=3),
            fillcolor="rgba(96, 165, 250, 0.22)",
            marker=dict(size=7, color="#93c5fd"),
            hovertemplate="<b>%{theta}</b><br>Índice: %{r:.2f}<extra></extra>",
            name="Índices",
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e5e7eb"),
        margin=dict(l=30, r=30, t=30, b=30),
        showlegend=False,
        polar=dict(
            bgcolor="rgba(15,23,42,0.18)",
            radialaxis=dict(
                visible=True,
                range=[0, maximo],
                tickfont=dict(color="#cbd5e1"),
                gridcolor="rgba(148,163,184,0.12)",
                linecolor="rgba(148,163,184,0.18)",
            ),
            angularaxis=dict(
                tickfont=dict(color="#e5e7eb", size=12),
                gridcolor="rgba(148,163,184,0.10)",
                linecolor="rgba(148,163,184,0.18)",
            ),
        ),
    )
    return fig

def montar_dados_cadastrais(linha: pd.Series) -> pd.DataFrame:
    campos = [
        ("Razão Social", valor_linha(linha, "DSC_RAZAO_SOCIAL")),
        ("CNPJ", formatar_cnpj(valor_linha(linha, "COD_CNPJ", ""))),
        ("CGF", valor_linha(linha, "COD_CGF")),
        ("Situação Atual", valor_linha(linha, "SITUAÇÃO ATUAL", valor_linha(linha, "DSC_SIT_ATU_CONTRIBUINTE"))),
        ("Município", valor_linha(linha, "C_DSC_MUNICIPIO")),
        ("Órgão Local", valor_linha(linha, "DSC_ORGAO_LOCAL")),
        ("Segmento", valor_linha(linha, "DSC_SEGMENTO")),
        ("Regime", valor_linha(linha, "DSC_REGIME_REC_CONTRIBUINTE")),
        ("CNAE Principal", valor_linha(linha, "COD_CNAE_PRINC_CONTRIBUINTE")),
        ("Descrição CNAE", valor_linha(linha, "DSC_CNAE_PRINC_CONTRIBUINTE")),
        ("Código do Contador", valor_linha(linha, "COD_CONTADOR")),
        ("Nome do Contador", valor_linha(linha, "NOM_CONTADOR")),
        ("CRC do Contador", valor_linha(linha, "NUM_CRC_CONTADOR")),
        ("Início de Atividade", valor_linha(linha, "INICIO_ATIVIDADE")),
        ("Decreto", valor_linha(linha, "DECRETO")),
        ("Diligência", valor_linha(linha, "DILIGENCIA")),
        ("Dias para Saída", valor_linha(linha, "DIAS_PARA_SAIDA")),
        ("Primeiro Doc. Fiscal de Saída", valor_linha(linha, "DAT_PRIMEIRO_DOC_FISCAL_SAIDA")),
        ("Último Doc. Fiscal de Saída", valor_linha(linha, "DAT_ULTIMO_DOC_FISCAL_SAIDA")),
        ("Primeira NFe de Entrada", valor_linha(linha, "DAT_PRIMEIRA_NFE_ENTRADA")),
        ("Última NFe de Entrada", valor_linha(linha, "DAT_ULTIMA_NFE_ENTRADA")),
    ]
    campos_filtrados = []
    for campo, valor in campos:
        if valor is None:
            continue
        texto = str(valor).strip()
        if texto == "" or texto.lower() == "nan":
            continue
        campos_filtrados.append((campo, valor))
    return pd.DataFrame(campos_filtrados, columns=["Campo", "Valor"])

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
        <h1>🔎 Consulta do Contribuinte</h1>
        <p>
            Ficha analítica individual do FAROL para leitura consolidada do contribuinte,
            com indicadores, radar dimensional, regras acionadas, justificativa e dados cadastrais.
        </p>
        <div class="farol-chip-row">
            <span class="farol-chip">Visão 360</span>
            <span class="farol-chip">Radar incorporado</span>
            <span class="farol-chip">Análise individual</span>
            <span class="farol-chip">Leitura operacional</span>
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

# =========================
# BUSCA
# =========================
st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Localizar contribuinte</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="farol-section-subtitle">Pesquise diretamente pelo CNPJ ou selecione o contribuinte a partir de um recorte assistido da base.</div>',
    unsafe_allow_html=True,
)

prefill_cnpj = ""
try:
    qp_cnpj = st.query_params.get("cnpj", "")
    if isinstance(qp_cnpj, list):
        qp_cnpj = qp_cnpj[0] if qp_cnpj else ""
    prefill_cnpj = normalizar_cnpj_texto(qp_cnpj)
except Exception:
    prefill_cnpj = ""

if not prefill_cnpj:
    for chave in ["consulta_cnpj_input", "cnpj_consulta_preselecionado", "cnpj_consulta", "farol_cnpj_inicial"]:
        valor = st.session_state.get(chave, "")
        valor = normalizar_cnpj_texto(valor)
        if valor:
            prefill_cnpj = valor
            break

if prefill_cnpj:
    st.session_state["consulta_modo_busca"] = "Digitar CNPJ"
    st.session_state["consulta_cnpj_input"] = prefill_cnpj

modo_busca = st.radio(
    "Forma de busca",
    ["Digitar CNPJ", "Selecionar da base"],
    horizontal=True,
    index=0,
    key="consulta_modo_busca",
)

linha = None
cnpj_consulta = ""

if modo_busca == "Digitar CNPJ":
    c1, c2 = st.columns([1.3, 2.0])
    with c1:
        cnpj_digitado = st.text_input("CNPJ", placeholder="Digite apenas números ou o CNPJ formatado", key="consulta_cnpj_input")
    with c2:
        st.caption("A busca localiza o contribuinte a partir do CNPJ informado na base consolidada do FAROL.")
    if cnpj_digitado.strip():
        cnpj_consulta = normalizar_cnpj_texto(cnpj_digitado)
        encontrado = buscar_contribuinte(semaforo, cnpj_consulta)
        if encontrado is not None:
            linha = encontrado
        else:
            st.warning("CNPJ não encontrado na base FAROL.")

else:
    f1, f2, f3 = st.columns([1.15, 1.15, 1.7])

    municipios = ["Todos"]
    if "C_DSC_MUNICIPIO" in semaforo.columns:
        municipios += sorted(semaforo["C_DSC_MUNICIPIO"].dropna().astype(str).unique().tolist())

    riscos = ["Todos"]
    if "nivel_risco" in semaforo.columns:
        riscos += sorted(semaforo["nivel_risco"].dropna().astype(str).unique().tolist())

    orgaos = ["Todos"]
    if "DSC_ORGAO_LOCAL" in semaforo.columns:
        orgaos += sorted(semaforo["DSC_ORGAO_LOCAL"].dropna().astype(str).unique().tolist())

    municipio_sel = f1.selectbox("Município", municipios, index=0)
    risco_sel = f2.selectbox("Nível de risco", riscos, index=0)
    orgao_sel = f3.selectbox("Órgão local", orgaos, index=0)

    base_filtrada = semaforo.copy()
    if municipio_sel != "Todos" and "C_DSC_MUNICIPIO" in base_filtrada.columns:
        base_filtrada = base_filtrada[base_filtrada["C_DSC_MUNICIPIO"].astype(str) == municipio_sel]
    if risco_sel != "Todos" and "nivel_risco" in base_filtrada.columns:
        base_filtrada = base_filtrada[base_filtrada["nivel_risco"].astype(str) == risco_sel]
    if orgao_sel != "Todos" and "DSC_ORGAO_LOCAL" in base_filtrada.columns:
        base_filtrada = base_filtrada[base_filtrada["DSC_ORGAO_LOCAL"].astype(str) == orgao_sel]

    base_filtrada = base_filtrada.copy()
    base_filtrada["__rotulo__"] = (
        base_filtrada["DSC_RAZAO_SOCIAL"].astype(str)
        + " — "
        + base_filtrada["COD_CNPJ"].astype(str)
    ) if {"DSC_RAZAO_SOCIAL", "COD_CNPJ"}.issubset(base_filtrada.columns) else base_filtrada.index.astype(str)

    if base_filtrada.empty:
        st.info("Nenhum contribuinte foi encontrado para o recorte selecionado.")
    else:
        rotulo_sel = st.selectbox(
            "Contribuinte",
            base_filtrada["__rotulo__"].tolist(),
            index=0,
        )
        linha_df = base_filtrada[base_filtrada["__rotulo__"] == rotulo_sel].head(1)
        if not linha_df.empty:
            linha = linha_df.iloc[0]
            cnpj_consulta = normalizar_cnpj_texto(str(valor_linha(linha, "COD_CNPJ", "")))

st.markdown('</div>', unsafe_allow_html=True)

if linha is None:
    st.info("Selecione um contribuinte para exibir a ficha analítica individual.")
    st.stop()

# =========================
# IDENTIDADE
# =========================
razao = valor_linha(linha, "DSC_RAZAO_SOCIAL")
cnpj_fmt = formatar_cnpj(valor_linha(linha, "COD_CNPJ", ""))
tipologia = valor_linha(linha, "tipologia_principal")
risco = valor_linha(linha, "nivel_risco")

st.markdown(
f"""<div class="farol-identity-card">
<div class="farol-identity-top" style="align-items:flex-start;">
<div style="display:flex; flex-direction:column; gap:0.45rem;">
<div class="farol-identity-title" style="font-size:2rem; line-height:1.15; font-weight:800;">{razao}</div>
<div class="farol-identity-subtitle" style="font-size:1.45rem; line-height:1.35; font-weight:700;">CNPJ {cnpj_fmt}</div>
</div>
</div>
</div>""",
unsafe_allow_html=True,
)

# =========================
# KPIS
# =========================
_idx_farol  = formatar_decimal(valor_linha(linha, "indice_geral_farol", 0))
_idx_oper   = formatar_decimal(valor_linha(linha, "indice_operacional", 0))
_idx_fin    = formatar_decimal(valor_linha(linha, "indice_financeiro", 0))
_idx_fisc   = formatar_decimal(valor_linha(linha, "indice_fiscal", 0))
_qtd_regras = formatar_inteiro(valor_linha(linha, "qtd_regras_acionadas", 0))
_dias_saida = formatar_dias_para_saida(valor_linha(linha, "DIAS_PARA_SAIDA", None))

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(_kpi_card(
        "Índice FAROL", _idx_farol,
        f"Operacional: {_idx_oper}",
        "primary", "📈",
        "Índice geral de risco do contribuinte, combinando as três dimensões do FAROL.",
    ), unsafe_allow_html=True)
with k2:
    _accent_risco = "danger" if str(risco).strip().lower() in ("crítico", "critico", "muito alto") else "warning" if str(risco).strip().lower() == "alto" else "info"
    st.markdown(_kpi_card(
        "Nível de Risco", str(risco),
        f"Índice FAROL: {_idx_farol}",
        _accent_risco, "🚨",
        "Classificação de risco do contribuinte com base no índice geral FAROL.",
    ), unsafe_allow_html=True)
with k3:
    st.markdown(_kpi_card(
        "Tipologia Principal", str(tipologia),
        f"{_qtd_regras} regras acionadas",
        "warning", "🎯",
        "Principal padrão de risco identificado pelo motor FAROL para este contribuinte.",
    ), unsafe_allow_html=True)
with k4:
    st.markdown(_kpi_card(
        "Prazo até Saída", _dias_saida,
        f"Financeiro: {_idx_fin} · Fiscal: {_idx_fisc}",
        "info", "⏱️",
        "Dias restantes até o contribuinte sair do campo de visão do FAROL.",
    ), unsafe_allow_html=True)

# =========================
# ABAS
# =========================
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs(
    ["Resumo executivo", "Radar", "Regras acionadas", "Justificativa", "Dados cadastrais", "Indicadores numéricos"]
)

with aba1:
    st.markdown(construir_resumo_estruturado(linha), unsafe_allow_html=True)

with aba2:
    maior_eixo, menor_eixo, perfil = construir_leitura_radar(linha)

    st.markdown('<div class="farol-card">', unsafe_allow_html=True)
    st.markdown('<div class="farol-section-title">Radar dimensional</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="farol-section-subtitle">Leitura comparativa dos índices operacional, financeiro e fiscal do contribuinte.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="farol-mini-stat-grid">
            <div class="farol-mini-stat">
                <div class="farol-mini-stat-label">Maior eixo</div>
                <div class="farol-mini-stat-value">{maior_eixo}</div>
            </div>
            <div class="farol-mini-stat">
                <div class="farol-mini-stat-label">Menor eixo</div>
                <div class="farol-mini-stat-value">{menor_eixo}</div>
            </div>
            <div class="farol-mini-stat">
                <div class="farol-mini-stat-label">Perfil</div>
                <div class="farol-mini-stat-value">{perfil}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    fig = construir_grafico_radar(linha)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f"""
        <div class="farol-reading-card">
            <div class="farol-section-title">Interpretação do radar</div>
            <div class="farol-reading-small">
                O radar mostra onde a pressão analítica se concentra. Neste caso, o maior eixo é <b>{maior_eixo}</b> e o menor eixo é <b>{menor_eixo}</b>, sugerindo <b>{perfil.lower()}</b>.
                Essa leitura ajuda a direcionar o aprofundamento do caso para a dimensão mais sensível e a calibrar o peso relativo das demais.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

with aba3:
    regras = extrair_regras_acionadas(valor_linha(linha, "regras_acionadas", ""))
    st.markdown('<div class="farol-card">', unsafe_allow_html=True)
    st.markdown('<div class="farol-section-title">Regras acionadas</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="farol-section-subtitle">Lista das regras identificadas para o contribuinte, com leitura mais amigável e aderente ao FAROL.</div>',
        unsafe_allow_html=True,
    )

    if not regras:
        st.info("Nenhuma regra acionada foi informada para este contribuinte.")
    else:
        chips = []
        for regra in regras:
            nome = REGRAS_NOMES.get(regra, "Regra não mapeada")
            chips.append(f'<span class="farol-rule-chip">{regra} <small>{nome}</small></span>')
        st.markdown(f'<div class="farol-rule-chip-wrap">{"".join(chips)}</div>', unsafe_allow_html=True)

        detalhes = []
        for regra in regras:
            detalhes.append(
                {
                    "Regra": regra,
                    "Nome": REGRAS_NOMES.get(regra, "Regra não mapeada"),
                    "Descrição": REGRAS_DESC.get(regra, "Descrição não mapeada."),
                    "Campos que influenciaram": construir_evidencias_regra(regra, linha),
                }
            )
        st.markdown(
            '<div class="farol-section-subtitle" style="margin-top:0.9rem;">Além da descrição da regra, a tabela abaixo mostra os principais campos da saída FAROL que ajudam a explicar o acionamento.</div>',
            unsafe_allow_html=True,
        )
        renderizar_tabela_html(pd.DataFrame(detalhes))
    st.markdown('</div>', unsafe_allow_html=True)

with aba4:
    justificativa = str(valor_linha(linha, "justificativa_resumida", "")).strip()
    if not justificativa:
        justificativa = "Não informada."

    st.markdown(
        f"""
        <div class="farol-reading-card">
            <div class="farol-section-title">Justificativa resumida do motor</div>
            <div class="farol-section-subtitle">Texto interpretativo gerado a partir das regras e índices do contribuinte.</div>
            <div class="farol-reading-small">
                {justificativa}
                <br><br>
                <b>Leitura operacional sugerida:</b> usar esta justificativa como ponto de partida da análise individual, confrontando o texto do motor com as regras acionadas, a tipologia principal e o radar dimensional para verificar convergência do caso.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with aba5:
    cad = montar_dados_cadastrais(linha)
    renderizar_tabela_html(cad)

with aba6:
    st.markdown('<div class="farol-section-title">Indicadores numéricos</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="farol-section-subtitle">Todos os campos quantitativos do contribuinte na base FAROL, '
        'organizados por grupo. Útil como conferência e visão completa dos dados disponíveis.</div>',
        unsafe_allow_html=True,
    )

    def _num(col, default=None, inteiro=False, data=False):
        v = valor_linha(linha, col, default)
        if data:
            try:
                import pandas as _pd
                ts = _pd.to_datetime(v, errors="coerce")
                if _pd.notna(ts):
                    return ts.strftime("%Y-%m-%d")
            except Exception:
                pass
            s = str(v).strip() if v is not None else ""
            return s[:10] if len(s) >= 10 else (s if s else "Não disponível")
        try:
            f = float(v)
            if inteiro:
                return f"{int(f):,}".replace(",", ".")
            return formatar_numero_analitico(f)
        except Exception:
            return str(v) if v is not None else "Não disponível"

    def _grupo_indicadores(titulo, campos):
        """Renderiza um grupo de indicadores como tabela HTML.
        Cada entrada em campos pode ser (rotulo, coluna) ou
        (rotulo, coluna, tipo) onde tipo é "int", "data" ou "val" (padrão).
        """
        linhas_html = ""
        for entrada in campos:
            rotulo, coluna = entrada[0], entrada[1]
            tipo = entrada[2] if len(entrada) > 2 else "val"
            val = _num(coluna, inteiro=(tipo == "int"), data=(tipo == "data"))
            linhas_html += f'<tr><td style="padding:.4rem .8rem;color:#94a3b8;font-size:.85rem;">{rotulo}</td><td style="padding:.4rem .8rem;font-weight:600;text-align:right;">{val}</td></tr>'
        return (
            f'<div style="margin-bottom:1.2rem;">'
            f'<div class="farol-section-title" style="font-size:.95rem;margin-bottom:.5rem;">{titulo}</div>'
            f'<table style="width:100%;border-collapse:collapse;background:rgba(15,23,42,.45);border-radius:8px;overflow:hidden;">'
            f'<tbody>{linhas_html}</tbody></table></div>'
        )

    _col1, _col2 = st.columns(2)

    with _col1:
        # ── Entradas NF-e (total recebido) ──────────────────────────────
        st.markdown(_grupo_indicadores("🔵 Entradas NF-e (total recebido)", [
            ("Entradas totais (R$)",            "ENTRADAS"),
            ("Entradas dentro do CE (R$)",      "ENTRADAS_DENTRO_CE"),
            ("Entradas fora do CE (R$)",        "ENTRADAS_FORA_CE"),
            ("Entradas não seladas (R$)",       "ENTRADAS_NAO_SELADAS"),
            ("Qtd. documentos fiscais",         "Qtd_Doc_Fiscais_Entrada",           "int"),
            ("Valor médio das notas (R$)",      "Vr_Medio_Notas_Entrada"),
            ("Qtd. emitentes distintos",        "Qtd_Emitentes_Distintos_Entrada",   "int"),

        ]), unsafe_allow_html=True)

        # ── Compras (subconjunto de Entradas) ───────────────────────────
        st.markdown(_grupo_indicadores("🔵 Compras (subconjunto de Entradas)", [
            ("Compras (R$)",                    "COMPRAS"),
            ("Compras dentro do CE (R$)",       "COMPRAS_DENTRO_CE"),
            ("Compras fora do CE (R$)",         "COMPRAS_FORA_CE"),
            ("Qtd. documentos fiscais",         "Qtd_Doc_Fiscais_Compra",            "int"),
            ("Valor médio das notas (R$)",      "Vr_Medio_Notas_Compra"),
            ("Qtd. emitentes distintos",        "Qtd_Emitentes_Distintos_Compra",    "int"),
        ]), unsafe_allow_html=True)

        # ── Saídas NF-e (todas as NF-e emitidas) ───────────────────────
        st.markdown(_grupo_indicadores("🟢 Saídas NF-e (todas as NF-e emitidas)", [
            ("Saídas NF-e (R$)",                "Saidas"),
            ("Qtd. documentos fiscais",         "Qtd_Documentos_Fiscais_Saida",      "int"),
            ("Valor médio das notas (R$)",      "Vlr_Medio_Notas_Saidas"),
            ("Qtd. destinatários distintos",    "Qtd_Destinatarios_Distintos_Saidas", "int"),

        ]), unsafe_allow_html=True)

        # ── Vendas NF-e (subconjunto comercial de Saídas) ───────────────
        st.markdown(_grupo_indicadores("🟢 Vendas NF-e (subconjunto comercial de Saídas)", [
            ("Vendas NF-e (R$)",                "Vendas"),
            ("Qtd. documentos fiscais",         "Qtd_Documentos_Fiscais_Vendas",     "int"),
            ("Valor médio das notas (R$)",      "Vlr_Medio_Notas_Vendas"),
            ("Qtd. destinatários distintos",    "Qtd_Destinatarios_Distintos_Vendas", "int"),
        ]), unsafe_allow_html=True)

        # ── Totais consolidados (NF-e + NFC-e + CT-e) ───────────────────
        st.markdown(_grupo_indicadores("🟢 Totais consolidados (NF-e + NFC-e + CT-e)", [
            ("Saídas totais (R$)",              "Saidas Totais"),
            ("Vendas totais (R$)",              "Vendas Totais"),
        ]), unsafe_allow_html=True)

        # ── NFC-e ────────────────────────────────────────────────────────
        st.markdown(_grupo_indicadores("🟡 NFC-e (Nota Fiscal ao Consumidor)", [
            ("NFC-e total (R$)",                "NFCE"),
            ("Qtd. documentos NFC-e",           "Qtd_Doc_Fiscais_NFCE",              "int"),
            ("Valor médio NFC-e (R$)",          "Vlr_Medio_Notas_NFCE"),
            ("Qtd. destinatários distintos",    "Qtd_Destinatarios_Distintos_NFCE",  "int"),

        ]), unsafe_allow_html=True)

        # ── CT-e ─────────────────────────────────────────────────────────
        st.markdown(_grupo_indicadores("🚚 CT-e (Conhecimento de Transporte)", [
            ("CT-e total (R$)",                 "CTE"),
            ("Qtd. documentos CT-e",            "Qtd_Documentos_Fiscais_CTE",        "int"),
            ("Valor médio CT-e (R$)",           "VLR_MEDIO_CTE"),

        ]), unsafe_allow_html=True)

        # ── CF-e ─────────────────────────────────────────────────────────
        st.markdown(_grupo_indicadores("🟠 CF-e (Cupom Fiscal Eletrônico)", [
            ("CF-e total (R$)",                 "CFE"),
            ("Qtd. documentos CF-e",            "Qtd_Doc_Fiscais_CFE",               "int"),
            ("Valor médio CF-e (R$)",           "Vlr_Medio_Cupom_CFE"),

        ]), unsafe_allow_html=True)

    with _col2:
        # ── Financeiro ───────────────────────────────────────────────────
        st.markdown(_grupo_indicadores("💰 Financeiro / DIMP / Arrecadação", [
            ("VR DIMP (R$)",                    "VR_DIMP"),
            ("Arrecadação (R$)",                "ARRECADACAO"),
        ]), unsafe_allow_html=True)

        # ── SPED ─────────────────────────────────────────────────────────
        st.markdown(_grupo_indicadores("🔴 SPED", [
            ("SPED Saídas (R$)",                "SPED_Saídas"),
            ("SPED Entradas (R$)",              "SPED_Entradas"),
            ("Omissão SPED",                    "Omissão SPED (Flag)"),
        ]), unsafe_allow_html=True)

        # ── Outras entradas ──────────────────────────────────────────────
        st.markdown(_grupo_indicadores("⚪ Outras entradas", [
            ("Outras entradas (R$)",            "Outras Entradas"),
            ("Qtd. doc. outras entradas",       "Qtd_Documentos_Fiscais_Outras_Entradas", "int"),
            ("Valor médio outras entradas (R$)","Vlr_Medio_Notas_Outras_Entradas"),
            ("Qtd. emitentes distintos",        "Qtd_Emitentes_Distintos_Outras_Entradas", "int"),
        ]), unsafe_allow_html=True)

        # ── Outras compras ───────────────────────────────────────────────
        st.markdown(_grupo_indicadores("⚪ Outras compras", [
            ("Outras compras (R$)",             "Outras Compras"),
            ("Qtd. doc. outras compras",        "Qtd_Documentos_Fiscais_Outras_Compras",  "int"),
            ("Valor médio outras compras (R$)", "Vlr_Medio_Notas_Outras_Compras"),
            ("Qtd. emitentes distintos",        "Qtd_Emitentes_Distintos_Outras_Compras", "int"),
        ]), unsafe_allow_html=True)

        # ── Índices do motor ─────────────────────────────────────────────
        st.markdown(_grupo_indicadores("📊 Índices do motor FAROL", [
            ("Índice geral FAROL",              "indice_geral_farol"),
            ("Índice operacional",              "indice_operacional"),
            ("Índice financeiro",               "indice_financeiro"),
            ("Índice fiscal",                   "indice_fiscal"),
            ("Qtd. regras acionadas",           "qtd_regras_acionadas",              "int"),
            ("Dias para saída",                 "DIAS_PARA_SAIDA",                   "int"),
        ]), unsafe_allow_html=True)