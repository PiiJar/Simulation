# generate_processing_matrix – Toimintakuvaus

Tämä dokumentti kuvaa yksityiskohtaisesti, miten `generate_processing_matrix`-funktio toimii ja mitä vaiheita se sisältää.

## 1. Parametrit ja alustus
- **Parametrit:**
  - `output_dir`: simulaation tuloskansio
  - `programs_dir`: käsittelyohjelmien kansio (esim. original_programs tai stretched_programs)
  - `output_file`: tiedosto, johon line-matriisi tallennetaan
  - `step_logging`: (oletuksena False) – ohjaa vaihekohtaista lokitusta
- Alustaa tyhjän DataFramen line-matriisia varten.

## 2. Ohjelmatiedostojen läpikäynti
- Käy läpi kaikki käsittelyohjelmat (esim. `Batch_001_Treatment_program_002.csv`) kansiosta `programs_dir`.
- Jokainen ohjelmatiedosto sisältää yhden erän käsittelyvaiheet (batch, program, stage, ajat).

## 3. Vaiheiden purku ja line-matriisin rakentaminen
- Jokaisesta ohjelmatiedostosta luetaan vaiheet järjestyksessä.
- Jokaisesta vaiheesta poimitaan:
  - Erän tunniste (Batch)
  - Ohjelman tunniste (Treatment_program)
  - Vaiheen numero (Stage)
  - Asema (Station)
  - Vaiheen alku- ja loppuaika (Start_time, End_time)
- Rakentaa line-matriisin rivin jokaisesta vaiheesta:
  - Yksi rivi = yksi erä–asema–vaihe–aikaväli
- Lisää kaikki rivit line-matriisi-DataFrameen.

## 4. Tallennus
- Tallentaa line-matriisin CSV-tiedostoon `output_file`.
- Tarvittaessa tallentaa myös HTML-version (esim. visualisointia varten).

## 5. Palautus
- Palauttaa line-matriisin DataFramen jatkokäsittelyä varten.

## 6. Lokitus
- Kirjaa vaiheet ja mahdolliset virheet lokiin (jos loggeri käytössä).

---

**Yhteenveto:**
- Funktio yhdistää kaikki käsittelyohjelmien vaiheet yhdeksi line-matriisiksi, jossa näkyy jokaisen erän, ohjelman ja vaiheen ajoitus ja asema.
- Line-matriisi toimii pohjana tuotantolinjan visualisoinnille ja analyysille.
