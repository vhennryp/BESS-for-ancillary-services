import os
import opendssdirect as dss
import numpy as np
import pandas as pd
import warnings
from sklearn.preprocessing import MinMaxScaler

# Ajustar opciones de visualización de pandas para mostrar el DataFrame completo en una sola línea
[pd.set_option(option, None) for option in ['display.max_rows', 'display.max_columns', 'display.width', 'display.max_colwidth']]
pd.set_option('display.float_format', '{:.4f}'.format)
warnings.filterwarnings("ignore", message="The 'delay_after_gen' parameter is deprecated")

def f_PJM_buses():
    # print("Master.dss\n... Ejecutando ...")

    # Ruta de los archivos requeridos
    required_files_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Required_Files')
    script_path = os.path.dirname(os.path.abspath(__file__))

    # Compilar y resolver el archivo Master.dss
    dss_file = os.path.join(required_files_path, 'Master.dss')
    dss.Command(f"compile [{dss_file}]")
    dss.Command("Solve")

    # Definir tolerancia para aproximación
    tolerance = 0.01

    # Función para obtener y mostrar las pérdidas totales del sistema en kW
    def get_total_losses_kw():
        losses = dss.Circuit.Losses()
        total_losses_kw = losses[0] / 1000  # Convertir de W a kW
        return total_losses_kw

    # Obtener las pérdidas iniciales del sistema
    initial_losses_kw = get_total_losses_kw()

    # Obtener y mostrar todas las propiedades asociadas a cada bus
    all_buses = dss.Circuit.AllBusNames()
    bus_data = []
    suitable_buses = []

    # print("Propiedades de cada bus en el sistema:")

    for bus in all_buses:
        dss.Circuit.SetActiveBus(bus)
        base_kv_phase = dss.Bus.kVBase()  # Tensión base (LN)
        num_phases = dss.Bus.NumNodes()  # Número de nodos (puede indicar el número de fases)
        
        # Determinar la tensión de línea basada en el número de fases
        if num_phases == 3:
            base_kv_line = base_kv_phase * np.sqrt(3)  # Sistema trifásico
        else:
            base_kv_line = base_kv_phase  # Para sistemas monofásicos o bifásicos, no se aplica la raíz de 3
        
        coord_x = dss.Bus.X()
        coord_y = dss.Bus.Y()
        
        bus_data.append({
            "Bus": bus,
            "Base kV (fase)": base_kv_phase,
            "Base kV (línea)": base_kv_line,
            "Número de nodos (fases)": num_phases,
            "Coordenada X": coord_x,
            "Coordenada Y": coord_y
        })
        
        # Determinar si el nodo es adecuado
        #if any(abs(base_kv_line - target) < tolerance for target in [0.208, 13.8]) and num_phases == 3:
        if any(abs(base_kv_line - target) < tolerance for target in [13.8]) and num_phases == 3:    
            suitable_buses.append({
                "Bus": bus,
                "Base kV (fase)": base_kv_phase,
                "Base kV (línea)": base_kv_line,
                "Número de nodos (fases)": num_phases,
                "Coordenada X": coord_x,
                "Coordenada Y": coord_y
            })

    # Crear DataFrame de todos los buses
    bus_data_df = pd.DataFrame(bus_data)

    # Crear DataFrame de nodos adecuados
    suitable_buses_df = pd.DataFrame(suitable_buses)

    # print(f"\nNodos adecuados para la instalación de BESS:\n{suitable_buses_df}")

    # Crear la carpeta "Output_Buses" en la ubicación del script si no existe
    output_folder = os.path.join(script_path, 'Output_Buses')
    os.makedirs(output_folder, exist_ok=True)

    # Guardar los DataFrames en archivos Excel en la carpeta "Output_Buses"
    bus_data_file_path = os.path.join(output_folder, 'All_Buses.xlsx')
    suitable_buses_file_path = os.path.join(output_folder, 'Suitable_Buses.xlsx')

    

    # print(f"All buses saved to {bus_data_file_path}")
    # print(f"Suitable buses saved to {suitable_buses_file_path}")

    # Extraer la parte numérica y crear una nueva columna 'Bus_num'
    suitable_buses_df['Bus_num'] = suitable_buses_df['Bus'].str.extract(r'(\d+)', expand=False)

    # Rellenar los valores NaN (como los que provienen de 'bus_xfmr') con 0
    suitable_buses_df['Bus_num'] = suitable_buses_df['Bus_num'].fillna(0).astype(int)

    # Ordenar el DataFrame en base a 'Bus_num'
    suitable_buses_df = suitable_buses_df.sort_values(by='Bus_num')

    # Opcional: Reiniciar el índice si lo deseas
    suitable_buses_df = suitable_buses_df.reset_index(drop=True)


    # print(f"bus_data_df: \n{bus_data_df}")
    # print(f"suitable_buses_df: \n{suitable_buses_df}")

    bus_data_df.to_excel(bus_data_file_path, index=False, float_format="%.4f")
    suitable_buses_df.to_excel(suitable_buses_file_path, index=False, float_format="%.4f")
    
    return bus_data_df, suitable_buses_df


bus_data_df, suitable_buses_df = f_PJM_buses()

# # print(f"bus_data_df: \n{bus_data_df}")
# print(f"suitable_buses_df AFTER: \n{suitable_buses_df}")

# # # Llamada a la función y obtener los DataFrames
# # bus_data_df, suitable_buses_df = f_PJM_buses()
