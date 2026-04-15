"""
coate_config.py
===============
Configurações centrais do Painel COATE.

Ponto único de identidade, versão e constantes compartilhadas entre
todos os módulos (FAROL, CNAE e futuros).

Como usar:
    from coate_config import COATE_TITLE, COATE_VERSION, COATE_AREAS
"""

# =============================================================
# IDENTIDADE
# =============================================================

COATE_NAME: str = "COATE"
COATE_FULL_NAME: str = "Coordenadoria de Atendimento e Execução"
COATE_VERSION: str = "v3"
COATE_TITLE: str = f"Painel {COATE_NAME}"
COATE_SUBTITLE: str = "Central de Inteligência"
COATE_ICON: str = "🏛️"
COATE_KICKER: str = f"SEFAZ-CE • {COATE_FULL_NAME}"


COATE_MODULOS: dict[str, str] = {
    "home": "Painel COATE",
    "farol": "FAROL",
    "cnae": "Reclassificação CNAE",
    "simples": "Simples Nacional",
    "itcd": "ITCD",
    "atendimento": "Atendimento",
    "admin": "Administração",
}

COATE_MODULOS_LABEL: dict[str, str] = {
    "home": "Home COATE",
    "farol": "FAROL",
    "cnae": "Reclassificação CNAE",
    "simples": "Simples Nacional",
    "itcd": "ITCD",
    "atendimento": "Atendimento",
    "admin": "Gestão de Acessos",
}

# Brasão (SVG embutido em base64 ou caminho relativo)
# Se tiver o arquivo PNG/SVG do brasão, coloque em assets/brasao_sefaz.png
# e aponte aqui:
COATE_BRASAO_PATH: str = "assets/brasao_sefaz.png"
COATE_BRASAO_B64: str = ""  # alternativa: string base64 do PNG/SVG

# Rodapé institucional
COATE_FOOTER: str = (
    f"{COATE_TITLE} {COATE_VERSION} • Produto institucional desenvolvido no âmbito da COATE, "
    "com participação da CEACO e da CESIN/NUSIN · SEFAZ-CE"
)

# =============================================================
# ÁREAS DE ATUAÇÃO
# Cada área é um dicionário com metadados para os cards da home.
# =============================================================

COATE_AREAS: list[dict] = [
    {
        "id": "simples_nacional",
        "icon": "🗂️",
        "icon_file": "simples_nacional_icon.png",
        "title": "Simples Nacional",
        "subtitle": "Monitoramento tributário do Simples Nacional no Ceará",
        "desc": "Monitoramento de contribuintes com pendências de regularização e diferenças declaradas entre PGDAS e DIMP.",
        "cor": "primary",
        "status": "ativo",
        "projetos": ["Notificação de Eventos", "Notificação PGDAS X DIMP"],
    },
    {
        "id": "itcd",
        "icon": "⚖️",
        "icon_file": "itcd_icon.png",
        "title": "ITCD",
        "subtitle": "Monitoramento de processos de transmissão patrimonial",
        "desc": "Acompanhamento analítico de processos ITCD com foco no OKR de produtividade fiscal.",
        "cor": "purple",
        "status": "ativo",
        "projetos": ["Painel de Processos", "Exploração de Processos", "Consulta do Processo"],
    },
    {
        "id": "atendimento",
        "icon": "🧾",
        "title": "Atendimento",
        "subtitle": "Espaço reservado para rotinas e painéis de atendimento",
        "desc": "Módulo placeholder para evolução futura de funcionalidades da área de atendimento.",
        "cor": "info",
        "status": "ativo",
        "projetos": ["Página Inicial do Módulo"],
    },
]

# =============================================================
# PROJETOS ESPECIAIS
# =============================================================

COATE_PROJETOS_ESPECIAIS: list[dict] = [
    {
        "id": "farol",
        "icon": "🚦",
        "title": "FAROL",
        "subtitle": "Ferramenta de Avaliação de Risco Operacional em Larga Escala",
        "desc": (
            "Monitora contribuintes abertos nos últimos 180 dias, "
            "detecta irregularidades e classifica o risco fiscal (0–100) "
            "por meio de 14 regras organizadas em 3 índices."
        ),
        "cor": "danger",
        "status": "ativo",
        "paginas": [
            "Visão Geral",
            "Ranking de Análise",
            "Consulta de Contribuinte",
            "Exploração da Base",
            "Agente FAROL",
            "Metodologia",
        ],
    },
    {
        "id": "cnae",
        "icon": "🧭",
        "icon_file": "cnae_icon.png",
        "title": "Reclassificação CNAE",
        "subtitle": "Monitoramento de predições de CNAE por Machine Learning",
        "desc": (
            "Monitora as predições de um modelo de ML que sugere reclassificações "
            "de CNAE, identificando divergências, "
            "instabilidade temporal e priorizando casos para revisão."
        ),
        "cor": "info",
        "status": "ativo",
        "paginas": [
            "Visão Geral",
            "Ranking de Reclassificação",
            "Consulta do Contribuinte",
            "Exploração da Base",
            "Metodologia",
            "Qualidade do Modelo",
        ],
    },
]

# =============================================================
# TÍTULOS DE PÁGINA (aba do navegador)
# =============================================================

PAGE_TITLES: dict[str, str] = {
    "home":             f"{COATE_TITLE} — Home",
    # FAROL
    "farol_visao":      "FAROL — Visão Geral",
    "farol_ranking":    "FAROL — Ranking de Análise",
    "farol_consulta":   "FAROL — Consulta do Contribuinte",
    "farol_exploracao": "FAROL — Exploração da Base",
    "farol_agente":     "FAROL — Agente",
    "farol_metodologia":"FAROL — Metodologia",
    # CNAE
    "cnae_visao":       "CNAE — Visão Geral",
    "cnae_ranking":     "CNAE — Ranking de Reclassificação",
    "cnae_consulta":    "CNAE — Consulta do Contribuinte",
    "cnae_exploracao":  "CNAE — Exploração da Base",
    "cnae_metodologia": "CNAE — Metodologia",
    "cnae_qualidade":   "CNAE — Qualidade do Modelo",
}

# =============================================================
# CACHE
# =============================================================

CACHE_TTL: int = 3600  # 1 hora

# =============================================================
# DESIGN — paleta compartilhada (usada pelo coate_styles.py)
# =============================================================

COLORS = {
    "bg_app":       "#07101d",
    "bg_surface":   "#0f172a",
    "bg_elevated":  "#1e293b",
    "bg_card":      "#111827",
    "border":       "rgba(148, 163, 184, 0.14)",
    "border_strong":"rgba(148, 163, 184, 0.26)",
    "border_accent":"rgba(59, 130, 246, 0.30)",
    "text":         "#f1f5f9",
    "text_soft":    "#cbd5e1",
    "text_muted":   "#64748b",
    # Semânticas
    "primary":      "#3b82f6",
    "success":      "#22c55e",
    "danger":       "#ef4444",
    "warning":      "#f59e0b",
    "info":         "#38bdf8",
    "purple":       "#8b5cf6",
}

# Mapeamento cor → classe CSS (usado nos cards da home)
COR_PARA_ACCENT: dict[str, str] = {
    "primary": "accent-primary",
    "success": "accent-success",
    "danger":  "accent-danger",
    "warning": "accent-warning",
    "info":    "accent-info",
    "purple":  "accent-purple",
}
