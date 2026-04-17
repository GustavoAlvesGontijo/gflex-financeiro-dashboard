# -*- coding: utf-8 -*-
"""Fluxo de Caixa Realizado — só o que JÁ ENTROU/SAIU do banco."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
from datetime import date

from config import fmt_brl, fmt_brl_milhao, COR_POSITIVO, COR_NEGATIVO
from data_loader import (
    load_pagamentos, load_recebimentos, filtrar, eh_pago,
    classificar_grupo, entrada_saida_periodo, lista_empresas,
)
from styles import inject_css

st.set_page_config(page_title="Fluxo de Caixa", page_icon="💹", layout="wide")
inject_css()

# Aqui usamos Data PGTO. — fluxo é só o que REALIZOU
df_pag = filtrar(load_pagamentos(), "DATA DE PGTO.")
df_rec = filtrar(load_recebimentos(), "Data PGTO.")

st.markdown("""
<div class="hero" style="background:linear-gradient(135deg,#27AE60 0%,#1a1a2e 100%)">
<h1>💹 Fluxo de Caixa Realizado</h1>
<p>Só o que JÁ SAIU/ENTROU no banco (data real de pagamento). Filtros globais aplicados.</p>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns([1, 3])
with c1:
    granul = st.radio("Granularidade", ["Dia","Semana","Mês"], index=2, horizontal=True, key="fc_granul")
with c2:
    emps_ativas = st.session_state.get("f_empresas", [])
    emp_text = f"{len(emps_ativas)} empresa(s)" if emps_ativas else "Todas empresas"
    st.info(f"⚙️ **{emp_text}** · Agrupado por data real (Data PGTO.)")

# ========== 1. TOTAL CONSOLIDADO ==========
st.markdown(f"### 💰 1. Consolidado por {granul} (todas empresas somadas)")
fluxo = entrada_saida_periodo(df_pag, df_rec, granul)

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

    # Aplica cor por célula pra Entrada (verde) e Saída (vermelho)
    def cor_col(col_name, color):
        def _apply(v):
            if v == "R$ 0,00": return ""
            return f"color: {color}; font-weight: 600"
        return _apply

    styler = show.style.apply(estilo_tot, axis=1)
    styler = styler.map(cor_col("Entrada", COR_POSITIVO), subset=["Entrada"])
    styler = styler.map(cor_col("Saída", COR_NEGATIVO), subset=["Saída"])

    st.dataframe(styler, width="stretch", hide_index=True, height=min(500, 45*(len(show)+1)))

st.markdown("---")

# ========== 2. REALIZADO POR EMPRESA (tabela) ==========
st.markdown(f"### 🏢 2. Realizado por Empresa (no período filtrado)")

todas_emp = sorted(set(df_pag["Emp. Prop."].dropna().unique().tolist() +
                        df_rec["Emp. Prop."].dropna().unique().tolist()))
rows = []
for emp in todas_emp:
    entrada = float(df_rec[df_rec["Emp. Prop."] == emp]["Valor Total"].sum()) if not df_rec.empty else 0
    saida = float(df_pag[df_pag["Emp. Prop."] == emp]["VALOR"].sum()) if not df_pag.empty else 0
    rows.append({
        "Empresa": emp,
        "Grupo": classificar_grupo(emp),
        "Entrada": entrada,
        "Saída": saida,
        "Saldo": entrada - saida,
        "Qtd Entradas": len(df_rec[df_rec["Emp. Prop."] == emp]),
        "Qtd Saídas": len(df_pag[df_pag["Emp. Prop."] == emp]),
    })
tab = pd.DataFrame(rows)
tab = tab[(tab["Entrada"] != 0) | (tab["Saída"] != 0)]

if tab.empty:
    st.info("Sem movimentação por empresa.")
else:
    total = {
        "Empresa":"TOTAL","Grupo":"—",
        "Entrada":tab["Entrada"].sum(),"Saída":tab["Saída"].sum(),
        "Saldo":tab["Saldo"].sum(),
        "Qtd Entradas":tab["Qtd Entradas"].sum(),"Qtd Saídas":tab["Qtd Saídas"].sum(),
    }
    tab_f = pd.concat([tab.sort_values("Saldo", ascending=False), pd.DataFrame([total])], ignore_index=True)

    show = tab_f.copy()
    for c in ["Entrada","Saída","Saldo"]:
        show[c] = show[c].apply(fmt_brl)

    def estilo_tot(row):
        if row["Empresa"] == "TOTAL":
            return ['background-color: #1a1a2e; color: white; font-weight: 700']*len(row)
        return ['']*len(row)

    def cor_col(color):
        def _apply(v):
            if v == "R$ 0,00": return ""
            return f"color: {color}; font-weight: 600"
        return _apply

    styler = show.style.apply(estilo_tot, axis=1)
    styler = styler.map(cor_col(COR_POSITIVO), subset=["Entrada"])
    styler = styler.map(cor_col(COR_NEGATIVO), subset=["Saída"])

    st.dataframe(styler, width="stretch", hide_index=True, height=min(600, 45*(len(show)+1)))

    # Totais
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("💵 Entrada Total", fmt_brl_milhao(total["Entrada"]))
    with c2: st.metric("💸 Saída Total", fmt_brl_milhao(total["Saída"]))
    with c3:
        st.metric("💰 Saldo", fmt_brl_milhao(total["Saldo"]),
                   delta_color="normal" if total["Saldo"]>=0 else "inverse")

st.markdown("---")

# ========== 3. MATRIZ EMPRESA × PERÍODO (saldo) ==========
st.markdown(f"### 📊 3. Saldo por Empresa × {granul}")
st.caption("Cada célula = Entrada − Saída daquela empresa naquele período.")

from data_loader import fluxo_empresa_periodo
mat = fluxo_empresa_periodo(df_pag, df_rec, granul)
if mat.empty:
    st.info("Sem dados.")
else:
    num_cols = [c for c in mat.columns if c != "Empresa"]

    def color_cell(val):
        try:
            v = float(val)
            if v > 0: return "background-color: #d5f5e3; color: #1e8449; font-weight: 600"
            if v < 0: return "background-color: #fadbd8; color: #a93226; font-weight: 600"
        except: pass
        return ""

    styler = mat.style.format({c: lambda v: fmt_brl(v) if pd.notna(v) else "—" for c in num_cols})
    styler = styler.map(color_cell, subset=num_cols)
    def estilo_tot_row(row):
        if row["Empresa"] == "TOTAL":
            return ['background-color: #1a1a2e; color: white; font-weight: 700']*len(row)
        return ['']*len(row)
    styler = styler.apply(estilo_tot_row, axis=1)

    st.dataframe(styler, width="stretch", hide_index=True, height=min(600, 45*(len(mat)+1)))

st.markdown("---")

# ========== 4. TABELAS DETALHADAS ==========
st.markdown("### 📋 Movimentações Individuais")
tab1, tab2 = st.tabs([f"💵 Recebimentos ({len(df_rec)})", f"💸 Pagamentos ({len(df_pag)})"])

with tab1:
    if df_rec.empty:
        st.info("Sem recebimentos.")
    else:
        cols = ["Emp. Prop.","Empresa","OS","NF","Valor Total","Data PGTO.","Vencimento","Forma PGTO.","Situação (Normalizada)"]
        cols = [c for c in cols if c in df_rec.columns]
        show = df_rec[cols].sort_values("Data PGTO.", ascending=False).copy()
        for dc in ["Data PGTO.", "Vencimento"]:
            if dc in show: show[dc] = show[dc].dt.strftime("%d/%m/%Y")
        if "Valor Total" in show: show["Valor Total"] = show["Valor Total"].apply(fmt_brl)
        st.dataframe(show, width="stretch", hide_index=True, height=400)

with tab2:
    if df_pag.empty:
        st.info("Sem pagamentos.")
    else:
        cols = ["Emp. Prop.","FORNECEDOR","DESCRIÇÃO","Descrição Plano de Contas","TIPO",
                "VALOR","DATA DE PGTO.","VENCIMENTO","FORMA PGTO","Situação (Normalizada)"]
        cols = [c for c in cols if c in df_pag.columns]
        show = df_pag[cols].sort_values("DATA DE PGTO.", ascending=False).copy()
        for dc in ["DATA DE PGTO.", "VENCIMENTO"]:
            if dc in show: show[dc] = show[dc].dt.strftime("%d/%m/%Y")
        if "VALOR" in show: show["VALOR"] = show["VALOR"].apply(fmt_brl)
        st.dataframe(show, width="stretch", hide_index=True, height=400)
