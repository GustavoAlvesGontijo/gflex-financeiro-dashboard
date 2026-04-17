# -*- coding: utf-8 -*-
"""Por Empresa — multi-seleção. Ver 1, algumas, ou todas somadas."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
import streamlit as st
import pandas as pd

from config import fmt_brl, fmt_brl_milhao, CORES, COR_POSITIVO, COR_NEGATIVO
from data_loader import (
    load_pagamentos, load_recebimentos, filtrar, eh_pago, eh_aberto,
    lista_empresas, classificar_grupo, entrada_saida_periodo,
)
from styles import inject_css

st.set_page_config(page_title="Por Empresa", page_icon="🏢", layout="wide")
inject_css()

base = st.session_state.get("f_base_data", "Vencimento")
base_pag = "VENCIMENTO" if base == "Vencimento" else "DATA DE PGTO."
base_rec = "Vencimento" if base == "Vencimento" else "Data PGTO."

df_pag_all = load_pagamentos()
df_rec_all = load_recebimentos()
df_pag = filtrar(df_pag_all, base_pag)
df_rec = filtrar(df_rec_all, base_rec)

emp_disponiveis = lista_empresas(df_pag, df_rec)

st.markdown("""
<div class="hero">
<h1>🏢 Por Empresa — Análise</h1>
<p>Selecione 1 ou várias empresas pra ver o exercício somado.</p>
</div>
""", unsafe_allow_html=True)

if not emp_disponiveis:
    st.warning("Sem dados. Ajuste filtros.")
    st.stop()

c1, c2 = st.columns([3, 1])
with c1:
    emp_sel = st.multiselect("Empresa(s) em foco",
                              options=emp_disponiveis,
                              default=[emp_disponiveis[0]] if emp_disponiveis else [],
                              placeholder="Selecione 1 ou mais",
                              key="emp_focus_multi")
with c2:
    granul = st.radio("Granularidade", ["Dia","Semana","Mês"], index=2, horizontal=True, key="emp_gran")

if not emp_sel:
    st.info("👆 Selecione pelo menos 1 empresa pra começar.")
    st.stop()

# Filtra pelas empresas selecionadas
dp_e = df_pag[df_pag["Emp. Prop."].isin(emp_sel)].copy()
dr_e = df_rec[df_rec["Emp. Prop."].isin(emp_sel)].copy()

if len(emp_sel) == 1:
    titulo = emp_sel[0]
else:
    titulo = f"{len(emp_sel)} empresas somadas: {', '.join(emp_sel[:3])}" + ("..." if len(emp_sel) > 3 else "")

st.markdown(f"""
<div style="background:linear-gradient(135deg,#004A9D 0%, #1a1a2e 100%);padding:18px 22px;border-radius:12px;color:white;margin-bottom:18px">
<h2 style="margin:0;color:white">{titulo}</h2>
</div>
""", unsafe_allow_html=True)

# ========== KPIs ==========
pago = float(dp_e.loc[eh_pago(dp_e["Situação (Normalizada)"]), "VALOR"].sum())
a_pagar = float(dp_e.loc[eh_aberto(dp_e["Situação (Normalizada)"]), "VALOR"].sum())
atraso_p = float(dp_e.loc[eh_aberto(dp_e["Situação (Normalizada)"]) & (dp_e.get("Atrasado?") == "S"), "VALOR"].sum())
qtd_atr = int((eh_aberto(dp_e["Situação (Normalizada)"]) & (dp_e.get("Atrasado?") == "S")).sum())

rec = float(dr_e.loc[eh_pago(dr_e["Situação (Normalizada)"]), "Valor Total"].sum())
a_rec = float(dr_e.loc[eh_aberto(dr_e["Situação (Normalizada)"]), "Valor Total"].sum())
inad = float(dr_e.loc[eh_aberto(dr_e["Situação (Normalizada)"]) & (dr_e.get("Atrasado?") == "S"), "Valor Total"].sum())
qtd_inad = int((eh_aberto(dr_e["Situação (Normalizada)"]) & (dr_e.get("Atrasado?") == "S")).sum())

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("💵 Recebido", fmt_brl_milhao(rec))
    st.metric("📝 A Receber", fmt_brl_milhao(a_rec))
with c2:
    st.metric("💸 Pago", fmt_brl_milhao(pago))
    st.metric("📋 A Pagar", fmt_brl_milhao(a_pagar))
with c3:
    st.metric("⚠️ Inadimplência", fmt_brl_milhao(inad), delta=f"{qtd_inad} faturas", delta_color="inverse")
    st.metric("⏰ Pagto Atrasado", fmt_brl_milhao(atraso_p), delta=f"{qtd_atr} faturas", delta_color="inverse")
with c4:
    st.metric("💰 Saldo Realizado", fmt_brl_milhao(rec - pago),
               delta="Positivo" if rec-pago>=0 else "Negativo",
               delta_color="normal" if rec-pago>=0 else "inverse")
    st.metric("🔮 Saldo Projetado", fmt_brl_milhao(a_rec - a_pagar),
               delta_color="normal" if a_rec-a_pagar>=0 else "inverse")

st.markdown("---")

# ========== FLUXO POR PERÍODO (tabela) ==========
st.markdown(f"### 📈 Exercício por {granul}")
fluxo = entrada_saida_periodo(dp_e, dr_e, granul)
if fluxo.empty:
    st.info("Sem movimentação.")
else:
    show = fluxo.copy()
    for c in ["Entrada","Saída","Saldo","Acumulado"]:
        show[c] = show[c].apply(fmt_brl)

    def estilo_tot(row):
        if row["Período"] == "TOTAL":
            return ['background-color: #1a1a2e; color: white; font-weight: 700']*len(row)
        return ['']*len(row)

    st.dataframe(show.style.apply(estilo_tot, axis=1),
                 width="stretch", hide_index=True, height=min(600, 45*(len(show)+1)))

st.markdown("---")

# ========== BREAKDOWN POR EMPRESA (se múltiplas) ==========
if len(emp_sel) > 1:
    st.markdown("### 🏢 Breakdown por empresa selecionada")
    rows = []
    for emp in emp_sel:
        dp = dp_e[dp_e["Emp. Prop."] == emp]
        dr = dr_e[dr_e["Emp. Prop."] == emp]
        rows.append({
            "Empresa": emp,
            "Recebido": float(dr.loc[eh_pago(dr["Situação (Normalizada)"]), "Valor Total"].sum()),
            "Pago": float(dp.loc[eh_pago(dp["Situação (Normalizada)"]), "VALOR"].sum()),
            "A Receber": float(dr.loc[eh_aberto(dr["Situação (Normalizada)"]), "Valor Total"].sum()),
            "A Pagar": float(dp.loc[eh_aberto(dp["Situação (Normalizada)"]), "VALOR"].sum()),
        })
    df = pd.DataFrame(rows)
    df["Saldo"] = df["Recebido"] - df["Pago"]
    total = {"Empresa":"TOTAL",
             "Recebido":df["Recebido"].sum(),"Pago":df["Pago"].sum(),
             "A Receber":df["A Receber"].sum(),"A Pagar":df["A Pagar"].sum(),
             "Saldo":df["Saldo"].sum()}
    df = pd.concat([df.sort_values("Saldo", ascending=False), pd.DataFrame([total])], ignore_index=True)
    show = df.copy()
    for c in ["Recebido","Pago","A Receber","A Pagar","Saldo"]:
        show[c] = show[c].apply(fmt_brl)
    def estilo(row):
        if row["Empresa"] == "TOTAL":
            return ['background-color: #1a1a2e; color: white; font-weight: 700']*len(row)
        return ['']*len(row)
    st.dataframe(show.style.apply(estilo, axis=1),
                 width="stretch", hide_index=True, height=min(400, 45*(len(show)+1)))

    st.markdown("---")

# ========== PLANO DE CONTAS ==========
st.markdown("### 🏗️ Despesa por Plano de Contas")
if "Descrição Plano de Contas" in dp_e.columns and not dp_e.empty:
    pc = dp_e.groupby(["Descrição Plano de Contas","TIPO"], dropna=False).apply(
        lambda x: pd.Series({
            "Pago": x.loc[eh_pago(x["Situação (Normalizada)"]), "VALOR"].sum(),
            "A Pagar": x.loc[eh_aberto(x["Situação (Normalizada)"]), "VALOR"].sum(),
            "Total": x["VALOR"].sum(),
            "Qtd": len(x),
        }),
    ).reset_index().sort_values("Total", ascending=False)

    total = {"Descrição Plano de Contas":"TOTAL","TIPO":"—",
             "Pago":pc["Pago"].sum(),"A Pagar":pc["A Pagar"].sum(),
             "Total":pc["Total"].sum(),"Qtd":pc["Qtd"].sum()}
    pc = pd.concat([pc, pd.DataFrame([total])], ignore_index=True)

    show = pc.copy()
    for c in ["Pago","A Pagar","Total"]:
        show[c] = show[c].apply(fmt_brl)
    def estilo_tot(row):
        if row["Descrição Plano de Contas"] == "TOTAL":
            return ['background-color: #1a1a2e; color: white; font-weight: 700']*len(row)
        return ['']*len(row)
    st.dataframe(show.style.apply(estilo_tot, axis=1),
                 width="stretch", hide_index=True, height=min(600, 45*(len(show)+1)))

st.markdown("---")

# ========== TABELAS DETALHE ==========
tab1, tab2 = st.tabs([f"💸 Pagamentos ({len(dp_e)})", f"💵 Recebimentos ({len(dr_e)})"])

with tab1:
    st.caption("💡 Busca à direita | Clique cabeçalho pra ordenar")
    cols_p = ["Emp. Prop.","FORNECEDOR","DESCRIÇÃO","Descrição Plano de Contas","TIPO","DEPARTAMENTO",
              "VALOR","VENCIMENTO","DATA DE PGTO.","Situação (Normalizada)","Dias de Atraso"]
    cols_p = [c for c in cols_p if c in dp_e.columns]
    show_p = dp_e[cols_p].copy()
    if "VENCIMENTO" in show_p: show_p["VENCIMENTO"] = show_p["VENCIMENTO"].dt.strftime("%d/%m/%Y")
    if "DATA DE PGTO." in show_p: show_p["DATA DE PGTO."] = show_p["DATA DE PGTO."].dt.strftime("%d/%m/%Y")
    if "VALOR" in show_p: show_p["VALOR"] = show_p["VALOR"].apply(fmt_brl)
    st.dataframe(show_p, width="stretch", hide_index=True, height=500)

with tab2:
    st.caption("💡 Busca à direita | Clique cabeçalho pra ordenar")
    cols_r = ["Emp. Prop.","Empresa","OS","NF","Valor Total","Emissão","Vencimento","Data PGTO.",
              "Situação (Normalizada)","Dias de Atraso","Forma PGTO."]
    cols_r = [c for c in cols_r if c in dr_e.columns]
    show_r = dr_e[cols_r].copy()
    for c in ["Emissão","Vencimento","Data PGTO."]:
        if c in show_r: show_r[c] = show_r[c].dt.strftime("%d/%m/%Y")
    if "Valor Total" in show_r: show_r["Valor Total"] = show_r["Valor Total"].apply(fmt_brl)
    st.dataframe(show_r, width="stretch", hide_index=True, height=500)
