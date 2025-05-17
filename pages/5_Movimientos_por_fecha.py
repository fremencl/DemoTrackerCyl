# pages/5_Movimientos_por_fecha.py

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

# ————————————————————————————————
# 4) Normalizar nombres de columnas a mayúsculas y sin espacios
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
# 7) Construir df_full incluyendo SERIE y SERVICIO
#    (SERVICIO viene de df_detalle)
# ————————————————————————————————
if df_proceso is not None and df_detalle is not None:
    # asegurarnos de tomar sólo una fila por IDPROC en df_detalle
    detalle_unico = df_detalle[["IDPROC", "SERIE", "SERVICIO"]].drop_duplicates("IDPROC")
    df_full = df_proceso.merge(
        detalle_unico,
        on="IDPROC",
        how="left"
    )
else:
    df_full = pd.DataFrame()

# ————————————————————————————————
# 8) UI: selección de rango de fechas
# ————————————————————————————————
st.title("FASTRACK")
st.subheader("CONSULTA DE MOVIMIENTOS POR RANGO DE FECHA")

hoy = datetime.now().date()
predeterminado = (hoy - pd.Timedelta(days=7), hoy)

fecha_inicio, fecha_termino = st.date_input(
    "Seleccione rango de fechas",
    value=predeterminado,
    help="Elija fecha de inicio y fecha de término"
)

# ————————————————————————————————
# 9) Al hacer clic en Buscar
# ————————————————————————————————
if st.button("Buscar"):
    if fecha_inicio > fecha_termino:
        st.warning("La fecha de inicio no puede ser posterior a la fecha de término.")
    else:
        # Filtrar por fecha (solo parte date, sin hora)
        mask = (
            (df_full["FECHA"].dt.date >= fecha_inicio) &
            (df_full["FECHA"].dt.date <= fecha_termino)
        )
        df_filtrado = df_full.loc[mask].copy()

        if df_filtrado.empty:
            st.warning("No se encontraron movimientos en ese rango de fechas.")
        else:
            # Convertir FECHA a puro date (quita la hora)
            df_filtrado["FECHA"] = df_filtrado["FECHA"].dt.date

            st.success(
                f"Movimientos desde {fecha_inicio.isoformat()} hasta {fecha_termino.isoformat()}:"
            )
            st.dataframe(
                df_filtrado[
                    ["FECHA", "IDPROC", "PROCESO", "CLIENTE", "UBICACION", "SERIE", "SERVICIO"]
                ]
            )

            # Función compacta para CSV
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
