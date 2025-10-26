# Optimointivaatimukset

## Tavoite
Etsiä nostimelle ajallisesti optimaalisin reitti, joka minimoi kokonaisajan (makespan) huomioiden kaikki rajoitteet, kuten asemien käyttö, tehtävien järjestys ja siirtymäajat.

## Säännöt

### Sääntö 1
Erien käsittelyohjelman määrittelemää käsittelyjärjestystä on noudatettava. Tämä tarkoittaa, että jokaisen erän vaiheet on suoritettava annetussa järjestyksessä ilman poikkeuksia.

### Sääntö 2
Käsittelyohjelmien ohjelma-askeleiden käsittelyaikoja pitää kunnioittaa. Jokaisen askeleen kesto on vähintään määritelty minimi ja enintään määritelty maksimi.

### Sääntö 3
Asemilla ei voi olla kuin yksi erä kerrallaan. Tämä tarkoittaa, että aseman resurssit ovat varattuja yhden erän käsittelyn aikana, eikä päällekkäisyyksiä sallita.

### Sääntö 4
Nostimen liikkeet pitää perustua esilaskettuihin (fysiikkaan perustuviin) tietoihin. Liikkeisiin tarvittava aika tulee esikäsittelytiedostosta, ja optimoinnin on käytettävä näitä arvoja sellaisenaan.

### Sääntö 4.1
Nostin ei voi olla kahdessa paikassa yhtäaikaa. Kaikkien siirtotehtävien välissä on oltava riittävästi aikaa siirtymiseen tehtävältä toiselle, ja tämä aika perustuu esikäsittelytiedostossa määriteltyihin arvoihin.

## Vapausasteet

### Vapausaste 1
Käsittelyohjelmien käsittelyajat voivat olla mitä tahansa määritellyn minimi- ja maksimiarvon välillä. Tämä mahdollistaa nostimen tehtävien ajoittamisen ja päällekkäisyyksien eliminoinnin säätämällä käsittelyaikoja.

### Vapausaste 2
Jos ohjelmassa on rinnakkaisia asemia (sama Group-numero), niitä voidaan käyttää yhtäaikaisesti. Tämä mahdollistaa resurssien tehokkaamman hyödyntämisen ja tehtävien rinnakkaisen suorittamisen.

## Kysymykset ongelman ymmärtämiseksi

1. Mikä on optimoinnin tarkka tavoite?
   - Onko kyse vain nostimen reitin optimoinnista, vai pitääkö myös resurssien käyttöä (esim. asemat) optimoida?

   ### Vastaus kysymykseen 1
   Optimoinnin tavoite on minimoida kokonaistuotannon läpimenoaika. Tämä toteutuu, jos nostimelle (nostimille) löydetään ajallisesti nopein reitti. Reaalimaailman tavoite on siis tuotantoajan minimointi, mutta CP-SAT-optimoinnin tavoite on löytää nopein reitti nostimelle / nostimille.

2. Miten askel 0 liittyy ongelman ratkaisuun?
   - Ymmärrän, että askel 0 tarjoaa joustavuutta, mutta miten se käytännössä varmistaa ratkaisun löytymisen?

   ### Vastaus kysymykseen 2
   Tuotantosuunnitelmassa on luettelo eristä. Osoittautui, että sen huomioiminen CP-SAT-optimoinnissa oli vaikeaa. Tämän vuoksi ohjelmaan lisättiin askel 0, joka edustaa erän lähtöä prosessiin. Askeleelle 0 asetetaan mahdollisimman laaja aikaikkuna, jotta optimoinnilla on suurin vapausaste "säätää" mahdollisia nostimen tehtävien päällekkäisyyksiä.

3. Mitä tarkoitat sillä, että optimointi ei ole valjastettu oikein?
   - Onko ongelma rajoitteiden mallinnuksessa, muuttujien rajoissa vai optimoinnin tavoitteessa?

   ### Vastaus kysymykseen 3
   Koska optimointi ei löydä ratkaisua aivan perusongelmaan, tämä paljastaa joko virheen optimointialgoritmissa tai sen parametroinnissa. Koska CP-SAT-algoritmi on laajasti käytetty ja luotettava, ongelman täytyy todennäköisesti olla parametroinnissa. Näiden kysymysten ja vastausten tavoitteena on varmistaa, että ongelman luonne ymmärretään oikein ja että parametrointi vastaa ongelman vaatimuksia.

4. Mitä erityisiä ongelmia olet havainnut optimoinnin tuloksissa?
   - Esimerkiksi: jääkö jokin rajoite täyttymättä, vai eikö ratkaisu löydy lainkaan?

   ### Vastaus kysymykseen 4
   Optimointi ei löydä ratkaisua ongelmaan, joka on luonteeltaan hyvin yksinkertainen. Testitapauksessa on yksi erä, jossa ohjelmassa on kaksi vaihetta. Yksi nostin pystyy suorittamaan nämä tehtävät nopeimmin noudattamalla minimiaikojen mukaisesti. Ratkaisun löytäminen ei siis voi olla mahdotonta. Tämä vahvistaa aiemman analyysin (kysymys 3), että ongelma liittyy todennäköisesti parametrointiin eikä itse algoritmiin.

## Esimerkkitapaus

### Lähtötiedot

#### Asemat
- **301**: Ryhmä 1, X-sijainti 1000, Valutussaika 0, Asematyyppi 0, Laitteen viive 0.0
- **302**: Ryhmä 2, X-sijainti 2000, Valutusaika 0, Asematyyppi 0, Laitteen viive 0.0
- **303**: Ryhmä 3, X-sijainti 3000, Valutusaika 0, Asematyyppi 0, Laitteen viive 0.0

#### Nostin 1
- **Minimi X-sijainti**: 900 mm
- **Maksimi X-sijainti**: 10200 mm
- **Kiihdytysaika**: 2.0 s
- **Hidastusaika**: 2.0 s
- **Maksiminopeus**: 300 mm/s
- **Z-akselin kokonaismatka**: 1800 mm
- **Z-akselin hidas matka (kuiva)**: 300 mm
- **Z-akselin hidas matka (märkä)**: 1500 mm
- **Z-akselin hidas loppumatka**: 50 mm
- **Z-akselin hidas nopeus**: 100 mm/s
- **Z-akselin nopea nopeus**: 200 mm/s

### Lähtötiedot erän 1 käsittelyohjelmasta

| Stage | MinStat | MaxStat | MinTime   | MaxTime   | CalcTime   |
|-------|---------|---------|-----------|-----------|------------|
| 0     | 301     | 301     | 00:00:00  | 100:00:00 | 00:00:00   |
| 1     | 302     | 302     | 00:10:00  | 00:12:00  | 00:10:00   |
| 1     | 303     | 303     | 00:00:00  | 00:12:00  | 00:00:00   |

Nämä tiedot on poimittu tiedostosta `Batch_001_Treatment_program_001.csv` ja ne kuvaavat erän 1 käsittelyohjelman vaiheet ja aikarajoitteet.

### Tehtävä- ja siirtoajat asemille 301, 302 ja 303

- **301 → 301**: Lift Time: 17 s, Transfer Time: 0.0 s, Sink Time: 16 s, Total Task Time: 33.0 s
- **301 → 302**: Lift Time: 17 s, Transfer Time: 5.0 s, Sink Time: 16 s, Total Task Time: 38.0 s
- **301 → 303**: Lift Time: 17 s, Transfer Time: 9.0 s, Sink Time: 16 s, Total Task Time: 42.0 s
- **302 → 301**: Lift Time: 17 s, Transfer Time: 5.0 s, Sink Time: 16 s, Total Task Time: 38.0 s
- **302 → 302**: Lift Time: 17 s, Transfer Time: 0.0 s, Sink Time: 16 s, Total Task Time: 33.0 s
- **302 → 303**: Lift Time: 17 s, Transfer Time: 5.0 s, Sink Time: 16 s, Total Task Time: 38.0 s
- **303 → 301**: Lift Time: 17 s, Transfer Time: 9.0 s, Sink Time: 16 s, Total Task Time: 42.0 s
- **303 → 302**: Lift Time: 17 s, Transfer Time: 5.0 s, Sink Time: 16 s, Total Task Time: 38.0 s
- **303 → 303**: Lift Time: 17 s, Transfer Time: 0.0 s, Sink Time: 16 s, Total Task Time: 33.0 s

Nämä tiedot on poimittu tiedostosta `transfer_tasks.csv` ja ne kuvaavat siirto- ja tehtäväaikoja asemien välillä.

### Kuvaus
Tässä esimerkkitapauksessa on yksi nostin ja kolme asemaa. Erän 1 käsittelyohjelma sisältää kolme vaihetta, jotka tulee suorittaa annetussa järjestyksessä. Optimoinnin tavoitteena on löytää nostimelle ajallisesti optimaalisin reitti, joka minimoi kokonaisajan (makespan) noudattaen kaikkia sääntöjä ja rajoitteita.

### Esimerkki nostimen tehtävistä

1. **301 → 302**: 00:00:00 → 00:00:38  
   - **Lift Time**: 17 s  
   - **Transfer Time**: 5 s  
   - **Sink Time**: 16 s  

2. **302 → 303**: 00:10:38 → 00:11:16  
   - **Käsittelyaika (302)**: 10 min  
   - **Lift Time**: 17 s  
   - **Transfer Time**: 5 s  
   - **Sink Time**: 16 s  

Nämä tehtävät perustuvat käsittelyohjelman vaiheisiin ja siirto- sekä käsittelyaikoihin.

