import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import pandas as pd
import streamlit as st
from projetos_especiais.farol.farol_config import APP_TITLE, APP_ICON, PAGE_TITLES
from projetos_especiais.farol.farol_rules_catalog import (
    RULES, INDICES, REGRAS_OFICIAIS,
    RULE_DESCRIPTIONS, RULE_NAMES,
    RULES_BY_INDEX, TIPOLOGIA_RULES,
)
from coate_styles import aplicar_estilos
from coate_auth import exigir_acesso
from projetos_especiais.farol.farol_metadata import banner_atualizacao




# ── helpers ──────────────────────────────────────────────────────────────────

def nome_regra(codigo: str, fallback: str = "") -> str:
    return RULE_NAMES.get(codigo, fallback or codigo)


def descricao_regra(codigo: str, fallback: str = "") -> str:
    return RULE_DESCRIPTIONS.get(codigo, fallback)


def renderizar_tabela_html(df: pd.DataFrame) -> None:
    html = df.to_html(index=False, classes="farol-table", border=0, escape=False)
    st.markdown(f'<div class="farol-table-wrap">{html}</div>', unsafe_allow_html=True)


# ── tabelas geradas do catálogo (nunca desincronizam) ────────────────────────

def tabela_regras_por_indice(indice: str) -> pd.DataFrame:
    """Gera a tabela de regras de um índice lendo direto do catálogo."""
    rows = []
    for codigo in RULES_BY_INDEX.get(indice, []):
        m = RULES[codigo]
        rows.append([codigo, m.nome, m.peso])
    return pd.DataFrame(rows, columns=["Regra", "Nome da Regra", "Peso Máximo"])


def tabela_tipologias() -> pd.DataFrame:
    """Gera a tabela de tipologias lendo direto do catálogo.
    Descrições interpretativas mantidas aqui — são textuais, não estruturais.
    """
    descricoes = {
        "Saída Sem Entrada": (
            "Relacionada às regras R01 e R02, indicando predominância de saídas "
            "frente às entradas ou ausência total de entradas relevantes."
        ),
        "Concentração de cadeia — cliente ou fornecedor único": (
            "Relacionada às regras R03 e R04, indicando que toda a operação "
            "está concentrada em um único fornecedor (R03) ou em um único "
            "cliente/destinatário (R04). Sinal de cadeia fechada ou empresa laranja."
        ),
        "Entrada Sem Saída": (
            "Relacionada às regras R05 e R06, indicando predominância de entradas "
            "frente às saídas ou ausência total de saídas relevantes."
        ),
        "Movimentação financeira sem documento fiscal": (
            "Relacionada às regras R08 e R09, indicando vendas inexistentes ou "
            "cobertura insuficiente das vendas sobre a DIMP."
        ),
        "Documento fiscal sem movimentação financeira": (
            "Relacionada às regras R12 e R13, indicando DIMP sem vendas "
            "correspondentes ou movimentação fiscal muito acima da financeira."
        ),
        "Omissão de SPED": (
            "Relacionada à regra R14, indicando omissão relevante de escrituração."
        ),
        "Entradas interestaduais não seladas": (
            "Relacionada às regras R15 e R16, indicando entradas de fora do estado "
            "parcial ou integralmente não seladas."
        ),
        "Arrecadação zerada com movimentação relevante": (
            "Relacionada à regra R17, indicando ausência de arrecadação no recorte "
            "apesar de sinais consistentes de movimentação econômica ou fiscal."
        ),
    }
    # Obter tipologias únicas na ordem em que aparecem no catálogo
    vistas: dict = {}
    for codigo in REGRAS_OFICIAIS:
        tip = RULES[codigo].tipologia
        if tip not in vistas:
            regras = [c for c in REGRAS_OFICIAIS if RULES[c].tipologia == tip]
            vistas[tip] = regras
    rows = [[tip, descricoes.get(tip, "—")] for tip in vistas]
    return pd.DataFrame(rows, columns=["Tipologia", "Interpretação"])


def tabela_regras_detalhadas() -> pd.DataFrame:
    """Gera a tabela completa de regras com descrição e dimensão, do catálogo."""
    indice_label = {
        "operacional": "Operacional",
        "financeiro":  "Financeiro",
        "fiscal":      "Fiscal",
    }
    rows = []
    for codigo in REGRAS_OFICIAIS:
        m = RULES[codigo]
        rows.append([
            codigo,
            m.nome,
            m.descricao,
            indice_label.get(m.indice, m.indice),
        ])
    return pd.DataFrame(rows, columns=["Regra", "Nome", "Descrição funcional", "Dimensão"])


# ── página ───────────────────────────────────────────────────────────────────

aplicar_estilos()
exigir_acesso("farol")

_banner_farol = banner_atualizacao()
if _banner_farol:
    st.markdown(_banner_farol, unsafe_allow_html=True)

st.markdown(
    """
    <div class="farol-page-hero">
        <h1>📘 Metodologia, Índices e Regras</h1>
        <p>
            Referência funcional do motor atual do FAROL para interpretação do modelo,
            composição dos índices, regras oficiais consideradas na saída do motor,
            tipologias analíticas e lógica geral de priorização.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── visão geral ──────────────────────────────────────────────────────────────
st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Visão geral da metodologia</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="farol-note">
    O motor atual do FAROL consolida a análise por contribuinte a partir de três dimensões principais:
    <strong>Operacional</strong>, <strong>Financeira</strong> e <strong>Fiscal</strong>.
    Cada dimensão é composta por regras oficiais, com tratamento por <strong>blocos lógicos</strong>
    quando há regras extremas e graduadas que representam o mesmo fenômeno.

    <br><br>
    Na saída oficial do modelo, entram apenas as regras homologadas que alimentam:
    <ul>
        <li>contagem de regras acionadas;</li>
        <li>lista de regras acionadas;</li>
        <li>justificativa resumida;</li>
        <li>tipologia principal;</li>
        <li>índices dimensionais;</li>
        <li>índice geral.</li>
    </ul>

    Em especial, o motor atual trata como blocos:
    <ul>
        <li><strong>Operacional — bloco de saída:</strong> R01/R02, usando apenas o maior score do bloco;</li>
        <li><strong>Operacional — bloco de entrada:</strong> R05/R06, usando apenas o maior score do bloco;</li>
        <li><strong>Operacional — qualificadores de concentração:</strong> R03 e R04 somam ao bloco dominante como agravantes independentes;</li>
        <li><strong>Financeiro — bloco principal:</strong> R08/R09, somado ao bloco inverso R12/R13;</li>
        <li><strong>Fiscal:</strong> R14 + bloco de selagem max(R15/R16) + R17.</li>
    </ul>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

# ── regras por dimensão (geradas do catálogo) ─────────────────────────────────
st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Regras oficiais por dimensão</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Índice Operacional**")
    renderizar_tabela_html(tabela_regras_por_indice("operacional"))
with col2:
    st.markdown("**Índice Financeiro**")
    renderizar_tabela_html(tabela_regras_por_indice("financeiro"))
with col3:
    st.markdown("**Índice Fiscal**")
    renderizar_tabela_html(tabela_regras_por_indice("fiscal"))

st.markdown('</div>', unsafe_allow_html=True)

# ── cálculo dos índices ───────────────────────────────────────────────────────
st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Cálculo dos índices</div>', unsafe_allow_html=True)

st.markdown("**1. Índice Operacional**")
st.markdown(
    """
    O índice operacional é calculado a partir de dois blocos antagônicos —
    <strong>bloco de saída</strong> (R01/R02) e <strong>bloco de entrada</strong> (R05/R06) —
    mais dois qualificadores de concentração de cadeia: <strong>R03</strong> (fornecedor único)
    e <strong>R04</strong> (cliente único). Nos blocos antagônicos, o motor considera o maior
    score entre a regra extrema e a regra graduada e, em seguida, usa apenas o bloco dominante.
    R03 e R04 somam sobre o bloco dominante como agravantes — o score resultante pode
    superar o denominador histórico de 7, sendo capeado em 100.

    <br><br>
    <strong>Entradas</strong> correspondem exclusivamente às NF-e de entrada
    (coluna <code>ENTRADAS</code>), sem fallback para compras.
    <strong>Saídas</strong> correspondem à soma de NF-e de saída e NFC-e
    (coluna <code>Saidas Totais</code>).

    <br><br>
    As regras de adicionamento (R02 e R06) só pontuam a partir de desproporções
    realmente preocupantes — adicionamentos comercialmente normais não são penalizados:
    R02 aciona a partir de 3× (saídas/entradas); R06 aciona a partir de 2× (entradas/saídas).
    """
)
st.markdown(
    """
    <div class="farol-formula">
Bloco de saída          = max(R01, R02)
Bloco de entrada        = max(R05, R06)
Bloco dominante         = max(Bloco de saída, Bloco de entrada)

Score Operacional       = Bloco dominante + R03 + R04
Índice Operacional      = min((Score Operacional / 7) × 100,  100)
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("**2. Índice Financeiro**")
st.markdown(
    """
    O índice financeiro é composto por dois blocos distintos:
    <strong>bloco principal</strong> (R08/R09), ligado à cobertura de vendas sobre a DIMP,
    e <strong>bloco inverso</strong> (R12/R13), ligado à movimentação fiscal acima da financeira.
    Dentro de cada bloco, o motor usa o maior score entre extremo e gradação. Ao final,
    os dois blocos são somados.
    """
)
st.markdown(
    """
    <div class="farol-formula">
Bloco financeiro principal = max(R08, R09)
Bloco financeiro inverso   = max(R12, R13)

Score Financeiro  = Bloco financeiro principal + Bloco financeiro inverso
Índice Financeiro = (Score Financeiro / 14) × 100
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("**3. Índice Fiscal**")
st.markdown(
    """
    O índice fiscal soma a regra de omissão de SPED, o bloco de selagem de entradas
    interestaduais e a regra de arrecadação zerada com movimentação relevante.
    No bloco de selagem, o motor considera apenas o maior score entre a regra parcial e a regra extrema.
    """
)
st.markdown(
    """
    <div class="farol-formula">
Bloco de selagem = max(R15, R16)

Score Fiscal  = R14 + Bloco de selagem + R17
Índice Fiscal = (Score Fiscal / 14) × 100
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("**4. Índice Geral FAROL**")
pesos_indices = pd.DataFrame(
    [
        ["Índice Operacional", "60%"],
        ["Índice Financeiro",  "30%"],
        ["Índice Fiscal",      "10%"],
    ],
    columns=["Componente", "Peso no Índice Geral"],
)
renderizar_tabela_html(pesos_indices)
st.markdown(
    """
    <div class="farol-formula">
Índice Geral FAROL =
(Índice Operacional × 0,60) +
(Índice Financeiro  × 0,30) +
(Índice Fiscal      × 0,10)
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="farol-note">
    A leitura do índice geral deve ser feita em conjunto com:
    <ul>
        <li>o nível de risco atribuído ao contribuinte;</li>
        <li>a quantidade de regras acionadas;</li>
        <li>a tipologia principal identificada;</li>
        <li>a justificativa resumida gerada pelo motor.</li>
    </ul>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

# ── tipologias (geradas do catálogo) ─────────────────────────────────────────
st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Tipologias oficiais</div>', unsafe_allow_html=True)
renderizar_tabela_html(tabela_tipologias())
st.markdown('</div>', unsafe_allow_html=True)

# ── regras detalhadas (geradas do catálogo) ───────────────────────────────────
st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Regras oficiais consideradas na saída do modelo</div>', unsafe_allow_html=True)
renderizar_tabela_html(tabela_regras_detalhadas())
st.markdown('</div>', unsafe_allow_html=True)

# ── faixas graduadas ──────────────────────────────────────────────────────────
faixas_resumo = pd.DataFrame(
    [
        ["R02", "Razão saídas/entradas: ≤3× não pontua (normal); 3×–5× → 2; 5×–10× → 4; >10× → 6", "0, 2, 4 ou 6"],
        ["R06", "Razão entradas/saídas: ≤2× não pontua (normal); 2×–4× → 2; 4×–8× → 4; >8× → 6",  "0, 2, 4 ou 6"],
        ["R09", "Cobertura Vendas / DIMP: ≤0,10; ≤0,25; ≤0,50; ≤0,75; <0,90; <1",                 "6 a 1"],
        ["R13", "Razão DIMP / Vendas: >1; ≥1,25; ≥1,5; ≥2; ≥4; ≥10",                              "1 a 6"],
        ["R15", "Selagem parcial: ≤0,10; ≤0,25; ≤0,50; ≤0,75; <0,90; ≥0,90",                      "1 a 6"],
    ],
    columns=["Regra", "Estrutura de Faixas", "Score Aplicado"],
)

st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Estrutura resumida de faixas graduadas</div>', unsafe_allow_html=True)
renderizar_tabela_html(faixas_resumo)
st.markdown('</div>', unsafe_allow_html=True)

# ── interpretação operacional ─────────────────────────────────────────────────
st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Interpretação operacional</div>', unsafe_allow_html=True)

with st.expander("Como interpretar os índices"):
    st.markdown(
        """
        - **Índice Operacional**: sinaliza inconsistências ligadas à relação entre entradas
          (NF-e de entrada) e saídas (NF-e saída + NFC-e), incluindo casos extremos de ausência
          total de um dos lados, adicionamentos anômalos (R02 acima de 3×, R06 acima de 2×)
          e concentração de cadeia em fornecedor ou cliente único (R03/R04).
        - **Índice Financeiro**: sinaliza descolamentos entre vendas e DIMP, tanto pela ótica da
          cobertura de vendas quanto pela ótica da movimentação fiscal acima da financeira.
        - **Índice Fiscal**: sinaliza omissão de SPED, irregularidades de selagem de entradas
          interestaduais e situações de arrecadação zerada com movimentação relevante.
        - **Índice Geral FAROL**: sintetiza o risco do contribuinte a partir da composição
          ponderada das três dimensões.
        """
    )

with st.expander("Como interpretar a quantidade de regras acionadas"):
    st.markdown(
        """
        A quantidade de regras acionadas informa quantas regras oficiais do modelo foram disparadas
        para o contribuinte. Esse indicador deve ser lido em conjunto com:
        - o peso ou score das regras acionadas;
        - o índice geral;
        - a tipologia principal;
        - a justificativa resumida.
        """
    )

with st.expander("Como interpretar as tipologias"):
    st.markdown(
        """
        As tipologias são leituras sintéticas do principal padrão de risco identificado.
        Elas são definidas a partir do somatório dos scores das regras associadas a cada fenômeno,
        e a tipologia principal corresponde àquela com maior score total no contribuinte.
        """
    )

with st.expander("Observação importante"):
    st.markdown(
        """
        Esta página é gerada dinamicamente a partir do `farol_rules_catalog.py`.
        As tabelas de regras, tipologias e dimensões refletem automaticamente qualquer
        alteração feita no catálogo — sem necessidade de editar esta página.

        Apenas os textos explicativos (fórmulas, interpretação dos blocos e descrições de
        tipologias) precisam de revisão manual quando houver mudança estrutural no motor.
        """
    )

st.markdown('</div>', unsafe_allow_html=True)
