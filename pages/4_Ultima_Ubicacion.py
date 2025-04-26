import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd

# 1) Importamos la función de autenticación
from auth import check_password

# Primero verificamos la contraseña.
if not check_password():
    st.stop()

# Función para obtener datos desde Google Sheets
def get_gsheet_data(sheet_name):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=scopes
        )
        client = gspread.authorize(credentials)
        sheet = client.open("TRAZABILIDAD").worksheet(sheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# Cargar los datos
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# Normalizar columnas
df_proceso.columns = df_proceso.columns.str.strip().str.upper()
df_detalle.columns = df_detalle.columns.str.strip().str.upper()

# Convertir claves a texto
df_proceso["IDPROC"] = df_proceso["IDPROC"].astype(str)
df_detalle["IDPROC"] = df_detalle["IDPROC"].astype(str)

# Eliminar columna PROCESO de df_detalle si existe
if "PROCESO" in df_detalle.columns:
    df_detalle = df_detalle.drop(columns=["PROCESO"])

# Merge conservando campos principales
df_movimientos = df_detalle.merge(
    df_proceso[["IDPROC", "PROCESO", "FECHA", "CLIENTE", "UBICACION"]],
    on="IDPROC",
    how="left"
)

# Título y subtítulo
st.title("Demo TrackerCyl")
st.subheader("Último Movimiento de Cada Cilindro")

# Normalizar serie
df_movimientos["SERIE"] = df_movimientos["SERIE"].astype(str).str.replace(",", "", regex=False)

# Conversión de fecha
df_movimientos["FECHA"] = pd.to_datetime(df_movimientos["FECHA"], format="%d/%m/%Y", errors="coerce")

# Último movimiento por SERIE
df_ultimo_movimiento = (
    df_movimientos
    .sort_values(by=["FECHA"], ascending=False)
    .drop_duplicates(subset="SERIE", keep="first")
)

# Filtro de Ubicación
ubicaciones = df_ultimo_movimiento["UBICACION"].dropna().unique().tolist()
ubicacion_seleccionada = st.selectbox("Selecciona una ubicación:", ["Todas"] + ubicaciones)

if ubicacion_seleccionada != "Todas":
    df_filtrado = df_ultimo_movimiento[df_ultimo_movimiento["UBICACION"] == ubicacion_seleccionada]
else:
    df_filtrado = df_ultimo_movimiento

# Mostrar resultados
if not df_filtrado.empty:
    st.write(f"Mostrando últimos movimientos{' para ubicación: ' + ubicacion_seleccionada if ubicacion_seleccionada != 'Todas' else ''}:")

    df_filtrado["FECHA"] = df_filtrado["FECHA"].dt.strftime("%Y-%m-%d")

    st.dataframe(df_filtrado[["SERIE", "IDPROC", "FECHA", "PROCESO", "CLIENTE", "UBICACION"]])

    def convert_to_excel(dataframe):
        return dataframe.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descargar listado en Excel",
        data=convert_to_excel(df_filtrado),
        file_name="Ultimo_Movimiento_Cilindros.csv",
        mime="text/csv",
    )
else:
    st.warning("No se encontraron datos para los criterios seleccionados.")
