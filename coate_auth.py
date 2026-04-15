"""Autenticação e sessão do Painel COATE."""

from __future__ import annotations

import streamlit as st

from coate_access_store import buscar_usuario, garantir_estrutura_segurança
from coate_security import normalizar_login, verificar_senha

SESSION_DEFAULTS = {
    "coate_logado": False,
    "coate_login": "",
    "coate_nome": "",
    "coate_admin": False,
    "coate_permissoes": {},
    "coate_senha_provisoria": False,
}

MODULOS = ["home", "itcd", "simples", "atendimento", "farol", "cnae"]


def inicializar_sessao() -> None:
    for chave, valor in SESSION_DEFAULTS.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


def _montar_permissoes(usuario: dict) -> dict:
    return {modulo: bool(int(usuario.get(modulo, 0) or 0)) for modulo in MODULOS}


def fazer_login(login: str, senha: str) -> tuple[bool, str]:
    garantir_estrutura_segurança()
    login = normalizar_login(login)
    if not login or not senha:
        return False, "Informe login e senha."

    usuario = buscar_usuario(login)
    if not usuario:
        return False, "Usuário não encontrado."
    if not bool(int(usuario.get("ativo", 0) or 0)):
        return False, "Usuário inativo."
    if not verificar_senha(senha, str(usuario.get("senha_hash", ""))):
        return False, "Senha inválida."

    st.session_state["coate_logado"] = True
    st.session_state["coate_login"] = login
    st.session_state["coate_nome"] = str(usuario.get("nome", "")).strip() or login
    st.session_state["coate_admin"] = bool(int(usuario.get("admin", 0) or 0))
    st.session_state["coate_permissoes"] = _montar_permissoes(usuario)
    st.session_state["coate_senha_provisoria"] = bool(int(usuario.get("senha_provisoria", 0) or 0))
    return True, "Login realizado com sucesso."


def fazer_logout() -> None:
    for chave, valor in SESSION_DEFAULTS.items():
        st.session_state[chave] = valor


def usuario_esta_logado() -> bool:
    return bool(st.session_state.get("coate_logado", False))


def obter_usuario_atual() -> dict:
    return {
        "login": st.session_state.get("coate_login", ""),
        "nome": st.session_state.get("coate_nome", ""),
        "admin": bool(st.session_state.get("coate_admin", False)),
        "permissoes": st.session_state.get("coate_permissoes", {}),
        "senha_provisoria": bool(st.session_state.get("coate_senha_provisoria", False)),
    }


def usuario_eh_admin() -> bool:
    return bool(st.session_state.get("coate_admin", False))


def usuario_tem_acesso(modulo: str) -> bool:
    if usuario_eh_admin():
        return True
    permissoes = st.session_state.get("coate_permissoes", {}) or {}
    return bool(permissoes.get(modulo, False))


def listar_modulos_permitidos() -> list[str]:
    if usuario_eh_admin():
        return MODULOS.copy()
    permissoes = st.session_state.get("coate_permissoes", {}) or {}
    return [modulo for modulo in MODULOS if permissoes.get(modulo, False)]


def exigir_login() -> None:
    if usuario_esta_logado():
        return
    st.error("Acesso restrito. Faça login para continuar.")
    st.stop()


def exigir_acesso(modulo: str) -> None:
    exigir_login()
    if usuario_tem_acesso(modulo):
        return
    st.error("Acesso negado. Seu perfil não possui permissão para este módulo.")
    st.stop()


def usuario_com_senha_provisoria() -> bool:
    """Retorna True se o usuário logado ainda está com senha provisória."""
    return bool(st.session_state.get("coate_senha_provisoria", False))


def limpar_flag_senha_provisoria() -> None:
    """Chamado após troca bem-sucedida de senha para atualizar a sessão."""
    st.session_state["coate_senha_provisoria"] = False
