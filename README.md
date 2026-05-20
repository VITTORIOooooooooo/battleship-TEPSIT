# Battleship – Client & Server

## Descrizione

Questo progetto implementa una versione multiplayer del classico gioco Battaglia Navale in Python, usando socket TCP per la comunicazione di rete e Pygame per l'interfaccia grafica.

L'applicazione segue un'architettura client-server: il server gestisce la logica della partita, i turni, la validazione dei colpi e la sincronizzazione tra i giocatori; i client rappresentano la parte grafica con cui gli utenti interagiscono.

## Come funziona

La partita supporta due giocatori collegati in rete locale. All'avvio, il server resta in attesa delle connessioni. Il primo client che si collega diventa il Giocatore 1, il secondo il Giocatore 2.
Dopo la connessione inizia la fase di posizionamento delle navi: i giocatori collocano le proprie unità sulla griglia personale a turno, uno alla volta. Quando entrambi hanno terminato, la partita parte automaticamente.
Durante il gioco i giocatori si alternano: il giocatore attivo seleziona una casella della griglia nemica per sparare, il server verifica il colpo e sincronizza il risultato su entrambi i client. Se il colpo va a segno il giocatore attivo ottiene un turno bonus e può continuare ad attaccare; se manca, il turno passa all'avversario. La partita termina quando uno dei due ha affondato l'intera flotta nemica. Su entrambi i client compare la schermata di fine partita con l'esito per ciascun giocatore.

## Griglia di gioco

Le griglie sono 10x10 (righe da A a J, colonne da 1 a 10) e mostrano le proprie navi, i colpi subiti, i colpi effettuati sulla griglia nemica e le celle già colpite.

## Caratteristiche principali

- Gestione completa dei turni e controllo delle vittorie
- Sincronizzazione in tempo reale tra i giocatori
- Chat in-game tra i partecipanti
- Leaderboard persistente aggiornata al termine di ogni partita
- Menu iniziale interattivo e finestra ridimensionabile

## Requisiti di sistema

- Python 3.9 o superiore
- Sistema operativo: Windows, macOS o Linux
- Risoluzione schermo consigliata: 1280x720 o superiore

## Librerie necessarie

Il progetto richiede l'installazione di pygame. Tutte le altre librerie utilizzate (socket, json, threading, sys, os) sono incluse nella libreria standard di Python.

## File del progetto

- server_battaglia_navale.py — gestisce connessioni, turni e logica di gioco
- client_bn.py — interfaccia grafica Pygame e interazione utente
- leaderboard.json — classifica (generata automaticamente alla fine della prima partita)
- README.md — questo file

## Avvio

Il server deve essere avviato prima dei client. I due client vanno avviati in finestre o terminali separati.
python server_battaglia_navale.py
python client_bn.py


## Note

- La comunicazione avviene tramite socket TCP sulla porta 50005.
- Il server mostra nel prompt le connessioni in ingresso, assegnando automaticamente Player 1 e Player 2 con indirizzo e porta di provenienza.
- La leaderboard viene salvata nel file leaderboard.json e aggiornata automaticamente al termine di ogni partita.
