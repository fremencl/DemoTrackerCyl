import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime, timedelta

from auth import check_password

# ————————————————————————————————
# 1) Autenticación
# ————————————————————————————————
if not check_password():
    st.stop()

# ————————————————————————————————
# 2) Función para cargar cada hoja
# ————————————————————————————————
def get_gsheet_data(sheet_name: str) -> pd.DataFrame | None:
    try:
        creds = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds_obj = service_account.Credentials.from_service_account_info(creds, scopes=scopes)
        client = gspread.authorize(creds_obj)
        sheet = client.open("TRAZABILIDAD").worksheet(sheet_name)
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# ————————————————————————————————
# 3) Cargar datos
# ————————————————————————————————
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# ————————————————————————————————
# 4) Normalizar nombres de columnas
# ————————————————————————————————
for df in (df_proceso, df_detalle):
    if df is not None:
        df.columns = df.columns.str.strip().str.upper()

# ————————————————————————————————
# 5) Limpiar la columna SERIE en df_detalle
# ————————————————————————————————
if df_detalle is not None:
    df_detalle["SERIE"] = (
        df_detalle["SERIE"]
        .astype(str)
        .str.replace(",", "", regex=False)
    )

# ————————————————————————————————
# 6) Convertir FECHA en datetime
# ————————————————————————————————
if df_proceso is not None:
    df_proceso["FECHA"] = pd.to_datetime(
        df_proceso["FECHA"], format="%d/%m/%Y", errors="coerce"
    )

# ————————————————————————————————
# 7) UI: rango de fechas
# ————————————————————————————————
st.title("Demo TrackerCyl")
st.subheader("CONSULTA DE MOVIMIENTOS POR RANGO DE FECHA")

today = datetime.now().date()
default_range = (today - timedelta(days=7), today)

start_date, end_date = st.date_input(
    "Seleccione rango de fechas",
    value=default_range,
    help="Elija fecha de inicio y fecha de término"
)

# ————————————————————————————————
# 8) Al hacer clic en Buscar
# ————————————————————————————————
if st.button("Buscar"):
    if df_proceso is None or df_detalle is None:
        st.error("No se pudieron cargar los datos de Google Sheets.")
    elif start_date > end_date:
        st.warning("La fecha de inicio no puede ser posterior a la fecha de término.")
    else:
        # Filtrar procesos en el rango de fechas
        mask = (
            (df_proceso["FECHA"].dt.date >= start_date) &
            (df_proceso["FECHA"].dt.date <= end_date)
        )
        df_proc_filtered = df_proceso.loc[mask]

        if df_proc_filtered.empty:
            st.warning("No se encontraron movimientos en ese rango de fechas.")
        else:
            # Merge con todos los detalles (uno por cilindro)
            df_merged = df_proc_filtered.merge(
                df_detalle[["IDPROC", "SERIE"]],
                on="IDPROC",
                how="left"
            )

            # Convertir FECHA a date puro para mostrar
            df_merged["FECHA"] = df_merged["FECHA"].dt.date

            st.success(
                f"Movimientos desde {start_date.isoformat()} hasta {end_date.isoformat()}:"
            )
            st.dataframe(
                df_merged[
                    ["FECHA", "IDPROC", "PROCESO", "CLIENTE", "UBICACION", "SERIE", "SERVICIO"]
                ]
            )

            # Descargar CSV
            def convert_to_csv(df: pd.DataFrame) -> bytes:
                return df.to_csv(index=False).encode("utf-8")

            filename = f"movimientos_{start_date.isoformat()}_a_{end_date.isoformat()}.csv"
            st.download_button(
                label="⬇️ Descargar resultados en CSV",
                data=convert_to_csv(df_merged),
                file_name=filename,
                mime="text/csv",
            )
