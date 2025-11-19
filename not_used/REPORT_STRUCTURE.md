# Simulaatioraportin rakenne ja datavaatimukset

**Päivitetty:** 13.11.2025  
**Tarkoitus:** Määritellä raportin sisältörakenne ja `prepare_report_data.py`-funktion tuottama data

---

## 1. Raportin rakenne

### 1.1 Etusivu (Cover Page)
**Sisältö:**
- Otsikko: "Production Line Simulation Report"
- Asiakastiedot (Customer name)
- Tehdas/linja (Plant name)
- Simulaation aikaleima (timestamp)
- Versiotiedot (ohjelmisto, algoritmi)
- Logo/branding (valinnainen)

**Data-tarpeet:**
```json
{
  "cover_page": {
    "title": "Production Line Simulation Report",
    "customer": "900135 - Factory X",
    "plant": "Nammo Zinc-Phosphating",
    "timestamp": "2025-11-12 11:21:26",
    "report_date": "2025-11-13",
    "software_version": "2.0",
    "algorithm": "Two-Phase CP-SAT Optimization",
    "snapshot_folder": "900135_-_Factory_X_-_Nammo_Zinc-Phosphating_2025-11-12_11-21-26"
  }
}
```

---

### 1.2 Sisällysluettelo (Table of Contents)
**Sisältö:**
- Automaattisesti generoitu sisällysluettelo kaikista pääkohdista
- Sivunumerot (PDF) tai ankkurilinkit (HTML)

**Data-tarpeet:**
```json
{
  "table_of_contents": {
    "sections": [
      {"title": "Executive Summary", "page": 2},
      {"title": "Input Parameters", "page": 3},
      {"title": "Simulation Results", "page": 5},
      {"title": "Analysis", "page": 12},
      {"title": "Conclusions", "page": 18},
      {"title": "Appendices", "page": 20}
    ]
  }
}
```

---

### 1.3 Lopputulosten nostot (Executive Summary)
**Sisältö:**
- Keskeiset tunnusluvut (KPI:t) korostettuina
- Tuotannon tehokkuus ja pullonkaulat
- Kriittiset löydökset ja suositukset
- Yhteenveto optimoinnin tuloksista

**Data-tarpeet:**
```json
{
  "executive_summary": {
    "key_metrics": {
      "total_batches": 10,
      "total_production_time_hours": 8.45,
      "average_lead_time_hours": 6.32,
      "max_lead_time_hours": 7.89,
      "min_lead_time_hours": 4.21,
      "line_utilization_percent": 87.3,
      "makespan_hours": 8.45
    },
    "bottlenecks": [
      {
        "station_number": 108,
        "station_name": "Activation",
        "utilization_percent": 98.5,
        "waiting_time_total_minutes": 145.2,
        "severity": "critical"
      },
      {
        "station_number": 115,
        "station_name": "Hot Water Rinse",
        "utilization_percent": 92.1,
        "waiting_time_total_minutes": 89.7,
        "severity": "moderate"
      }
    ],
    "optimization_results": {
      "phase_1": {
        "status": "OPTIMAL",
        "solve_time_seconds": 12.45,
        "objective_value": 30420,
        "conflicts_resolved": 23
      },
      "phase_2": {
        "status": "OPTIMAL",
        "solve_time_seconds": 8.73,
        "objective_value": 28950,
        "schedule_improvements": "Minimized transporter travel and waiting times"
      }
    },
    "critical_findings": [
      "Station 108 (Activation) is the primary bottleneck at 98.5% utilization",
      "Transporter 1 has 12% idle time which could be optimized",
      "Average batch lead time is 6.32 hours with good consistency"
    ],
    "recommendations": [
      "Consider adding parallel capacity at Station 108",
      "Review treatment times for stages using Station 108",
      "Optimize transporter task allocation to reduce idle time"
    ]
  }
}
```

---

### 1.4 Simulaation lähtötiedot (Input Parameters)
**Sisältö:**
- Tuotantoerien määrä ja saapumisajat
- Asemakonfiguraatio (stations table)
- Nosturikonfiguraatio (transporters)
- Käsittelyohjelmat (treatment programs)
- Fysiikkaparametrit (nopeudet, kiihtyvyydet)
- Optimointiparametrit

**Data-tarpeet:**
```json
{
  "input_parameters": {
    "production_batches": {
      "total_batches": 10,
      "batch_list": [
        {
          "batch_id": 1,
          "entry_time_seconds": 0,
          "treatment_program": "001",
          "total_stages": 14
        }
        // ... (kaikki batchit)
      ],
      "source_file": "production.csv"
    },
    "stations_configuration": {
      "total_stations": 21,
      "stations": [
        {
          "number": 101,
          "group": 1,
          "name": "Loading Station",
          "x_position": 0,
          "dropping_time_seconds": 0.0,
          "device_delay_seconds": 0.0,
          "transporter_1_lift": true,
          "transporter_1_sink": true,
          "transporter_2_lift": false,
          "transporter_2_sink": false
        }
        // ... (kaikki asemat)
      ],
      "source_file": "stations.csv"
    },
    "transporter_configuration": {
      "total_transporters": 2,
      "transporters": [
        {
          "transporter_id": 1,
          "name": "Transporter 1",
          "color": "#1f77b4",
          "start_position": 101,
          "lift_zone": {"min": 101, "max": 111},
          "sink_zone": {"min": 101, "max": 114},
          "max_speed_mps": 0.5,
          "acceleration_mps2": 0.2,
          "deceleration_mps2": 0.2
        },
        {
          "transporter_id": 2,
          "name": "Transporter 2",
          "color": "#2ca02c",
          "start_position": 118,
          "lift_zone": {"min": 112, "max": 118},
          "sink_zone": {"min": 111, "max": 118},
          "max_speed_mps": 0.5,
          "acceleration_mps2": 0.2,
          "deceleration_mps2": 0.2
        }
      ],
      "source_files": ["transporters.csv", "transporters_physics.csv", "transporters_task_areas.csv"]
    },
    "treatment_programs": {
      "programs": [
        {
          "program_id": "001",
          "name": "Zinc Phosphating Standard",
          "total_stages": 14,
          "stages": [
            {
              "stage": 1,
              "station": 107,
              "treatment_time_seconds": 300,
              "description": "Degreasing"
            }
            // ... (kaikki vaiheet)
          ],
          "source_file": "treatment_program_001.csv"
        }
      ]
    },
    "optimization_parameters": {
      "algorithm": "Two-Phase CP-SAT",
      "phase_1_objective": "Minimize total makespan and conflicts",
      "phase_2_objective": "Minimize transporter travel time and waiting",
      "time_limit_seconds": 300,
      "num_workers": 8
    }
  }
}
```

---

### 1.5 Simulaation tulokset (Simulation Results)
**Sisältö:**
- Batch-kohtaiset tulokset (taulukko)
- Gantt-kaavio (timeline visualization)
- Nostureiden käyttöprofiilit (transporter profiles)
- Asemien käyttöasteet (station utilization)
- Aikajanat ja metriikat

**Data-tarpeet:**
```json
{
  "simulation_results": {
    "batch_results": {
      "batches": [
        {
          "batch_id": 1,
          "entry_time_seconds": 0,
          "exit_time_seconds": 22764,
          "total_stages": 14,
          "lead_time_hours": 6.32,
          "waiting_time_total_seconds": 1245,
          "processing_time_total_seconds": 21519,
          "status": "completed"
        }
        // ... (kaikki batchit)
      ],
      "statistics": {
        "average_lead_time_hours": 6.32,
        "std_dev_lead_time_hours": 0.87,
        "min_lead_time_hours": 4.21,
        "max_lead_time_hours": 7.89
      }
    },
    "gantt_chart": {
      "figure_path": "reports/figures/gantt_chart.png",
      "total_timespan_hours": 8.45,
      "overlapping_tasks": 0,
      "conflicts_detected": 0
    },
    "transporter_profiles": [
      {
        "transporter_id": 1,
        "figure_path": "reports/figures/transporter_1_profile.png",
        "total_tasks": 28,
        "total_distance_meters": 1456.3,
        "total_travel_time_seconds": 3245,
        "idle_time_seconds": 1289,
        "utilization_percent": 88.2,
        "task_breakdown": {
          "lift_tasks": 14,
          "sink_tasks": 14
        }
      },
      {
        "transporter_id": 2,
        "figure_path": "reports/figures/transporter_2_profile.png",
        "total_tasks": 24,
        "total_distance_meters": 987.6,
        "total_travel_time_seconds": 2156,
        "idle_time_seconds": 2341,
        "utilization_percent": 76.5,
        "task_breakdown": {
          "lift_tasks": 12,
          "sink_tasks": 12
        }
      }
    ],
    "station_utilization": {
      "stations": [
        {
          "station_number": 107,
          "station_name": "Degreasing",
          "total_occupancy_seconds": 3000,
          "utilization_percent": 98.5,
          "number_of_visits": 10,
          "average_processing_time_seconds": 300
        }
        // ... (kaikki asemat)
      ],
      "figure_path": "reports/figures/station_utilization_chart.png"
    },
    "timeline_metrics": {
      "makespan_seconds": 30420,
      "makespan_hours": 8.45,
      "first_batch_entry": 0,
      "last_batch_exit": 30420,
      "peak_simultaneous_batches": 4,
      "average_batches_in_system": 2.3
    }
  }
}
```

---

### 1.6 Tulosten analyysi (Analysis)
**Sisältö:**
- Pullonkaulojen analysointi
- Nostureiden tehokkuus ja optimointipotentiaali
- Asemien käyttöasteiden vertailu
- Odotusaikojen ja viiveiden analyysi
- "What-if" -skenaariot (valinnainen)

**Data-tarpeet:**
```json
{
  "analysis": {
    "bottleneck_analysis": {
      "primary_bottleneck": {
        "station_number": 108,
        "station_name": "Activation",
        "utilization_percent": 98.5,
        "total_waiting_time_caused_minutes": 145.2,
        "batches_affected": 9,
        "recommendation": "Consider adding parallel capacity or reducing treatment time"
      },
      "secondary_bottlenecks": [
        {
          "station_number": 115,
          "station_name": "Hot Water Rinse",
          "utilization_percent": 92.1,
          "impact": "moderate"
        }
      ],
      "figure_path": "reports/figures/bottleneck_analysis.png"
    },
    "transporter_efficiency": {
      "overall_utilization_percent": 82.4,
      "transporter_comparison": [
        {
          "transporter_id": 1,
          "utilization_percent": 88.2,
          "idle_time_percent": 11.8,
          "average_travel_distance_meters": 52.0,
          "optimization_potential": "Low - well utilized"
        },
        {
          "transporter_id": 2,
          "utilization_percent": 76.5,
          "idle_time_percent": 23.5,
          "average_travel_distance_meters": 41.2,
          "optimization_potential": "Moderate - consider task rebalancing"
        }
      ],
      "recommendations": [
        "Transporter 2 could handle additional tasks during idle periods",
        "Consider dynamic task allocation to balance workload"
      ]
    },
    "waiting_time_analysis": {
      "total_waiting_time_minutes": 234.9,
      "waiting_time_by_cause": [
        {
          "cause": "Station occupied",
          "total_minutes": 145.2,
          "percentage": 61.8
        },
        {
          "cause": "Transporter unavailable",
          "total_minutes": 67.3,
          "percentage": 28.6
        },
        {
          "cause": "Schedule constraints",
          "total_minutes": 22.4,
          "percentage": 9.6
        }
      ],
      "figure_path": "reports/figures/waiting_time_breakdown.png"
    },
    "station_load_distribution": {
      "balanced_stations": 15,
      "underutilized_stations": 4,
      "overutilized_stations": 2,
      "recommendations": [
        "Stations 101, 102, 121 have <30% utilization - consider consolidation",
        "Stations 108, 115 have >90% utilization - monitor for capacity issues"
      ],
      "figure_path": "reports/figures/station_load_distribution.png"
    },
    "optimization_effectiveness": {
      "phase_1_improvements": "Eliminated all station conflicts and minimized makespan",
      "phase_2_improvements": "Reduced transporter travel time by 15% compared to naive allocation",
      "overall_assessment": "OPTIMAL - No further improvements possible within current constraints"
    }
  }
}
```

---

### 1.7 Yhteenveto (Conclusions)
**Sisältö:**
- Simulaation onnistumisen arviointi
- Keskeisten tavoitteiden saavuttaminen
- Jatkotoimenpide-ehdotukset
- Rajoitukset ja oletukset
- Validointitulokset

**Data-tarpeet:**
```json
{
  "conclusions": {
    "simulation_success": {
      "status": "SUCCESS",
      "all_batches_completed": true,
      "conflicts_detected": 0,
      "schedule_feasibility": "FEASIBLE",
      "optimization_convergence": "OPTIMAL"
    },
    "objectives_achieved": [
      {
        "objective": "Minimize total production time (makespan)",
        "target": "< 9 hours",
        "achieved": "8.45 hours",
        "status": "MET"
      },
      {
        "objective": "Maximize line utilization",
        "target": "> 80%",
        "achieved": "87.3%",
        "status": "MET"
      },
      {
        "objective": "Balance transporter workload",
        "target": "< 20% difference",
        "achieved": "11.7% difference",
        "status": "MET"
      }
    ],
    "recommendations_summary": [
      "SHORT-TERM: Monitor Station 108 utilization and add capacity if batches increase",
      "MEDIUM-TERM: Optimize Transporter 2 task allocation to reduce idle time",
      "LONG-TERM: Consider treatment time reductions at high-utilization stations"
    ],
    "limitations": [
      "Simulation assumes perfect equipment reliability (no breakdowns)",
      "Treatment times are fixed and do not account for temperature/chemistry variations",
      "Transporter physics model assumes ideal conditions (no acceleration delays)",
      "Does not model operator interventions or manual overrides"
    ],
    "validation": {
      "input_data_verified": true,
      "physical_constraints_satisfied": true,
      "schedule_conflicts_resolved": true,
      "results_reviewed_by": "Simulation System v2.0",
      "validation_date": "2025-11-13"
    }
  }
}
```

---

### 1.8 Liitteet (Appendices)
**Sisältö:**
- Täydelliset taulukot (CSV-exportit)
- Tekniset parametrit
- Solver-lokit
- Algoritmikuvaukset
- Käytetyt tiedostot

**Data-tarpeet:**
```json
{
  "appendices": {
    "appendix_a_full_batch_schedule": {
      "title": "Complete Batch Schedule with All Stages",
      "csv_export_path": "reports/data/full_batch_schedule.csv",
      "description": "Detailed timeline of every batch stage with start/end times and assigned stations"
    },
    "appendix_b_transporter_tasks": {
      "title": "Complete Transporter Task List",
      "csv_export_path": "reports/data/transporter_tasks_full.csv",
      "description": "All transporter movements with timestamps, distances, and task types"
    },
    "appendix_c_solver_logs": {
      "title": "CP-SAT Solver Execution Logs",
      "phase_1_log": "reports/data/phase_1_solver.log",
      "phase_2_log": "reports/data/phase_2_solver.log",
      "description": "Detailed solver output including search statistics and solution quality"
    },
    "appendix_d_algorithm_description": {
      "title": "Two-Phase CP-SAT Optimization Algorithm",
      "content": "Detailed description of the optimization approach, constraints, and objectives",
      "reference_documents": [
        "documentation/SIMULATION_OPTIMIZATION.md",
        "documentation/REQUIREMENTS_FOR_CPSAT_1.md",
        "documentation/REQUIREMENTS_FOR_CPSAT_2.md"
      ]
    },
    "appendix_e_input_files": {
      "title": "Input Configuration Files",
      "files": [
        {"name": "production.csv", "path": "initialization/production.csv"},
        {"name": "stations.csv", "path": "initialization/stations.csv"},
        {"name": "transporters.csv", "path": "initialization/transporters.csv"},
        {"name": "treatment_program_001.csv", "path": "initialization/treatment_program_001.csv"}
      ]
    }
  }
}
```

---

## 2. Kansiorakenne ja tiedostot

### 2.1 Välivaiheen data-kansio
```
output/900135_.../reports/data/
├── metadata.json                    # Etusivu + perustiedot
├── executive_summary.json           # Lopputulosten nostot
├── input_parameters.json            # Lähtötiedot
├── simulation_results.json          # Tulokset
├── analysis.json                    # Analyysit
├── conclusions.json                 # Yhteenveto
├── appendices.json                  # Liitteet
├── full_batch_schedule.csv          # Liite A
├── transporter_tasks_full.csv       # Liite B
├── phase_1_solver.log               # Liite C
└── phase_2_solver.log               # Liite C
```

### 2.2 Kuvakansio
```
output/900135_.../reports/figures/
├── gantt_chart.png                  # Gantt-kaavio
├── transporter_1_profile.png        # Nosturi 1 profiili
├── transporter_2_profile.png        # Nosturi 2 profiili
├── station_utilization_chart.png    # Asemien käyttöasteet
├── bottleneck_analysis.png          # Pullonkaula-analyysi
├── waiting_time_breakdown.png       # Odotusaikaeritittely
├── station_load_distribution.png    # Asemien kuormitus
└── (muut tarvittavat kuvat)
```

---

## 3. `prepare_report_data.py` - Funktioiden vastuut

### 3.1 Pääfunktio
```python
def prepare_report_data(output_dir: str) -> dict:
    """
    Kerää kaikki raporttiin tarvittava data ja generoi kuvat.
    
    Args:
        output_dir: Polku simulaation output-kansioon
        
    Returns:
        dict: Kaikki raporttiin tarvittava data strukturoituna
    """
    data = {
        'metadata': collect_metadata(output_dir),
        'executive_summary': generate_executive_summary(output_dir),
        'input_parameters': collect_input_parameters(output_dir),
        'simulation_results': collect_simulation_results(output_dir),
        'analysis': perform_analysis(output_dir),
        'conclusions': generate_conclusions(output_dir),
        'appendices': prepare_appendices(output_dir)
    }
    
    # Tallenna kaikki JSON-tiedostot
    save_data_files(data, output_dir)
    
    # Generoi kaikki kuvat
    figures = generate_all_figures(data, output_dir)
    
    return data, figures
```

### 3.2 Osafunktiot

#### collect_metadata()
- Lukee kansion nimen ja parsee siitä asiakastiedot
- Kerää timestampit
- Lataa versiotiedot

#### generate_executive_summary()
- Laskee kaikki KPI:t
- Tunnistaa pullonkaulat
- Lataa solver-tulokset
- Generoi kriittiset löydökset ja suositukset

#### collect_input_parameters()
- Lukee initialization/-kansion CSV-tiedostot
- Parsee production.csv
- Lukee stations.csv, transporters.csv
- Lataa treatment program -tiedostot

#### collect_simulation_results()
- Lukee optimoidut aikataulut
- Laskee batch-kohtaiset metriikat
- Kerää transporter task -data
- Laskee asemien käyttöasteet

#### perform_analysis()
- Suorittaa pullonkaula-analyysi
- Vertailee nostureiden tehokkuutta
- Analysoi odotusajat ja syyt
- Arvioi optimoinnin tuloksia

#### generate_conclusions()
- Arvioi simulaation onnistuminen
- Vertaa tavoitteisiin
- Kokoaa suositukset
- Dokumentoi rajoitukset

#### prepare_appendices()
- Kopioi relevantit CSV-tiedostot
- Kerää solver-lokit
- Luo viittaukset dokumentaatioon

#### generate_all_figures()
- Luo Gantt-kaavio
- Piirtää transporter-profiilit
- Generoi station utilization -kaaviot
- Luo kaikki analyysikuvat

---

## 4. Renderöintifunktioiden rajapinta

### 4.1 PDF Renderer
```python
def render_pdf_report(data: dict, figures: dict, output_path: str):
    """
    Renderöi PDF-raportti data- ja kuvapolkujen perusteella.
    
    Args:
        data: Kaikki raportin data (ladattu JSON-tiedostoista)
        figures: Dict jossa avain = kuvan ID, arvo = polku tiedostoon
        output_path: Minne PDF tallennetaan
    """
    pdf = EnhancedPDF(...)
    
    # Renderöi jokainen osio datasta
    render_cover_page(pdf, data['metadata'])
    render_table_of_contents(pdf, data)
    render_executive_summary(pdf, data['executive_summary'], figures)
    render_input_parameters(pdf, data['input_parameters'])
    render_simulation_results(pdf, data['simulation_results'], figures)
    render_analysis(pdf, data['analysis'], figures)
    render_conclusions(pdf, data['conclusions'])
    render_appendices(pdf, data['appendices'])
    
    pdf.output(output_path)
```

### 4.2 HTML Renderer (tulevaisuudessa)
```python
def render_html_report(data: dict, figures: dict, output_path: str):
    """
    Renderöi HTML-raportti samasta datasta.
    
    Käyttää Jinja2-templateja ja luo interaktiivisen version
    Plotly-kaavioilla ja filtteröitävillä taulukoilla.
    """
    pass
```

---

## 5. Toteutusjärjestys

1. **Vaihe 1**: Luo `prepare_report_data.py` runko
   - Määrittele kaikki collect_* funktiot
   - Toteuta JSON-tallennus
   - Testaa että data kerätään oikein

2. **Vaihe 2**: Siirrä kuvagenerointi
   - Eristä kaikki matplotlib-koodit generate_all_figures()
   - Tallenna kuvat figures/-kansioon
   - Palauta polkujen dict

3. **Vaihe 3**: Refaktoroi PDF-renderöinti
   - Muuta generate_enhanced_report.py lukemaan data JSON:sta
   - Muuta kuvien upotus käyttämään figures/-polkuja
   - Testaa että PDF näyttää samalta

4. **Vaihe 4**: Lisää uudet analyysit
   - Toteuta bottleneck_analysis
   - Lisää waiting_time_analysis
   - Luo uudet visualisoinnit

5. **Vaihe 5**: HTML-renderöinti (valinnainen)
   - Luo HTML-template
   - Lisää interaktiiviset kaaviot
   - Testaa eri selaimilla

---

## 6. Hyödyt uudesta rakenteesta

### 6.1 Kehittäjälle
- **Debuggaus**: Voit tarkastaa välivaiheen datan ilman PDF:ää
- **Testaus**: Jokainen osafunktio testattavissa erikseen
- **Ylläpito**: Selkeä vastuunjako funktioiden välillä
- **Laajennus**: Uudet analyysit/kuvat helppo lisätä

### 6.2 Käyttäjälle
- **Joustavuus**: Sama data → PDF, HTML, Excel
- **Nopeus**: Voi generoida uusia raportteja muuttamatta dataa
- **Läpinäkyvyys**: JSON-data on ihmisluettavaa
- **Integraatiot**: Data helppo viedä muihin järjestelmiin

### 6.3 Projektille
- **Modulaarisuus**: Eristetyt komponentit
- **Skaalautuvuus**: Helppo lisätä uusia raporttityyppejä
- **Dokumentointi**: Data-rakenne on itsessään dokumentaatiota
- **Versionhallinta**: Kaikki muutokset näkyvät selkeästi

---

## 7. Seuraavat askeleet

1. **Hyväksyntä**: Tarkista että rakenne vastaa tarpeitasi
2. **Priorisointi**: Mitkä osiot ovat kriittisimmät?
3. **Aloitus**: Luodaanko `prepare_report_data.py` runko?
4. **Testaus**: Millä datalla testaamme?
5. **Iteraatio**: Rakennetaan vaiheittain toimivaksi

---

**Kysymyksiä keskusteltavaksi:**
- Puuttuuko rakenteesta jotain olennaista?
- Onko jokin osio liian yksityiskohtainen tai turha?
- Tarvitaanko lisää visualisointeja?
- Millainen HTML-raportti olisi hyödyllisin?
- Mitä muita formaatteja kannattaisi tukea (Excel, PowerPoint)?
