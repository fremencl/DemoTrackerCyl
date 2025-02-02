import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd

# 1) Importamos la función de autenticación
from auth import check_password

# Primero verificamos la contraseña.
if not check_password():
    st.stop()

# @st.cache_data
def get_gsheet_data(sheet_name):
    try:
        # Cargar las credenciales desde los secretos de Streamlit
        creds_dict = st.secrets["gcp_service_account"]
        
        # Definir los scopes necesarios
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets", 
            "https://www.googleapis.com/auth/drive"
        ]

        # Crear las credenciales con los scopes especificados
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, 
            scopes=scopes
        )
        
        # Conectar con gspread usando las credenciales
        client = gspread.authorize(credentials)
        
        # Abrir la hoja de cálculo y obtener los datos
        sheet = client.open("TRAZABILIDAD").worksheet(sheet_name)
        data = sheet.get_all_records()
        
        # Retornar los datos como un DataFrame de pandas
        return pd.DataFrame(data)
    
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# Cargar los datos desde Google Sheets
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# Normalizar la columna SERIE en df_detalle
# 1) Convertimos a string
df_detalle["SERIE"] = df_detalle["SERIE"].astype(str)

# 2) Quitamos separadores de miles (comas). 
#    Si tienes otros caracteres no deseados, agrégalos al replace.
df_detalle["SERIE"] = df_detalle["SERIE"].str.replace(",", "", regex=False)

st.title("Demo TrackerCyl")
st.subheader("CONSULTA DE MOVIMIENTOS POR CILINDRO")

# Cuadro de texto para ingresar la ID del cilindro
target_cylinder = st.text_input("Ingrese la ID del cilindro a buscar:")

if st.button("Buscar"):
    if target_cylinder:
        # Normalizar también lo que ingresa el usuario
        target_cylinder_normalized = target_cylinder.replace(",", "")

        # Filtrar las transacciones asociadas a la ID de cilindro
        ids_procesos = df_detalle[df_detalle["SERIE"] == target_cylinder_normalized]["DOCUMENTO"]
        df_resultados = df_proceso[df_proceso["DOCUMENTO"].isin(ids_procesos)]

        # Mostrar los resultados
        if not df_resultados.empty:
            st.write(f"Movimientos para el cilindro ID: {target_cylinder}")
            st.dataframe(df_resultados[["FECHA", "HORA", "DOCUMENTO", "PROCESO", "CLIENTE", "UBICACION"]])
        else:
            st.warning("No se encontraron movimientos para el cilindro ingresado.")
    else:
        st.warning("Por favor, ingrese una ID de cilindro.")
