import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

import streamlit as st
from coate_styles import aplicar_estilos
from coate_auth import exigir_acesso

aplicar_estilos()
exigir_acesso("atendimento")

st.markdown("## Atendimento")
st.info("Esta é uma página placeholder do módulo Atendimento. O espaço está pronto para evoluções futuras sem interferir nos demais módulos.")
