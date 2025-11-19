# config.py – muuttujien tarkoitus ja käyttö

Tämä dokumentti kuvaa `config.py`-tiedostossa määriteltyjen konfiguraatioparametrien tarkoituksen ja käytön.

## Yleistä
Kaikki parametrit voidaan yliajaa ympäristömuuttujilla (esim. `CPSAT_PHASE2_MAX_TIME=7200 python main.py`).

---

## CP-SAT Phase 1
- **get_cpsat_phase1_groups**: Käytetäänkö ryhmärajoitetta (kaikki vaiheet samalle nostimelle). Oletus: päällä.
- **get_cpsat_phase1_max_time**: Maksimiaika (s) Phase 1 -optimoinnille. Oletus: 0 (ei rajaa).
- **get_cpsat_phase1_threads**: Säikeiden määrä Phase 1:lle. Oletus: 0 (automaattinen).

## CP-SAT Phase 2
- **get_cpsat_phase2_max_time**: Maksimiaika (s) Phase 2 -optimoinnille. Oletus: 7200 (2h).
- **get_cpsat_phase2_threads**: Säikeiden määrä Phase 2:lle. Oletus: 0 (automaattinen).
- **get_cpsat_phase2_anchor_stage1**: Lukitaanko identtisten ohjelmien erien järjestys Phase 1:n mukaiseksi. Oletus: pois päältä.
- **get_cpsat_phase2_window_margin_sec**: Aikaikkunan ylärajan marginaali (s). Oletus: 600.
- **get_cpsat_phase2_window_stage_margin_sec**: Vaihekohtainen marginaali (s). Oletus: 300.
- **get_cpsat_phase2_overlap_mode**: Aikaikkunoiden päällekkäisyyden käsittelytapa. Oletus: 'phase1_with_margin'.
- **get_cpsat_phase2_transporter_safe_margin_sec**: Nostimen siirtymien turvamarginaali (s). Oletus: 600.
- **get_cpsat_phase2_avoid_time_margin_sec**: Avoid-alueen minimi turvamarginaali (s). Oletus: 3.
- **get_cpsat_phase2_avoid_dynamic_enable**: Käytetäänkö dynaamista avoid-marginaalia. Oletus: pois päältä.
- **get_cpsat_phase2_avoid_dynamic_per_mm_sec**: Dynaamisen avoid-marginaalin kerroin (s/mm). Oletus: 0.0.
- **get_cpsat_phase2_decompose**: Hajotetaanko ongelma osiin. Oletus: pois päältä.
- **get_cpsat_phase2_decompose_append**: Liitetäänkö hajotuksen tulokset. Oletus: pois päältä.
- **get_cpsat_phase2_decompose_guard_sec**: Hajotuksen osien välinen puskuriaika (s). Oletus: 600.

## CP-SAT Phase 3
- **get_cpsat_phase3_max_time**: Maksimiaika (s) Phase 3 -optimoinnille. Oletus: 7200.
- **get_cpsat_phase3_threads**: Säikeiden määrä Phase 3:lle. Oletus: 0 (automaattinen).

## Yleiset asetukset
- **get_cpsat_log_progress**: Tulostetaanko CP-SAT:n etenemisloki reaaliajassa. Oletus: pois päältä.

---

## Käyttövinkit
- Useimmat parametrit toimivat hyvin oletusarvoilla.
- Nopeuta Phase 2:ta pienentämällä max_time ja window_margin.
- Paranna laatua kasvattamalla max_time ja window_margin.
- Suurille ongelmille (50+ erää) käytä decompose-parametria.
- Turvallisempi aikataulu: kasvata transporter_safe_margin_sec ja avoid_time_margin_sec.

Katso tarkemmat kuvaukset ja suositukset suoraan `config.py`-tiedoston docstringeistä.
