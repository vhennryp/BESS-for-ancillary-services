# BESS Service Simulation Figures

## Disclaimer

This repository is currently being updated to include all the resources required to reproduce the main results presented in the paper.

At this stage, only the results related to the Frequency Regulation service can be reproduced. The main implementation file for this service is `f_BESS_Sv_FR.py`. The following notebooks can be executed to reproduce the corresponding figures:

- `FR_Fig_07_BESS_Size_Options.ipynb`
- `FR_Fig_08a_Annual_Operation.ipynb`
- `FR_Fig_08b_Monthly_Operation.ipynb`
- `FR_Fig_09_Weekly_Operation.ipynb`

The remaining service cases, namely Peak Shaving and Stacked Service, will be completed and documented in the next update.

This folder contains the notebooks and Python functions used to reproduce the
paper figures for three BESS services:

- `FR`: frequency regulation, implemented in `f_BESS_Sv_FR.py`
- `PS`: peak shaving, implemented in `f_BESS_Sv_PS.py`
- `STK`: stacked service, implemented in `f_BESS_Sv_STK.py`

The BESS configuration varies by power capacity, energy capacity, and placement.
Each notebook fixes one service and one figure context, runs or loads the
corresponding operation data, and writes the figure outputs to a dedicated
folder.

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
