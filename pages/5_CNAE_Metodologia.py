from __future__ import annotations

import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

# Ícone CNAE
import base64 as _b64cnae
_cnae_icon_path = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'assets', 'cnae_icon.png'))
_cnae_img_tag = ""
if _os.path.exists(_cnae_icon_path):
    with open(_cnae_icon_path, "rb") as _f:
        _cnae_img_tag = (f'<img src="data:image/png;base64,{_b64cnae.b64encode(_f.read()).decode()}" '
                         f'style="height:52px;border-radius:10px;margin-bottom:0.5rem;display:block;" alt="CNAE">')

import streamlit as st

from coate_styles import aplicar_estilos
from coate_auth import exigir_acesso
from projetos_especiais.cnae.cnae_utils import render_section_header

aplicar_estilos()
exigir_acesso("cnae")

# ──────────────────────────────────────────────────────────────
# HERO
# ──────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hero">
        {_cnae_img_tag}
        <div class="hero-kicker">📘 Documentação</div>
        <h1>Metodologia</h1>
        <p>
            Regras de derivação das colunas, lógica de priorização,
            métricas utilizadas, unidade analítica e limitações do modelo.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────
# SECTION 1 — Unidade de análise
# ──────────────────────────────────────────────────────────────
render_section_header(
    "Unidade de Análise",
    subtitle="Estrutura",
    desc="Como a base é organizada e quais são as duas visões complementares.",
    divider=True,
)
st.markdown(
    """
    <div class="panel">
        <p>
            A base operacional possui granularidade <strong>empresa + snapshot mensal</strong>.
            Isso exige duas visões complementares para análise adequada:
        </p>
        <ul style="color:var(--text-soft); font-size:0.95rem; line-height:1.75; margin:0.75rem 0 0 1rem; padding:0;">
            <li><strong>Detalhe mensal</strong> — usada para histórico, oscilação, divergência pontual e inspeção por snapshot.</li>
            <li><strong>Consolidado por empresa</strong> — usada para ranking, priorização de revisão e leitura gerencial.</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────
# SECTION 2 — Colunas derivadas
# ──────────────────────────────────────────────────────────────
render_section_header(
    "Colunas Derivadas Principais",
    subtitle="Schema",
    desc="Campos calculados em tempo de query pelo sistema — não presentes no Parquet original.",
    divider=True,
)

colunas = [
    ("cnpj_str", "CNPJ tratado como string padronizada de 14 dígitos."),
    ("mes_snapshot", "Derivado de dt_snapshot no formato YYYY-MM."),
    ("flag_divergencia_*", "Divergência entre CNAE real e previsto por nível (secao, divisao, grupo, classe, subclasse)."),
    ("flag_predicao_ausente", "Identifica ausência de predição final ou rótulos vazios/Other."),
    ("qtd_predicoes_distintas_empresa", "Quantas predições distintas a empresa recebeu ao longo dos snapshots."),
    ("flag_instabilidade_predicao", "Indica oscilação entre snapshots (> 1 predição distinta)."),
    ("predicao_moda_empresa", "Classe prevista mais frequente para a empresa."),
    ("taxa_consistencia_empresa", "Aproximação auditável da estabilidade temporal da predição."),
    ("par_reclassificacao", "Combinação CNAE real → predito para leitura executiva."),
    ("prioridade_revisao", "Classificação final da carteira: Alta, Média ou Baixa."),
    ("score_prioridade", "Score numérico de 0 a 100 que ordena o ranking de revisão."),
]

rows_html = "".join(
    f"""
    <tr>
        <td style="padding:0.55rem 0.9rem;color:#93c5fd;font-family:monospace;font-size:0.85rem;
                   border-bottom:1px solid var(--border);white-space:nowrap;">{col}</td>
        <td style="padding:0.55rem 0.9rem;color:var(--text-soft);font-size:0.88rem;
                   border-bottom:1px solid var(--border);">{desc}</td>
    </tr>
    """
    for col, desc in colunas
)

st.markdown(
    f"""
    <div class="panel" style="padding:0;">
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr>
                    <th style="padding:0.65rem 0.9rem;text-align:left;color:var(--text-muted);
                               font-size:0.75rem;font-weight:700;letter-spacing:0.06em;
                               text-transform:uppercase;border-bottom:1px solid var(--border-strong);">
                        Coluna
                    </th>
                    <th style="padding:0.65rem 0.9rem;text-align:left;color:var(--text-muted);
                               font-size:0.75rem;font-weight:700;letter-spacing:0.06em;
                               text-transform:uppercase;border-bottom:1px solid var(--border-strong);">
                        Descrição
                    </th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────
# SECTION 3 — Estabilidade
# ──────────────────────────────────────────────────────────────
render_section_header(
    "Lógica de Estabilidade",
    subtitle="Métrica",
    desc="Como é calculada a consistência temporal das predições.",
    divider=True,
)
st.markdown(
    """
    <div class="panel">
        <p>
            A estabilidade considera quantas predições distintas aparecem para a mesma empresa
            ao longo do tempo. A fórmula utilizada é:
        </p>
        <p style="margin-top:0.75rem; font-family:monospace; font-size:0.92rem;
                  color:#93c5fd; background:rgba(59,130,246,0.08); padding:0.7rem 1rem;
                  border-radius:10px; border-left:3px solid #3b82f6;">
            taxa_consistencia = 1 − (qtd_predicoes_distintas − 1) / qtd_registros
        </p>
        <p style="margin-top:0.75rem;">
            Quanto maior o número de classes previstas distintas, menor a consistência temporal.
            Empresas com apenas uma predição ao longo de todos os meses têm consistência de <strong>100%</strong>.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────
# SECTION 4 — Prioridade
# ──────────────────────────────────────────────────────────────
render_section_header(
    "Lógica da Priorização",
    subtitle="Régua",
    desc="Regras explicáveis e auditáveis para classificação da carteira.",
    divider=True,
)

regras = [
    ("🔴", "Alta",  "Ausência de predição (qtd_predicoes_ausentes > 0)."),
    ("🔴", "Alta",  "Divergência em subclasse ≥ 50% + consistência < limiar configurado."),
    ("🔴", "Alta",  "Divergência em classe ≥ 50% + predições distintas ≥ limiar de oscilação."),
    ("🟠", "Média", "Divergência em subclasse ≥ 25%."),
    ("🟠", "Média", "Mais de uma predição distinta observada."),
    ("🟢", "Baixa", "Nenhuma das condições acima atingida."),
]

regras_html = "".join(
    f"""
    <div style="display:flex;align-items:flex-start;gap:0.75rem;
                padding:0.6rem 0;border-bottom:1px solid var(--border);">
        <span style="font-size:1rem;flex-shrink:0;margin-top:1px;">{ic}</span>
        <div>
            <span style="font-size:0.78rem;font-weight:700;color:var(--text-muted);
                         text-transform:uppercase;letter-spacing:0.04em;">{lvl}</span>
            <div style="color:var(--text-soft);font-size:0.9rem;margin-top:0.15rem;">{desc}</div>
        </div>
    </div>
    """
    for ic, lvl, desc in regras
)

st.markdown(
    f'<div class="panel">{regras_html}</div>',
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────
# SECTION 5 — Score
# ──────────────────────────────────────────────────────────────
render_section_header(
    "Fórmula do Score de Prioridade",
    subtitle="Score",
    desc="Composição numérica (0–100) que ordena o ranking.",
    divider=True,
)
st.markdown(
    """
    <div class="panel">
        <p style="font-family:monospace;font-size:0.88rem;color:#93c5fd;
                  background:rgba(59,130,246,0.08);padding:0.9rem 1rem;
                  border-radius:10px;border-left:3px solid #3b82f6;line-height:1.8;">
            score = (taxa_div_subclasse × 40)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ (taxa_div_classe × 20)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ (taxa_div_grupo × 10)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ (15 se instável)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ (10 se consistência abaixo do limiar)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ (5 se tem atividade de saída)
        </p>
        <p style="margin-top:0.85rem;">
            Quando há predição ausente, o score é fixado em <strong>100</strong>
            (máxima urgência de revisão).
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────
# SECTION 6 — Limitações
# ──────────────────────────────────────────────────────────────
render_section_header(
    "Limitações",
    subtitle="Atenção",
    desc="Pontos de cautela na interpretação dos resultados.",
    divider=True,
)

limitacoes = [
    "A prioridade atual é uma régua gerencial inicial — não substitui análise humana.",
    "O painel depende da consistência do schema do Parquet; colunas ausentes são tratadas com valores padrão.",
    "Snapshots múltiplos exigem cuidado: mudança de predição ao longo do tempo não é automaticamente erro.",
    "Features econômicas adicionais podem ser incorporadas futuramente para refinamento do score.",
    "A taxa de consistência é uma aproximação — não reflete causalidade entre predições.",
]

items_html = "".join(
    f"""
    <div style="display:flex;gap:0.7rem;padding:0.55rem 0;border-bottom:1px solid var(--border);
                align-items:flex-start;">
        <span style="color:#f59e0b;font-size:0.9rem;flex-shrink:0;margin-top:2px;">⚠</span>
        <span style="color:var(--text-soft);font-size:0.9rem;line-height:1.55;">{item}</span>
    </div>
    """
    for item in limitacoes
)

st.markdown(
    f'<div class="panel">{items_html}</div>',
    unsafe_allow_html=True,
)
