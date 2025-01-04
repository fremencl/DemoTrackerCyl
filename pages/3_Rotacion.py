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
st.subheader("CILINDROS FUERA DE ROTACIÓN (> 30 DÍAS)")

# Calcular fecha límite
fecha_limite = datetime.now() - timedelta(days=30)

# Filtrar cilindros entregados y no retornados
df_entregas = df_proceso[df_proceso["PROCESO"].isin(["DESPACHO", "ENTREGA"])]

# Convertir las fechas en la columna "FECHA" y manejar errores de formato
try:
    df_entregas["FECHA"] = pd.to_datetime(df_entregas["FECHA"], format="%d/%m/%Y", errors="coerce")
except Exception as e:
    st.error(f"Error al procesar las fechas: {e}")
    st.stop()

# Verificar si hay valores nulos después de la conversión
if df_entregas["FECHA"].isna().any():
    st.warning("Algunas fechas no pudieron ser procesadas. Revisa el formato de las fechas en la hoja de cálculo.")

# Filtrar por cilindros entregados hace más de 30 días
df_fuera_rotacion = df_entregas[df_entregas["FECHA"] < fecha_limite]

# Mostrar los resultados
if not df_fuera_rotacion.empty:
    st.write(f"Cilindros entregados hace más de 30 días (Fecha límite: {fecha_limite.date()}):")
    st.dataframe(df_fuera_rotacion[["IDPROC", "FECHA", "PROCESO", "CLIENTE", "UBICACION"]])

    # Botón para descargar el listado en Excel
    @st.cache_data
    def convert_to_excel(dataframe):
        return dataframe.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descargar listado en Excel",
        data=convert_to_excel(df_fuera_rotacion),
        file_name="Cilindros_Fuera_Rotacion.csv",
        mime="text/csv",
    )
else:
    st.warning("No se encontraron cilindros fuera de rotación (> 30 días).")
