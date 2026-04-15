"""
app.py — Painel COATE
"""

import os
import base64
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from coate_auth import (
    fazer_login,
    fazer_logout,
    inicializar_sessao,
    listar_modulos_permitidos,
    obter_usuario_atual,
    usuario_esta_logado,
    usuario_eh_admin,
    usuario_com_senha_provisoria,
)
from coate_access_store import garantir_estrutura_segurança, registrar_solicitacao
from coate_config import (
    COATE_FOOTER, COATE_FULL_NAME, COATE_ICON,
    COATE_KICKER, COATE_SUBTITLE, COATE_TITLE,
    PAGE_TITLES,
    COATE_AREAS, COATE_PROJETOS_ESPECIAIS,
)
from coate_styles import aplicar_estilos

_ROOT = os.path.dirname(os.path.abspath(__file__))
_ASSETS = os.path.join(_ROOT, "assets")
_PAGES_DIR = os.path.join(_ROOT, "pages")


def _img(filename: str, size: int = 44) -> str:
    path = os.path.join(_ASSETS, filename)
    if not filename or not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return (
        f'<img src="data:image/png;base64,{b64}" '
        f'style="height:{size}px;width:{size}px;object-fit:contain;border-radius:8px;" alt="">'
    )


_ICO_BRASAO = _img("brasao_coate.png", 160)
_ICO_CNAE = _img("cnae_icon.png", 44)
_ICO_FAROL = ""
_ICO_SN = _img("simples_nacional_icon.png", 44)
_ICO_ITCD = _img("itcd_icon.png", 44)
_ICO_ATD = ""

try:
    from PIL import Image as _PIL
    _icon_file = os.path.join(_ASSETS, "coate_app_icon.png")
    _page_icon = _PIL.open(_icon_file) if os.path.exists(_icon_file) else COATE_ICON
except Exception:
    _page_icon = COATE_ICON

st.set_page_config(
    page_title=PAGE_TITLES["home"],
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_estilos()
inicializar_sessao()
garantir_estrutura_segurança()


def _render_home():
    st.markdown(
        f"""
        <div class="coate-hero">
            <div class="coate-hero-kicker">🏛️ {COATE_KICKER}</div>
            <div style="display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;">
                {f'<div style="flex-shrink:0;">{_ICO_BRASAO}</div>' if _ICO_BRASAO else ""}
                <div>
                    <h1 style="margin:0 0 0.4rem 0;">{COATE_TITLE}</h1>
                    <p style="margin:0 0 0.3rem 0;">{COATE_SUBTITLE}</p>
                    <p style="color:var(--text-muted);font-size:0.88rem;margin:0;">
                        {COATE_FULL_NAME} · SEFAZ-CE
                    </p>
                    <div class="coate-chip-row" style="margin-top:0.9rem;">
                        <span class="coate-chip">🚦 FAROL</span>
                        <span class="coate-chip">🔄 Reclassificação CNAE</span>
                        <span class="coate-chip">🟡 Simples Nacional</span>
                        <span class="coate-chip">🌳 ITCD</span>
                        <span class="coate-chip">🧾 Atendimento</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="coate-section">
            <div class="coate-section-super">⭐ Projetos Especiais</div>
            <div class="coate-section-title">Módulos Ativos</div>
            <div class="coate-section-desc">Ferramentas analíticas e de inteligência fiscal em produção.</div>
        </div>
        <hr class="coate-section-divider"/>
        """,
        unsafe_allow_html=True,
    )

    _proj_icons = {"farol": _ICO_FAROL, "cnae": _ICO_CNAE}
    cols = st.columns(len(COATE_PROJETOS_ESPECIAIS))
    for col, projeto in zip(cols, COATE_PROJETOS_ESPECIAIS):
        paginas_html = "".join(f'<span class="coate-chip" style="margin-top:0.3rem;">{p}</span>' for p in projeto["paginas"])
        ico = _proj_icons.get(projeto["id"], "")
        ico_html = ico if ico else f'<span style="font-size:1.6rem;">{projeto["icon"]}</span>'
        with col:
            st.markdown(
                f"""
                <div class="coate-nav-card">
                    <div class="coate-nav-card-header">
                        <div style="flex-shrink:0;">{ico_html}</div>
                        <div>
                            <div class="coate-nav-card-title">{projeto["title"]}</div>
                            <div class="coate-nav-card-subtitle">{projeto["subtitle"]}</div>
                        </div>
                    </div>
                    <p class="coate-nav-card-desc">{projeto["desc"]}</p>
                    <span class="coate-nav-badge ativo">● Ativo</span>
                    <div class="coate-chip-row" style="margin-top:0.8rem;">{paginas_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="coate-section">
            <div class="coate-section-super">📂 Áreas de Atuação</div>
            <div class="coate-section-title">Expansão do Painel</div>
            <div class="coate-section-desc">Novos módulos analíticos incorporados progressivamente.</div>
        </div>
        <hr class="coate-section-divider"/>
        """,
        unsafe_allow_html=True,
    )

    _area_icons = {"simples_nacional": _ICO_SN, "itcd": _ICO_ITCD, "atendimento": _ICO_ATD}
    cols2 = st.columns(len(COATE_AREAS))
    for col, area in zip(cols2, COATE_AREAS):
        ico = _area_icons.get(area["id"], "")
        ico_html = ico if ico else f'<span style="font-size:1.6rem;">{area["icon"]}</span>'
        _is_ativo = area.get("status") == "ativo"
        _opacity = "1" if _is_ativo else "0.75"
        _badge = '<span class="coate-nav-badge ativo">● Ativo</span>' if _is_ativo else '<span class="coate-nav-badge em_breve">⏳ Em breve</span>'
        _subtitle_html = f'<div class="coate-nav-card-subtitle">{area["subtitle"]}</div>' if area.get("subtitle") else ""
        _chips_html = "".join(f'<span class="coate-chip" style="margin-top:0.3rem;">{p}</span>' for p in area.get("projetos", []))
        _chips_block = f'<div class="coate-chip-row" style="margin-top:0.8rem;">{_chips_html}</div>' if _chips_html else ""
        with col:
            st.markdown(
                f"""
                <div class="coate-nav-card" style="opacity:{_opacity};">
                    <div class="coate-nav-card-header">
                        <div style="flex-shrink:0;">{ico_html}</div>
                        <div>
                            <div class="coate-nav-card-title">{area["title"]}</div>
                            {_subtitle_html}
                        </div>
                    </div>
                    <p class="coate-nav-card-desc">{area["desc"]}</p>
                    {_badge}
                    {_chips_block}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="coate-panel">
            <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.7rem;">
                <span style="font-size:1.2rem;">🧭</span>
                <span style="font-size:1rem;font-weight:700;color:#f1f5f9;">Como navegar</span>
            </div>
            <p>Use o menu lateral para acessar os módulos liberados ao seu perfil. Cada módulo mantém suas páginas próprias de análise, consulta e metodologia.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="coate-footer">{COATE_FOOTER}</div>', unsafe_allow_html=True)


def _render_login() -> None:
    st.markdown(
        f"""
        <div class="coate-hero">
            <div class="coate-hero-kicker">🔐 Acesso restrito</div>
            <div style="display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;">
                {f'<div style="flex-shrink:0;">{_ICO_BRASAO}</div>' if _ICO_BRASAO else ""}
                <div>
                    <h1 style="margin:0 0 0.4rem 0;">{COATE_TITLE}</h1>
                    <p style="margin:0 0 0.3rem 0;">Autenticação de usuários</p>
                    <p style="color:var(--text-muted);font-size:0.92rem;margin:0;">
                        Faça login para acessar os módulos permitidos ao seu perfil ou solicite autorização.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b, col_c = st.columns([1, 1.35, 1])
    with col_b:
        tab_login, tab_solic = st.tabs(["Entrar", "Solicitar autorização"])

        with tab_login:
            with st.form("form_login"):
                login = st.text_input("Login")
                senha = st.text_input("Senha", type="password")
                entrar = st.form_submit_button("Entrar", use_container_width=True)
            if entrar:
                ok, mensagem = fazer_login(login, senha)
                if ok:
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.error(mensagem)

        with tab_solic:
            with st.form("form_solicitacao"):
                nome = st.text_input("Nome completo")
                login_desejado = st.text_input("Login desejado")
                email = st.text_input("E-mail institucional")
                setor = st.text_input("Setor / unidade")
                justificativa = st.text_area("Justificativa de uso", height=120)
                c1, c2 = st.columns(2)
                with c1:
                    deseja_itcd = st.checkbox("ITCD")
                    deseja_simples = st.checkbox("Simples Nacional")
                    deseja_atendimento = st.checkbox("Atendimento")
                with c2:
                    deseja_farol = st.checkbox("FAROL")
                    deseja_cnae = st.checkbox("Reclassificação CNAE")
                enviar = st.form_submit_button("Enviar solicitação", use_container_width=True)

            if enviar:
                ok, mensagem = registrar_solicitacao(
                    nome=nome,
                    login_desejado=login_desejado,
                    email=email,
                    setor=setor,
                    justificativa=justificativa,
                    deseja_itcd=deseja_itcd,
                    deseja_simples=deseja_simples,
                    deseja_atendimento=deseja_atendimento,
                    deseja_farol=deseja_farol,
                    deseja_cnae=deseja_cnae,
                )
                if ok:
                    st.success(mensagem)
                else:
                    st.error(mensagem)


def _montar_paginas_permitidas():
    pg_home = st.Page(_render_home, title="Home COATE", icon="🏛️", default=True)

    pg_farol_visao = st.Page(os.path.join(_PAGES_DIR, "1_FAROL_Visao_Geral.py"), title="Visão Geral", icon="📊")
    pg_farol_ranking = st.Page(os.path.join(_PAGES_DIR, "2_FAROL_Ranking_de_Analise.py"), title="Ranking de Análise", icon="🏁")
    pg_farol_consulta = st.Page(os.path.join(_PAGES_DIR, "3_FAROL_Consulta_de_Contribuinte.py"), title="Consulta do Contribuinte", icon="🔎")
    pg_farol_explora = st.Page(os.path.join(_PAGES_DIR, "4_FAROL_Exploracao_da_Base.py"), title="Exploração da Base", icon="🧪")
    pg_farol_agente = st.Page(os.path.join(_PAGES_DIR, "5_FAROL_Agente.py"), title="Agente FAROL", icon="🤖")
    pg_farol_metod = st.Page(os.path.join(_PAGES_DIR, "6_FAROL_Metodologia.py"), title="Metodologia", icon="📘")
    pg_farol_bares = st.Page(os.path.join(_PAGES_DIR, "23_FAROL_Bares.py"), title="Bares e Restaurantes", icon="🍺")

    pg_cnae_visao = st.Page(os.path.join(_PAGES_DIR, "1_CNAE_Visao_Geral.py"), title="Visão Geral", icon="📊")
    pg_cnae_ranking = st.Page(os.path.join(_PAGES_DIR, "2_CNAE_Ranking_de_Reclassificacao.py"), title="Ranking de Reclassificação", icon="🏁")
    pg_cnae_consulta = st.Page(os.path.join(_PAGES_DIR, "3_CNAE_Consulta_do_Contribuinte.py"), title="Consulta do Contribuinte", icon="🔎")
    pg_cnae_explora = st.Page(os.path.join(_PAGES_DIR, "4_CNAE_Exploracao_da_Base.py"), title="Exploração da Base", icon="🧪")
    pg_cnae_metod = st.Page(os.path.join(_PAGES_DIR, "5_CNAE_Metodologia.py"), title="Metodologia", icon="📘")
    pg_cnae_qualidade = st.Page(os.path.join(_PAGES_DIR, "6_CNAE_Qualidade_do_Modelo.py"), title="Qualidade do Modelo", icon="🧠")
    pg_cnae_impacto = st.Page(os.path.join(_PAGES_DIR, "14_CNAE_Matriz_de_Impacto.py"), title="Matriz de Impacto", icon="💹")
    pg_cnae_decretos = st.Page(os.path.join(_PAGES_DIR, "15_CNAE_Lista_de_CNAEs_por_Decreto.py"), title="CNAEs por Decreto", icon="📚")

    pg_sn_notif = st.Page(os.path.join(_PAGES_DIR, "7_SN_Notificacao_de_Eventos.py"), title="Notificação de Eventos", icon="🔔")
    pg_sn_pgdas_dimp = st.Page(os.path.join(_PAGES_DIR, "13_SN_Notificacao_PGDAS_X_DIMP.py"), title="Notificação PGDAS X DIMP", icon="🧮")
    pg_sn_icms_st = st.Page(os.path.join(_PAGES_DIR, "14_SN_Diferenca_ICMS_ST_Recolhido.py"), title="Diferença ICMS-ST Recolhido", icon="💰")
    pg_sn_omissao_pgdas = st.Page(os.path.join(_PAGES_DIR, "15_SN_Omissao_PGDAS.py"), title="Omissão PGDAS", icon="🚫")
    pg_sn_omissao_defis = st.Page(os.path.join(_PAGES_DIR, "16_SN_Omissao_DEFIS.py"), title="Omissão DEFIS", icon="📋")
    pg_sn_sublimites = st.Page(os.path.join(_PAGES_DIR, "17_SN_Sublimites_e_Limites.py"), title="Sublimites e Limites", icon="⚠️")
    pg_sn_segregacao = st.Page(os.path.join(_PAGES_DIR, "18_SN_Segregacao_Indevida.py"), title="Segregação Indevida", icon="🔍")
    pg_sn_efetividade = st.Page(os.path.join(_PAGES_DIR, "19_SN_Efetividade_PGDAS.py"), title="Efetividade das Notificações", icon="📈")
    pg_sn_contribuintes = st.Page(os.path.join(_PAGES_DIR, "21_SN_Contribuintes.py"), title="Contribuintes", icon="🏪")
    pg_sn_pgdas = st.Page(os.path.join(_PAGES_DIR, "22_SN_PGDAS.py"), title="Declarações PGDAS", icon="📋")
    pg_itcd_painel = st.Page(os.path.join(_PAGES_DIR, "8_ITCD_Painel_de_Processos.py"), title="Painel de Processos", icon="📋")
    pg_itcd_consulta = st.Page(os.path.join(_PAGES_DIR, "10_ITCD_Consulta_do_Processo.py"), title="Consulta do Processo", icon="🔎")
    pg_atendimento = st.Page(os.path.join(_PAGES_DIR, "11_ATD_Atendimento.py"), title="Página Inicial do Módulo", icon="🧾")
    pg_admin = st.Page(os.path.join(_PAGES_DIR, "12_Admin_Gestao_de_Acessos.py"), title="Gestão de Acessos", icon="🛡️")
    pg_minha_conta = st.Page(os.path.join(_PAGES_DIR, "20_Minha_Conta.py"), title="Minha Conta", icon="👤")

    modulos = set(listar_modulos_permitidos())
    nav_items = {"Painel COATE": [pg_home, pg_minha_conta]}

    if "farol" in modulos:
        nav_items["FAROL"] = [pg_farol_visao, pg_farol_ranking, pg_farol_consulta, pg_farol_explora, pg_farol_agente, pg_farol_metod, pg_farol_bares]
    if "cnae" in modulos:
        nav_items["Reclassificação CNAE"] = [pg_cnae_visao, pg_cnae_ranking, pg_cnae_consulta, pg_cnae_explora, pg_cnae_metod, pg_cnae_qualidade, pg_cnae_impacto, pg_cnae_decretos]
    if "simples" in modulos:
        nav_items["Simples Nacional"] = [pg_sn_notif, pg_sn_pgdas_dimp, pg_sn_icms_st, pg_sn_omissao_pgdas, pg_sn_omissao_defis, pg_sn_sublimites, pg_sn_segregacao, pg_sn_efetividade, pg_sn_contribuintes, pg_sn_pgdas]
    if "itcd" in modulos:
        nav_items["ITCD"] = [pg_itcd_painel, pg_itcd_consulta]
    if "atendimento" in modulos:
        nav_items["Atendimento"] = [pg_atendimento]
    if usuario_eh_admin():
        nav_items["Administração"] = [pg_admin]

    return nav_items


if not usuario_esta_logado():
    _render_login()
else:
    usuario = obter_usuario_atual()
    with st.sidebar:
        st.markdown(f"**Usuário:** {usuario['nome']}")
        st.caption(usuario["login"])
        if usuario.get("admin"):
            st.caption("Perfil administrador")
        if usuario_com_senha_provisoria():
            st.warning("🔑 Senha provisória — altere em **Minha Conta**", icon=None)
        if st.button("Sair", use_container_width=True):
            fazer_logout()
            st.rerun()

    nav = st.navigation(_montar_paginas_permitidas(), position="sidebar")
    nav.run()
