# Vaatimusmäärittely CP-SAT Vaihe 1: Asemaoptimointi

## Tavoite
Optimoi erien käsittelyaikataulu asemilla huomioiden vain asemavaraukset ja käsittelyajat, ei nostimen rajoitteita.

## Lähtötiedot

### Tiedostorakenne
Optimointi käyttää samoja lähtötietoja kuin nykyinen toteutus:

1. `cp_sat_batches.csv`
   - Lista käsiteltävistä eristä
   - Sarakkeet: Batch, Treatment_program

2. `cp_sat_stations.csv`
   - Asemien tiedot
   - Sarakkeet: Station, Group (asemaryhmä)

3. `cp_sat_treatment_program_{batch_id}.csv`
   - Eräkohtaiset käsittelyohjelmat
   - Sarakkeet: Stage, MinStat, MaxStat, MinTime, MaxTime

4. `cp_sat_transfer_tasks.csv`
   - Siirtotehtävien tiedot (ei käytetä vaiheessa 1)
   - Säilytetään vaihetta 2 varten

## Optimoinnin muuttujat

### 1. Erien lähtöajat
- Jokaisen erän Stage 0:n lähtöaika
- Rajoite: aika ≥ 0

### 2. Asemavalinnat
- Jokaiselle vaiheelle valittu asema väliltä MinStat-MaxStat
- Huomioitava Group-rajoitteet

### 3. Käsittelyajat
- Jokaisen vaiheen käsittelyaika MinTime-MaxTime välillä
- Vaiheessa 1 voidaan käyttää maksimiaikoja, jotta jää joustoa vaiheeseen 2

## Rajoitteet

### 1. Asemien yksikäyttöisyys
- Yhdellä asemalla voi olla vain yksi erä kerrallaan
- Poikkeus: Stage 0 (aloitusasema) sallii päällekkäisyydet

### 2. Erän sisäinen järjestys
- Erän vaiheet suoritettava määritellyssä järjestyksessä
- Seuraava vaihe voi alkaa vasta kun edellinen on päättynyt

### 3. Asemaryhmät (Group)
- Asemavalinta sallittu vain saman Group-numeron sisällä
- MinStat-MaxStat määrittelee valittavissa olevat asemat

## Vapausasteet

### 1. Erien järjestys
- Erien keskinäinen käsittelyjärjestys on vapaa
- Poikkeus: identtiset erät käsitellään alkuperäisessä järjestyksessä

### 2. Asemavalinta
- Vapaa valinta MinStat-MaxStat väliltä saman Group-numeron sisällä
- Mahdollistaa rinnakkaisten asemien tehokkaan käytön

### 3. Käsittelyajat
- Säädettävissä MinTime-MaxTime rajoissa
- Vaiheessa 1 suositaan pidempiä aikoja jouston mahdollistamiseksi

## Optimoinnin tavoite
1. Ensisijainen: Minimoi kokonaisläpimenoaika (makespan)
2. Toissijainen: Jätä joustoa käsittelyaikoihin vaihetta 2 varten

## Tulostiedot vaiheelle 2
1. Erien lähtöajat
2. Valitut asemat jokaiselle vaiheelle
3. Käsittelyaikojen alku- ja loppuajat
4. Asemien varausajat

## Huomioitavaa
1. Vaihe 1 keskittyy vain asemakapasiteetin optimointiin
2. Ratkaisun on oltava toteutuskelpoinen myös nostinrajoitteiden kanssa
3. Käsittelyaikoihin jätettävä riittävästi joustoa vaihetta 2 varten
4. Tulos muodostaa lähtökohdan nostinoptimoinnille
5. Toteutus voi hyödyntää nykyistä cp_sat_optimization.py rakennetta:
   - Sama tiedostorakenne ja nimeämiskäytännöt
   - Sama muuttujien alustuslogiikka
   - Vain rajoitteet ja tavoitefunktio muuttuvat