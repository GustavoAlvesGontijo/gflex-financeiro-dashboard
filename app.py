# -*- coding: utf-8 -*-
import streamlit as st
st.title("🔬 Teste GFlex")
st.write("Se você vê isso, o Streamlit Cloud funciona. Vou restaurar o app completo.")
try:
    token_presente = "github" in st.secrets and "token" in st.secrets["github"]
    st.success(f"Secret [github] OK: {token_presente}")
except Exception as e:
    st.error(f"Secret erro: {e}")
