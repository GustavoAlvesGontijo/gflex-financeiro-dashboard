# -*- coding: utf-8 -*-
"""
Carrega xlsx consolidados + expõe funções de filtro e agregação.
Foco: decisão diária/semanal, tabela por empresa.
"""
import os
import io
from datetime import date, timedelta, datetime
import pandas as pd
import streamlit as st
from config import (
    ONEDRIVE_DIR, ARQ_PAGAMENTOS, ARQ_RECEBIMENTOS,
    SIT_PAGO, SIT_CANCELADO, GRUPOS, CACHE_TTL_SECONDS,
    MESES_PT,
)

# ============ HELPER: resolve fonte (URL remota via secrets OU caminho local) ============
def _resolve_source(secret_key: str, nome_arquivo: str):
    """
    Tenta URL dos secrets primeiro (pra deploy Cloud), fallback pro caminho local (PC do Gustavo).
    Retorna: ('url', str) ou ('file', str) ou (None, None)
    """
    # 1) Via secrets (Streamlit Cloud)
    try:
        url = st.secrets["data"][secret_key]
        if url:
            return ("url", url)
    except Exception:
        pass
    # 2) Via variável de ambiente
    env_val = os.getenv(secret_key)
    if env_val:
        return ("url", env_val)
    # 3) Fallback pra arquivo local
    fp = os.path.join(ONEDRIVE_DIR, nome_arquivo)
    if os.path.exists(fp):
        return ("file", fp)
    return (None, None)

def _read_excel(src, sheet_name):
    """Lê Excel de URL ou caminho local."""
    tipo, valor = src
    if tipo == "url":
        import requests
        r = requests.get(valor, timeout=30)
        r.raise_for_status()
        return pd.read_excel(io.BytesIO(r.content), sheet_name=sheet_name)
    elif tipo == "file":
        return pd.read_excel(valor, sheet_name=sheet_name)
    return pd.DataFrame()


# ============ LOADERS ============
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Carregando União de Pagamentos...")
def load_pagamentos() -> pd.DataFrame:
    src = _resolve_source("URL_PAGAMENTOS", ARQ_PAGAMENTOS)
    if src[0] is None:
        st.error(f"❌ Fonte de dados (Pagamentos) não configurada. Veja README.md")
        return pd.DataFrame()
    df = _read_excel(src, "Pagamentos")
    for c in ["VENCIMENTO", "PGTO", "DATA DE PGTO."]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    if "VALOR" in df.columns:
        df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce").fillna(0)
    for c in ["Dias de Atraso", "Ano Vencimento", "Mês Vencimento", "Ano Pagamento", "Mês Pagamento"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    if "Grupo" not in df.columns or df["Grupo"].isna().all():
        df["Grupo"] = df["Emp. Prop."].apply(classificar_grupo)
    # Força colunas mistas a string (pyarrow safety)
    for c in ["N. DA NOTA", "COD", "TAG", "CONTA", "DEPARTAMENTO", "TIPO", "Pgto. = Venc."]:
        if c in df.columns:
            df[c] = df[c].apply(_as_str)
    # Normaliza TIPO (Orçamento/orçamento → Orçamento, vazio → "Não classificado")
    if "TIPO" in df.columns:
        df["TIPO"] = df["TIPO"].apply(lambda v: str(v).strip().capitalize() if str(v).strip() else "Não classificado")
        df["TIPO"] = df["TIPO"].replace({"Orçamento": "Orçamento", "Orcamento": "Orçamento"})
    return df

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Carregando União de Recebimentos...")
def load_recebimentos() -> pd.DataFrame:
    src = _resolve_source("URL_RECEBIMENTOS", ARQ_RECEBIMENTOS)
    if src[0] is None:
        st.error(f"❌ Fonte de dados (Recebimentos) não configurada. Veja README.md")
        return pd.DataFrame()
    df = _read_excel(src, "Recebimentos")
    for c in ["Emissão", "Vencimento", "Previsão PGTO.", "Data PGTO."]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in ["Valor Total", "Valor da NF"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    for c in ["Dias de Atraso", "Ano Vencimento", "Mês Vencimento"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    if "Grupo" not in df.columns or df["Grupo"].isna().all():
        df["Grupo"] = df["Emp. Prop."].apply(classificar_grupo)
    for c in ["OS", "NF", "UC", "COD", "Ref.", "Proposta", "Contrato", "Num. Parcela", "TIPO DE NF"]:
        if c in df.columns:
            df[c] = df[c].apply(_as_str)
    return df

def _as_str(v):
    if pd.isna(v): return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)

def classificar_grupo(emp):
    s = str(emp or "").strip()
    for g, lst in GRUPOS.items():
        for e in lst:
            if e.lower() in s.lower() or s.lower() in e.lower():
                return g
    return "OUTROS"


# ============ FILTROS UNIVERSAIS ============
def filtrar(df: pd.DataFrame, coluna_data: str) -> pd.DataFrame:
    """
    Aplica filtros do sidebar a QUALQUER DataFrame:
    - empresas (multi)
    - grupos (multi)
    - data_ini, data_fim aplicados em `coluna_data`
    """
    if df.empty: return df

    empresas = st.session_state.get("f_empresas", [])
    grupos   = st.session_state.get("f_grupos", [])
    data_ini = st.session_state.get("f_data_ini", None)
    data_fim = st.session_state.get("f_data_fim", None)

    if empresas:
        df = df[df["Emp. Prop."].isin(empresas)]
    if grupos:
        df = df[df["Grupo"].isin(grupos)]
    if data_ini and coluna_data in df.columns:
        df = df[df[coluna_data] >= pd.Timestamp(data_ini)]
    if data_fim and coluna_data in df.columns:
        df = df[df[coluna_data] <= pd.Timestamp(data_fim)]
    return df


# ============ TESTES DE SITUAÇÃO ============
def eh_aberto(serie: pd.Series) -> pd.Series:
    return (~serie.isin([SIT_PAGO, SIT_CANCELADO])) & serie.notna() & (serie.astype(str).str.strip() != "")

def eh_pago(serie: pd.Series) -> pd.Series:
    return serie == SIT_PAGO

# Aliases retrocompatíveis
_eh_aberto = eh_aberto
_eh_pago = eh_pago


# ============ RESUMO POR EMPRESA (TABELA PRINCIPAL) ============
def resumo_por_empresa(df_pag: pd.DataFrame, df_rec: pd.DataFrame,
                         base_pag: str = "VENCIMENTO",
                         base_rec: str = "Vencimento") -> pd.DataFrame:
    """
    Retorna tabela UMA LINHA POR EMPRESA com:
    Empresa, Grupo, Recebido, A Receber, Inadimplência,
    Pago, A Pagar, Em Atraso, Saldo (Recebido−Pago), Saldo Projetado (A Receber−A Pagar).

    Os filtros universais (empresa, grupo, período) já devem ter sido aplicados.
    """
    emp_set = set()
    if not df_pag.empty: emp_set.update(df_pag["Emp. Prop."].dropna().unique())
    if not df_rec.empty: emp_set.update(df_rec["Emp. Prop."].dropna().unique())

    rows = []
    for emp in sorted(emp_set):
        grp = classificar_grupo(emp)
        dp = df_pag[df_pag["Emp. Prop."] == emp] if not df_pag.empty else pd.DataFrame()
        dr = df_rec[df_rec["Emp. Prop."] == emp] if not df_rec.empty else pd.DataFrame()

        pago = float(dp.loc[eh_pago(dp["Situação (Normalizada)"]), "VALOR"].sum()) if not dp.empty else 0
        a_pagar = float(dp.loc[eh_aberto(dp["Situação (Normalizada)"]), "VALOR"].sum()) if not dp.empty else 0
        em_atr = 0
        qtd_atr_p = 0
        if not dp.empty and "Atrasado?" in dp.columns:
            m = eh_aberto(dp["Situação (Normalizada)"]) & (dp["Atrasado?"] == "S")
            em_atr = float(dp.loc[m, "VALOR"].sum())
            qtd_atr_p = int(m.sum())

        rec = float(dr.loc[eh_pago(dr["Situação (Normalizada)"]), "Valor Total"].sum()) if not dr.empty else 0
        a_rec = float(dr.loc[eh_aberto(dr["Situação (Normalizada)"]), "Valor Total"].sum()) if not dr.empty else 0
        inad = 0
        qtd_inad = 0
        if not dr.empty and "Atrasado?" in dr.columns:
            m = eh_aberto(dr["Situação (Normalizada)"]) & (dr["Atrasado?"] == "S")
            inad = float(dr.loc[m, "Valor Total"].sum())
            qtd_inad = int(m.sum())

        rows.append({
            "Empresa": emp,
            "Grupo": grp,
            "Recebido": rec,
            "A Receber": a_rec,
            "Inadimplência": inad,
            "Qtd Inad": qtd_inad,
            "Pago": pago,
            "A Pagar": a_pagar,
            "Em Atraso": em_atr,
            "Qtd Atraso": qtd_atr_p,
            "Saldo Realizado": rec - pago,
            "Saldo Projetado": a_rec - a_pagar,
        })
    df = pd.DataFrame(rows)
    if df.empty: return df

    # Total consolidado no final
    total = {"Empresa": "TOTAL", "Grupo": "—"}
    for c in ["Recebido","A Receber","Inadimplência","Pago","A Pagar","Em Atraso",
              "Saldo Realizado","Saldo Projetado"]:
        total[c] = df[c].sum()
    total["Qtd Inad"] = df["Qtd Inad"].sum()
    total["Qtd Atraso"] = df["Qtd Atraso"].sum()
    df = pd.concat([df, pd.DataFrame([total])], ignore_index=True)
    return df


# ============ QUEBRA DIÁRIA/SEMANAL/MENSAL POR EMPRESA ============
def fluxo_empresa_periodo(df_pag: pd.DataFrame, df_rec: pd.DataFrame,
                           granularidade: str = "Mês") -> pd.DataFrame:
    """
    Retorna DataFrame wide: rows = empresa + "TOTAL", colunas = períodos,
    valores = saldo (Entrada - Saída) no período.
    Usa DATA DE PGTO./Data PGTO. (realizado).
    """
    def _bucket(series):
        if granularidade == "Semana":
            return series.dt.to_period("W-SUN").astype(str)
        if granularidade == "Mês":
            return series.dt.to_period("M").astype(str)
        return series.dt.strftime("%Y-%m-%d")

    # Entradas
    dfe = df_rec[eh_pago(df_rec["Situação (Normalizada)"])].dropna(subset=["Data PGTO."])
    dfe = dfe.assign(_p=_bucket(dfe["Data PGTO."]))
    ent = dfe.groupby(["Emp. Prop.", "_p"])["Valor Total"].sum().unstack(fill_value=0)

    # Saídas
    dfs = df_pag[eh_pago(df_pag["Situação (Normalizada)"])].dropna(subset=["DATA DE PGTO."])
    dfs = dfs.assign(_p=_bucket(dfs["DATA DE PGTO."]))
    sai = dfs.groupby(["Emp. Prop.", "_p"])["VALOR"].sum().unstack(fill_value=0)

    # Alinha colunas
    all_cols = sorted(set(list(ent.columns) + list(sai.columns)))
    if not all_cols: return pd.DataFrame()
    ent = ent.reindex(columns=all_cols, fill_value=0)
    sai = sai.reindex(columns=all_cols, fill_value=0)

    all_emp = sorted(set(list(ent.index) + list(sai.index)))
    ent = ent.reindex(index=all_emp, fill_value=0)
    sai = sai.reindex(index=all_emp, fill_value=0)

    saldo = ent - sai
    saldo.loc["TOTAL"] = saldo.sum()
    saldo = saldo.reset_index().rename(columns={"Emp. Prop.": "Empresa"})
    return saldo


def entrada_saida_periodo(df_pag: pd.DataFrame, df_rec: pd.DataFrame,
                           granularidade: str = "Mês") -> pd.DataFrame:
    """
    Retorna DataFrame long: Período, Entrada, Saída, Saldo, Acumulado.
    """
    def _bucket(series):
        if granularidade == "Semana":
            return series.dt.to_period("W-SUN").astype(str)
        if granularidade == "Mês":
            return series.dt.to_period("M").astype(str)
        return series.dt.strftime("%Y-%m-%d")

    dfs = df_pag[eh_pago(df_pag["Situação (Normalizada)"])].dropna(subset=["DATA DE PGTO."])
    dfs = dfs.assign(_p=_bucket(dfs["DATA DE PGTO."]))
    saidas = dfs.groupby("_p")["VALOR"].sum().rename("Saída")

    dfe = df_rec[eh_pago(df_rec["Situação (Normalizada)"])].dropna(subset=["Data PGTO."])
    dfe = dfe.assign(_p=_bucket(dfe["Data PGTO."]))
    entradas = dfe.groupby("_p")["Valor Total"].sum().rename("Entrada")

    df = pd.concat([entradas, saidas], axis=1).fillna(0).reset_index().rename(columns={"_p":"Período"})
    df["Saldo"] = df["Entrada"] - df["Saída"]
    df = df.sort_values("Período")
    df["Acumulado"] = df["Saldo"].cumsum()
    # Total
    total = pd.DataFrame([{
        "Período": "TOTAL",
        "Entrada": df["Entrada"].sum(),
        "Saída": df["Saída"].sum(),
        "Saldo": df["Saldo"].sum(),
        "Acumulado": df["Acumulado"].iloc[-1] if not df.empty else 0,
    }])
    return pd.concat([df, total], ignore_index=True)


# ============ DRE ============
def dre_por_empresa(df_pag: pd.DataFrame, df_rec: pd.DataFrame) -> pd.DataFrame:
    """Retorna DRE por empresa: Receita, Despesa, Resultado."""
    emp_set = set()
    if not df_pag.empty: emp_set.update(df_pag["Emp. Prop."].dropna().unique())
    if not df_rec.empty: emp_set.update(df_rec["Emp. Prop."].dropna().unique())
    rows = []
    for emp in sorted(emp_set):
        dp = df_pag[df_pag["Emp. Prop."] == emp] if not df_pag.empty else pd.DataFrame()
        dr = df_rec[df_rec["Emp. Prop."] == emp] if not df_rec.empty else pd.DataFrame()
        receita = float(dr["Valor Total"].sum()) if not dr.empty else 0
        despesa = float(dp["VALOR"].sum()) if not dp.empty else 0
        rows.append({
            "Empresa": emp, "Grupo": classificar_grupo(emp),
            "Receita": receita, "Despesa": despesa, "Resultado": receita - despesa,
            "Margem %": (receita - despesa) / receita if receita > 0 else 0,
        })
    df = pd.DataFrame(rows)
    if df.empty: return df
    total = {"Empresa":"TOTAL","Grupo":"—",
             "Receita":df["Receita"].sum(),
             "Despesa":df["Despesa"].sum(),
             "Resultado":df["Resultado"].sum()}
    total["Margem %"] = total["Resultado"]/total["Receita"] if total["Receita"] > 0 else 0
    return pd.concat([df, pd.DataFrame([total])], ignore_index=True)


def dre_plano_contas_por_empresa(df_pag: pd.DataFrame) -> pd.DataFrame:
    """Matrix despesa: rows=Plano de Contas, cols=Empresa."""
    if df_pag.empty: return pd.DataFrame()
    col = "Descrição Plano de Contas"
    if col not in df_pag.columns: return pd.DataFrame()
    df = df_pag.copy()
    df[col] = df[col].fillna("(Sem classificação)").replace("", "(Sem classificação)")
    m = df.pivot_table(index=col, columns="Emp. Prop.", values="VALOR",
                        aggfunc="sum", fill_value=0)
    m["TOTAL"] = m.sum(axis=1)
    m = m.sort_values("TOTAL", ascending=False)
    m.loc["TOTAL"] = m.sum()
    return m.reset_index()


# ============ SIMULAÇÃO ============
def simular_fluxo(df_pag: pd.DataFrame, df_rec: pd.DataFrame,
                   dias_atrasar: int = 0,
                   data_ini: date = None, data_fim: date = None) -> dict:
    """
    Simula: se eu atrasar X dias os pagamentos com vencimento em [ini, fim],
    qual fica a posição de caixa?
    Retorna dict com valores originais e simulados.
    """
    data_ini = data_ini or date.today()
    data_fim = data_fim or (date.today() + timedelta(days=30))
    ini_ts, fim_ts = pd.Timestamp(data_ini), pd.Timestamp(data_fim)

    # Saída prevista (VENCIMENTO no período + não pago)
    m_sai = (df_pag["VENCIMENTO"] >= ini_ts) & (df_pag["VENCIMENTO"] <= fim_ts) & eh_aberto(df_pag["Situação (Normalizada)"])
    saida_orig = float(df_pag.loc[m_sai, "VALOR"].sum())

    # Saída simulada: o que vence no período original é ATRASADO X dias, ou seja,
    # não sai neste período se os dias de atraso levam além de fim_ts
    # Simplificação: consideramos que ao atrasar X dias, os pagamentos com venc entre (fim-X, fim]
    # ficam FORA do período (vão sair depois)
    if dias_atrasar > 0:
        saida_sim_mask = m_sai & (df_pag["VENCIMENTO"] <= (fim_ts - pd.Timedelta(days=dias_atrasar)))
        saida_sim = float(df_pag.loc[saida_sim_mask, "VALOR"].sum())
    else:
        saida_sim = saida_orig

    # Entrada prevista
    m_ent = (df_rec["Vencimento"] >= ini_ts) & (df_rec["Vencimento"] <= fim_ts) & eh_aberto(df_rec["Situação (Normalizada)"])
    entrada = float(df_rec.loc[m_ent, "Valor Total"].sum())

    return {
        "Entrada Prevista": entrada,
        "Saída Original": saida_orig,
        "Saída Simulada": saida_sim,
        "Saldo Original": entrada - saida_orig,
        "Saldo Simulado": entrada - saida_sim,
        "Economia no Período": saida_orig - saida_sim,
    }


# ============ AUDITORIA ============
def auditar_pagamentos(df: pd.DataFrame) -> dict:
    from config import SITUACOES_VALIDAS
    if df.empty: return {}
    res = {}
    m = df["Emp. Prop."].isna() | (df["Emp. Prop."].astype(str).str.strip() == "")
    res["Empresa Proprietária vazia"] = df[m]
    m = df["VALOR"].isna() | (df["VALOR"] == 0)
    res["VALOR zerado ou nulo"] = df[m]
    m = df["VENCIMENTO"].isna()
    res["VENCIMENTO inválido/vazio"] = df[m]
    if "Situação (Normalizada)" in df.columns:
        m = ~df["Situação (Normalizada)"].fillna("").isin(SITUACOES_VALIDAS) & (df["Situação (Normalizada)"].fillna("") != "")
        res["Situação não reconhecida"] = df[m]
    if "FORNECEDOR" in df.columns:
        m = df["FORNECEDOR"].isna() | (df["FORNECEDOR"].astype(str).str.strip() == "")
        res["FORNECEDOR vazio"] = df[m]
    if "DATA DE PGTO." in df.columns:
        m = eh_pago(df["Situação (Normalizada)"]) & df["DATA DE PGTO."].isna()
        res["Pago sem DATA DE PGTO."] = df[m]
    if "Descrição Plano de Contas" in df.columns:
        m = df["Descrição Plano de Contas"].isna() | (df["Descrição Plano de Contas"].astype(str).str.strip() == "")
        res["Sem Plano de Contas"] = df[m]
    return res

def auditar_recebimentos(df: pd.DataFrame) -> dict:
    from config import SITUACOES_VALIDAS
    if df.empty: return {}
    res = {}
    m = df["Emp. Prop."].isna() | (df["Emp. Prop."].astype(str).str.strip() == "")
    res["Empresa Proprietária vazia"] = df[m]
    m = df["Valor Total"].isna() | (df["Valor Total"] == 0)
    res["Valor Total zerado ou nulo"] = df[m]
    m = df["Vencimento"].isna()
    res["Vencimento inválido/vazio"] = df[m]
    if "Situação (Normalizada)" in df.columns:
        m = ~df["Situação (Normalizada)"].fillna("").isin(SITUACOES_VALIDAS) & (df["Situação (Normalizada)"].fillna("") != "")
        res["Situação não reconhecida"] = df[m]
    if "Empresa" in df.columns:
        m = df["Empresa"].isna() | (df["Empresa"].astype(str).str.strip() == "")
        res["Cliente (Empresa) vazio"] = df[m]
    if "Data PGTO." in df.columns:
        m = eh_pago(df["Situação (Normalizada)"]) & df["Data PGTO."].isna()
        res["Pago sem Data PGTO."] = df[m]
    if "NF" in df.columns:
        m = df["NF"].isna() | (df["NF"].astype(str).str.strip() == "")
        res["NF vazia"] = df[m]
    return res


# ============ LISTAS PARA SLICERS ============
def lista_empresas(df_pag, df_rec):
    emp = set()
    if not df_pag.empty: emp.update(df_pag["Emp. Prop."].dropna().unique())
    if not df_rec.empty: emp.update(df_rec["Emp. Prop."].dropna().unique())
    return sorted([e for e in emp if str(e).strip()])

def lista_anos(df_pag, df_rec):
    anos = set()
    if not df_pag.empty:
        anos.update(df_pag["VENCIMENTO"].dt.year.dropna().unique())
    if not df_rec.empty:
        anos.update(df_rec["Vencimento"].dt.year.dropna().unique())
    return sorted([int(a) for a in anos if not pd.isna(a)], reverse=True)

def lista_departamentos(df_pag):
    if df_pag.empty or "DEPARTAMENTO" not in df_pag.columns: return []
    return sorted([d for d in df_pag["DEPARTAMENTO"].dropna().unique() if str(d).strip()])


# ============ FORMATADORES DE TABELA ============
def formatar_tabela_brl(df: pd.DataFrame, cols_brl: list, cols_pct: list = None) -> pd.DataFrame:
    """Formata colunas em R$ e % mantendo o DataFrame pronto pra st.dataframe."""
    from config import fmt_brl, fmt_pct
    show = df.copy()
    for c in cols_brl:
        if c in show.columns:
            show[c] = show[c].apply(fmt_brl)
    for c in (cols_pct or []):
        if c in show.columns:
            show[c] = show[c].apply(fmt_pct)
    return show
