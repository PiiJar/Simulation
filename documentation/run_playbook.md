# Simulaation ajon pikaopas (playbook)

Tämä on lyhyt, toistettava ohje simulaation ajamiseen paikallisesti.

## Pika-ajo

1) Aktivoi projektin Python-tulkki (.venv) ja aja putki:

```bash
# repo-juuressa
./.venv/bin/python main.py
```

- Jos `.venv` puuttuu, luo se ja asenna riippuvuudet (jos tiedosto on):

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt  # jos olemassa
./.venv/bin/python main.py
```

2) Valmiit artefaktit löytyvät uudesta aikaleimakansiosta `output/<YYYY-MM-DD_HH-MM>/`.

- Päivitetty `initialization/production.csv` (sis. `Start_optimized` Phase 2 jälkeen)
- `cp_sat/`-snapshotit (vaiheiden tulokset)
- Visualisoinnit ja raportit (PDF/HTML)

## VS Code -taski (suositus)

Valmiina on taski: “Run simulation after movement anchoring fix”. Aja: Terminal → Run Task… → valitse taski.

Halutessasi voit lisätä toisen nimen alla saman komennon.

## Ympäristömuuttujat (valinnaiset)

- Phase 1
  - `CPSAT_PHASE1_MAX_TIME` (sek) – aikaraja
  - `CPSAT_PHASE1_THREADS` – säikeiden määrä
  - `CPSAT_LOG_PROGRESS=1` – solver-loki päälle
- Phase 2
  - `CPSAT_PHASE2_MAX_TIME` (sek), `CPSAT_PHASE2_THREADS`
  - `CPSAT_PHASE2_DECOMPOSE=1` – aja eräkomponentteina
  - `CPSAT_PHASE2_WINDOW_MARGIN_SEC` (oletus 600)
  - `CPSAT_PHASE2_WINDOW_STAGE_MARGIN_SEC` (oletus 300)
  - `CPSAT_PHASE2_TRANSPORTER_SAFE_MARGIN_SEC` (oletus 600)
  - `CPSAT_LOG_PROGRESS=1` – solver-loki päälle

Aseta ne ennen ajoa:

```bash
export CPSAT_PHASE2_MAX_TIME=600
export CPSAT_LOG_PROGRESS=1
./.venv/bin/python main.py
```

## Nopea validointi ajon jälkeen

- Varmista että Phase 2 päivitti tuotannon:
  - `output/<ts>/initialization/production.csv` sisältää sarakkeen `Start_optimized`
- Aikataulujen snapshotit:
  - `output/<ts>/cp_sat/cp_sat_hoist_schedule.csv`
  - `output/<ts>/cp_sat/cp_sat_station_schedule.csv`
- Konfliktitilanteet (jos infeasible/virheitä):
  - `cp_sat_hoist_conflicts.csv`, `cp_sat_station_conflicts.csv`, `cp_sat_cross_conflicts.csv`

## Yleiset virheet ja korjaukset

- “python: command not found” → käytä `python3` tai suoraan `.venv/bin/python`
- Puuttuva `.venv` → `python3 -m venv .venv`
- Puuttuu riippuvuudet → `.venv/bin/python -m pip install -r requirements.txt` (jos tiedosto on)
- Infeasible Phase 2 → katso `cp_sat_*_conflicts.csv` ja tarkista change_time/deadhead/avoid/siirtojen määrittelyt
- Tuotannon polkuvirheet → varmista että koodi käyttää vain simulaatiokansion `initialization/production.csv`

## Komentoriviscripti (vaihtoehto)

Voit käyttää myös skriptiä:

```bash
bash tools/run_simulation.sh
```

Se käyttää `.venv/bin/python`-tulkkia ja tulostaa vaiheet lokiin.
