import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd

# Funciones para obtener datos de Google Sheets
@st.cache_data
def get_gsheet_data(sheet_name):
    try:
        # Cargar las credenciales desde los secretos de Streamlit
        creds_dict = st.secrets["gcp_service_account"]
        
        # Definir los scopes necesarios
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

        # Crear las credenciales con los scopes especificados
        credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
        
        # Conectar con gspread usando las credenciales
        client = gspread.authorize(credentials)
        
        # Abrir la hoja de cálculo y obtener los datos
        sheet = client.open("TRAZABILIDAD").worksheet(sheet_name)
        data = sheet.get_all_records()
        
        # Retornar los datos como un DataFrame de pandas
        return pd.DataFrame(data)
    
    except Exception as e:
        # En caso de error, mostrar el mensaje y retornar None
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# Cargar los datos desde Google Sheets
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# Título de la aplicación
st.title("Demo TrackerCyl")

# Subtítulo de la aplicación
st.subheader("CONSULTA DE MOVIMIENTOS POR CILINDRO")

# Cuadro de texto para ingresar la ID del cilindro
target_cylinder = st.text_input("Ingrese la ID del cilindro a buscar:")

# Botón de búsqueda
if st.button("Buscar"):
    if target_cylinder:
        # Filtrar las transacciones asociadas a la ID de cilindro
        ids_procesos = df_detalle[df_detalle["SERIE"] == target_cylinder]["IDPROC"]
        df_resultados = df_proceso[df_proceso["IDPROC"].isin(ids_procesos)]

        # Mostrar los resultados
        if not df_resultados.empty:
            st.write(f"Movimientos para el cilindro ID: {target_cylinder}")
            st.dataframe(df_resultados[["FECHA", "HORA", "IDPROC", "PROCESO", "CLIENTE", "UBICACION"]])
        else:
            st.warning("No se encontraron movimientos para el cilindro ingresado.")
    else:
        st.warning("Por favor, ingrese una ID de cilindro.")
