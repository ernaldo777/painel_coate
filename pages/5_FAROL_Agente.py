import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import pandas as pd
import streamlit as st
from projetos_especiais.farol.farol_config import APP_TITLE, PAGE_TITLES
from coate_styles import aplicar_estilos, loading
from coate_auth import exigir_acesso

from projetos_especiais.farol.farol_core import load_data
from projetos_especiais.farol.farol_agent.farol_agent import agente_economico
from projetos_especiais.farol.farol_rules_catalog import REGRAS_ATIVAS, RULE_NAMES, RULE_DESCRIPTIONS
from projetos_especiais.farol.farol_metadata import banner_atualizacao


def renderizar_resposta(texto: str):
    import re
    # Converte Markdown básico para HTML antes de colocar no div customizado
    html = str(texto)
    # Negrito: **texto** → <strong>texto</strong>
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    # Itálico: *texto* → <em>texto</em>
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    # Quebras de linha
    html = html.replace("\n", "<br>")
    st.markdown(
        f'<div class="farol-resposta-box">{html}</div>',
        unsafe_allow_html=True,
    )


def renderizar_tabela(df: pd.DataFrame):
    if df is None or df.empty:
        return
    st.dataframe(df, use_container_width=True, hide_index=True)


def renderizar_contexto(contexto: dict | None):
    if not contexto:
        st.caption("Nenhum contexto ativo.")
        return
    tipo = contexto.get("tipo", "N/I")
    partes = [f"<b>Tipo:</b> {tipo}"]
    if contexto.get("dimensao_nome"):
        partes.append(f"<b>Dimensão:</b> {contexto.get('dimensao_nome')}")
    if contexto.get("grupo_lider"):
        partes.append(f"<b>Grupo líder:</b> {contexto.get('grupo_lider')}")
    if contexto.get("nivel_risco"):
        partes.append(f"<b>Risco:</b> {contexto.get('nivel_risco')}")
    if contexto.get("universo") is not None:
        partes.append(f"<b>Universo:</b> {contexto.get('universo')}")
    if contexto.get("cnpj"):
        partes.append(f"<b>CNPJ:</b> {contexto.get('cnpj')}")
    if contexto.get("razao_social"):
        partes.append(f"<b>Contribuinte:</b> {contexto.get('razao_social')}")
    if contexto.get("top_n"):
        partes.append(f"<b>Top N:</b> {contexto.get('top_n')}")
    st.markdown(" | ".join(partes), unsafe_allow_html=True)


def registrar_historico(pergunta: str, resposta: str):
    historico = st.session_state.get("agente_farol_historico", [])
    historico.append({"pergunta": pergunta, "resposta": resposta})
    st.session_state["agente_farol_historico"] = historico[-12:]


def montar_catalogo_regras_markdown() -> str:
    linhas = []
    for codigo in REGRAS_ATIVAS:
        nome = RULE_NAMES.get(codigo, codigo)
        descricao = RULE_DESCRIPTIONS.get(codigo, "")
        linhas.append(f"<b>{codigo} — {nome}</b><br><span>{descricao}</span>")
    return "<br><br>".join(linhas)


def montar_sugestoes_regras() -> str:
    sugestoes = []
    for codigo in REGRAS_ATIVAS[:4]:
        nome = RULE_NAMES.get(codigo, codigo)
        sugestoes.append(f"Explique a regra {codigo} — {nome}.")
    return "<br>".join(sugestoes)


CATALOGO_REGRAS_MD = montar_catalogo_regras_markdown()
SUGESTOES_REGRAS_MD = montar_sugestoes_regras()

# =========================
# APP
# =========================
aplicar_estilos()
exigir_acesso("farol")

_banner_farol = banner_atualizacao()
if _banner_farol:
    st.markdown(_banner_farol, unsafe_allow_html=True)

st.markdown("""
    <style>
    .farol-resposta-box {
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.94), rgba(2, 6, 23, 0.98));
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 18px;
        padding: 1rem 1.1rem;
        color: #e5e7eb;
        line-height: 1.7;
        font-size: 1rem;
        white-space: normal;
    }
    .farol-sugestoes {
        background: linear-gradient(180deg, rgba(2, 6, 23, 0.88), rgba(15, 23, 42, 0.94));
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 18px;
        padding: 1rem 1.1rem;
        color: #dbe4f0;
        line-height: 1.75;
        font-size: 0.97rem;
    }
    .farol-history-item {
        border: 1px solid rgba(148, 163, 184, 0.12);
        background: rgba(15, 23, 42, 0.58);
        border-radius: 16px;
        padding: 0.85rem 0.95rem;
        margin-bottom: 0.75rem;
    }
    .farol-history-q {
        font-size: 0.82rem;
        color: #93c5fd;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.35rem;
    }
    .farol-history-a {
        font-size: 0.92rem;
        color: #e5e7eb;
        line-height: 1.55;
    }
    .stTextArea textarea {
        background: rgba(15, 23, 42, 0.92) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(148, 163, 184, 0.18) !important;
        border-radius: 16px !important;
        caret-color: #f8fafc !important;
        font-size: 1rem !important;
    }
    .stTextArea textarea::placeholder { color: #94a3b8 !important; }
    </style>
""", unsafe_allow_html=True)

with loading():
    data = load_data()
semaforo = data["semaforo"]
mapa_regras = data["mapa_regras"]
mapa_regras_interpretado = data["mapa_regras_interpretado"]
ranking = data["ranking_fiscalizacao"]

if "agente_farol_contexto" not in st.session_state:
    st.session_state["agente_farol_contexto"] = None
if "agente_farol_historico" not in st.session_state:
    st.session_state["agente_farol_historico"] = []
if "agente_farol_last_rows" not in st.session_state:
    st.session_state["agente_farol_last_rows"] = []
if "agente_farol_last_rows_type" not in st.session_state:
    st.session_state["agente_farol_last_rows_type"] = None

with st.sidebar:
    st.header("Controle")
    if st.button("Limpar contexto", use_container_width=True):
        st.session_state["agente_farol_contexto"] = None
        st.session_state["agente_farol_last_rows"] = []
        st.session_state["agente_farol_last_rows_type"] = None
        st.rerun()
    if st.button("Limpar histórico", use_container_width=True):
        st.session_state["agente_farol_historico"] = []
        st.rerun()
    st.caption("Limpe o contexto para reiniciar a linha de raciocínio.")
    n_rows = len(st.session_state.get("agente_farol_last_rows", []))
    if n_rows > 0:
        rows_type = st.session_state.get("agente_farol_last_rows_type", "")
        st.caption(f"✦ {n_rows} registros em memória ({rows_type or 'resultado anterior'}). Você pode refinar: \"desse grupo, mostre só os críticos\"")

st.markdown("""
    <div class="farol-page-hero">
        <h1>🤖 Agente FAROL</h1>
        <p>Consultas em linguagem natural sobre a base fiscal — contribuintes, agrupamentos, rankings e análises abertas.</p>
        <div class="farol-chip-row">
            <span class="farol-chip">LLM + Pandas</span>
            <span class="farol-chip">Memória conversacional</span>
            <span class="farol-chip">Catálogo oficial</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# =========================
# ÁREA PRINCIPAL — PERGUNTA
# =========================
st.markdown('<div class="farol-card">', unsafe_allow_html=True)
st.markdown('<div class="farol-section-title">Perguntar ao Agente FAROL</div>', unsafe_allow_html=True)
st.markdown('<div class="farol-section-subtitle">Formule sua pergunta livremente ou use o modo guiado.</div>', unsafe_allow_html=True)

c1, c2 = st.columns([1.2, 1.2])
modo_pergunta = c1.selectbox(
    "Modo da pergunta",
    ["Livre", "Agrupamentos", "Contribuinte individual", "Ranking / Top N", "Comparações", "Continuação do contexto"],
    index=0,
)
modelo = c2.selectbox("Modelo", ["gpt-4.1-mini", "gpt-4.1"], index=0)

placeholder_map = {
    "Livre": "Digite sua pergunta livre sobre a base FAROL...",
    "Agrupamentos": "Ex.: Qual órgão local apresenta a maior quantidade de contribuintes críticos?",
    "Contribuinte individual": "Ex.: Explique o contribuinte 62614005000161.",
    "Ranking / Top N": "Ex.: Mostre o top 20 do ranking de fiscalização.",
    "Comparações": "Ex.: Compare os municípios por média de índice FAROL.",
    "Continuação do contexto": "Ex.: Quais contribuintes puxam a média para cima?",
}
pergunta = st.text_area("Pergunta", height=120, placeholder=placeholder_map.get(modo_pergunta, ""))
perguntar = st.button("Perguntar ao FAROL", type="primary", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# RESPOSTA
# =========================
if perguntar:
    if not pergunta.strip():
        st.info("Digite uma pergunta.")
    else:
        try:
            with st.spinner("Processando..."):
                retorno = agente_economico(
                    pergunta=pergunta,
                    semaforo=semaforo,
                    mapa_regras=mapa_regras,
                    mapa_regras_interpretado=mapa_regras_interpretado,
                    ranking=ranking,
                    model=modelo,
                    contexto=st.session_state.get("agente_farol_contexto"),
                    historico=st.session_state.get("agente_farol_historico", []),
                    last_rows=st.session_state.get("agente_farol_last_rows", []),
                    last_rows_type=st.session_state.get("agente_farol_last_rows_type"),
                )

            if isinstance(retorno, dict):
                st.session_state["agente_farol_contexto"] = retorno.get("contexto")
                # Sempre atualizar last_rows quando o agente retornar o campo
                # (mesmo lista vazia = refinamento sem resultado é informação válida)
                if "last_rows" in retorno:
                    st.session_state["agente_farol_last_rows"] = retorno["last_rows"] or []
                    st.session_state["agente_farol_last_rows_type"] = retorno.get("last_rows_type")
                resposta = retorno.get("resposta", "Não foi possível gerar resposta.")
                tabela = retorno.get("tabela")
                tabela_completa = retorno.get("tabela_completa")
                total = retorno.get("total")
                followups = retorno.get("followups", [])
                tipo_resposta = retorno.get("tipo_resposta", "texto")
                usado_llm = retorno.get("usado_llm", False)
            else:
                resposta = str(retorno)
                tabela = None
                tabela_completa = None
                total = None
                followups = []
                tipo_resposta = "texto"
                usado_llm = False

            registrar_historico(pergunta, resposta)

            st.markdown('<div class="farol-card">', unsafe_allow_html=True)
            if usado_llm:
                st.markdown(
                    '<div class="farol-section-title">Resposta '
                    '<span style="font-size:0.75rem;font-weight:600;padding:0.2rem 0.6rem;'
                    'border-radius:999px;background:rgba(37,99,235,0.18);color:#93c5fd;'
                    'border:1px solid rgba(96,165,250,0.22);margin-left:0.5rem;vertical-align:middle;">'
                    '✨ LLM</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="farol-section-title">Resposta '
                    '<span style="font-size:0.75rem;font-weight:600;padding:0.2rem 0.6rem;'
                    'border-radius:999px;background:rgba(15,23,42,0.72);color:#94a3b8;'
                    'border:1px solid rgba(148,163,184,0.18);margin-left:0.5rem;vertical-align:middle;">'
                    '⚙️ Motor</span></div>',
                    unsafe_allow_html=True,
                )
            renderizar_resposta(resposta)
            st.markdown('</div>', unsafe_allow_html=True)

            if isinstance(tabela, pd.DataFrame) and not tabela.empty:
                st.markdown('<div class="farol-card">', unsafe_allow_html=True)

                # Cabeçalho: título + info de total + botão de download
                n_exib = len(tabela)
                n_total = total if total and total > n_exib else n_exib
                col_tit, col_dl = st.columns([3, 1])
                with col_tit:
                    if n_total > n_exib:
                        st.markdown(
                            f'<div class="farol-section-title">Tabela de apoio '
                            f'<span style="font-size:0.78rem;font-weight:400;color:#94a3b8;">'
                            f'— exibindo {n_exib} de {n_total} registros</span></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown('<div class="farol-section-title">Tabela de apoio</div>', unsafe_allow_html=True)

                with col_dl:
                    df_dl = tabela_completa if isinstance(tabela_completa, pd.DataFrame) and not tabela_completa.empty else tabela
                    csv_bytes = df_dl.to_csv(index=False).encode("utf-8")
                    label_dl = f"⬇ CSV ({len(df_dl)} registros)" if len(df_dl) > n_exib else "⬇ CSV"
                    st.download_button(
                        label=label_dl,
                        data=csv_bytes,
                        file_name="farol_resultado.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

                renderizar_tabela(tabela)
                st.markdown('</div>', unsafe_allow_html=True)

            if followups:
                with st.expander("💡 Próximos passos sugeridos", expanded=False):
                    st.markdown('<div class="farol-sugestoes">' + "<br>".join(followups) + "</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro no Agente FAROL: {e}")

# =========================
# SEÇÕES SECUNDÁRIAS — EXPANDERS
# =========================
with st.expander("🔁 Contexto da conversa", expanded=False):
    st.markdown('<div class="farol-section-subtitle">O agente usa este contexto para responder perguntas de continuação.</div>', unsafe_allow_html=True)
    renderizar_contexto(st.session_state.get("agente_farol_contexto"))

with st.expander("💬 Perguntas sugeridas", expanded=False):
    st.markdown(f"""
        <div class="farol-sugestoes">
        <b>Agrupamentos</b><br>
        Qual órgão local apresenta a maior quantidade de contribuintes críticos?<br>
        Qual município tem maior média de índice FAROL entre os muito altos?<br>
        Qual tipologia tem maior média de regras entre os críticos?<br><br>
        <b>Contribuinte individual</b><br>
        Explique o contribuinte 62614005000161.<br>
        Quais regras foram acionadas nesse contribuinte?<br><br>
        <b>Ranking</b><br>
        Mostre o top fiscalização.<br>
        Mostre o top 20 do ranking.<br><br>
        <b>Comparações</b><br>
        Compare os órgãos locais por quantidade de críticos.<br>
        Compare os municípios por média de índice FAROL.<br><br>
        <b>Regras do catálogo oficial</b><br>
        {SUGESTOES_REGRAS_MD}<br><br>
        <b>Continuação de contexto</b><br>
        Quais contribuintes puxam a média para cima?<br>
        Mostre os 10 primeiros desse grupo.<br>
        E só os críticos?
        </div>
    """, unsafe_allow_html=True)

historico = st.session_state.get("agente_farol_historico", [])
if historico:
    with st.expander(f"🕓 Histórico recente ({len(historico)} interações)", expanded=False):
        for item in reversed(historico[-6:]):
            pergunta_hist = str(item.get("pergunta", ""))
            resposta_hist = str(item.get("resposta", ""))
            resposta_curta = resposta_hist if len(resposta_hist) <= 420 else resposta_hist[:420].rstrip() + "..."
            st.markdown(f"""
                <div class="farol-history-item">
                    <div class="farol-history-q">Pergunta</div>
                    <div class="farol-history-a">{pergunta_hist}</div>
                    <div class="farol-history-q" style="margin-top:0.8rem;">Resposta</div>
                    <div class="farol-history-a">{resposta_curta}</div>
                </div>
            """, unsafe_allow_html=True)

with st.expander("📋 Catálogo oficial de regras", expanded=False):
    st.markdown('<div class="farol-section-subtitle">Regras do farol_rules_catalog.py — fonte oficial.</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="farol-sugestoes">{CATALOGO_REGRAS_MD}</div>', unsafe_allow_html=True)
