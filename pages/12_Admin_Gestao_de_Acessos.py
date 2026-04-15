import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import streamlit as st

from coate_styles import aplicar_estilos
from coate_auth import exigir_acesso, obter_usuario_atual
from coate_access_store import (
    aprovar_solicitacao,
    carregar_auditoria,
    carregar_solicitacoes,
    carregar_usuarios,
    redefinir_senha_usuario,
    rejeitar_solicitacao,
    atualizar_permissoes_usuario,
)

aplicar_estilos()
exigir_acesso("admin")

usuario = obter_usuario_atual()
ator = usuario["login"]

st.markdown("## Gestão de Acessos")
st.caption("Aprovação de solicitações, manutenção de perfis e trilha simples de auditoria.")

tab_sol, tab_usr, tab_aud = st.tabs(["Solicitações", "Usuários", "Auditoria"])

with tab_sol:
    df_sol = carregar_solicitacoes()
    c1, c2 = st.columns([1, 2])
    with c1:
        status = st.selectbox("Status", ["Todos", "PENDENTE", "APROVADO", "REJEITADO"], index=1)
    with c2:
        busca = st.text_input("Buscar por nome, login ou e-mail")
    df_f = df_sol.copy()
    if status != "Todos":
        df_f = df_f[df_f["status"].str.upper() == status]
    if busca.strip():
        termo = busca.strip().lower()
        mask = (
            df_f["nome"].str.lower().str.contains(termo, na=False)
            | df_f["login_desejado"].str.lower().str.contains(termo, na=False)
            | df_f["email"].str.lower().str.contains(termo, na=False)
        )
        df_f = df_f[mask]

    st.dataframe(df_f[["id", "data_solicitacao", "nome", "login_desejado", "email", "status"]], use_container_width=True, hide_index=True)

    if not df_f.empty:
        sid = st.selectbox("Selecione a solicitação", [str(x) for x in df_f["id"].tolist()])
        sel = df_sol[df_sol["id"].astype(str) == sid].iloc[0]

        st.markdown("### Análise da solicitação")
        st.write(f"**Nome:** {sel['nome']}")
        st.write(f"**Login desejado:** {sel['login_desejado']}")
        st.write(f"**E-mail:** {sel['email']}")
        st.write(f"**Setor:** {sel['setor']}")
        st.write(f"**Justificativa:** {sel['justificativa']}")

        c1, c2, c3 = st.columns(3)
        with c1:
            p_itcd = st.checkbox("ITCD", value=bool(int(sel["deseja_itcd"])), key=f"sol_itcd_{sid}")
            p_simples = st.checkbox("Simples Nacional", value=bool(int(sel["deseja_simples"])), key=f"sol_simples_{sid}")
        with c2:
            p_atd = st.checkbox("Atendimento", value=bool(int(sel["deseja_atendimento"])), key=f"sol_atd_{sid}")
            p_farol = st.checkbox("FAROL", value=bool(int(sel["deseja_farol"])), key=f"sol_farol_{sid}")
        with c3:
            p_cnae = st.checkbox("Reclassificação CNAE", value=bool(int(sel["deseja_cnae"])), key=f"sol_cnae_{sid}")
            p_admin = st.checkbox("Admin", value=False, key=f"sol_admin_{sid}")

        senha_temporaria = st.text_input("Senha temporária", value="coate123", key=f"senha_{sid}")
        observacao = st.text_area("Observação da análise", key=f"obs_{sid}")

        b1, b2 = st.columns(2)
        with b1:
            if st.button("Aprovar solicitação", use_container_width=True, key=f"aprovar_{sid}"):
                ok, msg = aprovar_solicitacao(
                    solicitacao_id=sid,
                    ator=ator,
                    permissoes={
                        "itcd": p_itcd,
                        "simples": p_simples,
                        "atendimento": p_atd,
                        "farol": p_farol,
                        "cnae": p_cnae,
                        "admin": p_admin,
                    },
                    senha_temporaria=senha_temporaria,
                    observacao=observacao,
                )
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()
        with b2:
            if st.button("Rejeitar solicitação", use_container_width=True, key=f"rejeitar_{sid}"):
                ok, msg = rejeitar_solicitacao(sid, ator=ator, observacao=observacao)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()
    else:
        st.info("Nenhuma solicitação encontrada para o filtro selecionado.")

with tab_usr:
    df_usr = carregar_usuarios()
    c1, c2 = st.columns([2, 1])
    with c1:
        busca_usr = st.text_input("Buscar usuário por login ou nome")
    with c2:
        status_usr = st.selectbox("Situação", ["Todos", "Ativos", "Inativos"])
    dfu = df_usr.copy()
    if busca_usr.strip():
        termo = busca_usr.strip().lower()
        dfu = dfu[dfu["login"].str.lower().str.contains(termo, na=False) | dfu["nome"].str.lower().str.contains(termo, na=False)]
    if status_usr == "Ativos":
        dfu = dfu[dfu["ativo"] == 1]
    elif status_usr == "Inativos":
        dfu = dfu[dfu["ativo"] == 0]

    st.dataframe(dfu[["login", "nome", "setor", "ativo", "admin", "itcd", "simples", "atendimento", "farol", "cnae"]], use_container_width=True, hide_index=True)

    if not dfu.empty:
        login_sel = st.selectbox("Selecione o usuário", dfu["login"].tolist())
        row = df_usr[df_usr["login"] == login_sel].iloc[0]

        c1, c2, c3 = st.columns(3)
        with c1:
            u_itcd = st.checkbox("ITCD", value=bool(int(row["itcd"])), key=f"usr_itcd_{login_sel}")
            u_simples = st.checkbox("Simples Nacional", value=bool(int(row["simples"])), key=f"usr_simples_{login_sel}")
        with c2:
            u_atd = st.checkbox("Atendimento", value=bool(int(row["atendimento"])), key=f"usr_atd_{login_sel}")
            u_farol = st.checkbox("FAROL", value=bool(int(row["farol"])), key=f"usr_farol_{login_sel}")
        with c3:
            u_cnae = st.checkbox("Reclassificação CNAE", value=bool(int(row["cnae"])), key=f"usr_cnae_{login_sel}")
            u_admin = st.checkbox("Admin", value=bool(int(row["admin"])), key=f"usr_admin_{login_sel}")

        u_ativo = st.checkbox("Usuário ativo", value=bool(int(row["ativo"])), key=f"usr_ativo_{login_sel}")
        observacao_usr = st.text_area("Observação do usuário", value=str(row.get("observacao", "")), key=f"obs_usr_{login_sel}")
        nova_senha = st.text_input("Nova senha (opcional)", type="password", key=f"nova_senha_{login_sel}")

        b1, b2 = st.columns(2)
        with b1:
            if st.button("Salvar permissões", use_container_width=True, key=f"salvar_{login_sel}"):
                ok, msg = atualizar_permissoes_usuario(
                    login=login_sel,
                    ator=ator,
                    permissoes={
                        "itcd": u_itcd,
                        "simples": u_simples,
                        "atendimento": u_atd,
                        "farol": u_farol,
                        "cnae": u_cnae,
                    },
                    ativo=u_ativo,
                    admin=u_admin,
                    observacao=observacao_usr,
                )
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()
        with b2:
            if st.button("Redefinir senha", use_container_width=True, key=f"senha_btn_{login_sel}"):
                if not nova_senha:
                    st.error("Informe a nova senha antes de redefinir.")
                else:
                    ok, msg = redefinir_senha_usuario(login_sel, nova_senha, ator=ator)
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()

with tab_aud:
    df_aud = carregar_auditoria()
    busca_aud = st.text_input("Filtrar auditoria")
    if busca_aud.strip():
        termo = busca_aud.strip().lower()
        mask = (
            df_aud["ator"].str.lower().str.contains(termo, na=False)
            | df_aud["acao"].str.lower().str.contains(termo, na=False)
            | df_aud["login_alvo"].str.lower().str.contains(termo, na=False)
            | df_aud["detalhe"].str.lower().str.contains(termo, na=False)
        )
        df_aud = df_aud[mask]
    st.dataframe(df_aud, use_container_width=True, hide_index=True)
