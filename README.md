# BESS Service Simulation Figures

This folder contains the notebooks and Python functions used to reproduce the
paper figures for three BESS services:

- `FR`: frequency regulation, implemented in `f_BESS_Sv_FR.py`
- `PS`: peak shaving, implemented in `f_BESS_Sv_PS.py`
- `STK`: stacked service, implemented in `f_BESS_Sv_STK.py`

The BESS configuration varies by power capacity, energy capacity, and placement.
Each notebook fixes one service and one figure context, runs or loads the
corresponding operation data, and writes the figure outputs to a dedicated
folder.

## Figure Map

| Service | Figure | Notebook | Output folder |
| --- | ---: | --- | --- |
| FR | 7 | `FR_Fig_07_BESS_Size_Options.ipynb` | `FR_Fig_07_BESS_Option_Sizes` |
| FR | 8 prev | `FR_Fig_08_orev_Annual_Operation.ipynb` | root CSV output |
| FR | 8 | `FR_Fig_08_Monthly_Operation.ipynb` | `File` |
| FR | 9 | `FR_Fig_09_Weekly_Operation.ipynb` | `FR_Fig_09_Weekly_Operation` |
| PS | 11 | `PS_Fig_11_BESS_Size_Options.ipynb` | `PS_Fig_11_BESS_Option_Sizes` |
| PS | 12 | `PS_Fig_12_Monthly_Operation.ipynb` | `PS_Fig_12_Monthly_Operation` |
| PS | 13 | `PS_Fig_13_Weekly_Operation.ipynb` | `PS_Fig_13_Weekly_Operation` |
| STK | 15 | `STK_Fig_15_BESS_Size_Options.ipynb` | `STK_Fig_15_BESS_Option_Sizes` |
| STK | 16 | `STK_Fig_16_Monthly_Operation.ipynb` | `STK_Fig_16_Monthly_Operation` |
| STK | 17 | `STK_Fig_17_Weekly_Operation.ipynb` | `STK_Fig_17_Weekly_Operation` |

`reproducibility.py` centralizes these output folders and the mapping from
service names to simulation functions. The existing notebooks can continue to
run as before; new notebooks should prefer importing helpers from that module.

## Main Data Inputs

- Annual operation files: `One_year_FR.csv`, `One_year_PS.csv`, `One_year_STK.csv`
- Sizing options: `Data_BESS_Size_Options/df_<SERVICE>_h_1to8760.csv`
- Network and OpenDSS files: `Required_Files/`

## Suggested Execution Order

0. Create an environment and install the Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

1. Run the one-year simulation notebook for the service if the corresponding
   `One_year_<SERVICE>.csv` needs to be regenerated.
2. Run the sizing notebook for that service.
3. Run the monthly, weekly, and annual operation notebooks.

For FR, run `FR_Fig_08_orev_Annual_Operation.ipynb` first. It generates
`Annual_Op_bus2017_2000kWh_500kW.csv`, which is then loaded by
`FR_Fig_08_Monthly_Operation.ipynb`.

## One-Year Simulation Notebooks

The one-year simulation notebooks are named with the service and the selected
BESS solution:

| Service | Notebook | Placement | Energy | Power |
| --- | --- | --- | ---: | ---: |
| FR | `OneYearSimulation_FR_bus2017_2000kWh_500kW.ipynb` | `bus2017` | 2000 kWh | 500 kW |
| PS | `OneYearSimulation_PS_bus2028_1000kWh_250kW.ipynb` | `bus2028` | 1000 kWh | 250 kW |
| STK | `OneYearSimulation_STK_bus3007_3000kWh_750kW.ipynb` | `bus3007` | 3000 kWh | 750 kW |

Each notebook passes `SoC_i` explicitly to its service function and writes both
the canonical `One_year_<SERVICE>.csv` file and a solution-specific CSV file.
