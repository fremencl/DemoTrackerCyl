import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd

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

# ------------------------------------------------------------------
# Cargar datos
# ------------------------------------------------------------------
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# ------------------------------------------------------------------
# Normalizar columna SERIE en df_detalle
# ------------------------------------------------------------------
if df_detalle is not None:
    df_detalle["SERIE"] = (
        df_detalle["SERIE"]
        .astype(str)
        .str.replace(",", "", regex=False)
    )

# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------
st.title("FASTRACK")
st.subheader("CONSULTA DE CILINDROS POR CLIENTE")

if df_proceso is not None:
    clientes_unicos = df_proceso["CLIENTE"].unique()
    cliente_seleccionado = st.selectbox(
        "Seleccione el cliente:", clientes_unicos
    )
else:
    cliente_seleccionado = None

# ------------------------------------------------------------------
# Botón de búsqueda
# ------------------------------------------------------------------
if st.button("Buscar Cilindros del Cliente"):
    if cliente_seleccionado:
        ids_procesos_cliente = df_proceso.loc[
            df_proceso["CLIENTE"] == cliente_seleccionado, "IDPROC"
        ]
        df_cilindros_cliente = df_detalle[
            df_detalle["IDPROC"].isin(ids_procesos_cliente)
        ]

        df_procesos_filtrados = df_proceso[
            df_proceso["IDPROC"].isin(df_cilindros_cliente["IDPROC"])
        ].sort_values(by=["FECHA", "HORA"])

        df_ultimos_procesos = df_procesos_filtrados.drop_duplicates(
            subset="IDPROC", keep="last"
        )

        cilindros_en_cliente = df_ultimos_procesos[
            df_ultimos_procesos["PROCESO"].isin(["DESPACHO", "ENTREGA"])
        ]

        ids_cilindros_en_cliente = df_cilindros_cliente[
            df_cilindros_cliente["IDPROC"].isin(cilindros_en_cliente["IDPROC"])
        ].merge(
            df_ultimos_procesos[["IDPROC", "FECHA"]],
            on="IDPROC",
            how="left",
        )

        # ----------------------------------------------------------
        # Mostrar resultados y botón de descarga
        # ----------------------------------------------------------
        if not ids_cilindros_en_cliente.empty:
            st.write(
                f"Cilindros actualmente en el cliente: {cliente_seleccionado}"
            )
            st.dataframe(
                ids_cilindros_en_cliente[["SERIE", "IDPROC", "FECHA"]]
            )

            # ▶️ Función de conversión a CSV+bytes
            def convert_to_csv(df: pd.DataFrame) -> bytes:
                return df.to_csv(index=False).encode("utf-8")

            # ▶️ Botón de descarga
            st.download_button(
                label="⬇️ Descargar resultados en CSV",
                data=convert_to_csv(ids_cilindros_en_cliente),
                file_name=f"cilindros_{cliente_seleccionado}.csv",
                mime="text/csv",
            )
        else:
            st.warning("No se encontraron cilindros en el cliente seleccionado.")
    else:
        st.warning("Por favor, seleccione un cliente.")
