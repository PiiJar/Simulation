# config.py
# CP-SAT ja muut simulaation konfiguraatiot

import os

# ============================================================================
# CP-SAT PHASE 1 KONFIGURAATIOT
# ============================================================================

def get_cpsat_phase1_groups():
    """Käytetäänkö ryhmärajoitteita Phase 1:ssä
    
    Phase 1 optimoi nostimen valinnan jokaiselle erälle ja vaiheelle.
    Ryhmärajoitteet pakottavat erän kaikki vaiheet samalle nostimelle,
    mikä vähentää nostimien välistä siirtymistä mutta rajoittaa joustavuutta.
    
    Oletus: '1' (käytössä)
    Vaikutus: Kun päällä, vähentää nostinvaihtojen määrää mutta voi pidentää
              kokonaisaikaa. Kun pois, optimoija voi valita eri nostimet eri
              vaiheille joustavammin.
    """
    return os.getenv('CPSAT_PHASE1_GROUPS', '1').strip().lower() in ('1', 'true', 'yes')

def get_cpsat_phase1_max_time():
    """Phase 1 maksimiaika sekunteina (0 = ei rajoitusta)
    
    Rajoittaa kuinka kauan CP-SAT saa etsiä optimaalista ratkaisua Phase 1:lle.
    Phase 1 on yleensä nopea (muutama sekunti), joten tätä ei yleensä tarvita.
    
    Oletus: 0 (ei aikarajaa)
    Vaikutus: Jos asetettu > 0, CP-SAT pysähtyy ajan umpeuduttua ja palauttaa
              parhaan löydetyn ratkaisun (ei välttämättä optimaalinen).
    Esimerkki: 300 = 5 minuuttia
    """
    try:
        # Oletusarvo muutettu 300 sekuntiin (5 min), jotta ei jää jumiin
        return float(os.getenv('CPSAT_PHASE1_MAX_TIME', '300') or '300')
    except:
        return 300.0

def get_cpsat_phase1_threads():
    """Phase 1 säikeiden määrä (0 = automaattinen)
    
    Määrittää kuinka monta CPU-säiettä CP-SAT käyttää rinnakkain.
    
    Oletus: 0 (CP-SAT valitsee automaattisesti prosessorin ytimien mukaan)
    Vaikutus: Enemmän säikeitä = nopeampi ratkaisu, mutta vie enemmän muistia.
    Esimerkki: 4 = käytä 4 säiettä, 0 = automaattinen
    """
    try:
        return int(os.getenv('CPSAT_PHASE1_THREADS', '0') or '0')
    except:
        return 0

def get_cpsat_phase1_round_robin():
    """Käytetäänkö rinnakkaisasemien Round Robin -kiinnitystä Phase 1:ssä
    
    Jos päällä ('1'), optimoija ei saa valita rinnakkaisasemien (esim. 207, 208)
    välillä vapaasti, vaan ne jaetaan erille vuorotellen (Round Robin).
    
    Oletus: '1' (käytössä)
    Vaikutus: Nopeuttaa Phase 1:stä HUOMATTAVASTI, koska se poistaa
              kombinatoriikkaa asemavalinnoista. Vähentää joustavuutta hieman,
              mutta identtisillä asemilla tämä on yleensä haluttu käytös.
    """
    return os.getenv('CPSAT_PHASE1_ROUND_ROBIN', '1').strip().lower() in ('1', 'true', 'yes')

# ============================================================================
# CP-SAT PHASE 2 KONFIGURAATIOT
# ============================================================================

def get_cpsat_phase2_max_time():
    """Phase 2 maksimiaika sekunteina
    
    Phase 2 on aikataulu-optimointi, joka määrittää tarkat aloitus- ja lopetusajat
    jokaiselle erälle ja vaiheelle. Tämä on simulaation kriittisin ja aikaa vievin vaihe.
    
    Oletus: 1800 sekuntia (30 minuuttia)
    Vaikutus: Pidempi aika antaa CP-SAT:lle enemmän aikaa löytää parempi ratkaisu.
              - 300-600s: Nopea ratkaisu, ei välttämättä optimaalinen
              - 1800s (30min): Hyvä tasapaino laadun ja nopeuden välillä
              - 3600-7200s (1-2h): Parempi laatu suurille ongelmille
    Suositus: 1800s normaalille ajolle, 7200s tuotantoajolle
    """
    try:
        return int(os.environ.get("CPSAT_PHASE2_MAX_TIME", "7200"))  # oletus 2 tuntia
    except:
        return 1800

def get_cpsat_phase2_threads():
    """Phase 2 säikeiden määrä (0 = automaattinen)
    
    Määrittää rinnakkaisuuden tason Phase 2:ssa.
    
    Oletus: 0 (automaattinen, käyttää kaikkia CPU-ytimiä)
    Vaikutus: Enemmän säikeitä = nopeampi ratkaisu suurille ongelmille.
    Suositus: Jätä 0:ksi, jolloin CP-SAT optimoi automaattisesti.
    """
    try:
        return int(os.getenv("CPSAT_PHASE2_THREADS", "0") or "0")
    except:
        return 0

def get_cpsat_phase2_anchor_stage1():
    """Käytetäänkö Stage 1 järjestysankkuria identtisille ohjelmille (symmetrianmurtaja)
    
    Lukitsee identtisten käsittelyohjelmien erien keskinäisen järjestyksen Phase 1:n
    mukaiseksi. Kun erät käyttävät samaa ohjelmaa, niiden keskinäisen järjestyksen
    vaihtaminen ei vaikuta kokonaistulokseen (symmetria), joten Phase 1:n järjestys
    voidaan pakottaa myös Phase 2:een.
    
    TOTEUTUS: Jos Phase 1:ssä erä A alkoi ennen erää B (sama ohjelma), Phase 2:ssa
              lisätään rajoite Entry_2(A,1) <= Entry_2(B,1). Tämä eliminoi kaikki
              permutaatiot joissa järjestys olisi eri.
    
    Oletus: '0' (pois päältä)
    Vaikutus: Kun päällä, CP-SAT ei tuhlaa aikaa kokeilemalla identtisten erien
              eri järjestyksiä Stage 1:ssä. Voi nopeuttaa optimointia merkittävästi
              kun on useita saman ohjelman eriä (esim. 5+ erää samalla ohjelmalla).
    Käyttötapaus: Kun samaa käsittelyohjelmaa ajetaan useilla erillä ja halutaan
                  nopeuttaa Phase 2:ta eliminoimalla symmetriset ratkaisut.
    Tekninen huomio: Klassinen symmetrianmurtaja (symmetry breaking constraint).
    """
    return os.getenv("CPSAT_PHASE2_ANCHOR_STAGE1", "0") in ("1", "true", "True")

def get_cpsat_phase2_window_margin_sec():
    """Aikaikkunan loppumarginaali sekunteina
    
    Phase 2 rajoittaa jokaisen erän aikaikkunaa Phase 1:n ratkaisun perusteella.
    Koska Phase 1:n ratkaisu on AINA nopeampi kuin Phase 2 voi saavuttaa, aikaikkunan
    alaraja on Phase 1:n Entry-aika. Marginaali lisätään vain ylärajaan (Exit + M).
    
    IKKUNA: [Entry_phase1, Exit_phase1 + margin]
    
    Oletus: 600 sekuntia (10 minuuttia)
    Vaikutus: Suurempi marginaali = enemmän joustavuutta loppuaikoihin = parempi ratkaisu (hitaampi).
              Pienempi marginaali = tiukempi ylärajoitus = nopeampi (mutta vähemmän optimaalinen).
    Esimerkki: Jos Phase 1 antoi erälle Entry=1000, Exit=5000, marginaalilla 600:
               → Phase 2:n ikkuna on [1000, 5600] (EI [400, 5600])
    TÄRKEÄÄ: Ikkuna EI ole symmetrinen! Phase 1 ratkaisu on lähtökohta, ei keskipiste.
    Suositus: 600-900s normaalille ajolle
    """
    try:
        return int(float(os.getenv("CPSAT_PHASE2_WINDOW_MARGIN_SEC", "600")))
    except:
        return 600

def get_cpsat_phase2_window_stage_margin_sec():
    """Stage-kohtainen aikaikkunan marginaali sekunteina
    
    Kuten window_margin, mutta stage-tasolla (jokainen vaihe erikseen).
    Rajoittaa kunkin vaiheen alkamis- ja päättymisaikaa Phase 1:n mukaan.
    
    Oletus: 300 sekuntia (5 minuuttia)
    Vaikutus: Tiukempi kuin batch-tason marginaali, koska stage on pienempi yksikkö.
              Suurempi arvo antaa enemmän joustavuutta, mutta voi hidastaa ratkaisua.
    """
    try:
        return int(float(os.getenv("CPSAT_PHASE2_WINDOW_STAGE_MARGIN_SEC", "300")))
    except:
        return 300

def get_cpsat_phase2_overlap_mode():
    """Aikaikkunan päällekkäisyyden hallintatapa
    
    Määrittää kuinka eri erät voivat olla ajallisesti päällekkäin Phase 2:ssa.
    
    Vaihtoehdot:
    - 'phase1_with_margin': Käyttää Phase 1 ratkaisua + marginaalia (oletus, suositeltu)
    - 'anchored': Käyttää ankkuroitua ikkunaa käsittelyohjelman maksimikeston mukaan
    - 'sliding': Käyttää liukuvaa ikkunaa (dynaamisempi, mutta hitaampi)
    
    Oletus: 'phase1_with_margin'
    Vaikutus: Vaikuttaa siihen, mitkä erät voivat olla ajallisesti päällekkäin.
              phase1_with_margin on nopein ja antaa hyviä tuloksia.
    Suositus: Älä muuta ilman erityistä syytä.
    """
    return os.getenv("CPSAT_PHASE2_OVERLAP_MODE", "phase1_with_margin").lower()

def get_cpsat_phase2_transporter_safe_margin_sec():
    """Nostimen turvallinen marginaali sekunteina
    
    Lisää aikavaraa nostimen siirtymille ja varmistaa, että nostin
    ehtii siirtyä asemalta toiselle ilman kiirettä.
    
    Oletus: 600 sekuntia (10 minuuttia)
    Vaikutus: Suurempi arvo = enemmän puskuria nostimen siirroille = turvallisempi aikataulu.
              Pienempi arvo = tiukempi aikataulu = voi aiheuttaa ongelmia jos fysiikka ei riitä.
    Suositus: 600s on hyvä lähtökohta. Pienennä vain jos haluat tiukempaa aikataulua
              ja olet varma että nostimet ehtivät.
    """
    try:
        return int(float(os.getenv("CPSAT_PHASE2_TRANSPORTER_SAFE_MARGIN_SEC", "600")))
    except:
        return 600

def get_cpsat_phase2_avoid_time_margin_sec():
    """Avoid-rajoitteiden aikamarginaali sekunteina
    
    Kun kaksi nostinta liikkuu samassa tilassa (avoid-alue), tämä määrittää
    minimaalisen aikaeron niiden välillä törmäysten välttämiseksi.
    
    Oletus: 3 sekuntia
    Vaikutus: Suurempi arvo = enemmän turvaväliä nostimien välillä = turvallisempi.
              Pienempi arvo = tiukempi aikataulu = riski törmäyksiin.
    Käyttötapaus: Jos nostimilla on yhteinen alue (esim. saman radan osuus),
                  tämä varmistaa että ne eivät ole siellä samaan aikaan.
    Suositus: 3-5s riittää useimmille tapauksille.
    """
    try:
        return int(float(os.getenv("CPSAT_PHASE2_AVOID_TIME_MARGIN_SEC", "3")))
    except:
        return 3

def get_cpsat_phase2_avoid_dynamic_enable():
    """Käytetäänkö dynaamista avoid-marginaalia
    
    Dynaaminen marginaali skaalaa avoid-ajan asemien välisen etäisyyden mukaan:
    mitä pidempi yhteinen alue, sitä enemmän aikaa tarvitaan.
    
    Oletus: '0' (pois päältä)
    Vaikutus: Kun päällä, avoid-aika lasketaan kaavalla:
              avoid_time = base_margin + (overlap_distance_mm * per_mm_factor)
              Tämä tekee aikataulusta realistisemman mutta hieman monimutkaisemman.
    Suositus: Laita päälle jos nostimilla on pitkiä yhteisiä alueita ja haluat
              tarkemman mallinnuksen.
    """
    return str(os.getenv("CPSAT_PHASE2_AVOID_DYNAMIC_ENABLE", "0")).strip().lower() in ("1", "true", "yes", "on")

def get_cpsat_phase2_avoid_dynamic_per_mm_sec():
    """Dynaaminen avoid-marginaali per millimetri per sekunti
    
    Kerroin dynaamiselle avoid-marginaalille. Käytetään vain jos 
    avoid_dynamic_enable on päällä.
    
    Oletus: 0.0 (ei lisää)
    Vaikutus: Esimerkki: 0.002 tarkoittaa 2 sekuntia per 1000mm yhteistä aluetta.
              Jos nostimilla on 2000mm yhteinen alue → lisää 4s avoid-aikaa.
    Suositus: 0.001-0.003 on järkevä arvo, jos käytät dynaamista laskentaa.
    """
    try:
        return float(os.getenv("CPSAT_PHASE2_AVOID_DYNAMIC_PER_MM_SEC", "0"))
    except:
        return 0.0

def get_cpsat_phase2_decompose():
    """Käytetäänkö hajotusta (decompose)
    
    Hajottaa suuren optimointiongelman pienempiin osiin aikaikkunoiden perusteella.
    Jokainen osa ratkaistaan erikseen, mikä nopeuttaa suurten ongelmien ratkaisua.
    
    Oletus: '1' (päällä)
    Vaikutus: Kun päällä, CP-SAT jakaa erät komponentteihin joiden aikaikkunat eivät
              leikkaa. Tämä voi nopeuttaa ratkaisua merkittävästi suurilla erämäärillä
              (>30 erää), mutta saattaa antaa hieman heikomman globaalin ratkaisun.
    Käyttötapaus: Suuri ongelma (50+ erää) joka ei ratkea kohtuullisessa ajassa.
    Suositus: Kokeile jos Phase 2 kestää yli 2 tuntia ilman hyvää ratkaisua.
    """
    return os.getenv("CPSAT_PHASE2_DECOMPOSE", "0") in ("1", "true", "True")

def get_cpsat_phase2_decompose_append():
    """Liitetäänkö hajotuksen tulokset (sisäinen käyttö)
    
    SISÄINEN PARAMETRI - älä muuta ilman erityistä syytä.
    
    Käytetään hajotuslogiikassa määrittämään, liitetäänkö komponenttien
    tulokset yhteen vai ylikirjoitetaanko ne.
    
    Oletus: '0' (ei liitä)
    Vaikutus: Tekninen parametri hajotuksen toteutukselle.
    """
    return os.getenv("CPSAT_PHASE2_DECOMPOSE_APPEND", "0") in ("1", "true", "True")

def get_cpsat_phase2_decompose_guard_sec():
    """Hajotuksen guard-aika sekunteina
    
    Kun käytetään hajotusta, tämä lisää puskuria komponenttien välille
    varmistaakseen että ne eivät häiritse toisiaan ajallisesti.
    
    Oletus: 600 sekuntia (10 minuuttia)
    Vaikutus: Suurempi guard = varmempi että komponentit pysyvät erillään.
              Pienempi guard = tiukempi aikataulu mutta riski päällekkäisyyksiin.
    Suositus: Pidä 600s jos käytät hajotusta. Kasvata 900-1200s jos ongelmia.
    """
    try:
        return int(float(os.getenv("CPSAT_PHASE2_DECOMPOSE_GUARD_SEC", "600")))
    except:
        return 600

# ============================================================================
# YLEISET CP-SAT KONFIGURAATIOT
# ============================================================================

def get_cpsat_log_progress():
    """Tulostetaanko ratkaisun eteneminen
    
    Näyttää CP-SAT:n sisäisen hakulokin reaaliajassa. Hyödyllinen
    debuggauksessa ja pitkissä ajoissa sen näkemiseksi mitä tapahtuu.
    
    Oletus: '0' (pois päältä)
    Vaikutus: Kun päällä, CP-SAT tulostaa jatkuvasti:
              - Löydetyt ratkaisut ja niiden laatu
              - Rajat (bounds) ja gap optimaaliseen
              - Mitä strategioita käytetään
              - Kuinka monta muuttujaa ja rajoitetta on jäljellä
    Käyttötapaus: Debuggaus, pitkien ajojen seuranta, suorituskyvyn analyysi
    Suositus: Laita päälle jos haluat nähdä mitä CP-SAT tekee sisäisesti.
              Tuottaa PALJON tulostetta, joten älä käytä normaalissa ajossa.
    """
    return os.getenv('CPSAT_LOG_PROGRESS', '0') in ('1', 'true', 'True')


# ============================================================================
# PIKAOPAS PARAMETRIEN SÄÄTÖÖN
# ============================================================================
#
# YLEISIMMÄT SÄÄDÖT:
# ------------------
# 1. Nopeuta Phase 2:ta:
#    - Vähennä get_cpsat_phase2_max_time → esim. 600s (10min)
#    - Vähennä get_cpsat_phase2_window_margin_sec → esim. 300s
#
# 2. Paranna Phase 2:n laatua (hitaampi):
#    - Kasvata get_cpsat_phase2_max_time → esim. 7200s (2h)
#    - Kasvata get_cpsat_phase2_window_margin_sec → esim. 900s
#
# 3. Debuggaus ja seuranta:
#    - Laita get_cpsat_log_progress päälle ('1')
#
# 4. Suuret ongelmat (50+ erää):
#    - Kokeile get_cpsat_phase2_decompose → '1'
#    - Varmista riittävä get_cpsat_phase2_max_time → 3600s+
#
# 5. Turvallisempi aikataulu (enemmän puskuria):
#    - Kasvata get_cpsat_phase2_transporter_safe_margin_sec → 900s
#    - Kasvata get_cpsat_phase2_avoid_time_margin_sec → 5s
#
# MUISTA:
# - Voit yhä käyttää ympäristömuuttujia yliajoon:
#   CPSAT_PHASE2_MAX_TIME=7200 python main.py
# - Useimmat parametrit toimivat hyvin oletusarvoilla
# - Säädä vain jos tiedät mitä teet tai testaat jotain
#
# ============================================================================
