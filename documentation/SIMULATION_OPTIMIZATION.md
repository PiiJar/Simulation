# SIMULATION_OPTIMIZATION

## Yleistä

Tämä ohjelma simuloi ja optimoi tuotantolinjan toimintaa, jossa useat erät (batchit) kulkevat läpi eri käsittelyvaiheiden (stage) ja asemien (station) hyödyntäen nostimia (transporters). Tavoitteena on löytää optimaalinen ajoitus ja järjestys, joka minimoi kokonaisläpimenoajan (makespan) ja huomioi kaikki tuotantoon liittyvät rajoitteet, kuten asemien ja nostimien kapasiteetit sekä siirtojen ja käsittelyjen kestoajat.

Ohjelma koostuu vaiheittaisesta putkesta, jossa dataa esikäsitellään, optimoidaan CP-SAT-mallilla, venytetään aikatauluja, muodostetaan nostintehtävät ja tuotetaan visuaaliset sekä numeeriset raportit tuotannon kulusta.

Tarkemmat toiminnalliset ja tekniset vaatimukset löytyvät tiedostosta `REQUIREMENTS.md`.

Lähtötiedot:
Käyttäjä laatii kaikki tarvittavat lähtötiedot `initialization`-kansioon. Näihin kuuluvat tuotantolinjan rakenne (esim. asemat ja nostimet), käsittelyohjelmat sekä tuotannon perusrakenteet (esim. erät ja ohjelmien jaksotus). Näiden pohjalta simulaatioputki rakentaa ja optimoi koko tuotannon ajoituksen.

Tulokset:
Simulaation ja optimoinnin tulokset löytyvät 'reports' kansiosta.

Simulaation välivaiheet sijoitetaan 'Logs' hakemistoon.

## Pääohjelman rakenne ja vaiheet (Main pipeline structure and steps)

Simulointi- ja optimointiputki koostuu seuraavista päävaiheista:

1. **Alustus (Initialization):**
   - Luo simulaatiokansion ja kopioi lähtötiedot
   - Valmistelee kaikki tarvittavat tiedostot ja kansiot
   - **Funktiot:**
     - `initialize_simulation`
     - `create_simulation_directory`
     - `generate_batch_treatment_programs_original`

2. **Esikäsittely (Preprocessing):**
   - Muuntaa ja tarkistaa lähtödataa
   - Valmistelee datan optimointia varten
   - **Funktiot:**
     - `preprocess_for_cpsat`

3. **Optimointi / Simulointi (Optimization / Simulation):**
   - Ratkaisee tuotannon ajoituksen CP-SAT-mallilla
   - Luo optimoidut käsittelyohjelmat ja aikataulut
   - **Funktiot:**
     - `cp_sat_stepwise`
     - `solve_and_save`

4. **Lopputulokset (Results):**
   - Venytetyn matriisin ja nostinliikkeiden muodostus
   - Visualisointi ja raportointi
   - Kaikki tulokset tallennetaan reports-kansioon
   - **Funktiot:**
     - `generate_matrix_stretched`
     - `extract_transporter_tasks`
     - `create_detailed_movements`
     - `visualize_stretched_matrix`
     - `generate_production_report`
