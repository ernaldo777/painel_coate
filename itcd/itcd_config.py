"""
itcd_config.py
==============
Configurações centrais do módulo ITCD.
"""
from __future__ import annotations

import os
from pathlib import Path

# =============================================================
# IDENTIDADE
# =============================================================
APP_TITLE    = "ITCD — Painel de Processos"
APP_SUBTITLE = "Acompanhamento analítico de processos de transmissão causa mortis e doação"
APP_ICON     = "⚖️"

# =============================================================
# DADOS
# =============================================================
BASE_DIR          = Path(__file__).resolve().parent
DATA_DIR          = BASE_DIR / "data"
DEFAULT_DATA_PATH = DATA_DIR / "ITCD.xlsx"
DATA_PATH         = Path(os.getenv("ITCD_DATA_PATH", str(DEFAULT_DATA_PATH)))

# =============================================================
# FASES — quais contam como tempo do fiscal
# 3=DISTRIBUIDO, 4=REABERTO, 5=REENVIADO,
# 8=REDISTRIBUIDO, 9=REDIRECIONADO, 14=EM INSTRUÇÃO
# =============================================================
FASES_FISCAL: set[int] = {3, 4, 5, 8, 9, 14}

FASES_NOMES: dict[int, str] = {
    1:  "Aberto",
    2:  "Enviado",
    3:  "Distribuído",
    4:  "Reaberto",
    5:  "Reenviado",
    8:  "Redistribuído",
    9:  "Redirecionado",
    10: "Cancelado",
    11: "Concluído",
    12: "Transmitido",
    14: "Em Instrução",
}

# =============================================================
# OKR — meta de prazo líquido
# =============================================================
PRAZO_META_DIAS: int = 15   # meta: processo concluído em ≤ 15 dias líquidos

# Status de pendência que "congela" o contador do fiscal
PENDENCIA_BLOQUEANTES: set[str] = {"CRIADA", "NAO RESOLVIDA"}
PENDENCIA_ENCERRADAS:  set[str] = {"CANCELADA", "RESOLVIDA"}

# =============================================================
# STATUS DO PROCESSO (lógica Fase Minima / Fase Máxima)
# Reproduz o campo calculado do Tableau:
#   IF Fase Minima IN (5..11) AND Fase Máxima IN (5..11) → CONCLUÍDO
#   ELSE → A TRABALHAR
# =============================================================
FASES_CONCLUIDO: set[int] = {5, 6, 7, 8, 9, 10, 11}

STATUS_PROCESSO_LABELS: list[str] = ["A TRABALHAR", "CONCLUÍDO"]

STATUS_PROCESSO_COLOR_MAP: dict[str, str] = {
    "CONCLUÍDO":   "#22c55e",
    "A TRABALHAR": "#3b82f6",
}

# =============================================================
# TIPOS DE TRANSMISSÃO
# =============================================================
TIPOS_TRANSMISSAO: dict[int, str] = {
    1: "Inter Vivos",
    2: "Causa Mortis",
}

# =============================================================
# CACHE
# =============================================================
CACHE_TTL: int = 3600  # 1 hora

# =============================================================
# PLOTLY
# =============================================================
PLOTLY_TEMPLATE      = "plotly_dark"
PLOTLY_PAPER_BGCOLOR = "rgba(0,0,0,0)"
PLOTLY_PLOT_BGCOLOR  = "rgba(0,0,0,0)"
PLOTLY_FONT_COLOR    = "#cbd5e1"
PLOTLY_FONT_FAMILY   = "'Segoe UI', Inter, sans-serif"

COLOR_EM_DIA   = "#22c55e"
COLOR_ATRASADO = "#ef4444"
COLOR_ALERTA   = "#f59e0b"
COLOR_PRIMARY  = "#3b82f6"
COLOR_PURPLE   = "#8b5cf6"

PRAZO_COLOR_MAP: dict[str, str] = {
    "EM DIA":   COLOR_EM_DIA,
    "ATRASADO": COLOR_ATRASADO,
}

# =============================================================
# UX
# =============================================================
LOADING_MESSAGES: dict[str, str] = {
    "processos":  "Carregando processos...",
    "okr":        "Calculando OKR de produtividade...",
    "detalhe":    "Buscando detalhes do processo...",
    "ranking":    "Montando ranking de processos...",
}

PAGE_ICONS: dict[str, str] = {
    "painel":     "📋",
    "okr":        "🎯",
    "consulta":   "🔎",
    "metodologia":"📘",
}
