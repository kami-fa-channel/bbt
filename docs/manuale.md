# Manuale di legatoria — dal PDF al libro cucito

Questo manuale copre tutta la catena che porta da un PDF qualsiasi a un libro rilegato in casa, in brossura o in copertina rigida: imposizione delle pagine, stampa fronte/retro a blocchi, piegatura, guardie, foratura, cucitura e copertina. È la parte manuale, che è quella dove si sbaglia di più.

Fa parte del progetto **bbt** (*books binding tool*) ([README](../README.md)), il programma che si occupa della parte informatica: imposizione, misure della copertina e tasselli. Il manuale si legge anche da solo, senza il programma. Le opzioni come `-f`, `-g`, `-p` o `--shingling`, che compaiono nei capitoli, sono quelle di `legatoria imposizione`; nella finestra sono i campi *Fogli per fascicolo*, *Fogli di guardia*, *Bianche di correzione*, *Shingling* (la tabella di corrispondenza è nel [README](../README.md#imposizione)).

**Indice**

1. [Vocabolario](#1-vocabolario)
2. [Che legatura scegliere](#2-che-legatura-scegliere)
3. [Quanti fogli mettere in un fascicolo](#3-quanti-fogli-mettere-in-un-fascicolo)
4. [Destra o sinistra: la regola d'oro](#4-destra-o-sinistra-la-regola-doro)
5. [Le guardie](#5-le-guardie)
6. [Carta e direzione della fibra](#6-carta-e-direzione-della-fibra)
7. [Stampa](#7-stampa)
8. [Stampa a tranches e formule](#8-stampa-a-tranches-e-formule)
9. [Logistica post-stampa](#9-logistica-post-stampa)
10. [Piegatura e pressatura](#10-piegatura-e-pressatura)
11. [Rifilo del taglio davanti e shingling](#11-rifilo-del-taglio-davanti-e-shingling)
12. [Foratura](#12-foratura)
13. [Cucitura](#13-cucitura)
14. [Colle](#14-colle)
15. [La brossura](#15-la-brossura)
16. [La copertina rigida](#16-la-copertina-rigida)
17. [Le scritte sulla copertina](#17-le-scritte-sulla-copertina)

---

## 1. Vocabolario

#### Il blocco e la cucitura

| Termine | Significato |
| --- | --- |
| **Pagina / facciata** | Una singola facciata stampata. |
| **Foglio fisico** | Un foglio A4 stampato fronte/retro e piegato a metà → **4 pagine** del libro in formato A5. |
| **Fascicolo (segnatura)** | Un gruppo di fogli piegati insieme e cuciti con un'unica passata di filo. Con `F` fogli si hanno `4 × F` pagine. |
| **Blocco libro** | L'insieme dei fascicoli cuciti, prima della copertina. |
| **Guardia (risguardo)** | Foglio all'inizio e alla fine del blocco: una sua metà viene incollata al cartone della copertina, l'altra resta libera (il *volante*). Capitolo 5. |
| **Brachetta** | Striscia di carta o telina piegata a metà, incollata a cavallo della piega di un fascicolo per rinforzarlo prima di cucirlo. |
| **Fibra, grana** | La direzione preferenziale delle fibre della carta: deve sempre correre parallela al dorso. Capitolo 6. |
| **Nastro** | La fettuccia (di solito di cotone) su cui si cuciono i fascicoli, perpendicolare al dorso; il filo la scavalca a ogni foro. Il libro finito ha tanti nastri quanti ne hai usati, visibili come rilievi orizzontali se il dorso non è rivestito. Capitolo 12. |
| **Catenella (*kettle stitch*)** | Il nodo che, a fine fascicolo, aggancia il filo al fascicolo precedente. |
| **Nodo da tessitore (*weaver's knot*)** | Il nodo con cui si unisce un filo nuovo a uno che sta per finire, a metà cucitura: piccolo e piatto, non fa da tappo nei fori successivi. Capitolo 13. |
| **Scorrimento (*creep*)** | Le pagine più interne di un fascicolo piegato sporgono in avanti rispetto alle esterne. Più fogli si piegano insieme, più sporgono. Capitolo 11. |
| **Rigonfiamento (*swell*)** | L'ispessimento del dorso dovuto al filo accumulato fra i fascicoli, rispetto al taglio davanti. Capitolo 13. |
| **Menabò** | Il fascicolo di prova che si stampa e si piega prima di lanciare tutto il libro. |
| **Marca di collazione** | Il quadratino che il programma stampa su ogni fascicolo, un gradino più in basso del precedente: impilati, formano una diagonale che permette di controllare a colpo d'occhio che nessun fascicolo sia fuori posto o mancante. |

#### La copertina e i suoi pezzi

| Termine | Significato |
| --- | --- |
| **Piatto** | Ciascuna delle due facce rigide (o flessibili, in brossura) della copertina: quella anteriore e quella posteriore. Non è il dorso, che è il pezzo che le unisce sul retro del libro. |
| **Dorso (della copertina)** | Il pezzo che copre la costola del blocco e unisce i due piatti. Da non confondere con il dorso del blocco, cioè la costola cucita del libro stesso: il dorso della copertina la ricopre. Capitoli 16 e 15. |
| **Cassa** | La copertina rigida già montata ma ancora staccata dal blocco: due piatti di cartone e un dorso di cartoncino, tenuti insieme dal rivestimento. Si costruisce a parte e solo alla fine si incassa. Capitolo 16. |
| **Incassatura** | L'operazione finale che incolla il blocco cucito dentro la cassa già pronta. Capitolo 16.11. |
| **Rivestimento** | Il materiale (carta, tela o pelle) che copre l'esterno della cassa: un solo pezzo che avvolge piatti, gole e dorso. |
| **Gola** | Lo spazio vuoto, sul rivestimento, fra ciascun piatto e il dorso: è lì che la copertina si piega quando apri il libro, e fa da cerniera. Capitolo 16.6. |
| **Cerniera** | Il punto in cui la copertina si piega per aprirsi. Nella copertina rigida coincide con la gola; nella brossura sono due solchi incisi (le **cordonature**, capitolo 15.3) che delimitano due strisce di cartoncino larghe 6–8 mm. |
| **Cordonatura** | Il solco inciso (non tagliato) sul cartoncino della brossura, che guida la piega della cerniera nel punto giusto invece di lasciarla capitare a caso. Capitolo 15.3. |
| **Unghia** | Quanto il cartone della copertina sporge oltre il blocco, su testa, piede e taglio davanti. Capitolo 16.6. |
| **Rimbocco** | Il margine di rivestimento che sborda oltre il cartone e viene ripiegato all'interno, sul retro dei piatti, per bloccarlo. |
| **Capitello** | Le due strisce, a nastro o cucite a mano, visibili a testa e piede del dorso nei libri cartonati: oggi soprattutto decorative. Capitolo 16.5. |
| **Tassello** | Un rettangolo di carta, pelle o tela, con titolo e autore, incollato sul piatto o sul dorso invece di stampare o dorare direttamente sul rivestimento. Capitolo 17.2. |
| **Arco / corda del dorso** | La misura del dorso arrotondato si prende lungo la curva (l'**arco**), non in linea retta da uno spigolo all'altro (la **corda**): l'arco è sempre un po' più lungo. Capitolo 16.6. |
| **Arrotondatura** | Il colpo di martello che dà al dorso del blocco cucito una curva convessa (e al taglio davanti la concavità corrispondente). Capitolo 16.2. |
| **Indorsatura (formazione delle cerniere)** | Il passaggio, facoltativo e più delicato, che ripiega i fascicoli più esterni formando due spalle dove poi si alloggiano i piatti. Da non confondere con l'arrotondatura: stesso attrezzo (il martello), operazione diversa. Capitolo 16.3. |
| **Dorso cavo / dorso incollato** | Due modi di montare il dorso della cassa: nel *dorso cavo* un tubo di carta separa il cartoncino dal dorso del blocco, che così resta libero di flettere; nel *dorso incollato* il cartoncino aderisce direttamente al blocco. Capitolo 16.7. |
| **Precurvare** | Dare in anticipo al cartoncino del dorso la stessa curva del blocco arrotondato, prima di incollarlo: un cartoncino piatto su un dorso curvo non aderisce. Capitolo 16.9. |
| **Cerniera francese** | Nella brossura, la striscia di cartoncino larga 6–8 mm che sta fra le due cordonature esterne e interne, e permette al piatto di aprirsi senza spaccare il dorso. Capitolo 15.3. |
| **Brossura** | Copertina flessibile di cartoncino, incollata (non montata come una cassa). Ne esistono due tipi molto diversi: *fresata* (pagine sciolte, solo colla) e *cucita* (fascicoli interi, come una legatura rigida). Capitolo 15. |
| **Cucitura a sella** | La cucitura di un fascicolo unico, a cavallo della piega centrale: adatta solo a libretti sottili (capitolo 2), diversa dalla cucitura su nastri usata per i libri a più fascicoli. |

---

## 2. Che legatura scegliere

Prima di stampare conviene decidere come sarà rilegato il libro, perché la scelta cambia qualche parametro a monte: quante guardie servono, quanto margine lasciare al dorso, se ha senso arrotondare.

Il criterio è uno solo: **lo spessore del blocco**. Non il numero di pagine in sé, ma quanti millimetri di carta si accumulano, che dipende anche dalla grammatura.

Per una stima veloce, con carta da 80 g/m²: `spessore in mm ≈ pagine × 0,05`. Poi aggiungi il filo della cucitura: circa 0,3–0,5 mm per fascicolo, e non una percentuale fissa (capitolo 13 spiega perché).

| Spessore del blocco | Pagine indicative a 80 g/m² | Legatura consigliata |
| --- | --- | --- |
| fino a 3 mm | fino a 60 | fascicolo unico, cucitura a sella con 3 o 5 fori |
| 3–10 mm | 60–200 | brossura cucita |
| 10–25 mm | 200–500 | brossura cucita, oppure cassa rigida se il libro deve durare |
| 25–40 mm | 500–800 | cassa rigida |
| oltre 40 mm | oltre 800 | cassa rigida, con arrotondatura del dorso |

I confini non sono muri. Sopra i 25 mm la brossura comincia a soffrire: tutto il peso del blocco scarica su una cerniera di cartoncino e su un filo di colla, il dorso si affloscia e col tempo le pagine centrali scendono. Sotto i 10 mm, al contrario, una cassa rigida è sproporzionata: il libro diventa più copertina che testo.

Un libro di riferimento, che resterà aperto sul tavolo mentre lavori, chiede una legatura più solida di un romanzo della stessa taglia. A parità di spessore, sposta la scelta verso la cassa rigida.

### Cosa cambia al crescere del libro

| | sottile, fino a 10 mm | medio, 10–25 mm | grosso, oltre 25 mm |
| --- | --- | --- | --- |
| Nastri e fori (capitolo 12) | 2 nastri, 6 fori | 3 nastri, 8 fori | 3–4 nastri, 8–10 fori |
| Filo di lino | 18/3 | 25/3 | 30/3, sottile per contenere il rigonfiamento |
| Arrotondatura del dorso | non serve | facoltativa | sì |
| Guardie | 1 foglio per lato | 1 foglio per lato | 1–2 fogli, con brachetta |
| Cartone dei piatti | 2 mm | 2,5 mm | 3 mm |
| Unghia | 2–3 mm | 3 mm | 3–4 mm |
| Fogli per fascicolo | secondo il capitolo 3 | secondo il capitolo 3 | come sopra, ma stare bassi limita il rigonfiamento |

L'unica cosa che **non** cambia con la taglia è la direzione della fibra: sempre parallela al dorso, su ogni pezzo (capitolo 6).

---

## 3. Quanti fogli mettere in un fascicolo

Non esiste un numero universale: dipende dalla carta. Due vincoli fisici governano la scelta.

**Lo scorrimento.** Piegando `F` fogli insieme, la pagina più interna sporge in avanti di circa

```
scorrimento ≈ (F − 1) × spessore del foglio
```

È materiale che andrà rifilato al taglio davanti, o che resterà visibile come gradino se non rifili. Sopra il mezzo millimetro si nota.

**Lo spessore sulla piega.** Sulla costola il fascicolo è spesso `2 × F × spessore`. Oltre il millimetro abbondante l'ago non entra più dritto, la piega non tiene e il fascicolo tende a riaprirsi a molla.

Lo spessore del foglio si stima dalla grammatura: per carta non patinata (densità ≈ 0,8 g/cm³)

```
spessore in mm ≈ grammatura / 800
```

quindi 80 g/m² ≈ 0,10 mm, 100 g/m² ≈ 0,125 mm, 160 g/m² ≈ 0,20 mm.

| Carta | Spessore | Fogli/fascicolo sensati | Pagine/fascicolo |
| --- | --- | --- | --- |
| 60–70 g/m² | 0,075–0,09 mm | 5–6 | 20–24 |
| 80 g/m² (fotocopie) | 0,10 mm | 4–5 | 16–20 |
| 90–100 g/m² | 0,11–0,13 mm | 3–4 | 12–16 |
| 120 g/m² | 0,15 mm | 2–3 | 8–12 |
| 160 g/m² e oltre | ≥ 0,20 mm | 1–2 | 4–8 |

C'è poi il compromesso di lavoro: **meno fogli per fascicolo = più fascicoli = più cuciture e più rigonfiamento del dorso**; più fogli per fascicolo = cucitura rapida ma piegatura, foratura e rifilo più difficili. La tabella di `-n` mostra entrambi gli effetti e segnala anche quale valore spreca meno carta bianca nell'ultimo fascicolo.

---

## 4. Destra o sinistra: la regola d'oro

I libri seguono una regola che non dipende dai numeri stampati in fondo alle pagine (romani o arabi), ma solo dal **contatore assoluto del lettore PDF**:

> Qualsiasi pagina che vuoi vedere sul lato **DESTRO** del libro aperto deve occupare una posizione **DISPARI** nel contatore assoluto (1, 3, 5, 7…).
> Le pagine sul lato **SINISTRO** occupano sempre posizioni **PARI**.

### Come trovare dove inserire la bianca (`-p`)

1. Apri il PDF **originale** nel lettore (Okular, Evince…).
2. Vai alla prima pagina che vuoi tassativamente a **destra**: l'inizio del testo, il frontespizio, l'inizio del capitolo I.
3. Leggi il contatore assoluto: "Pagina X di N".
4. Se **X è pari**, passa `-p X`: la bianca prende il posto di `X` e spinge il tuo testo in posizione `X+1`, che essendo dispari finisce a destra.
5. Se **X è dispari**, il file è già corretto.

Puoi correggere più punti in una volta (`-p 4 -p 220 -p 388`): le posizioni si riferiscono **sempre** alla numerazione del PDF originale, ci pensa lo script a tenere conto degli spostamenti.

Attenzione però: ogni bianca inserita inverte la parità di **tutto ciò che segue**. Dopo la prima correzione, i punti che prima erano giusti diventano sbagliati e viceversa. Procedi per prove: correggi il primo punto, rigenera, ricontrolla, e vai avanti.

---

## 5. Le guardie

La guardia è il foglio piegato che si trova all'inizio e alla fine del blocco libro. Una sua metà finisce incollata al cartone del piatto, l'altra resta libera come prima pagina che sfogli. Serve a tre cose: nascondere il cartone, tenere insieme copertina e blocco, e assorbire la trazione dell'apertura.

Ci sono tre modi di attaccarla, e la scelta dipende soprattutto da **se la guardia è della stessa carta del testo o di carta diversa**.

### 5.1 Guardia a cavallo del primo fascicolo

Prendi un foglio piegato e lo infili all'esterno del primo fascicolo, poi cuci tutto insieme.

Semplicissimo, robustissimo, nessuna colla. Ma ha una conseguenza geometrica inevitabile: un foglio piegato ha due metà, e se una sta davanti a pagina 1, **l'altra esce dall'altra parte del fascicolo**, cioè dopo l'ultima pagina di quel fascicolo (pagina 16 con `-f 4`). Ti ritrovi una pagina in più a metà del capitolo I.

Va bene solo se la guardia è **della stessa carta del testo**: allora quella pagina in più sembra un normale foglio bianco e non dà fastidio. Con carta colorata o diversa, si vede e basta.

Se scegli questa strada, la guardia la fai direttamente dallo script con `-g 1`: sono 2 facciate bianche davanti e 2 dietro, che entrano nel primo e nell'ultimo fascicolo e vengono cucite con loro. È il motivo per cui `-g` lavora a *fogli* e non a facciate singole: un numero pari di facciate lascia intatta la parità destra/sinistra di tutto il libro (capitolo 4), una facciata sola la ribalterebbe ovunque.

### 5.2 Guardia cucita a parte, con brachetta

È la soluzione giusta quando la guardia è di carta diversa.

La guardia diventa un **fascicoletto a sé**, fatto di un solo foglio piegato, cucito prima del primo fascicolo (e uno speculare dopo l'ultimo). Le sue due metà restano entrambe davanti a pagina 1: nessuna pagina spuria in mezzo al testo, il fascicolo del testo non viene toccato.

Il problema è che un foglio singolo cucito da solo si strappa: il filo taglia la piega. Si rinforza con la **brachetta**:

1. Taglia una striscia della stessa carta (o di telina da legatoria) alta quanto il dorso e larga **3–4 cm**.
2. Piegala a metà nel senso della lunghezza, con la stecca.
3. Incollala a cavallo della piega della guardia, **dalla parte esterna** (quella che darà verso la copertina), con un velo sottile di vinilica.
4. Lascia asciugare sotto peso.

Il filo passerà attraverso guardia + brachetta: tre spessori, tiene senza problemi. La guardia si aggancia poi al primo fascicolo con i nodi di catenella in testa e in piede, come due fascicoli qualsiasi.

Ricorda che i fori della guardia devono coincidere con quelli di tutti gli altri fascicoli: usa la stessa dima (capitolo 12).

Con questo metodo lascia `-g 0`: il volante te lo dà già la guardia. Puoi comunque usare `-g 1` se vuoi *anche* un foglio di rispetto nella carta del testo, utile per proteggere il frontespizio.

### 5.3 Guardia incollata a filo

È quello che fanno quasi tutti i libri commerciali. Metti un velo di vinilica su una striscia di **3 mm** lungo il bordo della piega della guardia, la appoggi sulla prima pagina del blocco e metti sotto peso. Nessuna modifica alla cucitura.

Usa un foglio di scarto come maschera per non sporcare oltre i 3 mm. Sappi che è la soluzione più debole delle tre (regge la carta, non il filo) e che irrigidisce la prima apertura, perché quelle due pagine incollate insieme non si aprono più.

### 5.4 Quale scegliere

* Guardia nella stessa carta del testo → **5.1**, con `-g 1`. Zero lavoro extra.
* Guardia in carta diversa, libro medio o pesante → **5.2**.
* Guardia in carta diversa, libro leggero, o non vuoi toccare la cucitura → **5.3**.

Grammatura della guardia: **100–140 g/m²**. Sotto i 100 non regge il tiro dell'apertura, sopra i 160 fa da leva e strappa la prima pagina del testo.

---

## 6. Carta e direzione della fibra

La carta ha una direzione preferenziale delle fibre. Nella legatoria la regola è una sola: **la fibra deve correre parallela al dorso**. Se la sbagli, il libro non si apre bene, le pagine ondulano con l'umidità e — soprattutto — la guardia incollata imbarca il cartone del piatto in modo vistoso.

**Come riconoscerla senza attrezzi:** piega un angolo del foglio nei due sensi senza schiacciare. Nel verso della fibra la piega è docile e liscia; nell'altro oppone resistenza e la piega si increspa. In alternativa inumidisci una striscia: si arriccia lungo l'asse delle fibre.

**Il caso A4 → A5.** Piegando un A4 a metà ottieni un A5 con il dorso lungo 210 mm, quindi ti servirebbe carta **a grana corta** (fibra parallela al lato da 210). La carta da fotocopie comune è a grana lunga: il blocco libro stampato in casa è quasi sempre a fibra sbagliata. È il compromesso standard della legatoria casalinga e a stampa fatta non c'è rimedio.

Le guardie però le compri a parte: lì puoi e devi prendere carta a grana corta, o tagliarla da un formato più grande orientando la fibra nel verso giusto. È la parte dove la fibra conta di più, perché è l'unica che viene incollata a un cartone.

---

## 7. Stampa

Configurazione del modulo di stampa (CUPS o altro):

1. **Fronte/retro**: attiva il Duplex.
2. **Direzione del flip — fondamentale**: imposta **"Capovolgi sul lato corto"** (*Flip on Short Edge*). Con il lato lungo il retro esce sottosopra.
3. **Nessun adattamento alla pagina**: scala 100%, "dimensioni reali", niente "adatta all'area stampabile". Altrimenti i margini calcolati dal programma saltano e il margine di cucitura si mangia il testo.
4. **Menabò di prova**: stampa **solo il primo fascicolo**, cioè le prime `2 × F` pagine del file finale (8 pagine con `-f 4`, 10 con `-f 5`, 6 con `-f 3`). Piegalo e sfoglialo a mano. Se i numeri scorrono senza salti e i capitoli iniziano a destra, l'imposizione è giusta.

Se il margine interno risulta stretto una volta piegato, aumenta *Margine al dorso* nella finestra (`--margine-dorso` da riga di comando). Ricordati che qualche millimetro se lo mangia anche il rifilo finale.

---

## 8. Stampa a tranches e formule

Su un libro grosso, mandare tutto in stampa in una volta è rischioso: inceppamenti, surriscaldamento, e un errore di pescata che scopri 200 fogli dopo. Il programma calcola da solo la tabella degli intervalli (nella finestra sta nel riquadro sotto l'anteprima), pensata per **non spezzare mai un fascicolo a metà**. Le tranche sono di circa 50 pagine: dalla finestra il valore è fisso, da riga di comando si cambia con `-t`. Le formule sono queste.

**Variabili**

* $P_{\text{orig}}$ = pagine del PDF originale
* $F$ = fogli fisici per fascicolo (parametro `-f`)
* $S = 4F$ = pagine logiche per fascicolo
* $n_p$ = pagine bianche di correzione inserite con `-p` (0 se non usato)
* $G$ = fogli di guardia per lato (parametro `-g`, 0 se non usato)
* $N_{\text{fasc/blocco}}$ = quanti fascicoli interi vuoi in ogni tranche

**1. Pagine totali del blocco libro**

$$P_{\text{tot}} = P_{\text{orig}} + n_p + 4G$$

(ogni guardia vale 2 facciate e ce n'è una per lato)

**2. Numero di fascicoli**

$$N_{\text{fasc}} = \left\lceil \frac{P_{\text{tot}}}{S} \right\rceil$$

Le pagine mancanti per arrivare a $N_{\text{fasc}} \times S$ le aggiunge bianche lo script.

**3. Pagine del file finale**

Ogni fascicolo, dopo l'imposizione, occupa $2F$ pagine orizzontali del PDF (un foglio fisico = 2 facciate A4 landscape):

$$T_{\text{finale}} = N_{\text{fasc}} \times 2F$$

**4. Intervalli**

$$N_{\text{pagine}} = N_{\text{fasc/blocco}} \times 2F$$

* Inizio della tranche $k$: $(k-1) \times N_{\text{pagine}} + 1$
* Fine della tranche $k$: $\min\left(k \times N_{\text{pagine}},\ T_{\text{finale}}\right)$

**Esempio** ($P_{\text{orig}} = 749$, `-p 4`, `-g 1`, `-f 4`):

1. $P_{\text{tot}} = 749 + 1 + 4 = 754$
2. $N_{\text{fasc}} = \lceil 754 / 16 \rceil = 48$ fascicoli (14 pagine bianche di riempimento)
3. $T_{\text{finale}} = 48 \times 8 = 384$ pagine nel file `_booklet.pdf`
4. Con 6 fascicoli per tranche: `1-48`, `49-96`, `97-144`, … , `337-384`

Regola pratica: **la pagina di fine di ogni blocco è sempre un multiplo di $2F$** (8 con `-f 4`, 10 con `-f 5`), e la successiva riparte da quella +1.

---

## 9. Logistica post-stampa

Con qualche decina di fascicoli, confondere l'ordine è facilissimo.

**Pila a mattoncino.** Non accumulare tutto in un'unica risma dritta. Quando una tranche finisce, controllala e adagiala sul tavolo **ruotata di 90° rispetto al blocco precedente**. La pila incrociata ti dice sempre dove finisce una tranche e dove inizia l'altra.

**Isolare i fascicoli prima di piegare.** Dentro ogni tranche i fogli escono sequenziali ma vanno divisi in gruppi di `F` fogli:

* prendi i primi `F` fogli usciti: è il fascicolo 1;
* infilaci sopra un ritaglio di carta colorata con scritto a matita `F1`;
* prosegui con `F2`, `F3`…

Fallo **prima** di piegare. Se un gruppo ha un foglio in più o in meno, c'è stata una doppia pescata della stampante e te ne accorgi subito, non sul telaio di cucitura.

**Numera la costola.** Dopo la piegatura, segna a matita leggera il numero del fascicolo sulla piega esterna. Quando i fascicoli sono impilati e tutti uguali, quel numero è l'unica cosa che ti salva.

---

## 10. Piegatura e pressatura

* Piega i `F` fogli del fascicolo **tutti insieme in un colpo solo**, non uno per uno: piegandoli insieme lo scorrimento si distribuisce come deve e le pagine interne finiscono dove devono.
* Allinea con cura il bordo di testa e il bordo davanti prima di segnare la piega.
* Schiaccia la piega con la stecca d'osso o il dorso di un cucchiaio pulito, partendo dal centro verso i due estremi.
* Metti i fascicoli piegati **sotto peso** — un dizionario, o due tavolette con dei morsetti — per qualche ora o tutta la notte. Elimina l'effetto molla della carta e rende foratura e cucitura molto più precise. Su un libro di molti fascicoli è il passaggio che fa la differenza fra un dorso piatto e un dorso a fisarmonica.

---

## 11. Rifilo del taglio davanti e shingling

Mettiamo in chiaro una cosa: **lo scorrimento non lo elimina nessun software**. Se pieghi `F` fogli insieme, quello interno sporge e continuerà a sporgere, perché è geometria della carta. L'unico modo per farlo sparire è tagliare.

### Rifilare fascicolo per fascicolo

Una taglierina a leva da ufficio non può rifilare un blocco cucito da 38 mm: taglia 10–12 fogli per volta e basta. Ma non serve rifilare il blocco: **rifila ogni fascicolo dopo la piegatura e prima della cucitura**. Un fascicolo da 4 fogli piegato sono 8 spessori, ben dentro la portata di qualunque taglierina a leva.

Il risultato geometrico è identico a quello di una cesoia da legatoria, perché lo scorrimento è un fenomeno interno al singolo fascicolo: risolto lì, è risolto ovunque.

1. Lavora su fascicoli **già piegati e già pressati**. Senza pressatura la piega fa molla e la misura ti scappa.
2. Fissa con due morsetti un listello di legno sul piano della taglierina, parallelo alla lama, alla distanza voluta. Serve un **riscontro fisso**: senza, i fascicoli non verranno mai tutti uguali.
3. Appoggia sempre la **piega** contro il listello. Mai il taglio davanti, che è proprio il bordo irregolare che stai eliminando.
4. Togli una striscia sottile, **3–4 mm**: quanto basta a mangiare il gradino con un margine di sicurezza.
5. Controlla ogni cinque o sei fascicoli che il listello non sia slittato.

Testa e piede non si toccano: sono i bordi di taglio originali del foglio A4, già squadrati e identici fra loro.

L'unico vero rischio del metodo è la costanza: se i fascicoli escono di larghezze diverse, il taglio davanti del libro finito risulta ondulato. Meglio dedicare due minuti in più al riscontro che rincorrere il problema dopo.

Attenzione alla portata: 4 fogli piegati sono 8 spessori e vanno bene; 5 fogli sono 10 spessori ed è il limite di molte taglierine domestiche; oltre, o tagli in due riprese o riduci `-f`. Lama affilata e colpo unico e deciso — se la lama striscia, le pagine interne si spostano e il taglio esce a scaletta.

### Lo shingling

Quando rifili, alle pagine interne togli più carta che a quelle esterne (togli anche il gradino). Dopo il taglio, quindi, il loro margine esterno risulta più stretto di qualche decimo. Lo **shingling** anticipa il problema: sposta il contenuto dei fogli più interni verso il dorso, in modo che dopo il rifilo tutti i margini tornino uguali.

Da riga di comando:

```bash
--shingling 0.12      # millimetri di spostamento per ogni foglio verso l'interno
--shingling-auto      # stima teorica: grammatura / 800
```

Nella finestra è il campo *Shingling (mm/foglio)*; il pulsante *Shingling dalla grammatura* ci mette la stima teorica.

**Come misurare il valore giusto**, che è meglio della stima: piega un fascicolo di prova con la tua carta e il tuo `F`, mettilo sotto peso qualche ora, poi misura col calibro di quanto sporge la pagina più interna rispetto alla più esterna. Dividi per `F − 1` e usa quel numero. La stima teorica di solito sottostima, perché non tiene conto di quanto la piega stessa consuma di carta.

Ordine di grandezza: 4 fogli di carta da 80 g/m² fanno 0,3 mm in tutto. Se non rifili e il gradino non ti dà fastidio, lo shingling puoi ignorarlo tranquillamente — è una rifinitura, non una necessità.

### Se non hai come rifilare

Riduci i fogli per fascicolo. Con `-f 2` lo scorrimento è un decimo di millimetro, invisibile a occhio nudo. Paghi con il doppio dei fascicoli e il doppio delle cuciture, ma il taglio davanti viene pulito senza toccare una lama.

---

## 12. Foratura

I fori devono essere **identici su tutti i fascicoli**, altrimenti il dorso viene storto. Non misurarli fascicolo per fascicolo: fatti una **dima**.

### Quanti fori

**Il numero dei fori deve essere pari.** Non è una superstizione: il filo entra nel fascicolo dal primo foro e, alternando dentro e fuori, può uscirne dall'ultimo solo se i fori sono in numero pari. Con un numero dispari ti ritrovi il filo dentro il fascicolo quando dovresti passare al successivo.

Nella cucitura su nastri il conto torna da solo:

```
fori = 2 (catenella, testa e piede) + 2 × numero di nastri
```

Per un A5 vanno bene **3 nastri → 8 fori**. Su un libro molto spesso o pesante, 4 nastri → 10 fori.

### Dove

* I due fori di catenella a **15–20 mm** dalla testa e dal piede.
* Gli altri a coppie, uno per lato di ogni nastro, distanziati di quanto è largo il nastro (in genere 10–12 mm) più un paio di millimetri.
* Distribuisci i nastri in modo abbastanza uniforme sull'altezza restante, tenendo il primo e l'ultimo un po' più lontani dal centro che dagli estremi.

### Come

1. Prepara la dima: una striscia di cartoncino alta quanto il dorso, con le posizioni segnate e tacche a matita.
2. Apri il fascicolo a metà e appoggialo su un **cavalletto di foratura** (due tavolette a V, o anche solo un vecchio catalogo aperto).
3. Appoggia la dima nell'interno della piega, tenendo la testa del fascicolo contro un riscontro fisso — sempre lo stesso lato, per tutti i fascicoli.
4. Fora **dall'interno verso l'esterno** con un punteruolo sottile, tenendolo perpendicolare alla piega. Fori grandi = filo lasco e dorso gonfio: bucare il minimo indispensabile.

---

## 13. Cucitura

Cucitura su nastri, telaio o no. Lo schema è sempre lo stesso: entri nel primo foro, esci dal secondo passando **sopra** il nastro, rientri dal terzo, e così via; a fine fascicolo fai il nodo di catenella agganciando il fascicolo precedente, poi appoggi il fascicolo successivo e riparti in senso inverso.

Qualche accortezza per un libro da molti fascicoli:

* **Filo proporzionato alla taglia.** Ogni fascicolo aggiunge sul dorso uno spessore di filo, circa 0,3–0,5 mm per fascicolo. Su un libro da dieci o quindici fascicoli sono già 3–8 mm, e con fascicoli sottili si vedono; da quaranta in su, con un lino 18/3 (0,55–0,6 mm) il dorso cresce di più di venti millimetri rispetto al taglio davanti e il libro diventa a cuneo. Regolati con la tabella del capitolo 2 e con il paragrafo che segue.
* **Non tirare troppo.** Il filo va teso quel tanto che basta a chiudere la piega, tirando lungo la direzione del dorso e non verso l'esterno, altrimenti strappi i fori.
* **Cera d'api.** Passa il filo sulla cera: scorre meglio, non si annoda su sé stesso e tiene meglio il nodo. Ma la cera indurisce il filo, che si schiaccia meno nel fascicolo e rigonfia di più: poca, una o due passate.
* **Batti il dorso.** Ogni 8–10 fascicoli, comprimi la pila e controlla che il dorso resti piano. A cucitura finita, il dorso va battuto leggermente con un martello a testa piatta per distribuire il rigonfiamento, prima di incollarlo.
* **La guardia è un fascicolo.** Se hai scelto il metodo 5.2, la guardia con brachetta si cuce esattamente come tutti gli altri: primo elemento della sequenza in testa, ultimo in coda.

### Quando il filo finisce: il nodo da tessitore

Su un libro di molti fascicoli il filo si esaurisce prima della fine, ed è normale: meglio tagliare un pezzo comodo da lavorare (60–80 cm) e cambiarlo spesso che lottare con un filo lunghissimo che si attorciglia e si consuma sfregando nei fori.

Il nodo giusto è il **nodo da tessitore** (*weaver's knot*, lo stesso che in marina si chiama *nodo piano incrociato* o *sheet bend*), non un nodo qualsiasi: fatto bene resta piccolo e piatto, così non fa da tappo quando il filo passa nel foro successivo, e non scivola anche se i due fili hanno spessori leggermente diversi.

**Quando cambiarlo.** Non aspettare che il filo finisca a metà di un passaggio: quando restano 10–15 cm, esci dal fascicolo che stai cucendo, verso l'esterno, e fai il cambio lì. Il nodo resterà nascosto nella piega del fascicolo, non in vista sul dorso.

**Il nodo, passo per passo:**

1. Con il filo **vecchio** (quello che sta per finire) fai un piccolo cappio, tenendolo con due dita.
2. Fai passare il filo **nuovo** attraverso il cappio, da dietro in avanti.
3. Con il nuovo filo fai a sua volta un secondo cappio, che passa *sopra* la coda del primo.
4. Tieni fermo questo secondo cappio e tira i due capi del filo nuovo in direzioni opposte: il cappio si stringe attorno al filo vecchio, bloccandolo. Senti un piccolo scatto quando il filo vecchio è agganciato per bene.
5. Regola la posizione del nodo facendolo scorrere lungo il filo prima di stringerlo del tutto: portalo il più vicino possibile all'ultimo foro cucito, così il tratto di filo doppio che ne segue è cortissimo.
6. Prova a tirare piano il filo nuovo: se il nodo tiene, continua a cucire da dove avevi lasciato; se scivola via, rifallo.

Se il nodo non ti convince o non riesci a impratichirti, un doppio nodo piano stretto bene funziona quasi altrettanto: è solo un po' più ingombrante, e in un punto nascosto nella piega non si nota.

### Quanto rigonfia il filo

Il filo ingrossa il dorso rispetto al taglio davanti: è il *rigonfiamento* del capitolo 1. In prima approssimazione è **lo spessore del filo per il numero di fascicoli**, ed è per questo che molti rilegatori lo visualizzano avvolgendo il filo attorno a una matita tante volte quanti sono i fascicoli. Una formula esatta non esiste: il rigonfiamento dipende da una decina di fattori, quindi il programma dà un intervallo e non un valore.

**Prova della penna.** È il modo più sicuro per misurarlo con il *tuo* filo, prima di cucire. Il filo nei fascicoli si accumula sul dorso; avvolgendolo attorno a una penna lo accumuli allo stesso modo, ma in un punto dove puoi misurarlo:

1. Conta i fascicoli del libro (il programma li mostra nel riepilogo). Diciamo 40.
2. Avvolgi il filo attorno alla penna 40 volte, con le spire una accanto all'altra.
3. Spingile l'una contro l'altra, senza schiacciare forte, e misura con un righello la larghezza della fascia di filo. Diciamo 16 mm.
4. Dividi per i giri: 16 ÷ 40 = **0,4 mm per fascicolo**. È il numero da dare al programma.

Misura solo il filo, non la carta: è una stima, ma parte da un dato reale del tuo filo, cerato o no, e di come lo tiri. Il valore va nel campo *Filo per fascicolo (mm)* della scheda Imposizione, che sotto il campo scrive da solo quanti giri fare per il tuo libro, oppure in `--filo` da riga di comando. Conviene fare tutti i giri: con pochi, l'errore di misura pesa di più (mezzo millimetro su 5 giri sono 0,1 mm per fascicolo).

**Il filo.** Spessori approssimativi dei lini di uso comune, dai cataloghi di due fornitori (il filo che il produttore vende già cerato è più grosso):

| Filo | Spessore |
| --- | --- |
| 12/3 | circa 1 mm |
| 18/3 | 0,55–0,6 mm |
| 25/3 | circa 0,5 mm (il più usato in legatoria a mano) |
| 30/3 | 0,42–0,45 mm |
| 35/3 | 0,38–0,4 mm |

**Il valore del programma: 0,3–0,5 mm per fascicolo.** Il massimo è il 25/3; il minimo è un filo fine che la battitura schiaccia. La stima delle misure per la copertina usa il valore di mezzo, 0,4 mm, cioè un 30/3–35/3: il filo che il capitolo 2 consiglia per i libri grossi, dove la stima conta di più, e che Hollander's indica per i blocchi grandi. Con un 18/3 o con un filo molto cerato si va sopra il massimo, fino a 0,6 mm per fascicolo. Se hai misurato il tuo filo, indicalo (vedi sopra) e il programma usa quello al posto dell'intervallo; per cambiare l'intervallo predefinito basta una riga ([README](../README.md#per-chi-vuole-modificare-il-codice)).

**Quanto pesa, in percentuale.** Quello che conta è il rapporto fra il filo e la carta del fascicolo. Con carta da 80 g/m² (0,1 mm a foglio), un fascicolo di `F` fogli ha `2F` foglie e quindi `0,2 × F` mm di carta:

| Fogli per fascicolo | Carta per fascicolo | Filo 0,3 mm | Filo 0,4 mm | Filo 0,5 mm |
| --- | --- | --- | --- | --- |
| 1 | 0,2 mm | 150 % | 200 % | 250 % |
| 2 | 0,4 mm | 75 % | 100 % | 125 % |
| 3 | 0,6 mm | 50 % | 67 % | 83 % |
| 4 | 0,8 mm | 38 % | 50 % | 63 % |
| 5 | 1,0 mm | 30 % | 40 % | 50 % |
| 6 | 1,2 mm | 25 % | 33 % | 42 % |

Più fogli per fascicolo, meno rigonfiamento in proporzione: è uno dei motivi per cui il capitolo 3 indica 4–5 fogli per la carta da 80 g/m².

**Quanto va bene.** Per un dorso arrotondato la regola che molti rilegatori seguono è che il blocco cucito risulti circa il 30 % più spesso del taglio davanti; per il tradizionale arrotondamento fra un quarto e un terzo di cerchio si parla di un rigonfiamento misurato del 15–25 %, e con molti fascicoli sottili si arriva anche oltre il 50 % lavorando sulla forma delle spalle. Un dorso piatto, invece, vorrebbe un rigonfiamento nullo. Ne segue che un libro casalingo su carta da 80 g e fascicoli da 4–5 fogli sta quasi sempre **sopra** il 30 %: è normale. Si contiene con un filo sottile (30/3–35/3, senza cera in eccesso), pressando i fascicoli piegati prima di cucirli (capitolo 10) e arrotondando il dorso (capitolo 16.2).

**Da cosa dipende ancora.** Filo più grosso, più duro o cerato: più rigonfiamento. Carta più spessa o più morbida, più fogli per fascicolo: meno. Con la cucitura su nastri il filo non si sovrappone e il rigonfiamento è minimo; sui cordoncini un po' più alto. Battere i fascicoli e consolidarli mentre cuci lo riduce, e una cucitura più tesa dà un blocco più sottile prima della pressatura; ma tirare troppo deforma il dorso e strappa i fori. La stessa cucitura fatta da due persone può dare risultati diversi. Per questo la misura vera, sul blocco cucito, resta l'unica che conta.

**Perché non "più il 10 %".** Nei calcolatori di dorso dei tipografi, per la brossura cucita, si trova la regola di aggiungere un 10 % per il refe. È una regola generale, che non guarda a quanto sono spessi i fascicoli, e più fogli per fascicolo significa meno rigonfiamento in proporzione. Con i fascicoli da 4 fogli di una legatura casalinga il rapporto è quello della tabella qui sopra, molto più alto.

**Fonti** (consultate a settembre 2026; i numeri sono una sintesi, non una citazione):

* Jeff Peachey, *A Guide to Swell*, 2015: <https://jeffpeachey.com/2015/11/24/a-guide-to-swell/>. I fattori che governano il rigonfiamento; dice esplicitamente che una formula non esiste.
* Misty McIntosh (Paper Craft Panda), *Easy Way to Estimate Thread Thickness for Bookbinding*: <https://blog.papercraftpanda.com/easy-way-to-estimate-thread-thickness-for-bookbinding/>. La regola del 30 % e la prova della penna, che l'autrice attribuisce a Peter Geraty.
* Tom Conroy, *The Movement of the Book Spine*, Book and Paper Group Annual 6, 1987: <https://cool.culturalheritage.org/coolaic/sg/bpg/annual/v06/bp06-01.html>. Il 15–25 % per il tradizionale arrotondamento; il commento sopra il 50 % è dello stesso autore nella discussione dell'articolo di Peachey.
* Hollander's, schede dei fili di lino 18/3, 25/3, 30/3 e 35/3: <https://hollanders.com/collections/linen-threads-unwaxed>, e John Neal Books, schede dei fili Londonderry 18/3 e 30/3: <https://www.johnnealbooks.com/product/londonberry-thread-30-3>. Gli spessori nominali.
* Diatecx, *Dorso libro, com'è fatto e come si calcola il suo spessore*: <https://www.diatecx.com/dorso-libro-com-e-fatto-e-come-si-calcola-il-suo-spessore/>. La regola del 10 % per il refe.
* *Swell (bookbinding)*, Wikipedia: <https://en.wikipedia.org/wiki/Swell_(bookbinding)>. Il dorso piatto che vorrebbe rigonfiamento nullo.

---

## 14. Colle

* **Vinilica (PVA)**: presa rapida, elastica, ottima per il dorso e per la brachetta. Ma tira: sulla carta sottile fa arricciare.
* **Colla d'amido o metilcellulosa**: lenta, dà tempo di posizionare, imbarca molto meno. È quella giusta per **incollare la guardia al cartone del piatto**.
* **Miscela amido + vinilica** (indicativamente metà e metà): il compromesso più usato per i risguardi.

Per incollare il risguardo al piatto: stendi la colla sulla guardia (non sul cartone), appoggia, liscia dal centro verso l'esterno con la stecca sopra un foglio di protezione, infila un foglio di **carta oleata** fra la guardia incollata e il resto del libro, chiudi e metti sotto peso per una notte. Se usi vinilica pura su carta pesante, il piatto si incurva verso l'interno quasi sempre.

---

## 15. La brossura

Brossura significa copertina flessibile, di cartoncino, incollata al dorso del blocco. Non è una sola tecnica: ce ne sono due, e la differenza fra le due è enorme.

### 15.1 Fresata o cucita

Nella **brossura fresata** — quella dei tascabili da edicola — la piega dei fascicoli viene tagliata via, le pagine restano singole e sono tenute insieme soltanto dalla colla. È rapida, ma è anche il motivo per cui certi libri economici perdono le pagine.

Nella **brossura cucita** i fascicoli restano interi e cuciti su nastri, esattamente come in una legatura rigida: cambia soltanto che al posto dei cartoni c'è un cartoncino. È incomparabilmente più solida, si apre meglio, e soprattutto **riusa tutto il lavoro fatto finora**: stessa imposizione, stessi fascicoli, stessa piegatura, stessa foratura, stessa cucitura, stessa collatura del dorso. Ti fermi dopo la cucitura e monti una copertina flessibile invece di una cassa.

È questa la brossura che ha senso fare in casa. La fresata la si fa solo quando si parte da fogli sciolti, tipicamente perché il documento non era impaginato a fascicoli.

### 15.2 La copertina

Cartoncino da **250–300 g/m²**, fibra parallela al dorso come sempre.

| Misura | Formula | Esempio (blocco 148 × 210, dorso 12 mm) |
| --- | --- | --- |
| Altezza | `H + 2u` | 216 mm |
| Larghezza | `2 × (L + u + h) + D` | 328 mm |

dove `H` e `L` sono altezza e larghezza del blocco, `D` lo spessore del dorso, `u` l'unghia e `h` la larghezza delle cerniere francesi (paragrafo 15.3). Le cerniere vanno contate: sono materiale in più, non ricavato dai piatti, e dimenticarle lascia la copertina corta di `h` per lato sul taglio davanti.

Sull'unghia c'è una scelta da fare. La brossura industriale ha la copertina **a filo** con le pagine, ma per ottenerla bisogna rifilare i tre lati a libro finito, cosa che a mano non è alla portata. La soluzione pratica è dichiarare l'intenzione: lascia deliberatamente **2–3 mm di unghia** su testa, piede e taglio davanti, come in una copertina rigida. Sembra una scelta, mentre una copertina "quasi a filo" sembra un errore.

### 15.3 Le cordonature

È il dettaglio che decide se il libro si apre o si crepa, e viene saltato quasi sempre.

Sul lato interno del cartoncino, incidi con la stecca e una riga **quattro solchi verticali**: due che delimitano il dorso, e due a **6–8 mm** all'esterno dei primi. Le due coppie formano due cerniere francesi, cioè due strisce di cartoncino larghe 6–8 mm che fanno da giunto fra dorso e piatti.

Senza cordonature il cartoncino si piega dove capita — di solito appena fuori dal dorso, a caso sui due lati — e alla terza apertura il dorso si sbriciola.

Incidi con la stecca, senza tagliare: devi schiacciare le fibre, non reciderle. Se il cartoncino è oltre i 300 g/m², passa la punta smussata due volte con decisione.

### 15.4 Montaggio

1. Blocco cucito, dorso collato e asciutto, garza applicata (paragrafi 16.1 e 16.4).
2. Stendi la vinilica sul dorso del blocco e sulla fascia centrale del cartoncino, fra le due cordonature interne.
3. Appoggia il blocco, centrandolo in altezza per ottenere unghie uguali a testa e piede.
4. Chiudi i due piatti **partendo dal dorso**, e stringi le due cerniere francesi con le dita lungo tutta l'altezza.
5. Metti in morsa o sotto peso, con due bacchette sottili appoggiate nelle cordonature, per una notte.

Le alette dei risvolti, se le vuoi, si aggiungono alla larghezza: 60–90 mm per lato, con la loro cordonatura.

### 15.5 La brossura fresata, quando serve

Se parti da fogli sciolti e non da fascicoli:

1. Stringi il blocco fra due tavolette con il dorso che sporge di 3–4 mm.
2. Taglia via la piega, se c'è, con cutter o sega a denti fini.
3. **Incidi sul dorso intagli trasversali profondi 2 mm ogni 2–3 cm.** È il passaggio che quasi tutti saltano e che fa la differenza fra un libro e un mazzo di fogli: danno alla colla qualcosa a cui aggrapparsi.
4. Vinilica in due mani sottili, garza sopra, e ad asciugare in morsa.

Non usare la colla a caldo della pistola: diventa fragile con il freddo e si stacca a blocchi interi.

### 15.6 La brossura svizzera

Variante che merita su un libro da consultazione: il blocco è incollato **soltanto al piatto posteriore**, e il dorso resta libero. Il libro si apre completamente piatto, resta aperto da solo, e mostra la cucitura sul dorso.

Si fa esattamente come la cucita, ma la copertina è più stretta — il dorso non c'è — e la colla va solo sulla guardia posteriore. Richiede una cucitura ordinata, perché resta in vista.

---

## 16. La copertina rigida

La copertina rigida si costruisce a parte, come una scatola aperta fatta di due cartoni e un dorso tenuti insieme dal rivestimento, e solo alla fine ci si incolla dentro il blocco. In gergo si chiama **cassa**, e l'operazione finale **incassatura**.

Le misure della cassa non si calcolano dal PDF: si misurano sul blocco finito. Quindi prima si prepara il dorso, poi si misura, poi si taglia.

### In due parole: la sequenza

1. Colli il dorso del blocco cucito.
2. Aspetti che la colla diventi gommosa, non secca.
3. **Arrotondi** il dorso col martello. Questa falla.
4. **Non** fai l'indorsatura, cioè le spalle: richiede una pressa e senza fai danni. Saltala.
5. Incolli garza e carta di rinforzo sul dorso.
6. Fai il tubo del dorso cavo.
7. Misuri il blocco e costruisci la cassa.
8. Incassi il libro nella cassa.

Attenzione a non confondere i punti 3 e 4: sono due operazioni diverse che si fanno tutte e due col martello. L'arrotondatura dà al dorso la curva convessa e non richiede attrezzi; l'indorsatura ripiega i fascicoli esterni formando due spalle e richiede una pressa. Qui facciamo solo la prima.

### 16.1 Collatura del dorso

A cucitura finita, comprimi il blocco fra due tavolette con il dorso che sporge di un paio di millimetri e stendi sul dorso uno strato sottile di vinilica, facendola penetrare fra i fascicoli senza annegarli. Prima di incollare, batti leggermente il blocco a squadro sul tavolo: testa e dorso devono essere perfettamente allineati, perché quello che sbagli qui non si recupera più.

### 16.2 Arrotondatura

Serve a dare al dorso una curva convessa e al taglio davanti la corrispondente concavità.

Quanto conta dipende dalla taglia. Sotto i 15 mm di dorso puoi saltarla senza rimpianti. Fra i 15 e i 25 mm è facoltativa e migliora l'estetica. Oltre i 25 mm diventa necessaria: un blocco spesso, lasciato piatto, col tempo si incurva al contrario e si apre a ventaglio sul taglio davanti, perché il rigonfiamento del filo spinge in quella direzione.

**Che martello.** Quello giusto si chiama martello da legatore: testa da 700 g – 1 kg, faccia larga 4–5 cm, leggermente bombata e lucida. In mancanza va bene un **martello da carpentiere con la faccia liscia e lucida**, da 400–500 g. È vietata la faccia zigrinata a quadretti di certi martelli da muratore: stampa il reticolo sulla carta al primo colpo. Se la faccia che hai è piccola o segnata, appoggia sul dorso un ritaglio di pelle sottile o due strati di cartoncino liscio e batti su quello.

Controintuitivo ma vero: **un martello più pesante fa meno danni**, perché ti permette di dare colpi leggeri. Con un martelletto da 200 g finisci per picchiare forte e ammacchi. Il mazzuolo di gomma non va bene: rimbalza e non trasmette il movimento laterale che serve.

**Quando.** La colla del dorso deve essere **gommosa, non vetrosa**: con la vinilica sono 30–60 minuti dalla stesura, quando premendo col dito il dorso cede e riprende. Se ti sei perso il momento, passa un velo d'acqua col pennello sul dorso e aspetta dieci minuti che si riammorbidisca.

**Il gesto.** La curva la fa la mano; il martello serve solo a convincere i fascicoli a scorrere uno sull'altro di un pelo.

1. Appoggia il blocco piatto sul tavolo, con il dorso verso di te e sporgente di un paio di centimetri dal bordo del piano.
2. Con la sinistra afferra il taglio davanti e **tira leggermente verso di te**, tenendo il blocco compresso. È questa mano che decide la curva.
3. Con la destra dai colpi **radenti**, quasi di sfregamento, sullo **spigolo superiore del dorso** — non al centro, sullo spigolo — inclinando il martello di una trentina di gradi, così che ogni colpo spinga di lato i fascicoli più esterni.
4. Percorri tutta la lunghezza del dorso, dalla testa al piede. Poi gira il blocco sottosopra e fai lo stesso sull'altro spigolo.
5. Alterna le due facce molte volte, poco per volta: sono decine di passate leggere, non dieci colpi decisi.

Ogni tanto fermati e guarda il dorso di infilata: deve venire un arco regolare, all'incirca un terzo di cerchio. Se un tratto resta piatto, lavora solo lì.

### 16.3 Formazione delle cerniere (indorsatura) — opzionale

Serve a ripiegare verso l'esterno i fascicoli più esterni formando due spalle, alte quanto è spesso il cartone dei piatti, dentro cui poi si alloggiano i piatti stessi.

Il blocco va stretto fra due tavolette arretrate rispetto al dorso di quanto è spesso il cartone, e i fascicoli esterni si martellano fino a farli ripiegare. **Richiede una pressa che tenga davvero**, perché la spinta è forte: con due tavolette e quattro morsetti si può fare, ma il blocco tende a scappare e il rischio concreto è ritrovarsi le spalle storte e i fascicoli sfalsati.

Per un primo libro il consiglio è chiaro: **arrotonda e salta l'indorsatura**, poi fai la copertina con il dorso cavo (paragrafo 16.7). Ottieni comunque il dorso convesso e il taglio davanti concavo, che è il grosso del beneficio. La pressa da indorsatura è il primo attrezzo da comprare se poi la cosa ti prende.

### 16.4 Rinforzo del dorso

Incolla sul dorso una striscia di garza o tarlatana che sbordi di 2–3 cm su ciascun lato, sopra le guardie. Poi, se li vuoi, i capitelli (paragrafo 16.5). Infine una striscia di carta robusta larga esattamente quanto il dorso, che blocca tutto.

### 16.5 I capitelli

Sono le due strisce di tessuto, spesso a righe colorate, che si vedono a testa e a piede del dorso nei libri cartonati. In inglese *headbands*.

**A cosa servono.** Oggi quasi solo a riempire e a decorare: nascondono il vuoto che resterebbe fra il dorso del blocco e il cartoncino della copertina, che con il dorso cavo è particolarmente visibile guardando il libro dall'alto. Strutturalmente non reggono niente, ma un dorso senza capitelli sembra incompiuto. Sono due centimetri di nastro e trenta secondi di lavoro.

Nell'originale invece erano strutturali: un cordoncino d'anima cucito al blocco, che rinforzava le estremità del dorso — il punto dove il libro si rompe per primo, perché è lì che si infila il dito per tirarlo giù dallo scaffale.

#### Il capitello a nastro

È la versione industriale, e per un libro fatto in casa va benissimo. È una fettuccia con un bordino ingrossato lungo un margine, venduta a metro in cartoleria o nei negozi di legatoria.

1. Taglia il nastro **esattamente largo quanto il dorso**, né più né meno.
2. Stendi un velo di vinilica sull'estremità del dorso del blocco.
3. Appoggialo con il bordino verso l'esterno, in modo che sporga di **circa 1 mm** oltre il taglio di testa delle pagine. Non di più: un capitello che sporge troppo fa da spessore e tiene la copertina sollevata.
4. Ripeti al piede.
5. La striscia di carta di rinforzo, incollata sopra, li blocca definitivamente.

In mancanza del nastro apposito, una strisciolina di tela da legatoria o di nastro di cotone piegato copre comunque il vuoto: non avrai il bordino, ma l'effetto è decoroso.

#### Il capitello cucito a mano

È l'alternativa artigianale, ed è una delle poche operazioni di legatoria che danno un piacere sproporzionato rispetto alla difficoltà. Si impara in un pomeriggio.

A differenza del nastro incollato, questo è **cucito dentro i fascicoli**, quindi lavora davvero: quando tiri il libro dallo scaffale prendendolo per il bordo del dorso, la trazione la prende il capitello e non la carta.

**Materiali.**

* Un'**anima**: cordoncino di canapa, spago di lino, o una strisciolina di pelle sottile arrotolata su se stessa. Deve essere rigida quanto basta a tenere la forma, spessa 1–2 mm.
* Due **fili** di seta o cotone da ricamo, sottili, in due colori che stiano bene insieme. Il classico è rosso e bianco, oppure verde e oro.
* Un ago sottile e curvo, se ce l'hai; dritto va bene lo stesso.

**Procedimento.**

1. Appoggia l'anima sul dorso, appena sopra il taglio di testa, e tienila ferma con la sinistra.
2. Con l'ago passa il filo **dentro il primo fascicolo**, esci dal dorso sotto l'anima, scavalcala e riporta l'ago nello stesso punto. Questo primo giro **ancora l'anima al blocco**.
3. Avvolgi il filo attorno all'anima, giro dopo giro, stringendo ogni giro contro il precedente come si avvolge un filo su una bobina.
4. Ogni **cinque o sei giri**, ripeti l'ancoraggio infilando l'ago dentro un fascicolo. È questo che rende il capitello solido invece che decorativo.
5. I due colori si alternano: porti avanti un filo per un tratto, poi lo lasci pendere e prendi l'altro, scambiandoli. Ne nasce il motivo a righe, quello che l'industria ha poi copiato stampandolo su nastro.
6. Arrivato in fondo, chiudi con un paio di giri fermi e un nodo nascosto sotto l'anima.
7. Ripeti al piede.

**Due avvertenze.** Fallo dopo la garza e prima della carta di rinforzo, come il nastro. E la prima volta non provarlo sul libro buono: prendi tre o quattro fascicoli di scarto, cucili grossolanamente e fai due o tre capitelli su quelli. In un pomeriggio ti viene la mano, e il quarto è già presentabile.

### 16.6 Le tre misure e le formule

Misura sul blocco **rifilato, cucito, collato e arrotondato**:

* `H` = altezza del blocco
* `L` = larghezza di **una pagina**, dal taglio davanti alla piega, dorso escluso (dopo il rifilo del taglio davanti: se hai tolto 3 mm, da 148 sei a 145).
* `D` = lunghezza dell'**arco** del dorso, non la sua corda. Se il dorso è arrotondato non usare il calibro: appoggia una strisciolina di carta sulla curva, falla aderire e segna dove arriva.

  L'arco va preso **esattamente da spigolo a spigolo**, cioè dai due punti in cui il dorso curvo incontra le facce piane del blocco. È l'errore che si fa più facilmente: se la strisciolina scavalla di un paio di millimetri per lato, poi ci sommi i due spessori di cartone e i 2 mm del tubo, e ti ritrovi un cartoncino largo 4–5 mm di troppo, che resta lasco e non aderisce alla curva. Nel dubbio taglialo **1–2 mm più stretto** del calcolo: un dorso leggermente stretto tira le cerniere e aderisce meglio, uno largo resta sempre un po' staccato.

Poi:

| Pezzo | Altezza | Larghezza |
| --- | --- | --- |
| Piatti (×2) | `H + 2u` | `L + u − g` |
| Dorso (cartoncino) | `H + 2u` | `D + 2c` (`+ 2 mm` se fai il dorso cavo) |
| Rivestimento | tutto l'insieme disteso, `+ 15 mm` per lato | idem |

dove:

* `u` = **unghia**, la sporgenza del cartone oltre il blocco su testa, piede e taglio davanti. **3 mm** è lo standard; 2 mm su libri piccoli, 4–5 mm su formati grandi.
* `g` = **gola**, lo spazio vuoto fra piatto e dorso che fa da cerniera. Circa **il doppio dello spessore del cartone**, con un minimo di 6 mm. Troppo stretta e il libro si apre a fatica; troppo larga e la cerniera sbadiglia. **Se non hai fatto l'indorsatura**, scendi a circa 1,5 volte lo spessore del cartone, con un minimo di 4 mm: non c'è la spalla a riempire la gola, e una gola larga resterebbe un vuoto.
* `c` = spessore del cartone dei piatti.

**Esempio** (blocco A5 spesso 48 mm: `H` = 210, `L` = 145, `D` = 48, cartone da 3 mm, unghia 3 mm, gola 5 mm perché senza indorsatura, dorso cavo):

* piatti: `216 × 143` mm
* dorso: `216 × 56` mm
* rivestimento: l'insieme disteso misura `216 × (143 + 5 + 56 + 5 + 143) = 216 × 352`, quindi taglia **246 × 382** mm

Per ottenere esattamente questi numeri dal programma imposta unghia, cartone e gola a mano (campi della scheda Copertina, oppure `bbt copertina -H 210 -L 145 -D 48 -u 3 -c 3 -g 5`). Lasciandoli vuoti, per un dorso di 48 mm il programma sceglie unghia 3,5 mm e gola 4,5 mm, e i pezzi vengono `217 × 144`, `217 × 56` e **247 × 383** mm: un millimetro di differenza, che conta solo se hai già tagliato il cartone.

**Stimare le misure prima di cucire.** La scheda Imposizione può ricavare le tre misure dal PDF (*Porta le misure alla copertina*): `H` è il lato corto del foglio di stampa, `L` è metà del lato lungo meno il rifilo previsto (3 mm salvo diversa indicazione), `D` è lo spessore stimato della carta più il filo, che il programma conta a 0,3–0,5 mm per fascicolo (capitolo 13): la scheda Copertina parte dal valore di mezzo e nell'avviso ti dice fra quali estremi può cadere. Se hai misurato il tuo filo con la prova della penna, indicalo nel campo *Filo per fascicolo* della scheda Imposizione: il dorso viene calcolato con quello. Sono stime per ordinare i materiali, non misure: il dorso in particolare dipende da quanto tiri il filo e da come batti il blocco. **Prima di tagliare il cartone sostituisci sempre le tre misure con quelle vere del blocco finito.**

### 16.7 Il dorso cavo

Nel dorso cavo il cartoncino della copertina **non tocca il dorso del libro**: fra i due c'è un tubo di carta che si incolla da una parte al blocco e dall'altra alla cassa. Quando apri il libro, il blocco flette e il tubo si apre a triangolo, mentre il dorso della copertina resta liscio e rigido.

È la soluzione giusta ogni volta che non hai indorsato, per tre motivi: perdona le imprecisioni della cerniera quando non hai indorsato, lascia il libro aperto molto meglio, e il dorso della copertina non si deforma con l'uso.

**Costruzione** (il classico "uno incollato, due liberi"):

Si parte da **una sola striscia** di carta, non da tre: è una striscia larga tre volte il dorso, che si piega in tre come una lettera.

1. Taglia una striscia di carta kraft robusta (100–120 g/m²), alta quanto il dorso del blocco e larga **3 volte `D`**. Fibra parallela al dorso. Con un dorso da 48 mm: una striscia di 144 × 210 mm.
2. Piegala in tre pannelli uguali, `A`, `B`, `C`, aiutandoti con la stecca e una riga.
3. Incolla il pannello `A` sul dorso del blocco, sopra la garza e la carta di rinforzo.
4. Ribalta `B` sopra `A` **senza mettere colla**. È il punto che conta: `B` deve restare libero di sollevarsi da `A`.
5. Incolla `C` sopra `B`. Ora `B`+`C` formano la parete esterna del tubo, a doppio spessore.
6. Lascia asciugare a libro chiuso, con il tubo ben aderente.

Il risultato è un tubo schiacciato: parete interna `A` incollata al libro, parete esterna `B`+`C` libera, unite solo lungo le due pieghe ai due spigoli del dorso. La copertina si incollerà alla faccia esterna del tubo, **non** al dorso del libro. Aprendo il libro, il blocco flette portandosi dietro `A`, mentre `B`+`C` resta con la copertina, e fra i due si apre un vuoto triangolare: è quello che permette al libro di aprirsi bene lasciando il dorso della copertina liscio e dritto.

L'alternativa è il **dorso incollato**, cioè la copertina attaccata direttamente al dorso del libro senza tubo. Si fa prima, e sotto i 15 mm di dorso è una scelta legittima; più il dorso è spesso, più la copertina si increspa a ogni apertura e il libro fatica a stare aperto.

In fase di incassatura la colla va sulla faccia esterna del tubo e sul cartoncino del dorso della cassa. Il cartoncino, prima, va **precurvato**: vedi il paragrafo 16.9, è il passaggio che decide se il dorso aderirà alla curva del libro. Con il dorso cavo puoi permetterti un cartoncino un po' più rigido, 0,5 mm, perché non deve flettere insieme al libro.

### 16.8 Tagliare i pezzi

* **Cartone dei piatti**: da legatoria, grigio, **2,5–3 mm** per un libro di questo peso. Fibra parallela al dorso.
* Taglia il primo piatto, verificalo sul blocco, e usalo come **dima per il secondo**. Se i due piatti non sono identici, le unghie risultano diverse fra fronte e retro e si vede subito.
* **Dorso**: cartoncino flessibile da 0,3–0,5 mm, mai cartone rigido.
* **Rivestimento**: tela da legatoria o carta pesante, fibra parallela al dorso. Angoli tagliati a 45° lasciando oltre lo spigolo del cartone circa **una volta e mezza lo spessore del cartone**: se tagli più vicino, l'angolo resta scoperto.

### 16.9 Precurvare il cartoncino del dorso

Se hai arrotondato il dorso del blocco, questo passaggio non è facoltativo. Un cartoncino piatto incollato su una superficie curva **non si dispone in arco**: fa una specie di "U", con i due tratti quasi dritti vicino alle gole e tutta la curvatura concentrata al centro. Il raggio che ne risulta è più grande di quello del libro e il suo centro cade più in basso: il dorso non aderisce, e schiacciarlo sotto un peso non serve, perché appena togli il peso torna dov'era.

Il sintomo, a libro finito, è esattamente questo: guardando il libro dalla testa, la curva della copertina e quella del blocco non sono concentriche.

**Tre modi per precurvare**, dal più efficace.

1. **Arrotolalo stretto.** Avvolgi il cartoncino attorno a un tubo di diametro **più piccolo** di quello del dorso — il manico di un cucchiaio di legno, una matita grossa, un tubo da 2–3 cm — fermalo con un elastico e lascialo lì qualche minuto. Rilasciandolo si riapre e si assesta su un raggio più grande di quello su cui l'hai arrotolato: per questo devi esagerare in curvatura, come quando arricci il nastro di un pacco regalo.
2. **Tiralo contro uno spigolo.** Appoggia il cartoncino sullo spigolo del tavolo e tiralo verso il basso premendo col pollice, facendolo scorrere. Ripeti qualche volta e su tutta la larghezza, non solo al centro.
3. **Inumidiscilo appena** sul lato che diventerà interno, con una spugnetta ben strizzata, poi arrotolalo e lascialo **asciugare arrotolato**. Asciugandosi la carta memorizza la forma, e la curva diventa permanente.

**La verifica, prima di incollare.** Appoggia il cartoncino precurvato sul dorso del blocco, senza colla. Deve aderire dappertutto per gravità, senza che tu prema, e i suoi bordi devono cadere esattamente sui due spigoli del blocco.

* Se tocca solo al centro e le estremità si alzano, non è abbastanza curvo: torna ad arrotolare.
* Se abbraccia oltre gli spigoli, hai esagerato: appiattiscilo leggermente in senso inverso.

**Una precisazione su cosa è normale.** A libro finito il dorso arrotondato **sporge un po' oltre il piano dei piatti**, e deve essere così: il profilo giusto è una curva che si raccorda dolcemente ai due piatti. Il difetto è un altro, ed è quando fra piatto e dorso si vede un gradino, o il dorso è visibilmente più piatto della curva del blocco.

**Rimedio a posteriori**, se il libro è già finito e la cosa dà fastidio: inumidire leggermente il dorso dall'esterno, fasciarlo stretto con una benda elastica o del nastro di carta modellando la curva con le dita, e lasciarlo asciugare così una notte. Non è garantito, e su un rivestimento chiaro rischi gli aloni.

### 16.10 Montare la cassa

1. Sul rovescio del rivestimento traccia a matita la posizione dei tre pezzi: dorso al centro, gole ai lati, piatti.
2. Stendi la colla sul **rivestimento**, non sul cartone (il cartone la beve e si imbarca).
3. Posiziona prima il dorso, poi i due piatti, usando come distanziale per la gola due strisce di cartone della larghezza giusta: a occhio non viene mai simmetrica.
4. Gira, e ripiega i rimbocchi: prima testa e piede, poi i lati. Pizzica bene gli angoli con le dita mentre la colla è ancora umida.
5. Con la stecca affonda le due gole, lavorando il rivestimento dentro il canale fra dorso e piatto: è quella piega che poi fa da cerniera.
6. Metti la cassa ad asciugare **sotto peso e in piano**, fra due fogli di carta oleata.

### 16.11 Incassatura

1. Prova a secco: appoggia il blocco nella cassa e controlla che le unghie siano uguali sui tre lati.
2. Apri il primo piatto, infila un foglio di **carta oleata** subito sotto la guardia da incollare, e stendi la colla sulla guardia (metà amido e metà vinilica, così hai tempo di posizionare e imbarca meno). Se hai fatto il dorso cavo, incolla anche la faccia esterna del tubo.
3. Sfila il foglio di protezione, chiudi il piatto **dal dorso verso il taglio davanti**, e liscia dal centro verso i bordi con la stecca sopra un foglio pulito.
4. Rigira il libro e ripeti sull'altra faccia.
5. Metti sotto pressione per una notte, con due bacchette sottili (di legno o metallo) appoggiate nelle due gole: sono loro a dare alla cerniera il solco netto.

### 16.12 Gli errori che si pagano

* **Piatti non identici** → unghie diverse fra le due facce.
* **Gola sbagliata** → il libro si apre a fatica, o la copertina balla.
* **Fibra nel verso sbagliato** su cartone o rivestimento → piatti imbarcati appena la colla asciuga. È l'errore più comune e non è recuperabile.
* **Colla troppo secca in arrotondatura** → il dorso non prende la curva e insisti col martello finché non ammacchi la carta.
* **Cartoncino del dorso non precurvato** → la copertina fa la "U" invece dell'arco e non aderisce alla curva del blocco (paragrafo 16.9).
* **Arco misurato oltre gli spigoli** → dorso largo, che resta staccato e lascia ballare le cerniere.
* **Dorso di cartone rigido** invece che cartoncino → copertina che non si apre.
* **Niente carta oleata** in fase di incassatura → l'umidità della colla passa alle prime pagine e le ondula.

---

## 17. Le scritte sulla copertina

Tre strade, in ordine di difficoltà. Quale conviene dipende soprattutto da come rivesti la copertina.

| Metodo | Va bene su | Attrezzatura | Se sbagli |
| --- | --- | --- | --- |
| Rivestimento stampato | carta | la stampante che hai già | butti un foglio |
| Tassello | carta e tela | stampante, più eventuale foil | rifai solo il tassello |
| Stencil | carta e tela | bisturi e acrilico | rovini la copertina |
| Impressione a caldo | tela e pelle | caratteri di ottone, fornelletto | rovini la copertina |

Lo stencil regge solo su titoli grandi sul piatto: sotto i 15–20 mm di altezza delle lettere, ritagliarlo a mano diventa impossibile, e il dorso vorrebbe lettere da 8–10 mm. Se lo provi, il trucco decisivo è dare una mano di medium acrilico trasparente su tutta la scritta appena applicato lo stencil: sigilla i bordi, e le infiltrazioni di colore trovano la strada già chiusa.

### 17.1 Stampare direttamente il rivestimento

Se copri in carta è la soluzione migliore, e non richiede niente che tu non abbia. Disegni tutta la copertina in un file — titolo sul piatto, titolo sul dorso, eventuali fregi — la stampi su carta da 120–160 g/m² e la usi come rivestimento.

Il rivestimento dell'esempio del capitolo 16 misura **246 × 382 mm**, quindi ci sta in un A3 (297 × 420) con margine abbondante. La fibra deve essere parallela al dorso, cioè al lato da 246: serve un A3 a grana corta, perché quello comune ha la fibra nel verso sbagliato.

**Le fasce del file**, misurate dal bordo sinistro del foglio da 382 mm:

| Da | A | Cosa |
| --- | --- | --- |
| 0 | 15 | rimbocco |
| 15 | 158 | piatto posteriore |
| 158 | 163 | gola |
| 163 | 219 | **dorso** |
| 219 | 224 | gola |
| 224 | 367 | **piatto anteriore** |
| 367 | 382 | rimbocco |

In verticale: 15 mm di rimbocco, 216 mm di piatto, 15 mm di rimbocco.

Il titolo del piatto va quindi nella fascia 224–367, quello del dorso ruotato di 90° nella fascia 163–219. Metti tutti i riferimenti — bordo di taglio, linee di rimbocco, gole — come sottili linee grigie **su un livello separato che spegni prima di stampare la versione buona**.

La scheda Copertina esporta una **sagoma PDF in scala 1:1** con queste stesse fasce: la pagina ha le dimensioni esatte del rivestimento (246 × 382 mm nell'esempio, non un formato standard) e contiene solo i contorni dei piatti, delle gole e del dorso, senza testo né grafica. Serve come riferimento sotto il file di grafica, o da stampare per controllare a occhio i pezzi tagliati. Per la brossura la sagoma mostra le quattro cordonature come linee tratteggiate. Se la stampi, disattiva ogni adattamento alla pagina.

Accortezze:

* **Stampa una prova su carta comune**, ritagliala e appoggiala sui cartoni già tagliati prima di sacrificare il foglio buono. Il registro fra scritta del dorso e dorso reale è la cosa che si sbaglia.
* Estendi il fondo (se colorato) di 3–5 mm oltre la linea di taglio, altrimenti un millimetro di sbieco ti lascia un filo bianco sul bordo.
* **A getto d'inchiostro**: dai una passata di fissativo spray prima di incollare, o l'umidità della colla scioglie l'inchiostro.
* **A laser**: non lisciare con la stecca direttamente sul toner, metti sopra un foglio pulito.
* Se hai solo l'A4, stampa il dorso come tassello a parte e il piatto come pannello incollato.

### 17.2 Il tassello

È la soluzione tradizionale, funziona anche sulla tela, e ha il vantaggio decisivo che se lo sbagli lo rifai senza buttare la copertina.

Prima di tutto un cambio di prospettiva: **il tassello si deve vedere**. Non è un ripiego mal riuscito, è l'elemento tradizionale della legatura — sui libri antichi il tassello di pelle rossa o verde sul dorso in cuoio è esattamente quello che fa "libro". L'obiettivo non è nasconderlo, è farlo sembrare **voluto** invece che appiccicato. Sono due cose diverse, e la seconda si ottiene curando cinque dettagli banali.

#### Misure

Per un dorso da 48 mm:

* larghezza: **spessore del dorso meno 12 mm circa**, quindi 36 mm, così resta un margine di rivestimento visibile ai due lati (la scheda Tasselli parte con 24 mm per i tasselli di dorso: adattali al tuo libro);
* altezza: 60–80 mm secondo la lunghezza del titolo;
* posizione: bordo superiore a **45–55 mm dalla testa**, cioè circa un quinto dell'altezza. Un tassello centrato in altezza sembra sempre troppo basso.

#### Che materiale

Il vincolo lo detta il metodo di scrittura. Se vuoi la doratura da toner, il tassello deve passare nella stampante laser, quindi dev'essere **carta** — niente pelle, niente tela — e dev'essere **liscia**, non vergata o ruvida: il foil si trasferisce solo dove il toner appoggia bene, e su una carta a grana viene a chiazze.

**Carta patinata opaca da 120–160 g/m², in colore scuro**: bordeaux, verde bottiglia, blu notte o nero, con l'oro sopra. È la combinazione classica e non sbaglia.

* Sopra i 250 g/m² il tassello sporge come una piastrella.
* Sotto i 120 g/m² si increspa quando lo incolli.

Se rinunci all'oro e scrivi in altro modo, si aprono la **pelle sottile da legatoria** (lo *skiver*, 0,5–0,8 mm), che è il materiale nobile, e la **tela** in colore contrastante rispetto alla copertina.

#### La doratura da toner

Con due soldi si ottengono scritte in oro vero. Il foglio da stampare lo prepara la scheda Tasselli ([README](../README.md#tasselli)), che ha una modalità *solo nero pieno* proprio per questo. Stampi il titolo con una **stampante laser** su carta liscia, appoggi sopra un foglio di *foil termico per toner* e lo passi in una plastificatrice a rulli — in mancanza, ferro da stiro tiepido con un foglio di carta forno sopra. Il foil aderisce solo dove c'è il toner: ottieni lettere dorate nitide, con il carattere che vuoi. Poi ritagli il tassello e lo incolli. Non funziona con le stampanti a getto d'inchiostro.

#### I cinque dettagli che fanno la differenza

1. **Il bordo tagliato.** Lama nuova, riga d'acciaio, un colpo solo per lato: un bordo seghettato è la prima cosa che si nota. Poi **colora il taglio** con un pennarello o un filo di acrilico del colore del tassello. Su carta scura, il bordo bianco dell'anima è ciò che urla "incollato sopra", ed è il dettaglio che quasi nessuno cura.
2. **Lo spessore ai bordi.** Passa un pezzetto di carta vetrata fine sul retro lungo i quattro lati, tenendola inclinata: assottigli il bordo a cuneo e il gradino sparisce quasi del tutto.
3. **Gli angoli.** Smussali appena, un raggio di un millimetro o due. Gli spigoli vivi sono quelli che si sollevano per primi e che si impigliano.
4. **Il filetto.** Un secondo tassello leggermente più grande sotto, in colore diverso, che sborda di 1,5–2 mm tutt'intorno. Cinque minuti di lavoro che trasformano la percezione: da toppa a cornice.
5. **La coppia.** Un tassello solo sembra un rattoppo, due sembrano un progetto. Mettine un secondo più in basso sul dorso, più piccolo, con l'anno o il tuo nome. È la disposizione dei libri ottocenteschi.

#### Se lo vuoi a filo: l'intarsio

Ritagli nel rivestimento una finestra delle dimensioni esatte del tassello **prima** di incollare il rivestimento sui cartoni, e ci alloggi dentro il tassello, che va a battuta senza gradino. Il risultato è ottimo, ma la finestra dev'essere precisa al decimo di millimetro e non c'è margine d'errore. Su un primo libro non ci proverei.

#### Quando incollarlo

Sulla **cassa già montata e rivestita**, ma **prima dell'incassatura**, con la copertina distesa piatta sul tavolo. Colla sul tassello e non sul dorso, posizioni, carta oleata sopra, mezz'ora sotto un peso.

Attaccarlo su un dorso già curvo e già incassato significa premere su una superficie tonda che non puoi mettere sotto peso: i bordi si sollevano.

### 17.3 Impressione a caldo

Caratteri di ottone montati su un compositoio, scaldati, e foglia d'oro impressa direttamente sulla tela o sulla pelle. Il risultato è di un altro livello, perché la scritta è incisa oltre che dorata. Ma un set di caratteri decente costa centinaia di euro e ci vuole pratica per non bruciare il rivestimento e non restare storti. Ha senso solo se rileghi con regolarità.

### 17.4 Note tipografiche

* **Sul dorso**, con 48 mm hai spazio abbondante: titolo nel terzo superiore, autore o anno in basso, almeno 15 mm liberi a testa e piede.
* **Verso di lettura**: in Italia si trovano libri scritti dall'alto in basso e libri scritti dal basso in alto. Il criterio pratico è che con il testo dall'alto in basso il titolo si legge dritto quando il libro è appoggiato sul tavolo con il piatto anteriore in su.
* **Sul piatto**, il classico è il titolo centrato nel terzo superiore, con i margini laterali coerenti con le unghie.
* **La prova dei due metri**: stampa il titolo su carta comune, ritaglialo, appoggialo sulla copertina finita e guardalo da lontano. I corpi che sembrano giusti sullo schermo, sul dorso, vengono quasi sempre troppo grandi.
