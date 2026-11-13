# Richtlijnen, Rubric & Beoordelingsgids: Pacman Capture The Flag
**Vak:** Decision Making (Minor Autonome Systemen)  
**Instituut:** Hogeschool van Amsterdam (HvA) / Universiteit van Amsterdam (UvA)  
**Docententeam:** o.a. Patrick Kok  
**Competitie:** Pacman Capture The Flag (CTF) Toernooi  
**Doel van dit document:** Vastleggen van alle eisen, de beoordelingsrubric, toernooiregels en interviewvragen uit de colleges en presentaties, zodat alle informatie centraal en permanent in de repository beschikbaar is.

---

## 1. Overzicht van de Opdracht

De eindopdracht van *Decision Making* is een multi-agent Capture The Flag competitie waarin teams van twee autonome agents tegen elkaar strijden op een tweedimensionaal doolhofrooster:
- Het speelveld is verdeeld in een **rode helft (links)** en een **blauwe helft (rechts)**.
- Agents op de eigen helft zijn **geesten** (verdedigers). Zodra een agent de middellijn oversteekt, transformeert deze in een **Pacman** (aanvaller).
- Een Pacman verzamelt bolletjes op vijandig grondgebied. Deze worden pas omgezet in wedstrijdpunten wanneer de Pacman veilig terugkeert over de eigen grens.
- Wordt een Pacman op vijandig terrein opgegeten door een vijandige geest, dan respawnt hij op de startpositie en "ontploffen" alle verzamelde bolletjes terug op het bord.
- **Inzending:** Uitsluitend het bestand `myTeam.py` (bevat de code van beide agents) plus het **Technisch Verslag** (`Verslag_Pacman_Contest_DM_E.md`).

---

## 2. De Officiële Rubric (4 Pijlers)

Zoals gepresenteerd tijdens de kick-off en hoorcolleges, wordt het eindcijfer bepaald aan de hand van vier hoofdpijlers:

```
                              ┌────────────────────────────────────────┐
                              │      Eindbeoordeling Decision Making    │
                              └───────────────────┬────────────────────┘
             ┌────────────────────────┬───────────┴────────────┬────────────────────────┐
             ▼                        ▼                        ▼                        ▼
┌─────────────────────────┐ ┌───────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│ 1. Theorie & Techniek   │ │ 2. Toernooi &     │ │ 3. Technisch Verslag    │ │ 4. Mondeling Assessment │
│    (Complexiteit AI)    │ │    Prestaties     │ │    (Documentatie)       │ │    (Explainability)     │
│ • Doolhofanalyse        │ │ • 100% vs Base    │ │ • Wiskundige modellen   │ │ • Replay analyse        │
│ • Bayesiaanse mist      │ │ • Win vs Klas     │ │ • 3 Iteraties vgl.      │ │ • Waarom-vragen         │
│ • Doelgerichte A*       │ │ • < 1.0s op Pi    │ │ • Testtabellen & data   │ │ • Individuele kennis    │
└─────────────────────────┘ └───────────────────┘ └─────────────────────────┘ └─────────────────────────┘
```

---

### Pijler 1: Theoretische Diepgang & Complexiteit van Technieken

In deze pijler beoordelen de docenten hoe geavanceerd de toegepaste technieken zijn en of de student theorie uit de modules (*Search, Multi-Agent, Probabilistiek/Bayes, MDP/Reinforcement*) doordacht heeft geïntegreerd:

| Cijfer / Niveau | Kenmerken & Eisen uit de Presentaties |
| :--- | :--- |
| **Onvoldoende (1 – 5)** | • Eenvoudige reflex-agent met hardgecodeerde acties of puur willekeurige stappen.<br>• Geen zoekalgoritmen, geen rekening houden met vijanden of gevaren. |
| **Voldoende (6)** | • Een eenvoudige Finite State Machine (FSM) of regelgebaseerde beslisboom.<br>• Gebruik van basis kortste paden (BFS/Dijkstra) naar het dichtstbijzijnde bolletje.<br>• *Voorbeeld in ons repo:* `simpleTeam.py`. |
| **Goed (7 – 8)** | • Duidelijke rolverdeling tussen 1 Aanvaller en 1 Verdediger.<br>• $A^*$-padplanning met dynamische kosten voor naderende geesten.<br>• Logica voor capsules en veilig terugkeren naar de grens bij gevaar. |
| **Uitmuntend (9 – 10)** | **Geavanceerde compositie van multi-agent technieken:**<br>1. **Topologische Doolhofanalyse (Cul-de-sac Pruning):** Voorberekenen van doodlopende gangen en gangdieptes vóór aanvang van het spel. Nooit klem komen te zitten doordat de agent alleen een tunnel in gaat als hij bewezen sneller buiten is dan de geest bij de ingang kan zijn.<br>2. **Probabilistische Toestandsschatting (Bayesiaanse Filtering):** Bijhouden van kansverdelingen over vijandige posities in dichte mist (*fog of war* buiten 5 stappen) via sonar-afstandsmetingen ($[-6, +6]$ ruis) en het registreren van verdwijnend voedsel (inbreker-alarm).<br>3. **Goal Commitment & Dynamische Flankering:** Vasthouden aan gekozen doelen (geen doel-oscillatie / target-thrashing) en het automatisch omzeilen van kamperende verdedigers via open grensovergangen. |

---

### Pijler 2: Competitieve Prestaties & Robuustheid (Toernooi)

Het team wordt getest in een geautomatiseerd toernooi (round-robin) op een **Raspberry Pi 4 / 5 Model B (8 GB RAM)**:

1. **Winst tegen `baselineTeam`:**
   - **Verplicht 100% winstpercentage.** Verliezen of gelijkspelen tegen de baseline leidt tot puntenaftrek.
2. **Prestaties tegen klasgenoten:**
   - Standhouden en overwinningen behalen tegen teams van medestudenten over verschillende kaarten (`defaultCapture`, `alleyCapture`, `officeCapture`, `distantCapture`, `bloxCapture` en random seeds `RANDOM[seed]`).
3. **Hardware- en Snelheidsrestricties:**
   - **Tijdslimiet:** Maximaal **1.0 seconde** rekentijd per actie. Na 3 waarschuwingen volgt automatische diskwalificatie. Een enkele actie die langer dan **3.0 seconden** duurt leidt direct tot een forfeit (verlies).
   - **Opstarttijd:** Maximaal **15 seconden** in `registerInitialState` om afstanden of doolhoftransformaties voor te berekenen.
   - **Zero Exception Rule:** Nul ongehandelde fouten of crashes in de wedstrijdlogs.
   - **Geen Multithreading:** Berekeningen mogen uitsluitend plaatsvinden tijdens de eigen beurt van de agent. Threads op de achtergrond zijn verboden en leiden tot diskwalificatie.

---

### Pijler 3: Technisch Verslag (`Verslag_Pacman_Contest_DM_E.md`)

De schriftelijke verantwoording van het project. Dit moet een formeel, academisch gestructureerd verslag zijn:

1. **Evolutie & Vergelijking van Iteraties:**
   - Beschrijf minimaal 2 tot 3 ontwikkelingsfasen (bv. Iteratie 1: Heuristische Evaluator, Iteratie 2: Simpele FSM, Iteratie 3: Geavanceerde Compositie met Topologie & Bayes).
2. **Wiskundige en Formele Onderbouwing:**
   - Geen vage programmeerverhaaltjes, maar formele definities van:
     * De $A^*$-evaluatiefunctie: $f(n) = g(n) + h(n)$ met consistente heuristiek en strafkostenvelden.
     * De Bayesiaanse sensorfusie: Kansverdeling $B_t(s)$ bijgewerkt via de meetvergelijking $P(z_t \mid s) = \frac{1}{13}$.
     * De wiskundige tunnel-veiligheidsconditie:
       $$d(g, J(c)) > d(\text{pacman}, J(c)) + \text{depth}(c) + 2$$
3. **Empirische Validatie:**
   - Gestructureerde tabellen met scores, speelduur en gemiddelde zoektijd per zet over meerdere officiële layouts.

---

### Pijler 4: Mondeling Assessment / Trainer-Interview (Explainability)

Tijdens de eindbeoordeling gaan de studenten in gesprek met de docent/trainer. Dit gesprek draait om **Explainability (Verklaarbaarheid)**:

* De trainer opent een wedstrijd-replay en zet deze stil op een cruciaal moment.
* **De "Waarom"-eis:** De studenten moeten binnen maximaal **2 minuten** helder, theoretisch en zonder twijfel kunnen uitleggen *waarom* een agent een specifieke zet koos.
* **Individuele toetsing:** Beide studenten (Matin & Gabriel) worden individueel bevraagd. Blind vertrouwen op elkaars code wordt bestraft; beiden moeten elk onderdeel kunnen verantwoorden.

---

## 3. Spelregels & Spelspecificaties in Detail

| Parameter | Waarde / Regel | Toelichting |
| :--- | :--- | :--- |
| **Aantal Spelers** | 4 agents (2 teams van 2) | Rood: indices `[0, 2]`. Blauw: indices `[1, 3]`. |
| **Maximale Zetten** | 1200 totale zetten | 300 beurten per individuele agent. |
| **Eindconditie** | 2 overgebleven pellets of zetlimiet | Het team met de meeste verzilverde punten wint. Bij gelijke score is het een gelijkspel. |
| **Gezichtsveld (Zicht)** | Manhattan afstand $\le 5$ | Vijanden binnen 5 stappen zijn exact zichtbaar (positie en kijkrichting). |
| **Mist (Fog of War)** | Manhattan afstand $> 5$ | Positie is onbekend; agents ontvangen enkel een ruizige afstand $d_{\text{noisy}} = d_{\text{true}} + e$, waarbij $e \in \{-6, \dots, +6\}$ uniform gekozen is. |
| **Krachtcapsules** | 40 beurten Scared-status | Geesten van de tegenstander worden blauw en kwetsbaar. Eet Pacman een scared geest, dan respawnt die geest op de startpositie. |
| **Puntenregeling** | 1 punt per afgeleverd bolletje | Eten van vijanden levert géén punten op, maar ontregelt de tegenstander. |

---

## 4. Cheat Sheet: Vragen & Modelantwoorden voor het Mondeling Assessment

Hieronder staan de meest voorkomende vragen die docenten tijdens het assessment stellen, met de exacte antwoorden gebaseerd op onze implementatie in `myTeam.py`:

### Vraag 1: "Waarom keert Pacman hier plotseling om terwijl er nog stippen voor hem liggen?"
> **Modelantwoord:**  
> *"Onze agent heeft een dubbele veiligheidscheck:  
> 1. Hij draagt op dat moment al minimaal 4 pellets (of minimaal 1 pellet terwijl een actieve geest binnen bereik is). Om het verzamelde voedsel veilig te stellen, schakelt hij rationeel over naar de `RETURN_HOME` modus via het kortste veilige pad naar de grens.  
> 2. Als de stip in een doodlopende gang ligt, toetst onze `MazeAnalyzer` of de afstand van de naderende geest tot de tunnelingang kleiner is dan onze eigen retourtijd plus de tunneldiepte ($d(g, J) \le d(p, J) + \text{depth} + 2$). Als dat zo is, is de gang een zekere valstrik en keert hij direct om."*

### Vraag 2: "Waarom valt de verdediger de Pacman niet aan als hij 'scared' is?"
> **Modelantwoord:**  
> *"Omdat de tegenstander een krachtcapsule heeft gegeten. Als onze verdediger als scared geest Pacman aanraakt, wordt hij zelf opgegeten en respawnt hij op de beginpositie. Daardoor zou de tegenstander tot wel 40 zetten lang vrij spel hebben om onze hele helft leeg te eten. In onze scared-toestand houdt de verdediger daarom een veilige buffer van 2 tot 3 stappen aan en positioneert hij zich tussen de indringer en onze resterende stippen om de doorgang te blokkeren tot de scared-timer afloopt."*

### Vraag 3: "Waarom loopt de verdediger doelgericht naar een leeg vakje in dichte mist?"
> **Modelantwoord:**  
> *"Onze `BayesianBeliefTracker` combineert twee informatiestromen:  
> Ten eerste monitoren wij het eigen voedselbestand per tick. Zodra een pellet op coördinaat $(x, y)$ verdwijnt zonder dat wij daar zelf staan, is met 100% zekerheid bekend dat een vijandige Pacman zich op exact dat vakje bevindt.  
> Ten tweede vermenigvuldigen we bij afwezigheid van direct zicht de sonarmetingen met uniforme kans $\frac{1}{13}$ voor afstanden binnen $[-6, +6]$ en propageren we dit over de legale overgangen. De verdediger navigeert direct naar de maximale waarschijnlijkheidspositie."*

### Vraag 4: "Hoe voorkomt jullie team dat agents gaan 'oscilleren' (doelloos heen en weer schudden bij de grens)?"
> **Modelantwoord:**  
> *"We lossen dit op met twee mechanismen:  
> 1. **Goal Commitment (Target Persistence):** In plaats van elke tick opnieuw te wisselen tussen stippen die een fractie in score verschillen, committeert de aanvaller zich aan zijn gekozen stip totdat deze is opgegeten of totdat er acuut gevaar optreedt binnen afstand 2.  
> 2. **Dynamische Flankering:** Wanneer een vijandelijke verdediger direct bij de centrale grensovergang kampeert, berekent onze BFS een omtrekkende route via een alternatieve grensovergang aan de flanken waar de afstand tot de vijand maximaal is."*

---

## 5. Overzicht van Onze Drie Geïmplementeerde Iteraties

In de repository zijn de drie iteraties bewaard gebleven ter vergelijking:

```
pacman-competition-3-master/
├── heuristicTeam.py   --> Iteratie 1: Reflex-evaluator (lokale features & gewichten)
├── simpleTeam.py      --> Iteratie 2: Toestand-automaat (FSM, 1 aanvaller / 1 verdediger, stabiele 6)
├── ApexPredators.py   --> Iteratie 3: Geavanceerde Compositie (Topologie + Bayes + A*)
└── myTeam.py          --> Onze definitieve inlevering (identiek aan ApexPredators.py voor 9-10)
```

| Eigenschap | Iteratie 1 (`heuristicTeam`) | Iteratie 2 (`simpleTeam`) | Iteratie 3 (`ApexPredators` / `myTeam`) |
| :--- | :--- | :--- | :--- |
| **Architectuur** | Gewogen lineaire featuresom | Finite State Machine (FSM) | Multi-Agent Compositie (Topologie + Bayes + $A^*$) |
| **Waarneming in Mist** | Enkel direct zicht ($\le 5$) | Zicht $\le 5$ + voedselalarm | Volledige Bayesiaanse kansverdeling ($B_t$) |
| **Doodlopende Gangen** | Negatieve strafscore per stap | Vluchtgedrag bij zichtbare geest | Offline cul-de-sac pruning met wiskundige dieptetest |
| **Toernooiscore vs Baseline** | Wisselend (0-0 tot +8) | Ruime winst (+13) | **Grote overwinningen (+10 tot +37, knock-outs)** |
| **Doel beoordeling** | Experimenteel startpunt | Betrouwbare voldoende (6) | **Maximale score (9 – 10)** |
