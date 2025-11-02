# Vaatimusmäärittely CP-SAT Vaihe 2: Nostinoptimointi

## Tavoite
Optimoi nostimen siirtotehtävät vaiheen 1 asemavarausaikataulun pohjalta hyödyntäen käsittelyaikojen joustoa.

## Lähtötiedot

### Vaiheen 1 tulokset
- `cp_sat_batch_schedule.csv`
  - Optimoitu asemavarausaikataulu
  - Sarakkeet: Transporter, Batch, Station, EntryTime, ExitTime

### Muut lähtötiedot
1. `cp_sat_transfer_tasks.csv`
   - Nostimen siirtotehtävien tiedot
   - Siirtymäajat asemien välillä

2. `cp_sat_treatment_program_{batch_id}.csv`
   - Käsittelyohjelmien MinTime-MaxTime rajat
   - Käytetään käsittelyaikojen hienosäätöön

3. `cp_sat_stations.csv`
   - Asemien tiedot ja sijainnit
   - Tarvitaan nostimen reitityksen optimointiin

## Optimoinnin muuttujat

### 1. Käsittelyaikojen hienosäätö
- Jokaisen vaiheen todellinen käsittelyaika MinTime-MaxTime rajoissa
- Säätövara määräytyy vaiheen 1 ratkaisun mukaan

### 2. Siirtotehtävien ajoitus
- Nostimen tehtävien aloitusajat
- Siirtotehtävien järjestys identtisten erien välillä

### 3. Nostimen sijainti
- Nostimen sijainti eri ajanhetkillä
- Tyhjäsiirtojen (deadhead) ajoitus

## Rajoitteet

### 1. Nostimen kapasiteetti
- Nostin voi suorittaa vain yhden siirtotehtävän kerrallaan
- Siirtoaika määräytyy Transfer_tasks.csv:n mukaan

### 2. Siirtymäajat
- Nostimen siirtymäaika asemalta toiselle huomioitava
- Tyhjäsiirrot vaativat myös aikaa

### 3. Asemavarausten yhteensopivuus
- Siirrot sovitettava vaiheen 1 asemavarausaikatauluun
- Käsittelyajat säädettävä MinTime-MaxTime rajojen sisällä

## Vapausasteet

### 1. Käsittelyaikojen säätö
- Vaiheen 1 käsittelyaikoja voi säätää rajojen sisällä
- Mahdollistaa siirtotehtävien limittämisen

### 2. Rinnakkaiset siirrot
- Toisen erän siirto voidaan suorittaa ensimmäisen käsittelyaikana
- Tyhjäsiirtojen ajoitus optimoitavissa

### 3. Siirtotehtävien järjestys
- Identtisten erien siirtotehtävien järjestystä voi vaihtaa
- Tyhjäsiirtojen reititys optimoitavissa

## Optimoinnin tavoitteet
1. Ensisijainen: Minimoi viimeisen siirtotehtävän päättymisaika
2. Toissijainen: Minimoi nostimen tyhjäsiirtojen kokonaisaika

## Tulostiedot
1. Optimoitu siirtotehtävien aikataulu
2. Päivitetyt käsittelyajat
3. Nostimen yksityiskohtainen reititys
4. Lopullinen läpimenoaika (makespan)

## Huomioitavaa
1. Nostimen reitityksen on oltava fyysisesti toteutettavissa
2. Käsittelyaikojen muutokset eivät saa rikkoa vaiheen 1 asemavarauksia
3. Tyhjäsiirtojen optimointi voi merkittävästi parantaa kokonaistehokkuutta
4. Nostimen kapasiteetti on kriittinen rajoite

## Optimoinnin prosessi
1. Lue vaiheen 1 tulokset
2. Muodosta siirtotehtävälista
3. Optimoi nostimen reititys
4. Hienosäädä käsittelyajat
5. Validoi lopullinen ratkaisu