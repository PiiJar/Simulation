# generate_matrix_stretched.py – Toimintakuvaus

Tämä dokumentti kuvaa yksityiskohtaisesti, miten `generate_matrix_stretched.py`-skripti toimii ja mitä vaiheita se sisältää.

## 1. Tiedostojen ja polkujen määrittely
- Määrittää polut:
  - `logs_dir`: output-kansion alikansio, johon tallennetaan lokit ja tulokset
  - `stretched_dir`: kansio, jossa ovat venytetyt käsittelyohjelmat (stretched_programs)
  - `output_file`: tiedosto, johon uusi line-matriisi tallennetaan (esim. `line_matrix_stretched.csv`)

## 2. Matriisin generointi
- Kutsuu funktiota `generate_processing_matrix`, joka rakentaa line-matriisin venytettyjen ohjelmien pohjalta.
  - Parametrit:
    - `output_dir`: simulaation tuloskansio
    - `programs_dir`: venytettyjen ohjelmien kansio (stretched_programs)
    - `output_file`: tiedosto, johon uusi matriisi tallennetaan
    - `step_logging`: (oletuksena False) – ohjaa vaihekohtaista lokitusta
- Funktio `generate_processing_matrix` lukee venytetyt ohjelmat, rakentaa niistä line-matriisin ja tallentaa sen CSV-tiedostoon.

## 3. Palautus ja käyttö
- Palauttaa generoidun matriisin DataFramen (tai None, jos vain tiedosto tallennetaan).
- Skripti voidaan ajaa suoraan komentoriviltä:
  - `python generate_matrix_stretched.py <output_dir>`
  - Oletuksena käyttää polkua "output"

## 4. Tyypillinen käyttötapa
- Skriptiä käytetään pipeline-vaiheessa, jossa halutaan muodostaa uusi line-matriisi venytettyjen tehtävien ja ohjelmien pohjalta.
- Tyypillisesti tätä seuraa visualisointi (esim. visualize_stretched_matrix.py).

---

**Yhteenveto:**
- Skripti generoi uuden line-matriisin venytettyjen ohjelmien perusteella ja tallentaa sen output-kansioon.
- Toimii pipeline-vaiheena, joka yhdistää venytetyt ohjelmat yhdeksi matriisiksi jatkokäsittelyä varten.
