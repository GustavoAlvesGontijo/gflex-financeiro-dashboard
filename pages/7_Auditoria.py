# -*- coding: utf-8 -*-
"""Auditoria — detecta erros de preenchimento nas planilhas-fonte."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
import pandas as pd

from config import fmt_brl, SITUACOES_VALIDAS
from data_loader import (
    load_pagamentos, load_recebimentos,
    auditar_pagamentos, auditar_recebimentos,
)
from styles import inject_css, kpi_card

st.set_page_config(page_title="Auditoria", page_icon="🔍", layout="wide")
inject_css()

st.markdown("""
<div class="hero" style="background:linear-gradient(135deg,#E74C3C 0%,#1a1a2e 100%)">
<h1>🔍 Auditoria das Planilhas</h1>
<p>Detecta erros de preenchimento nas planilhas-fonte. Corrigir na fonte → melhor análise.</p>
</div>
""", unsafe_allow_html=True)

# Carrega SEM filtros — auditoria precisa ver tudo
df_pag = load_pagamentos()
df_rec = load_recebimentos()

# ========== RESUMO ==========
aud_p = auditar_pagamentos(df_pag)
aud_r = auditar_recebimentos(df_rec)

total_p = sum(len(v) for v in aud_p.values())
total_r = sum(len(v) for v in aud_r.values())

c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Total Pagamentos", f"{len(df_pag):,}".replace(",","."))
with c2: kpi_card("Erros em Pagamentos", f"{total_p:,}".replace(",","."),
                  color="neg" if total_p>0 else "pos",
                  sub=f"{total_p/max(len(df_pag),1)*100:.1f}% dos registros")
with c3: kpi_card("Total Recebimentos", f"{len(df_rec):,}".replace(",","."))
with c4: kpi_card("Erros em Recebimentos", f"{total_r:,}".replace(",","."),
                  color="neg" if total_r>0 else "pos",
                  sub=f"{total_r/max(len(df_rec),1)*100:.1f}% dos registros")

st.markdown("---")

# ========== PAGAMENTOS ==========
st.markdown("## 💸 Erros em Pagamentos")

if total_p == 0:
    st.success("✅ Nenhum erro de preenchimento em Pagamentos!")
else:
    # Resumo tabelado
    resumo_p = []
    for k, v in aud_p.items():
        if len(v) > 0:
            resumo_p.append({"Tipo de Erro": k, "Quantidade": len(v),
                              "% do Total": f"{len(v)/len(df_pag)*100:.2f}%"})
    if resumo_p:
        st.dataframe(pd.DataFrame(resumo_p), width='stretch', hide_index=True)

    for k, v in aud_p.items():
        if len(v) == 0:
            continue
        with st.expander(f"🔎 {k} — {len(v):,} registros".replace(",",".")):
            cols = ["Emp. Prop.","FORNECEDOR","DESCRIÇÃO","VALOR","VENCIMENTO",
                    "Situação (Normalizada)","Arquivo Origem"]
            cols = [c for c in cols if c in v.columns]
            show = v[cols].head(100).copy()
            if "VENCIMENTO" in show.columns:
                show["VENCIMENTO"] = pd.to_datetime(show["VENCIMENTO"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("—")
            if "VALOR" in show.columns:
                show["VALOR"] = show["VALOR"].apply(lambda x: fmt_brl(x) if pd.notna(x) else "—")
            st.dataframe(show, width='stretch', hide_index=True, height=350)
            if len(v) > 100:
                st.caption(f"Mostrando 100 de {len(v)} registros. Exporte pra ver todos.")

st.markdown("---")

# ========== RECEBIMENTOS ==========
st.markdown("## 💵 Erros em Recebimentos")

if total_r == 0:
    st.success("✅ Nenhum erro de preenchimento em Recebimentos!")
else:
    resumo_r = []
    for k, v in aud_r.items():
        if len(v) > 0:
            resumo_r.append({"Tipo de Erro": k, "Quantidade": len(v),
                              "% do Total": f"{len(v)/len(df_rec)*100:.2f}%"})
    if resumo_r:
        st.dataframe(pd.DataFrame(resumo_r), width='stretch', hide_index=True)

    for k, v in aud_r.items():
        if len(v) == 0:
            continue
        with st.expander(f"🔎 {k} — {len(v):,} registros".replace(",",".")):
            cols = ["Emp. Prop.","Empresa","OS","NF","Valor Total","Vencimento",
                    "Situação (Normalizada)","Arquivo Origem"]
            cols = [c for c in cols if c in v.columns]
            show = v[cols].head(100).copy()
            if "Vencimento" in show.columns:
                show["Vencimento"] = pd.to_datetime(show["Vencimento"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("—")
            if "Valor Total" in show.columns:
                show["Valor Total"] = show["Valor Total"].apply(lambda x: fmt_brl(x) if pd.notna(x) else "—")
            st.dataframe(show, width='stretch', hide_index=True, height=350)
            if len(v) > 100:
                st.caption(f"Mostrando 100 de {len(v)} registros.")

st.markdown("---")

st.markdown("""
### 📝 Como Corrigir

Os erros acima vêm das **planilhas-fonte** no servidor `192.168.10.200`. Para corrigir:

1. **Abrir a planilha original** indicada na coluna "Arquivo Origem"
2. **Localizar a linha** usando FORNECEDOR + VENCIMENTO (pagamentos) ou Empresa + Vencimento (recebimentos)
3. **Preencher o campo vazio** ou corrigir o valor inválido
4. **Aguardar 30 minutos** — o script consolida automaticamente
5. **Voltar aqui** e verificar se o erro sumiu

### Situações Válidas (para referência)
""")
st.write(sorted(SITUACOES_VALIDAS))
