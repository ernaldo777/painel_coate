"""Utilitários simples de segurança para autenticação do Painel COATE."""

from __future__ import annotations

import hashlib
import hmac


def normalizar_login(login: str) -> str:
    return (login or "").strip().lower()


def hash_senha(senha: str) -> str:
    senha = senha or ""
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def verificar_senha(senha_texto: str, senha_hash: str) -> bool:
    calculado = hash_senha(senha_texto)
    return hmac.compare_digest(calculado, str(senha_hash or ""))
