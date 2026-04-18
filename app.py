# -*- coding: utf-8 -*-
"""
Dashboard Financeiro GFlex — Filtros Globais + Página Inicial.
"""
import sys, traceback
print("[GFLEX] app.py iniciando...", flush=True)
print("[GFLEX] python", sys.version, flush=True)

try:
    import streamlit as st
    print("[GFLEX] streamlit importado", flush=True)
except Exception as e:
    print(f"[GFLEX] ERRO importando streamlit: {e}", flush=True)
    traceback.print_exc()
    raise

from datetime import date, datetime, timedelta
import os
print("[GFLEX] datetime/os importados", flush=True)

try:
    from config import (
        MESES_PT, GRUPOS, ORDEM_EMPRESAS,
        ONEDRIVE_DIR, ARQ_PAGAMENTOS, ARQ_RECEBIMENTOS,
        fmt_brl_milhao, fmt_brl,
    )
    print("[GFLEX] config importado", flush=True)
except Exception as e:
    print(f"[GFLEX] ERRO importando config: {e}", flush=True)
    traceback.print_exc()
    raise
from data_loader import (
    load_pagamentos, load_recebimentos,
    lista_empresas, lista_departamentos,
    filtrar, resumo_por_empresa,
)
from styles import inject_css

st.set_page_config(
    page_title="GFlex Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# =========================================
# AUTH
# =========================================
def check_password():
    try:
        correct = st.secrets["app"]["password"]
    except Exception:
        correct = None
    if correct is None: return True
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated: return True
    st.markdown('<div class="hero"><h1>💰 GFlex Financeiro</h1><p>Acesso Restrito</p></div>', unsafe_allow_html=True)
    pwd = st.text_input("Senha", type="password")
    if pwd:
        if pwd == correct:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    return False

if not check_password():
    st.stop()

# =========================================
# DADOS
# =========================================
df_pag_raw = load_pagamentos()
df_rec_raw = load_recebimentos()

def ultima_atualizacao():
    # Local: pega mtime do arquivo
    fp = os.path.join(ONEDRIVE_DIR, ARQ_PAGAMENTOS)
    if os.path.exists(fp):
        return datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%d/%m/%Y %H:%M")
    # Cloud: mostra data atual (cache de 5min)
    return datetime.now().strftime("%d/%m/%Y %H:%M") + " (cache 5min)"


# =========================================
# SIDEBAR — FILTROS GLOBAIS
# =========================================
with st.sidebar:
    st.markdown('<div style="text-align:center;padding:4px 0 10px 0"><h1 style="margin:0;font-size:1.35rem">💰 GFlex</h1><div style="color:#EC8500;font-size:0.72rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase">Financeiro</div></div>', unsafe_allow_html=True)

    st.markdown("### 🎛️ Filtros Globais")
    st.caption("Aplicam em TODAS as páginas")

    todas_emp = lista_empresas(df_pag_raw, df_rec_raw)

    # ===== EMPRESAS =====
    st.markdown("**🏢 Empresas**")
    c1, c2, c3 = st.columns(3)
    if c1.button("OLD CO", width="stretch", key="btn_oldco"):
        st.session_state["f_empresas"] = [e for e in todas_emp if any(o.lower() in e.lower() for o in GRUPOS["OLD CO"])]
        st.rerun()
    if c2.button("NEW CO", width="stretch", key="btn_newco"):
        st.session_state["f_empresas"] = [e for e in todas_emp if any(n.lower() in e.lower() for n in GRUPOS["NEW CO"])]
        st.rerun()
    if c3.button("Todas", width="stretch", key="btn_todas"):
        st.session_state["f_empresas"] = []
        st.rerun()

    empresas_sel = st.multiselect(
        "Empresas",
        options=todas_emp,
        default=st.session_state.get("f_empresas", []),
        placeholder="Todas as empresas",
        key="f_empresas",
        label_visibility="collapsed",
    )

    # ===== PERÍODO — PRESETS =====
    st.markdown("**📅 Período**")
    hoje = date.today()

    c1, c2 = st.columns(2)
    if c1.button("Hoje", width="stretch", key="p_hoje"):
        st.session_state["f_data_ini"] = hoje
        st.session_state["f_data_fim"] = hoje
        st.rerun()
    if c2.button("Ontem", width="stretch", key="p_ontem"):
        o = hoje - timedelta(days=1)
        st.session_state["f_data_ini"] = o
        st.session_state["f_data_fim"] = o
        st.rerun()
    c3, c4 = st.columns(2)
    if c3.button("Esta Sem.", width="stretch", key="p_sem"):
        ini = hoje - timedelta(days=hoje.weekday())
        st.session_state["f_data_ini"] = ini
        st.session_state["f_data_fim"] = ini + timedelta(days=6)
        st.rerun()
    if c4.button("Próx Sem.", width="stretch", key="p_psem"):
        ini = hoje - timedelta(days=hoje.weekday()) + timedelta(days=7)
        st.session_state["f_data_ini"] = ini
        st.session_state["f_data_fim"] = ini + timedelta(days=6)
        st.rerun()
    c5, c6 = st.columns(2)
    if c5.button("Este Mês", width="stretch", key="p_mes"):
        import calendar
        st.session_state["f_data_ini"] = hoje.replace(day=1)
        _, n = calendar.monthrange(hoje.year, hoje.month)
        st.session_state["f_data_fim"] = hoje.replace(day=n)
        st.rerun()
    if c6.button("Próx Mês", width="stretch", key="p_pmes"):
        import calendar
        if hoje.month == 12:
            ini = date(hoje.year+1, 1, 1)
        else:
            ini = date(hoje.year, hoje.month+1, 1)
        _, n = calendar.monthrange(ini.year, ini.month)
        st.session_state["f_data_ini"] = ini
        st.session_state["f_data_fim"] = date(ini.year, ini.month, n)
        st.rerun()
    c7, c8 = st.columns(2)
    if c7.button("Este Ano", width="stretch", key="p_ano"):
        st.session_state["f_data_ini"] = date(hoje.year, 1, 1)
        st.session_state["f_data_fim"] = date(hoje.year, 12, 31)
        st.rerun()
    if c8.button("Tudo", width="stretch", key="p_tudo"):
        st.session_state["f_data_ini"] = None
        st.session_state["f_data_fim"] = None
        st.rerun()

    # Campos manuais de/até
    di_raw = st.session_state.get("f_data_ini", hoje - timedelta(days=30))
    df_raw = st.session_state.get("f_data_fim", hoje)
    data_ini = st.date_input("De", value=di_raw if di_raw else hoje - timedelta(days=30),
                              key="di_manual", format="DD/MM/YYYY")
    data_fim = st.date_input("Até", value=df_raw if df_raw else hoje,
                              key="df_manual", format="DD/MM/YYYY")
    if data_ini != st.session_state.get("f_data_ini"):
        st.session_state["f_data_ini"] = data_ini
    if data_fim != st.session_state.get("f_data_fim"):
        st.session_state["f_data_fim"] = data_fim

    if st.checkbox("Sem filtro de período", key="f_sem_periodo",
                   value=(st.session_state.get("f_data_ini") is None)):
        st.session_state["f_data_ini"] = None
        st.session_state["f_data_fim"] = None

    # ===== BASE =====
    st.markdown("**🗓️ Base de Data**")
    base = st.radio(
        "Filtrar por:",
        options=["Vencimento", "Pagamento"],
        index=0,
        key="f_base_data",
        horizontal=True,
        help="Vencimento = data em que deveria pagar/receber. Pagamento = data real que saiu/entrou.",
    )

    st.markdown("---")
    st.caption(f"📅 Atualizado: {ultima_atualizacao()}")
    if st.button("🔁 Recarregar", width="stretch"):
        st.cache_data.clear()
        st.rerun()


# =========================================
# APLICA FILTROS
# =========================================
base_col_pag = "VENCIMENTO" if base == "Vencimento" else "DATA DE PGTO."
base_col_rec = "Vencimento" if base == "Vencimento" else "Data PGTO."

df_pag = filtrar(df_pag_raw, base_col_pag)
df_rec = filtrar(df_rec_raw, base_col_rec)


# =========================================
# HERO + FILTROS ATIVOS
# =========================================
st.markdown("""
<div class="hero">
<h1>💰 Dashboard Financeiro GFlex</h1>
<p>Decisão diária/semanal — caixa curto, foco em ação</p>
</div>
""", unsafe_allow_html=True)

# Banner filtros ativos
filtros = []
if empresas_sel:
    filtros.append(f"🏢 **{len(empresas_sel)} empresa(s)**")
else:
    filtros.append(f"🏢 **Todas empresas**")
ini, fim = st.session_state.get("f_data_ini"), st.session_state.get("f_data_fim")
if ini and fim:
    if ini == fim:
        filtros.append(f"📅 **{ini.strftime('%d/%m/%Y')}**")
    else:
        filtros.append(f"📅 **{ini.strftime('%d/%m/%Y')} → {fim.strftime('%d/%m/%Y')}**")
else:
    filtros.append("📅 **Sem filtro**")
filtros.append(f"🗓️ **{base}**")
st.info(" · ".join(filtros))


# =========================================
# TABELA RESUMO POR EMPRESA
# =========================================
st.markdown("## 📊 Resumo por Empresa")

resumo = resumo_por_empresa(df_pag, df_rec)

if resumo.empty:
    st.warning("Sem dados no período/filtros selecionados.")
else:
    show = resumo.copy()
    for c in ["Recebido","A Receber","Inadimplência","Pago","A Pagar","Em Atraso",
              "Saldo Realizado","Saldo Projetado"]:
        show[c] = show[c].apply(fmt_brl)

    def estilo(row):
        if row["Empresa"] == "TOTAL":
            return ['background-color: #1a1a2e; color: white; font-weight: 700'] * len(row)
        return [''] * len(row)

    st.dataframe(
        show.style.apply(estilo, axis=1),
        width="stretch", hide_index=True,
        height=min(700, 45*(len(show)+2)),
        column_config={
            "Qtd Inad": st.column_config.NumberColumn("Qtd Inad"),
            "Qtd Atraso": st.column_config.NumberColumn("Qtd Atraso"),
        },
    )
    st.caption("💡 Clique em qualquer coluna pra **ordenar**. Use o campo de busca no topo direito da tabela pra **filtrar por texto**.")

    # ========== TOTAIS (Cards grandes) ==========
    total = resumo[resumo["Empresa"] == "TOTAL"].iloc[0]
    st.markdown("## 💰 Totais Consolidados (filtro aplicado)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("💵 Recebido",       fmt_brl_milhao(total["Recebido"]))
        st.metric("📝 A Receber",       fmt_brl_milhao(total["A Receber"]))
        st.metric("⚠️ Inadimplência",  fmt_brl_milhao(total["Inadimplência"]),
                   delta=f"{int(total['Qtd Inad'])} faturas", delta_color="inverse")
    with c2:
        st.metric("💸 Pago",            fmt_brl_milhao(total["Pago"]))
        st.metric("📋 A Pagar",          fmt_brl_milhao(total["A Pagar"]))
        st.metric("⏰ Em Atraso",        fmt_brl_milhao(total["Em Atraso"]),
                   delta=f"{int(total['Qtd Atraso'])} faturas", delta_color="inverse")
    with c3:
        sr = total["Saldo Realizado"]
        sp = total["Saldo Projetado"]
        st.metric("💰 Saldo Realizado",  fmt_brl_milhao(sr),
                   delta="Recebido − Pago")
        st.metric("🔮 Saldo Projetado",  fmt_brl_milhao(sp),
                   delta="A Receber − A Pagar")
        st.metric("⚖️ Posição Líquida",  fmt_brl_milhao(sr + sp),
                   delta="Saldo Real + Projetado")

st.markdown("---")
st.markdown("### 🧭 Páginas")
st.markdown("""
Use o menu lateral. Todas as páginas respeitam os filtros globais.

| Página | Uso |
|---|---|
| **Painel do Dia** | Decisão rápida hoje/semana — tabela por empresa |
| **Por Empresa** | Drill-down individual |
| **Fluxo de Caixa** | Tabela período × empresa (dia/semana/mês) |
| **Projeção & Simulação** | "Se eu atrasar X dias, saldo fica Y" |
| **DRE** | Receita/Despesa/Resultado por empresa e plano de contas |
| **Auditoria** | Erros de preenchimento nas planilhas |
| **Glossário** | Definição de cada KPI |
""")
