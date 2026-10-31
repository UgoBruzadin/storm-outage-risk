"""How it works: a plain-language summary, with links to the detail."""
import streamlit as st
from lib import text

st.title(text("about.title"))
st.markdown(text("about.body"))
