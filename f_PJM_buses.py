import os
import opendssdirect as dss
import numpy as np
import pandas as pd
import warnings
from sklearn.preprocessing import MinMaxScaler

# Ajustar opciones de visualizaciÃ³n de pandas para mostrar el DataFrame completo en una sola lÃ­nea
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

    # Definir tolerancia para aproximaciÃ³n
    tolerance = 0.01

    # FunciÃ³n para obtener y mostrar las pÃ©rdidas totales del sistema en kW
    def get_total_losses_kw():
        losses = dss.Circuit.Losses()
        total_losses_kw = losses[0] / 1000  # Convertir de W a kW
        return total_losses_kw

    # Obtener las pÃ©rdidas iniciales del sistema
    initial_losses_kw = get_total_losses_kw()

    # Obtener y mostrar todas las propiedades asociadas a cada bus
    all_buses = dss.Circuit.AllBusNames()
    bus_data = []
    suitable_buses = []

    # print("Propiedades de cada bus en el sistema:")

    for bus in all_buses:
        dss.Circuit.SetActiveBus(bus)
        base_kv_phase = dss.Bus.kVBase()  # TensiÃ³n base (LN)
        num_phases = dss.Bus.NumNodes()  # NÃºmero de nodos (puede indicar el nÃºmero de fases)
        
        # Determinar la tensiÃ³n de lÃ­nea basada en el nÃºmero de fases
        if num_phases == 3:
            base_kv_line = base_kv_phase * np.sqrt(3)  # Sistema trifÃ¡sico
        else:
            base_kv_line = base_kv_phase  # Para sistemas monofÃ¡sicos o bifÃ¡sicos, no se aplica la raÃ­z de 3
        
        coord_x = dss.Bus.X()
        coord_y = dss.Bus.Y()
        
        bus_data.append({
                "bus": bus,
                "base_kv_phase": base_kv_phase,
                "base_kv_phase": base_kv_line,
                "num_phases": num_phases,
                "coord_x": coord_x,
                "coord_y": coord_y
        })
        
        # Determinar si el nodo es adecuado
        #if any(abs(base_kv_line - target) < tolerance for target in [0.208, 13.8]) and num_phases == 3:
        if any(abs(base_kv_line - target) < tolerance for target in [13.8]) and num_phases == 3:    
            suitable_buses.append({
                "bus": bus,
                "base_kv_phase": base_kv_phase,
                "base_kv_line": base_kv_line,
                "num_phases": num_phases,
                "coord_x": coord_x,
                "coord_y": coord_y
            })

    # Crear DataFrame de todos los buses
    bus_data_df = pd.DataFrame(bus_data)

    # Crear DataFrame de nodos adecuados
    suitable_buses_df = pd.DataFrame(suitable_buses)

    # print(f"\nNodos adecuados para la instalaciÃ³n de BESS:\n{suitable_buses_df}")
    # Extraer la parte numÃ©rica y crear una nueva columna 'Bus_num'
    suitable_buses_df['Bus_num'] = suitable_buses_df['bus'].str.extract(r'(\d+)', expand=False)

    # Rellenar los valores NaN (como los que provienen de 'bus_xfmr') con 0
    suitable_buses_df['Bus_num'] = suitable_buses_df['Bus_num'].fillna(0).astype(int)

    # Ordenar el DataFrame en base a 'Bus_num'
    suitable_buses_df = suitable_buses_df.sort_values(by='Bus_num')

    # Opcional: Reiniciar el Ã­ndice si lo deseas
    suitable_buses_df = suitable_buses_df.reset_index(drop=True)


    # print(f"bus_data_df: \n{bus_data_df}")
    # print(f"suitable_buses_df: \n{suitable_buses_df}")
    
    return bus_data_df, suitable_buses_df


bus_data_df, suitable_buses_df = f_PJM_buses()

# # print(f"bus_data_df: \n{bus_data_df}")
# print(f"suitable_buses_df AFTER: \n{suitable_buses_df}")

# # # Llamada a la funciÃ³n y obtener los DataFrames
# # bus_data_df, suitable_buses_df = f_PJM_buses()

