# Technisch Verslag: Pacman Capture The Flag
**Vak:** Decision Making (Minor Autonome Systemen)  
**Instituut:** Hogeschool van Amsterdam (HvA) / Universiteit van Amsterdam (UvA)  
**Auteurs:** Matin & Gabriel  
**Team:** MazeRunner  
**Bestand:** `myTeam.py`

---

## 1. Inleiding en Doelstelling

Voor de eindopdracht van het vak *Decision Making* hebben wij een team van twee samenwerkende agents ontworpen en gebouwd voor *Pacman Capture The Flag*. Het doel is om zo veel mogelijk voedselpunten op de helft van de tegenstander te verzamelen en veilig over de eigen middenlijn terug te brengen, terwijl we ons eigen voedsel verdedigen tegen indringers.

Bij ons ontwerp hebben wij gekozen voor een heldere, betrouwbare aanpak met gescheiden rollen en een toestand-automaat (Finite State Machine), zodat elke zet van onze agents tijdens een replay direct te verklaren is.

---

## 2. Ontwerp en Werking van `myTeam.py`

Ons team (**MazeRunner**) bestaat uit twee vaste rollen:
1. **`MazeRunnerOffense` (Aanvaller):** Verzamelt stippen aan de overkant en brengt ze veilig terug.
2. **`MazeRunnerDefense` (Verdediger):** Blijft op de eigen helft en onderschept vijandelijke Pacmans.

Beide agents erven van `MazeRunnerBase`, waarin we bij de start (`registerInitialState`) de grenslijn en alle open grensovergangen bepalen. Voor de navigatie gebruiken we de voorberekende doolhofafstanden (`getMazeDistance`).

### 2.1 Aanvaller (`MazeRunnerOffense`)
De aanvaller kiest elke beurt uit drie toestanden (op volgorde van prioriteit):
1. **RETREAT (Terug naar huis):** Zodra we minimaal 3 stippen dragen, of minimaal 1 stip dragen terwijl een spook binnen 4 stappen nadert (of de tijd bijna op is / er nog <= 2 stippen over zijn), lopen we via de dichtstbijzijnde grensovergang terug naar onze eigen helft om te scoren.
2. **CAPSULE (Krachtcapsule pakken):** Als er een spook in de buurt is (afstand < 6) en er een krachtcapsule dichterbij ligt dan dat spook, pakken we eerst de capsule zodat de spoken 40 zetten kwetsbaar worden.
3. **COLLECT (Stippen eten):** In alle andere gevallen lopen we naar de dichtstbijzijnde stip. Vakjes waar een actief spook staat (en de 4 aangrenzende vakjes) slaan we over als verboden terrein (`forbidden_cells`).

### 2.2 Verdediger (`MazeRunnerDefense`)
De verdediger kiest elke beurt uit drie toestanden:
1. **INTERCEPT (Onderscheppen):** Zien we een vijand op onze helft (binnen zichtbereik van 5 stappen)? Dan jagen we direct op hem af. Zijn we zelf `scared` (omdat de vijand een capsule at), dan houden we ~2.5 stappen afstand op eigen helft zodat we de weg blijven blokkeren zonder opgegeten te worden.
2. **ALARM (Verdwenen voedsel):** Buiten 5 stappen zien we tegenstanders niet door de mist. Daarom vergelijken we elke beurt ons overgebleven voedsel met de vorige beurt. Verdwijnt er een stip, dan weten we dat daar net een indringer liep en lopen we direct naar die positie.
3. **PATROL (Grens bewaken):** Als er niets te zien is en er geen alarm actief is, bewaken we de middelste doorgang op de grenslijn.

---

## 3. Testresultaten vs `baselineTeam`

Wij hebben `myTeam.py` getest tegen het standaard `baselineTeam` over verschillende kaarten:

| Kaart | Teamkleur | Scoreverschil | Uitkomst |
| :--- | :---: | :---: | :--- |
| `defaultCapture` | Rood | **+11** | Gewonnen |
| `alleyCapture` | Rood | **+2** | Gewonnen |
| `officeCapture` | Rood | **+41** | Gewonnen |
| `distantCapture` | Rood | **+16** | Gewonnen |
| `bloxCapture` | Rood | **+17** | Gewonnen |
| `RANDOM1` | Rood | **+18** | Gewonnen |
| `RANDOM13` | Rood | **+16** | Gewonnen |

Alle potjes draaiden ruim binnen de 1.0 seconde tijdslimiet per zet en zonder foutmeldingen of waarschuwingen.

