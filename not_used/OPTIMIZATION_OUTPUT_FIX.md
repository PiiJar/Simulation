# CP-SAT Optimoinnin Tulosten Tallennus - Korjaus

## Ongelma
CP-SAT optimointi toimi, mutta **tulokset eivät päivittyneet** seuraaviin vaiheisiin:
- ✅ Optimointi laskee: erien järjestys, alkuajat, CalcTime-arvot (MinTime-MaxTime välillä)
- ❌ Tulokset eivät tallentuneet → seuraavat vaiheet käyttivät vanhoja arvoja
- ❌ Optimoinnin hyödyt eivät näkyneet lopputuloksessa

## Ratkaisu

### 1. Lisätty `save_optimized_calctimes()` funktio (optimize_cpsat.py)
**Tallentaa optimoidut CalcTime-arvot eräkohtaisiin treatment_program-tiedostoihin:**
- Luo kansion: `output/YYYY-MM-DD_HH-MM-SS/optimized_programs/`
- Tallentaa: `Batch_XXX_Treatment_program_YYY.csv`
- Päivittää: `CalcTime` sarakkeen optimoiduilla arvoilla (MinTime-MaxTime väliltä)
- Luo raportin: `calctime_changes_report.csv` (näyttää mitä muuttui)

### 2. Lisätty `save_optimized_production()` funktio (optimize_cpsat.py)
**Tallentaa optimoidut alkuajat ja järjestyksen:**
- Tallentaa: `optimized_programs/production_optimized.csv`
- Lisää sarakkeen: `Start_optimized` (optimoitu alkuaika Stage 1:lle)
- Järjestää erät: aikajärjestykseen (optimoitu järjestys)
- Raportoi: jos erien järjestys muuttui

### 3. Päivitetty `generate_matrix.py`
**Lukee optimoidut arvot automaattisesti:**
```python
# ENNEN: Luki aina initialization/production.csv (vanhat arvot)
# JÄLKEEN: Tarkistaa onko optimized_programs/production_optimized.csv
#          → Jos on, käyttää optimoituja arvoja
#          → Jos ei, käyttää alkuperäisiä
```

### 4. Lisätty disjunktiiviset rajoitteet
**Korjattiin fyysinen mahdottomuus (nostin ei voi laskea uutta ennen kuin vanha nostettu):**
- ENNEN: 42 ordering-rajoitetta → Model INFEASIBLE
- JÄLKEEN: Disjunktiiviset rajoitteet (JOKO A ennen B TAI B ennen A)
  - Käyttää boolean-muuttujia
  - CP-SAT valitsee järjestyksen optimoinnissa
  - Malli pysyy feasible

## Datavirta

```
CP-SAT Optimointi
    ↓
save_optimized_calctimes()
    ↓
optimized_programs/Batch_XXX_Treatment_program_YYY.csv  ← CalcTime optimoitu
    ↓
save_optimized_production()
    ↓
optimized_programs/production_optimized.csv  ← Start_optimized, järjestys
    ↓
generate_matrix.py
    ↓ (lukee optimized_programs/)
line_matrix_stretched.csv  ← Lopullinen matriisi optimoiduilla arvoilla
    ↓
Visualisointi & Raportit
```

## Tiedostot Muutettu
1. `optimize_cpsat.py`:
   - `save_optimized_calctimes()` - uusi funktio
   - `save_optimized_production()` - uusi funktio
   - `optimize_transporter_schedule()` - kutsuu tallennusfunktioita
   - Disjunktiiviset rajoitteet (RAJOITE 4)

2. `generate_matrix.py`:
   - `load_production_batches_stretched()` - tarkistaa optimoidun version

## Tulokset
- ✅ Optimoidut CalcTime-arvot päivittyvät
- ✅ Optimoidut alkuajat päivittyvät
- ✅ Optimoitu erien järjestys päivittyy
- ✅ Raportit näyttävät mitä muuttui
- ✅ Lopullinen matriisi käyttää optimoituja arvoja
- ✅ Fyysinen mahdottomuus korjattu disjunktiivisilla rajoitteilla
