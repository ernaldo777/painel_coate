import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from projetos_especiais.farol.farol_config import APP_TITLE, PAGE_TITLES

from projetos_especiais.farol.farol_core import load_data, distribuicao_risco, metricas_gerais
from coate_styles import aplicar_estilos, loading
from coate_auth import exigir_acesso
from projetos_especiais.farol.farol_rules_catalog import REGRAS_ATIVAS, RULE_DESCRIPTIONS, RULE_NAMES
from projetos_especiais.farol.farol_metadata import banner_atualizacao


# =========================
# CONFIGURAÇÕES GERAIS
# =========================
REGRAS_OFICIAIS = list(REGRAS_ATIVAS)

DESCRICOES_REGRAS = {
    codigo: RULE_DESCRIPTIONS.get(codigo, "")
    for codigo in REGRAS_OFICIAIS
}

NOMES_REGRAS = {
    codigo: RULE_NAMES.get(codigo, codigo)
    for codigo in REGRAS_OFICIAIS
}

CORES_RISCO = {
    "Baixo": "#22c55e",
    "Médio": "#f59e0b",
    "Moderado": "#14b8a6",
    "Alto": "#f97316",
    "Crítico": "#ef4444",
    "Critico": "#ef4444",
    "Muito Alto": "#dc2626",
}

CORES_REGRAS = {
    "R01": "#38bdf8",
    "R02": "#60a5fa",
    "R05": "#818cf8",
    "R06": "#a78bfa",
    "R08": "#f59e0b",
    "R09": "#f97316",
    "R12": "#fb7185",
    "R13": "#e879f9",
    "R14": "#ef4444",
    "R15": "#22c55e",
    "R16": "#14b8a6",
    "R17": "#f43f5e",
}


# =========================
# ESTILO GLOBAL
# =========================

def estilizar_figura(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.18)",
        font=dict(color="#e5e7eb"),
        margin=dict(l=20, r=20, t=25, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1"),
        ),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.10)", zeroline=False)
    return fig


def renderizar_tabela_html(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Sem dados para exibir.")
        return

    html = df.to_html(index=False, classes="farol-table", border=0, escape=False)
    st.markdown(f'<div class="farol-table-wrap">{html}</div>', unsafe_allow_html=True)


def formatar_inteiro(valor):
    try:
        return f"{int(valor):,}".replace(",", ".")
    except Exception:
        return "0"


def formatar_decimal(valor, casas=2):
    try:
        return f"{float(valor):.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


def obter_coluna(df: pd.DataFrame, candidatas: list[str]) -> str | None:
    cols_lower = {c.lower(): c for c in df.columns}
    for nome in candidatas:
        if nome.lower() in cols_lower:
            return cols_lower[nome.lower()]
    return None

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



def aplicar_filtros(semaforo: pd.DataFrame, mapa_regras: pd.DataFrame):
    semaforo_filtrado = semaforo.copy()
    mapa_regras_filtrado = mapa_regras.copy()

    col_cnpj_sem = obter_coluna(semaforo_filtrado, ["CNPJ", "cnpj", "cod_cnpj", "COD_CNPJ"])
    col_cnpj_map = obter_coluna(mapa_regras_filtrado, ["CNPJ", "cnpj", "cod_cnpj", "COD_CNPJ"])

    col_municipio = obter_coluna(
        semaforo_filtrado,
        ["municipio", "MUNICIPIO", "nome_municipio", "NOME_MUNICIPIO", "C_DSC_MUNICIPIO"]
    )
    col_orgao = obter_coluna(
        semaforo_filtrado,
        ["DSC_ORGAO_LOCAL", "orgao_local", "ORGAO_LOCAL", "órgão_local", "ORGAO", "orgao"]
    )
    col_risco = obter_coluna(
        semaforo_filtrado,
        ["nivel_risco", "NIVEL_RISCO", "faixa_risco", "FAIXA_RISCO"]
    )

    with st.container():
        st.markdown('<div class="farol-chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="farol-section-title">Filtros rápidos</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="farol-section-subtitle">Use filtros leves para recortar a leitura executiva sem sair da Visão Geral.</div>',
            unsafe_allow_html=True,
        )

        f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.2, 0.95])

        municipio_sel = "Todos"
        if col_municipio:
            municipios = ["Todos"] + sorted(
                [str(x) for x in semaforo_filtrado[col_municipio].dropna().astype(str).unique()]
            )
            municipio_sel = f1.selectbox("Município", municipios, index=0)

        orgao_sel = "Todos"
        if col_orgao:
            orgaos = ["Todos"] + sorted(
                [str(x) for x in semaforo_filtrado[col_orgao].dropna().astype(str).unique()]
            )
            orgao_sel = f2.selectbox("Órgão local", orgaos, index=0)

        risco_sel = f3.selectbox(
            "Faixa de risco",
            ["Todos", "Alto", "Muito Alto", "Crítico", "Baixo", "Médio", "Moderado"],
            index=0
        )

        modo_leitura = f4.radio("Modo", ["Executivo", "Analítico"], index=0)

        if col_municipio and municipio_sel != "Todos":
            semaforo_filtrado = semaforo_filtrado[
                semaforo_filtrado[col_municipio].astype(str) == municipio_sel
            ]

        if col_orgao and orgao_sel != "Todos":
            semaforo_filtrado = semaforo_filtrado[
                semaforo_filtrado[col_orgao].astype(str) == orgao_sel
            ]

        if col_risco and risco_sel != "Todos":
            risco_upper = risco_sel.upper()
            if risco_sel == "Muito Alto":
                semaforo_filtrado = semaforo_filtrado[
                    semaforo_filtrado[col_risco].astype(str).str.upper().isin(
                        ["MUITO ALTO", "CRÍTICO", "CRITICO"]
                    )
                ]
            else:
                semaforo_filtrado = semaforo_filtrado[
                    semaforo_filtrado[col_risco].astype(str).str.upper() == risco_upper
                ]

        if (
            col_cnpj_sem
            and col_cnpj_map
            and not semaforo_filtrado.empty
            and not mapa_regras_filtrado.empty
        ):
            cnpjs_validos = set(semaforo_filtrado[col_cnpj_sem].astype(str))
            mapa_regras_filtrado = mapa_regras_filtrado[
                mapa_regras_filtrado[col_cnpj_map].astype(str).isin(cnpjs_validos)
            ].copy()

        st.markdown('</div>', unsafe_allow_html=True)

    return semaforo_filtrado, mapa_regras_filtrado, modo_leitura


def calcular_top_regras_por_flags(mapa_regras: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    colunas_oficiais = [f"{r}_flag" for r in REGRAS_OFICIAIS if f"{r}_flag" in mapa_regras.columns]

    if mapa_regras is None or mapa_regras.empty or not colunas_oficiais:
        return pd.DataFrame(columns=["Regra", "Nome", "Descrição", "Quantidade de Acionamentos", "Percentual"])

    total_base = len(mapa_regras)
    contagens_regras = []

    for col in colunas_oficiais:
        qtd = pd.to_numeric(mapa_regras[col], errors="coerce").fillna(0).sum()
        if qtd > 0:
            codigo_regra = col.replace("_flag", "")
            perc = (qtd / total_base) * 100 if total_base > 0 else 0
            contagens_regras.append(
                {
                    "Regra": codigo_regra,
                    "Nome": NOMES_REGRAS.get(codigo_regra, codigo_regra),
                    "Descrição": DESCRICOES_REGRAS.get(codigo_regra, "Descrição não informada"),
                    "Quantidade de Acionamentos": int(qtd),
                    "Percentual": round(perc, 2),
                }
            )

    if not contagens_regras:
        return pd.DataFrame(columns=["Regra", "Nome", "Descrição", "Quantidade de Acionamentos", "Percentual"])

    return (
        pd.DataFrame(contagens_regras)
        .sort_values("Quantidade de Acionamentos", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def preparar_distribuicao_risco(semaforo: pd.DataFrame) -> pd.DataFrame:
    dist = distribuicao_risco(semaforo).copy()

    if dist.empty:
        return pd.DataFrame(columns=["nivel_risco", "quantidade", "percentual"])

    total_dist = dist["quantidade"].sum()
    dist["percentual"] = dist["quantidade"].apply(
        lambda x: round((x / total_dist) * 100, 2) if total_dist > 0 else 0
    )

    dist = dist.sort_values(
        by=["percentual", "quantidade"],
        ascending=[False, False]
    ).reset_index(drop=True)

    return dist




def renderizar_kpis_executivos(metricas: dict, metricas_diligencia: dict | None = None):
    metricas_diligencia = metricas_diligencia or {}
    total = int(metricas.get("total", 0) or 0)
    em_risco = int(metricas.get("em_risco", 0) or 0)
    muito_alto_critico = int(metricas.get("muito_alto_critico", 0) or 0)
    indice_medio = float(metricas.get("indice_medio", 0) or 0)
    com_diligencia = int(metricas_diligencia.get("com_diligencia", 0) or 0)
    muito_alto_critico_com_diligencia = int(metricas_diligencia.get("muito_alto_critico_com_diligencia", 0) or 0)

    perc_em_risco = (em_risco / total * 100) if total else 0
    perc_muito_alto_critico = (muito_alto_critico / total * 100) if total else 0
    perc_diligencia = (com_diligencia / total * 100) if total else 0
    perc_ma_crit_dilig = (muito_alto_critico_com_diligencia / max(com_diligencia, 1) * 100) if com_diligencia else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            _kpi_card(
                "Contribuintes",
                formatar_inteiro(total),
                "Base filtrada atual",
                "primary",
                "🏢",
                "Total de contribuintes no recorte aplicado na Visão Geral.",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _kpi_card(
                "Em risco",
                formatar_inteiro(em_risco),
                f"{formatar_decimal(perc_em_risco)}% da base",
                "warning",
                "⚠️",
                "Contribuintes fora da faixa de menor risco e que merecem monitoramento.",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            _kpi_card(
                "Muito Alto / Crítico",
                formatar_inteiro(muito_alto_critico),
                f"{formatar_decimal(perc_muito_alto_critico)}% da base",
                "danger",
                "🔥",
                "Núcleo prioritário para ação fiscal imediata.",
            ),
            unsafe_allow_html=True,
        )

    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown(
            _kpi_card(
                "Índice médio FAROL",
                formatar_decimal(indice_medio),
                "Leitura sintética do recorte",
                "info",
                "📈",
                "Média do índice FAROL considerando o recorte atualmente filtrado.",
            ),
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            _kpi_card(
                "Diligência exigida",
                formatar_inteiro(com_diligencia),
                f"{formatar_decimal(perc_diligencia)}% da base",
                "success",
                "🧭",
                "Empresas em que a diligência inicial é juridicamente cabível.",
            ),
            unsafe_allow_html=True,
        )
    with c6:
        st.markdown(
            _kpi_card(
                "Muito Alto / Crítico com diligência",
                formatar_inteiro(muito_alto_critico_com_diligencia),
                f"{formatar_decimal(perc_ma_crit_dilig)}% do universo com diligência",
                "warning",
                "🎯",
                "Casos em que a diligência é cabível e o risco está no núcleo prioritário.",
            ),
            unsafe_allow_html=True,
        )
def montar_cards_de_destaque(metricas: dict, dist: pd.DataFrame, top_rules: pd.DataFrame, metricas_diligencia: dict | None = None):
    total = metricas.get("total", 0)
    em_risco = metricas.get("em_risco", 0)
    muito_alto_critico = metricas.get("muito_alto_critico", 0)

    perc_em_risco = (em_risco / total * 100) if total else 0
    perc_muito_alto_critico = (muito_alto_critico / total * 100) if total else 0

    nivel_predominante = "Não identificado"
    if not dist.empty and "quantidade" in dist.columns:
        linha_top = dist.sort_values("quantidade", ascending=False).iloc[0]
        nivel_predominante = str(linha_top["nivel_risco"])

    regra_top = "Não identificada"
    regra_top_qtd = 0
    regra_top_perc = 0.0
    if not top_rules.empty:
        linha_regra = top_rules.iloc[0]
        regra_top = f"{linha_regra['Regra']} — {linha_regra['Nome']}"
        regra_top_qtd = int(linha_regra["Quantidade de Acionamentos"])
        regra_top_perc = float(linha_regra["Percentual"])

    metricas_diligencia = metricas_diligencia or {}
    com_diligencia = int(metricas_diligencia.get("com_diligencia", 0))
    muito_alto_critico_com_diligencia = int(metricas_diligencia.get("muito_alto_critico_com_diligencia", 0))
    perc_muito_alto_critico_diligencia = (muito_alto_critico_com_diligencia / com_diligencia * 100) if com_diligencia else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            _kpi_card(
                "Pressão de risco",
                f"{formatar_decimal(perc_em_risco)}%",
                f"{formatar_inteiro(em_risco)} contribuintes acima do menor risco",
                "warning",
                "📡",
                "Indica a massa da base que já exige monitoramento e triagem mais atenta.",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _kpi_card(
                "Prioridade imediata",
                formatar_inteiro(muito_alto_critico),
                f"{formatar_decimal(perc_muito_alto_critico)}% da base",
                "danger",
                "🚨",
                "Contribuintes nas faixas Muito Alto e Crítico, foco da atuação imediata.",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            _kpi_card(
                "Sinal predominante",
                nivel_predominante,
                f"Regra líder: {regra_top.split(' — ')[0]}",
                "primary",
                "🧠",
                f"A regra mais recorrente foi {regra_top}, com {formatar_inteiro(regra_top_qtd)} acionamentos ({formatar_decimal(regra_top_perc)}%).",
            ),
            unsafe_allow_html=True,
        )

    c4, c5 = st.columns(2)
    with c4:
        st.markdown(
            _kpi_card(
                "Universo com diligência",
                formatar_inteiro(com_diligencia),
                "Potencial jurídico de diligência inicial",
                "info",
                "📝",
                "Empresas do segmento indústria e contribuintes alcançados por decreto de carga líquida.",
            ),
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            _kpi_card(
                "Eficiência da priorização",
                formatar_inteiro(muito_alto_critico_com_diligencia),
                f"{formatar_decimal(perc_muito_alto_critico_diligencia)}% do universo com diligência",
                "success",
                "✅",
                "Casos em que a diligência é cabível e o FAROL apontou risco Muito Alto ou Crítico.",
            ),
            unsafe_allow_html=True,
        )


def gerar_leitura_executiva(metricas: dict, dist: pd.DataFrame, top_rules: pd.DataFrame) -> str:
    total = metricas.get("total", 0)
    em_risco = metricas.get("em_risco", 0)
    muito_alto_critico = metricas.get("muito_alto_critico", 0)
    indice_medio = metricas.get("indice_medio", 0)

    perc_em_risco = (em_risco / total * 100) if total else 0
    perc_muito_alto_critico = (muito_alto_critico / total * 100) if total else 0

    nivel_predominante = "Não identificado"
    if not dist.empty and "quantidade" in dist.columns:
        linha_top = dist.sort_values("quantidade", ascending=False).iloc[0]
        nivel_predominante = str(linha_top["nivel_risco"])

    regra_top = "Não identificada"
    regra_top_qtd = 0
    regra_top_perc = 0.0
    regra_top_desc = "Sem descrição."

    if not top_rules.empty:
        linha_regra = top_rules.iloc[0]
        regra_top = f"{linha_regra['Regra']} — {linha_regra['Nome']}"
        regra_top_qtd = int(linha_regra["Quantidade de Acionamentos"])
        regra_top_perc = float(linha_regra["Percentual"])
        regra_top_desc = str(linha_regra["Descrição"])

    return f"""
<div class="farol-reading-card">
    <div class="farol-section-title">Leitura executiva</div>
    <div class="farol-section-subtitle">
        Síntese orientada à gestão e à priorização operacional, considerando apenas as regras homologadas da saída oficial.
    </div>

- **Base analisada:** {formatar_inteiro(total)} contribuintes.
- **Contribuintes em risco:** {formatar_inteiro(em_risco)} ({formatar_decimal(perc_em_risco)}% da base).
- **Núcleo prioritário Muito Alto / Crítico:** {formatar_inteiro(muito_alto_critico)} ({formatar_decimal(perc_muito_alto_critico)}%).
- **Faixa predominante de risco:** **{nivel_predominante}**.
- **Índice médio FAROL:** **{formatar_decimal(indice_medio)}**.
- **Regra oficial mais recorrente:** **{regra_top}**, com {formatar_inteiro(regra_top_qtd)} acionamentos ({formatar_decimal(regra_top_perc)}%).

<ul>
    <li><b>Concentração de atenção:</b> o subconjunto em faixas Muito Alto / Crítico deve compor a principal trilha de priorização imediata da fiscalização.</li>
    <li><b>Leitura do padrão dominante:</b> a predominância da faixa <b>{nivel_predominante}</b> ajuda a calibrar o esforço entre monitoramento amplo e atuação focalizada.</li>
    <li><b>Sinal mais recorrente:</b> a incidência de <b>{regra_top}</b> sugere um comportamento que merece leitura operacional recorrente no recorte atual.</li>
</ul>

<div class="farol-reading-small">
<b>Descrição sintética da regra mais acionada:</b> {regra_top_desc}<br><br>
<b>Sugestão de uso operacional:</b> utilizar esta página como porta de entrada executiva do FAROL, direcionando em seguida a análise detalhada para o Ranking de Análise e para a Consulta do Contribuinte.
</div>
</div>
""".strip()


def grafico_distribuicao_risco(dist: pd.DataFrame):
    if dist.empty:
        st.info("Não há dados de distribuição de risco para o recorte selecionado.")
        return

    ordem_dinamica = dist["nivel_risco"].tolist()

    fig = px.bar(
        dist,
        x="quantidade",
        y="nivel_risco",
        orientation="h",
        text="percentual",
        color="nivel_risco",
        color_discrete_map=CORES_RISCO,
        category_orders={"nivel_risco": ordem_dinamica},
    )
    fig.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Quantidade: %{x}<br>Percentual: %{text:.2f}%<extra></extra>",
    )
    fig.update_layout(
        showlegend=False,
        yaxis_title="",
        xaxis_title="Quantidade de contribuintes",
        yaxis=dict(categoryorder="array", categoryarray=ordem_dinamica[::-1]),
    )
    fig = estilizar_figura(fig)
    st.plotly_chart(fig, use_container_width=True)


def grafico_top_regras(top_rules: pd.DataFrame):
    if top_rules.empty:
        st.info("Não foi possível calcular o top de regras a partir da base atual.")
        return

    top_rules_plot = top_rules.sort_values("Quantidade de Acionamentos", ascending=True).copy()
    top_rules_plot["rotulo"] = top_rules_plot["Regra"] + " — " + top_rules_plot["Nome"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=top_rules_plot["Quantidade de Acionamentos"],
            y=top_rules_plot["rotulo"],
            orientation="h",
            text=top_rules_plot["Percentual"].map(lambda x: f"{x:.2f}%"),
            textposition="outside",
            marker=dict(
                color=[CORES_REGRAS.get(regra, "#60a5fa") for regra in top_rules_plot["Regra"]]
            ),
            customdata=top_rules_plot[["Descrição"]],
            hovertemplate="<b>%{y}</b><br>Quantidade: %{x}<br>Percentual: %{text}<br>Descrição: %{customdata[0]}<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Quantidade de acionamentos",
        yaxis_title="",
        showlegend=False,
    )
    fig = estilizar_figura(fig)
    st.plotly_chart(fig, use_container_width=True)






def contar_muito_alto_critico(semaforo: pd.DataFrame) -> int:
    if semaforo is None or semaforo.empty:
        return 0
    nivel_col = None
    for cand in ["nivel_risco", "NIVEL_RISCO"]:
        if cand in semaforo.columns:
            nivel_col = cand
            break
    if nivel_col is None:
        return 0
    nivel_norm = semaforo[nivel_col].astype(str).str.strip().str.upper()
    return int(nivel_norm.isin(["MUITO ALTO", "CRÍTICO", "CRITICO"]).sum())

def calcular_metricas_diligencia(semaforo: pd.DataFrame) -> dict:
    if semaforo is None or semaforo.empty or "DILIGENCIA" not in semaforo.columns:
        return {"com_diligencia": 0, "muito_alto_critico_com_diligencia": 0}

    dilig = semaforo.copy()
    dilig["__diligencia_norm"] = (
        dilig["DILIGENCIA"]
        .astype(str)
        .str.strip()
        .str.upper()
    )
    mask_dilig = dilig["__diligencia_norm"].isin(["S", "SIM", "TRUE", "1"])

    nivel_col = None
    for cand in ["nivel_risco", "NIVEL_RISCO"]:
        if cand in dilig.columns:
            nivel_col = cand
            break

    if nivel_col is None:
        muito_alto_critico = 0
    else:
        nivel_norm = dilig[nivel_col].astype(str).str.strip().str.upper()
        mask_muito_alto_critico = nivel_norm.isin(["MUITO ALTO", "CRÍTICO", "CRITICO"])
        muito_alto_critico = int((mask_dilig & mask_muito_alto_critico).sum())

    return {
        "com_diligencia": int(mask_dilig.sum()),
        "muito_alto_critico_com_diligencia": muito_alto_critico,
    }


aplicar_estilos()
exigir_acesso("farol")

_banner_farol = banner_atualizacao()
if _banner_farol:
    st.markdown(_banner_farol, unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="farol-page-hero">
        <h1>📊 Visão Geral</h1>
        <p>
            Painel executivo do FAROL para leitura sintética da base monitorada,
            distribuição de risco, incidência das regras homologadas e direcionamento da priorização fiscal.
        </p>
        <div class="farol-chip-row">
            <span class="farol-chip">{APP_TITLE}</span>
            <span class="farol-chip">Painel executivo</span>
            <span class="farol-chip">Regras homologadas</span>
            <span class="farol-chip">Leitura institucional</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with loading():
    data = load_data(required=("semaforo", "mapa_regras"))
semaforo = data["semaforo"]
mapa_regras = data["mapa_regras"]

if semaforo is None or semaforo.empty:
    st.warning("A base do semáforo não foi carregada ou está vazia.")
    st.stop()

if mapa_regras is None:
    mapa_regras = pd.DataFrame()

semaforo, mapa_regras, modo_leitura = aplicar_filtros(semaforo, mapa_regras)

metricas = metricas_gerais(semaforo)
metricas["muito_alto_critico"] = contar_muito_alto_critico(semaforo)
metricas_diligencia = calcular_metricas_diligencia(semaforo)
dist = preparar_distribuicao_risco(semaforo)

top_n = 5 if modo_leitura == "Executivo" else 10
top_rules = calcular_top_regras_por_flags(mapa_regras, n=top_n)

st.markdown('<div class="farol-divider-space"></div>', unsafe_allow_html=True)
renderizar_kpis_executivos(metricas, metricas_diligencia)

st.markdown('<div class="farol-chart-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Destaques executivos</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="farol-section-subtitle">Leitura rápida da base com o mesmo padrão visual dos cards institucionais do painel.</div>',
    unsafe_allow_html=True,
)
montar_cards_de_destaque(metricas, dist, top_rules, metricas_diligencia)
st.markdown('</div>', unsafe_allow_html=True)

if modo_leitura == "Executivo":
    col_a, col_b = st.columns([1.08, 0.92])

    with col_a:
        st.markdown('<div class="farol-chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="farol-section-title">Distribuição de risco</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="farol-section-subtitle">Composição da base por faixa de risco no recorte selecionado.</div>',
            unsafe_allow_html=True,
        )
        grafico_distribuicao_risco(dist)

        with st.expander("Ver tabela completa da distribuição"):
            dist_exibicao = dist.rename(
                columns={
                    "nivel_risco": "Nível de Risco",
                    "quantidade": "Quantidade",
                    "percentual": "Percentual",
                }
            ).copy()
            if not dist_exibicao.empty:
                dist_exibicao["Percentual"] = dist_exibicao["Percentual"].map(lambda x: f"{x:.2f}%")
            renderizar_tabela_html(dist_exibicao)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="farol-chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="farol-section-title">Regras oficiais mais acionadas</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="farol-section-subtitle">Ranking restrito às regras homologadas da saída oficial do FAROL.</div>',
            unsafe_allow_html=True,
        )
        grafico_top_regras(top_rules)

        with st.expander("Ver tabela completa das regras"):
            top_rules_exibicao = top_rules.copy()
            if not top_rules_exibicao.empty:
                top_rules_exibicao["Percentual"] = top_rules_exibicao["Percentual"].map(lambda x: f"{x:.2f}%")
            renderizar_tabela_html(top_rules_exibicao)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown('<div class="farol-chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="farol-section-title">Distribuição de risco</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="farol-section-subtitle">Composição da base por faixa de risco no recorte selecionado.</div>',
        unsafe_allow_html=True,
    )
    grafico_distribuicao_risco(dist)
    with st.expander("Ver tabela completa da distribuição"):
        dist_exibicao = dist.rename(
            columns={
                "nivel_risco": "Nível de Risco",
                "quantidade": "Quantidade",
                "percentual": "Percentual",
            }
        ).copy()
        if not dist_exibicao.empty:
            dist_exibicao["Percentual"] = dist_exibicao["Percentual"].map(lambda x: f"{x:.2f}%")
        renderizar_tabela_html(dist_exibicao)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="farol-chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="farol-section-title">Regras oficiais mais acionadas</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="farol-section-subtitle">Ranking restrito às regras homologadas da saída oficial do FAROL.</div>',
        unsafe_allow_html=True,
    )

    if hasattr(st, "segmented_control"):
        top_n_analitico = st.segmented_control(
            "Quantidade de regras no ranking",
            options=[5, 10, 15],
            default=10,
            key="top_regras_segmentado",
        )
    else:
        top_n_analitico = st.radio(
            "Quantidade de regras no ranking",
            options=[5, 10, 15],
            index=1,
            horizontal=True,
            key="top_regras_radio",
        )

    top_rules = calcular_top_regras_por_flags(mapa_regras, n=int(top_n_analitico))
    grafico_top_regras(top_rules)

    with st.expander("Ver tabela completa das regras"):
        top_rules_exibicao = top_rules.copy()
        if not top_rules_exibicao.empty:
            top_rules_exibicao["Percentual"] = top_rules_exibicao["Percentual"].map(lambda x: f"{x:.2f}%")
        renderizar_tabela_html(top_rules_exibicao)
    st.markdown('</div>', unsafe_allow_html=True)

leitura_executiva = gerar_leitura_executiva(metricas, dist, top_rules)
st.markdown(leitura_executiva, unsafe_allow_html=True)