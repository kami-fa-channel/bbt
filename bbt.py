#!/usr/bin/env python3
"""bbt (books binding tool): avvio senza installare niente.

    python bbt.py                       apre la finestra
    python bbt.py copertina -H 210 -L 145 -D 48

Equivale a  python -m legatoria  e accetta gli stessi argomenti.  Le librerie
(pypdf, reportlab, fonttools) devono essere disponibili al Python che lo esegue:
vedi il README, sezione Installazione.

Il file non si chiama legatoria.py di proposito: accanto al pacchetto
(la cartella legatoria/) un file con lo stesso nome fa confondere gli strumenti di
installazione, e pip install . smette di funzionare.
"""
import runpy

runpy.run_module("legatoria", run_name="__main__")
