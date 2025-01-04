import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime, timedelta

# 1) Importamos la función de autenticación
from auth import check_password

# Primero verificamos la contraseña.
if not check_password():
    st.stop()

# Funciones para obtener datos de Google Sheets
@st.cache_data
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
        # En caso de error, mostrar el mensaje y retornar None
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# Cargar los datos desde Google Sheets
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# Título de la aplicación
st.title("Demo TrackerCyl")

# Subtítulo de la aplicación
st.subheader("CILINDROS NO RETORNADOS")

# Asegurar que IDPROC sea tratado como string
df_detalle["IDPROC"] = df_detalle["IDPROC"].astype(str)

# Cruzar con la pestaña PROCESO
df_movimientos = df_detalle.merge(df_proceso, on="IDPROC", how="left")

# Filtrar cilindros "Entregados" y "Retornados"
df_entregados = df_movimientos[df_movimientos["PROCESO"].isin(["DESPACHO", "ENTREGA"])]
df_retorno = df_movimientos[df_movimientos["PROCESO"].isin(["RETIRO", "RECEPCION"])]

# Identificar cilindros no retornados
cilindros_entregados = set(df_entregados["SERIE"])
cilindros_retorno = set(df_retorno["SERIE"])
cilindros_no_retorno = cilindros_entregados - cilindros_retorno

# Filtrar los datos finales
df_no_retorno = df_entregados[df_entregados["SERIE"].isin(cilindros_no_retorno)]

# Verificar si hay datos para mostrar
if not df_no_retorno.empty:
    # Mostrar los resultados
    st.write("Cilindros que han sido entregados pero no retornados:")
    st.dataframe(df_no_retorno[["SERIE", "IDPROC", "FECHA", "PROCESO", "CLIENTE"]])

    # Botón para descargar el listado en Excel
    @st.cache_data
    def convert_to_excel(dataframe):
        return dataframe.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descargar listado en Excel",
        data=convert_to_excel(df_no_retorno),
        file_name="Cilindros_No_Retornados.csv",
        mime="text/csv",
    )
else:
    st.warning("No se encontraron cilindros no retornados.")
