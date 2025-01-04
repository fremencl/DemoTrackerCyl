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
st.subheader("CILINDROS NO RETORNADOS (> 30 DÍAS)")

# Calcular fecha límite
fecha_limite = datetime.now() - timedelta(days=30)

# Asegurar que IDPROC es numérico
df_detalle["IDPROC"] = pd.to_numeric(df_detalle["IDPROC"], errors="coerce")
df_detalle = df_detalle.dropna(subset=["IDPROC"])

# Convertir IDPROC a entero para garantizar consistencia
df_detalle["IDPROC"] = df_detalle["IDPROC"].astype(int)

# Obtener el último movimiento de cada cilindro
df_ultimo_movimiento = df_detalle.sort_values(by=["IDPROC"], ascending=False).drop_duplicates(subset="SERIE", keep="first")

# Cruzar con la pestaña PROCESO para verificar el tipo de movimiento
df_ultimo_movimiento = df_ultimo_movimiento.merge(df_proceso, on="IDPROC", how="left")

# Filtrar cilindros con último proceso de "ENTREGA" o "DESPACHO"
df_no_retorno = df_ultimo_movimiento[
    (df_ultimo_movimiento["PROCESO"].isin(["DESPACHO", "ENTREGA"])) &
    (pd.to_datetime(df_ultimo_movimiento["FECHA"], format="%d/%m/%Y", errors="coerce") < fecha_limite)
]

# Verificar si hay datos para mostrar
if not df_no_retorno.empty:
    # Mostrar los resultados
    st.write(f"Cilindros no retornados hace más de 30 días (Fecha límite: {fecha_limite.date()}):")
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
    st.warning("No se encontraron cilindros no retornados hace más de 30 días.")
