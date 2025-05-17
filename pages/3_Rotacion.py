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

# ------------------------------------------------------------------
# Función para obtener datos desde Google Sheets
# ------------------------------------------------------------------
def get_gsheet_data(sheet_name):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=scopes
        )
        client = gspread.authorize(credentials)
        sheet = client.open("TRAZABILIDAD").worksheet(sheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# ------------------------------------------------------------------
# Cargar datos desde las hojas
# ------------------------------------------------------------------
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# ------------------------------------------------------------------
# Normalización de columnas
# ------------------------------------------------------------------
df_proceso.columns = df_proceso.columns.str.strip().str.upper()
df_detalle.columns = df_detalle.columns.str.strip().str.upper()

# Convertir claves a string
df_proceso["IDPROC"] = df_proceso["IDPROC"].astype(str)
df_detalle["IDPROC"] = df_detalle["IDPROC"].astype(str)

# Eliminar columna PROCESO de df_detalle si existe
if "PROCESO" in df_detalle.columns:
    df_detalle = df_detalle.drop(columns=["PROCESO"])

# ------------------------------------------------------------------
# Merge incluyendo ahora SERVICIO ▶️
# ------------------------------------------------------------------
df_movimientos = df_detalle.merge(
    df_proceso[["IDPROC", "PROCESO", "FECHA", "CLIENTE", "SERVICIO"]],  # ▶️ añadimos SERVICIO
    on="IDPROC",
    how="left"
)

# ------------------------------------------------------------------
# Título y subtítulo
# ------------------------------------------------------------------
st.title("Demo TrackerCyl")
st.subheader("CILINDROS NO RETORNADOS")

# ------------------------------------------------------------------
# Normalización de serie
# ------------------------------------------------------------------
df_movimientos["SERIE"] = (
    df_movimientos["SERIE"]
    .astype(str)
    .str.replace(",", "", regex=False)
)

# ------------------------------------------------------------------
# Conversión de fecha
# ------------------------------------------------------------------
df_movimientos["FECHA"] = pd.to_datetime(
    df_movimientos["FECHA"], format="%d/%m/%Y", errors="coerce"
)

# ------------------------------------------------------------------
# Filtro: entregados hace más de 30 días
# ------------------------------------------------------------------
fecha_limite = datetime.now() - timedelta(days=30)
df_entregados = df_movimientos[
    (df_movimientos["PROCESO"].isin(["DESPACHO", "ENTREGA"])) &
    (df_movimientos["FECHA"] < fecha_limite)
]

# Último movimiento por serie
df_entregados_ultimo = (
    df_entregados
    .sort_values(by=["FECHA"], ascending=False)
    .drop_duplicates(subset="SERIE", keep="first")
)

# Últimos retornos (RETIRO o RECEPCION)
df_retorno = df_movimientos[df_movimientos["PROCESO"].isin(["RETIRO", "RECEPCION"])]
df_retorno_ultimo = (
    df_retorno
    .sort_values(by=["FECHA"], ascending=False)
    .drop_duplicates(subset="SERIE", keep="first")
)

# Comparación entre entregas y retornos
df_retorno_validos = df_retorno_ultimo.merge(
    df_entregados_ultimo[["SERIE", "FECHA"]],
    on="SERIE",
    suffixes=("_retorno", "_entrega")
)
df_retorno_validos = df_retorno_validos[
    df_retorno_validos["FECHA_retorno"] > df_retorno_validos["FECHA_entrega"]
]

# Determinar cilindros no retornados
cilinds_ent = set(df_entregados_ultimo["SERIE"])
cilinds_ret = set(df_retorno_validos["SERIE"])
cilinds_no_ret = cilinds_ent - cilinds_ret
df_no_retorno = df_entregados_ultimo[
    df_entregados_ultimo["SERIE"].isin(cilinds_no_ret)
]

# ------------------------------------------------------------------
# Mostrar resultados + descarga incluyendo SERVICIO ▶️
# ------------------------------------------------------------------
if not df_no_retorno.empty:
    st.write("Cilindros entregados hace más de 30 días y no retornados:")

    df_no_retorno["FECHA"] = df_no_retorno["FECHA"].dt.strftime("%Y-%m-%d")

    st.dataframe(
        df_no_retorno[
            ["SERIE", "IDPROC", "FECHA", "PROCESO", "CLIENTE", "SERVICIO"]  # ▶️ SERVICIO en el listado
        ]
    )

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
