# -*- coding: utf-8 -*-
"""
Configuração central do Dashboard Financeiro GFlex.
"""
import os
from datetime import date, timedelta, datetime

# ============ CAMINHOS ============
ONEDRIVE_DIR = r"C:\Users\Gustavo Gontijo\OneDrive\GFlex Financeiro"
SERVIDOR_DIR = r"\\192.168.10.200\consórcios\PROCESSO\DESPESAS\Novo Processo\GESTÃO INTEGRADA"

ARQ_PAGAMENTOS   = "União de Pagamentos.xlsx"
ARQ_RECEBIMENTOS = "União de Recebimentos.xlsx"

# ============ CORES ============
CORES = {
    "GFlex":          {"primaria": "#1a1a2e", "secundaria": "#EC8500"},
    "Flex Energy":    {"primaria": "#EC8500", "secundaria": "#F7C42D"},
    "GF2":            {"primaria": "#004A9D", "secundaria": "#ffffff"},
    "Flex Tendas":    {"primaria": "#3f469c", "secundaria": "#ffffff"},
    "Flex Locações":  {"primaria": "#3f469c", "secundaria": "#ffffff"},
    "Flex Medições":  {"primaria": "#517e45", "secundaria": "#ffffff"},
    "MEC":            {"primaria": "#151515", "secundaria": "#555555"},
    "Flex Solar":     {"primaria": "#FF8728", "secundaria": "#f1f3f4"},
    "Flex Engenharia":{"primaria": "#2C3E50", "secundaria": "#ffffff"},
    "Flex Assistance":{"primaria": "#8E44AD", "secundaria": "#ffffff"},
    "Geradora GTJ":   {"primaria": "#D35400", "secundaria": "#ffffff"},
    "MIP":            {"primaria": "#16A085", "secundaria": "#ffffff"},
    "Smart & Easy Energy":        {"primaria": "#F39C12", "secundaria": "#ffffff"},
    "Flex Energia Sustentável":   {"primaria": "#27AE60", "secundaria": "#ffffff"},
}

COR_POSITIVO = "#27AE60"
COR_NEGATIVO = "#E74C3C"
COR_NEUTRO   = "#F7C42D"
COR_PRIMARIA = "#1a1a2e"
COR_DESTAQUE = "#EC8500"

# ============ GRUPOS ============
OLDCO_EMPRESAS = ["GF2", "MEC", "MEC Estruturas", "Flex Solar", "Flex Engenharia"]
NEWCO_EMPRESAS = ["Flex Energy", "Flex Locações", "Flex Tendas", "Flex Medições",
                  "MIP", "Smart & Easy Energy", "Flex Energia Sustentável"]
INFRA_EMPRESAS = ["Geradora GTJ", "Geradora Gontijo", "Flex Assistance"]

GRUPOS = {
    "OLD CO": OLDCO_EMPRESAS,
    "NEW CO": NEWCO_EMPRESAS,
    "INFRA":  INFRA_EMPRESAS,
}

# Ordem de exibição (OLD CO primeiro por preferência do Gustavo)
ORDEM_EMPRESAS = OLDCO_EMPRESAS + INFRA_EMPRESAS + NEWCO_EMPRESAS

# ============ SITUAÇÕES ============
SIT_PAGO       = "Pago"
SIT_CANCELADO  = "Cancelado"
SIT_ABERTAS    = ["Em Aberto", "Atrasado", "Inadimplente", "Protestado",
                  "Garantia", "Permuta", "Provisão"]

# ============ FORMATAÇÃO ============
def fmt_brl(v):
    """Formata valor em BRL. Aceita None/NaN."""
    try:
        import math
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "R$ 0,00"
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def fmt_brl_milhao(v):
    """Formata em milhões (R$ 1,2 Mi) ou milhares (R$ 125 Mil)."""
    try:
        import math
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "R$ 0"
        av = abs(v)
        if av >= 1_000_000:
            s = f"R$ {v/1_000_000:.2f} Mi"
        elif av >= 1_000:
            s = f"R$ {v/1_000:.1f} Mil"
        else:
            s = f"R$ {v:.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0"

def fmt_int(v):
    try:
        return f"{int(v):,}".replace(",", ".")
    except Exception:
        return "0"

def fmt_pct(v):
    try:
        return f"{v*100:.1f}%".replace(".", ",")
    except Exception:
        return "0,0%"

# ============ DATAS ============
MESES_PT = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
            7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
MESES_PT_FULL = {1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",
                 5:"Maio",6:"Junho",7:"Julho",8:"Agosto",
                 9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}

def inicio_semana(d=None):
    d = d or date.today()
    return d - timedelta(days=d.weekday())  # segunda

def fim_semana(d=None):
    return inicio_semana(d) + timedelta(days=6)

def inicio_mes(d=None):
    d = d or date.today()
    return d.replace(day=1)

def fim_mes(d=None):
    import calendar
    d = d or date.today()
    _, n = calendar.monthrange(d.year, d.month)
    return d.replace(day=n)

def proximo_mes_inicio(d=None):
    d = d or date.today()
    if d.month == 12:
        return date(d.year+1, 1, 1)
    return date(d.year, d.month+1, 1)

def proximo_mes_fim(d=None):
    import calendar
    ini = proximo_mes_inicio(d)
    _, n = calendar.monthrange(ini.year, ini.month)
    return date(ini.year, ini.month, n)

# ============ CACHE ============
CACHE_TTL_SECONDS = 300  # 5 min — arquivo é regenerado a cada 30min pelo Task Scheduler

# ============ GLOSSÁRIO DE KPIs ============
# Cada entrada: (label curto, fórmula em português, campos usados)
KPI_DEFS = {
    # Painel do Dia
    "Pgto Vencendo Hoje":
        ("Soma dos valores cujo VENCIMENTO = hoje E situação ≠ Pago/Cancelado",
         "VALOR, VENCIMENTO, Situação (Normalizada)"),
    "Pago Ontem":
        ("Soma de pagamentos com DATA DE PGTO. = ontem E situação = Pago",
         "VALOR, DATA DE PGTO., Situação (Normalizada)"),
    "Pgto Vencendo Esta Semana":
        ("Soma de pagamentos cujo VENCIMENTO está entre segunda e domingo desta semana, E não está pago/cancelado",
         "VALOR, VENCIMENTO, Situação (Normalizada)"),
    "Total Pgto em Atraso":
        ("Soma de pagamentos com VENCIMENTO < hoje, não pagos/cancelados (flag Atrasado? = S)",
         "VALOR, VENCIMENTO, Situação (Normalizada), Atrasado?"),
    "Rec Previsto Hoje":
        ("Soma de recebíveis com Vencimento = hoje E não recebidos",
         "Valor Total, Vencimento, Situação (Normalizada)"),
    "Recebido Ontem":
        ("Soma de recebimentos com Data PGTO. = ontem E situação = Pago",
         "Valor Total, Data PGTO., Situação (Normalizada)"),
    "Inadimplência":
        ("Soma de recebíveis vencidos e não pagos (flag Atrasado? = S)",
         "Valor Total, Vencimento, Situação (Normalizada), Atrasado?"),
    # Totais
    "Total Pago":
        ("Soma de TODOS os pagamentos com situação = Pago (independente da data)",
         "VALOR, Situação (Normalizada)"),
    "Total a Pagar":
        ("Soma de pagamentos não pagos/cancelados (em aberto)",
         "VALOR, Situação (Normalizada)"),
    "Total Recebido":
        ("Soma de TODOS os recebimentos com situação = Pago",
         "Valor Total, Situação (Normalizada)"),
    "Total a Receber":
        ("Soma de recebimentos não pagos/cancelados",
         "Valor Total, Situação (Normalizada)"),
    "Saldo":
        ("Total Recebido − Total Pago. Positivo = entrou mais do que saiu no período filtrado",
         "VALOR + Valor Total + Situação"),
    # Projeção
    "Saída Prevista":
        ("Soma de pagamentos com VENCIMENTO dentro do período escolhido E ainda não pagos",
         "VALOR, VENCIMENTO, Situação (Normalizada)"),
    "Entrada Prevista":
        ("Soma de recebíveis com Vencimento dentro do período escolhido E ainda não recebidos",
         "Valor Total, Vencimento, Situação (Normalizada)"),
    "Saldo Projetado":
        ("Entrada Prevista − Saída Prevista. Indica se o caixa do período será positivo ou negativo",
         ""),
    # DRE
    "Receita Total":
        ("Soma de TODOS os valores em Recebimentos (independente da situação) — base contábil",
         "Valor Total"),
    "Despesa Total":
        ("Soma de TODOS os valores em Pagamentos — base contábil",
         "VALOR"),
    "Resultado Líquido":
        ("Receita Total − Despesa Total (para DRE simplificado)",
         ""),
}

# ============ SITUAÇÕES VÁLIDAS ============
SITUACOES_VALIDAS = {
    "Pago", "Em Aberto", "Cancelado", "Atrasado", "Inadimplente",
    "Protestado", "Garantia", "Permuta", "Provisão"
}

# ============ PRESETS DE PERÍODO ============
def get_periodo_preset(nome):
    """Retorna (ini, fim, label) para um preset rápido."""
    import calendar
    hoje = date.today()
    if nome == "Hoje":
        return hoje, hoje, f"Hoje ({hoje.strftime('%d/%m')})"
    if nome == "Ontem":
        o = hoje - timedelta(days=1)
        return o, o, f"Ontem ({o.strftime('%d/%m')})"
    if nome == "Esta Semana":
        ini = hoje - timedelta(days=hoje.weekday())
        fim = ini + timedelta(days=6)
        return ini, fim, f"{ini.strftime('%d/%m')} → {fim.strftime('%d/%m')}"
    if nome == "Próxima Semana":
        ini = hoje - timedelta(days=hoje.weekday()) + timedelta(days=7)
        fim = ini + timedelta(days=6)
        return ini, fim, f"{ini.strftime('%d/%m')} → {fim.strftime('%d/%m')}"
    if nome == "Este Mês":
        ini = hoje.replace(day=1)
        _, n = calendar.monthrange(hoje.year, hoje.month)
        fim = hoje.replace(day=n)
        return ini, fim, MESES_PT_FULL[hoje.month] + "/" + str(hoje.year)
    if nome == "Próximo Mês":
        if hoje.month == 12:
            ini = date(hoje.year+1, 1, 1)
        else:
            ini = date(hoje.year, hoje.month+1, 1)
        _, n = calendar.monthrange(ini.year, ini.month)
        fim = date(ini.year, ini.month, n)
        return ini, fim, MESES_PT_FULL[ini.month] + "/" + str(ini.year)
    if nome == "Próximos 30 dias":
        return hoje, hoje + timedelta(days=30), f"Hoje + 30 dias"
    if nome == "Últimos 30 dias":
        return hoje - timedelta(days=30), hoje, f"Últimos 30 dias"
    if nome == "Este Ano":
        return date(hoje.year,1,1), date(hoje.year,12,31), str(hoje.year)
    return None, None, nome
