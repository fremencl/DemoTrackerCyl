# pages/5_RangoFechas.py

import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime

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
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=scopes
        )
        client = gspread.authorize(credentials)
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

# Normalizar la columna SERIE en df_detalle
if df_detalle is not None:
    df_detalle["SERIE"] = (
        df_detalle["SERIE"]
        .astype(str)
        .str.replace(",", "", regex=False)
    )

# ————————————————————————————————
# 4) Convertir FECHA en datetime
# ————————————————————————————————
if df_proceso is not None:
    df_proceso["FECHA"] = pd.to_datetime(
        df_proceso["FECHA"], format="%d/%m/%Y", errors="coerce"
    )

# ————————————————————————————————
# 5) Merge para traer SERIE a los procesos
# ————————————————————————————————
if df_proceso is not None and df_detalle is not None:
    df_full = df_proceso.merge(
        df_detalle[["IDPROC", "SERIE"]],
        on="IDPROC",
        how="left"
    )
else:
    df_full = pd.DataFrame()

# ————————————————————————————————
# 6) UI
# ————————————————————————————————
st.title("Demo TrackerCyl")
st.subheader("CONSULTA DE MOVIMIENTOS POR RANGO DE FECHA")

# Por defecto: última semana
hoy = datetime.now().date()
predeterminado = (hoy - pd.Timedelta(days=7), hoy)

fecha_inicio, fecha_termino = st.date_input(
    "Seleccione rango de fechas",
    value=predeterminado,
    help="Elija fecha de inicio y fecha de término"
)

if st.button("Buscar"):
    # Validar rango
    if fecha_inicio > fecha_termino:
        st.warning("La fecha de inicio no puede ser posterior a la fecha de término.")
    else:
        mask = (
            (df_full["FECHA"].dt.date >= fecha_inicio) &
            (df_full["FECHA"].dt.date <= fecha_termino)
        )
        df_filtrado = df_full.loc[mask]

        if df_filtrado.empty:
            st.warning("No se encontraron movimientos en ese rango de fechas.")
        else:
            st.success(
                f"Movimientos desde {fecha_inicio.isoformat()} hasta {fecha_termino.isoformat()}:"
            )
            st.dataframe(
                df_filtrado[
                    ["FECHA", "IDPROC", "PROCESO", "CLIENTE", "UBICACION", "SERIE"]
                ]
            )

            # ————————————————————————————————
            # Descarga en CSV
            # ————————————————————————————————
            def convert_to_csv(df: pd.DataFrame) -> bytes:
                return df.to_csv(index=False).encode("utf-8")

            nombre_archivo = (
                f"movimientos_{fecha_inicio.isoformat()}_a_{fecha_termino.isoformat()}.csv"
            )
            st.download_button(
                label="⬇️ Descargar resultados en CSV",
                data=convert_to_csv(df_filtrado),
                file_name=nombre_archivo,
                mime="text/csv",
            )
