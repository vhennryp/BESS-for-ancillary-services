def f_BESS_Sv_PS(P_BESS, E_BESS, n_dc, n_ch, BatteryNode, primera_hora, ultima_hora, annual_discount_rate, SoC_i):

    Svc = 'PS'

    # Operational policies shared by FR, PS, and STK.
    # Keep these IDs synchronized with df_info_STK['name_policy'].
    OPERATIONAL_POLICIES = {
        1: 'Daily charging',
        2: 'Idle',
        3: 'Peak-shaving service',
        4: 'Frequency regulation service',
        5: 'Attaining SOC objective',
    }
    ACTIVE_POLICIES_BY_SERVICE = {
        'FR':  (2, 4, 5),
        'PS':  (1, 2, 3),
        'STK': (1, 2, 3, 4, 5),
    }
    ACTIVE_POLICIES = ACTIVE_POLICIES_BY_SERVICE[Svc]
    # Policies not listed in ACTIVE_POLICIES remain visible below as commented
    # blocks so the three service files keep the same operating-policy layout.

    import matplotlib
    import matplotlib.pyplot as plt
    # matplotlib.use('Agg')                                               # Para no mostrar la gráfica en pantalla
    import scipy.io
    import opendssdirect as dss
    import pathlib
    import numpy as np
    import sys
    import os
    import pandas as pd
    import time

    from os.path import expanduser
    from matplotlib.collections import LineCollection
    from datetime import datetime

    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    start_time = time.time()  # Iniciar el cronómetro

    print("🔹" * 40)     
    print(f"Start Time\t: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    ###########################################################################################################################
    ######################  F R : R E Q U I R E D   F I L E S 
    ###########################################################################################################################    
    
    # Crear la carpeta Output_Images si no existe
    if not os.path.exists('Output_Images'):
        os.makedirs('Output_Images')

    # Ruta de los archivos CSV
    required_files_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Required_Files')
    freq_csv_file_path = os.path.join(required_files_path, 'PJM_2017_freq_2s_to_6min.csv')
    prices_csv_file_path = os.path.join(required_files_path, 'PJM_2017_prices_1h.csv')

    # Cargar los datos de los archivos CSV con encabezados
    MR_freq = pd.read_csv(freq_csv_file_path, header=None, names=['Frequency'])
    MR_prices = pd.read_csv(prices_csv_file_path, header=None, names=['Price'])
    
    ###########################################################################################################################
    ######################  F R : P A R A M E T R O S  
    ###########################################################################################################################    
    
 
    # -------- PARAMETROS DEL MERCADO
    t_btw_rf = 360               # Tiempo entre analisis de datos (analisis de datos cada dos segundos)
    P_bid_min = 100              # kW
     
    SoC_obj = 0.5                # SoC Objetive: Permite controlar y gestionar de manera más efectiva la operación de la batería
    E_BESS_obj = SoC_obj*E_BESS
    b = 0                        # Tasa Autodescarga por Hora  

    # -------- CONDICIONES INICIALES ------------
    SoC_f = SoC_i            # SoC_f Inicial
    E_BESS_i = SoC_i*E_BESS  # Dependiente de E_BESS_i Inicial
    P_bid_h = P_bid_min      # kW
    E_BESS_ch_2 = 0          # kWh de la siguiente hora cargada para analizar CARGA o DESCARGA
    f_dc = 1                 # Variable Binaria BESS
    f_ch = 0                 # Variable Binaria BESS

    # ---------------- ACUMULADORES ----------------

    Col_E_BESS_t_h = [] #>>>>>>>>>> Usado para calcular los revenues
  
    ###########################################################################################################################
    ######################  P S : P A R A M E T R O S  
    ###########################################################################################################################
    
    print(f"... Executing ... f_BESS_Sv2_PS ")

    # -------- PARAMETROS DEL MERCAD
    t_btw_rf = 360                     # Tiempo entre analisis de datos (analisis de datos cada dos segundos)
    P_bid_min = 100                  # kW

    SoC_obj = 0.5                    # SoC Objetive: Permite controlar y gestionar de manera más efectiva la operación de la batería
    E_BESS_obj = SoC_obj*E_BESS
    b = 0.00                         # Tasa Autodescarga por Hora

    PS_SoC_max = 0.90
    # BESS_SoC_min = 0.20

    # -------- CONDICIONES INICIALES ------------
    SoC_i = SoC_i                    # SoC_i Inicial
    # SoC_i = 0.82                   # SoC_i Inicial
    SoC_f = SoC_i                    # SoC_f Inicial
    E_BESS_i = SoC_i*E_BESS          # Dependiente de E_BESS_i Inicial
    P_bid_h = 100                    # kW
    E_BESS_ch_2 = 0                  # kWh de la siguiente hora cargada para analizar CARGA o DESCARGA
    f_dc = 1                         # Variable Binaria BESS
    f_ch = 0                         # Variable Binaria BESS

    # ---------------- VARIABLES ----------------
    S_E_BESS_t_h = 0
    SoC_evaluator = 0
    # ---------------- COLECTORES ----------------

    Col_P_bid_h = []
    Col_SoC     = []
    P_BESS_bhv  = []                  # BESS Behaviour
    P_BESS_t = []

    # = = = = = = = = = = = = = = = = = = = C H A P T E R : II  = = = = = = = = = = = = = = = = = = = =
    # ------------- 1. READ  DATA PJM 240 NODOS

    script_path = os.path.dirname(os.path.abspath(__file__))
    required_files_path = os.path.join(script_path, 'Required_Files') 

    # Rutas de los archivos en la carpeta 'Required_Files'
    Temp_FeederA_P = os.path.join(required_files_path, 'FeederA_P_origen.xlsx')
    df = pd.read_excel(Temp_FeederA_P, header=None)
    FeederA_P = df.to_numpy()

    Temp_FeederA_Q = os.path.join(required_files_path,  'FeederA_Q_origen.xlsx')
    df = pd.read_excel(Temp_FeederA_Q, header=None)
    FeederA_Q = df.to_numpy()

    Temp_FeederB_P = os.path.join(required_files_path,  'FeederB_P_origen.xlsx')
    df = pd.read_excel(Temp_FeederB_P, header=None)
    FeederB_P = df.to_numpy()

    Temp_FeederB_Q = os.path.join(required_files_path,  'FeederB_Q_origen.xlsx')
    df = pd.read_excel(Temp_FeederB_Q, header=None)
    FeederB_Q = df.to_numpy()

    Temp_FeederC_P = os.path.join(required_files_path,  'FeederC_P_origen.xlsx')
    df = pd.read_excel(Temp_FeederC_P, header=None)
    FeederC_P = df.to_numpy()

    Temp_FeederC_Q = os.path.join(required_files_path,  'FeederC_Q_origen.xlsx')
    df = pd.read_excel(Temp_FeederC_Q, header=None)
    FeederC_Q = df.to_numpy()

    # ------------- 3. COMPILAR OPENDSS
    script_path = os.path.dirname(os.path.abspath(__file__)) 
    dss_file = os.path.join(required_files_path, 'Master.dss')
    dss.Command(f"compile [{dss_file}]")
    
    

    #------------- POLITICA I: Variables Temporales -------------- #

    # ------------- INFORMATION CB

    # // This file is to define the parameters of circuit breakers.

    # //---------------------Circuit Breakers of Feeder A----------------------// 
    # New Line.CB_101  Phases=3  Bus1=bus1.1.2.3   Bus2=bus1001.1.2.3  Switch=y  r1=1e-4  r0=1e-4  x1=0  x0=0  c1=0  c0=0
    # New Line.CB_102  Phases=3  Bus1=bus1010.1.2.3   Bus2=bus1010.4.5.6  Switch=y  r1=1e-4  r0=1e-4  x1=0  x0=0  c1=0  c0=0   ! Bus2 is supposed to connect to bus2057.1.2.3 when reconfiguring, normally open
    # ! Circuit breaker name, number of phases, 1st bus, 2nd bus, this line is a switch, positive-sequence resistance per uint length, zero-sequence resistance per uint length, positive-sequence reactance per uint length, zero-sequence reactance per uint length, positive-sequence capacitance per uint length, zero-sequence capacitance per uint length. Note that we use Bus2=bus2057.4.5.6 to achieve a normally open circuit breaker, i.e. connecting the energized nodes (bus1010.1.2.3) to non-energized nodes (bus2057.4.5.6).

    # //---------------------Circuit Breakers of Feeder B----------------------// 
    # New Line.CB_201  Phases=3  Bus1=bus1.1.2.3      Bus2=bus2001.1.2.3  Switch=y  r1=1e-4  r0=1e-4  x1=0  x0=0  c1=0  c0=0
    # New Line.CB_202  Phases=3  Bus1=bus2012.1.2.3   Bus2=bus2013.1.2.3  Switch=y  r1=1e-4  r0=1e-4  x1=0  x0=0  c1=0  c0=0
    # New Line.CB_203  Phases=3  Bus1=bus2021.1.2.3   Bus2=bus2026.1.2.3  Switch=y  r1=1e-4  r0=1e-4  x1=0  x0=0  c1=0  c0=0
    # New Line.CB_204  Phases=3  Bus1=bus2013.1.2.3   Bus2=bus2013.4.5.6  Switch=y  r1=1e-4  r0=1e-4  x1=0  x0=0  c1=0  c0=0  ! Bus2 is supposed to connect to bus3005.1.2.3 when reconfiguring, normally open

    # //---------------------Circuit Breakers of Feeder C----------------------// 
    # New Line.CB_301  Phases=3  Bus1=bus1.1.2.3      Bus2=bus3001.1.2.3  Switch=y  r1=1e-4  r0=1e-4  x1=0  x0=0  c1=0  c0=0
    # New Line.CB_302  Phases=3  Bus1=bus3075.1.2.3   Bus2=bus3076.1.2.3  Switch=y  r1=1e-4  r0=1e-4  x1=0  x0=0  c1=0  c0=0
    # New Line.CB_303  Phases=3  Bus1=bus3081.1.2.3   Bus2=bus3081.4.5.6  Switch=y  r1=1e-4  r0=1e-4  x1=0  x0=0  c1=0  c0=0   ! Bus2 is supposed to connect to bus2016.1.2.3 when reconfiguring, normally open

    # Definir valores predeterminados
    CB_Monitored = "Line.CB_101"
    threshold_peak_demand = 800  # Valor predeterminado

    # Verificar condiciones
    if BatteryNode.startswith('bus1'):
        CB_Monitored = "Line.CB_101"
        threshold_peak_demand = 170 #170  # kW

    elif BatteryNode.startswith('bus2'):
        node_number = int(BatteryNode[4:])  # Extraer la parte numérica correctamente
        if 1 <= node_number <= 12:
            CB_Monitored = "Line.CB_201"
            threshold_peak_demand = 710  # kW
        elif 14 <= node_number <= 21:
            CB_Monitored = "Line.CB_202"
            threshold_peak_demand = 540  # kW
        elif 26 <= node_number <= 999:
            CB_Monitored = "Line.CB_203"
            threshold_peak_demand = 480  # kW

    elif BatteryNode.startswith('bus3'):
        node_number = int(BatteryNode[4:])  # Extraer la parte numérica correctamente
        if 1 <= node_number <= 75:
            CB_Monitored = "Line.CB_301"
            threshold_peak_demand = 1500  # kW
        elif 76 <= node_number <= 999:  # Incluye bus3076
            CB_Monitored = "Line.CB_302"
            threshold_peak_demand = 800  # kW

    # Ahora siempre tendrá un valor
    # threshold_peak_demand = threshold_peak_demand
    print(f"CB_Monitored: {CB_Monitored}")
    P_3f_cb_302_previous_data = 0                 # kW
    num_hrs_BESS_ch = E_BESS//P_BESS                # Número de horas para cargar la BESS
    num_hrs_BESS_ch = 10
    hrs_in_year = list(range(0, 8760))
    hrs_day_starts = hrs_in_year[::24]

    hrs_in_year = list(range(0, 8760))
    hrs_day_starts = hrs_in_year[::24]
    n = num_hrs_BESS_ch                             # Número de elementos consecutivos a generar

    # Crear una nueva lista donde cada elemento de hrs_day_starts tiene añadidos sus n consecutivos sin incluir el elemento inicial (la semilla)

    expanded_list = []
    for start in hrs_day_starts:
        expanded_list.extend(range(start, start + n))

    hrs_day_starts = expanded_list
    
    List_P_3f_cb_302_dat = []

    # ------------   5.	SPECIFY LOAD BUSES (BUSES WITH LOAD)  

    FeederA_bus_with_load = list(range(1003, 1018))     # Buses of Feeder A that have loads
    FeederB_bus_with_load = list(range(2002, 2004)) + [2005] + list(range(2008, 2012)) + list(range(2014, 2019)) + [2020] + list(range(2022, 2026)) + list(range(2028, 2033)) + list(range(2034, 2036)) + [2037] + list(range(2040, 2044)) + list(range(2045, 2057)) + list(range(2058, 2061))  # Buses of Feeder B that have loads
    FeederC_bus_with_load = ([3002, 3004] + list(range(3006, 3008)) + list(range(3009, 3015)) + list(range(3016, 3022)) + list(range(3023, 3030)) + list(range(3031, 3040)) + list(range(3041, 3046)) + list(range(3047, 3053)) + [3054] + list(range(3056, 3068)) + list(range(3070, 3075)) + [3077, 3078, 3081] + list(range(3083, 3092)) + list(range(3093, 3100)) + list(range(3101, 3107)) + list(range(3108, 3113)) + list(range(3114, 3118)) + list(range(3120, 3133)) + list(range(3134, 3139)) + list(range(3141, 3156)) + list(range(3157, 3163)))

    # ------------   6. SOLVE QUASI-STATIC TIME-SERIES POWER FLOW VIA Opendssdirect AND COLLECT RESULTS   ------------- #

    E_BESS_h = E_BESS * 0.5

    primera_fila = primera_hora - 1               # 1st hour , row 0 reflects hour 1
    ultima_fila = ultima_hora - 1                # Lst hour , row 8759 reflects hour 8760

    E_BESS_f = E_BESS_i    

    # ------------   POLICY I: Charge the BESS in the first 6 hrs of the day.

    # ------------   Variables de Iniciación
    first_print = True
    second_print = True
    thrird_print = True
    first_run = True 

    df_info_STK = pd.DataFrame(columns=['hr', 'Col_SoC', 'P_BESS_t', 'name_policy', 'P_3f_cb_302'])
    name_policy = 0
    insp = False
    pk_sh_P = 0
    P_BESS_t = 0 
    
    # ------------   STK: Parámetros
    
    botom_ch_dayly = 0
    P_bid_Chosen = P_BESS
    SoC = SoC_i
    PS_P_max = 1000
    P_BESS_t = 0
    pk_sh_P = 0
    
    # ------------   FR: FMR Rules
    FRM_E_min = 100
    E_BESS_max_FR = E_BESS - FRM_E_min
    E_BESS_min_FR = FRM_E_min
    
    # FR_SoCmin = 0.18
    # FR_SoCmax = 0.82
    
    FR_SoCmin = 0.10
    FR_SoCmax = 0.90
    
    SW_FR_SoCmin = 0
    SW_FR_SoCmax = 0

    SW_FR = 0
    SW_PS = 0 
    PS_insp = 0
    
    FR_lim_min_SoC =  P_BESS / E_BESS
    FR_lim_max_SoC = 1 - FR_lim_min_SoC
    
    Svc_NOT = 1

    # +++++++++++++++++++++++++++ 6.1  BESS INSTALLATION ++++++++++++++++++++++++++++
                
    BatteryPower = P_BESS #kW
    dss.Command(f"New Load.BESS_PJM_FRM Bus1={BatteryNode} Phases=2 Conn=Wye Model=1 kV=13.8 kW={BatteryPower} kVAR=1 Vmaxpu=1.10 Vminpu=0.90")
    #dss.Command(f"New Load.BESS_PJM_FRM Bus1={BatteryNode} Phases=1 Conn=Wye Model=1 kV=13.8 kW={BatteryPower} kVAR=1 Vmaxpu=1.10 Vminpu=0.90")
    BESS_name = dss.Loads.Name()

    # +++++++++++++++++++++++++++ ACTIVATED SERVICES ++++++++++++++++++++++++++++

    SW_FR == 1 

    # ------------   DSS: All Buses
    all_buses = dss.Circuit.AllBusNames()
    all_lines = dss.Lines.AllNames()

    # ------------   Funciones Necesarias

    def calcular_rms(voltajes, num_fases):
        if num_fases == 1:
            # Calcular el valor RMS para una fase
            return (voltajes[0]**2 + voltajes[1]**2)**0.5
        elif num_fases == 2:
            # Calcular el valor RMS para dos fases
            V1 = (voltajes[0]**2 + voltajes[1]**2)**0.5
            V2 = (voltajes[2]**2 + voltajes[3]**2)**0.5
            return ((V1**2 + V2**2) / 2)**0.5
        elif num_fases == 3 or num_fases == 6:
            # Calcular el valor RMS para tres fases
            V1 = (voltajes[0]**2 + voltajes[1]**2)**0.5
            V2 = (voltajes[2]**2 + voltajes[3]**2)**0.5
            V3 = (voltajes[4]**2 + voltajes[5]**2)**0.5
            return ((V1**2 + V2**2 + V3**2) / 3)**0.5
        else:
            return None  # Para casos no previstos

    # ------------   7. ITERATE THROUGH THE DATA AND ACTIVATE THE POLICIES
    #print(f"primera_fila: {primera_fila}\tultima_fila: {ultima_fila}")
    
    for h in range(primera_fila, ultima_fila + 1):

        print(f"Hora: {h}")
        
        # ------------ PS: Inspeción de la Política III
        
        PS_insp = 0
        
        if name_policy == 3:
            insp = True                                                   # Variable de inspección para el comienzo de la ejecución de Política III

        for k in range(1, len(FeederA_bus_with_load) + 1):
            bus_num = FeederA_bus_with_load[k - 1]
            dss.Command(f"Edit Load.Load_{bus_num} kW={FeederA_P[h, bus_num - 1000 - 1]} kvar={FeederA_Q[h, bus_num - 1000 - 1]}")
        for k in range(1,len(FeederB_bus_with_load) + 1):
            bus_num = FeederB_bus_with_load[k - 1]
            dss.Command(f"Edit Load.Load_{bus_num} kW={FeederB_P[h, bus_num - 2000 - 1]} kvar={FeederB_Q[h, bus_num - 2000 - 1]} ")
        for k in range(1,len(FeederC_bus_with_load) + 1):
            bus_num = FeederC_bus_with_load[k - 1]
            dss.Command(f"Edit Load.Load_{bus_num} kW={FeederC_P[h, bus_num - 3000 - 1]} kvar={FeederC_Q[h, bus_num - 3000 - 1]} ")
        
        # ------------   FR: P bid
        
        P_bid_h = min(min(SoC * E_BESS * 1, (1 - SoC) * E_BESS * 1),P_BESS)  # Atengo con el SoC_f
        
        # ------------ Switches
        if  P_bid_h >= P_bid_min:
            SW_FR = 1
        else:
            SW_FR = 0
        
        if  P_3f_cb_302_previous_data >= threshold_peak_demand:
            SW_PS = 1 
            SW_FR = 0
        else:
            SW_PS = 0 
        
        if h % 24 == 0 :
            botom_ch_dayly = 0   

        if  SoC == PS_SoC_max:
            botom_ch_dayly = 1  

        # ------------   FR: Variables de Iniciación 
        
        # Iteración de 10 datos por Hora
        primer_min_h = h * 10 + 1                                         # 1er min. de la h. iterada
        ultimo_min_h = (h + 1) * 10
        #print(f"primer_min_h: {primer_min_h}\tultimo_min_h: {ultimo_min_h}")
        for num_dato in range(primer_min_h, ultimo_min_h + 1):

                    # < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <  START ACTIVATION : PARAMETERS 
                    #region 
                    # -------------------- CB_305 Monitoring
                    dss.Command(f"Edit Load.BESS_PJM_FRM kW=0")
                    dss.Command("Solve")

                    dss.Circuit.SetActiveElement(f"{CB_Monitored}")     # Activation of Line.cb_302
                    P_3f_cb_302_BESS_0 = dss.CktElement.Powers()[0] + dss.CktElement.Powers()[2] + dss.CktElement.Powers()[4]  
                    df_info_STK.at[num_dato, 'P_3f_cb_302_BESS_0'] = P_3f_cb_302_BESS_0
                    PS_peak_num_dato = P_3f_cb_302_BESS_0
                    # print(f"num_dato: {num_dato}\tPS_peak_num_dato: {PS_peak_num_dato}")
                    # input("Press Enter to continue...")
                    DSS_Total_Looses = dss.Circuit.Losses()[0] 
                    df_info_STK.at[num_dato, 'DSS_Total_Looses'] = DSS_Total_Looses

                    df_info_STK.at[num_dato, 'hr'] = h

                    buses_data = [] #<<<<<<<<<<<<<<<<<< Inicializacion de una lista colectora que tiene que ser vaciada en cada iteración

                    for bus in all_buses:
                        dss.Circuit.SetActiveBus(bus)  # Seleccionar el bus activo
                        voltages  = dss.Bus.PuVoltage()  # Obtener las tensiones en pu y los angulos correspondientes
                        kvBase    = dss.Bus.kVBase()  # Obtener el kV base del bus
                        numPhases = dss.Bus.NumNodes()  # Obtener el número de fases/nodos del bus
                        
                        properties = {
                            "Bus_Name"  : bus,
                            "Num_fases" : numPhases,
                            "V_RMS"     : calcular_rms(voltages, numPhases) 
                        }
                        
                        buses_data.append(properties)

                    # Crear un DataFrame a partir de la lista de propiedades
                    df_voltage_droop = pd.DataFrame(buses_data)
                    
                    ######################################################################################################################
                    ############################# CURRENT ANAYLISIS

                    # Lista para almacenar los datos de las líneas
                    lines_data = []    
                    
                    for line in all_lines:
                        dss.Lines.Name(line)  # Seleccionar la línea activa por su nombre
                        
                        # Ahora trabajar con el CktElement correspondiente a la línea activa
                        seq_currents = dss.CktElement.SeqCurrents()  # Obtener las corrientes de secuencia (I1, I2, I0)
                        emerg_amps = dss.CktElement.EmergAmps()  # Obtener la corriente de emergencia
                        norm_amps = dss.CktElement.NormalAmps()  # Obtener la corriente nominal
                        currents = dss.CktElement.CurrentsMagAng()  # Obtener las corrientes en magnitud y ángulo


                        # Calcular los porcentajes
                        I0 = seq_currents[0]
                        I1 = seq_currents[1]
                        I2 = seq_currents[2]
                        percent_I2_I1 = (I2 / I1) * 100 if I1 != 0 and I1 != 1  else 0
                        percent_I0_I1 = (I0 / I1) * 100 if I1 != 0 and I1 != 1  else 0
                        
                        # Calcular los porcentajes de utilización en condiciones normales y de emergencia
                        current_magnitude = max([currents[i] for i in range(0, len(currents), 2)])  # Tomar la magnitud máxima
                        percent_normal = (current_magnitude / norm_amps) * 100 if norm_amps != 0 else 0
                        percent_emergency = (current_magnitude / emerg_amps) * 100 if emerg_amps != 0 else 0

                        properties = {
                                        "Line_Name": line,
                                                "I1": I1,
                                                "I2": I2,
                                                "p_I2_I1": percent_I2_I1,
                                                "I0": I0,
                                                "p_I0_I1": percent_I0_I1,
                                                "p_Normal": percent_normal,
                                                "p_Emergency": percent_emergency
                                    }

                        
                        
                        # Añadir el diccionario a la lista
                        lines_data.append(properties)

                    # Crear un DataFrame a partir de la lista de propiedades
                    df_line_currents = pd.DataFrame(lines_data)

                    ######################################################################################################################


                    # ------------   STK: Police Activation
                    activate_politica = 0

                    #endregion
                    # > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > FINISH ACTIVATION : PARAMETERS
                    
                    

                    # < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <  START ACTIVATION : STACKABLE
                    #region 
    
                    # # -------------------- FRM Violations
                    
                    # if SoC < FR_SoCmin and (num_dato - 1) % 10 == 0:
                    #     SW_FR_SoCmin = 1
                    # else:
                    #     SW_FR_SoCmin = 0
                    
                    # if SoC > FR_SoCmax and (num_dato - 1) % 10 == 0:
                    #     SW_FR_SoCmax = 1
                    # else:
                    #     SW_FR_SoCmax = 0

                    #endregion  
                    # > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > FINISH ACTIVATION : STACKABLE



                    # < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <  START ACTIVATION : PEAK-SHAVING
                    # #region 
                    if PS_peak_num_dato > threshold_peak_demand and SoC > FR_SoCmin and SoC <= FR_SoCmax :  # PS PRIORITY
                    #if PS_peak_num_dato > threshold_peak_demand_of: # FR PRIORITY    
                        SW_PS = 1

                    # if SoC < FR_SoCmin:
                    #         SW_PS_Rest = 1
                    #         SW_PS = 0

                    if P_3f_cb_302_BESS_0 > threshold_peak_demand:
                        SW_PS_Rest = 1
                    else:
                        SW_PS_Rest = 0

                    #endregion  
                    # > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > FINISH ACTIVATION : PEAK-SHAVING

                    if num_dato == 47353:
                            print(f"num_dato: {num_dato} activate_politica: {activate_politica} name_policy: {name_policy} ")


                    # # < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <  START ACTIVATION : PEAK SHAVING 
                    # # POLITICA III: Peak Shaving

                    if activate_politica == 0 and SW_PS == 1 and PS_peak_num_dato > threshold_peak_demand and SW_FR_SoCmax == 0 and SW_FR_SoCmin == 0:
                        if num_dato == 47353:
                            print("Entro en la POLITICA 3 ")


                        if num_dato == 47353:
                            print(f"2_activate_politica: {activate_politica}, SW_PS: {SW_PS}, PS_peak_num_dato > threshold_peak_demand: {PS_peak_num_dato > threshold_peak_demand}, SW_FR_SoCmax: {SW_FR_SoCmax}, SW_FR_SoCmin: {SW_FR_SoCmin}")

                        # if SoC < BESS_SoC_min:
                        #     print(f"Hora {h} - Activacion:{num_dato}")
                            

                        # else:
                        #     print(f"Hora {h} - Paso el límite inferior de SoC: {num_dato}")

                        # >>>>>>>>>>>>>>>>>>> Asignación de politica
                        name_policy = 3       
                        activate_politica = 1
                        #print(f"num_dato: {num_dato}, name_policy: {name_policy}, activate_politica: {activate_politica}")
                        # >>>>>>>>>>>>>>>>>>>
                        
                        
                        f_dc = 1
                        f_ch = 0
                        
                        
                        #PS_peak_num_dato
                        
                        if PS_insp == 0:
                            
                            P_BESS_t = 0
                            E_BESS_t = 0
                            E_BESS_f = E_BESS_i + E_BESS_t
                            SoC = E_BESS_f / E_BESS 
                            E_BESS_i = E_BESS_f 

                            
                            dss.Command(f"Edit Load.BESS_PJM_FRM kW={P_BESS_t}")
                            dss.Command("Solve")
                            dss.Circuit.SetActiveElement(f"{CB_Monitored}")    # Activation of Line.cb_302
                            P_3f_cb_302 = dss.CktElement.Powers()[0] + dss.CktElement.Powers()[2] + dss.CktElement.Powers()[4]   # Suma de las P de 3 fases del CB_302
                            DSS_Total_Looses_BESS = dss.Circuit.Losses()[0] 
                            
                            List_P_3f_cb_302_dat.append([P_3f_cb_302])
                            P_BESS_bhv.append(P_BESS_t)
                            Col_SoC.append(SoC)                                 # Almacena el valor actual de SoC en la lista
                            
                            # SW_FR_SoCmin = 1 if SoC < FR_SoCmin else 0
                            # SW_FR_SoCmax = 1 if SoC > FR_SoCmax else 0

                            if SoC < FR_SoCmin:
                                    SW_FR_SoCmin = 1
                                    SW_FR_SoCmax = 0
                                    
                            if SoC > FR_SoCmax:
                                    SW_FR_SoCmax = 1
                                    SW_FR_SoCmin = 0

                            P_bid_h = 0

                            # -------------------- START: Voltage Droop

                            buses_data = []

                            for bus in all_buses:
                                dss.Circuit.SetActiveBus(bus)  # Seleccionar el bus activo
                                voltages = dss.Bus.PuVoltage()  # Obtener las tensiones en pu
                                numPhases = dss.Bus.NumNodes()  # Obtener el número de fases/nodos del bus
                                rms_value = calcular_rms(voltages, numPhases)
                                buses_data.append(rms_value)
  
                            df_voltage_droop['V_RMS - 1'] = df_voltage_droop['V_RMS'] - 1
                            df_voltage_droop['V_RMS_BESS'] = buses_data                           
                            df_voltage_droop['V_RMS_BESS - 1'] = df_voltage_droop['V_RMS_BESS'] - 1
                            df_voltage_droop['Delta_V'] = (abs(1 - df_voltage_droop['V_RMS']) - abs(1 - df_voltage_droop['V_RMS_BESS'])) # / (1 - df_voltage_droop['V_RMS'])) * 100

                            # print(f"df_voltage_droop:\n{df_voltage_droop}")

                            # Ordenar el DataFrame por la columna 'Delta_V' de menor a mayor
                            df_voltage_droop = df_voltage_droop.sort_values(by='Delta_V', ascending=False)

                            # Calcular la desviación estándar ajustada respecto a 1 pu utilizando valor absoluto
                            desviacion_droop_antes = abs(df_voltage_droop['V_RMS'] - 1).std()
                            desviacion_droop_despues = abs(df_voltage_droop['V_RMS_BESS'] - 1).std()

                            f4_t = (desviacion_droop_despues - desviacion_droop_antes)/desviacion_droop_antes

                            

                            # ## #### #### #######################################

                            P_3f_cb_302 = threshold_peak_demand

                            pk_sh_P = PS_peak_num_dato - threshold_peak_demand 
                            
                            E_BESS_t = (f_ch) * (n_ch) * (t_btw_rf / 3600) * (pk_sh_P) + (f_dc) * (( t_btw_rf / 3600) * (- pk_sh_P) / (n_dc)) - E_BESS_i*b*(t_btw_rf / 3600)
                            P_BESS_t = (f_dc) * (n_dc) * E_BESS_t / ((t_btw_rf / 3600)) + (1/n_ch) * (f_ch)* E_BESS_t / ((t_btw_rf / 3600))

                            # ## #### #### #######################################

                            # -------------------- FINAL: Voltage Droop

                            df_info_STK.at[num_dato, 'hr'] = h
                            df_info_STK.at[num_dato, 'Col_SoC'] = SoC
                            df_info_STK.at[num_dato, 'P_BESS_t'] = P_BESS_t
                            df_info_STK.at[num_dato, 'name_policy'] = name_policy
                            df_info_STK.at[num_dato, 'P_3f_cb_302'] = P_3f_cb_302
                            df_info_STK.at[num_dato, 'switch_FR'] = SW_FR
                            df_info_STK.at[num_dato, 'P_bid_h'] = P_bid_h
                            df_info_STK.at[num_dato, 'switch_PS'] = SW_PS
                            df_info_STK.at[num_dato, 'PS_peak'] = PS_peak_num_dato
                            df_info_STK.at[num_dato, 'SW_FR_SoCmin'] = SW_FR_SoCmin
                            df_info_STK.at[num_dato, 'SW_FR_SoCmax'] = SW_FR_SoCmax
                            df_info_STK.at[num_dato, 'DSS_Total_Looses_BESS'] = DSS_Total_Looses_BESS
                            df_info_STK.at[num_dato, 'f4_t'] = f4_t

                            ######################################################################################################################
                            ############################# CURRENT ANAYLISIS

                            # Lista para almacenar los datos de las líneas
                            lines_data = []

                            for line in all_lines:
                                dss.Lines.Name(line)  # Seleccionar la línea activa por su nombre
                                
                                # Ahora trabajar con el CktElement correspondiente a la línea activa
                                seq_currents = dss.CktElement.SeqCurrents()  # Obtener las corrientes de secuencia (I1, I2, I0)
                                emerg_amps = dss.CktElement.EmergAmps()  # Obtener la corriente de emergencia
                                norm_amps = dss.CktElement.NormalAmps()  # Obtener la corriente nominal
                                currents = dss.CktElement.CurrentsMagAng()  # Obtener las corrientes en magnitud y ángulo
                                
                                # Calcular los porcentajes
                                I0 = seq_currents[0]
                                I1 = seq_currents[1]
                                I2 = seq_currents[2]
                                percent_I2_I1 = (I2 / I1) * 100 if I1 != 0 and I1 != 1  else 0
                                percent_I0_I1 = (I0 / I1) * 100 if I1 != 0 and I1 != 1  else 0
                                
                                # Calcular los porcentajes de utilización en condiciones normales y de emergencia
                                current_magnitude = max([currents[i] for i in range(0, len(currents), 2)])  # Tomar la magnitud máxima
                                percent_normal = (current_magnitude / norm_amps) * 100 if norm_amps != 0 else 0
                                percent_emergency = (current_magnitude / emerg_amps) * 100 if emerg_amps != 0 else 0

                                # Guardar las propiedades de la línea en un diccionario
                                properties = {
                                               "Line_Name_BESS": line,
                                                "I1_BESS": I1,
                                                "I2_BESS": I2,
                                                "p_I2_I1_BESS": percent_I2_I1,
                                                "I0_BESS": I0,
                                                "p_I0_I1_BESS": percent_I0_I1,
                                                "p_Normal_BESS": percent_normal,
                                                "p_Emergency_BESS": percent_emergency
                                }
                                    
                                # Añadir el diccionario a la lista
                                lines_data.append(properties)

                            df_line_currents_BESS = pd.DataFrame(lines_data)

                            ######################################################################################################################
                                                
                            PS_insp = 1
                            
                        else:
                            
                            pk_sh_P = PS_peak_num_dato - threshold_peak_demand 
                            
                            E_BESS_t = (f_ch) * (n_ch) * (t_btw_rf / 3600) * (pk_sh_P) + (f_dc) * (( t_btw_rf / 3600) * (- pk_sh_P) / (n_dc)) - E_BESS_i*b*(t_btw_rf / 3600)
                            P_BESS_t = (f_dc) * (n_dc) * E_BESS_t / ((t_btw_rf / 3600)) + (1/n_ch) * (f_ch)* E_BESS_t / ((t_btw_rf / 3600))
                            
                            
                            E_BESS_f = E_BESS_i + E_BESS_t                      # Energia final en la BESS
                            SoC = E_BESS_f / E_BESS                             # SoC final
                            E_BESS_i = E_BESS_f                                 # Reiniciar E_BESS_i
                            
                            dss.Command(f"Edit Load.BESS_PJM_FRM kW={P_BESS_t}")
                            dss.Command("Solve")
                            dss.Circuit.SetActiveElement(f"{CB_Monitored}")    # Activation of Line.cb_302
                            P_3f_cb_302 = dss.CktElement.Powers()[0] + dss.CktElement.Powers()[2] + dss.CktElement.Powers()[4]   # Suma de las P de 3 fases del CB_302
                            DSS_Total_Looses_BESS = dss.Circuit.Losses()[0] 
                            
                            List_P_3f_cb_302_dat.append([P_3f_cb_302])
                            P_BESS_bhv.append(P_BESS_t)
                            Col_SoC.append(SoC)                                 # Almacena el valor actual de SoC en la lista
                            
                            # SW_FR_SoCmin = 1 if SoC < FR_SoCmin else 0
                            # SW_FR_SoCmax = 1 if SoC > FR_SoCmax else 0

                            if SoC - (E_BESS_t/E_BESS) < FR_SoCmin:
                                    SW_FR_SoCmin = 1
                                    SW_FR_SoCmax = 0
                                    
                            if SoC > FR_SoCmax:
                                    SW_FR_SoCmax = 1
                                    SW_FR_SoCmin = 0

                            P_bid_h = 0

                            # -------------------- START: Voltage Droop

                            buses_data = []

                            for bus in all_buses:
                                dss.Circuit.SetActiveBus(bus)  # Seleccionar el bus activo
                                voltages = dss.Bus.PuVoltage()  # Obtener las tensiones en pu
                                numPhases = dss.Bus.NumNodes()  # Obtener el número de fases/nodos del bus
                                rms_value = calcular_rms(voltages, numPhases)
                                buses_data.append(rms_value)
  
                            df_voltage_droop['V_RMS - 1'] = df_voltage_droop['V_RMS'] - 1
                            df_voltage_droop['V_RMS_BESS'] = buses_data                           
                            df_voltage_droop['V_RMS_BESS - 1'] = df_voltage_droop['V_RMS_BESS'] - 1
                            df_voltage_droop['Delta_V'] = (abs(1 - df_voltage_droop['V_RMS']) - abs(1 - df_voltage_droop['V_RMS_BESS'])) # / (1 - df_voltage_droop['V_RMS'])) * 100

                            # print(f"df_voltage_droop:\n{df_voltage_droop}")

                            # Ordenar el DataFrame por la columna 'Delta_V' de menor a mayor
                            df_voltage_droop = df_voltage_droop.sort_values(by='Delta_V', ascending=False)

                            # Calcular la desviación estándar ajustada respecto a 1 pu utilizando valor absoluto
                            desviacion_droop_antes = abs(df_voltage_droop['V_RMS'] - 1).std()
                            desviacion_droop_despues = abs(df_voltage_droop['V_RMS_BESS'] - 1).std()

                            f4_t = (desviacion_droop_despues - desviacion_droop_antes)/desviacion_droop_antes

                            # -------------------- FINAL: Voltage Droop

                            df_info_STK.at[num_dato, 'hr'] = h
                            df_info_STK.at[num_dato, 'Col_SoC'] = SoC
                            df_info_STK.at[num_dato, 'P_BESS_t'] = P_BESS_t
                            df_info_STK.at[num_dato, 'name_policy'] = name_policy
                            df_info_STK.at[num_dato, 'P_3f_cb_302'] = P_3f_cb_302
                            df_info_STK.at[num_dato, 'switch_FR'] = SW_FR
                            df_info_STK.at[num_dato, 'P_bid_h'] = P_bid_h
                            df_info_STK.at[num_dato, 'switch_PS'] = SW_PS
                            df_info_STK.at[num_dato, 'PS_peak'] = PS_peak_num_dato
                            df_info_STK.at[num_dato, 'SW_FR_SoCmin'] = SW_FR_SoCmin
                            df_info_STK.at[num_dato, 'SW_FR_SoCmax'] = SW_FR_SoCmax
                            df_info_STK.at[num_dato, 'DSS_Total_Looses_BESS'] = DSS_Total_Looses_BESS
                            df_info_STK.at[num_dato, 'f4_t'] = f4_t

                            ######################################################################################################################
                            ############################# CURRENT ANAYLISIS

                            # Lista para almacenar los datos de las líneas
                            lines_data = []

                            for line in all_lines:
                                dss.Lines.Name(line)  # Seleccionar la línea activa por su nombre
                                
                                # Ahora trabajar con el CktElement correspondiente a la línea activa
                                seq_currents = dss.CktElement.SeqCurrents()  # Obtener las corrientes de secuencia (I1, I2, I0)
                                emerg_amps = dss.CktElement.EmergAmps()  # Obtener la corriente de emergencia
                                norm_amps = dss.CktElement.NormalAmps()  # Obtener la corriente nominal
                                currents = dss.CktElement.CurrentsMagAng()  # Obtener las corrientes en magnitud y ángulo
                                
                                # Calcular los porcentajes
                                I0 = seq_currents[0]
                                I1 = seq_currents[1]
                                I2 = seq_currents[2]
                                percent_I2_I1 = (I2 / I1) * 100 if I1 != 0 and I1 != 1  else 0
                                percent_I0_I1 = (I0 / I1) * 100 if I1 != 0 and I1 != 1  else 0
                                
                                # Calcular los porcentajes de utilización en condiciones normales y de emergencia
                                current_magnitude = max([currents[i] for i in range(0, len(currents), 2)])  # Tomar la magnitud máxima
                                percent_normal = (current_magnitude / norm_amps) * 100 if norm_amps != 0 else 0
                                percent_emergency = (current_magnitude / emerg_amps) * 100 if emerg_amps != 0 else 0

                                # Guardar las propiedades de la línea en un diccionario
                                properties = {
                                               "Line_Name_BESS": line,
                                                "I1_BESS": I1,
                                                "I2_BESS": I2,
                                                "p_I2_I1_BESS": percent_I2_I1,
                                                "I0_BESS": I0,
                                                "p_I0_I1_BESS": percent_I0_I1,
                                                "p_Normal_BESS": percent_normal,
                                                "p_Emergency_BESS": percent_emergency
                                }
                                    
                                # Añadir el diccionario a la lista
                                lines_data.append(properties)

                            df_line_currents_BESS = pd.DataFrame(lines_data)

                            ######################################################################################################################

                            
                        # -------------------- FRM Violations

                        if SoC + (E_BESS_t/E_BESS) < FR_SoCmin:
                            # print(f"SoC: {SoC}, E_BESS_t: {E_BESS_t}, FR_SoCmin: {FR_SoCmin}")
                            # print(f"Soc + (E_BESS_t/E_BESS): {SoC + (E_BESS_t/E_BESS)}")
                            SW_PS_Rest = 1
                            SW_PS = 0

                    # # > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > FINISH ACTIVATION : PEAK SHAVING


                    # # < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <  START ACTIVATION : PEAK-SHAVING
                    # # POLITICA I: BESS Cargando

                    if activate_politica == 0 and h in hrs_day_starts and E_BESS_f < PS_SoC_max * E_BESS and botom_ch_dayly == 0  and SW_FR_SoCmax == 0:    
                            
                            f_dc = 0
                            f_ch = 1    
                            
                            # >>>>>>>>>>>>>>>>>>> Asignación de politica
                            name_policy = 1       
                            activate_politica = 1
                            SW_PS_Rest = 0

                            if P_BESS <= threshold_peak_demand - P_3f_cb_302_BESS_0:
                                P_BESS_max_ch = P_BESS
                                P_BESS_t = P_BESS_max_ch

                            else: 
                                P_BESS_max_ch = threshold_peak_demand - P_3f_cb_302_BESS_0
                                
                                if P_BESS_max_ch < 0:
                                    #print(f"P_BESS_max_ch: {P_BESS_max_ch}")
                                    P_BESS_max_ch = 0
                                    name_policy = 2
                                    

                                P_BESS_t = P_BESS_max_ch
                            
                            if num_dato == 47353:
                                print(f"BESS CHARGING num_dato: {num_dato} activate_politica: {activate_politica} name_policy: {name_policy} ")


                            # >>>>>>>>>>>>>>>>>>>
                            
                            # Evaluadora Ultimo Carga
                            E_BESS_i_var = E_BESS_i
                            E_BESS_f_var = E_BESS_i_var + (f_ch) * (n_ch) * (t_btw_rf / 3600) * (P_BESS_max_ch) + \
                                                          (f_dc) * (( t_btw_rf / 3600) * (- P_BESS_max_ch) / (n_dc)) - \
                                                                      E_BESS_i*b*(t_btw_rf / 3600)
                            
                            if E_BESS_f_var > PS_SoC_max * E_BESS :
                                
                                E_BESS_t = PS_SoC_max * E_BESS - E_BESS_i
                                P_BESS_t = (f_dc) * (n_dc) * E_BESS_t / ((t_btw_rf / 3600)) + (1/n_ch) * (f_ch)* E_BESS_t / ((t_btw_rf / 3600))
                                P_BESS_bhv.append(P_BESS_t)

                                E_BESS_f = E_BESS_i + E_BESS_t                      # Energia final en la BESS
                                SoC = E_BESS_f / E_BESS                             # SoC final
                                Col_SoC.append(SoC)                                 # Almacena el valor actual de SoC en la lista
                                E_BESS_i = E_BESS_f                                 # Reiniciar E_BESS_i

                                dss.Command(f"Edit Load.BESS_PJM_FRM kW={P_BESS_t}")
                                dss.Command("Solve")
                                dss.Circuit.SetActiveElement(f"{CB_Monitored}")    # Activation of Line.cb_302
                                P_3f_cb_302 = dss.CktElement.Powers()[0] + dss.CktElement.Powers()[2] + dss.CktElement.Powers()[4]   # Suma de las P de 3 fases del CB_302
                                List_P_3f_cb_302_dat.append([P_3f_cb_302])
                                DSS_Total_Looses_BESS = dss.Circuit.Losses()[0] 


                            else:

                                E_BESS_t = (f_ch) * (n_ch) * (t_btw_rf / 3600) * (P_BESS_max_ch) + (f_dc) * (( t_btw_rf / 3600) * (- P_BESS_max_ch) / (n_dc)) - E_BESS_i*b*(t_btw_rf / 3600)
                                P_BESS_t = (f_dc) * (n_dc) * E_BESS_t / ((t_btw_rf / 3600)) + (1/n_ch) * (f_ch)* E_BESS_t / ((t_btw_rf / 3600))
                                P_BESS_bhv.append(P_BESS_t)
                                
                                E_BESS_f = E_BESS_i + E_BESS_t                      # Energia final en la BESS
                                SoC = E_BESS_f / E_BESS                             # SoC final
                                Col_SoC.append(SoC)                                 # Almacena el valor actual de SoC en la lista
                                E_BESS_i = E_BESS_f                                 # Reiniciar E_BESS_i

                                dss.Command(f"Edit Load.BESS_PJM_FRM kW={P_BESS_t}")
                                dss.Command("Solve")
                                dss.Circuit.SetActiveElement(f"{CB_Monitored}")   # Activation of Line.cb_302
                                P_3f_cb_302 = dss.CktElement.Powers()[0] + dss.CktElement.Powers()[2] + dss.CktElement.Powers()[4]   # Suma de las P de 3 fases del CB_302
                                List_P_3f_cb_302_dat.append([P_3f_cb_302])
                                DSS_Total_Looses_BESS = dss.Circuit.Losses()[0] 

                            if SoC == PS_SoC_max:
                                botom_ch_dayly = 1
                            else:
                                botom_ch_dayly = 0
                            
                            # SW_FR_SoCmin = 1 if SoC < FR_SoCmin else 0
                            # SW_FR_SoCmax = 1 if SoC > FR_SoCmax else 0

                            P_bid_h = 0

                            # -------------------- START: VOLTAGE ANALYSIS

                            buses_data = []

                            for bus in all_buses:
                                dss.Circuit.SetActiveBus(bus)  # Seleccionar el bus activo
                                voltages = dss.Bus.PuVoltage()  # Obtener las tensiones en pu
                                numPhases = dss.Bus.NumNodes()  # Obtener el número de fases/nodos del bus
                                rms_value = calcular_rms(voltages, numPhases)
                                buses_data.append(rms_value)
  
                            df_voltage_droop['V_RMS - 1'] = df_voltage_droop['V_RMS'] - 1
                            df_voltage_droop['V_RMS_BESS'] = buses_data                           
                            df_voltage_droop['V_RMS_BESS - 1'] = df_voltage_droop['V_RMS_BESS'] - 1
                            df_voltage_droop['Delta_V'] = (abs(1 - df_voltage_droop['V_RMS']) - abs(1 - df_voltage_droop['V_RMS_BESS'])) # / (1 - df_voltage_droop['V_RMS'])) * 100

                            # Ordenar el DataFrame por la columna 'Delta_V' de menor a mayor
                            df_voltage_droop = df_voltage_droop.sort_values(by='Delta_V', ascending=False)

                            # Calcular la desviación estándar ajustada respecto a 1 pu utilizando valor absoluto
                            desviacion_droop_antes = abs(df_voltage_droop['V_RMS'] - 1).std()
                            desviacion_droop_despues = abs(df_voltage_droop['V_RMS_BESS'] - 1).std()

                            f4_t = (desviacion_droop_despues - desviacion_droop_antes)/desviacion_droop_antes

                            # -------------------- FINAL: Voltage Droop

                            df_info_STK.at[num_dato, 'hr'] = h
                            df_info_STK.at[num_dato, 'Col_SoC'] = SoC
                            df_info_STK.at[num_dato, 'P_BESS_t'] = P_BESS_t
                            df_info_STK.at[num_dato, 'name_policy'] = name_policy
                            df_info_STK.at[num_dato, 'P_3f_cb_302'] = P_3f_cb_302
                            df_info_STK.at[num_dato, 'switch_FR'] = SW_FR
                            df_info_STK.at[num_dato, 'P_bid_h'] = P_bid_h
                            df_info_STK.at[num_dato, 'switch_PS'] = SW_PS
                            df_info_STK.at[num_dato, 'PS_peak'] = PS_peak_num_dato
                            df_info_STK.at[num_dato, 'SW_FR_SoCmin'] = SW_FR_SoCmin
                            df_info_STK.at[num_dato, 'SW_FR_SoCmax'] = SW_FR_SoCmax
                            df_info_STK.at[num_dato, 'DSS_Total_Looses_BESS'] = DSS_Total_Looses_BESS
                            df_info_STK.at[num_dato, 'f4_t'] = f4_t

                            ######################################################################################################################
                            ############################# CURRENT ANAYLISIS

                            # Lista para almacenar los datos de las líneas
                            lines_data = []

                            for line in all_lines:
                                dss.Lines.Name(line)  # Seleccionar la línea activa por su nombre
                                
                                # Ahora trabajar con el CktElement correspondiente a la línea activa
                                seq_currents = dss.CktElement.SeqCurrents()  # Obtener las corrientes de secuencia (I1, I2, I0)
                                emerg_amps = dss.CktElement.EmergAmps()  # Obtener la corriente de emergencia
                                norm_amps = dss.CktElement.NormalAmps()  # Obtener la corriente nominal
                                currents = dss.CktElement.CurrentsMagAng()  # Obtener las corrientes en magnitud y ángulo
                                
                                # Calcular los porcentajes
                                I0 = seq_currents[0]
                                I1 = seq_currents[1]
                                I2 = seq_currents[2]
                                percent_I2_I1 = (I2 / I1) * 100 if I1 != 0 and I1 != 1  else 0
                                percent_I0_I1 = (I0 / I1) * 100 if I1 != 0 and I1 != 1  else 0
                                
                                # Calcular los porcentajes de utilización en condiciones normales y de emergencia
                                current_magnitude = max([currents[i] for i in range(0, len(currents), 2)])  # Tomar la magnitud máxima
                                percent_normal = (current_magnitude / norm_amps) * 100 if norm_amps != 0 else 0
                                percent_emergency = (current_magnitude / emerg_amps) * 100 if emerg_amps != 0 else 0

                                # Guardar las propiedades de la línea en un diccionario
                                properties = {
                                               "Line_Name_BESS": line,
                                                "I1_BESS": I1,
                                                "I2_BESS": I2,
                                                "p_I2_I1_BESS": percent_I2_I1,
                                                "I0_BESS": I0,
                                                "p_I0_I1_BESS": percent_I0_I1,
                                                "p_Normal_BESS": percent_normal,
                                                "p_Emergency_BESS": percent_emergency
                                }
                                    
                                # Añadir el diccionario a la lista
                                lines_data.append(properties)

                            df_line_currents_BESS = pd.DataFrame(lines_data)

                            ######################################################################################################################


                            # -------------------- FRM Violations
                            
                            if SoC < FR_SoCmin and (num_dato) % 10 == 0:
                                SW_FR_SoCmin = 1
                            else:
                                SW_FR_SoCmin = 0
                            
                            if SoC > FR_SoCmax and (num_dato) % 10 == 0:
                                SW_FR_SoCmax = 1
                            else:
                                SW_FR_SoCmax = 0

                    # # > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > FINISH ACTIVATION : PEAK SHAVING 




                    # < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <  START ACTIVATION : FREQUENCY REGULATION 
                    #region 

                    # # POLITICA IV: BESS FRM
                    # if SW_FR == 1 and activate_politica == 0 and SW_PS == 0 and SW_FR_SoCmax == 0 and SW_FR_SoCmin == 0:
                                
                    #             # >>>>>>>>>>>>>>>>>>> Asignación de politica
                    #             name_policy = 4       
                    #             activate_politica = 1
                    #             # >>>>>>>>>>>>>>>>>>>
                                
                    #             senal_rf = MR_freq.iloc[num_dato- 1, 0]
                                
                    #             if abs(MR_freq.iloc[num_dato- 1, 0]) > 1:       # Señales mayores a 1 (1.1) o -1 (-1.1) se asumen 1 y -1
                    #                 if MR_freq.iloc[num_dato- 1, 0] > 0:
                    #                     MR_freq.iloc[num_dato- 1, 0] = 1
                    #                 else:
                    #                     MR_freq.iloc[num_dato- 1, 0] = -1
                                
                    #             if MR_freq.iloc[num_dato- 1, 0]< 0:             # Variable "Binaria" de Carga o Descarga, solo activa, la senhal viene con signo (-/+)
                    #                 f_dc = 1
                    #                 f_ch = 0
                    #             else:
                    #                 f_dc = 0
                    #                 f_ch = 1
                                    
                    #             # Energia transmitida por cada dato
                    #             E_BESS_t = (f_ch)*(n_ch)*(t_btw_rf/3600)*(P_BESS)*( MR_freq.iloc[num_dato- 1, 0]) + \
                    #                     (f_dc)*((t_btw_rf/3600)*(P_BESS)*(MR_freq.iloc[num_dato- 1, 0])/(n_dc)) \
                    #                         - E_BESS_i*b*(t_btw_rf / 3600)
                                
                    #             # Acumulador de Potencia MRF PJM
                    #             P_BESS_t = (f_dc) * (n_dc) * E_BESS_t / ((t_btw_rf / 3600)) + \
                    #                     (1/n_ch) * (f_ch)* E_BESS_t / ((t_btw_rf / 3600))
                                
                    #             P_BESS_bhv.append(P_BESS_t)

                    #             S_E_BESS_t_h = S_E_BESS_t_h + abs(E_BESS_t)  # Contador de Energia Transmitida
                    #             E_BESS_f = E_BESS_i + E_BESS_t               # Energia final en la BESS
                                
                    #             SoC = E_BESS_f / E_BESS                      # SoC para evaluar P_bid_h
                    #             Col_SoC.append(SoC)                          # Almacena el valor actual de SoC en la lista

                    #             #Reiniciar E_BESS_i
                    #             E_BESS_i = E_BESS_f                          # Reiniciacion E_BESS_f

                    #             # Calculo del nuevo P_bid_h después de 1 hora de CARGAR o DESCARGAR la BESS
                    #             Col_E_BESS_t_h.append(S_E_BESS_t_h)                                       # Suma de toda la energía transmitida para el MARKET REVENUES PJM
                    #             #P_bid_h = min(min(SoC * E_BESS * 1, (1 - SoC) * E_BESS * 1), P_BESS)        # Nuevo P_bid_h

                    #             # SoC_f_h al final de la hora
                    #             SoC_f_h = E_BESS_f/E_BESS
                                
                    #             # Validador proximidad de carga o descarga, valida si está encima/abajo del 50%
                    #             SoC_evaluator = SoC_f_h - SoC_obj                                                     

                    #             # Colector de P_bid_h por hora
                    #             Col_P_bid_h.append(P_bid_h)                                                 

                    #             # Reiniciar COLECTORES
                    #             S_E_BESS_t_h = 0
                                                          
                                
                    #             dss.Command(f"Edit Load.BESS_PJM_FRM kW={P_BESS_t}")
                    #             dss.Command("Solve")
                    #             dss.Circuit.SetActiveElement("Line.cb_101")     # Activation of Line.cb_302
                                
                    #             P_3f_cb_302 = dss.CktElement.Powers()[0] + dss.CktElement.Powers()[2] + dss.CktElement.Powers()[4]   # Suma de las P de 3 fases del CB_302
                    #             List_P_3f_cb_302_dat.append([P_3f_cb_302])
                    #             DSS_Total_Looses_BESS = dss.Circuit.Losses()[0] 

                                
                    #             if SoC < FR_SoCmin and (num_dato) % 10 == 0:
                    #                 SW_FR_SoCmin = 1
                    #                 SW_FR_SoCmax = 0
                                    
                    #             if SoC > FR_SoCmax and (num_dato) % 10 == 0:
                    #                 SW_FR_SoCmax = 1
                    #                 SW_FR_SoCmin = 0

                    #             # if second_print:
                    #             #     print(f" ******* POLITICA V: h: {h}, num_dato: {num_dato}")
                    #             #     second_print = False
                                
                    #             # SW_FR_SoCmin = 1 if SoC < FR_SoCmin else 0
                    #             # SW_FR_SoCmax = 1 if SoC > FR_SoCmax else 0
                                
                    #             # -------------------- START: VOLTAGE ANALYSIS

                    #             buses_data = []

                    #             for bus in all_buses:
                    #                 dss.Circuit.SetActiveBus(bus)  # Seleccionar el bus activo
                    #                 voltages = dss.Bus.PuVoltage()  # Obtener las tensiones en pu
                    #                 numPhases = dss.Bus.NumNodes()  # Obtener el número de fases/nodos del bus
                    #                 rms_value = calcular_rms(voltages, numPhases)
                    #                 buses_data.append(rms_value)
    
                    #             df_voltage_droop['V_RMS - 1'] = df_voltage_droop['V_RMS'] - 1
                    #             df_voltage_droop['V_RMS_BESS'] = buses_data                           
                    #             df_voltage_droop['V_RMS_BESS - 1'] = df_voltage_droop['V_RMS_BESS'] - 1
                    #             df_voltage_droop['Delta_V'] = (abs(1 - df_voltage_droop['V_RMS']) - abs(1 - df_voltage_droop['V_RMS_BESS'])) # / (1 - df_voltage_droop['V_RMS'])) * 100

                    #             # print(f"df_voltage_droop:\n{df_voltage_droop}")

                    #             # Ordenar el DataFrame por la columna 'Delta_V' de menor a mayor
                    #             df_voltage_droop = df_voltage_droop.sort_values(by='Delta_V', ascending=False)

                    #             # Calcular la desviación estándar ajustada respecto a 1 pu utilizando valor absoluto
                    #             desviacion_droop_antes = abs(df_voltage_droop['V_RMS'] - 1).std()
                    #             desviacion_droop_despues = abs(df_voltage_droop['V_RMS_BESS'] - 1).std()

                    #             f4_t = (desviacion_droop_despues - desviacion_droop_antes)/desviacion_droop_antes

                    #             # -------------------- FINAL: Voltage Droop

                    #             df_info_STK.at[num_dato, 'hr'] = h
                    #             df_info_STK.at[num_dato, 'Col_SoC'] = SoC
                    #             df_info_STK.at[num_dato, 'P_BESS_t'] = P_BESS_t
                    #             df_info_STK.at[num_dato, 'name_policy'] = name_policy
                    #             df_info_STK.at[num_dato, 'P_3f_cb_302'] = P_3f_cb_302
                    #             df_info_STK.at[num_dato, 'switch_FR'] = SW_FR
                    #             df_info_STK.at[num_dato, 'P_bid_h'] = P_bid_h
                    #             df_info_STK.at[num_dato, 'switch_PS'] = SW_PS
                    #             df_info_STK.at[num_dato, 'PS_peak'] = PS_peak_num_dato
                    #             df_info_STK.at[num_dato, 'SW_FR_SoCmin'] = SW_FR_SoCmin
                    #             df_info_STK.at[num_dato, 'SW_FR_SoCmax'] = SW_FR_SoCmax
                    #             df_info_STK.at[num_dato, 'DSS_Total_Looses_BESS'] = DSS_Total_Looses_BESS
                    #             df_info_STK.at[num_dato, 'f4_t'] = f4_t


                    

                    #endregion             
                    # > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > FINISH ACTIVATION : FREQUENCY REGULATION             




                #    # < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <  START ACTIVATION : PEAK SHAVING 
                   # POLITICA II: BESS en reposo
                   #if (E_BESS_f == BESS_SoC_max * E_BESS or P_BESS_t <= 0) and SW_PS == 1 and activate_politica == 0:
                    
                   # print(f"num_dato: {num_dato}, activate_politica: {activate_politica}, SW_PS: {SW_PS}, SW_PS_Rest: {SW_PS_Rest}")

                    if  SW_PS == 0 and activate_politica == 0 and (E_BESS_f == PS_SoC_max * E_BESS or SW_PS_Rest == 1 or PS_peak_num_dato < threshold_peak_demand) :   
                        
                        if num_dato == 47353:
                            print("Entro en la POLITICA 1 ")

                        if num_dato == 47353:
                            print(f"1_activate_politica: {activate_politica}, SW_PS: {SW_PS}, PS_peak_num_dato > threshold_peak_demand: {PS_peak_num_dato > threshold_peak_demand}, SW_FR_SoCmax: {SW_FR_SoCmax}, SW_FR_SoCmin: {SW_FR_SoCmin}")


                        # >>>>>>>>>>>>>>>>>>> Asignación de politica
                        name_policy = 2       
                        activate_politica = 1
                        # >>>>>>>>>>>>>>>>>>>

                        E_BESS_t = 0
                        P_BESS_t = 0
                        P_BESS_bhv.append(P_BESS_t)
                        E_BESS_f = E_BESS_i
                        SoC = E_BESS_f / E_BESS
                        Col_SoC.append(SoC)
                        
                        dss.Command(f"Edit Load.BESS_PJM_FRM kW={P_BESS_t}")
                        dss.Command("Solve")
                        dss.Circuit.SetActiveElement(f"{CB_Monitored}")    # Activation of Line.cb_302
                        P_3f_cb_302 = dss.CktElement.Powers()[0] + dss.CktElement.Powers()[2] + dss.CktElement.Powers()[4]   # Suma de las P de 3 fases del CB_302
                        List_P_3f_cb_302_dat.append([P_3f_cb_302])
                        DSS_Total_Looses_BESS = dss.Circuit.Losses()[0] 
                        
                        
                        # SW_FR_SoCmin = 1 if SoC < FR_SoCmin else 0
                        # SW_FR_SoCmax = 1 if SoC > FR_SoCmax else 0

                        P_bid_h = 0

                        # -------------------- START: VOLTAGE ANALYSIS

                        buses_data = []

                        for bus in all_buses:
                            dss.Circuit.SetActiveBus(bus)  # Seleccionar el bus activo
                            voltages = dss.Bus.PuVoltage()  # Obtener las tensiones en pu
                            numPhases = dss.Bus.NumNodes()  # Obtener el número de fases/nodos del bus
                            rms_value = calcular_rms(voltages, numPhases)
                            buses_data.append(rms_value)
  
                        df_voltage_droop['V_RMS - 1'] = df_voltage_droop['V_RMS'] - 1
                        df_voltage_droop['V_RMS_BESS'] = buses_data                           
                        df_voltage_droop['V_RMS_BESS - 1'] = df_voltage_droop['V_RMS_BESS'] - 1
                        df_voltage_droop['Delta_V'] = (abs(1 - df_voltage_droop['V_RMS']) - abs(1 - df_voltage_droop['V_RMS_BESS'])) # / (1 - df_voltage_droop['V_RMS'])) * 10    
                        # print(f"df_voltage_droop:\n{df_voltage_droop}"    
                        # Ordenar el DataFrame por la columna 'Delta_V' de menor a mayor
                        df_voltage_droop = df_voltage_droop.sort_values(by='Delta_V', ascending=False)    
         
                        desviacion_droop_antes = abs(df_voltage_droop['V_RMS'] - 1).std()
                        desviacion_droop_despues = abs(df_voltage_droop['V_RMS_BESS'] - 1).std()    
                          
                        f4_t = (desviacion_droop_despues - desviacion_droop_antes)/desviacion_droop_antes
       

                            # -------------------- FINAL: Voltage Droop

                        df_info_STK.at[num_dato, 'hr'] = h
                        df_info_STK.at[num_dato, 'Col_SoC'] = SoC
                        df_info_STK.at[num_dato, 'P_BESS_t'] = P_BESS_t
                        df_info_STK.at[num_dato, 'name_policy'] = name_policy
                        df_info_STK.at[num_dato, 'P_3f_cb_302'] = P_3f_cb_302
                        df_info_STK.at[num_dato, 'switch_FR'] = SW_FR
                        df_info_STK.at[num_dato, 'P_bid_h'] = P_bid_h
                        df_info_STK.at[num_dato, 'switch_PS'] = SW_PS
                        df_info_STK.at[num_dato, 'PS_peak'] = PS_peak_num_dato
                        df_info_STK.at[num_dato, 'SW_FR_SoCmin'] = SW_FR_SoCmin
                        df_info_STK.at[num_dato, 'SW_FR_SoCmax'] = SW_FR_SoCmax
                        df_info_STK.at[num_dato, 'DSS_Total_Looses_BESS'] = DSS_Total_Looses_BESS
                        df_info_STK.at[num_dato, 'f4_t'] = f4_t

                        ######################################################################################################################
                        ############################# CURRENT ANAYLISIS

                        # Lista para almacenar los datos de las líneas
                        lines_data = []

                        for line in all_lines:
                            dss.Lines.Name(line)  # Seleccionar la línea activa por su nombre
                                    
                            # Ahora trabajar con el CktElement correspondiente a la línea activa
                            seq_currents = dss.CktElement.SeqCurrents()  # Obtener las corrientes de secuencia (I1, I2, I0)
                            emerg_amps = dss.CktElement.EmergAmps()  # Obtener la corriente de emergencia
                            norm_amps = dss.CktElement.NormalAmps()  # Obtener la corriente nominal
                            currents = dss.CktElement.CurrentsMagAng()  # Obtener las corrientes en magnitud y ángulo
                                    
                            # Calcular los porcentajes
                            I0 = seq_currents[0]
                            I1 = seq_currents[1]
                            I2 = seq_currents[2]
                            percent_I2_I1 = (I2 / I1) * 100 if I1 != 0 and I1 != 1  else 0
                            percent_I0_I1 = (I0 / I1) * 100 if I1 != 0 and I1 != 1  else 0
                                    
                            # Calcular los porcentajes de utilización en condiciones normales y de emergencia
                            current_magnitude = max([currents[i] for i in range(0, len(currents), 2)])  # Tomar la magnitud máxima
                            percent_normal = (current_magnitude / norm_amps) * 100 if norm_amps != 0 else 0
                            percent_emergency = (current_magnitude / emerg_amps) * 100 if emerg_amps != 0 else 0

                            # Guardar las propiedades de la línea en un diccionario
                            properties = {
                                               "Line_Name_BESS": line,
                                                "I1_BESS": I1,
                                                "I2_BESS": I2,
                                                "p_I2_I1_BESS": percent_I2_I1,
                                                "I0_BESS": I0,
                                                "p_I0_I1_BESS": percent_I0_I1,
                                                "p_Normal_BESS": percent_normal,
                                                "p_Emergency_BESS": percent_emergency
                            }
                                    
                            # Añadir el diccionario a la lista
                            lines_data.append(properties)

                        df_line_currents_BESS = pd.DataFrame(lines_data)

                        #####################################################################################################################
                        # -------------------- FRM Violations
                            
 

                #      # > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > FINISH ACTIVATION : PEAK SHAVING
                      

                    
                    


                    
                    # < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <  START ACTIVATION : FREQUENCY REGULATION 
                    #region 

                    # # POLITICA V: BESS Dischrge SoC Objective
                    # if activate_politica == 0 and (SW_FR_SoCmax == 1 or SW_FR_SoCmin == 1): 
 
                    #     # >>>>>>>>>>>>>>>>>>> Asignación de politica
                    #     name_policy = 5       
                    #     activate_politica = 1
                    #     # >>>>>>>>>>>>>>>>>>>
                    
                    #     if SW_FR_SoCmax == 1:
                    #         f_ch = 0
                    #         f_dc = 1
                        
                    #     if SW_FR_SoCmin == 1:
                    #         f_ch = 1
                    #         f_dc = 0
                        
                    #     E_BESS_t = (f_ch) * (n_ch) * (t_btw_rf / 3600) * (P_BESS) + (f_dc) * (( t_btw_rf / 3600) * (- P_BESS) / (n_dc)) - E_BESS_i*b*(t_btw_rf / 3600)
                    #     P_BESS_t = (f_dc) * (n_dc) * E_BESS_t / ((t_btw_rf / 3600)) + (1/n_ch) * (f_ch)* E_BESS_t / ((t_btw_rf / 3600))
                        
                    #     # print(f"FRM Violation: E_BESS_t: {E_BESS_t}, P_BESS_t: {P_BESS_t}")
                        
                    #     E_BESS_f = E_BESS_i + E_BESS_t                      # Energia final en la BESS
                    #     SoC = E_BESS_f / E_BESS                             # SoC final
                    #     E_BESS_i = E_BESS_f                                 # Reiniciar E_BESS_i
                        
                    #     dss.Command(f"Edit Load.BESS_PJM_FRM kW={P_BESS_t}")
                    #     dss.Command("Solve")
                    #     dss.Circuit.SetActiveElement("Line.cb_101")     # Activation of Line.cb_302
                    #     P_3f_cb_302 = dss.CktElement.Powers()[0] + dss.CktElement.Powers()[2] + dss.CktElement.Powers()[4]   # Suma de las P de 3 fases del CB_302
                        
                    #     List_P_3f_cb_302_dat.append([P_3f_cb_302])
                    #     P_BESS_bhv.append(P_BESS_t)
                    #     Col_SoC.append(SoC)                                 # Almacena el valor actual de SoC en la lista
                    #     DSS_Total_Looses_BESS = dss.Circuit.Losses()[0] 
                        
                    #     # SW_FR_SoCmin = 1 if SoC < FR_SoCmin else 0
                    #     # SW_FR_SoCmax = 1 if SoC > FR_SoCmax else 0
                                          
                    #     # -------- Fraction of Energy Transmitted in a Time Period
                        
                    #     δ_ch_dc = (P_BESS)/E_BESS
                        
                    #     if (num_dato) % 10 == 0:
                            
                    #         δ_ch_dc_h = (P_BESS)/E_BESS
                            
                    #         if SW_FR_SoCmin == 1 and SoC + δ_ch_dc > SoC_obj:
                                
                    #             SW_FR_SoCmax = 0
                    #             SW_FR_SoCmin = 0
                    #             SW_FR = 1
                            
                    #         if SW_FR_SoCmax==1 and SoC - δ_ch_dc < SoC_obj:
                            
                    #             SW_FR_SoCmax = 0
                    #             SW_FR_SoCmin = 0
                    #             SW_FR = 1

                    #     # print(f"δ_ch_dc: \t{δ_ch_dc}")  
                        
                    #     # if SW_FR_SoCmax==1 and SoC - δ_ch_dc < SoC_obj:
                            
                    #     #     SW_FR_SoCmax = 0
                    #     #     SW_FR_SoCmin = 0
                            
                    #     #     SW_FR = 1
                            
                    #     # if SW_FR_SoCmin==1 and SoC + δ_ch_dc > SoC_obj:
                    #     #     SW_FR_SoCmax = 0
                    #     #     SW_FR_SoCmin = 0
                    #     #     SW_FR = 1

                    #     P_bid_h = 0

                    #     # -------------------- START: Voltage Droop

                    #     buses_data = []

                    #     for bus in all_buses:
                    #         dss.Circuit.SetActiveBus(bus)  # Seleccionar el bus activo
                    #         voltages = dss.Bus.PuVoltage()  # Obtener las tensiones en pu
                    #         numPhases = dss.Bus.NumNodes()  # Obtener el número de fases/nodos del bus
                    #         rms_value = calcular_rms(voltages, numPhases)
                    #         buses_data.append(rms_value)
  
                    #     df_voltage_droop['V_RMS - 1'] = df_voltage_droop['V_RMS'] - 1
                    #     df_voltage_droop['V_RMS_BESS'] = buses_data                           
                    #     df_voltage_droop['V_RMS_BESS - 1'] = df_voltage_droop['V_RMS_BESS'] - 1
                    #     df_voltage_droop['Delta_V'] = (abs(1 - df_voltage_droop['V_RMS']) - abs(1 - df_voltage_droop['V_RMS_BESS'])) # / (1 - df_voltage_droop['V_RMS'])) * 10    
                    #     # print(f"df_voltage_droop:\n{df_voltage_droop}"    
                    #     # Ordenar el DataFrame por la columna 'Delta_V' de menor a mayor
                    #     df_voltage_droop = df_voltage_droop.sort_values(by='Delta_V', ascending=False)    
                        
                    #     desviacion_droop_antes = abs(df_voltage_droop['V_RMS'] - 1).std()
                    #     desviacion_droop_despues = abs(df_voltage_droop['V_RMS_BESS'] - 1).std()    
    
                    #     f4_t = (desviacion_droop_despues - desviacion_droop_antes)/desviacion_droop_antes

                    #         # -------------------- FINAL: Voltage Droop

                    #     df_info_STK.at[num_dato, 'hr'] = h
                    #     df_info_STK.at[num_dato, 'Col_SoC'] = SoC
                    #     df_info_STK.at[num_dato, 'P_BESS_t'] = P_BESS_t
                    #     df_info_STK.at[num_dato, 'name_policy'] = name_policy
                    #     df_info_STK.at[num_dato, 'P_3f_cb_302'] = P_3f_cb_302
                    #     df_info_STK.at[num_dato, 'switch_FR'] = SW_FR
                    #     df_info_STK.at[num_dato, 'P_bid_h'] = P_bid_h
                    #     df_info_STK.at[num_dato, 'switch_PS'] = SW_PS
                    #     df_info_STK.at[num_dato, 'PS_peak'] = PS_peak_num_dato
                    #     df_info_STK.at[num_dato, 'SW_FR_SoCmin'] = SW_FR_SoCmin
                    #     df_info_STK.at[num_dato, 'SW_FR_SoCmax'] = SW_FR_SoCmax
                    #     df_info_STK.at[num_dato, 'DSS_Total_Looses_BESS'] = DSS_Total_Looses_BESS
                    #     df_info_STK.at[num_dato, 'f4_t'] = f4_t

                    #     # -------------------- FRM Violations
                            
 
                        
                    #endregion 
                    # > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > > FINISH ACTIVATION : FREQUENCY REGULATION    
                    

                    # ------------   STK: Evaluation of Stackable Services
                    # print(f"num_dato: {num_dato} | activate_politica: {activate_politica} | SoC: {SoC} | PS_peak_num_dato: {PS_peak_num_dato} ")
                    # print(f"SW_PS == 0 and activate_politica == 0 and (E_BESS_f == PS_SoC_max * E_BESS or SW_PS_Rest == 1 or PS_peak_num_dato < threshold_peak_demand_of) :")
                    # print(f"SW_PS: {SW_PS} | activate_politica: {activate_politica} | E_BESS_f: {E_BESS_f} | PS_SoC_max * E_BESS: {PS_SoC_max * E_BESS} | SW_PS_Rest: {SW_PS_Rest} | PS_peak_num_dato: {PS_peak_num_dato} | threshold_peak_demand_of: {threshold_peak_demand_of}\n")
                    
                    if activate_politica == 0 :
                        print(f"-------- SIN POLITICA -------- num_dato: {num_dato}\t SoC: {SoC}\t" )
           

                    # -------------------- VOLTAGE CONTROL
                        
                    # Ordenar el dataframe de mayor a menor con respecto a la columna '1-V_RMS'
                    df_voltage_droop_sorted = df_voltage_droop.sort_values(by='V_RMS - 1', ascending=False)
                    df_head = df_voltage_droop_sorted.head(5)
                    df_tail_filtered = df_voltage_droop_sorted[df_voltage_droop_sorted['V_RMS'] < 1]
                    df_tail = df_tail_filtered.tail(5)
                    df_V_Drop_Top = pd.concat([df_head, df_tail]).reset_index(drop=True)

                    # print(f"ORDERED: h: {h} num_dato: {num_dato} df_V_Drop_Top:\n{df_V_Drop_Top}")
                    
                    sobretension_df = df_V_Drop_Top[df_V_Drop_Top['V_RMS'] > 1]
                    # print(f"Sobretension_df: \n{sobretension_df}")

                    caida_voltaje_df = df_V_Drop_Top[df_V_Drop_Top['V_RMS'] < 1]
                    # print(f"Caida_voltaje_df: \n{caida_voltaje_df}")

                    if not sobretension_df.empty:
                        ISV = sobretension_df.apply(lambda row: (row['V_RMS_BESS'] - row['V_RMS'])/ (row['V_RMS']), axis=1).mean()
                    else:
                        ISV = None  # No hay nodos con sobretensión

                    # print(f"********ISV: {ISV}")
                    df_info_STK.at[num_dato, 'ISV'] = ISV

                    if not caida_voltaje_df.empty:
                        ICV = caida_voltaje_df.apply(lambda row: (-(row['V_RMS_BESS'] - row['V_RMS']))/(row['V_RMS']), axis=1).mean()
                    else:
                        ICV = None  # No hay nodos con caídas de voltaje

                    # # print(f"********ICV: {ICV}")
                    df_info_STK.at[num_dato, 'ICV'] = ICV
                    
                    # print(f"num_dato: {num_dato} length: {len(df_voltage_droop)}\ndf_voltage_droop: \n{df_voltage_droop.head()}")

                    # print(f"sobretension_df:\n{sobretension_df}")
                    # print(f"caida_voltaje_df:\n{caida_voltaje_df}")


                    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> VOLTAGE CONTROL
                    if num_dato == 67:
                        df_voltage_control = df_voltage_droop[['Bus_Name', 'V_RMS', 'V_RMS_BESS']].copy()
                        df_voltage_control['P_BESS_t'] = P_BESS_t
                        df_voltage_control['num_dato'] = num_dato
                        df_voltage_control['h'] = h
                        df_voltage_control['P_BESS'] = P_BESS
                        df_voltage_control['E_BESS'] = E_BESS
                        file_name = f'VControl_hr{h}_num_dato{num_dato}_{E_BESS}kWh_P_BESS_t{P_BESS_t:.0f}.xlsx'

                    ##################################################################### CURRENT ANALYSIS

                    ######################################################################################################################
                    ############################# CURRENT ANAYLISIS

                    df_line_compare = pd.concat([df_line_currents_BESS, df_line_currents], axis=1)
                    # print(f"********* {num_dato} df_line_compare: \n{df_line_compare}")

                    media_p_I2_I1 = df_line_compare['p_I2_I1'].mean()
                    media_p_I2_I1_BESS = df_line_compare['p_I2_I1_BESS'].mean()
                    # print(f"num_dato: {num_dato} | media_p_I2_I1     : {media_p_I2_I1}")
                    # print(f"num_dato: {num_dato} | media_p_I2_I1_BESS:{media_p_I2_I1_BESS}")
                 
                    media_p_I0_I1 = df_line_compare['p_I0_I1'].mean()
                    media_p_I0_I1_BESS = df_line_compare['p_I0_I1_BESS'].mean()
                    # print(f"num_dato: {num_dato} | media_p_I2_I1     : {media_p_I0_I1}")
                    # print(f"num_dato: {num_dato} | media_p_I2_I1_BESS: {media_p_I0_I1_BESS}")

                    media_p_Normal = df_line_compare['p_Normal'].mean()
                    media_p_Normal_BESS = df_line_compare['p_Normal_BESS'].mean()
                    # print(f"num_dato: {num_dato} | media_p_I2_I1     : {media_p_Normal}")
                    # print(f"num_dato: {num_dato} | media_p_I2_I1_BESS: {media_p_Normal_BESS}")

                    df_info_STK.at[num_dato, 'm_p_I2_I1'] = media_p_I2_I1
                    df_info_STK.at[num_dato, 'm_p_I2_I1_BESS'] = media_p_I2_I1_BESS
                    df_info_STK.at[num_dato, 'm_p_I0_I1'] = media_p_I0_I1
                    df_info_STK.at[num_dato, 'm_p_I0_I1_BESS'] = media_p_I0_I1_BESS
                    df_info_STK.at[num_dato, 'm_p_Normal'] = media_p_Normal
                    df_info_STK.at[num_dato, 'm_p_Normal_BESS'] = media_p_Normal_BESS
                
                    ######################################################################################################################

                    if num_dato == 47352:
                            print(f"num_dato: {num_dato} name_policy: {name_policy} ")

                    if num_dato == 47353:
                            print(f"num_dato: {num_dato} name_policy: {name_policy} ")


        if len(List_P_3f_cb_302_dat) != len(P_BESS_bhv) or len(P_BESS_bhv) != len(Col_SoC):
             print(f" ******* Las listas no tienen la misma longitud. h: {h}, num_dato: {num_dato}")
             print(f" ******* Longitud de List_P_3f_cb_302_dat: {len(List_P_3f_cb_302_dat)}, Longitud de P_BESS_bhv: {len(P_BESS_bhv)}, Longitud de Col_SoC: {len(Col_SoC)}")
    
    
    ############################################################################################################
    ########################################## IMPRESIÓN DE DATAFRAME

    
    df_info_STK['hr'] = df_info_STK['hr'].apply(lambda x: x - primera_hora + 1)
      
    # Filtrar los valores de P_bid_h donde (índice - 1) es divisible entre 10
    df_E_BESS_t_h = df_info_STK[df_info_STK.index.map(lambda x: (x - 1) % 10 == 0)][['P_bid_h']]

    # Agregar una nueva columna que almacene el número de índice original
    df_E_BESS_t_h['original_index'] = df_info_STK.index[df_info_STK.index.map(lambda x: (x - 1) % 10 == 0)]

    # Reiniciar el índice del nuevo DataFrame
    df_E_BESS_t_h = df_E_BESS_t_h.reset_index(drop=True)

    datos_filtrados = MR_prices.iloc[primera_hora - 1:ultima_hora]
    datos_filtrados = datos_filtrados.reset_index(drop=True)
    df_E_BESS_t_h['MR_prices_USD_MW'] = datos_filtrados['Price']

    df_E_BESS_t_h['Rev_MR_h'] = (df_E_BESS_t_h['P_bid_h'] * df_E_BESS_t_h['MR_prices_USD_MW']) / 1000

    # # Mostrar el resultado
    # print(f"df_E_BESS_t_h: \n{df_E_BESS_t_h}")

    annual_revenue = df_E_BESS_t_h['Rev_MR_h'].sum()
    print(f"annual_revenue 1: {annual_revenue}")
    factor_escalabilidad = 8760 / (ultima_hora - primera_hora + 1)
    annual_revenue = annual_revenue * factor_escalabilidad 
    print(f"annual_revenue 2: {annual_revenue}")
    #print(f"annual_revenue: {annual_revenue}\n")
   
    # Obtener la fecha y hora actuales
    now = datetime.now()
    fecha_hora = now.strftime("%Y%m%d_%H%M%S")

    ###########################################################################################################
    ######################################### CREACION DE FIGURA

    # # Supongamos que df_new_value es tu DataFrame ya cargado

    # # Obtener la ruta del directorio del script
    # script_dir = os.path.dirname(os.path.abspath(__file__))

    # # Crear la carpeta 'Outfiles_STK' en la misma ubicación que el script si no existe
    # output_dir = os.path.join(script_dir, 'Results_PS_Test_001')
    # if not os.path.exists(output_dir):
    #     os.makedirs(output_dir)

    ########################

    # # Especificar la ruta completa del archivo de Excel
    # output_file = os.path.join(output_dir, file_name)
    
    # # Guardar el DataFrame en una hoja de Excel
    # df_voltage_control.to_excel(output_file, index=False)

    ########################

    # Extraer los valores de las columnas 'P_3f_cb_302' y 'Col_SoC'
    P_3f_cb_302 = df_info_STK['P_3f_cb_302']
    Col_SoC = df_info_STK['Col_SoC']

    ###########################################################################################################
    #>>>>>>>>>>>>>>>>>>>>>>>> GENERADOR DE GRÁFICOS

    #region 
    # import matplotlib.pyplot as plt
    # import matplotlib.ticker as ticker
    # import matplotlib.lines as mlines

    # # Función para crear una colección de líneas con colores
    # def colored_line(x, y, colors, ax, **kwargs):
    #     for i in range(len(x) - 1):
    #         ax.plot(x[i:i+2], y[i:i+2], color=colors[i], **kwargs)
    #         ax.scatter(x[i], y[i], color=colors[i], **kwargs, s=2)  # Ajustar el tamaño del marcador


    # fig, axs = plt.subplots(4, 1, figsize=(18, 23), dpi=700, gridspec_kw={'height_ratios': [1, 1, 1, 1], 'hspace': 0.3})  # Reducir el tamaño general de la figura

    # colors_dict = {1: 'black', 2: 'teal', 3: 'magenta', 4: 'blue', 5: 'darkgray'}
    # colors_policy = df_info_STK['name_policy'].map(colors_dict).fillna('blue').to_numpy()

    # # Crear los ticks en el eje X en los múltiplos de 120
    # xticks = [x for x in range(df_info_STK.index.min(), df_info_STK.index.max() + 1) if x % 120 == 0]
    # xticklabels = [str(x // 10) for x in xticks]

    # # Graficar P_BESS_t en el primer eje con colores según la política
    # x = df_info_STK.index.to_numpy()
    # y = df_info_STK['P_BESS_t'].to_numpy()
    # colored_line(x, y, colors_policy, axs[0], linewidth=1.5)  # Reducir el grosor de la línea
    # axs[0].set_title(f'BESS Active Power - Service: FR - BESS Properties: {P_BESS} kW {E_BESS} kWh - Time Period: {primera_hora} to {ultima_hora} hours', fontsize=15, fontname='Times New Roman')
    # axs[0].set_xlabel('Time [h]', fontsize=12, fontname='Times New Roman')
    # axs[0].set_ylabel('BESS Power [kW]', fontsize=12, fontname='Times New Roman')
    # axs[0].tick_params(axis='x', labelsize=12, rotation=0)
    # axs[0].tick_params(axis='y', labelsize=12)

    # # Configurar los ticks y los límites del eje y para axs[0]
    # axs[0].set_yticks([i * 100 for i in range(-int(P_BESS/100), int(P_BESS/100) + 1)])  # De -P_BESS a P_BESS con saltos de 100
    # axs[0].set_ylim(-P_BESS - 100, P_BESS + 100)  # Establecer los límites del eje y
    # axs[0].axhline(y=P_BESS, color='gray', linestyle='--', linewidth=1.5)
    # axs[0].axhline(y=-P_BESS, color='gray', linestyle='--', linewidth=1.5)
    # axs[0].grid(True)
    # axs[0].set_xlim([df_info_STK.index.min(), df_info_STK.index.max()])
    # axs[0].set_xticks(xticks)
    # axs[0].set_xticklabels(xticklabels, fontsize=12, fontname='Times New Roman')
    # axs[0].set_yticks(axs[0].get_yticks())
    # axs[0].set_yticklabels([f"{int(tick)}" for tick in axs[0].get_yticks()], fontsize=12, fontname='Times New Roman')

    # # Configurar notación científica para el eje Y del primer gráfico
    # axs[0].yaxis.set_major_formatter(ticker.ScalarFormatter(useMathText=True))
    # axs[0].ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    # axs[0].yaxis.get_offset_text().set_fontsize(10)

    # legend_1 = mlines.Line2D([], [], color='black', label='Mode: BESS Charge ', linestyle='-', marker='o', markersize=5)
    # legend_2 = mlines.Line2D([], [], color='teal', label='Mode: BESS Idle', linestyle='-', marker='o', markersize=5)
    # legend_3 = mlines.Line2D([], [], color='magenta', label='Mode: Service PS', linestyle='-', marker='o', markersize=5)
    # legend_4 = mlines.Line2D([], [], color='blue', label='Mode: Service FRM', linestyle='-', marker='o', markersize=5)
    # legend_5 = mlines.Line2D([], [], color='darkgray', label='Mode: Recovering SoC Objective', linestyle='-', marker='o', markersize=5)

    # # Agregar a la leyenda
    # axs[0].legend(handles=[legend_1, legend_2, legend_3, legend_4, legend_5], prop={'size': 8}, ncol=5)

    # # Graficar Col_SoC en el segundo eje con colores según la política
    # y = df_info_STK['Col_SoC'].to_numpy()
    # colored_line(x, y, colors_policy, axs[1], linewidth=1.5)
    # axs[1].set_title(f'BESS SoC - Service: FR - BESS Properties: {P_BESS} kW {E_BESS} kWh - Time Period: {primera_hora} to {ultima_hora} hours', fontsize=15, fontname='Times New Roman')
    # axs[1].set_xlabel('Time [h]', fontsize=12, fontname='Times New Roman')
    # axs[1].set_ylabel('SoC [p.u.]', fontsize=12, fontname='Times New Roman')
    # axs[1].tick_params(axis='x', labelsize=12, rotation=0)
    # axs[1].tick_params(axis='y', labelsize=12)
    # axs[1].set_yticks([i * 0.1 for i in range(11)])
    # axs[1].set_ylim(0, 1)
    # axs[1].grid(True)
    # axs[1].set_xlim([df_info_STK.index.min(), df_info_STK.index.max()])
    # axs[1].set_xticks(xticks)
    # axs[1].set_xticklabels(xticklabels, fontsize=12, fontname='Times New Roman')
    # axs[1].set_yticks(axs[1].get_yticks())
    # axs[1].set_yticklabels([f"{tick:.1f}" for tick in axs[1].get_yticks()], fontsize=12, fontname='Times New Roman')

    # # Agregar líneas horizontales en y = 0.05 y y = 0.95
    # axs[1].axhline(y=0.1, color='gray', linestyle='--', linewidth=1.5)
    # axs[1].axhline(y=0.9, color='gray', linestyle='--', linewidth=1.5)

    # linea_soc_objective = axs[1].axhline(y=0.5, color='black', linestyle='--', linewidth=1.5, label='SoC Objective')
    # legend_1 = mlines.Line2D([], [], color='black', label='Mode: BESS Charge ', linestyle='-', marker='o', markersize=5)
    # legend_2 = mlines.Line2D([], [], color='teal', label='Mode: BESS Idle', linestyle='-', marker='o', markersize=5)
    # legend_3 = mlines.Line2D([], [], color='magenta', label='Mode: Service PS', linestyle='-', marker='o', markersize=5)
    # legend_4 = mlines.Line2D([], [], color='blue', label='Mode: Service FRM', linestyle='-', marker='o', markersize=5)
    # legend_5 = mlines.Line2D([], [], color='darkgray', label='Mode: Recovering SoC Objective', linestyle='-', marker='o', markersize=5)

    # axs[1].legend(handles=[legend_1, legend_2, legend_3, legend_4, legend_5, linea_soc_objective], prop={'size': 8}, ncol=6)

    # # Graficar DSS_Total_Looses y DSS_Total_Looses_BESS en el tercer eje
    # axs[2].plot(df_info_STK.index, df_info_STK['P_3f_cb_302_BESS_0'], color='red', linewidth=1.5, label='Without BESS')
    # axs[2].plot(df_info_STK.index, df_info_STK['P_3f_cb_302'], color='blue', linewidth=1.5, label='With BESS')
    # axs[2].set_title(f'Active Power through CB_302 - Service: FR - BESS Properties: {P_BESS} kW {E_BESS} kWh - Time Period: {primera_hora} to {ultima_hora} hours', fontsize=15, fontname='Times New Roman')
    # axs[2].set_xlabel('Time [h]', fontsize=12, fontname='Times New Roman')
    # axs[2].set_ylabel('Active Power [kW]', fontsize=12, fontname='Times New Roman')

    # axs[2].tick_params(axis='x', labelsize=12, rotation=0, which='both')
    # axs[2].tick_params(axis='y', labelsize=12, which='both')

    # axs[2].set_yticks([i * 500 for i in range(4)])
    # axs[2].set_ylim(0, 1500)
    # axs[2].grid(True)
    # axs[2].set_xlim([df_info_STK.index.min(), df_info_STK.index.max()])

    # # Configurar los ticks y las etiquetas en el eje X
    # axs[2].set_xticks(xticks)
    # axs[2].set_xticklabels(xticklabels, fontsize=12, fontname='Times New Roman')

    # # Configurar las etiquetas del eje Y
    # axs[2].set_yticks(axs[2].get_yticks())
    # axs[2].set_yticklabels([f"{int(tick)}" for tick in axs[2].get_yticks()], fontsize=12, fontname='Times New Roman')

    # # Agregar línea horizontal en y = 1000
    # axs[2].axhline(y=1000, color='black', linestyle='--', linewidth=1.5, label='Peak-demand threshold')
    # axs[2].legend(prop={'size': 10}, loc='lower right', bbox_to_anchor=(1, 0))

    # # Configurar notación científica para el eje Y del tercer gráfico
    # axs[2].yaxis.set_major_formatter(ticker.ScalarFormatter(useMathText=True))
    # axs[2].ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    # axs[2].yaxis.get_offset_text().set_fontsize(10)

    # # Graficar DSS_Total_Looses y DSS_Total_Looses_BESS en el cuarto eje
    # axs[3].plot(df_info_STK.index, df_info_STK['DSS_Total_Looses'], color='red', linewidth=1.5, label='Without BESS')
    # axs[3].plot(df_info_STK.index, df_info_STK['DSS_Total_Looses_BESS'], color='blue', linewidth=1.5, label='With BESS')
    # axs[3].set_title(f'Total System Losses - Service: FR - BESS Properties: {P_BESS} kW {E_BESS} kWh - Time Period: {primera_hora} to {ultima_hora} hours', fontsize=15, fontname='Times New Roman')
    # axs[3].set_xlabel('Time [h]', fontsize=12, fontname='Times New Roman')
    # axs[3].set_ylabel('Total Losses [kW]', fontsize=12, fontname='Times New Roman')
    # axs[3].tick_params(axis='x', labelsize=12, rotation=0)
    # axs[3].tick_params(axis='y', labelsize=12)
    # axs[3].grid(True)
    # axs[3].set_xlim([df_info_STK.index.min(), df_info_STK.index.max()])
    # axs[3].set_xticks(xticks)
    # axs[3].set_xticklabels(xticklabels, fontsize=12, fontname='Times New Roman')
    # axs[3].set_yticks([i * 20000 for i in range(9)])
    # axs[3].set_ylim(0, 80000)
    # axs[3].set_yticklabels([f"{int(tick)}" for tick in axs[3].get_yticks()], fontsize=12, fontname='Times New Roman')

    # # Configurar notación científica para el eje Y del cuarto gráfico
    # axs[3].yaxis.set_major_formatter(ticker.ScalarFormatter(useMathText=True))
    # axs[3].ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    # axs[3].yaxis.get_offset_text().set_fontsize(10)
    # axs[3].legend(prop={'size': 10}, loc='lower right', bbox_to_anchor=(1, 0))

    # # Ajustar el layout para eliminar los espacios adicionales
    # plt.tight_layout(pad=0)

    # # Guardar la figura en la carpeta 'Outfiles_STK' sin mostrarla
    # nombre_archivo = f'{fecha_hora}_STK_FR_PS_{P_BESS}kW_{E_BESS}kWh_{primera_hora}to{ultima_hora}.png'
    # output_path = os.path.join(output_dir, nombre_archivo)
    # plt.savefig(output_path, bbox_inches='tight')
    #plt.show()
    # plt.close()  # Cerrar la figura para no mostrarla

    # print(f"Gráfico guardado en {output_path}")

    # # Guardar el DataFrame en una hoja de Excel
    # nombre_archivo_excel = f'{fecha_hora}_STK_FR_PS_{P_BESS}kW_{E_BESS}kWh_{primera_hora}to{ultima_hora}.xlsx'
    # output_path_excel = os.path.join(output_dir, nombre_archivo_excel)
    # df_info_STK.to_excel(output_path_excel, index=True)

    # print(f"DataFrame guardado en {output_path_excel}")

    #endregion
    
    ######################################### RESUMEN
    
    # # ****************** 4. BESS BEHAVIOUR EXCEL CSV ******************
       
 
    # Extraer la columna 'Col_SoC' en un nuevo dataframe y renombrarla
    df_SoC = df_info_STK[['Col_SoC']].copy()
    df_SoC.rename(columns={'Col_SoC': 'SoC'}, inplace=True)

    # Extraer la columna 'P_BESS_t' en un nuevo dataframe
    P_BESS_num = df_info_STK[['P_BESS_t']].copy()    

    # print(f"df_info_STK: \n{df_info_STK}")

    # >>>>>>>>>>>>>>>>>>>>>>> f3

    df_info_STK['f3_t'] = (df_info_STK['DSS_Total_Looses_BESS'] - df_info_STK['DSS_Total_Looses']) / df_info_STK['DSS_Total_Looses']
    f3 = df_info_STK['f3_t'].mean() * 100

    # >>>>>>>>>>>>>>>>>>>>>>> f4 
    f4 = df_info_STK['f4_t'].mean()* 100

    # >>>>>>>>>>>>>>>>>>>>>>> f5
    f5 = df_info_STK['ISV'].mean()* 100

    # >>>>>>>>>>>>>>>>>>>>>>> f6
    f6 = df_info_STK['ICV'].mean()* 100

    #########################################
    #########################################

    df_info_STK['f_i_1_t'] = (df_info_STK['m_p_I2_I1_BESS'] - df_info_STK['m_p_I2_I1']) / df_info_STK['m_p_I2_I1']
    f_i_1 = df_info_STK['f_i_1_t'].mean() * 100
    # print(f"******* f_i_1: {f_i_1}")
    df_info_STK['f_i_2_t'] = (df_info_STK['m_p_I0_I1_BESS'] - df_info_STK['m_p_I0_I1']) / df_info_STK['m_p_I0_I1']
    f_i_2 = df_info_STK['f_i_2_t'].mean() * 100
    # print(f"******* f_i_2: {f_i_2}")
    df_info_STK['f_i_3_t'] = (df_info_STK['m_p_Normal_BESS'] - df_info_STK['m_p_Normal']) / df_info_STK['m_p_Normal']
    f_i_3 = df_info_STK['f_i_3_t'].mean() * 100
    # print(f"******* f_i_3: {f_i_3}")    
    # print(f"f_i_1: {f_i_1}")
    # print(f"f_i_2: {f_i_2}")
    # print(f"f_i_3: {f_i_3}")
    
    #########################################

    #########################################

    # >>>>>>>>>>>>>>> f1: CALCULO DEL PAYBACK PERIOD

    #region
    #region
    years = 10000

    #----------------- Ajustar Precios

    def obtener_precios(E_BESS, P_BESS):
    # Definir los datos
        # data = {
        #     'USD_kW': [350.0, 559.9, 976.0, 343.7, 551.1, 961.8, 337.4, 542.4, 947.5],
        #     'USD_kWh': [355.0, 344.3, 300.1, 348.5, 338.9, 295.7, 341.9, 333.5, 291.4]
        # }

        data = {

          'USD_kW': [129.3,	206.8,	360.6,
                    126.9,	203.6,	355.3,
                    124.6,	200.3,	350.0],


            'USD_kWh': [432.6, 419.6, 365.7, 
                        424.6, 412.9, 360.3, 
                        416.6, 406.4, 355.0]
        }

        # Definir los índices de dos niveles: E_BESS y P_BESS
        index = pd.MultiIndex.from_tuples([
            (1000, 1000), (1000, 500), (1000, 250),
            (2000, 2000), (2000, 1000), (2000, 500),
            (3000, 3000), (3000, 1500), (3000, 750)
        ], names=['E_BESS', 'P_BESS'])

        # Crear el dataframe
        df = pd.DataFrame(data, index=index)

        # Tratar de obtener los valores correspondientes de USD_kW y USD_kWh
        try:
            fila = df.loc[(E_BESS, P_BESS)]
            USD_kW = fila['USD_kW']
            USD_kWh = fila['USD_kWh']
        except KeyError:
            # Si no se encuentra la tupla (E_BESS, P_BESS), devolver valores por defecto
            USD_kW = 350
            USD_kWh = 355
        
        return USD_kW, USD_kWh


    USD_kW, USD_kWh = obtener_precios(E_BESS, P_BESS)
    print (f"New Prices: USD_kW: {USD_kW}\t USD_kWh: {USD_kWh}")

    USD_BESS_kW_Total = P_BESS * USD_kW
    USD_BESS_kWh_Total = E_BESS * USD_kWh
    Total_Investment = USD_BESS_kW_Total + USD_BESS_kWh_Total
    
    print(f"Total_Investment: {Total_Investment}")
    

    #----------------- Ajustar Revenues

    print(f"BEFORE annual_revenue: {annual_revenue}")
    f_correccion = 1
    print(f"f_correccion: {f_correccion}")

    #------ OPEX
    OPEX_USD_kW_year = 0.025 * USD_kW
    OPEX = OPEX_USD_kW_year * P_BESS
    print(f"OPEX_USD_kW_year: {OPEX_USD_kW_year}")
    print(f"OPEX: {OPEX}")

    annual_revenue = f_correccion * annual_revenue - OPEX
    print(f"AFTER  annual_revenue: {annual_revenue}")

    f1_PS = Total_Investment

    f1 = f1_PS

    ####################################################
    ######## PRE - TRATAMIENTO annual_revenues
    ####################################################
    
    # factor_escalabilidad = 8760 / (ultima_hora - primera_hora + 1)
    # annual_revenue = annual_revenue * factor_escalabilidad
    
    ####################################################
    
    # # Crear un DataFrame con ingresos anuales constantes
    # annual_revenues = [annual_revenue] * years
    # df_revenues = pd.DataFrame({'Year': range(1, years + 1), 'Revenue': annual_revenues})

    # # Añadir columnas para Valor Presente (VP) y flujo de caja acumulado
    # df_revenues['VP'] = 0.0
    # df_revenues['Cumulative_Cash_Flow'] = 0.0

    # # Calcular el payback period utilizando los ingresos anuales constantes
    # cumulative_cash_flow = -Total_Investment
    # Y = 0
    # for y in range(1, years + 1):
    #     discounted_revenue = df_revenues.loc[y - 1, 'Revenue'] / ((1 + annual_discount_rate) ** y)
    #     cumulative_cash_flow += discounted_revenue
    #     df_revenues.at[y - 1, 'VP'] = discounted_revenue
    #     df_revenues.at[y - 1, 'Cumulative_Cash_Flow'] = cumulative_cash_flow
    #     if cumulative_cash_flow >= 0:
    #         Y = y
    #         break

    # # Identificar el último año con flujo de caja acumulado negativo
    # if Y > 1 and df_revenues.at[Y - 1, 'Cumulative_Cash_Flow'] >= 0:
    #     Y -= 1

    # if cumulative_cash_flow < 0:
    #     f1 = None
    #     print("El periodo de recuperación del capital no se alcanza en 30 años.")
    # else:
    #     # Calcular el segundo término de la fórmula
    #     numerator = -Total_Investment
    #     for y in range(1, Y + 1):
    #         numerator += df_revenues.loc[y - 1, 'Revenue'] * ((1 + annual_discount_rate) ** y)

    #     denominator = df_revenues.loc[Y, 'Revenue'] * ((1 + annual_discount_rate) ** (Y + 1))
    #     f1 = Y + abs(numerator / denominator)
    #endregion

    #########################################

    # >>>>>>>>>>>>>>> f2: CALCULO DEL PAYBACK PERIOD

    #region
    print("... Executing ... f_f2_delta_DOD ... ")
    new_row = pd.DataFrame({'SoC': [0.50]})

    # Concatenar la nueva fila al inicio del DataFrame existente
    df_SoC = pd.concat([new_row, df_SoC], ignore_index=True)

    # Inicializar las columnas MIN y MAX
    df_SoC['MIN'] = df_SoC['SoC']
    df_SoC['MAX'] = df_SoC['SoC']

    # Crear las columnas e_MIN y e_MAX calculando las diferencias respecto a MIN y MAX
    df_SoC['e_MIN'] = df_SoC['SoC'] - df_SoC['MIN']
    df_SoC['e_MAX'] = df_SoC['MAX'] - df_SoC['SoC']

    # Añadir las columnas NewValorMIN y NewValorMAX con valor por defecto de 0
    df_SoC['NewValorMIN'] = 0
    df_SoC['NewValorMAX'] = 0

    # Añadir las columnas t_MIN y t_MAX con el índice inicial de 0
    df_SoC['t_MIN'] = 0
    df_SoC['t_MAX'] = 0

    # Actualizar las columnas MIN, MAX, t_MIN y t_MAX recorriendo fila por fila y actualizar NewValorMIN y NewValorMAX
    for i in range(1, len(df_SoC)):
        # Actualizar MIN y MAX
        df_SoC.at[i, 'MIN'] = min(df_SoC.at[i-1, 'MIN'], df_SoC.at[i, 'SoC'])
        df_SoC.at[i, 'MAX'] = max(df_SoC.at[i-1, 'MAX'], df_SoC.at[i, 'SoC'])

        # Actualizar t_MIN y t_MAX
        df_SoC.at[i, 't_MIN'] = i if df_SoC.at[i, 'MIN'] == df_SoC.at[i, 'SoC'] else df_SoC.at[i-1, 't_MIN']
        df_SoC.at[i, 't_MAX'] = i if df_SoC.at[i, 'MAX'] == df_SoC.at[i, 'SoC'] else df_SoC.at[i-1, 't_MAX']

        # Calcular e_MIN y e_MAX
        df_SoC.at[i, 'e_MIN'] = df_SoC.at[i, 'SoC'] - df_SoC.at[i, 'MIN']
        df_SoC.at[i, 'e_MAX'] = df_SoC.at[i, 'MAX'] - df_SoC.at[i, 'SoC']

        # Actualizar NewValorMIN cuando e_MIN sea mayor o igual a 0.10
        if df_SoC.at[i, 'e_MIN'] >= 0.10:
            df_SoC.at[i, 'NewValorMIN'] = 1
            # Reiniciar MIN y t_MIN
            df_SoC.at[i, 'MIN'] = df_SoC.at[i, 'SoC']
            df_SoC.at[i, 't_MIN'] = i

        # Actualizar NewValorMAX cuando e_MAX sea mayor o igual a 0.10
        if df_SoC.at[i, 'e_MAX'] >= 0.10:
            df_SoC.at[i, 'NewValorMAX'] = 1
            # Reiniciar MAX y t_MAX
            df_SoC.at[i, 'MAX'] = df_SoC.at[i, 'SoC']
            df_SoC.at[i, 't_MAX'] = i

        # En las filas siguientes, establecer los nuevos valores de MIN y MAX
        if i < len(df_SoC) - 1:
            if df_SoC.at[i, 'NewValorMIN'] == 1 or df_SoC.at[i, 'NewValorMAX'] == 1:
                for j in range(i+1, len(df_SoC)):
                    df_SoC.at[j, 'MIN'] = df_SoC.at[i, 'SoC']
                    df_SoC.at[j, 'MAX'] = df_SoC.at[i, 'SoC']
                    df_SoC.at[j, 't_MIN'] = i
                    df_SoC.at[j, 't_MAX'] = i
                    break

    # Filtrar las filas donde NewValorMIN o NewValorMAX tienen el valor de 1 y también almacenar la fila anterior
    indices = df_SoC.index[(df_SoC['NewValorMIN'] == 1) | (df_SoC['NewValorMAX'] == 1)]
    indices = sorted(set(indices).union(set(indices - 1)))

    df_SoC_delta_DoD = df_SoC.loc[indices].copy()

    if not df_SoC_delta_DoD.empty:
        
        # Combinar filas de a dos
        combinaciones = []

        for i in range(1, len(df_SoC_delta_DoD), 2):
            fila_anterior = df_SoC_delta_DoD.iloc[i-1]
            fila_actual = df_SoC_delta_DoD.iloc[i]

            if fila_actual['NewValorMAX'] == 1:
                nueva_fila = {
                    'Indice': fila_actual.name,
                    'SoC': fila_actual['SoC'],
                    'MIN': fila_anterior['MIN'],
                    'MAX': fila_anterior['MAX'],
                    'e_MIN': fila_actual['e_MIN'],
                    'e_MAX': fila_actual['e_MAX'],
                    'NewValorMIN': fila_actual['NewValorMIN'],
                    'NewValorMAX': fila_actual['NewValorMAX'],
                    't_MIN': fila_actual['t_MIN'],
                    't_MAX': fila_anterior['t_MAX']
                }
            elif fila_actual['NewValorMIN'] == 1:
                nueva_fila = {
                    'Indice': fila_actual.name,
                    'SoC': fila_actual['SoC'],
                    'MIN': fila_anterior['MIN'],
                    'MAX': fila_anterior['MAX'],
                    'e_MIN': fila_actual['e_MIN'],
                    'e_MAX': fila_actual['e_MAX'],
                    'NewValorMIN': fila_actual['NewValorMIN'],
                    'NewValorMAX': fila_actual['NewValorMAX'],
                    't_MIN': fila_anterior['t_MIN'],
                    't_MAX': fila_actual['t_MAX']
                }
            else:
                nueva_fila = {
                    'Indice': fila_actual.name,
                    'SoC': fila_actual['SoC'],
                    'MIN': fila_actual['MIN'],
                    'MAX': fila_actual['MAX'],
                    'e_MIN': fila_actual['e_MIN'],
                    'e_MAX': fila_actual['e_MAX'],
                    'NewValorMIN': fila_actual['NewValorMIN'],
                    'NewValorMAX': fila_actual['NewValorMAX'],
                    't_MIN': fila_actual['t_MIN'],
                    't_MAX': fila_actual['t_MAX']
                }
            
            combinaciones.append(nueva_fila)

        df_delta_DOD = pd.DataFrame(combinaciones)

        # Renombrar y reordenar las columnas según lo especificado
        df_delta_DOD = df_delta_DOD.rename(columns={
            'NewValorMIN': 'Charge',
            'NewValorMAX': 'Discharge',
            't_MAX': 'Cycle_Start_Time',
            'SoC': 'Ending_SoC',
            't_MIN': 'Cycle_End_Time',
            'MIN': 'Starting_SoC_c',
            'MAX': 'Starting_SoC_d',
            'e_MAX': 'Delta_DOD_d',
            'e_MIN': 'Delta_DOD_c'
        })

        # Reordenar las columnas
        df_delta_DOD = df_delta_DOD[[
            'Discharge',
            'Charge',
            'Cycle_Start_Time',
            'Starting_SoC_c',
            'Starting_SoC_d',
            'Ending_SoC',
            'Cycle_End_Time',
            'Delta_DOD_d',
            'Delta_DOD_c'
        ]]

        ##############################################
        # Cycle-life curve for a sample battery system
        ##############################################
        
        # Parámetros ajustados
        beta_0 = 915.7320358375723
        beta_1 = 1.6
        beta_2 = 1.905

        # beta_0 = 914.7320358375723, beta_1 = 1.5917293278982396, beta_2 = 1.8411987529010783

        beta_0 = 914.7320358375723
        beta_1 = 1.5917293278982396
        beta_2 = 1.8411987529010783

        # Función para calcular la vida útil del ciclo (CL) en función de la profundidad de descarga (DOD)
        def cycle_life(DOD, beta_0, beta_1, beta_2):
            return  beta_0 * DOD ** -beta_1 * np.exp(beta_2 * (1 - DOD))

        # Crear la columna Delta_DOD
        df_delta_DOD['Delta_DOD'] = (df_delta_DOD['Delta_DOD_d'] + df_delta_DOD['Delta_DOD_c'])

        # Calcular Cycle_Life_Delta_DOD
        df_delta_DOD['Cycle_Life_Delta_DOD'] = cycle_life(df_delta_DOD['Delta_DOD'], beta_0, beta_1, beta_2)

        # Calcular Fraq_Life y formatear con 6 decimales
        df_delta_DOD['Fraq_Life'] = 1 / df_delta_DOD['Cycle_Life_Delta_DOD']
        df_delta_DOD['Fraq_Life'] = df_delta_DOD['Fraq_Life'].astype(float)  # Asegurarse de que los valores sean numéricos

        # Sumar todos los elementos de la columna 'Fraq_Life'
        Fractional_life_consumed = df_delta_DOD['Fraq_Life'].sum()

        # Calcular el valor de 1/Fractional_life_consumed y guardarlo en 'Expected_Life'
        Expected_Life = 1 / Fractional_life_consumed
        
        f2 = Fractional_life_consumed
    # print(f"f2_1: {f2}")

    else:  
        print(" ==SOS==SOS==| df_SoC_delta_DoD is EMPTY |==SOS==SOS==") 
        f2 = 0

    factor_escalabilidad = 8760 / (ultima_hora - primera_hora + 1)
    f2 = f2 * factor_escalabilidad * 100 
    
    # print(f"f2_1: {f2}")
    
    # return f2, df_delta_DOD, Expected_Life
    #endregion
    
    #########################################
    
    # print(f"h:{h} num_dato:{num_dato} df_info_STK: \n{df_info_STK}")


    #########################################

    Svc = 'PS'

    #------------------- Porcentaje de Picos Afeitados

    # Filtrar las columnas requeridas y crear una copia del DataFrame llamado df_PS_metrica
    df_PS_metrica = df_info_STK[['hr', 'Col_SoC',  'name_policy', 'P_3f_cb_302', 'P_3f_cb_302_BESS_0']].copy()

    # Crear la nueva columna 'm_PS_BESS' usando .loc para evitar el SettingWithCopyWarning
    df_PS_metrica.loc[:, 'm_PS'] = df_PS_metrica['P_3f_cb_302_BESS_0'].apply(lambda x: 1 if x > threshold_peak_demand else 0)
    tolerancia = 0.001
    df_PS_metrica['m_PS_BESS'] = df_PS_metrica.apply(
        lambda row: 0 if row['m_PS'] != 1 else (1 if abs(row['P_3f_cb_302'] - row['P_3f_cb_302_BESS_0']) > tolerancia else 0), 
        axis=1
    )

    # print(f"df_PS_metrica: \n{df_PS_metrica}")
    s_m_PS = df_PS_metrica['m_PS'].sum()
    print(f"s_m_PS: {s_m_PS}")
    s_m_PS_BESS = df_PS_metrica['m_PS_BESS'].sum()
    print(f"s_m_PS_BESS: {s_m_PS_BESS}")
    pct_m_PS = (s_m_PS_BESS / s_m_PS) * 100
    print(f"pct_m_PS: {pct_m_PS}%")
    end_time = time.time()  # Detener el cronómetro
    elapsed_time = (end_time - start_time) / 60   # Calcular el tiempo transcurrido

    #########################################

    df_threshold_analysis = df_info_STK[['P_3f_cb_302_BESS_0']].nlargest(10, 'P_3f_cb_302_BESS_0')
    print(f"df_threshold_analysis:\n{df_threshold_analysis}\n")
    P_CB_max = df_threshold_analysis['P_3f_cb_302_BESS_0'].max()
    #########################################
    #------------------- f6

    ω1 = 0.5
    ω2 = 0.5
    Total_Investment_max = 1744800
    pct_m_PS_max         = 100

    f5_PS = ω1*(Total_Investment/Total_Investment_max) + ω2*(1 - pct_m_PS/pct_m_PS_max)
    print(f"f5_PS = ω1*(Total_Investment/Total_Investment_max) + ω2*(pct_m_PS/pct_m_PS_max)")
    print(f"f5_PS = {ω1}*({Total_Investment}/{Total_Investment_max}) + {ω2}*({pct_m_PS}/{pct_m_PS_max})")
    print(f"f5_PS = {ω1*(Total_Investment/Total_Investment_max)} + {ω2*(pct_m_PS/pct_m_PS_max)}")

    ##
    sum_P_bid_h = df_info_STK['P_bid_h'].sum()
    count_non_zero_P_bid_h = (df_info_STK['P_bid_h'] != 0).sum()

    print(f"Suma de P_bid_h: {sum_P_bid_h}")
    print(f"Cantidad de elementos diferentes de 0 en P_bid_h: {count_non_zero_P_bid_h}")

        #########################################
    # Calcular el porcentaje de cada valor en la columna name_policy
    percentages = df_info_STK['name_policy'].value_counts(normalize=True) * 100

    # Inicializar variables de porcentaje para cada política
    p_1 = p_2 = p_3 = p_4 = p_5 = 0

    # Almacenar los porcentajes de cada valor (1, 2, 3, 4, 5) en las variables correspondientes
    for value, percentage in percentages.items():
        if value == 1:
            p_1 = percentage
        elif value == 2:
            p_2 = percentage
        elif value == 3:
            p_3 = percentage
        elif value == 4:
            p_4 = percentage
        elif value == 5:
            p_5 = percentage

    #########################################

    # Imprimir los porcentajes almacenados
    print(f"Porcentaje de p_1: {p_1:.2f}%")
    print(f"Porcentaje de p_2: {p_2:.2f}%")
    print(f"Porcentaje de p_3: {p_3:.2f}%")
    print(f"Porcentaje de p_4: {p_4:.2f}%")
    print(f"Porcentaje de p_5: {p_5:.2f}%")


    print("-" * 40) 
    print(f"Servicio         \t   : {Svc} \t ")
    print(f"Primera Hora     \t   : {primera_hora:.0f} \t ")
    print(f"Última  Hora     \t   : {ultima_hora:.0f}  \t ")
    print(f"BatteryNode:     \t   : {BatteryNode}")
    print(f"CB_Monitored:    \t   : {CB_Monitored}")
    print(f"threshold_peak_demand: \t   : {threshold_peak_demand} \t kW")
    print(f"P_CB_max:        \t   : {P_CB_max} \t kW")
    print(f"P_BESS:          \t   : {P_BESS} \t kW")
    print(f"E_BESS:          \t   : {E_BESS} \t kWh")
    print(f"annual_revenue:  \t   : {annual_revenue:.5f} \t USD")
    print(f"f1\t Payback     \t   : {f1:.5f} \t years")
    print(f"f2\t BESS Life   \t   : {f2:.5f} \t %")
    print(f"f3\t Total Losses\t   : {f3:.5f} \t %")
    print(f"f4\t Estabilidad \t   : {f4:.5f} \t %")
    print(f"f5\t ISV         \t   : {f5:.5f} \t %")
    print(f"f6\t ICV         \t   : {f6:.5f} \t %")
    print(f"f_i_1\t I2_I1    \t   : {f_i_1:.5f} \t %")
    print(f"f_i_2\t I0_I1    \t   : {f_i_2:.5f} \t %")
    print(f"f_i_3\t Normal   \t   : {f_i_3:.5f} \t %")   
    print(f"s_m_PS           \t   : {s_m_PS:.0f} \t ")
    print(f"s_m_PS_BESS      \t   : {s_m_PS_BESS:.0f} \t ") 
    print(f"pct_m_PS         \t   : {pct_m_PS:.5f} \t %")
    print(f"p_1              \t   : {p_1:.5f} \t %")
    print(f"p_2              \t   : {p_2:.5f} \t %")
    print(f"p_3              \t   : {p_3:.5f} \t %")
    print(f"p_4              \t   : {p_4:.5f} \t %")
    print(f"p_5              \t   : {p_5:.5f} \t %")
    print(f"f5_PS            \t   : {f5_PS:.5f} \t p.u.")
    print(f"Elapsed Time:    \t   : {elapsed_time} minutes")
    print(f"End Time         \t   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔹" * 40) 
    return Svc, df_info_STK, Total_Investment, annual_revenue, f1, f2 ,f3, f4, f5, f6, f_i_1, f_i_2, f_i_3, s_m_PS, s_m_PS_BESS, pct_m_PS, f5_PS, threshold_peak_demand, P_CB_max, p_1, p_2, p_3, p_4, p_5


####################################################################
##==================== B E S S    T E S T   ==========================

# import time

# n_dc = 0.9           # eficiencia de descarga
# n_ch = 0.9          # eficiencia de descarga
# BatteryNode = 'bus3076'

# # # ================== Parámetros Financieros

# USD_kW = 145 #245                 # USD/kW
# USD_kWh = 245 #345                # USD/kWh
# annual_discount_rate = 0.02  # 2%

# # # ------------ Hour Cases ------------

# # # -------- FR
# # # P_BESS = 100 
# # # E_BESS = 1000
# # # primera_hora = 1 
# # # ultima_hora =  168


# # # # -------- PS
# P_BESS = 300 
# E_BESS = 1800
# primera_hora = 4441 
# ultima_hora =  4608

# # # # -------- STK FR PS
# # # P_BESS = 400            # kW
# # # E_BESS = 2000           # kWh
# # # primera_hora = 1 
# # # ultima_hora =  12

# # # # -------- STK FR PS
# # # # primera_hora = 1 
# # # # ultima_hora =  24

# # # annual_discount_rate = 0.5

# # # #Test Case C: 4344 + 168 = 4512

# # start_time = time.time()

# df_info_STK, annual_revenue, f1, f2 ,f3, f4, f5, f6, f_i_1, f_i_2, f_i_3 = f_BESS_Sv_PS(P_BESS, E_BESS, n_dc, n_ch, BatteryNode, primera_hora, ultima_hora, annual_discount_rate, USD_kW, USD_kWh)

# print(f"df_info_STK: \n{df_info_STK.head()}")
# print(f"annual_revenue: {annual_revenue}")
# print(f"f1: {f1:.5f}")
# print(f"f2: {f2:.5f}")
# print(f"f3: {f3:.5f}")
# print(f"f4: {f4:.5f}")
# print(f"f5: {f5:.5f}")
# print(f"f6: {f6:.5f}")

# end_time = time.time()

# # Calcular e imprimir el tiempo de ejecución
# execution_time = end_time - start_time
# print(f"Tiempo de ejecución: {execution_time} segundos")

