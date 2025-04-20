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

# Título de la aplicación
st.title("Demo TrackerCyl")

# Subtítulo de la aplicación
st.subheader("CILINDROS NO RETORNADOS")

# Asegurar que DOCUMENTO sea tratado como texto
df_detalle["IDPROC"] = df_detalle["IDPROC"].astype(str)

# -----------------------------------------------------------------------
# NORMALIZACIÓN DE LA COLUMNA "SERIE" EN df_detalle
# -----------------------------------------------------------------------
df_detalle["SERIE"] = df_detalle["SERIE"].astype(str)
df_detalle["SERIE"] = df_detalle["SERIE"].str.replace(",", "", regex=False)
# -----------------------------------------------------------------------

# Cruce con la pestaña PROCESO
df_movimientos = df_detalle.merge(df_proceso, on="PROCESO", how="left")

# Filtrar cilindros entregados hace más de 30 días
fecha_limite = datetime.now() - timedelta(days=30)
df_movimientos["FECHA"] = pd.to_datetime(df_movimientos["FECHA"], format="%d/%m/%Y", errors="coerce")

df_entregados = df_movimientos[
    (df_movimientos["PROCESO"].isin(["DESPACHO", "ENTREGA"])) &
    (df_movimientos["FECHA"] < fecha_limite)
]

# Encontrar el último movimiento (por fecha) de cada cilindro entregado
df_entregados_ultimo = (
    df_entregados
    .sort_values(by=["FECHA"], ascending=False)
    .drop_duplicates(subset="SERIE", keep="first")
)

# Encontrar el último retorno (si existe) para cada cilindro
df_retorno = df_movimientos[df_movimientos["PROCESO"].isin(["RETIRO", "RECEPCION"])]
df_retorno_ultimo = (
    df_retorno
    .sort_values(by=["FECHA"], ascending=False)
    .drop_duplicates(subset="SERIE", keep="first")
)

# Ver si hubo retorno posterior a la última entrega
df_retorno_validos = df_retorno_ultimo.merge(
    df_entregados_ultimo[["SERIE", "FECHA"]],
    on="SERIE",
    suffixes=("_retorno", "_entrega")
)
df_retorno_validos = df_retorno_validos[
    df_retorno_validos["FECHA_retorno"] > df_retorno_validos["FECHA_entrega"]
]

cilindros_entregados_validos = set(df_entregados_ultimo["SERIE"])
cilindros_retorno_validos = set(df_retorno_validos["SERIE"])

# Diferencia: cilindros entregados pero no retornados
cilindros_no_retorno = cilindros_entregados_validos - cilindros_retorno_validos
df_no_retorno = df_entregados_ultimo[df_entregados_ultimo["SERIE"].isin(cilindros_no_retorno)]

# Mostrar resultados
if not df_no_retorno.empty:
    st.write("Cilindros entregados hace más de 30 días y no retornados:")

    # Simplificar la fecha al formato YYYY-MM-DD
    df_no_retorno["FECHA"] = df_no_retorno["FECHA"].dt.strftime("%Y-%m-%d")

    st.dataframe(df_no_retorno[["SERIE", "IDPROC", "FECHA", "PROCESO", "CLIENTE"]])

    # Función para convertir el DataFrame a CSV (sin caché)
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
