# -*- coding: utf-8 -*-
"""Atrasos — com filtros e sistema de ignorar inadimplências perdidas."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import date, timedelta
import streamlit as st
import pandas as pd

from config import fmt_brl, fmt_brl_milhao, COR_NEGATIVO
from data_loader import (
    load_pagamentos, load_recebimentos, eh_aberto, classificar_grupo, lista_empresas,
)
from styles import inject_css

st.set_page_config(page_title="Atrasos", page_icon="⚠️", layout="wide")
inject_css()

# ========== ARQUIVO DE IGNORADOS ==========
IGNORADOS_FILE = os.path.join(os.path.dirname(__file__), "..", "_ignorados.json")

def load_ignorados():
    if not os.path.exists(IGNORADOS_FILE):
        return {"pagamentos": [], "recebimentos": []}
    try:
        with open(IGNORADOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("pagamentos", [])
        data.setdefault("recebimentos", [])
        return data
    except Exception:
        return {"pagamentos": [], "recebimentos": []}

def save_ignorados(data):
    with open(IGNORADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def make_key_pag(row):
    """Chave única pra identificar um pagamento nas planilhas."""
    parts = [
        str(row.get("Emp. Prop.","")),
        str(row.get("FORNECEDOR","")),
        str(row.get("DESCRIÇÃO",""))[:50],
        str(row.get("VALOR","")),
        str(row.get("VENCIMENTO",""))[:10],
    ]
    return "|".join(parts)

def make_key_rec(row):
    parts = [
        str(row.get("Emp. Prop.","")),
        str(row.get("Empresa",""))[:50],
        str(row.get("OS","")),
        str(row.get("NF","")),
        str(row.get("Valor Total","")),
        str(row.get("Vencimento",""))[:10],
    ]
    return "|".join(parts)

ignorados = load_ignorados()

# ========== DADOS ==========
df_pag_raw = load_pagamentos()
df_rec_raw = load_recebimentos()

st.markdown("""
<div class="hero" style="background:linear-gradient(135deg,#E74C3C 0%,#1a1a2e 100%)">
<h1>⚠️ Atrasos — Ação Imediata</h1>
<p>Pagamentos atrasados + Recebimentos inadimplentes. Filtre, priorize, marque como perdido.</p>
</div>
""", unsafe_allow_html=True)

# ========== FILTROS LOCAIS ==========
c1, c2, c3 = st.columns([3, 2, 1])

with c1:
    todas_emp = lista_empresas(df_pag_raw, df_rec_raw)
    emp_sel = st.multiselect(
        "🏢 Empresas", options=todas_emp,
        default=st.session_state.get("f_empresas", []),
        placeholder="Todas empresas",
        key="atr_empresas",
    )

with c2:
    faixa = st.selectbox(
        "⏰ Faixa de atraso",
        options=["Todos","1–30 dias","31–60 dias","61–90 dias","90+ dias"],
        index=0, key="atr_faixa",
    )

with c3:
    mostrar_ignor = st.checkbox("Mostrar ignorados", value=False, key="atr_mostrar_ign",
                                  help="Por padrão, ocultamos inadimplências que você marcou como 'perdidas'.")

# ========== FILTRA ==========
pag_atr = df_pag_raw[eh_aberto(df_pag_raw["Situação (Normalizada)"]) &
                      (df_pag_raw.get("Atrasado?") == "S")].copy()
rec_inad = df_rec_raw[eh_aberto(df_rec_raw["Situação (Normalizada)"]) &
                       (df_rec_raw.get("Atrasado?") == "S")].copy()

if emp_sel:
    pag_atr = pag_atr[pag_atr["Emp. Prop."].isin(emp_sel)]
    rec_inad = rec_inad[rec_inad["Emp. Prop."].isin(emp_sel)]

# Faixa de atraso
def aplica_faixa(df, col="Dias de Atraso"):
    if col not in df.columns or df.empty: return df
    if faixa == "1–30 dias":    return df[(df[col] >= 1) & (df[col] <= 30)]
    if faixa == "31–60 dias":   return df[(df[col] >= 31) & (df[col] <= 60)]
    if faixa == "61–90 dias":   return df[(df[col] >= 61) & (df[col] <= 90)]
    if faixa == "90+ dias":     return df[df[col] > 90]
    return df

pag_atr = aplica_faixa(pag_atr)
rec_inad = aplica_faixa(rec_inad)

# Remove ignorados
if not mostrar_ignor:
    pag_atr = pag_atr[~pag_atr.apply(make_key_pag, axis=1).isin(ignorados["pagamentos"])]
    rec_inad = rec_inad[~rec_inad.apply(make_key_rec, axis=1).isin(ignorados["recebimentos"])]

ign_count = len(ignorados["recebimentos"]) + len(ignorados["pagamentos"])
if ign_count > 0 and not mostrar_ignor:
    st.caption(f"🙈 {ign_count} item(s) ignorado(s) ocultos. Marque 'Mostrar ignorados' pra ver/restaurar.")

st.markdown("---")

# ========== RESUMO POR EMPRESA ==========
st.markdown("### 📊 Resumo por Empresa")
todas_emp_f = sorted(set(pag_atr["Emp. Prop."].dropna().unique().tolist() +
                          rec_inad["Emp. Prop."].dropna().unique().tolist()))
rows = []
for emp in todas_emp_f:
    dp = pag_atr[pag_atr["Emp. Prop."] == emp]
    dr = rec_inad[rec_inad["Emp. Prop."] == emp]
    rows.append({
        "Empresa": emp,
        "Grupo": classificar_grupo(emp),
        "Pgto em Atraso (você deve)": float(dp["VALOR"].sum()),
        "Qtd Pgto": len(dp),
        "Max Dias (pgto)": int(dp["Dias de Atraso"].max()) if not dp.empty else 0,
        "Inadimplência (cliente deve)": float(dr["Valor Total"].sum()),
        "Qtd Rec": len(dr),
        "Max Dias (rec)": int(dr["Dias de Atraso"].max()) if not dr.empty else 0,
    })
tab = pd.DataFrame(rows)
if tab.empty:
    st.success("🎉 Nenhum atraso no filtro!")
else:
    total = {"Empresa":"TOTAL","Grupo":"—"}
    for c in ["Pgto em Atraso (você deve)","Qtd Pgto","Inadimplência (cliente deve)","Qtd Rec"]:
        total[c] = tab[c].sum()
    total["Max Dias (pgto)"] = tab["Max Dias (pgto)"].max() if not tab.empty else 0
    total["Max Dias (rec)"] = tab["Max Dias (rec)"].max() if not tab.empty else 0
    tab_f = pd.concat([tab.sort_values("Pgto em Atraso (você deve)", ascending=False),
                        pd.DataFrame([total])], ignore_index=True)

    show = tab_f.copy()
    show["Pgto em Atraso (você deve)"] = show["Pgto em Atraso (você deve)"].apply(fmt_brl)
    show["Inadimplência (cliente deve)"] = show["Inadimplência (cliente deve)"].apply(fmt_brl)

    def estilo(row):
        if row["Empresa"] == "TOTAL":
            return ['background-color: #1a1a2e; color: white; font-weight: 700']*len(row)
        return ['']*len(row)
    st.dataframe(show.style.apply(estilo, axis=1),
                 width="stretch", hide_index=True, height=min(500, 45*(len(show)+1)))

    # Cards
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("⏰ Você deve", fmt_brl_milhao(total["Pgto em Atraso (você deve)"]),
                        delta=f"{int(total['Qtd Pgto'])} faturas", delta_color="inverse")
    with c2: st.metric("💰 Cliente deve", fmt_brl_milhao(total["Inadimplência (cliente deve)"]),
                        delta=f"{int(total['Qtd Rec'])} faturas", delta_color="inverse")
    with c3:
        liq = total["Inadimplência (cliente deve)"] - total["Pgto em Atraso (você deve)"]
        st.metric("⚖️ Líquido", fmt_brl_milhao(liq),
                   delta="Se cobrar tudo, sobra esse valor",
                   delta_color="normal" if liq>=0 else "inverse")

st.markdown("---")

# ========== PAGAMENTOS EM ATRASO ==========
st.markdown("## ⏰ Pagamentos em Atraso (o que VOCÊ deve)")

if pag_atr.empty:
    st.success("🎉 Nenhum pagamento em atraso!")
else:
    pag_sorted = pag_atr.sort_values("Dias de Atraso", ascending=False).reset_index(drop=True)

    # Tabela com checkbox via st.data_editor (permite marcar pra ignorar)
    st.caption("💡 Marque a caixa na coluna **Ignorar** pra ocultar esse item das próximas visualizações.")

    # Prepara tabela interativa
    tab_edit = pag_sorted[[c for c in ["Emp. Prop.","FORNECEDOR","DESCRIÇÃO",
                                          "Descrição Plano de Contas","TIPO","VALOR",
                                          "VENCIMENTO","Dias de Atraso","Situação (Normalizada)"]
                            if c in pag_sorted.columns]].copy()
    tab_edit["Ignorar"] = False

    # Formata visualmente
    tab_display = tab_edit.copy()
    if "VENCIMENTO" in tab_display: tab_display["VENCIMENTO"] = tab_display["VENCIMENTO"].dt.strftime("%d/%m/%Y")
    if "VALOR" in tab_display: tab_display["VALOR"] = tab_display["VALOR"].apply(fmt_brl)

    edited = st.data_editor(
        tab_display,
        width="stretch", hide_index=True, height=500,
        column_config={
            "Ignorar": st.column_config.CheckboxColumn(
                "🙈 Ignorar",
                help="Marque pra remover esse item das visualizações (marca como perdido/a renegociar)",
                default=False, width="small",
            ),
        },
        disabled=[c for c in tab_display.columns if c != "Ignorar"],
        key="pag_atr_editor",
    )

    # Processar ignorados
    if edited is not None:
        novos_ign = []
        for i, row in edited.iterrows():
            if row.get("Ignorar", False):
                k = make_key_pag(pag_sorted.iloc[i])
                if k not in ignorados["pagamentos"]:
                    novos_ign.append(k)
        if novos_ign:
            ignorados["pagamentos"].extend(novos_ign)
            save_ignorados(ignorados)
            st.success(f"✅ {len(novos_ign)} pagamento(s) marcado(s) como ignorados. Recarregue (F5) pra atualizar.")

    st.caption(f"💰 **Total filtrado**: {fmt_brl(pag_atr['VALOR'].sum())} · **{len(pag_atr)} faturas** · Maior atraso: {int(pag_atr['Dias de Atraso'].max())} dias")

st.markdown("---")

# ========== RECEBÍVEIS INADIMPLENTES ==========
st.markdown("## 📉 Recebíveis Inadimplentes (o que CLIENTE deve)")
st.caption("🙈 Use a coluna **Ignorar** pra remover recebíveis que você considera perdidos (não vai receber).")

if rec_inad.empty:
    st.success("🎉 Nenhuma inadimplência!")
else:
    rec_sorted = rec_inad.sort_values(["Dias de Atraso","Valor Total"], ascending=[False, False]).reset_index(drop=True)

    tab_edit_r = rec_sorted[[c for c in ["Emp. Prop.","Empresa","OS","NF","Valor Total",
                                            "Vencimento","Dias de Atraso","Situação (Normalizada)"]
                              if c in rec_sorted.columns]].copy()
    tab_edit_r["Ignorar"] = False

    tab_display_r = tab_edit_r.copy()
    if "Vencimento" in tab_display_r: tab_display_r["Vencimento"] = tab_display_r["Vencimento"].dt.strftime("%d/%m/%Y")
    if "Valor Total" in tab_display_r: tab_display_r["Valor Total"] = tab_display_r["Valor Total"].apply(fmt_brl)

    edited_r = st.data_editor(
        tab_display_r,
        width="stretch", hide_index=True, height=500,
        column_config={
            "Ignorar": st.column_config.CheckboxColumn(
                "🙈 Ignorar",
                help="Marque pra considerar este recebível como perdido (não entra nas projeções)",
                default=False, width="small",
            ),
        },
        disabled=[c for c in tab_display_r.columns if c != "Ignorar"],
        key="rec_inad_editor",
    )

    if edited_r is not None:
        novos_ign = []
        for i, row in edited_r.iterrows():
            if row.get("Ignorar", False):
                k = make_key_rec(rec_sorted.iloc[i])
                if k not in ignorados["recebimentos"]:
                    novos_ign.append(k)
        if novos_ign:
            ignorados["recebimentos"].extend(novos_ign)
            save_ignorados(ignorados)
            st.success(f"✅ {len(novos_ign)} recebível(is) marcado(s) como ignorados. Recarregue (F5) pra atualizar.")

    st.caption(f"💰 **Total filtrado**: {fmt_brl(rec_inad['Valor Total'].sum())} · **{len(rec_inad)} faturas** · Maior atraso: {int(rec_inad['Dias de Atraso'].max())} dias")

st.markdown("---")

# ========== GERENCIAR IGNORADOS ==========
with st.expander(f"🙈 Gerenciar itens ignorados ({ign_count})"):
    if ign_count == 0:
        st.info("Nenhum item ignorado ainda.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Pagamentos ignorados ({len(ignorados['pagamentos'])})**")
            if ignorados["pagamentos"]:
                for i, k in enumerate(ignorados["pagamentos"]):
                    parts = k.split("|")
                    label = f"{parts[0]} · {parts[1]} · {parts[3]}"
                    if st.button(f"🔄 Restaurar: {label[:60]}", key=f"rest_p_{i}"):
                        ignorados["pagamentos"].remove(k)
                        save_ignorados(ignorados)
                        st.rerun()
        with c2:
            st.markdown(f"**Recebimentos ignorados ({len(ignorados['recebimentos'])})**")
            if ignorados["recebimentos"]:
                for i, k in enumerate(ignorados["recebimentos"]):
                    parts = k.split("|")
                    label = f"{parts[0]} · {parts[1]} · {parts[4]}"
                    if st.button(f"🔄 Restaurar: {label[:60]}", key=f"rest_r_{i}"):
                        ignorados["recebimentos"].remove(k)
                        save_ignorados(ignorados)
                        st.rerun()

        if st.button("🗑️ Limpar TODOS os ignorados", type="secondary"):
            ignorados["pagamentos"] = []
            ignorados["recebimentos"] = []
            save_ignorados(ignorados)
            st.rerun()

st.caption("💾 Os itens ignorados ficam salvos em `_ignorados.json` na pasta do dashboard. Persistem entre sessões.")
