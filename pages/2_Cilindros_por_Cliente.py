import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd

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
        scopes = ["https://www.googleapis.com/auth/spreadsheets", 
                  "https://www.googleapis.com/auth/drive"]

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

# -----------------------------------------------------------------------
# NORMALIZACIÓN DE LA COLUMNA "SERIE" EN df_detalle
# -----------------------------------------------------------------------
if df_detalle is not None:
    df_detalle["SERIE"] = df_detalle["SERIE"].astype(str)              # Convertir todo a texto
    df_detalle["SERIE"] = df_detalle["SERIE"].str.replace(",", "", regex=False)
# -----------------------------------------------------------------------

# Título de la aplicación
st.title("Demo TrackerCyl")

# Subtítulo de la aplicación
st.subheader("CONSULTA DE CILINDROS POR CLIENTE")

# Campo desplegable para seleccionar el cliente
if df_proceso is not None:
    clientes_unicos = df_proceso["CLIENTE"].unique()
    cliente_seleccionado = st.selectbox("Seleccione el cliente:", clientes_unicos)
else:
    cliente_seleccionado = None

# Botón de búsqueda
if st.button("Buscar Cilindros del Cliente"):
    if cliente_seleccionado:
        # Filtrar las transacciones asociadas al cliente seleccionado
        ids_procesos_cliente = df_proceso[df_proceso["CLIENTE"] == cliente_seleccionado]["IDPROC"]
        df_cilindros_cliente = df_detalle[df_detalle["IDPROC"].isin(ids_procesos_cliente)]

        # Ordenar las transacciones por fecha y hora
        df_procesos_filtrados = df_proceso[
            df_proceso["IDPROC"].isin(df_cilindros_cliente["IDPROC"])
        ].sort_values(by=["FECHA", "HORA"])

        # Conservar sólo el último registro por cada DOCUMENTO
        df_ultimos_procesos = df_procesos_filtrados.drop_duplicates(subset="IDPROC", keep="last")

        # Filtrar los cilindros cuyo último proceso sea "DESPACHO" o "ENTREGA"
        cilindros_en_cliente = df_ultimos_procesos[
            df_ultimos_procesos["PROCESO"].isin(["DESPACHO", "ENTREGA"])
        ]

        # Filtrar los registros de df_detalle que coincidan
        ids_cilindros_en_cliente = df_cilindros_cliente[
            df_cilindros_cliente["IDPROC"].isin(cilindros_en_cliente["IDPROC"])
        ]

        # Agregar la fecha del último proceso
        ids_cilindros_en_cliente = ids_cilindros_en_cliente.merge(
            df_ultimos_procesos[['IDPROC', 'FECHA']], 
            on='IDPROC', 
            how='left'
        )

        # Mostrar los cilindros en el cliente
        if not ids_cilindros_en_cliente.empty:
            st.write(f"Cilindros actualmente en el cliente: {cliente_seleccionado}")
            st.dataframe(ids_cilindros_en_cliente[["SERIE", "IDPROC", "FECHA"]])
        else:
            st.warning("No se encontraron cilindros en el cliente seleccionado.")
    else:
        st.warning("Por favor, seleccione un cliente.")
