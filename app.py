import streamlit as st
st.title("GFlex Financeiro")
st.write("Teste de ambiente Streamlit Cloud.")
if "github" in st.secrets:
    st.success("✅ Secret [github] OK")
else:
    st.error("Secret [github] faltando")
