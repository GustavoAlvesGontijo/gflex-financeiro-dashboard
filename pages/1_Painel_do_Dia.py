# -*- coding: utf-8 -*-
"""Painel do Dia — movimentação por empresa num período (hoje, ontem, semana, range custom)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
import streamlit as st
import pandas as pd

from config import fmt_brl, fmt_brl_milhao, COR_POSITIVO, COR_NEGATIVO
from data_loader import (
    load_pagamentos, load_recebimentos, eh_pago, eh_aberto,
    classificar_grupo, lista_empresas,
)
from styles import inject_css

st.set_page_config(page_title="Painel do Dia", page_icon="📅", layout="wide")
inject_css()

df_pag_raw = load_pagamentos()
df_rec_raw = load_recebimentos()

st.markdown("""
<div class="hero">
<h1>📅 Painel do Dia / Período</h1>
<p>Quanto cada empresa pagou/recebeu. Escolha a data ou intervalo.</p>
</div>
""", unsafe_allow_html=True)

# ========== FILTROS LOCAIS (sobrepõem globais) ==========
c1, c2 = st.columns([3, 2])

with c1:
    st.markdown("**🏢 Empresas (use vazio pra ver todas)**")
    todas_emp = lista_empresas(df_pag_raw, df_rec_raw)
    emp_sel = st.multiselect(
        "Empresas", options=todas_emp,
        default=st.session_state.get("f_empresas", []),
        placeholder="Todas as empresas",
        key="painel_empresas", label_visibility="collapsed",
    )

with c2:
    st.markdown("**📅 Período**")
    hoje = date.today()
    cb1, cb2, cb3, cb4 = st.columns(4)
    if cb1.button("Hoje", width="stretch", key="pd_h"):
        st.session_state["pd_ini"] = hoje
        st.session_state["pd_fim"] = hoje
        st.rerun()
    if cb2.button("Ontem", width="stretch", key="pd_o"):
        o = hoje - timedelta(days=1)
        st.session_state["pd_ini"] = o
        st.session_state["pd_fim"] = o
        st.rerun()
    if cb3.button("7 dias", width="stretch", key="pd_7d"):
        st.session_state["pd_ini"] = hoje - timedelta(days=6)
        st.session_state["pd_fim"] = hoje
        st.rerun()
    if cb4.button("Mês", width="stretch", key="pd_mes"):
        st.session_state["pd_ini"] = hoje.replace(day=1)
        st.session_state["pd_fim"] = hoje
        st.rerun()

ini = st.session_state.get("pd_ini", hoje - timedelta(days=1))
fim = st.session_state.get("pd_fim", hoje - timedelta(days=1))

c1, c2 = st.columns(2)
with c1:
    ini = st.date_input("De", value=ini, format="DD/MM/YYYY", key="pd_ini_in")
with c2:
    fim = st.date_input("Até", value=fim, format="DD/MM/YYYY", key="pd_fim_in")
st.session_state["pd_ini"] = ini
st.session_state["pd_fim"] = fim

# Aplica empresa
if emp_sel:
    df_pag_raw = df_pag_raw[df_pag_raw["Emp. Prop."].isin(emp_sel)]
    df_rec_raw = df_rec_raw[df_rec_raw["Emp. Prop."].isin(emp_sel)]

ini_ts, fim_ts = pd.Timestamp(ini), pd.Timestamp(fim)

if ini == fim:
    st.markdown(f"### 🎯 Movimentação em **{ini.strftime('%A, %d/%m/%Y').capitalize()}**")
else:
    dias = (fim - ini).days + 1
    st.markdown(f"### 🎯 Movimentação em **{ini.strftime('%d/%m/%Y')} → {fim.strftime('%d/%m/%Y')}** ({dias} dias)")

# ========== FILTROS POR DATA ==========
# PAGAMENTOS EFETUADOS (data de pgto real)
pag_efet = df_pag_raw[
    (df_pag_raw["DATA DE PGTO."] >= ini_ts) &
    (df_pag_raw["DATA DE PGTO."] <= fim_ts) &
    eh_pago(df_pag_raw["Situação (Normalizada)"])
].copy()

# RECEBIMENTOS EFETUADOS
rec_efet = df_rec_raw[
    (df_rec_raw["Data PGTO."] >= ini_ts) &
    (df_rec_raw["Data PGTO."] <= fim_ts) &
    eh_pago(df_rec_raw["Situação (Normalizada)"])
].copy()

# VENCIMENTOS NO PERÍODO (pagamentos a vencer não pagos)
venc_pag = df_pag_raw[
    (df_pag_raw["VENCIMENTO"] >= ini_ts) &
    (df_pag_raw["VENCIMENTO"] <= fim_ts) &
    eh_aberto(df_pag_raw["Situação (Normalizada)"])
].copy()

# VENCIMENTOS de recebíveis
venc_rec = df_rec_raw[
    (df_rec_raw["Vencimento"] >= ini_ts) &
    (df_rec_raw["Vencimento"] <= fim_ts) &
    eh_aberto(df_rec_raw["Situação (Normalizada)"])
].copy()

# ========== TABELA POR EMPRESA ==========
todas_emp_filt = sorted(set(
    df_pag_raw["Emp. Prop."].dropna().unique().tolist() +
    df_rec_raw["Emp. Prop."].dropna().unique().tolist()
))

rows = []
for emp in todas_emp_filt:
    recebido = float(rec_efet[rec_efet["Emp. Prop."] == emp]["Valor Total"].sum())
    pago = float(pag_efet[pag_efet["Emp. Prop."] == emp]["VALOR"].sum())
    rec_abrir = float(venc_rec[venc_rec["Emp. Prop."] == emp]["Valor Total"].sum())
    pag_abrir = float(venc_pag[venc_pag["Emp. Prop."] == emp]["VALOR"].sum())
    rows.append({
        "Empresa": emp,
        "Grupo": classificar_grupo(emp),
        "Recebido (realizado)": recebido,
        "Pago (realizado)": pago,
        "Saldo Realizado": recebido - pago,
        "A Receber (vence)": rec_abrir,
        "A Pagar (vence)": pag_abrir,
        "Saldo Projetado": rec_abrir - pag_abrir,
        "Qtd Rec": len(rec_efet[rec_efet["Emp. Prop."] == emp]),
        "Qtd Pag": len(pag_efet[pag_efet["Emp. Prop."] == emp]),
    })

tab = pd.DataFrame(rows)
tab = tab[(tab["Recebido (realizado)"] != 0) | (tab["Pago (realizado)"] != 0) |
           (tab["A Receber (vence)"] != 0) | (tab["A Pagar (vence)"] != 0)]

if tab.empty:
    st.info(f"Sem movimentação no período selecionado.")
else:
    total = {
        "Empresa": "TOTAL", "Grupo": "—",
        "Recebido (realizado)": tab["Recebido (realizado)"].sum(),
        "Pago (realizado)": tab["Pago (realizado)"].sum(),
        "Saldo Realizado": tab["Saldo Realizado"].sum(),
        "A Receber (vence)": tab["A Receber (vence)"].sum(),
        "A Pagar (vence)": tab["A Pagar (vence)"].sum(),
        "Saldo Projetado": tab["Saldo Projetado"].sum(),
        "Qtd Rec": tab["Qtd Rec"].sum(),
        "Qtd Pag": tab["Qtd Pag"].sum(),
    }
    tab_sorted = tab.sort_values("Saldo Realizado", ascending=False)
    tab_final = pd.concat([tab_sorted, pd.DataFrame([total])], ignore_index=True)

    show = tab_final.copy()
    for c in ["Recebido (realizado)","Pago (realizado)","Saldo Realizado",
              "A Receber (vence)","A Pagar (vence)","Saldo Projetado"]:
        show[c] = show[c].apply(fmt_brl)

    def estilo_cels(row):
        styles = [''] * len(row)
        if row["Empresa"] == "TOTAL":
            styles = ['background-color: #1a1a2e; color: white; font-weight: 700'] * len(row)
        return styles

    st.dataframe(show.style.apply(estilo_cels, axis=1),
                 width="stretch", hide_index=True, height=min(600, 45*(len(show)+1)))

    # Cards
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("💵 Recebido", fmt_brl_milhao(total["Recebido (realizado)"]),
                        delta=f"{int(total['Qtd Rec'])} faturas")
    with c2: st.metric("💸 Pago", fmt_brl_milhao(total["Pago (realizado)"]),
                        delta=f"{int(total['Qtd Pag'])} faturas")
    with c3:
        sr = total["Saldo Realizado"]
        st.metric("💰 Saldo Realizado", fmt_brl_milhao(sr),
                   delta="Positivo" if sr>=0 else "Negativo",
                   delta_color="normal" if sr>=0 else "inverse")

st.markdown("---")

# ========== DETALHAMENTO COM DATAS ==========
st.markdown("### 📋 Movimentações Detalhadas")

tab1, tab2, tab3, tab4 = st.tabs([
    f"💵 Recebidos ({len(rec_efet)})",
    f"💸 Pagos ({len(pag_efet)})",
    f"📝 A Receber no período ({len(venc_rec)})",
    f"📋 A Pagar no período ({len(venc_pag)})",
])

with tab1:
    if rec_efet.empty:
        st.info("Nenhum recebimento no período.")
    else:
        cols = ["Emp. Prop.","Empresa","OS","NF","Valor Total","Data PGTO.","Vencimento","Forma PGTO.","Situação (Normalizada)"]
        cols = [c for c in cols if c in rec_efet.columns]
        show = rec_efet[cols].sort_values("Data PGTO.", ascending=False).copy()
        if "Data PGTO." in show: show["Data PGTO."] = show["Data PGTO."].dt.strftime("%d/%m/%Y")
        if "Vencimento" in show: show["Vencimento"] = show["Vencimento"].dt.strftime("%d/%m/%Y")
        if "Valor Total" in show: show["Valor Total"] = show["Valor Total"].apply(fmt_brl)
        st.dataframe(show, width="stretch", hide_index=True, height=400)

with tab2:
    if pag_efet.empty:
        st.info("Nenhum pagamento no período.")
    else:
        cols = ["Emp. Prop.","FORNECEDOR","DESCRIÇÃO","Descrição Plano de Contas","TIPO","DEPARTAMENTO",
                "VALOR","DATA DE PGTO.","VENCIMENTO","FORMA PGTO"]
        cols = [c for c in cols if c in pag_efet.columns]
        show = pag_efet[cols].sort_values("DATA DE PGTO.", ascending=False).copy()
        if "DATA DE PGTO." in show: show["DATA DE PGTO."] = show["DATA DE PGTO."].dt.strftime("%d/%m/%Y")
        if "VENCIMENTO" in show: show["VENCIMENTO"] = show["VENCIMENTO"].dt.strftime("%d/%m/%Y")
        if "VALOR" in show: show["VALOR"] = show["VALOR"].apply(fmt_brl)
        st.dataframe(show, width="stretch", hide_index=True, height=400)

with tab3:
    if venc_rec.empty:
        st.info("Nenhum recebível vencendo no período.")
    else:
        cols = ["Emp. Prop.","Empresa","OS","NF","Valor Total","Vencimento","Previsão PGTO.","Situação (Normalizada)","Dias de Atraso"]
        cols = [c for c in cols if c in venc_rec.columns]
        show = venc_rec[cols].sort_values("Vencimento").copy()
        if "Vencimento" in show: show["Vencimento"] = show["Vencimento"].dt.strftime("%d/%m/%Y")
        if "Previsão PGTO." in show: show["Previsão PGTO."] = show["Previsão PGTO."].dt.strftime("%d/%m/%Y")
        if "Valor Total" in show: show["Valor Total"] = show["Valor Total"].apply(fmt_brl)
        st.dataframe(show, width="stretch", hide_index=True, height=400)

with tab4:
    if venc_pag.empty:
        st.info("Nenhum pagamento vencendo no período.")
    else:
        cols = ["Emp. Prop.","FORNECEDOR","DESCRIÇÃO","Descrição Plano de Contas","TIPO","DEPARTAMENTO",
                "VALOR","VENCIMENTO","Situação (Normalizada)","Dias de Atraso"]
        cols = [c for c in cols if c in venc_pag.columns]
        show = venc_pag[cols].sort_values("VENCIMENTO").copy()
        if "VENCIMENTO" in show: show["VENCIMENTO"] = show["VENCIMENTO"].dt.strftime("%d/%m/%Y")
        if "VALOR" in show: show["VALOR"] = show["VALOR"].apply(fmt_brl)
        st.dataframe(show, width="stretch", hide_index=True, height=400)

st.caption("💡 **Esta página ignora o filtro global de período** — você escolhe aqui. Filtros de empresa do sidebar são aplicados SE você não selecionar nada no seletor de empresas acima.")
