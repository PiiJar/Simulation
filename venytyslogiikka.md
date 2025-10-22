# Venytyslogiikka

## Lähtötiedot

### 1. Production.csv (`output_dir/initialization/production.csv`)
- **Luetaan:** `pd.read_csv()`
- **Sarakkeet käytössä:**
  - `Batch`: Erän numero
  - `Start_station`: Aloitusasema
  - `Start_station_check`: HH:MM:SS muodossa (asemakonfliktien jälkeen)
- **Muunnos muistissa:**
  - `Start_station_check` → `Start_time_seconds` (sekunteja, `pd.to_timedelta().dt.total_seconds()`)
- **Tallennetaan:** `production_cache` muuttujaan

### 2. Käsittelyohjelmat (`output_dir/optimized_programs/Batch_XXX_Treatment_program_YYY.csv`)
- **Luetaan:** Kaikki `Batch_*.csv` tiedostot
- **Sarakkeet käytössä:**
  - `Stage`: Vaiheen numero
  - `MinStat`, `MaxStat`: Rinnakkaiset asemat
  - `CalcTime`: HH:MM:SS muodossa (alustettu MinTime:ksi)
- **Muunnos muistissa:**
  - `CalcTime` → `CalcTime_seconds` (sekunteja)
- **Tallennetaan:** `program_cache` dictionary (avain = tiedostonimi)

### 3. Transporter tasks resolved (`output_dir/logs/transporter_tasks_resolved.csv`)
- **Luetaan:** `pd.read_csv()`
- **Kopioidaan:** `df_stretched = df.copy(deep=True)`
- **Sarakkeet:**
  - `Transporter_id`: Nostimen numero
  - `Batch`: Erän numero
  - `Stage`: Vaiheen numero
  - `Lift_stat`, `Sink_stat`: Nosto- ja laskuasemat
  - `Lift_time`, `Sink_time`: Sekunteina
  - `Phase_1`, `Phase_2`, `Phase_3`, `Phase_4`: Vaiheajat

### 4. Stations.csv ja Transporters.csv
- Ladataan asema- ja nostintiedot fysiikkalaskentaan

## Algoritmi

### 1. Iteraatio läpi transporter taskit
- **While-silmukka:** `i = 0` → `n-1` (kaikki peräkkäiset parit)
- **Vertaillaan:** Tehtävää `i` ja `i+1`

### 2. Phase_1 laskenta
- **Lasketaan:** Siirtoaika tehtävän `i` Sink_stat → tehtävän `i+1` Lift_stat
- **Funktio:** `calculate_physics_transfer_time(sink_row, lift_row, transporter_row)`
- **Tallennetaan:** `df_stretched.at[i+1, 'Phase_1']`

### 3. Konfliktitarkistus
- **Ehto 1:** Sama nostin? (`Transporter_id[i] == Transporter_id[i+1]`)
  - Jos EI → `shift = 0`, jatka seuraavaan
  - Jos KYLLÄ → jatka tarkistukseen

- **Ehto 2:** Tarvitaanko väliä?
  - Jos eri erä → `required_gap = Phase_1` (nostin pitää siirtyä edellisestä asemasta)
  - Jos sama erä → `required_gap = 0` (nostin on jo oikealla asemalla)

- **Laske shift:**
  ```
  shift = (Sink_time[i] + required_gap) - Lift_time[i+1]
  ```
  **shift** = Kuinka paljon tehtävää i+1 pitää siirtää eteenpäin, jotta required_gap mahtuu väliin
  - Jos `shift > 0` → KONFLIKTI, tehtävä i+1 alkaa liian aikaisin, siirretään
  - Jos `shift ≤ 0` → Ei konfliktia, aikaa riittää

### 4. Venytys (jos shift > 0)
`shift_ceil = math.ceil(shift)`

#### A. Päivitä nostoaseman aikaa (konfliktitehtävä i+1)

**Nostintehtävän Lift_stat määrittää mitä päivitetään:**

**Vaihtoehto 1: Lift_stat = Start_station**
- Nostoasema on aloitusasema
- → Päivitä **Production.csv Start_time_seconds**:
  ```
  Start_time_seconds = Start_time_seconds + shift_ceil
  ```

**Vaihtoehto 2: Lift_stat on käsittelyohjelman asemalla**
- Etsi käsittelyohjelmasta askel jossa `MinStat ≤ Lift_stat ≤ MaxStat`
- → Päivitä **sen askeleen CalcTime_seconds**:
  ```
  CalcTime_seconds = CalcTime_seconds + shift_ceil
  ```

#### B. Päivitä kaikkien saman erän tehtävien ajat

**Siirretään erän kaikki tehtävät kohdasta i+1 eteenpäin:**
```
For j = i+1 to n:
  If Batch[j] == Batch[i+1]:
    Lift_time[j] += shift_ceil
    Sink_time[j] += shift_ceil
```

**Tärkeä:** 
- Ei muuteta historiaa - siirretään vain kohdasta i+1 eteenpäin, ei aikaisempia tehtäviä
- **Listan järjestys säilyy ennallaan** - päivitys tehdään paikalleen (`df.at[j, ...]`), ei lajitella

---

## Tallennus

Kun kaikki tehtäväparit on käyty läpi, tallennetaan kolme tiedostoa:

### 1. transporter_tasks_stretched.csv
- Venytetty nostintehtävälista
- Sisältää päivitetyt `Lift_time` ja `Sink_time` -arvot
- Tallennetaan sellaisenaan (sekunteina)

### 2. Production.csv
- Jos `production_cache` muokattu (Start_time_seconds päivitetty)
- **Konversio takaisin HH:MM:SS-muotoon:**
  ```python
  Start_stretch = f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d}"
  ```
- Poistetaan `Start_time_seconds`-sarake ennen tallennusta
- Tallennetaan: `output_dir/initialization/production.csv`

### 3. Käsittelyohjelmat (optimized_programs/*.csv)
- Jos `program_cache` muokattu (CalcTime_seconds päivitetty)
- **Konversio takaisin HH:MM:SS-muotoon:**
  ```python
  CalcTime = f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d}"
  ```
- Poistetaan `CalcTime_seconds`-sarake ennen tallennusta
- Tallennetaan: `output_dir/initialization/optimized_programs/Batch_XXX_Treatment_program_YYY.csv`

**Yhteenveto aikaformaateista:**
- **Muistissa laskenta:** sekunneissa (`Start_time_seconds`, `CalcTime_seconds`)
- **Tiedostoissa tallennuksessa:** `HH:MM:SS` muodossa (`Start_stretch`, `CalcTime`)

