# -*- coding: utf-8 -*-
"""Glossário — definição e fórmula de cada KPI."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
from config import KPI_DEFS, SITUACOES_VALIDAS
from styles import inject_css

st.set_page_config(page_title="Glossário", page_icon="📖", layout="wide")
inject_css()

st.markdown("""
<div class="hero" style="background:linear-gradient(135deg,#1a1a2e 0%,#444 100%)">
<h1>📖 Glossário — Como Interpretar Cada KPI</h1>
<p>Fórmula exata de cada métrica e quais campos ela usa das planilhas</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
### Fundamentos — Datas que Importam

| Data | Significado |
|---|---|
| **VENCIMENTO** (pagamentos) | Data em que a empresa DEVERIA pagar. Usada pra projetar saída futura. |
| **DATA DE PGTO.** (pagamentos) | Data real em que o dinheiro saiu do banco. Usada pra fluxo realizado. |
| **Vencimento** (recebíveis) | Data em que o cliente DEVERIA pagar a fatura. Usada pra projetar entrada futura. |
| **Data PGTO.** (recebíveis) | Data real em que o cliente pagou. Usada pra fluxo realizado. |
| **Emissão** (recebíveis) | Data da nota fiscal. |

### Situações Válidas

Uma fatura pode estar em uma dessas situações (normalizadas):
""")

for s in sorted(SITUACOES_VALIDAS):
    st.markdown(f"- **{s}**")

st.markdown("""

### Regras de Contabilização

- **"Em aberto"** = qualquer situação que NÃO seja `Pago` NEM `Cancelado`. Inclui: Em Aberto, Atrasado, Inadimplente, Protestado, Garantia, Permuta, Provisão.
- **"Atrasado"** (coluna flag) = VENCIMENTO < hoje E situação ≠ Pago/Cancelado.
- **Fluxo Realizado** = agrupa por data REAL (DATA DE PGTO. / Data PGTO.). Só conta o que já aconteceu.
- **Projeção / Fluxo Futuro** = agrupa por VENCIMENTO. Só conta o que ainda não aconteceu.

---

## KPIs — Definição e Fórmula
""")

# Lista de KPIs com definição
for kpi, (formula, campos) in KPI_DEFS.items():
    with st.expander(f"📌 **{kpi}**"):
        st.markdown(f"**Fórmula:** {formula}")
        if campos:
            st.caption(f"Campos usados: `{campos}`")

st.markdown("---")

st.markdown("""
## 🧭 Guia de Navegação

| Aba | Quando usar |
|---|---|
| **Painel do Dia** | Início do dia — o que vence hoje, o que pagou/recebeu ontem, atrasos |
| **OLD CO** | Análise contábil do grupo OLD CO — DRE separado por exigência contábil |
| **NEW CO** | Análise contábil do grupo NEW CO |
| **Projeção** | Libero pagamentos ou atraso? Projeção próxima semana/mês |
| **Fluxo de Caixa** | Visão consolidada de entradas vs saídas, realizado + futuro |
| **DRE Simplificado** | Receita − Despesa por plano de contas |
| **Conciliação** | Saldo diário por empresa — bater com extrato bancário |
| **Glossário** | Dúvida sobre algum KPI? Consulta aqui |
| **Auditoria** | Ver erros de preenchimento nas planilhas-fonte |

## 💡 Dicas para Caixa Curto

1. **Comece pelo Painel do Dia** — veja o que VENCE hoje e quanto já pagou/recebeu
2. **Vá pra Projeção** — "o que vou pagar/receber esta semana e próxima?"
3. **Filtre por empresa** na sidebar — cada CNPJ tem caixa separado
4. **Use o preset "Esta Semana"** — foco operacional
5. **Troque a base de data** na sidebar pra ver "por vencimento" (projeção) vs "por data pgto" (realizado)

## ⚙️ Fonte de Dados

- Consolidado automaticamente a cada **30 minutos** por script Python no PC do Gustavo
- Origem: **16 planilhas Excel** no servidor `192.168.10.200`
- Saída: `União de Pagamentos.xlsx` + `União de Recebimentos.xlsx` (no OneDrive)
- Dashboard lê do OneDrive pessoal — sem Gateway, sem dependência de VPN pra consulta
- **Cache de 5 min** neste dashboard (botão "Recarregar dados agora" na sidebar força atualização)
""")
