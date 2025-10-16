# Dokumentaatio: test_step4.py (STEP 4)

Tämä dokumentaatio kuvaa, miten test_step4.py:n funktiot toimivat ja miten alkuperäisen line-matriisin visualisointi tuotetaan simulointiputkessa.

## Funktioiden tarkoitus

### test_step4_visualize_original_matrix(output_dir)
- Visualisoi alkuperäisen line-matriisin (line_matrix_original.csv) erien kulun asemilla aikajanalla.
- Tallentaa visualisointikuvan simulaatiokansioon (Logs/).
- Kirjaa vaiheen aloituksen ja lopetuksen simulation_log.csv-tiedostoon STEP-tyyppisillä riveillä.
- Palauttaa polun luotuun visualisointikuvaan.

## Vaiheittainen toiminta

1. Lue alkuperäinen line-matriisi (Logs/line_matrix_original.csv).
2. Luo timeline-visualisointi erien liikkeestä asemilla.
3. Tallentaa visualisoinnin tiedostoon (esim. Logs/original_matrix_timeline.png).
4. Kirjaa vaiheen aloituksen ja lopetuksen simulation_log.csv-tiedostoon STEP-tyyppisillä riveillä.
5. Palauttaa visualisointikuvan polun.

## Esimerkkikutsu

```python
visualization_file = test_step4_visualize_original_matrix(output_dir)
```

## Riippuvuudet
- Python standard library: os, sys, datetime
- pandas
- matplotlib

---

## Käyttö test_main.py:ssä

- Kutsu `test_step4_visualize_original_matrix` vasta sen jälkeen, kun alkuperäinen line-matriisi on luotu.
- Käytä aina output_dir-parametria polkujen rakentamiseen.
- Funktio kirjaa vaiheen aloituksen ja lopetuksen simulation_log.csv-tiedostoon STEP-tyyppisillä riveillä.
- Palauttaa polun luotuun kuvaan – käytä tätä polkua tarvittaessa seuraavissa pipeline-vaiheissa.
