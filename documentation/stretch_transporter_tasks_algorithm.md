# stretch_transporter_tasks.py – Algoritmin kuvaus

Tämä dokumentti kuvaa, miten `stretch_tasks`-funktio venyttää nostintehtävien ajoituksia ja päivittää käsittelyohjelmat sekä tuotannon aloitusajat.

## Vaiheittainen algoritmi

1. **Käsittelyohjelmien kopiointi**
   - Kopioi kaikki tiedostot kansiosta `original_programs` uuteen kansioon `stretched_programs`.
   - Näin muutokset eivät vaikuta alkuperäisiin ohjelmiin.

2. **Tehtävälistan valmistelu**
   - Kopioi `transporter_tasks_ordered.csv` → `transporter_tasks_stretched.csv`.
   - Lataa tehtävälista DataFrameen.
   - Lataa asemien X-koordinaatit ja nostimen parametrit (max_speed, acceleration_time, deceleration_time).

3. **Venytysalgoritmi**
   - Käy tehtävälista läpi peräkkäisinä pareina (i, i+1).
   - Laskee vaaditun siirtoajan:
     - Jos sama erä: vaadittu siirtoaika = 0
     - Jos eri erä: vaadittu siirtoaika lasketaan fysiikkapohjaisesti:
       - Lasketaan etäisyys asemien välillä (mm)
       - Lasketaan kiihdytys- ja jarrutusmatkat sekä -ajat nostimen parametreilla
       - Jos etäisyys on lyhyt, maksiminopeutta ei saavuteta (kolmioprofiili):
         - Siirtoaika = kiihdytys + jarrutus (nopeus kasvaa ja laskee, ei tasaista vaihetta)
       - Jos etäisyys on riittävä, käytetään trapezoidiprofiilia:
         - Siirtoaika = kiihdytys + tasaista nopeutta + jarrutus
   - Jos seuraavan tehtävän alku on liian aikaisin (aikaero < vaadittu siirtoaika):
     - Lasketaan tarvittava viive (shift = vaadittu siirtoaika - aikaero)
     - Siirretään kaikki saman erän myöhemmät tehtävät eteenpäin (Lift_time ja Sink_time)

4. **Käsittelyohjelmien ja tuotannon päivitys**
   - Jos venytetty tehtävä on erän ensimmäinen ohjelma-askel (stage==1):
     - Päivitetään kyseisen erän `Start_time` Production.csv-tiedostossa
   - Muussa tapauksessa:
     - Päivitetään vain kyseisen ohjelmatiedoston edellisen vaiheen (stage-1) `CalcTime`-arvo stretched_programs-kansiossa

5. **Tallennus ja lokitus**
   - Tallentaa venytetyn tehtävälistan `transporter_tasks_stretched.csv`-tiedostoon
   - Kirjaa muutokset ja vaiheet lokiin

## Yhteenveto
- Algoritmi varmistaa, että nostintehtävien välillä on riittävä siirtoaika.
- Siirtoajan laskenta huomioi nostimen kiihtyvyyden ja jarrutuksen sekä sen, ettei lyhyillä siirroilla maksiminopeutta saavuteta.
- Vain oikea ohjelma-askel tai Production.csv päivittyy, eikä muutoksia kumuloida vääriin kohtiin.
- Kaikki muutokset tehdään kopioihin, joten alkuperäiset tiedot säilyvät.
