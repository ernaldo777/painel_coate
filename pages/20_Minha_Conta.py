import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import streamlit as st

from coate_styles import aplicar_estilos
from coate_auth import (
    exigir_login,
    obter_usuario_atual,
    limpar_flag_senha_provisoria,
    usuario_com_senha_provisoria,
)
from coate_access_store import alterar_senha_proprio_usuario

aplicar_estilos()
exigir_login()

usuario = obter_usuario_atual()
login = usuario["login"]
nome = usuario["nome"]
senha_provisoria = usuario_com_senha_provisoria()

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    '<p class="coate-kicker">PAINEL COATE · SEFAZ-CE</p>',
    unsafe_allow_html=True,
)
st.markdown("## 👤 Minha Conta")
st.caption("Gerencie suas informações de acesso ao Painel COATE.")

# ── Aviso de senha provisória ─────────────────────────────────────────────────
if senha_provisoria:
    st.warning(
        "⚠️ Você está usando uma **senha provisória** definida pelo administrador. "
        "Recomendamos que você crie uma senha pessoal abaixo.",
        icon=None,
    )

st.divider()

# ── Informações do usuário ─────────────────────────────────────────────────────
st.markdown("### Seus dados")
c1, c2 = st.columns(2)
with c1:
    st.markdown(
        '<div class="coate-panel">'
        '<span style="color:var(--text-muted);font-size:0.78rem;text-transform:uppercase;letter-spacing:.06em;">Login</span>'
        '<p style="font-size:1.1rem;font-weight:600;margin:4px 0 0;">' + login + '</p>'
        '</div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        '<div class="coate-panel">'
        '<span style="color:var(--text-muted);font-size:0.78rem;text-transform:uppercase;letter-spacing:.06em;">Nome</span>'
        '<p style="font-size:1.1rem;font-weight:600;margin:4px 0 0;">' + (nome or "—") + '</p>'
        '</div>',
        unsafe_allow_html=True,
    )

st.divider()

# ── Formulário de troca de senha ──────────────────────────────────────────────
st.markdown("### Alterar senha")
st.caption("Informe sua senha atual e escolha uma nova senha com pelo menos 6 caracteres.")

with st.form("form_alterar_senha", clear_on_submit=True):
    senha_atual = st.text_input("Senha atual", type="password", placeholder="Digite sua senha atual")
    nova_senha = st.text_input(
        "Nova senha",
        type="password",
        placeholder="Mínimo 6 caracteres",
    )
    confirmar_senha = st.text_input(
        "Confirmar nova senha",
        type="password",
        placeholder="Repita a nova senha",
    )

    # Indicador visual de força (simples)
    if nova_senha:
        comprimento = len(nova_senha)
        if comprimento < 6:
            st.caption("🔴 Senha muito curta")
        elif comprimento < 10:
            st.caption("🟡 Senha razoável — considere usar mais caracteres")
        else:
            st.caption("🟢 Senha forte")

    submitted = st.form_submit_button("Alterar senha", use_container_width=True)

if submitted:
    ok, msg = alterar_senha_proprio_usuario(
        login=login,
        senha_atual=senha_atual,
        nova_senha=nova_senha,
        confirmar_senha=confirmar_senha,
    )
    if ok:
        limpar_flag_senha_provisoria()
        st.success("✅ " + msg + " Você pode continuar usando o sistema normalmente.")
    else:
        st.error("❌ " + msg)
