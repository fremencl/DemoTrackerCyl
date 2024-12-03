import streamlit as st
from PIL import Image
from pathlib import Path

def get_project_root() -> Path:
    """Returns the project root folder."""
    return Path(__file__).parent

def load_image(image_name: str) -> Image:
    """Loads an image from the specified path."""
    image_path = Path(get_project_root()) / f"assets/{image_name}"
    print(f"Trying to load image from: {image_path}")  # Para depurar
    return Image.open(image_path)

# Configuración de la aplicación
st.set_page_config(
    page_title="Demo Tracker Cyl",
    page_icon=":dollar:",
    initial_sidebar_state="expanded",
)

# Crear tres columnas y mostrar la imagen en la columna central
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(load_image("Logo.jpg"), width=150)

# Títulos y subtítulos
st.write("### SISTEMA TRACKING DE CILINDROS :chart_with_upwards_trend:")
st.write("#### URQUINOX RANCAGUA")

st.markdown("---")

# Mensaje en la barra lateral
st.sidebar.success("Selecciona un modelo de consulta")

# Contenido introductorio y descripción de la aplicación
st.write("")
st.markdown(
    """##### Bienvenido al sistema de gestion de cilindros de Carlitos Urquizar

    
Elije el modelo de conulta que necesitas:

- **Movimientos por Cilindro**: Te permitirá consultar todos los movimientos asociados a una serie específica.
- **Cilindros por cliente**: Te permitirá conocer los cilindros en un cliente especifico al momento de ejecutar la consulta.

:moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag:
    """
)