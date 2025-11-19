# Simulointiputken päävaiheet (2025-11-19)

Tämä dokumentti kuvaa tuotantolinjan simulointiputken päävaiheet ja niiden logiikan, perustuen `main.py`-tiedoston rakenteeseen.

## Yleiskuvaus

Simulointiputki koostuu useista vaiheista, jotka suoritetaan järjestyksessä. Jokainen vaihe on kapseloitu omaksi funktiokseen, ja päälogiikka löytyy `main.py`-tiedoston `main()`-funktiosta.

## Vaiheittainen toiminta

1. **Alustus**
   - Luo simulaatiokansion ja alustaa lokituksen.
   - Luo `goals.json` ja `production.csv`.
   - Luo kaikki eräkohtaiset käsittelyohjelmat.
   - Jos käytössä on vain yksi ohjelma, siirrytään "quick modeen" (rajoitettu erämäärä ja aikaraja).

2. **Esikäsittely**
   - Suorittaa esikäsittelytiedostojen luonnin ja valmistelun CP-SAT-optimointia varten.

3. **Optimointi, vaihe 1 (CP-SAT Phase 1)**
   - Suorittaa asemaoptimoinnin (station optimization).

4. **Optimointi, vaihe 2 (CP-SAT Phase 2)**
   - Suorittaa nostin- ja aikatauluoptimoinnin.
   - Jos quick mode on käytössä, aikaraja asetetaan lyhyemmäksi.

5. **Pattern mining (vain quick mode)**
   - Etsii syklisiä tuotantokuvioita (pattern mining) ja tuottaa raportit löydetyistä sykleistä.
   - Palauttaa alkuperäisen tuotantodatan seuraavaa vaihetta varten.
   - Suorittaa laajennetun optimoinnin (CP-SAT Phase 3).

6. **Tulosten keruu**
   - Luo matriisit, nostintehtävät ja yksityiskohtaiset liikkeet.
   - Korjaa raporttidatan.

7. **Raportointi ja visualisointi**
   - Visualisoi matriisit ja tuottaa kaikki raportit sekä kuvat.
   - Kokoaa simulaatioraportin.

## Virheenkäsittely ja lokitus
- Jokainen vaihe kirjaa etenemisensä ja mahdolliset virheet lokiin.
- Virhetilanteessa putki keskeytyy ja virhe kirjataan.

## Yhteenveto

Simulointiputki on rakennettu vaiheittain, ja jokainen vaihe on selkeästi eroteltu. Pääfunktio kutsuu vain korkeimman tason vaiheita, ja yksityiskohdat on kapseloitu vaiheiden sisälle. Tämä mahdollistaa selkeän ylläpidon ja laajennettavuuden.
