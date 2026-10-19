"""Errori del programma."""


class ErroreLegatoria(Exception):
    """Errore di dati o di parametri, con un messaggio gia' pronto per l'utente.

    La riga di comando lo stampa preceduto da "Errore:", la finestra lo mostra
    in una finestra di dialogo.
    """
