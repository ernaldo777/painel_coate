"""
coate_styles.py
===============
Design system unificado do Painel COATE.

Herda o dark theme robusto do FAROL e incorpora os tokens CSS
do módulo CNAE (variáveis CSS :root, KPI cards, hero, etc.).

Como usar em qualquer página:
    from coate_styles import aplicar_estilos, loading

Funções exportadas:
    aplicar_estilo_base()       — fundo, sidebar, tipografia, scrollbar
    aplicar_componentes_comuns()— classes .coate-* compartilhadas
    aplicar_estilos()           — atalho: chama as duas acima
    aplicar_estilo_loading()    — spinner dark
    loading(msg)                — context manager de loading
"""

import streamlit as st


# =============================================================
# BLOCO BASE
# Tokens CSS :root + reset + fundo + sidebar + scrollbar
# =============================================================
def aplicar_estilo_base() -> None:
    st.markdown(
        """
        <style>

        /* ============================================================
           TOKENS CSS GLOBAIS
        ============================================================ */
        :root {
            --bg-app:          #07101d;
            --bg-surface:      #0f172a;
            --bg-elevated:     #1e293b;
            --bg-card:         #111827;
            --bg-soft:         #172033;

            --border:          rgba(148, 163, 184, 0.14);
            --border-strong:   rgba(148, 163, 184, 0.26);
            --border-accent:   rgba(59, 130, 246, 0.30);

            --text-primary:    #f1f5f9;
            --text-soft:       #cbd5e1;
            --text-muted:      #64748b;
            --text-faint:      #475569;

            --primary:         #3b82f6;
            --primary-soft:    rgba(59, 130, 246, 0.14);
            --primary-glow:    rgba(59, 130, 246, 0.07);

            --success:         #22c55e;
            --success-soft:    rgba(34, 197, 94, 0.14);
            --danger:          #ef4444;
            --danger-soft:     rgba(239, 68, 68, 0.14);
            --warning:         #f59e0b;
            --warning-soft:    rgba(245, 158, 11, 0.14);
            --info:            #38bdf8;
            --info-soft:       rgba(56, 189, 248, 0.14);
            --purple:          #8b5cf6;
            --purple-soft:     rgba(139, 92, 246, 0.14);

            --shadow-sm:  0 2px  8px  rgba(0,0,0,0.24);
            --shadow-md:  0 8px  24px rgba(0,0,0,0.32);
            --shadow-lg:  0 16px 48px rgba(0,0,0,0.40);
            --shadow-glow:0 0   28px  rgba(59,130,246,0.10);

            --radius-sm:   10px;
            --radius-md:   16px;
            --radius-lg:   22px;
            --radius-xl:   28px;
            --radius-pill: 999px;

            --font: "Segoe UI", Inter, ui-sans-serif, system-ui,
                    -apple-system, BlinkMacSystemFont, sans-serif;
            --transition: 180ms cubic-bezier(0.4, 0, 0.2, 1);
        }

        /* ============================================================
           RESET & TIPOGRAFIA
        ============================================================ */
        html, body, [class*="css"] {
            font-family: var(--font) !important;
        }

        * { box-sizing: border-box; }

        h1, h2, h3, h4, h5, h6, p, div, span, label {
            color: #e5e7eb;
        }

        /* ============================================================
           FUNDO DO APP
        ============================================================ */
        .stApp {
            background:
                radial-gradient(ellipse 80% 50% at 50% -20%,
                    rgba(59,130,246,0.08) 0%, transparent 60%),
                radial-gradient(circle at top right, rgba(37,99,235,0.10), transparent 28%),
                linear-gradient(180deg, #07101d 0%, #0a1220 46%, #111827 100%);
            color: var(--text-primary);
        }

        /* ============================================================
           CABEÇALHO NATIVO (ocultar)
        ============================================================ */
        header[data-testid="stHeader"],
        .stAppHeader,
        [data-testid="stToolbar"] {
            background: transparent !important;
        }

        /* ============================================================
           CONTAINER PRINCIPAL
        ============================================================ */
        .block-container {
            padding-top: 1.05rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 1500px;
        }

        /* ============================================================
           SCROLLBAR
        ============================================================ */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb {
            background: rgba(148,163,184,0.18);
            border-radius: 99px;
        }
        ::-webkit-scrollbar-thumb:hover { background: rgba(148,163,184,0.34); }

        /* ============================================================
           SIDEBAR
        ============================================================ */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b1220 0%, #0f172a 100%) !important;
            border-right: 1px solid var(--border);
        }

        section[data-testid="stSidebar"] > div,
        [data-testid="stSidebarContent"],
        [data-testid="stSidebarNav"] {
            background: transparent !important;
        }

        [data-testid="stSidebarContent"] {
            padding-top: 0.8rem;
        }

        section[data-testid="stSidebar"] label {
            color: var(--text-soft) !important;
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em;
        }

        /* Navegação */
        [data-testid="stSidebarNav"] ul { gap: 0.3rem; }
        [data-testid="stSidebarNav"] li { margin-bottom: 0.2rem; }

        /* Mais separação entre os grupos principais da sidebar */
        [data-testid="stSidebarNav"] > ul > li {
            margin-top: 0.95rem;
        }

        [data-testid="stSidebarNav"] > ul > li:first-child {
            margin-top: 0.15rem;
        }

        /* Mais destaque para os títulos dos módulos do que para os subitens */
        [data-testid="stSidebarNav"] > ul > li > div,
        [data-testid="stSidebarNav"] > ul > li > header,
        [data-testid="stSidebarNav"] > ul > li > span,
        [data-testid="stSidebarNav"] > ul > li > p {
            color: #f1f5f9 !important;
            font-size: 0.98rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.01em;
            margin-bottom: 0.35rem !important;
        }

        [data-testid="stSidebarNav"] > ul > li ul {
            margin-top: 0.2rem;
        }

        [data-testid="stSidebarNav"] > ul > li ul li {
            margin-bottom: 0.1rem;
        }

        [data-testid="stSidebarNav"] > ul > li ul li a {
            color: #cbd5e1 !important;
            font-size: 0.92rem !important;
            font-weight: 500 !important;
            padding-left: 0.85rem;
        }

        [data-testid="stSidebarNav"] a {
            color: #cbd5e1 !important;
            border-radius: 12px;
            padding: 0.5rem 0.75rem;
            transition: all var(--transition);
        }

        [data-testid="stSidebarNav"] a:hover {
            background: rgba(59, 130, 246, 0.10) !important;
            color: #ffffff !important;
        }

        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: linear-gradient(90deg,
                rgba(37,99,235,0.22), rgba(59,130,246,0.10)) !important;
            color: #ffffff !important;
            font-weight: 600;
            border: 1px solid rgba(96,165,250,0.18);
        }


        /* ============================================================
           FORMULÁRIOS / AUTENTICAÇÃO / ADMIN
        ============================================================ */
        [data-testid="stForm"] {
            background: rgba(15, 23, 42, 0.35);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 0.8rem 1rem 0.2rem 1rem;
        }

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        textarea {
            background: rgba(15, 23, 42, 0.65) !important;
            color: var(--text-primary) !important;
        }

        .stAlert {
            border-radius: var(--radius-md);
        }

        /* ============================================================
           MÉTRICAS NATIVAS
        ============================================================ */
        [data-testid="metric-container"] {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
            padding: 0.9rem 1rem !important;
            box-shadow: var(--shadow-md);
        }

        [data-testid="metric-container"] label {
            color: #93c5fd !important;
            font-weight: 600;
        }

        [data-testid="metric-container"] [data-testid="stMetricValue"] {
            color: #f8fafc;
            font-weight: 700;
        }

        /* ============================================================
           TABS
        ============================================================ */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.2rem;
            background: transparent;
            border-bottom: 1px solid var(--border);
        }

        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border-radius: var(--radius-sm) var(--radius-sm) 0 0;
            color: var(--text-muted) !important;
            font-weight: 600;
            font-size: 0.87rem;
            padding: 0.5rem 1rem;
            border: none;
        }

        .stTabs [aria-selected="true"] {
            background: var(--primary-soft) !important;
            color: #93c5fd !important;
            border-bottom: 2px solid var(--primary) !important;
        }

        /* ============================================================
           BOTÕES
        ============================================================ */
        .stButton > button {
            background: var(--primary-soft);
            border: 1px solid rgba(59,130,246,0.28) !important;
            color: #93c5fd !important;
            border-radius: var(--radius-md) !important;
            font-weight: 700 !important;
            font-size: 0.88rem !important;
            min-height: 42px !important;
            transition: all var(--transition);
        }

        .stButton > button:hover {
            background: rgba(59,130,246,0.24) !important;
            border-color: var(--primary) !important;
            color: #bfdbfe !important;
        }

        .stDownloadButton > button {
            background: linear-gradient(135deg,
                rgba(59,130,246,0.17), rgba(59,130,246,0.09)) !important;
            border: 1px solid rgba(59,130,246,0.32) !important;
            color: #93c5fd !important;
            border-radius: var(--radius-md) !important;
            font-weight: 700 !important;
        }

        /* ============================================================
           SELECTS & INPUTS
        ============================================================ */
        .stSelectbox > div > div,
        .stMultiSelect > div > div {
            background: var(--bg-elevated) !important;
            border: 1px solid var(--border-strong) !important;
            border-radius: var(--radius-sm) !important;
            color: var(--text-soft) !important;
        }

        /* ============================================================
           EXPANDER
        ============================================================ */
        .streamlit-expanderHeader {
            background: var(--bg-elevated) !important;
            border-radius: var(--radius-sm) !important;
            color: var(--text-soft) !important;
            font-weight: 700 !important;
            font-size: 0.88rem !important;
        }

        /* ============================================================
           ALERTAS
        ============================================================ */
        [data-testid="stAlert"] {
            border-radius: var(--radius-md) !important;
            border: 1px solid var(--border) !important;
        }

        /* ============================================================
           DATAFRAME
        ============================================================ */
        div[data-testid="stDataFrame"] {
            border-radius: var(--radius-md) !important;
            overflow: hidden;
            border: 1px solid var(--border) !important;
            box-shadow: var(--shadow-sm);
        }

        /* ============================================================
           CAPTION
        ============================================================ */
        .stCaption { color: var(--text-muted) !important; font-size: 0.82rem !important; }

        /* ============================================================
           RESPONSIVO
        ============================================================ */
        @media (max-width: 900px) {
            .block-container { padding-top: 0.8rem !important; }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================
# COMPONENTES COMUNS
# Classes .coate-* usadas em 2 ou mais páginas/módulos.
# =============================================================
def aplicar_componentes_comuns() -> None:
    st.markdown(
        """
        <style>

        /* ============================================================
           HERO DA PÁGINA
        ============================================================ */
        .coate-hero {
            position: relative;
            overflow: hidden;
            padding: 1.5rem 1.7rem;
            border-radius: var(--radius-xl);
            background: linear-gradient(135deg,
                rgba(30,41,59,0.94) 0%,
                rgba(15,23,42,0.98) 60%,
                rgba(11,18,35,0.99) 100%);
            border: 1px solid var(--border-accent);
            box-shadow: var(--shadow-lg), var(--shadow-glow);
            margin-bottom: 1.2rem;
        }

        .coate-hero::before {
            content: "";
            position: absolute;
            top: -70px; right: -50px;
            width: 280px; height: 280px;
            background: radial-gradient(circle,
                rgba(59,130,246,0.11), transparent 70%);
            border-radius: 50%;
            pointer-events: none;
        }

        .coate-hero::after {
            content: "";
            position: absolute;
            bottom: -80px; left: 30%;
            width: 320px; height: 160px;
            background: radial-gradient(ellipse,
                rgba(139,92,246,0.06), transparent 70%);
            pointer-events: none;
        }

        .coate-hero-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.26rem 0.72rem;
            border-radius: var(--radius-pill);
            background: var(--primary-soft);
            border: 1px solid rgba(59,130,246,0.26);
            color: #93c5fd;
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            margin-bottom: 0.85rem;
        }

        .coate-hero h1 {
            color: #f8fafc;
            font-size: 2rem;
            font-weight: 800;
            margin: 0 0 0.5rem 0;
            line-height: 1.15;
            letter-spacing: -0.02em;
        }

        .coate-hero p {
            color: var(--text-soft);
            font-size: 0.97rem;
            margin: 0 0 0.35rem 0;
            max-width: 960px;
            line-height: 1.65;
        }

        .coate-hero-layout {
            display: flex;
            align-items: center;
            gap: 1.8rem;
        }

        .coate-hero-media {
            flex: 0 0 auto;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .coate-hero-image-frame {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 280px;
            height: 360px;
            padding: 1rem;
            border-radius: 34px;
            background: radial-gradient(circle at 50% 35%, rgba(10,30,70,0.55) 0%, rgba(2,6,23,0.96) 58%, rgba(2,6,23,1) 100%);
            border: 1px solid rgba(96,165,250,0.30);
            box-shadow: 0 18px 44px rgba(0,0,0,0.42), 0 0 42px rgba(59,130,246,0.14), inset 0 0 28px rgba(59,130,246,0.08);
        }

        .coate-hero-image {
            width: 100%;
            height: 100%;
            object-fit: contain;
            image-rendering: auto;
            filter: drop-shadow(0 16px 28px rgba(0,0,0,0.40)) saturate(1.08) contrast(1.06) brightness(1.03);
        }

        .coate-hero-content {
            flex: 1 1 auto;
            min-width: 0;
        }

        @media (max-width: 900px) {
            .coate-hero-layout {
                flex-direction: column;
                align-items: flex-start;
            }

            .coate-hero-image-frame {
                width: 210px;
                height: 270px;
                border-radius: 28px;
            }
        }

        /* ============================================================
           SIDEBAR BRAND
        ============================================================ */
        .coate-sidebar-brand {
            position: relative;
            overflow: hidden;
            background: linear-gradient(135deg,
                rgba(59,130,246,0.13) 0%,
                rgba(15,23,42,0.97) 80%);
            border: 1px solid var(--border-accent);
            border-radius: var(--radius-lg);
            padding: 1rem 1.1rem;
            margin-bottom: 1.2rem;
            box-shadow: var(--shadow-md), var(--shadow-glow);
        }

        .coate-sidebar-brand::before {
            content: "";
            position: absolute;
            top: -36px; right: -36px;
            width: 100px; height: 100px;
            background: radial-gradient(circle,
                rgba(59,130,246,0.18), transparent 70%);
            border-radius: 50%;
            pointer-events: none;
        }

        .coate-sidebar-brand-title {
            font-size: 1rem;
            font-weight: 800;
            color: #f8fafc;
            letter-spacing: -0.01em;
            margin: 0;
        }

        .coate-sidebar-brand-sub {
            color: var(--text-muted);
            font-size: 0.75rem;
            margin-top: 0.3rem;
            line-height: 1.4;
        }

        .coate-sidebar-divider {
            height: 1px;
            background: var(--border);
            margin: 0.85rem 0;
            border: none;
        }

        /* ============================================================
           CARD GENÉRICO
        ============================================================ */
        .coate-card {
            border: 1px solid var(--border);
            background: rgba(15, 23, 42, 0.76);
            border-radius: var(--radius-lg);
            padding: 1.1rem 1.2rem;
            box-shadow: var(--shadow-md);
            margin-bottom: 1rem;
        }

        .coate-card:hover {
            border-color: var(--border-strong);
            box-shadow: var(--shadow-lg);
        }

        /* ============================================================
           KPI CARD CUSTOMIZADO
        ============================================================ */
        .coate-kpi-card {
            position: relative;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1.1rem 1.2rem 1rem 1.35rem;
            box-shadow: var(--shadow-md);
            min-height: 148px;
            overflow: hidden;
            transition: transform var(--transition),
                        border-color var(--transition),
                        box-shadow var(--transition);
        }

        .coate-kpi-card:hover {
            transform: translateY(-2px);
            border-color: var(--border-strong);
            box-shadow: var(--shadow-lg);
        }

        /* barra de acento lateral */
        .coate-kpi-card::before {
            content: "";
            position: absolute;
            left: 0; top: 18px; bottom: 18px;
            width: 3px;
            border-radius: 0 3px 3px 0;
            background: var(--kpi-accent, var(--primary));
            opacity: 0.90;
        }

        /* glow lateral */
        .coate-kpi-card::after {
            content: "";
            position: absolute;
            left: 0; top: 0; bottom: 0;
            width: 64px;
            background: linear-gradient(90deg,
                var(--kpi-accent-soft, var(--primary-glow)), transparent);
            pointer-events: none;
        }

        .coate-kpi-card.accent-success { --kpi-accent: var(--success); --kpi-accent-soft: var(--success-soft); }
        .coate-kpi-card.accent-danger  { --kpi-accent: var(--danger);  --kpi-accent-soft: var(--danger-soft);  }
        .coate-kpi-card.accent-warning { --kpi-accent: var(--warning); --kpi-accent-soft: var(--warning-soft); }
        .coate-kpi-card.accent-info    { --kpi-accent: var(--info);    --kpi-accent-soft: var(--info-soft);    }
        .coate-kpi-card.accent-purple  { --kpi-accent: var(--purple);  --kpi-accent-soft: var(--purple-soft);  }
        .coate-kpi-card.accent-primary { --kpi-accent: var(--primary); --kpi-accent-soft: var(--primary-soft); }

        .coate-kpi-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.5rem;
            margin-bottom: 0.8rem;
        }

        .coate-kpi-label {
            color: var(--text-muted);
            font-size: 0.77rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            line-height: 1.35;
        }

        .coate-kpi-icon {
            width: 35px; height: 35px;
            border-radius: var(--radius-sm);
            display: flex; align-items: center; justify-content: center;
            font-size: 1rem;
            background: rgba(255,255,255,0.04);
            border: 1px solid var(--border);
            flex-shrink: 0;
        }

        .coate-kpi-value {
            color: #f8fafc;
            font-size: 2.05rem;
            line-height: 1;
            font-weight: 800;
            letter-spacing: -0.035em;
            margin-bottom: 0.55rem;
        }

        .coate-kpi-delta {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            font-size: 0.76rem;
            font-weight: 700;
            padding: 0.2rem 0.58rem;
            border-radius: var(--radius-pill);
            margin-bottom: 0.4rem;
        }

        .coate-kpi-help {
            color: var(--text-faint);
            font-size: 0.75rem;
            line-height: 1.4;
            margin-top: 0.18rem;
        }

        .delta-success { background: var(--success-soft); color: #86efac; }
        .delta-danger  { background: var(--danger-soft);  color: #fca5a5; }
        .delta-warning { background: var(--warning-soft); color: #fcd34d; }
        .delta-primary { background: var(--primary-soft); color: #93c5fd; }
        .delta-info    { background: var(--info-soft);    color: #7dd3fc; }
        .delta-purple  { background: var(--purple-soft);  color: #c4b5fd; }

        /* ============================================================
           SEÇÃO — TÍTULOS
        ============================================================ */
        .coate-section { margin: 1.4rem 0 0.8rem 0; }

        .coate-section-super {
            color: var(--primary);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.10em;
            margin-bottom: 0.22rem;
        }

        .coate-section-title {
            color: #f1f5f9;
            font-size: 1.12rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            margin: 0;
        }

        .coate-section-desc {
            color: var(--text-muted);
            font-size: 0.86rem;
            margin-top: 0.22rem;
            line-height: 1.5;
        }

        .coate-section-divider {
            height: 1px;
            background: linear-gradient(90deg, var(--border-accent), transparent);
            margin: 0.5rem 0 1rem 0;
            border: none;
        }

        /* ============================================================
           PANEL
        ============================================================ */
        .coate-panel {
            position: relative;
            margin-top: 0.75rem;
            padding: 1.2rem 1.5rem;
            border-radius: var(--radius-lg);
            background: linear-gradient(160deg,
                rgba(19,28,46,0.96) 0%,
                rgba(15,23,42,0.96) 100%);
            border: 1px solid var(--border);
            box-shadow: var(--shadow-md);
        }

        .coate-panel p { color: var(--text-soft); font-size: 0.96rem; line-height: 1.65; margin: 0; }
        .coate-panel strong { color: #f1f5f9; }

        /* ============================================================
           CARDS DE NAVEGAÇÃO (Home)
        ============================================================ */
        .coate-nav-card {
            position: relative;
            background: linear-gradient(160deg,
                rgba(19,28,46,0.96), rgba(15,23,42,0.96));
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1.3rem 1.4rem;
            box-shadow: var(--shadow-md);
            transition: transform var(--transition),
                        border-color var(--transition),
                        box-shadow var(--transition);
            overflow: hidden;
            height: 100%;
        }

        .coate-nav-card:hover {
            transform: translateY(-3px);
            border-color: var(--border-accent);
            box-shadow: var(--shadow-lg), var(--shadow-glow);
        }

        .coate-nav-card-header {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin-bottom: 0.75rem;
        }

        .coate-nav-card-icon {
            font-size: 1.6rem;
            line-height: 1;
        }

        .coate-nav-card-title {
            font-size: 1.05rem;
            font-weight: 800;
            color: #f8fafc;
            margin: 0;
            letter-spacing: -0.01em;
        }

        .coate-nav-card-subtitle {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.18rem;
            line-height: 1.35;
        }

        .coate-nav-card-desc {
            font-size: 0.88rem;
            color: var(--text-soft);
            line-height: 1.6;
            margin: 0 0 0.85rem 0;
        }

        .coate-nav-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            padding: 0.22rem 0.65rem;
            border-radius: var(--radius-pill);
            font-size: 0.73rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .coate-nav-badge.ativo {
            background: var(--success-soft);
            color: #86efac;
            border: 1px solid rgba(34,197,94,0.25);
        }

        .coate-nav-badge.em_breve {
            background: var(--warning-soft);
            color: #fcd34d;
            border: 1px solid rgba(245,158,11,0.25);
        }

        /* ============================================================
           CHIPS / TAGS
        ============================================================ */
        .coate-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.75rem;
        }

        .coate-chip {
            display: inline-block;
            padding: 0.3rem 0.65rem;
            border-radius: var(--radius-pill);
            border: 1px solid var(--border);
            background: rgba(15,23,42,0.68);
            color: #dbeafe;
            font-size: 0.8rem;
            font-weight: 600;
        }

        /* ============================================================
           TABELA CUSTOMIZADA
        ============================================================ */
        .coate-table-wrap {
            overflow-x: auto;
            border-radius: var(--radius-md);
            border: 1px solid var(--border);
        }

        .coate-table {
            width: 100%;
            border-collapse: collapse;
            min-width: 700px;
            font-size: 0.91rem;
        }

        .coate-table thead th {
            background: rgba(15,23,42,0.95);
            color: #93c5fd;
            font-weight: 700;
            padding: 0.75rem 0.85rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
        }

        .coate-table tbody td {
            padding: 0.65rem 0.85rem;
            color: #e2e8f0;
            border-bottom: 1px solid rgba(148,163,184,0.07);
            vertical-align: top;
        }

        .coate-table tbody tr:nth-child(odd)  { background: rgba(15,23,42,0.55); }
        .coate-table tbody tr:nth-child(even) { background: rgba(10,18,38,0.40); }
        .coate-table tbody tr:hover           { background: rgba(37,99,235,0.08); }

        /* ============================================================
           ESTADO VAZIO
        ============================================================ */
        .coate-empty {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 2.8rem 1.5rem;
            border-radius: var(--radius-lg);
            border: 1.5px dashed var(--border-strong);
            background: rgba(15,23,42,0.55);
            gap: 0.45rem;
        }

        .coate-empty-icon  { font-size: 2.2rem; margin-bottom: 0.3rem; }
        .coate-empty-title { font-size: 0.94rem; font-weight: 700; color: var(--text-soft); }
        .coate-empty-help  { font-size: 0.82rem; color: var(--text-muted); line-height: 1.5; max-width: 340px; }

        /* ============================================================
           PRIORITY BADGE
        ============================================================ */
        .coate-priority-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.3rem 0.8rem;
            border-radius: var(--radius-pill);
            font-weight: 800;
            font-size: 0.84rem;
            border: 1px solid transparent;
            letter-spacing: 0.02em;
        }

        /* ============================================================
           ALERT PANELS CUSTOMIZADOS
        ============================================================ */
        .coate-alert {
            display: flex;
            align-items: flex-start;
            gap: 0.85rem;
            padding: 0.9rem 1.1rem;
            border-radius: var(--radius-md);
            margin: 0.5rem 0;
            border: 1px solid;
        }

        .coate-alert.alert-danger  { background: var(--danger-soft);  border-color: rgba(239,68,68,0.3);  color: #fca5a5; }
        .coate-alert.alert-warning { background: var(--warning-soft); border-color: rgba(245,158,11,0.3); color: #fcd34d; }
        .coate-alert.alert-success { background: var(--success-soft); border-color: rgba(34,197,94,0.3);  color: #86efac; }
        .coate-alert.alert-info    { background: var(--info-soft);    border-color: rgba(56,189,248,0.3); color: #7dd3fc; }

        .coate-alert-icon { font-size: 1.15rem; flex-shrink: 0; margin-top: 1px; }
        .coate-alert-body { font-size: 0.87rem; font-weight: 600; line-height: 1.45; }
        .coate-alert-body strong { font-weight: 800; }

        /* ============================================================
           FOOTER
        ============================================================ */
        .coate-footer {
            margin-top: 2.2rem;
            padding-top: 1.2rem;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 0.80rem;
            text-align: center;
            line-height: 1.6;
        }

        /* ============================================================
           TAGS DE FILTRO ATIVO
        ============================================================ */
        .coate-filter-summary {
            margin-bottom: 0.75rem;
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            align-items: center;
        }

        .coate-filter-tag {
            display: inline-block;
            padding: 0.28rem 0.65rem;
            border-radius: var(--radius-pill);
            border: 1px solid rgba(96,165,250,0.22);
            background: rgba(37,99,235,0.12);
            color: #93c5fd;
            font-size: 0.8rem;
            font-weight: 600;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================
# FUNÇÃO COMBINADA (atalho principal)
# =============================================================
def aplicar_estilos() -> None:
    """Atalho: aplica estilo base + componentes comuns."""
    aplicar_estilo_base()
    aplicar_componentes_comuns()


# =============================================================
# SPINNER CUSTOMIZADO
# =============================================================
def aplicar_estilo_loading() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stSpinner"] > div {
            background: linear-gradient(135deg,
                rgba(15,23,42,0.97), rgba(10,18,38,0.99)) !important;
            border: 1px solid rgba(148,163,184,0.16) !important;
            border-radius: 18px !important;
            padding: 1.2rem 1.8rem !important;
            box-shadow: 0 16px 40px rgba(0,0,0,0.35) !important;
            min-width: 300px !important;
        }

        div[data-testid="stSpinner"] p {
            color: #cbd5e1 !important;
            font-size: 0.97rem !important;
            font-weight: 600 !important;
        }

        div[data-testid="stSpinner"] svg {
            stroke: #60a5fa !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def loading(mensagem: str = "Carregando dados..."):
    """Context manager de loading estilizado para uso nas páginas."""
    aplicar_estilo_loading()
    return st.spinner(mensagem)


# =============================================================
# COMPONENTE: SIDEBAR BRAND
# Renderiza o bloco de identidade do painel na sidebar.
# =============================================================
def render_sidebar_brand(
    titulo: str = "Painel COATE",
    subtitulo: str = "SEFAZ-CE • Inteligência Fiscal",
    versao: str = "v1.0",
    brasao_path: str | None = None,
) -> None:
    """
    Renderiza o brand block do painel na sidebar.

    Parâmetros
    ----------
    titulo      : título principal
    subtitulo   : texto secundário
    versao      : tag de versão exibida
    brasao_path : caminho para PNG do brasão (None = sem imagem)
    """
    if brasao_path:
        try:
            import base64
            with open(brasao_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            img_html = (
                f'<img src="data:image/png;base64,{b64}" '
                f'style="height:52px;width:auto;margin-bottom:0.65rem;'
                f'display:block;border-radius:6px;" alt="Brasão COATE">'
            )
        except Exception:
            img_html = ""
    else:
        img_html = ""

    # Injeta o brand como CSS ::before no topo da sidebar — não depende do DOM do st.navigation()
    import base64 as _b64
    _ico_b64 = ""
    if brasao_path:
        try:
            with open(brasao_path, "rb") as _f:
                _ico_b64 = _b64.b64encode(_f.read()).decode()
        except Exception:
            pass

    _img_css = (
        f"url(\'data:image/png;base64,{_ico_b64}\')"
        if _ico_b64 else "none"
    )

    brand_css = f"""
    <style>
    /* Brand block fixo no topo da sidebar via CSS — independente do st.navigation() */
    section[data-testid="stSidebar"] {{
        padding-top: 0 !important;
    }}
    section[data-testid="stSidebar"]::before {{
        content: "";
        display: block;
        height: 72px;
        background:
            linear-gradient(135deg, rgba(59,130,246,0.13), rgba(11,18,35,0.99));
        border-bottom: 1px solid rgba(59,130,246,0.20);
        position: sticky;
        top: 0;
        z-index: 999;
    }}
    .coate-brand-bar {{
        position: fixed;
        top: 0;
        left: 0;
        width: 244px;
        z-index: 1000;
        background: linear-gradient(135deg, rgba(59,130,246,0.13), rgba(11,18,35,0.99));
        border-bottom: 1px solid rgba(59,130,246,0.22);
        border-right: 1px solid rgba(148,163,184,0.10);
        padding: 0.55rem 0.85rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
        box-shadow: 0 4px 16px rgba(0,0,0,0.28);
    }}
    .coate-brand-bar img {{
        height: 32px; width: 32px;
        object-fit: contain;
        border-radius: 6px;
        flex-shrink: 0;
    }}
    .coate-brand-bar-icon {{
        font-size: 1.3rem;
        flex-shrink: 0;
    }}
    .coate-brand-bar-text {{ flex: 1; min-width: 0; }}
    .coate-brand-bar-title {{
        font-size: 0.85rem; font-weight: 800;
        color: #f8fafc; margin: 0;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    .coate-brand-bar-sub {{
        font-size: 0.68rem; color: #64748b; margin: 0;
        white-space: nowrap;
    }}
    .coate-brand-bar-ver {{
        font-size: 0.6rem; font-weight: 700;
        color: #334155; letter-spacing: 0.05em;
        text-transform: uppercase; flex-shrink: 0;
    }}
    /* Empurrar o conteúdo da sidebar para baixo do brand fixo */
    section[data-testid="stSidebar"] > div:first-child {{
        padding-top: 68px !important;
    }}
    </style>
    """

    _img_tag = (
        f'<img src="data:image/png;base64,{_ico_b64}" alt="COATE">'
        if _ico_b64 else
        '<span class="coate-brand-bar-icon">🏛️</span>'
    )

    st.markdown(brand_css, unsafe_allow_html=True)
    st.markdown(
        f'''<div class="coate-brand-bar">
            {_img_tag}
            <div class="coate-brand-bar-text">
                <p class="coate-brand-bar-title">{titulo}</p>
                <p class="coate-brand-bar-sub">{subtitulo}</p>
            </div>
            <span class="coate-brand-bar-ver">{versao}</span>
        </div>''',
        unsafe_allow_html=True,
    )
