# Raportointi (Reporting)

Raportointi-vaihe kokoaa simulaation ja optimoinnin lähtötiedot, tulokset ja analyysin yhdeksi dokumentiksi.

Tavoitteena on tuottaa helposti jaettavissa oleva yhteenveto, joka sisältää:
- Syötteiden ja konfiguraation kuvauksen
- Optimoinnin ja simulaation keskeiset tulokset
- Visuaaliset yhteenvedot (esim. aikajanat, Gantt, nostinten liikkeet)
- Keskeiset mittarit ja analyysit (esim. makespan, deadhead, venytykset)
- Mahdolliset poikkeamat, varoitukset ja tulkintaohjeet



Raportin alkuun lisätään etusivu, joka sisältää seuraavat tiedot:

- **Otsikko:** 'Simulation Report' (omalla rivillään)
- **Asiakas** ja **laitos**: haetaan initialization-kansion tiedostoista, esitetään omilla riveillään otsikon alla
- **Simulaatioajon päivämäärä ja kellonaika**: muodossa yyyy-mm-dd hh:mm:ss, omalla rivillään
- **(Vapaaehtoinen lyhyt tiivistelmä raportin sisällöstä)**
- **Alalaitaan**: simulaatiohakemiston nimi (output/snapshot-kansio)

Etusivu toimii kansilehtenä sekä HTML- että PDF-muodossa.

Raportti voidaan tuottaa HTML- ja/tai PDF-muodossa.

## Syötteet taulukoina

Raportin alkuun esitetään seuraavat tiedot taulukkomuodossa:

- **Asematiedot**: Kaikki simulaation asemat (station), sisältäen vähintään sarakkeet:
  - Station ID/Number
  - Nimi (Name)
  - X-koordinaatti (X Position)
  - Mahdolliset ryhmätiedot (Group)
  - Muut relevantit kentät (esim. tyyppi, kapasiteetti)


- **Käsittelyohjelmat**: Raportissa esitetään vain erilaiset käsittelyohjelmat (ei eräkohtaisia ohjelmia), taulukkona:
  - Stage
  - MinStat, MaxStat
  - MinTime, MaxTime

Taulukot voidaan esittää sekä HTML- että PDF-raportissa suoraan pandas DataFrame -muodosta.
