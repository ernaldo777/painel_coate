import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import pandas as pd
import streamlit as st
from projetos_especiais.farol.farol_config import PAGE_TITLES
from coate_styles import aplicar_estilos, loading
from coate_auth import exigir_acesso

from projetos_especiais.farol.farol_core import load_data, filtrar_base, build_ranking_fiscalizacao
from projetos_especiais.farol.farol_rules_catalog import RULE_TIPOLOGIAS
from projetos_especiais.farol.farol_metadata import banner_atualizacao


TIPOLOGIAS_CANONICAS = sorted({str(v) for v in RULE_TIPOLOGIAS.values() if str(v).strip()})

TIPOLOGIA_ALIASES = {
    "saída sem entrada": "Saída Sem Entrada",
    "saida sem entrada": "Saída Sem Entrada",
    "entrada sem saída": "Entrada Sem Saída",
    "entrada sem saida": "Entrada Sem Saída",
    "movimentação financeira sem documento fiscal": "Movimentação financeira sem documento fiscal",
    "movimentacao financeira sem documento fiscal": "Movimentação financeira sem documento fiscal",
    "documento fiscal sem movimentação financeira": "Documento fiscal sem movimentação financeira",
    "documento fiscal sem movimentacao financeira": "Documento fiscal sem movimentação financeira",
    "omissão de sped": "Omissão de SPED",
    "omissao de sped": "Omissão de SPED",
    "entradas interestaduais não seladas": "Entradas interestaduais não seladas",
    "entradas interestaduais nao seladas": "Entradas interestaduais não seladas",
    "arrecadação zerada com movimentação relevante": "Arrecadação zerada com movimentação relevante",
    "arrecadacao zerada com movimentacao relevante": "Arrecadação zerada com movimentação relevante",
}


def normalizar_tipologia_catalogo(valor):
    if pd.isna(valor):
        return valor
    texto = str(valor).strip()
    if not texto:
        return texto
    return TIPOLOGIA_ALIASES.get(texto.lower(), texto)


def compatibilizar_ranking_com_catalogo(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    base = df.copy()

    if "tipologia_principal" in base.columns:
        base["tipologia_principal"] = base["tipologia_principal"].map(normalizar_tipologia_catalogo)

    return base




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


def truncar_texto(texto, limite=95):
    texto = "" if pd.isna(texto) else str(texto)
    if len(texto) <= limite:
        return texto
    return texto[:limite].rstrip() + "..."

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


def _risco_predominante_info(df: pd.DataFrame):
    if df is None or df.empty or "nivel_risco" not in df.columns:
        return "Não identificado", 0.0
    serie = df["nivel_risco"].fillna("Não informado").astype(str)
    if serie.empty:
        return "Não identificado", 0.0
    dominante = serie.value_counts().idxmax()
    qtd = int((serie == dominante).sum())
    return dominante, _percentual(qtd, len(serie))


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

    return f'<span class="badge-risco {classe}"><span class="dot"></span>{texto}</span>'


def badge_prioridade(rank):
    try:
        rank = int(rank)
    except Exception:
        return '<span class="farol-priority-badge priority-monitoramento">Monitoramento</span>'

    if rank <= 10:
        return '<span class="farol-priority-badge priority-maxima">Prioridade Máxima</span>'
    if rank <= 50:
        return '<span class="farol-priority-badge priority-alta">Prioridade Alta</span>'
    return '<span class="farol-priority-badge priority-monitoramento">Monitoramento</span>'


def badge_dias_para_saida(valor):
    try:
        dias = int(pd.to_numeric(valor, errors="coerce"))
    except Exception:
        return '<span class="farol-days-badge days-na">N/D</span>'

    if dias <= 30:
        classe = "days-critico"
    elif dias <= 90:
        classe = "days-alerta"
    else:
        classe = "days-ok"

    sufixo = "dia" if dias == 1 else "dias"
    return f'<span class="farol-days-badge {classe}">{dias} {sufixo}</span>'


def renderizar_tabela_html(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Sem dados para exibir.")
        return

    html = df.to_html(index=False, classes="farol-table", border=0, escape=False)

    for i in range(10):
        html = html.replace("<tr>", '<tr class="top10">', 1) if i < len(df) else html

    st.markdown(f'<div class="farol-table-wrap">{html}</div>', unsafe_allow_html=True)


def obter_dominante(df: pd.DataFrame, coluna: str, padrao="Não identificado"):
    if coluna not in df.columns or df.empty:
        return padrao
    serie = df[coluna].fillna("Não informado").astype(str)
    if serie.empty:
        return padrao
    return serie.value_counts().idxmax()


def gerar_leitura_executiva_ranking(df: pd.DataFrame) -> str:
    if df.empty:
        return """
<div class="farol-reading-card">
    <div class="farol-section-title">Leitura executiva do ranking</div>
    <div class="farol-section-subtitle">Síntese operacional do recorte atual.</div>
    <div class="farol-reading-small">Nenhum contribuinte foi encontrado para o recorte aplicado.</div>
</div>
""".strip()

    total = len(df)
    risco_top = obter_dominante(df, "nivel_risco")
    tipologia_top = obter_dominante(df, "tipologia_principal", "Não identificada")

    media_farol = float(pd.to_numeric(df.get("indice_geral_farol", 0), errors="coerce").fillna(0).mean())
    media_pri = float(pd.to_numeric(df.get("indice_prioridade_fiscalizacao", 0), errors="coerce").fillna(0).mean())
    media_regras = float(pd.to_numeric(df.get("qtd_regras_acionadas", 0), errors="coerce").fillna(0).mean())

    primeira_razao = "Não informada"
    if "DSC_RAZAO_SOCIAL" in df.columns and not df.empty:
        primeira_razao = str(df.iloc[0]["DSC_RAZAO_SOCIAL"])

    return f"""
<div class="farol-reading-card">
    <div class="farol-section-title">Leitura executiva do ranking</div>
    <div class="farol-section-subtitle">Síntese orientada à priorização analítica no recorte atual.</div>

<ul>
    <li><b>Recorte ativo:</b> {formatar_inteiro(total)} contribuintes priorizados.</li>
    <li><b>Padrão dominante:</b> risco predominante em <b>{risco_top}</b> e concentração principal no eixo operacional mais sensível do recorte.</li>
    <li><b>Pressão média do ranking:</b> Índice FAROL médio de <b>{formatar_decimal(media_farol)}</b>, índice de priorização média de <b>{formatar_decimal(media_pri)}</b> e média de <b>{formatar_decimal(media_regras)}</b> regras acionadas por contribuinte.</li>
</ul>

<div class="farol-reading-small">
<b>Leitura operacional:</b> o ranking atual já destaca no topo os casos com maior combinação de risco, prioridade analítica e sensibilidade operacional. O primeiro contribuinte exibido é <b>{primeira_razao}</b>, indicando o ponto inicial mais forte para aprofundamento.<br><br>
<b>Uso sugerido:</b> utilizar esta página para selecionar a fila de atuação e, em seguida, aprofundar os casos prioritários na Consulta do Contribuinte.
</div>
</div>
""".strip()


def construir_resumo_filtros(municipio, risco, tipologia, orgao_local, top_n, modo):
    tags = [
        f'<span class="farol-filter-tag"><b>Município:</b> {municipio}</span>',
        f'<span class="farol-filter-tag"><b>Risco:</b> {risco}</span>',
        f'<span class="farol-filter-tag"><b>Tipologia:</b> {tipologia}</span>',
        f'<span class="farol-filter-tag"><b>Órgão local:</b> {orgao_local}</span>',
        f'<span class="farol-filter-tag"><b>Itens/página:</b> {top_n}</span>',
        f'<span class="farol-filter-tag"><b>Modo:</b> {modo}</span>',
    ]
    return f'<div class="farol-filter-summary">{"".join(tags)}</div>'


def preparar_tabela_exibicao(ranking_filtrado: pd.DataFrame, itens_por_pagina: int, modo: str) -> pd.DataFrame:
    if ranking_filtrado.empty:
        return pd.DataFrame()

    colunas_base = [
        "ranking_fiscalizacao",
        "faixa_prioridade",
        "COD_CNPJ",
        "DSC_RAZAO_SOCIAL",
        "DSC_SEGMENTO",
        "DECRETO",
        "SITUAÇÃO ATUAL",
        "DIAS_PARA_SAIDA",
        "nivel_risco",
        "indice_geral_farol",
    ]
    colunas_analiticas = [
        "DILIGENCIA",
    ]

    colunas = colunas_base + (colunas_analiticas if modo == "Analítico" else [])
    colunas = [c for c in colunas if c in ranking_filtrado.columns]
    df = ranking_filtrado[colunas].head(itens_por_pagina).copy()

    renomear = {
        "ranking_fiscalizacao": "Ranking",
        "faixa_prioridade": "Faixa",
        "COD_CNPJ": "CNPJ",
        "DSC_RAZAO_SOCIAL": "Razão Social",
        "DSC_SEGMENTO": "Segmento",
        "DECRETO": "Decreto",
        "SITUAÇÃO ATUAL": "Situação Atual",
        "DIAS_PARA_SAIDA": "Dias para Saída",
        "nivel_risco": "Nível de Risco",
        "indice_geral_farol": "Índice FAROL",
        "DILIGENCIA": "Diligência",
    }
    df = df.rename(columns=renomear)

    if "Faixa" in df.columns:
        df["Faixa"] = df["Faixa"].map(badge_prioridade_por_valor)
    if "Nível de Risco" in df.columns:
        df["Nível de Risco"] = df["Nível de Risco"].map(badge_risco)
    if "Índice FAROL" in df.columns:
        df["Índice FAROL"] = pd.to_numeric(df["Índice FAROL"], errors="coerce").fillna(0).map(lambda x: f"{x:.2f}")
    if "Dias para Saída" in df.columns:
        df["Dias para Saída"] = df["Dias para Saída"].map(badge_dias_para_saida)
    return df


def gerar_leitura_executiva_ranking(df: pd.DataFrame) -> str:
    if df.empty:
        return """
<div class="farol-reading-card">
    <div class="farol-section-title">Leitura executiva do ranking</div>
    <div class="farol-section-subtitle">Síntese operacional do recorte atual.</div>
    <div class="farol-reading-small">Nenhum contribuinte foi encontrado para o recorte aplicado.</div>
</div>
""".strip()

    total = len(df)
    risco_top = obter_dominante(df, "nivel_risco")
    tipologia_top = obter_dominante(df, "tipologia_principal", "Não identificada")

    media_farol = float(pd.to_numeric(df.get("indice_geral_farol", 0), errors="coerce").fillna(0).mean())
    media_pri = float(pd.to_numeric(df.get("indice_prioridade_fiscalizacao", 0), errors="coerce").fillna(0).mean())
    media_regras = float(pd.to_numeric(df.get("qtd_regras_acionadas", 0), errors="coerce").fillna(0).mean())

    primeira_razao = "Não informada"
    if "DSC_RAZAO_SOCIAL" in df.columns and not df.empty:
        primeira_razao = str(df.iloc[0]["DSC_RAZAO_SOCIAL"])

    return f"""
<div class="farol-reading-card">
    <div class="farol-section-title">Leitura executiva do ranking</div>
    <div class="farol-section-subtitle">Síntese orientada à priorização analítica no recorte atual.</div>

<ul>
    <li><b>Recorte ativo:</b> {formatar_inteiro(total)} contribuintes priorizados.</li>
    <li><b>Padrão dominante:</b> risco predominante em <b>{risco_top}</b> e concentração principal no eixo operacional mais sensível do recorte.</li>
    <li><b>Pressão média do ranking:</b> Índice FAROL médio de <b>{formatar_decimal(media_farol)}</b>, índice de priorização média de <b>{formatar_decimal(media_pri)}</b> e média de <b>{formatar_decimal(media_regras)}</b> regras acionadas por contribuinte.</li>
</ul>

<div class="farol-reading-small">
<b>Leitura operacional:</b> o ranking atual já destaca no topo os casos com maior combinação de risco, prioridade analítica e sensibilidade operacional. O primeiro contribuinte exibido é <b>{primeira_razao}</b>, indicando o ponto inicial mais forte para aprofundamento.<br><br>
<b>Uso sugerido:</b> utilizar esta página para selecionar a fila de atuação e, em seguida, aprofundar os casos prioritários na Consulta do Contribuinte.
</div>
</div>
""".strip()


def construir_resumo_filtros(municipio, risco, tipologia, orgao_local, top_n, modo):
    tags = [
        f'<span class="farol-filter-tag"><b>Município:</b> {municipio}</span>',
        f'<span class="farol-filter-tag"><b>Risco:</b> {risco}</span>',
        f'<span class="farol-filter-tag"><b>Tipologia:</b> {tipologia}</span>',
        f'<span class="farol-filter-tag"><b>Órgão local:</b> {orgao_local}</span>',
        f'<span class="farol-filter-tag"><b>Itens/página:</b> {top_n}</span>',
        f'<span class="farol-filter-tag"><b>Modo:</b> {modo}</span>',
    ]
    return f'<div class="farol-filter-summary">{"".join(tags)}</div>'


def preparar_tabela_exibicao(ranking_filtrado: pd.DataFrame, itens_por_pagina: int, modo: str) -> pd.DataFrame:
    if ranking_filtrado.empty:
        return pd.DataFrame()

    if modo == "Executivo":
        colunas = [
            "ranking_fiscalizacao",
            "DSC_RAZAO_SOCIAL",
            "nivel_risco",
            "tipologia_principal",
            "indice_prioridade_fiscalizacao",
            "qtd_regras_acionadas",
            "justificativa_resumida",
        ]
    else:
        colunas = [
            "ranking_fiscalizacao",
            "COD_CNPJ",
            "DSC_RAZAO_SOCIAL",
            "indice_geral_farol",
            "indice_prioridade_fiscalizacao",
            "nivel_risco",
            "tipologia_principal",
            "qtd_regras_acionadas",
            "justificativa_resumida",
        ]

    colunas = [c for c in colunas if c in ranking_filtrado.columns]
    df = ranking_filtrado[colunas].head(itens_por_pagina).copy()

    if "ranking_fiscalizacao" in df.columns:
        df.insert(1, "faixa_prioridade", df["ranking_fiscalizacao"].map(badge_prioridade))

    renomear = {
        "ranking_fiscalizacao": "Ranking",
        "faixa_prioridade": "Faixa",
        "COD_CNPJ": "CNPJ",
        "DSC_RAZAO_SOCIAL": "Razão Social",
        "indice_geral_farol": "Índice FAROL",
        "indice_prioridade_fiscalizacao": "Índice Priorização",
        "nivel_risco": "Nível de Risco",
        "tipologia_principal": "Tipologia",
        "qtd_regras_acionadas": "Qtd Regras",
        "justificativa_resumida": "Justificativa",
    }
    df = df.rename(columns=renomear)

    for col in ["Índice FAROL", "Índice Priorização"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).map(lambda x: f"{x:.2f}")

    if "Nível de Risco" in df.columns:
        df["Nível de Risco"] = df["Nível de Risco"].map(badge_risco)

    if "Justificativa" in df.columns and modo == "Executivo":
        df["Justificativa"] = df["Justificativa"].map(lambda x: truncar_texto(x, 92))

    return df




def abrir_consulta_cnpj(cnpj: str):
    cnpj = "".join(ch for ch in str(cnpj) if ch.isdigit())
    if not cnpj:
        st.warning("CNPJ inválido para navegação à consulta.")
        return
    st.session_state["cnpj_consulta_preselecionado"] = cnpj
    st.session_state["cnpj_consulta"] = cnpj
    st.session_state["farol_cnpj_inicial"] = cnpj
    st.session_state["consulta_cnpj_input"] = cnpj
    st.session_state["consulta_modo_busca"] = "Digitar CNPJ"
    try:
        st.query_params["cnpj"] = cnpj
    except Exception:
        pass
    try:
        st.switch_page("pages/3_FAROL_Consulta_de_Contribuinte.py")
    except Exception:
        st.success(f"CNPJ {cnpj} preparado. Abra a página Consulta do Contribuinte para continuar.")


def renderizar_grade_operacional(df: pd.DataFrame):
    if df is None or df.empty:
        st.info("Sem dados para exibir.")
        return

    cabecalhos = [
        "Rankin\ng", "Faixa", "CNPJ", "Razão Social", "Segmento",
        "Situação Atual", "Dias para\nSaída", "Nível de Risco", "Índice\nFAROL", "Ação"
    ]
    larguras = [0.65, 1.95, 1.85, 2.85, 1.65, 1.55, 1.20, 1.20, 1.00, 1.15]

    st.markdown('<div class="farol-table-wrap">', unsafe_allow_html=True)
    cols = st.columns(larguras)
    for c, h in zip(cols, cabecalhos):
        c.markdown(f"**{h.replace(chr(10), '<br>')}**", unsafe_allow_html=True)

    for idx, (_, row) in enumerate(df.iterrows()):
        st.markdown("<hr style='border-color: rgba(148,163,184,0.10); margin: 0.35rem 0 0.55rem 0;'>", unsafe_allow_html=True)
        cols = st.columns(larguras)
        cnpj = str(row.get("COD_CNPJ", "")).replace('.0', '').strip()
        cols[0].markdown(f"**{int(row.get('ranking_fiscalizacao', idx + 1))}**")
        cols[1].markdown(badge_prioridade_por_valor(row.get("faixa_prioridade", "Monitoramento")), unsafe_allow_html=True)
        cols[2].markdown(f'<span class="farol-cnpj-cell">{cnpj}</span>', unsafe_allow_html=True)
        cols[3].markdown(str(row.get("DSC_RAZAO_SOCIAL", "")))
        cols[4].markdown(str(row.get("DSC_SEGMENTO", "")))
        situacao = row.get("SITUAÇÃO ATUAL", row.get("DSC_SIT_ATU_CONTRIBUINTE", ""))
        cols[5].markdown(truncar_texto("" if pd.isna(situacao) else str(situacao), 38))
        cols[6].markdown(badge_dias_para_saida(row.get("DIAS_PARA_SAIDA", "")), unsafe_allow_html=True)
        cols[7].markdown(badge_risco(row.get("nivel_risco", "")), unsafe_allow_html=True)
        idx_farol = pd.to_numeric(row.get("indice_geral_farol", 0), errors="coerce")
        cols[8].markdown(formatar_decimal(0 if pd.isna(idx_farol) else idx_farol))
        if cols[9].button("Consultar", key=f"consultar_cnpj_{idx}_{cnpj}", use_container_width=True):
            abrir_consulta_cnpj(cnpj)

    st.markdown('</div>', unsafe_allow_html=True)


def aplicar_estilo_ranking():
    st.markdown(
        """
        <style>

        /* --- BADGE DE RISCO COLORIDO --- */
        .badge-risco {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.38rem 0.78rem;
            border-radius: 999px;
            font-weight: 700;
            white-space: nowrap;
            font-size: 0.88rem;
        }

        .badge-risco .dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }

        .risco-baixo { background: rgba(187, 247, 208, 0.12); color: #dcfce7; border: 1px solid rgba(187, 247, 208, 0.20); }
        .risco-baixo .dot { background: #86efac; box-shadow: 0 0 8px rgba(134, 239, 172, 0.45); }

        .risco-medio { background: rgba(253, 230, 138, 0.12); color: #fef3c7; border: 1px solid rgba(253, 230, 138, 0.20); }
        .risco-medio .dot { background: #facc15; box-shadow: 0 0 8px rgba(250, 204, 21, 0.45); }

        .risco-moderado { background: rgba(45, 212, 191, 0.12); color: #ccfbf1; border: 1px solid rgba(45, 212, 191, 0.20); }
        .risco-moderado .dot { background: #14b8a6; box-shadow: 0 0 8px rgba(20, 184, 166, 0.45); }

        .risco-alto { background: rgba(253, 186, 116, 0.14); color: #ffedd5; border: 1px solid rgba(253, 186, 116, 0.22); }
        .risco-alto .dot { background: #fb923c; box-shadow: 0 0 8px rgba(251, 146, 60, 0.45); }

        .risco-muito-alto { background: rgba(252, 165, 165, 0.16); color: #fee2e2; border: 1px solid rgba(252, 165, 165, 0.24); }
        .risco-muito-alto .dot { background: #f87171; box-shadow: 0 0 8px rgba(248, 113, 113, 0.45); }

        .risco-critico { background: rgba(127, 29, 29, 0.55); color: #fecaca; border: 1px solid rgba(248, 113, 113, 0.30); }
        .risco-critico .dot { background: #dc2626; box-shadow: 0 0 8px rgba(220, 38, 38, 0.55); }

        /* --- BADGE DE PRIORIDADE --- */
        .farol-priority-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.22rem 0.54rem;
            border-radius: 999px;
            font-weight: 700;
            white-space: nowrap;
            border: 1px solid rgba(148, 163, 184, 0.18);
        }

        .priority-maxima { background: rgba(127, 29, 29, 0.52); color: #fecaca; }
        .priority-alta { background: rgba(120, 53, 15, 0.42); color: #fed7aa; }
        .priority-monitoramento { background: rgba(30, 41, 59, 0.72); color: #cbd5e1; }

        /* --- CÉLULA DE CNPJ --- */
        .farol-cnpj-cell {
            color: #e2e8f0;
            font-weight: 600;
            letter-spacing: 0.02em;
            font-family: "Inter", "Segoe UI", sans-serif;
        }

        /* --- DESTAQUE TOP 10 --- */
        .top10 {
            background: linear-gradient(90deg, rgba(127, 29, 29, 0.22), rgba(30, 41, 59, 0.72));
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

aplicar_estilos()
exigir_acesso("farol")
aplicar_estilo_ranking()

_banner_farol = banner_atualizacao()
if _banner_farol:
    st.markdown(_banner_farol, unsafe_allow_html=True)


def normalizar_diligencia(valor) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip().upper()
    if texto in {"S", "SIM", "TRUE", "1", "Y", "YES"}:
        return "S"
    return texto


def eh_risco_muito_alto_critico(valor) -> bool:
    texto = "" if pd.isna(valor) else str(valor).strip().lower()
    return texto in {"muito alto", "crítico", "critico"}


def calcular_metricas_diligencia(df: pd.DataFrame) -> tuple[int, int]:
    if df is None or df.empty or "DILIGENCIA" not in df.columns:
        return 0, 0
    base = df.copy()
    base["_diligencia_norm"] = base["DILIGENCIA"].map(normalizar_diligencia)
    com_diligencia = base[base["_diligencia_norm"] == "S"]
    qtd_diligencia = int(len(com_diligencia))
    if "nivel_risco" in base.columns:
        mask_muito_alto_critico = base["nivel_risco"].map(eh_risco_muito_alto_critico)
        qtd_alto_critico_diligencia = int(len(base[(base["_diligencia_norm"] == "S") & mask_muito_alto_critico]))
    else:
        qtd_alto_critico_diligencia = 0
    return qtd_diligencia, qtd_alto_critico_diligencia


def badge_prioridade_por_valor(valor: str) -> str:
    texto = "" if pd.isna(valor) else str(valor).strip().lower()
    if texto == "prioridade máxima" or texto == "prioridade maxima":
        return '<span class="farol-priority-badge priority-maxima">Prioridade Máxima</span>'
    if texto == "prioridade alta":
        return '<span class="farol-priority-badge priority-alta">Prioridade Alta</span>'
    return '<span class="farol-priority-badge priority-monitoramento">Monitoramento</span>'


def classificar_faixa_prioridade(rank):
    try:
        rank = int(rank)
    except Exception:
        return "Monitoramento"
    if rank <= 10:
        return "Prioridade Máxima"
    if rank <= 50:
        return "Prioridade Alta"
    return "Monitoramento"


def construir_resumo_filtros(municipio, risco, orgao_local, faixa_prioridade, itens_pagina, modo):
    tags = [
        f'<span class="farol-filter-tag"><b>Município:</b> {municipio}</span>',
        f'<span class="farol-filter-tag"><b>Risco:</b> {risco}</span>',
        f'<span class="farol-filter-tag"><b>Órgão local:</b> {orgao_local}</span>',
        f'<span class="farol-filter-tag"><b>Faixa:</b> {faixa_prioridade}</span>',
        f'<span class="farol-filter-tag"><b>Itens/página:</b> {itens_pagina}</span>',
        f'<span class="farol-filter-tag"><b>Modo:</b> {modo}</span>',
    ]
    return f'<div class="farol-filter-summary">{"".join(tags)}</div>'


def preparar_opcoes_navegacao_consulta(df: pd.DataFrame):
    if df is None or df.empty or "COD_CNPJ" not in df.columns:
        return [], {}

    base = df.copy()
    base["COD_CNPJ"] = base["COD_CNPJ"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    if "DSC_RAZAO_SOCIAL" in base.columns:
        base["DSC_RAZAO_SOCIAL"] = base["DSC_RAZAO_SOCIAL"].fillna("").astype(str).str.strip()
    else:
        base["DSC_RAZAO_SOCIAL"] = ""

    opcoes = []
    mapa = {}
    for _, row in base[["COD_CNPJ", "DSC_RAZAO_SOCIAL"]].drop_duplicates().iterrows():
        cnpj = row["COD_CNPJ"]
        razao = row["DSC_RAZAO_SOCIAL"]
        label = f"{cnpj} — {razao}" if razao else cnpj
        opcoes.append(label)
        mapa[label] = cnpj
    return opcoes, mapa


def preparar_tabela_exibicao(ranking_filtrado: pd.DataFrame, itens_por_pagina: int, modo: str) -> pd.DataFrame:
    if ranking_filtrado.empty:
        return pd.DataFrame()

    colunas_base = [
        "ranking_fiscalizacao",
        "faixa_prioridade",
        "COD_CNPJ",
        "DSC_RAZAO_SOCIAL",
        "DSC_SEGMENTO",
        "DECRETO",
        "DIAS_PARA_SAIDA",
        "nivel_risco",
        "indice_prioridade_fiscalizacao",
    ]
    colunas_analiticas = [
        "SITUAÇÃO ATUAL",
        "indice_geral_farol",
        "DILIGENCIA",
    ]

    colunas = colunas_base + (colunas_analiticas if modo == "Analítico" else [])
    colunas = [c for c in colunas if c in ranking_filtrado.columns]
    df = ranking_filtrado[colunas].head(itens_por_pagina).copy()

    renomear = {
        "ranking_fiscalizacao": "Ranking",
        "faixa_prioridade": "Faixa",
        "COD_CNPJ": "CNPJ",
        "DSC_RAZAO_SOCIAL": "Razão Social",
        "DSC_SEGMENTO": "Segmento",
        "DECRETO": "Decreto",
        "DIAS_PARA_SAIDA": "Dias para Saída",
        "nivel_risco": "Nível de Risco",
        "indice_prioridade_fiscalizacao": "Índice Priorização",
        "SITUAÇÃO ATUAL": "Situação Atual",
        "indice_geral_farol": "Índice FAROL",
        "DILIGENCIA": "Diligência",
    }
    df = df.rename(columns=renomear)

    if "Faixa" in df.columns:
        df["Faixa"] = df["Faixa"].map(badge_prioridade_por_valor)
    if "Nível de Risco" in df.columns:
        df["Nível de Risco"] = df["Nível de Risco"].map(badge_risco)
    for col in ["Índice Priorização", "Índice FAROL"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).map(lambda x: f"{x:.2f}")
    if "Dias para Saída" in df.columns:
        df["Dias para Saída"] = df["Dias para Saída"].map(badge_dias_para_saida)
    return df


def gerar_leitura_executiva_ranking(df: pd.DataFrame) -> str:
    if df.empty:
        return """
<div class="farol-reading-card">
    <div class="farol-section-title">Leitura executiva do ranking</div>
    <div class="farol-section-subtitle">Síntese operacional do recorte atual.</div>
    <div class="farol-reading-small">Nenhum contribuinte foi encontrado para o recorte aplicado.</div>
</div>
""".strip()

    total = len(df)
    risco_top = obter_dominante(df, "nivel_risco")
    media_farol = float(pd.to_numeric(df.get("indice_geral_farol", 0), errors="coerce").fillna(0).mean())
    media_pri = float(pd.to_numeric(df.get("indice_prioridade_fiscalizacao", 0), errors="coerce").fillna(0).mean())
    media_dias = float(pd.to_numeric(df.get("DIAS_PARA_SAIDA", 0), errors="coerce").fillna(0).mean())
    qtd_diligencia, qtd_alto_critico_diligencia = calcular_metricas_diligencia(df)
    primeira_razao = str(df.iloc[0]["DSC_RAZAO_SOCIAL"]) if "DSC_RAZAO_SOCIAL" in df.columns and not df.empty else "Não informada"

    return f"""
<div class="farol-reading-card">
    <div class="farol-section-title">Leitura executiva do ranking</div>
    <div class="farol-section-subtitle">Síntese orientada à priorização analítica no recorte atual.</div>

<ul>
    <li><b>Recorte ativo:</b> {formatar_inteiro(total)} contribuintes no ranking de análise.</li>
    <li><b>Diligências previstas:</b> {formatar_inteiro(qtd_diligencia)} casos com diligência = 'S', dos quais <b>{formatar_inteiro(qtd_alto_critico_diligencia)}</b> também estão em risco Muito Alto/Crítico.</li>
    <li><b>Intensidade média:</b> Índice FAROL de <b>{formatar_decimal(media_farol)}</b>, priorização média de <b>{formatar_decimal(media_pri)}</b> e prazo médio de <b>{formatar_decimal(media_dias)}</b> dias para saída.</li>
</ul>

<div class="farol-reading-small">
<b>Leitura operacional:</b> o recorte atual concentra risco predominante em <b>{risco_top}</b> e já posiciona no topo os contribuintes com maior urgência de atuação. O primeiro contribuinte exibido é <b>{primeira_razao}</b>, representando o ponto inicial mais forte para abertura da análise detalhada.<br><br>
<b>Uso sugerido:</b> utilizar esta página para ordenar a fila de trabalho e aprofundar os casos prioritários na Consulta do Contribuinte.
</div>
</div>
""".strip()


st.markdown(
    """
    <div class="farol-page-hero">
        <h1>🏁 Ranking de Análise</h1>
        <p>
            Fila inteligente de priorização analítica com base no índice FAROL, no nível de risco,
            no prazo até a saída do campo de visão e na necessidade de diligência.
        </p>
        <div class="farol-chip-row">
            <span class="farol-chip">Priorização analítica</span>
            <span class="farol-chip">Fila de decisão</span>
            <span class="farol-chip">Prazo até saída</span>
            <span class="farol-chip">Exportação disponível</span>
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
    st.caption("Use esta página para montar a fila prioritária de análise e exportar o recorte atual.")

st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Comando do ranking</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="farol-section-subtitle">Defina o recorte operacional e o formato de leitura do ranking de análise.</div>',
    unsafe_allow_html=True,
)

f1, f2, f3, f4, f5, f6, f7 = st.columns([1.10, 1.12, 1.02, 1.05, 0.85, 0.72, 0.95])

municipio = f1.selectbox(
    "Município",
    ["Todos"] + sorted(semaforo["C_DSC_MUNICIPIO"].dropna().astype(str).unique().tolist())
) if "C_DSC_MUNICIPIO" in semaforo.columns else "Todos"

opcoes_risco = ["Muito Alto / Crítico", "Todos"]
if "nivel_risco" in semaforo.columns:
    valores_risco = sorted(semaforo["nivel_risco"].dropna().astype(str).unique().tolist())
    opcoes_risco.extend([v for v in valores_risco if v not in opcoes_risco])
risco = f2.selectbox("Nível de risco", opcoes_risco, index=0)

orgao_local = f3.selectbox(
    "Órgão local",
    ["Todos"] + sorted(semaforo["DSC_ORGAO_LOCAL"].dropna().astype(str).unique().tolist())
) if "DSC_ORGAO_LOCAL" in semaforo.columns else "Todos"

faixa_prioridade = f4.selectbox(
    "Faixa de prioridade",
    ["Todas", "Prioridade Máxima", "Prioridade Alta", "Monitoramento"],
    index=0,
)

itens_por_pagina = f5.selectbox("Itens/página", [10, 20, 50, 100], index=0)
pagina = max(1, int(f6.number_input("Nº", min_value=1, value=1, step=1)))
modo = f7.radio("Modo", ["Executivo", "Analítico"], index=0)

filtro_risco_base = "Todos" if risco == "Muito Alto / Crítico" else risco

filtrado = filtrar_base(
    semaforo,
    municipio=municipio,
    nivel_risco=filtro_risco_base,
    tipologia="Todos",
    orgao_local=orgao_local,
)

if risco == "Muito Alto / Crítico" and not filtrado.empty and "nivel_risco" in filtrado.columns:
    filtrado = filtrado[
        filtrado["nivel_risco"].astype(str).str.strip().str.lower().isin(["muito alto", "crítico", "critico"])
    ].copy()

ranking_filtrado = build_ranking_fiscalizacao(filtrado)
ranking_filtrado = compatibilizar_ranking_com_catalogo(ranking_filtrado)

if not ranking_filtrado.empty:
    ranking_filtrado = ranking_filtrado.copy()
    if "ranking_fiscalizacao" in ranking_filtrado.columns:
        ranking_filtrado["faixa_prioridade"] = ranking_filtrado["ranking_fiscalizacao"].map(classificar_faixa_prioridade)
    else:
        ranking_filtrado["faixa_prioridade"] = "Monitoramento"

    if faixa_prioridade != "Todas":
        ranking_filtrado = ranking_filtrado[ranking_filtrado["faixa_prioridade"] == faixa_prioridade].copy()

total_filtrado = len(ranking_filtrado)

if total_filtrado > 0:
    total_paginas = max(1, (total_filtrado - 1) // int(itens_por_pagina) + 1)
    pagina = min(pagina, total_paginas)
    inicio = (pagina - 1) * int(itens_por_pagina)
    fim = inicio + int(itens_por_pagina)
    ranking_pagina = ranking_filtrado.iloc[inicio:fim].copy()
else:
    total_paginas = 1
    pagina = 1
    ranking_pagina = ranking_filtrado.copy()

st.markdown(
    construir_resumo_filtros(municipio, risco, orgao_local, faixa_prioridade, itens_por_pagina, modo),
    unsafe_allow_html=True,
)
st.caption(f"Exibindo página {pagina} de {total_paginas} • {formatar_inteiro(total_filtrado)} contribuintes no recorte")
st.markdown('</div>', unsafe_allow_html=True)

total = len(ranking_filtrado)
risco_top, perc_risco_top = _risco_predominante_info(ranking_filtrado)
qtd_diligencia, qtd_alto_critico_diligencia = calcular_metricas_diligencia(ranking_filtrado)
media_farol = float(pd.to_numeric(ranking_filtrado.get("indice_geral_farol", 0), errors="coerce").fillna(0).mean()) if total else 0.0
media_dias_saida = float(pd.to_numeric(ranking_filtrado.get("DIAS_PARA_SAIDA", 0), errors="coerce").fillna(0).mean()) if total else 0.0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        _kpi_card(
            "Contribuintes",
            formatar_inteiro(total),
            f"Página {pagina} de {total_paginas}",
            "primary",
            "📋",
            "Quantidade total de contribuintes no recorte atual do ranking.",
        ),
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        _kpi_card(
            "Risco Predominante",
            str(risco_top),
            f"{formatar_decimal(perc_risco_top * 100, 1)}% do recorte",
            "warning",
            "🚨",
            "Faixa de risco mais frequente entre os contribuintes atualmente priorizados.",
        ),
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        _kpi_card(
            "Diligência Exigida",
            formatar_inteiro(qtd_diligencia),
            f"{formatar_decimal(_percentual(qtd_diligencia, total) * 100, 1)}% do recorte",
            "info",
            "🧭",
            "Empresas do recorte com diligência indicada pelas regras de negócio vigentes.",
        ),
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        _kpi_card(
            "Muito Alto / Crítico com Diligência",
            formatar_inteiro(qtd_alto_critico_diligencia),
            f"Índice FAROL médio: {formatar_decimal(media_farol)} · Saída média: {formatar_decimal(media_dias_saida, 1)} dias",
            "danger",
            "🎯",
            "Subconjunto mais sensível do recorte, combinando necessidade de diligência e maior gravidade analítica.",
        ),
        unsafe_allow_html=True,
    )

st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Destaques do recorte</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="farol-section-subtitle">Os mesmos destaques executivos da Visão Geral, agora aplicados ao recorte atual do ranking de análise.</div>',
    unsafe_allow_html=True,
)

d1, d2 = st.columns(2)

with d1:
    st.markdown(
        f"""
        <div class="farol-insight">
            <div class="farol-insight-kicker">Universo potencial de diligências</div>
            <div class="farol-insight-title">{formatar_inteiro(qtd_diligencia)} empresas com diligência prevista</div>
            <div class="farol-insight-text">
                Este número representa as empresas do recorte atual que, por enquadramento no segmento indústria
                ou por CNAE alcançado por decreto de carga líquida, demandariam diligência inicial.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with d2:
    st.markdown(
        f"""
        <div class="farol-insight">
            <div class="farol-insight-kicker">Eficiência da priorização analítica</div>
            <div class="farol-insight-title">{formatar_inteiro(qtd_alto_critico_diligencia)} empresas com diligência e risco Muito Alto/Crítico</div>
            <div class="farol-insight-text">
                Este número mostra quantas empresas do recorte atual combinam necessidade jurídica de diligência
                com risco Muito Alto ou Crítico, sinalizando maior aderência entre obrigação de diligência e prioridade analítica.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Fila operacional priorizada</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="farol-section-subtitle">Cada linha permite abrir diretamente a Consulta do Contribuinte com o CNPJ preenchido. A grade mantém CNPJ, Segmento, Situação Atual, Dias para Saída e Índice FAROL.</div>',
    unsafe_allow_html=True,
)

if total == 0:
    st.info("Nenhum contribuinte foi encontrado para os filtros aplicados.")
else:
    renderizar_grade_operacional(ranking_pagina)

    cexp1, cexp2 = st.columns([1.2, 0.8])
    with cexp1:
        st.caption("A grade exibe a página atual do recorte. Use o botão Consultar na própria linha do contribuinte para abrir a ficha individual já com o CNPJ preenchido.")
    with cexp2:
        csv_cols = [c for c in ranking_filtrado.columns]
        csv = ranking_filtrado[csv_cols].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Exportar recorte atual (CSV)",
            csv,
            "ranking_analise_filtrado.csv",
            "text/csv",
        )

    with st.expander("Ver justificativas completas dos primeiros colocados"):
        col_rank = "ranking_fiscalizacao" if "ranking_fiscalizacao" in ranking_filtrado.columns else None
        col_cnpj = "COD_CNPJ" if "COD_CNPJ" in ranking_filtrado.columns else None
        col_razao = "DSC_RAZAO_SOCIAL" if "DSC_RAZAO_SOCIAL" in ranking_filtrado.columns else None
        col_just = "justificativa_resumida" if "justificativa_resumida" in ranking_filtrado.columns else None

        if col_rank and col_cnpj and col_razao and col_just:
            detalhes = ranking_pagina[[col_rank, col_cnpj, col_razao, col_just]].head(min(len(ranking_pagina), 20)).copy()
            detalhes.columns = ["Ranking", "CNPJ", "Razão Social", "Justificativa Completa"]
            st.dataframe(detalhes, use_container_width=True, hide_index=True)
        else:
            st.info("As colunas necessárias para exibir as justificativas completas não estão disponíveis.")

st.markdown('</div>', unsafe_allow_html=True)

leitura_ranking = gerar_leitura_executiva_ranking(ranking_filtrado)
st.markdown(leitura_ranking, unsafe_allow_html=True)
