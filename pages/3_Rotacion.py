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
df_detalle["DOCUMENTO"] = df_detalle["DOCUMENTO"].astype(str)

# Cruzar con la pestaña PROCESO
df_movimientos = df_detalle.merge(df_proceso, on="DOCUMENTO", how="left")

# Filtrar cilindros entregados hace más de 30 días
fecha_limite = datetime.now() - timedelta(days=30)
df_movimientos["FECHA"] = pd.to_datetime(df_movimientos["FECHA"], format="%d/%m/%Y", errors="coerce")
df_entregados = df_movimientos[
    (df_movimientos["PROCESO"].isin(["DESPACHO", "ENTREGA"])) &
    (df_movimientos["FECHA"] < fecha_limite)
]

# Agrupar por SERIE para encontrar el último movimiento de entrega
df_entregados_ultimo = df_entregados.sort_values(by=["FECHA"], ascending=False).drop_duplicates(subset="SERIE", keep="first")

# Agrupar por SERIE para encontrar el último movimiento de retorno
df_retorno = df_movimientos[df_movimientos["PROCESO"].isin(["RETIRO", "RECEPCION"])]
df_retorno_ultimo = df_retorno.sort_values(by=["FECHA"], ascending=False).drop_duplicates(subset="SERIE", keep="first")

# Filtrar los retornos que son posteriores a la entrega
df_retorno_validos = df_retorno_ultimo.merge(
    df_entregados_ultimo[["SERIE", "FECHA"]],
    on="SERIE",
    suffixes=("_retorno", "_entrega")
)
df_retorno_validos = df_retorno_validos[df_retorno_validos["FECHA_retorno"] > df_retorno_validos["FECHA_entrega"]]

# Crear conjuntos de entregas válidas y retornos válidos
cilindros_entregados_validos = set(df_entregados_ultimo["SERIE"])
cilindros_retorno_validos = set(df_retorno_validos["SERIE"])

# Diferencia: cilindros entregados pero no retornados válidos
cilindros_no_retorno = cilindros_entregados_validos - cilindros_retorno_validos

# Filtrar los datos finales
df_no_retorno = df_entregados_ultimo[df_entregados_ultimo["SERIE"].isin(cilindros_no_retorno)]

# Verificar si hay datos para mostrar
if not df_no_retorno.empty:
    # Mostrar los resultados
    st.write("Cilindros entregados hace más de 30 días y no retornados:")
    st.dataframe(df_no_retorno[["SERIE", "DOCUMENTO", "FECHA", "PROCESO", "CLIENTE"]])

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
    st.warning("No se encontraron cilindros entregados hace más de 30 días y no retornados.")
