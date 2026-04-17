# -*- coding: utf-8 -*-
"""DRE — Receita − Despesa por empresa e plano de contas, COM filtros locais."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
import streamlit as st
import pandas as pd

from config import fmt_brl, fmt_brl_milhao, fmt_pct, COR_POSITIVO, COR_NEGATIVO
from data_loader import (
    load_pagamentos, load_recebimentos,
    dre_por_empresa, dre_plano_contas_por_empresa,
    lista_empresas, eh_aberto, eh_pago,
)
from styles import inject_css

st.set_page_config(page_title="DRE", page_icon="📊", layout="wide")
inject_css()

df_pag_raw = load_pagamentos()
df_rec_raw = load_recebimentos()

st.markdown("""
<div class="hero" style="background:linear-gradient(135deg,#517e45 0%,#1a1a2e 100%)">
<h1>📊 DRE Simplificado</h1>
<p>Receita − Despesa. Filtros locais — combina com os globais do sidebar.</p>
</div>
""", unsafe_allow_html=True)

# ========== FILTROS LOCAIS DA PÁGINA ==========
c1, c2, c3 = st.columns([2, 2, 2])
with c1:
    st.markdown("**🏢 Empresas**")
    emp_sel = st.multiselect(
        "Empresas", options=lista_empresas(df_pag_raw, df_rec_raw),
        default=st.session_state.get("f_empresas", []),
        placeholder="Todas", key="dre_empresas", label_visibility="collapsed",
    )
with c2:
    st.markdown("**📅 Período**")
    hoje = date.today()
    cb1, cb2, cb3 = st.columns(3)
    if cb1.button("Mês", width="stretch", key="dre_mes"):
        st.session_state["dre_ini"] = hoje.replace(day=1)
        st.session_state["dre_fim"] = hoje
        st.rerun()
    if cb2.button("Trim.", width="stretch", key="dre_tri"):
        st.session_state["dre_ini"] = hoje - timedelta(days=90)
        st.session_state["dre_fim"] = hoje
        st.rerun()
    if cb3.button("Ano", width="stretch", key="dre_ano"):
        st.session_state["dre_ini"] = date(hoje.year, 1, 1)
        st.session_state["dre_fim"] = hoje
        st.rerun()
with c3:
    st.markdown("**🗓️ Base**")
    base = st.radio("Base", ["Vencimento","Pagamento"], horizontal=True, key="dre_base", label_visibility="collapsed")

c1, c2 = st.columns(2)
with c1:
    ini = st.date_input("De", value=st.session_state.get("dre_ini", hoje.replace(day=1)),
                        format="DD/MM/YYYY", key="dre_ini_in")
with c2:
    fim = st.date_input("Até", value=st.session_state.get("dre_fim", hoje),
                        format="DD/MM/YYYY", key="dre_fim_in")
st.session_state["dre_ini"] = ini
st.session_state["dre_fim"] = fim

incluir_provisao = st.checkbox("Incluir Provisão (situação) na despesa", value=False,
                                 help="Provisão pode não se concretizar. Desmarque pra ver cenário realista.")

# Aplica filtros
base_col_pag = "VENCIMENTO" if base == "Vencimento" else "DATA DE PGTO."
base_col_rec = "Vencimento" if base == "Vencimento" else "Data PGTO."
ini_ts, fim_ts = pd.Timestamp(ini), pd.Timestamp(fim)

df_pag = df_pag_raw[
    (df_pag_raw[base_col_pag] >= ini_ts) & (df_pag_raw[base_col_pag] <= fim_ts)
].copy()
df_rec = df_rec_raw[
    (df_rec_raw[base_col_rec] >= ini_ts) & (df_rec_raw[base_col_rec] <= fim_ts)
].copy()

if emp_sel:
    df_pag = df_pag[df_pag["Emp. Prop."].isin(emp_sel)]
    df_rec = df_rec[df_rec["Emp. Prop."].isin(emp_sel)]

if not incluir_provisao:
    df_pag = df_pag[df_pag["Situação (Normalizada)"] != "Provisão"]

st.info(f"📅 **{ini.strftime('%d/%m/%Y')} → {fim.strftime('%d/%m/%Y')}** · 🏢 **{len(emp_sel) if emp_sel else 'Todas'}** · 🗓️ **{base}** · {'Com' if incluir_provisao else 'Sem'} Provisão")

st.markdown("---")

# ========== DRE POR EMPRESA ==========
st.markdown("### 🏢 Resultado por Empresa")
dre = dre_por_empresa(df_pag, df_rec)

if dre.empty:
    st.warning("Sem dados.")
else:
    show = dre.copy()
    show["Receita"] = show["Receita"].apply(fmt_brl)
    show["Despesa"] = show["Despesa"].apply(fmt_brl)
    show["Resultado"] = show["Resultado"].apply(fmt_brl)
    show["Margem %"] = show["Margem %"].apply(fmt_pct)

    def estilo(row):
        if row["Empresa"] == "TOTAL":
            return ['background-color: #1a1a2e; color: white; font-weight: 700']*len(row)
        return ['']*len(row)

    def cor_verde(v):
        return f"color: {COR_POSITIVO}; font-weight: 600" if v != "R$ 0,00" else ""
    def cor_vermelho(v):
        return f"color: {COR_NEGATIVO}; font-weight: 600" if v != "R$ 0,00" else ""

    styler = show.style.apply(estilo, axis=1)
    styler = styler.map(cor_verde, subset=["Receita"])
    styler = styler.map(cor_vermelho, subset=["Despesa"])

    st.dataframe(styler, width="stretch", hide_index=True, height=min(500, 45*(len(show)+1)))

    # Cards
    total = dre[dre["Empresa"] == "TOTAL"].iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("💵 Receita", fmt_brl_milhao(total["Receita"]))
    with c2: st.metric("💸 Despesa", fmt_brl_milhao(total["Despesa"]))
    with c3:
        st.metric("💰 Resultado", fmt_brl_milhao(total["Resultado"]),
                   delta="Positivo 🟢" if total["Resultado"]>=0 else "Negativo 🔴",
                   delta_color="normal" if total["Resultado"]>=0 else "inverse")
    with c4: st.metric("📈 Margem", fmt_pct(total["Margem %"]))

st.markdown("---")

# ========== MATRIZ PLANO DE CONTAS × EMPRESA ==========
st.markdown("### 🏗️ Despesa por Plano de Contas × Empresa")
st.caption("Linhas = categoria de despesa, colunas = empresa. Busca pra filtrar linhas, clique coluna pra ordenar.")

matriz = dre_plano_contas_por_empresa(df_pag)
if matriz.empty:
    st.warning("Sem dados.")
else:
    show = matriz.copy()
    for c in show.columns:
        if c != "Descrição Plano de Contas":
            show[c] = show[c].apply(lambda v: fmt_brl(v) if pd.notna(v) and v != 0 else "—")

    def estilo_m(row):
        if row["Descrição Plano de Contas"] == "TOTAL":
            return ['background-color: #1a1a2e; color: white; font-weight: 700']*len(row)
        return ['']*len(row)
    st.dataframe(show.style.apply(estilo_m, axis=1),
                 width="stretch", hide_index=True, height=min(700, 40*(len(show)+1)))

st.markdown("---")

# ========== BREAKDOWN POR TIPO ==========
if "TIPO" in df_pag.columns and not df_pag.empty:
    st.markdown("### 📊 Despesa por TIPO (Fixo/Variável/Orçamento)")
    tipos = df_pag.groupby("TIPO").agg(
        Valor=("VALOR","sum"), Qtd=("VALOR","count")
    ).reset_index().sort_values("Valor", ascending=False)
    total = {"TIPO":"TOTAL","Valor":tipos["Valor"].sum(),"Qtd":tipos["Qtd"].sum()}
    tipos_f = pd.concat([tipos, pd.DataFrame([total])], ignore_index=True)

    show = tipos_f.copy()
    show["Valor"] = show["Valor"].apply(fmt_brl)
    # Percentual
    tot_v = tipos["Valor"].sum()
    show["% do Total"] = [fmt_pct(v/tot_v) if tot_v > 0 else "0,0%" for v in tipos_f["Valor"]]

    def estilo(row):
        if row["TIPO"] == "TOTAL":
            return ['background-color: #1a1a2e; color: white; font-weight: 700']*len(row)
        return ['']*len(row)
    st.dataframe(show.style.apply(estilo, axis=1),
                 width="stretch", hide_index=True, height=min(300, 45*(len(show)+1)))
