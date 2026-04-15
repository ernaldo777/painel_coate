"""Camada de leitura e gravação dos arquivos de acesso do Painel COATE."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from coate_security import hash_senha, normalizar_login, verificar_senha

_ROOT = Path(__file__).resolve().parent
_SECURITY_DIR = _ROOT / "security"
_USUARIOS_PATH = _SECURITY_DIR / "usuarios.xlsx"
_SOLICITACOES_PATH = _SECURITY_DIR / "solicitacoes.xlsx"
_AUDITORIA_PATH = _SECURITY_DIR / "auditoria.xlsx"

MODULOS_CONTROLE = ["home", "itcd", "simples", "atendimento", "farol", "cnae", "admin"]

USUARIOS_COLUNAS = [
    "login", "nome", "email", "setor", "senha_hash",
    "ativo", "admin", "home", "itcd", "simples", "atendimento", "farol", "cnae",
    "senha_provisoria",
    "data_criacao", "aprovado_por", "observacao",
]

SOLICITACOES_COLUNAS = [
    "id", "data_solicitacao", "nome", "login_desejado", "email", "setor", "justificativa",
    "deseja_itcd", "deseja_simples", "deseja_atendimento", "deseja_farol", "deseja_cnae",
    "status", "analisado_por", "data_analise", "observacao",
]

AUDITORIA_COLUNAS = [
    "data_evento", "ator", "acao", "login_alvo", "detalhe"
]


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _df_vazio_usuarios() -> pd.DataFrame:
    return pd.DataFrame(columns=USUARIOS_COLUNAS)


def _df_vazio_solicitacoes() -> pd.DataFrame:
    return pd.DataFrame(columns=SOLICITACOES_COLUNAS)


def _df_vazio_auditoria() -> pd.DataFrame:
    return pd.DataFrame(columns=AUDITORIA_COLUNAS)


def garantir_estrutura_segurança() -> None:
    _SECURITY_DIR.mkdir(parents=True, exist_ok=True)
    if not _USUARIOS_PATH.exists():
        criar_usuario_inicial()
    if not _SOLICITACOES_PATH.exists():
        _df_vazio_solicitacoes().to_excel(_SOLICITACOES_PATH, index=False)
    if not _AUDITORIA_PATH.exists():
        _df_vazio_auditoria().to_excel(_AUDITORIA_PATH, index=False)


def _normalizar_bool_colunas(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = 0
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0).astype(int)
    return df


def criar_usuario_inicial() -> None:
    agora = _agora()
    df = pd.DataFrame([
        {
            "login": "ernaldo",
            "nome": "Francisco Ernaldo Vieira",
            "email": "",
            "setor": "COATE",
            "senha_hash": hash_senha("coate123"),
            "ativo": 1,
            "admin": 1,
            "home": 1,
            "itcd": 1,
            "simples": 1,
            "atendimento": 1,
            "farol": 1,
            "cnae": 1,
            "senha_provisoria": 0,
            "data_criacao": agora,
            "aprovado_por": "sistema",
            "observacao": "Usuário administrador inicial",
        }
    ], columns=USUARIOS_COLUNAS)
    salvar_usuarios(df)


def carregar_usuarios() -> pd.DataFrame:
    garantir_estrutura_segurança()
    try:
        df = pd.read_excel(_USUARIOS_PATH, dtype=str)
    except Exception:
        df = _df_vazio_usuarios()

    for coluna in USUARIOS_COLUNAS:
        if coluna not in df.columns:
            df[coluna] = ""

    df = df[USUARIOS_COLUNAS].copy()
    df = _normalizar_bool_colunas(
        df,
        ["ativo", "admin", "home", "itcd", "simples", "atendimento", "farol", "cnae", "senha_provisoria"],
    )

    for coluna in ["login", "nome", "email", "setor", "senha_hash", "data_criacao", "aprovado_por", "observacao"]:
        df[coluna] = df[coluna].fillna("").astype(str)

    df["login"] = df["login"].map(normalizar_login)
    return df


def salvar_usuarios(df: pd.DataFrame) -> None:
    garantir_estrutura_segurança()
    base = _df_vazio_usuarios()
    if df is None or df.empty:
        base.to_excel(_USUARIOS_PATH, index=False)
        return

    df = df.copy()
    for coluna in USUARIOS_COLUNAS:
        if coluna not in df.columns:
            df[coluna] = ""

    df = _normalizar_bool_colunas(
        df,
        ["ativo", "admin", "home", "itcd", "simples", "atendimento", "farol", "cnae", "senha_provisoria"],
    )
    df["login"] = df["login"].map(normalizar_login)
    df = df[USUARIOS_COLUNAS].drop_duplicates(subset=["login"], keep="last")
    df.to_excel(_USUARIOS_PATH, index=False)


def buscar_usuario(login: str) -> dict | None:
    login = normalizar_login(login)
    if not login:
        return None
    df = carregar_usuarios()
    filtrado = df[df["login"] == login]
    if filtrado.empty:
        return None
    return filtrado.iloc[0].to_dict()


def carregar_solicitacoes() -> pd.DataFrame:
    garantir_estrutura_segurança()
    try:
        df = pd.read_excel(_SOLICITACOES_PATH, dtype=str)
    except Exception:
        df = _df_vazio_solicitacoes()

    for coluna in SOLICITACOES_COLUNAS:
        if coluna not in df.columns:
            df[coluna] = ""

    df = df[SOLICITACOES_COLUNAS].copy()
    df = _normalizar_bool_colunas(df, ["deseja_itcd", "deseja_simples", "deseja_atendimento", "deseja_farol", "deseja_cnae"])
    for coluna in ["id", "data_solicitacao", "nome", "login_desejado", "email", "setor", "justificativa", "status", "analisado_por", "data_analise", "observacao"]:
        df[coluna] = df[coluna].fillna("").astype(str)
    df["login_desejado"] = df["login_desejado"].map(normalizar_login)
    return df


def salvar_solicitacoes(df: pd.DataFrame) -> None:
    garantir_estrutura_segurança()
    if df is None or df.empty:
        _df_vazio_solicitacoes().to_excel(_SOLICITACOES_PATH, index=False)
        return
    df = df.copy()
    for coluna in SOLICITACOES_COLUNAS:
        if coluna not in df.columns:
            df[coluna] = ""
    df = _normalizar_bool_colunas(df, ["deseja_itcd", "deseja_simples", "deseja_atendimento", "deseja_farol", "deseja_cnae"])
    df["login_desejado"] = df["login_desejado"].map(normalizar_login)
    df = df[SOLICITACOES_COLUNAS].drop_duplicates(subset=["id"], keep="last")
    df.to_excel(_SOLICITACOES_PATH, index=False)


def carregar_auditoria() -> pd.DataFrame:
    garantir_estrutura_segurança()
    try:
        df = pd.read_excel(_AUDITORIA_PATH, dtype=str)
    except Exception:
        df = _df_vazio_auditoria()
    for coluna in AUDITORIA_COLUNAS:
        if coluna not in df.columns:
            df[coluna] = ""
    return df[AUDITORIA_COLUNAS].fillna("").astype(str)


def salvar_auditoria(df: pd.DataFrame) -> None:
    garantir_estrutura_segurança()
    if df is None or df.empty:
        _df_vazio_auditoria().to_excel(_AUDITORIA_PATH, index=False)
        return
    for coluna in AUDITORIA_COLUNAS:
        if coluna not in df.columns:
            df[coluna] = ""
    df[AUDITORIA_COLUNAS].to_excel(_AUDITORIA_PATH, index=False)


def registrar_auditoria(ator: str, acao: str, login_alvo: str, detalhe: str) -> None:
    df = carregar_auditoria()
    novo = pd.DataFrame([{
        "data_evento": _agora(),
        "ator": normalizar_login(ator) or ator,
        "acao": acao,
        "login_alvo": normalizar_login(login_alvo) or login_alvo,
        "detalhe": detalhe,
    }])
    df = pd.concat([novo, df], ignore_index=True)
    salvar_auditoria(df)


def registrar_solicitacao(
    nome: str,
    login_desejado: str,
    email: str,
    setor: str,
    justificativa: str,
    deseja_itcd: bool,
    deseja_simples: bool,
    deseja_atendimento: bool,
    deseja_farol: bool,
    deseja_cnae: bool,
) -> tuple[bool, str]:
    garantir_estrutura_segurança()
    login_desejado = normalizar_login(login_desejado)
    if not nome.strip() or not login_desejado or not email.strip():
        return False, "Preencha nome, login desejado e e-mail."
    if buscar_usuario(login_desejado):
        return False, "Já existe um usuário aprovado com esse login."

    df = carregar_solicitacoes()
    pendente = df[(df["login_desejado"] == login_desejado) & (df["status"].str.upper() == "PENDENTE")]
    if not pendente.empty:
        return False, "Já existe solicitação pendente para esse login."

    ultimo_id = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int).max() if not df.empty else 0
    novo = pd.DataFrame([{
        "id": int(ultimo_id) + 1,
        "data_solicitacao": _agora(),
        "nome": nome.strip(),
        "login_desejado": login_desejado,
        "email": email.strip(),
        "setor": setor.strip(),
        "justificativa": justificativa.strip(),
        "deseja_itcd": int(bool(deseja_itcd)),
        "deseja_simples": int(bool(deseja_simples)),
        "deseja_atendimento": int(bool(deseja_atendimento)),
        "deseja_farol": int(bool(deseja_farol)),
        "deseja_cnae": int(bool(deseja_cnae)),
        "status": "PENDENTE",
        "analisado_por": "",
        "data_analise": "",
        "observacao": "",
    }])
    df = pd.concat([df, novo], ignore_index=True)
    salvar_solicitacoes(df)
    registrar_auditoria(login_desejado, "SOLICITACAO_CRIADA", login_desejado, "Solicitação registrada pelo formulário inicial.")
    return True, "Solicitação registrada com sucesso."


def aprovar_solicitacao(solicitacao_id: int | str, ator: str, permissoes: dict, senha_temporaria: str, observacao: str = "") -> tuple[bool, str]:
    df_sol = carregar_solicitacoes()
    sid = str(solicitacao_id)
    mask = df_sol["id"].astype(str) == sid
    if not mask.any():
        return False, "Solicitação não encontrada."

    row = df_sol.loc[mask].iloc[0]
    login = normalizar_login(row["login_desejado"])
    if not login:
        return False, "Login da solicitação é inválido."

    df_usr = carregar_usuarios()
    agora = _agora()
    registro = {
        "login": login,
        "nome": row["nome"],
        "email": row["email"],
        "setor": row["setor"],
        "senha_hash": hash_senha(senha_temporaria),
        "ativo": 1,
        "admin": int(bool(permissoes.get("admin", False))),
        "home": 1,
        "itcd": int(bool(permissoes.get("itcd", False))),
        "simples": int(bool(permissoes.get("simples", False))),
        "atendimento": int(bool(permissoes.get("atendimento", False))),
        "farol": int(bool(permissoes.get("farol", False))),
        "cnae": int(bool(permissoes.get("cnae", False))),
        "senha_provisoria": 1,  # sempre provisória na aprovação
        "data_criacao": agora,
        "aprovado_por": normalizar_login(ator) or ator,
        "observacao": observacao.strip(),
    }

    mask_usr = df_usr["login"] == login
    if mask_usr.any():
        for chave, valor in registro.items():
            df_usr.loc[mask_usr, chave] = valor
    else:
        df_usr = pd.concat([df_usr, pd.DataFrame([registro])], ignore_index=True)
    salvar_usuarios(df_usr)

    df_sol.loc[mask, "status"] = "APROVADO"
    df_sol.loc[mask, "analisado_por"] = normalizar_login(ator) or ator
    df_sol.loc[mask, "data_analise"] = agora
    df_sol.loc[mask, "observacao"] = observacao.strip()
    salvar_solicitacoes(df_sol)

    detalhe = f"Permissões: {', '.join([k for k, v in permissoes.items() if v]) or 'nenhuma'}."
    registrar_auditoria(ator, "SOLICITACAO_APROVADA", login, detalhe)
    return True, "Solicitação aprovada e usuário atualizado."


def rejeitar_solicitacao(solicitacao_id: int | str, ator: str, observacao: str = "") -> tuple[bool, str]:
    df = carregar_solicitacoes()
    sid = str(solicitacao_id)
    mask = df["id"].astype(str) == sid
    if not mask.any():
        return False, "Solicitação não encontrada."
    login = str(df.loc[mask, "login_desejado"].iloc[0])
    df.loc[mask, "status"] = "REJEITADO"
    df.loc[mask, "analisado_por"] = normalizar_login(ator) or ator
    df.loc[mask, "data_analise"] = _agora()
    df.loc[mask, "observacao"] = observacao.strip()
    salvar_solicitacoes(df)
    registrar_auditoria(ator, "SOLICITACAO_REJEITADA", login, observacao.strip() or "Sem observação.")
    return True, "Solicitação rejeitada."


def atualizar_permissoes_usuario(login: str, ator: str, permissoes: dict, ativo: bool, admin: bool, observacao: str = "") -> tuple[bool, str]:
    login = normalizar_login(login)
    df = carregar_usuarios()
    mask = df["login"] == login
    if not mask.any():
        return False, "Usuário não encontrado."
    df.loc[mask, "ativo"] = int(bool(ativo))
    df.loc[mask, "admin"] = int(bool(admin))
    df.loc[mask, "home"] = 1
    for modulo in ["itcd", "simples", "atendimento", "farol", "cnae"]:
        df.loc[mask, modulo] = int(bool(permissoes.get(modulo, False)))
    if observacao.strip():
        df.loc[mask, "observacao"] = observacao.strip()
    salvar_usuarios(df)
    detalhe = f"Ativo={int(bool(ativo))}; Admin={int(bool(admin))}; Permissões={', '.join([k for k,v in permissoes.items() if v]) or 'nenhuma'}."
    registrar_auditoria(ator, "USUARIO_ATUALIZADO", login, detalhe)
    return True, "Permissões atualizadas com sucesso."


def redefinir_senha_usuario(login: str, nova_senha: str, ator: str) -> tuple[bool, str]:
    """Admin redefine a senha de um usuário — marca como provisória."""
    login = normalizar_login(login)
    if not login or not nova_senha:
        return False, "Informe login e nova senha."
    df = carregar_usuarios()
    mask = df["login"] == login
    if not mask.any():
        return False, "Usuário não encontrado."
    df.loc[mask, "senha_hash"] = hash_senha(nova_senha)
    df.loc[mask, "senha_provisoria"] = 1  # marcada como provisória
    salvar_usuarios(df)
    registrar_auditoria(ator, "SENHA_REDEFINIDA", login, "Senha redefinida manualmente pela gestão.")
    return True, "Senha redefinida com sucesso."


def alterar_senha_proprio_usuario(login: str, senha_atual: str, nova_senha: str, confirmar_senha: str) -> tuple[bool, str]:
    """O próprio usuário altera sua senha, informando a atual para validação."""
    login = normalizar_login(login)
    if not login:
        return False, "Login inválido."
    if not senha_atual or not nova_senha or not confirmar_senha:
        return False, "Preencha todos os campos."
    if nova_senha != confirmar_senha:
        return False, "A nova senha e a confirmação não conferem."
    if len(nova_senha) < 6:
        return False, "A nova senha deve ter pelo menos 6 caracteres."
    if nova_senha == senha_atual:
        return False, "A nova senha deve ser diferente da senha atual."

    df = carregar_usuarios()
    mask = df["login"] == login
    if not mask.any():
        return False, "Usuário não encontrado."

    senha_hash_atual = str(df.loc[mask, "senha_hash"].iloc[0])
    if not verificar_senha(senha_atual, senha_hash_atual):
        return False, "Senha atual incorreta."

    df.loc[mask, "senha_hash"] = hash_senha(nova_senha)
    df.loc[mask, "senha_provisoria"] = 0  # limpa o flag provisório
    salvar_usuarios(df)
    registrar_auditoria(login, "SENHA_ALTERADA_PELO_USUARIO", login, "Usuário alterou a própria senha.")
    return True, "Senha alterada com sucesso."
