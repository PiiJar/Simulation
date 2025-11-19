# Simulation Project Overview

## Purpose
This simulation models a production line for batch-based industrial processing. Its main goal is to generate optimized schedules for material transporters and processing stations, ensuring efficient throughput, conflict-free operation, and adherence to process constraints.

## Input Data
The simulation receives:
- **Batch treatment programs**: CSV files describing each batch's required process stages, timing windows, and station assignments.
- **Transporter and station configuration**: Details of available transporters, stations, their physical layout, and movement times.
- **Initial production state**: Starting positions and times for all batches and resources.
- **Process constraints**: Minimum/maximum times per stage, changeover times, deadhead (empty run) times, and spatial collision limits.

## Output Data
The simulation produces:
- **Optimized batch schedules**: CSV files with entry/exit times for each batch at every stage and station.
- **Transporter movement schedules**: CSV files detailing all transporter tasks, including start/end times and station transitions.
- **Conflict reports**: CSV files listing any infeasible or conflicting assignments (if present).
- **Visualizations**: Gantt charts and summary plots of the schedule.
- **PDF report**: A comprehensive summary of the simulation results.

## Implementation
- **Language**: Python 3
- **Main libraries**:
  - `ortools` (Google OR-Tools): Constraint programming solver for schedule optimization.
  - `pandas`: Data manipulation and CSV I/O.
  - `numpy`: Numerical operations and array handling.
  - `matplotlib`: Visualization and plotting.
  - `fpdf2`: PDF report generation.
- **Project structure**: Modular pipeline with separate scripts for matrix generation, transporter task extraction, conflict resolution, schedule stretching, program updating, and visualization.
- **Execution**: Controlled via `main.py`, which runs the full pipeline and saves all outputs to a timestamped directory.

## Functionality
- Reads all input data and constraints, builds a mathematical model of the production line.
- Uses constraint programming to optimize batch and transporter schedules, respecting all timing and physical constraints.
- Validates the solution for station and transporter conflicts, and generates detailed reports and visualizations for analysis.

---
For further details, see the source code and individual module documentation.
## GitHub Usage

This project uses GitHub for version control and collaboration. Key concepts:

- **Repository (repo):** Central storage for all project files, history, and collaboration tools. Tracks every change and enables teamwork.
- **Version control:** Every change (commit) is saved with a timestamp and author, allowing you to revert to earlier versions and see who did what.
- **Branches:** Separate lines of development for features or fixes. For example, `main` for stable releases and `feature-x` for new work. Changes are merged when ready.
- **Commits:** Snapshots of changes, each with a descriptive message.
- **Push and pull:**
  - *Push* uploads your local commits to GitHub.
  - *Pull* downloads the latest changes from GitHub to your computer.
- **Collaboration:** Code review, discussion, and conflict resolution are managed via pull requests and comments.

GitHub ensures safe, traceable development and makes it easy to work together and maintain a complete history of all changes.