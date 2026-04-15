"""
itcd_core.py
============
Camada de dados do módulo ITCD.

Responsabilidades:
  - Carregar as 4 abas da planilha ITCD.xlsx (cache)
  - Corrigir o vínculo das pendências (processo direto ou via guia)
  - Calcular dias líquidos do fiscal por processo
  - Expor funções de apoio ao painel, exploração e consulta
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

try:
    from itcd_config import (
        CACHE_TTL, DATA_PATH, FASES_CONCLUIDO, FASES_FISCAL,
        PENDENCIA_BLOQUEANTES, PRAZO_META_DIAS,
    )
except ImportError:
    from itcd.itcd_config import (
        CACHE_TTL, DATA_PATH, FASES_CONCLUIDO, FASES_FISCAL,
        PENDENCIA_BLOQUEANTES, PRAZO_META_DIAS,
    )


@dataclass(frozen=True)
class ITCDDataSpec:
    path: str
    existe: bool
    n_processos: int
    n_fases: int
    n_pendencias: int
    n_guias: int


@st.cache_data(ttl=CACHE_TTL, show_spinner="⏳ Carregando dados ITCD...")
def _load_raw(path: str) -> dict[str, pd.DataFrame]:
    xl = pd.ExcelFile(path)
    sheets = {}
    for aba in ["Processos", "fases", "guias", "pendencias"]:
        if aba in xl.sheet_names:
            sheets[aba] = xl.parse(aba)
    return sheets


def get_data() -> dict[str, pd.DataFrame]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de dados ITCD não encontrado em: {DATA_PATH}\n"
            "Coloque o arquivo ITCD.xlsx em itcd/data/"
        )
    return _load_raw(str(DATA_PATH))


def get_spec() -> ITCDDataSpec:
    try:
        d = get_data()
        return ITCDDataSpec(
            path=str(DATA_PATH),
            existe=True,
            n_processos=len(d.get("Processos", [])),
            n_fases=len(d.get("fases", [])),
            n_pendencias=len(d.get("pendencias", [])),
            n_guias=len(d.get("guias", [])),
        )
    except Exception:
        return ITCDDataSpec(
            path=str(DATA_PATH), existe=False,
            n_processos=0, n_fases=0, n_pendencias=0, n_guias=0
        )


def _normalize_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.select_dtypes(include="object").columns:
        s = df[col].astype("string")
        s = s.str.strip()
        s = s.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})
        df[col] = s
    return df


def _to_datetime(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def _to_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def _status_pendencia_aberta(valor: Any) -> bool:
    return str(valor or "").upper() in PENDENCIA_BLOQUEANTES


def _dias_bloqueados_pendencia(row: pd.Series, hoje: pd.Timestamp) -> int:
    inicio = row.get("DAT_INCLUSAO")
    if pd.isna(inicio):
        return 0

    status = str(row.get("DSC_STA_PENDENCIA", "")).upper()

    if status == "CANCELADA" and pd.notna(row.get("DAT_CANCELAMENTO")):
        fim = row.get("DAT_CANCELAMENTO")
    elif status == "RESOLVIDA" and pd.notna(row.get("DAT_RESPOSTA")):
        fim = row.get("DAT_RESPOSTA")
    elif status in PENDENCIA_BLOQUEANTES:
        fim = hoje
    else:
        return 0

    return max(0, int((fim - inicio).days))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_pendencias_enriquecidas() -> pd.DataFrame:
    """
    Retorna pendências vinculadas ao processo de forma robusta:
    1) usa SEQ_PROCESSO_ITCD quando existir;
    2) quando vier vazio, usa SEQ_GUIA_ITCD -> SEQ_PROCESSO_ITCD.
    """
    data = get_data()
    pend = _normalize_text_columns(data["pendencias"])
    guias = _normalize_text_columns(data["guias"])

    pend = _to_datetime(pend, ["DAT_INCLUSAO", "DAT_VISUALIZACAO", "DAT_RESPOSTA", "DAT_CANCELAMENTO"])
    pend = _to_numeric(pend, ["SEQ_PENDENCIA", "SEQ_GUIA_ITCD", "SEQ_PROCESSO_ITCD"])
    guias = _to_numeric(guias, ["SEQ_GUIA_ITCD", "SEQ_PROCESSO_ITCD"])

    guia_to_proc = (
        guias[["SEQ_GUIA_ITCD", "SEQ_PROCESSO_ITCD"]]
        .dropna(subset=["SEQ_GUIA_ITCD", "SEQ_PROCESSO_ITCD"])
        .drop_duplicates()
        .rename(columns={"SEQ_PROCESSO_ITCD": "SEQ_PROCESSO_ITCD_GUIA"})
    )

    pend = pend.merge(guia_to_proc, on="SEQ_GUIA_ITCD", how="left")
    pend["SEQ_PROCESSO_CALCULADO"] = pend["SEQ_PROCESSO_ITCD"].fillna(pend["SEQ_PROCESSO_ITCD_GUIA"])
    pend = pend[pend["SEQ_PROCESSO_CALCULADO"].notna()].copy()

    pend["SEQ_PROCESSO_ITCD"] = pend["SEQ_PROCESSO_CALCULADO"].apply(_safe_int)
    pend["SEQ_PENDENCIA"] = pend["SEQ_PENDENCIA"].apply(_safe_int)
    pend["SEQ_GUIA_ITCD"] = pend["SEQ_GUIA_ITCD"].apply(_safe_int)
    pend.drop(columns=["SEQ_PROCESSO_CALCULADO", "SEQ_PROCESSO_ITCD_GUIA"], inplace=True, errors="ignore")

    hoje = pd.Timestamp.now().normalize()
    pend["pendencia_aberta"] = pend["DSC_STA_PENDENCIA"].map(_status_pendencia_aberta).fillna(False).astype(bool)
    pend["dias_bloqueados"] = pend.apply(_dias_bloqueados_pendencia, axis=1, hoje=hoje).apply(_safe_int)

    return pend.reset_index(drop=True)


@st.cache_data(ttl=CACHE_TTL, show_spinner="⏳ Calculando indicadores dos processos...")
def calcular_processos_enriquecidos() -> pd.DataFrame:
    """
    Retorna a aba Processos enriquecida com métricas operacionais, de prazo e de pendências.
    A coluna oficial de prazo continua sendo a coluna original `Prazo` da aba Processos.
    """
    data = get_data()
    proc = _normalize_text_columns(data["Processos"])
    fases = _normalize_text_columns(data["fases"])
    pend = get_pendencias_enriquecidas()

    proc = _to_datetime(proc, ["DAT_CRIACAO", "DAT_DISTRIBUICAO"])
    fases = _to_datetime(fases, ["DAT_FASE", "DAT_FASE_PROX"])

    proc = _to_numeric(proc, [
        "SEQ_PROCESSO_ITCD", "NUM_PROCESSO_ITCD", "TIP_TRANSMISSAO", "TIP_FASE",
        "STA_DISTRIBUICAO_AUTOMATICA", "TIP_ORIGEM_PROCESSO", "COD_ORGAO_DESTINO",
        "Guias", "Dias Aprov/Acumulados", "Dias Em Inst/Acumulados",
        "Prazo de Finalização", "Fase Minima", "Fase Máxima",
    ])
    fases = _to_numeric(fases, [
        "SEQ_PROCESSO_ITCD", "TIP_FASE", "DIAS",
        "FLG_APOS_INSTRUCAO", "DIAS_ACUMULADOS", "DIAS_ACUMULADOS_EM_INSTRUCAO",
    ])

    proc["Prazo"] = proc["Prazo"].astype("string").str.strip().str.upper()
    proc["DSC_TIP_FASE_GUIA"] = proc["DSC_TIP_FASE_GUIA"].astype("string").str.strip().str.upper()

    # 1) Tempo bruto do fiscal
    fases_f = fases[fases["TIP_FASE"].isin(FASES_FISCAL)].copy()
    dias_brutos = (
        fases_f.groupby("SEQ_PROCESSO_ITCD", dropna=False)["DIAS"]
        .sum(min_count=1)
        .reset_index()
        .rename(columns={"DIAS": "dias_brutos_fiscal"})
    )

    # 2) Pendências (corrigidas via processo ou guia)
    pend_ag = (
        pend.groupby("SEQ_PROCESSO_ITCD", dropna=False)
        .agg(
            dias_pendencias=("dias_bloqueados", "sum"),
            qtd_pendencias=("SEQ_PENDENCIA", "nunique"),
            qtd_pendencias_abertas=("pendencia_aberta", "sum"),
            ultima_pendencia=("DAT_INCLUSAO", "max"),
        )
        .reset_index()
    )
    pend_ag["tem_pendencia"] = pend_ag["qtd_pendencias"] > 0
    pend_ag["tem_pendencia_aberta"] = pend_ag["qtd_pendencias_abertas"] > 0

    # 3) Data de encerramento real (pela última fase final)
    fases_finais = fases[fases["DSC_TIP_FASE_GUIA"].astype("string").str.upper().isin(["CONCLUIDO", "CANCELADO"])].copy()
    encerramento = (
        fases_finais.groupby("SEQ_PROCESSO_ITCD", dropna=False)["DAT_FASE"]
        .max()
        .reset_index()
        .rename(columns={"DAT_FASE": "DAT_ENCERRAMENTO"})
    )

    df = proc.merge(dias_brutos, on="SEQ_PROCESSO_ITCD", how="left")
    df = df.merge(pend_ag, on="SEQ_PROCESSO_ITCD", how="left")
    df = df.merge(encerramento, on="SEQ_PROCESSO_ITCD", how="left")

    for col in ["dias_brutos_fiscal", "dias_pendencias", "qtd_pendencias", "qtd_pendencias_abertas", "Guias"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in ["tem_pendencia", "tem_pendencia_aberta"]:
        df[col] = df[col].fillna(False).astype(bool)

    df["dias_brutos_fiscal"] = df["dias_brutos_fiscal"].apply(_safe_int)
    df["dias_pendencias"] = df["dias_pendencias"].apply(_safe_int)
    df["qtd_pendencias"] = df["qtd_pendencias"].apply(_safe_int)
    df["qtd_pendencias_abertas"] = df["qtd_pendencias_abertas"].apply(_safe_int)
    df["Guias"] = df["Guias"].apply(_safe_int)

    df["dias_liquidos_fiscal"] = (df["dias_brutos_fiscal"] - df["dias_pendencias"]).clip(lower=0)
    denom = pd.to_numeric(df["dias_brutos_fiscal"], errors="coerce").replace(0, pd.NA)
    df["percentual_bloqueado"] = (pd.to_numeric(df["dias_pendencias"], errors="coerce") / denom).fillna(0.0).astype(float)

    # Status do processo — lógica Fase Minima / Fase Máxima
    # Reproduz o campo calculado do Tableau:
    #   IF Fase Minima IN {5..11} AND Fase Máxima IN {5..11} → CONCLUÍDO
    #   ELSE → A TRABALHAR
    def _calc_status_processo(row: pd.Series) -> str:
        fm = row.get("Fase Minima")
        fx = row.get("Fase Máxima")
        try:
            fm_i = int(float(fm)) if pd.notna(fm) else None
            fx_i = int(float(fx)) if pd.notna(fx) else None
        except (ValueError, TypeError):
            fm_i, fx_i = None, None
        if fm_i in FASES_CONCLUIDO and fx_i in FASES_CONCLUIDO:
            return "CONCLUÍDO"
        return "A TRABALHAR"

    df["status_processo"] = df.apply(_calc_status_processo, axis=1)
    df["encerrado"] = df["status_processo"] == "CONCLUÍDO"
    df["ativo"]     = df["status_processo"] == "A TRABALHAR"
    df["sem_distribuicao"] = df["DAT_DISTRIBUICAO"].isna()

    hoje = pd.Timestamp.now().normalize()
    df["idade_processo_dias"] = (hoje - df["DAT_CRIACAO"].dt.normalize()).dt.days
    df["dias_para_meta"] = PRAZO_META_DIAS - df["dias_liquidos_fiscal"]
    df["ano_criacao"] = df["DAT_CRIACAO"].dt.year
    df["mes_criacao"] = df["DAT_CRIACAO"].dt.to_period("M").astype(str)
    df["mes_encerramento"] = pd.to_datetime(df["DAT_ENCERRAMENTO"], errors="coerce").dt.to_period("M").astype("string")
    df["mes_encerramento"] = df["mes_encerramento"].replace("<NA>", pd.NA)

    def _faixa_idade(v: Any) -> str:
        if pd.isna(v):
            return "Sem data"
        v = int(v)
        if v <= 15:
            return "0–15"
        if v <= 30:
            return "16–30"
        if v <= 60:
            return "31–60"
        if v <= 90:
            return "61–90"
        return ">90"

    df["faixa_idade_estoque"] = df["idade_processo_dias"].apply(_faixa_idade)

    # Regra oficial de prazo: usar a coluna original Prazo da tabela Processos
    df["dentro_do_prazo"] = df["Prazo"].eq("EM DIA")
    df["status_okr"] = "Em Andamento"
    df.loc[df["encerrado"] & df["dentro_do_prazo"], "status_okr"] = "Dentro do Prazo"
    df.loc[df["encerrado"] & ~df["dentro_do_prazo"], "status_okr"] = "Fora do Prazo"
    df.loc[df["ativo"] & ~df["dentro_do_prazo"], "status_okr"] = "Em Risco"

    def _status_gerencial(row: pd.Series) -> str:
        if bool(row["encerrado"]):
            return "Concluído no Prazo" if bool(row["dentro_do_prazo"]) else "Concluído em Atraso"
        if bool(row["sem_distribuicao"]):
            return "Sem Distribuição"
        if bool(row["tem_pendencia_aberta"]):
            return "Com Pendência"
        if str(row.get("Prazo", "")).upper() == "ATRASADO":
            return "Crítico" if _safe_int(row.get("dias_liquidos_fiscal")) >= max(PRAZO_META_DIAS * 2, 30) else "Em Risco"
        return "Ativo Regular"

    df["status_gerencial"] = df.apply(_status_gerencial, axis=1)
    df["processos_com_pendencia_aberta"] = df["tem_pendencia_aberta"].astype(int)
    df["processos_sem_distribuicao"] = df["sem_distribuicao"].astype(int)

    return df.reset_index(drop=True)


@st.cache_data(ttl=CACHE_TTL, show_spinner="⏳ Calculando OKR de produtividade...")
def get_okr_kpis() -> dict[str, Any]:
    df = calcular_processos_enriquecidos()
    encerrados = df[df["encerrado"]].copy()
    ativos = df[df["ativo"]].copy()

    dentro = int((encerrados["dentro_do_prazo"]).sum())
    fora = int((~encerrados["dentro_do_prazo"]).sum())

    return {
        "total_processos": int(len(df)),
        "ativos": int(len(ativos)),
        "encerrados": int(len(encerrados)),
        "dentro_do_prazo": dentro,
        "fora_do_prazo": fora,
        "com_pendencia_aberta": int(ativos["tem_pendencia_aberta"].sum()),
        "sem_distribuicao_ativos": int((ativos["sem_distribuicao"]).sum()),
        "em_risco": int((df["status_gerencial"] == "Em Risco").sum()),
        "criticos": int((df["status_gerencial"] == "Crítico").sum()),
        "taxa_okr": _safe_float(dentro / max(len(encerrados), 1), 0.0),
        "media_dias_liquidos": round(_safe_float(encerrados["dias_liquidos_fiscal"].mean() if not encerrados.empty else 0, 0.0), 1),
        "mediana_dias_liquidos": round(_safe_float(encerrados["dias_liquidos_fiscal"].median() if not encerrados.empty else 0, 0.0), 1),
        "media_dias_pendencias": round(_safe_float(df["dias_pendencias"].mean() if not df.empty else 0, 0.0), 1),
        "prazo_meta": PRAZO_META_DIAS,
    }


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_distribuicao_okr() -> pd.DataFrame:
    df = calcular_processos_enriquecidos()
    ordem = ["Concluído no Prazo", "Concluído em Atraso", "Crítico", "Em Risco", "Com Pendência", "Sem Distribuição", "Ativo Regular"]
    grp = (
        df.groupby("status_gerencial", dropna=False)
        .size()
        .reset_index(name="quantidade")
    )
    grp["ordem"] = grp["status_gerencial"].map({v: i for i, v in enumerate(ordem)})
    return grp.sort_values(["ordem", "quantidade"], ascending=[True, False]).drop(columns="ordem")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_evolucao_mensal() -> pd.DataFrame:
    df = calcular_processos_enriquecidos()
    encerrados = df[df["encerrado"] & df["mes_encerramento"].notna()].copy()
    if encerrados.empty:
        return pd.DataFrame()

    grp = (
        encerrados.groupby("mes_encerramento", dropna=False)
        .agg(
            total=("SEQ_PROCESSO_ITCD", "count"),
            dentro=("dentro_do_prazo", "sum"),
            media_liq=("dias_liquidos_fiscal", "mean"),
        )
        .reset_index()
    )
    grp["fora"] = grp["total"] - grp["dentro"]
    grp["taxa_okr"] = grp["dentro"] / grp["total"].clip(lower=1)
    return grp.sort_values("mes_encerramento")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_distribuicao_por_tipo() -> pd.DataFrame:
    df = calcular_processos_enriquecidos()
    return (
        df.groupby(["DSC_TIP_TRANSMISSAO", "status_gerencial"], dropna=False)
        .size()
        .reset_index(name="quantidade")
    )


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_distribuicao_por_orgao(top_n: int = 15) -> pd.DataFrame:
    df = calcular_processos_enriquecidos()

    grp = (
        df.groupby("DSC_SIGLA_ORGAO_LOCAL", dropna=False)
        .agg(
            total=("SEQ_PROCESSO_ITCD", "count"),
            ativos=("ativo", "sum"),
            encerrados=("encerrado", "sum"),
            com_pendencia_aberta=("tem_pendencia_aberta", "sum"),
            sem_distribuicao=("sem_distribuicao", "sum"),
            media_liq=("dias_liquidos_fiscal", "mean"),
            mediana_liq=("dias_liquidos_fiscal", "median"),
        )
        .reset_index()
    )

    encerrados = df[df["encerrado"]].copy()
    desempenho = (
        encerrados.groupby("DSC_SIGLA_ORGAO_LOCAL", dropna=False)
        .agg(
            dentro=("dentro_do_prazo", "sum"),
            media_liq_enc=("dias_liquidos_fiscal", "mean"),
        )
        .reset_index()
    )

    grp = grp.merge(desempenho, on="DSC_SIGLA_ORGAO_LOCAL", how="left")
    grp["dentro"] = grp["dentro"].fillna(0)
    grp["taxa_okr"] = grp["dentro"] / grp["encerrados"].replace(0, pd.NA)
    grp["taxa_okr"] = grp["taxa_okr"].fillna(0.0)
    grp["media_liq_enc"] = grp["media_liq_enc"].fillna(0.0)

    return grp.sort_values("total", ascending=False).head(top_n)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_ranking_processos(
    status_okr: str | None = None,
    tipo_transmissao: str | None = None,
    orgao: str | None = None,
    limit: int = 500,
) -> pd.DataFrame:
    df = calcular_processos_enriquecidos()

    if status_okr and status_okr != "Todos":
        if status_okr in df["status_okr"].unique():
            df = df[df["status_okr"] == status_okr]
        elif status_okr in df["status_gerencial"].unique():
            df = df[df["status_gerencial"] == status_okr]
    if tipo_transmissao and tipo_transmissao != "Todos":
        df = df[df["DSC_TIP_TRANSMISSAO"] == tipo_transmissao]
    if orgao and orgao != "Todos":
        df = df[df["DSC_SIGLA_ORGAO_LOCAL"] == orgao]

    cols = [
        "SEQ_PROCESSO_ITCD", "NUM_PROCESSO_ITCD", "DSC_TIP_TRANSMISSAO",
        "DSC_SIGLA_ORGAO_LOCAL", "DSC_TIP_FASE_GUIA", "Prazo",
        "dias_brutos_fiscal", "dias_pendencias", "dias_liquidos_fiscal",
        "status_okr", "status_gerencial", "DAT_CRIACAO", "DAT_DISTRIBUICAO",
        "Dias Aprov/Acumulados", "Guias", "qtd_pendencias", "qtd_pendencias_abertas",
    ]
    cols_exist = [c for c in cols if c in df.columns]
    return (
        df[cols_exist]
        .sort_values(["dias_liquidos_fiscal", "dias_pendencias"], ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )


def get_processo_detalhe(seq: int) -> dict[str, pd.DataFrame]:
    data = get_data()
    fases = _normalize_text_columns(data["fases"])
    pend = get_pendencias_enriquecidas()
    guias = _normalize_text_columns(data["guias"])
    proc = calcular_processos_enriquecidos()

    fases = _to_datetime(fases, ["DAT_FASE", "DAT_FASE_PROX"])

    return {
        "processo": proc[proc["SEQ_PROCESSO_ITCD"] == seq],
        "fases": fases[fases["SEQ_PROCESSO_ITCD"] == seq].sort_values("DAT_FASE"),
        "pendencias": pend[pend["SEQ_PROCESSO_ITCD"] == seq].sort_values("DAT_INCLUSAO"),
        "guias": guias[guias["SEQ_PROCESSO_ITCD"] == seq],
    }
