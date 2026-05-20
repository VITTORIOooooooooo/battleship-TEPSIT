===========================================
 BATTLESHIP – CLIENT & SERVER 
===========================================

## DESCRIZIONE

Questo progetto implementa una versione multiplayer del classico gioco
“Battaglia Navale” sviluppata in Python utilizzando socket TCP per la
comunicazione di rete e Pygame per la realizzazione dell’interfaccia
grafica e delle animazioni.

L’applicazione utilizza un’architettura client-server:

- il server gestisce l’intera logica della partita,
  i turni, i controlli dei colpi e la sincronizzazione
  tra i giocatori;
- i client rappresentano invece la parte grafica con cui
  gli utenti interagiscono.

La partita supporta due giocatori collegati tramite rete locale.
Quando il server viene avviato, resta in attesa delle connessioni.
Il primo client che si collega viene assegnato automaticamente al
Giocatore 1, mentre il secondo diventa il Giocatore 2.

Dopo la connessione inizia la fase di posizionamento delle navi.
Ogni giocatore deve collocare le proprie unità sulla griglia personale aspettando il proprio turno perchè bisogna farlo un client alla volta, quando il primo giocatore ha finito di posizionare tocca al secondo giocatore. dopo nche entrambi i client hanno finito di posizionare, la partita comincia automaticamente,

Durante il gioco i partecipanti si alternano a turni:

- il giocatore attivo può selezionare una casella della griglia nemica
  per sparare;
- il server verifica se il colpo è andato a segno oppure no;
- il risultato viene sincronizzato e mostrato graficamente su entrambi
  i client.
- se viene colpita una nave avversaria, allora tocca di nuovo allo stesso giocatore attaccare fino a quando non sbaglia e allora il suo      turno di gioco finisce e passa all'avversario.
- la partita continua fino a quando uno dei due giocatori non ha colpito e affondato tutte le navi avversarie. Al termine della partita, che termina automaticamente, viene mostrata uan schermata su entrambi i client con una scritta "HAI VINTO" in verde e "HAI PERSO" in rosso.
 

Il sistema include:

* gestione completa dei turni;
* controllo delle vittorie;
* sincronizzazione in tempo reale tra i giocatori;
* menu iniziale interattivo;
* finestra ridimensionabile.

Le griglie di gioco mostrano :

* le griglie sono 5X5 (verticale da A a E, orizzontale da 1 a 5)
* le proprie navi;
* i colpi subiti;
* i colpi effettuati contro il nemico;
* le celle già colpite.


Questo progetto rappresenta un esempio pratico di sviluppo di un videogioco
multiplayer in Python e combina:

* programmazione di rete;
* gestione socket TCP;
* threading;
* grafica 2D;
* sincronizzazione client-server;
* gestione eventi;
* sviluppo di interfacce interattive.


REQUISITI DI SISTEMA
--------------------
- Python 3.9 o superiore
- Sistema operativo: Windows, macOS o Linux
- Risoluzione schermo consigliata: 1280x720 o superiore

LIBRERIE NECESSARIE
-------------------
Il progetto richiede le seguenti librerie Python:

1. pygame
2. socket (inclusa in Python)
3. json (inclusa in Python)
4. threading (inclusa in Python)
5. sys (inclusa in Python)
6. os (inclusa in Python)


FILE DEL PROGETTO
-----------------
Il progetto è composto da:

- server_battaglia_navale.py   → gestisce connessioni, turni e logica di gioco
- client_bn.py   → interfaccia grafica Pygame e interazione utente
- README.md  → informazioni sul progetto


NOTE
----
- Il server deve essere avviato prima dei client.
- I due client devono essere avviati in finestre separate.
- La comunicazione avviene tramite socket TCP sulla porta 50005.
- Il server  mostra automaticamente sul prompt le connessione dei due client e gli assegna player 1 e player 2 indicando anche da che numero di porta provengono.
