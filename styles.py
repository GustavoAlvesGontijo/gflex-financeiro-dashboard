# -*- coding: utf-8 -*-
"""CSS compartilhado — injeta em todas as páginas."""
import streamlit as st

def inject_css():
    st.markdown("""
<style>
/* Header e sidebar */
[data-testid="stHeader"]{background-color:#1a1a2e}
[data-testid="stSidebar"]{background:#f8f9fa}
[data-testid="stSidebarNav"]{padding-top:8px}
[data-testid="stSidebarNav"] a{
    font-size:0.95rem!important;font-weight:500;padding:10px 16px!important;
    border-radius:8px;margin:2px 8px;transition:all 0.2s;
    color:#333!important;text-decoration:none!important;
}
[data-testid="stSidebarNav"] a:hover{background:#EC850012;color:#EC8500!important}
[data-testid="stSidebarNav"] a[aria-selected="true"]{
    background:linear-gradient(90deg,#EC850018,#EC850008)!important;
    border-left:4px solid #EC8500!important;font-weight:700!important;
    color:#1a1a2e!important;
}
/* Métricas */
[data-testid="stMetricValue"]{font-size:1.5rem;font-weight:700;color:#1a1a2e}
[data-testid="stMetricLabel"]{font-size:0.72rem;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:#666}
[data-testid="stMetricDelta"]{font-size:0.8rem;font-weight:600}
/* Tabelas */
[data-testid="stDataFrame"] th{
    background:#1a1a2e!important;color:white!important;
    font-weight:600;font-size:0.85rem!important;text-transform:uppercase;
    padding:12px 14px!important;
}
[data-testid="stDataFrame"] td{
    padding:10px 14px!important;font-size:0.92rem!important;
    border-bottom:1px solid #eee!important;color:#1a1a2e!important;
}
[data-testid="stDataFrame"] tr:nth-child(even){background:#F8F9FA!important}
[data-testid="stDataFrame"] tr:hover{background:#FFF3E0!important}
/* Expanders e containers */
[data-testid="stExpander"]{background:white;border:1px solid #e0e0e0;border-radius:10px}
/* Footer */
footer{visibility:hidden}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-thumb{background:#ccc;border-radius:3px}
/* Títulos de página */
.hero{
    background:linear-gradient(135deg,#1a1a2e 0%,#2d2d5e 100%);
    padding:22px 28px;border-radius:14px;margin-bottom:18px;color:white;
}
.hero h1{margin:0;font-size:1.7rem;font-weight:700;color:white}
.hero p{margin:4px 0 0 0;color:#EC8500;font-size:0.92rem;font-weight:500}
/* KPI cards custom */
.kpi{
    background:white;border:1px solid #e8e8e8;border-radius:12px;
    padding:14px 18px;box-shadow:0 1px 3px rgba(0,0,0,0.04);
}
.kpi-label{font-size:0.72rem;text-transform:uppercase;color:#666;font-weight:600;letter-spacing:0.5px;margin:0}
.kpi-value{font-size:1.6rem;font-weight:700;color:#1a1a2e;margin:4px 0 0 0;line-height:1.1}
.kpi-value.pos{color:#27AE60}
.kpi-value.neg{color:#E74C3C}
.kpi-sub{font-size:0.75rem;color:#888;margin:2px 0 0 0}
</style>
""", unsafe_allow_html=True)


def kpi_card(label, value, color=None, sub=None):
    """Renderiza um KPI card com label+valor+sub opcional."""
    cls = ""
    if color == "pos": cls = "pos"
    elif color == "neg": cls = "neg"
    sub_html = f'<p class="kpi-sub">{sub}</p>' if sub else ""
    st.markdown(f"""
<div class="kpi">
<p class="kpi-label">{label}</p>
<p class="kpi-value {cls}">{value}</p>
{sub_html}
</div>
""", unsafe_allow_html=True)


# import após definir helpers (evita circular)
import streamlit as st
