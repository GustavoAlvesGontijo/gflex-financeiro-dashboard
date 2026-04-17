# -*- coding: utf-8 -*-
"""Projeção & Simulação — futuro por TIPO (Fixo/Variável/Orçamento/Provisão)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
import streamlit as st
import pandas as pd

from config import fmt_brl, fmt_brl_milhao, COR_POSITIVO, COR_NEGATIVO
from data_loader import (
    load_pagamentos, load_recebimentos, eh_aberto,
    classificar_grupo, simular_fluxo, lista_empresas,
)
from styles import inject_css

st.set_page_config(page_title="Projeção & Simulação", page_icon="🔮", layout="wide")
inject_css()

df_pag_raw = load_pagamentos()
df_rec_raw = load_recebimentos()

# Respeita filtro GLOBAL de empresa
emps = st.session_state.get("f_empresas", [])
if emps:
    df_pag_raw = df_pag_raw[df_pag_raw["Emp. Prop."].isin(emps)]
    df_rec_raw = df_rec_raw[df_rec_raw["Emp. Prop."].isin(emps)]

st.markdown("""
<div class="hero" style="background:linear-gradient(135deg,#8E44AD 0%,#1a1a2e 100%)">
<h1>🔮 Projeção & Simulação</h1>
<p>Projeta o futuro pela data de vencimento. Breakdown por TIPO (Fixo, Variável, Orçamento, Provisão).</p>
</div>
""", unsafe_allow_html=True)

# ========== PERÍODO ==========
hoje = date.today()
c1, c2, c3, c4 = st.columns(4)
if "proj_ini" not in st.session_state:
    st.session_state["proj_ini"] = hoje
if "proj_fim" not in st.session_state:
    st.session_state["proj_fim"] = hoje + timedelta(days=30)

if c1.button("7 dias", width="stretch", key="p7"):
    st.session_state["proj_ini"] = hoje
    st.session_state["proj_fim"] = hoje + timedelta(days=7)
    st.rerun()
if c2.button("15 dias", width="stretch", key="p15"):
    st.session_state["proj_ini"] = hoje
    st.session_state["proj_fim"] = hoje + timedelta(days=15)
    st.rerun()
if c3.button("30 dias", width="stretch", key="p30"):
    st.session_state["proj_ini"] = hoje
    st.session_state["proj_fim"] = hoje + timedelta(days=30)
    st.rerun()
if c4.button("60 dias", width="stretch", key="p60"):
    st.session_state["proj_ini"] = hoje
    st.session_state["proj_fim"] = hoje + timedelta(days=60)
    st.rerun()

c1, c2 = st.columns(2)
with c1:
    ini = st.date_input("De", value=st.session_state["proj_ini"], format="DD/MM/YYYY", key="pi")
with c2:
    fim = st.date_input("Até", value=st.session_state["proj_fim"], format="DD/MM/YYYY", key="pf")
st.session_state["proj_ini"] = ini
st.session_state["proj_fim"] = fim

st.markdown(f"### 📊 Projeção {ini.strftime('%d/%m/%Y')} → {fim.strftime('%d/%m/%Y')}")
ini_ts, fim_ts = pd.Timestamp(ini), pd.Timestamp(fim)

dp_fut = df_pag_raw[
    (df_pag_raw["VENCIMENTO"] >= ini_ts) & (df_pag_raw["VENCIMENTO"] <= fim_ts) &
    eh_aberto(df_pag_raw["Situação (Normalizada)"])
].copy()
dr_fut = df_rec_raw[
    (df_rec_raw["Vencimento"] >= ini_ts) & (df_rec_raw["Vencimento"] <= fim_ts) &
    eh_aberto(df_rec_raw["Situação (Normalizada)"])
].copy()

# ========== SAÍDAS POR TIPO (FIXO/VARIÁVEL/ORÇAMENTO/PROVISÃO) ==========
st.markdown("### 💸 Saídas Previstas por TIPO")
st.caption("⚠️ **Provisão** = situação 'Provisão' (pode não se concretizar). Foque em **Fixo + Variável** pro caixa essencial.")

if dp_fut.empty:
    st.info("Sem pagamentos previstos.")
else:
    # Separa Provisão (situação) e TIPO
    dp_fut["TIPO_final"] = dp_fut.apply(
        lambda r: "Provisão" if r.get("Situação (Normalizada)") == "Provisão" else (r.get("TIPO") or "Não classificado"),
        axis=1,
    )
    por_tipo = dp_fut.groupby("TIPO_final").agg(
        Valor=("VALOR","sum"), Qtd=("VALOR","count")
    ).reset_index().sort_values("Valor", ascending=False)
    total = {"TIPO_final":"TOTAL","Valor":por_tipo["Valor"].sum(),"Qtd":por_tipo["Qtd"].sum()}
    por_tipo = pd.concat([por_tipo, pd.DataFrame([total])], ignore_index=True)

    show = por_tipo.copy()
    show["Valor"] = show["Valor"].apply(fmt_brl)
    show = show.rename(columns={"TIPO_final": "Tipo"})

    def estilo(row):
        if row["Tipo"] == "TOTAL":
            return ['background-color: #1a1a2e; color: white; font-weight: 700']*len(row)
        if row["Tipo"] == "Provisão":
            return ['background-color: #fef9e7; color: #7d6608']*len(row)
        return ['']*len(row)

    st.dataframe(show.style.apply(estilo, axis=1),
                 width="stretch", hide_index=True, height=min(300, 45*(len(show)+1)))

    # Cards essenciais x provisão
    fixo = float(por_tipo[por_tipo["TIPO_final"] == "Fixo"]["Valor"].sum()) if "Fixo" in por_tipo["TIPO_final"].values else 0
    variavel = float(por_tipo[por_tipo["TIPO_final"] == "Variável"]["Valor"].sum()) if "Variável" in por_tipo["TIPO_final"].values else 0
    provisao = float(por_tipo[por_tipo["TIPO_final"] == "Provisão"]["Valor"].sum()) if "Provisão" in por_tipo["TIPO_final"].values else 0
    orcamento = float(por_tipo[por_tipo["TIPO_final"] == "Orçamento"]["Valor"].sum()) if "Orçamento" in por_tipo["TIPO_final"].values else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("🔒 Fixo", fmt_brl_milhao(fixo), delta="Essencial, não atrasa")
    with c2: st.metric("🔄 Variável", fmt_brl_milhao(variavel), delta="Pode renegociar")
    with c3: st.metric("📅 Orçamento", fmt_brl_milhao(orcamento), delta="Planejado, flexível")
    with c4: st.metric("❓ Provisão", fmt_brl_milhao(provisao), delta="Pode não acontecer", delta_color="off")

st.markdown("---")

# ========== PROJEÇÃO POR EMPRESA ==========
st.markdown("### 🏢 Projeção por Empresa")

todas_emp = sorted(set(dp_fut["Emp. Prop."].dropna().unique().tolist() +
                        dr_fut["Emp. Prop."].dropna().unique().tolist()))
rows = []
for emp in todas_emp:
    dp = dp_fut[dp_fut["Emp. Prop."] == emp]
    dr = dr_fut[dr_fut["Emp. Prop."] == emp]
    entrada = float(dr["Valor Total"].sum())
    saida_total = float(dp["VALOR"].sum())
    saida_fixo = float(dp[dp.get("TIPO") == "Fixo"]["VALOR"].sum()) if "TIPO" in dp.columns else 0
    saida_var = float(dp[dp.get("TIPO") == "Variável"]["VALOR"].sum()) if "TIPO" in dp.columns else 0
    saida_prov = float(dp[dp.get("Situação (Normalizada)") == "Provisão"]["VALOR"].sum())
    rows.append({
        "Empresa": emp,
        "Grupo": classificar_grupo(emp),
        "Entrada Prevista": entrada,
        "Saída Total": saida_total,
        "— Fixo": saida_fixo,
        "— Variável": saida_var,
        "— Provisão": saida_prov,
        "Saldo (c/ provisão)": entrada - saida_total,
        "Saldo (s/ provisão)": entrada - (saida_total - saida_prov),
    })

tab = pd.DataFrame(rows)
if tab.empty:
    st.info("Sem movimentação futura por empresa.")
else:
    total = {"Empresa":"TOTAL","Grupo":"—"}
    for c in ["Entrada Prevista","Saída Total","— Fixo","— Variável","— Provisão",
              "Saldo (c/ provisão)","Saldo (s/ provisão)"]:
        total[c] = tab[c].sum()
    tab_f = pd.concat([tab.sort_values("Saldo (s/ provisão)"), pd.DataFrame([total])], ignore_index=True)

    show = tab_f.copy()
    for c in ["Entrada Prevista","Saída Total","— Fixo","— Variável","— Provisão",
              "Saldo (c/ provisão)","Saldo (s/ provisão)"]:
        show[c] = show[c].apply(fmt_brl)

    def estilo(row):
        if row["Empresa"] == "TOTAL":
            return ['background-color: #1a1a2e; color: white; font-weight: 700']*len(row)
        return ['']*len(row)

    def cor_verde(v):
        if v == "R$ 0,00": return ""
        return f"color: {COR_POSITIVO}; font-weight: 600"
    def cor_vermelho(v):
        if v == "R$ 0,00": return ""
        return f"color: {COR_NEGATIVO}; font-weight: 600"

    styler = show.style.apply(estilo, axis=1)
    styler = styler.map(cor_verde, subset=["Entrada Prevista"])
    for c in ["Saída Total","— Fixo","— Variável","— Provisão"]:
        styler = styler.map(cor_vermelho, subset=[c])

    st.dataframe(styler, width="stretch", hide_index=True, height=min(600, 45*(len(show)+1)))

    # Cards gerais
    tot = tab_f.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("💵 Entrada", fmt_brl_milhao(tot["Entrada Prevista"]))
    with c2: st.metric("💸 Saída Total", fmt_brl_milhao(tot["Saída Total"]))
    with c3:
        sc = tot["Saldo (c/ provisão)"]
        st.metric("Saldo (c/ provisão)", fmt_brl_milhao(sc),
                   delta_color="normal" if sc>=0 else "inverse")
    with c4:
        ss = tot["Saldo (s/ provisão)"]
        st.metric("Saldo (s/ provisão)", fmt_brl_milhao(ss),
                   delta="Cenário realista",
                   delta_color="normal" if ss>=0 else "inverse")

st.markdown("---")

# ========== SIMULAÇÃO DE ATRASO ==========
st.markdown("## 🎯 Simulação: e se eu atrasar X dias?")
c1, c2 = st.columns([1, 3])
with c1:
    dias_atrasar = st.slider("Dias de atraso", min_value=0, max_value=60, value=0, step=1, key="sim_dias")
with c2:
    st.caption(f"Simulação: atraso de {dias_atrasar} dias em todos os pagamentos vencendo em {ini.strftime('%d/%m')} → {fim.strftime('%d/%m')}")

sim = simular_fluxo(df_pag_raw, df_rec_raw, dias_atrasar, ini, fim)
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("💵 Entrada Prevista", fmt_brl_milhao(sim["Entrada Prevista"]))
    st.metric("💸 Saída Original",  fmt_brl_milhao(sim["Saída Original"]))
with c2:
    st.metric("💸 Saída Simulada",  fmt_brl_milhao(sim["Saída Simulada"]),
               delta=fmt_brl_milhao(-sim["Economia no Período"]) + " vs orig.")
    st.metric("💰 Economia",         fmt_brl_milhao(sim["Economia no Período"]),
               delta=f"{dias_atrasar}d de fôlego")
with c3:
    st.metric("Saldo Original",     fmt_brl_milhao(sim["Saldo Original"]),
               delta_color="normal" if sim["Saldo Original"]>=0 else "inverse")
    st.metric("🎯 Saldo Simulado",    fmt_brl_milhao(sim["Saldo Simulado"]),
               delta_color="normal" if sim["Saldo Simulado"]>=0 else "inverse")

if dias_atrasar > 0:
    if sim["Saldo Simulado"] > 0 and sim["Saldo Original"] < 0:
        st.success(f"✅ Atrasando {dias_atrasar} dias, saldo fica POSITIVO. Viável.")
    elif sim["Saldo Simulado"] < 0 and sim["Saldo Original"] < 0:
        st.error(f"⚠️ Mesmo atrasando {dias_atrasar} dias, saldo NEGATIVO. Precisa renegociar entradas/cortar.")

st.markdown("---")

# ========== TABELA: TUDO QUE VENCE NO PERÍODO ==========
st.markdown("### 📋 Pagamentos previstos no período")
if dp_fut.empty:
    st.info("Sem pagamentos no período.")
else:
    cols = ["Emp. Prop.","FORNECEDOR","DESCRIÇÃO","Descrição Plano de Contas","TIPO","DEPARTAMENTO",
            "VALOR","VENCIMENTO","Situação (Normalizada)"]
    cols = [c for c in cols if c in dp_fut.columns]
    show = dp_fut[cols].sort_values("VENCIMENTO").copy()
    if "VENCIMENTO" in show: show["VENCIMENTO"] = show["VENCIMENTO"].dt.strftime("%d/%m/%Y")
    if "VALOR" in show: show["VALOR"] = show["VALOR"].apply(fmt_brl)
    st.dataframe(show, width="stretch", hide_index=True, height=400)
