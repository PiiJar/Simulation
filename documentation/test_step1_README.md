# Dokumentaatio: test_step1.py (STEP 1)

Tämä dokumentaatio kuvaa, miten test_step1.py:n funktiot toimivat ja miten simulaatiokansio luodaan sekä lokitus alustetaan simulointiputkessa.

## Funktioiden tarkoitus

### create_simulation_directory(base_dir="output")
- Luo aikaleimapohjaisen simulaatiokansion (esim. output/2025-06-24_10-30-00/).
- Kopioi juuren Initialization- ja Documentation-kansiot simulaatiokansioon.
- Luo Logs-kansion ja alustaa simulation_log.csv-tiedoston.
- Palauttaa luodun simulaatiokansion polun.

### test_step_1()
- Kutsuu create_simulation_directory-funktiota ja tulostaa vaiheen etenemisen.
- Tarkistaa, että Initialization- ja Documentation-kansiot sekä Logs-kansio ja simulation_log.csv on luotu oikein.
- Kirjaa ensimmäiset lokirivit simulation_log.csv-tiedostoon.
- Palauttaa output_dir-polun, jos kaikki onnistuu.

## Vaiheittainen toiminta

1. Luo simulaatiokansio (create_simulation_directory).
2. Kopioi Initialization- ja Documentation-kansiot.
3. Luo Logs-kansio ja simulation_log.csv.
4. Kirjaa ensimmäiset lokirivit (STEP, INIT) simulation_log.csv-tiedostoon.
5. Tulostaa etenemisen terminaaliin.

## Esimerkkikutsu

```python
output_dir = create_simulation_directory()
# ... voit käyttää output_dir:ia seuraavissa vaiheissa ...
```

## Riippuvuudet
- Python standard library: os, sys, datetime, shutil
- create_simulation_directory (oma moduuli)

---

## Käyttö test_main.py:ssä

- Kutsu test_step_1()-funktiota pipeline-logiikan mukaisesti.
- Käytä aina output_dir-parametria polkujen rakentamiseen.
- Kaikki vaiheet kirjaavat etenemisensä simulation_log.csv-tiedostoon.
