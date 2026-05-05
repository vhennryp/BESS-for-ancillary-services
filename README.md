# Multi-Objective Placement and Sizing of Battery Energy Storage Systems for Stackable Services

This repository contains the code, data, and simulation framework associated with the paper **“Multi-Objective Placement and Sizing of Battery Energy Storage Systems for Stackable Services.”**

The project proposes a multi-objective approach to determine the optimal placement and sizing of Battery Energy Storage Systems (BESS) in distribution systems. The BESS can provide ancillary services individually or as stackable services, including frequency regulation and peak-shaving.

## Overview

Battery Energy Storage Systems can improve the flexibility, reliability, and operational performance of distribution systems. However, their high investment cost requires planning strategies that account for financial return, technical impact, and operational performance.

This work evaluates BESS placement and sizing considering the following aspects:

- **Financial:** payback period associated with the investment and revenues from frequency regulation.
- **Operational:** BESS degradation and service provision performance.
- **Technical:** impact on voltage deviation and current unbalance in the distribution system.
- **Service stacking:** coordinated provision of frequency regulation and peak-shaving services.

The methodology evaluates candidate BESS sizes and installation nodes using a brute-force algorithm. Non-dominated solutions are identified through Pareto optimality, and representative solutions are selected using a k-means++ clustering approach.

## Methodology

The proposed framework consists of the following stages:

1. **Definition of the search space:**  
   Commercial BESS sizes are combined with candidate installation nodes in the distribution system.

2. **Simulation of ancillary services:**  
   Each BESS solution is simulated under different service configurations:
   - Frequency regulation
   - Peak-shaving
   - Stackable services combining frequency regulation and peak-shaving

3. **Multi-objective assessment:**  
   The solutions are evaluated using objective functions related to:
   - Payback period
   - BESS degradation
   - Voltage deviation
   - Current unbalance
   - Peak-shaving performance

4. **Pareto optimality:**  
   Non-dominated solutions are identified for each ancillary service.

5. **Representative solution selection:**  
   k-means++ clustering is applied to the Pareto fronts to select representative BESS placement and sizing solutions.

## Test Case

The methodology is tested on a real 240-node three-phase distribution system using OpenDSS and Python. The simulations consider:

- One year of operation
- Historical PJM frequency regulation signals and market prices
- Hourly load profiles
- Commercial BESS sizes
- Frequency regulation, peak-shaving, and stackable service operation
- Power-quality indicators obtained from AC power-flow simulations

## Results and Conclusions

The results show that the optimal BESS size depends on the ancillary service and market rules. Across the analyzed services, the 3000 kWh / 750 kW BESS appears frequently among the Pareto-optimal solutions.

Regarding placement, the Pareto-optimal solutions tend to concentrate around nodes 2016, 2017, and 2018. This pattern is related to the proximity of these nodes to the most unbalanced three-phase lines in the distribution system, indicating that current unbalance plays an important role in determining optimal BESS placement.

The results demonstrate that the proposed framework can support strategic planning decisions for BESS integration in distribution systems, especially when ancillary services are provided individually or in a stacked manner.

## Repository and Reproducibility

The code, data, and simulation models used in this study are provided in this repository to support reproducibility and further research.

The simulations were implemented in Python and OpenDSS, using OpenDSSDirect.py as the interface between the Python environment and the OpenDSS computational engine.

## Installation and Usage

The installation and usage instructions will be updated in the coming hours.

This section will include the required dependencies, the `requirements.txt` file, and the instructions needed to run the simulations and reproduce the results.

## Contributing

Contributions, suggestions, and bug reports are welcome. Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.
