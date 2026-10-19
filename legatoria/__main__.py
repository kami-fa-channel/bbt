"""python -m legatoria"""

import sys

try:
    from .cli import main
except ImportError as e:
    sys.exit(f"Errore: manca una libreria ({e}).\n"
             "Le librerie (pypdf, reportlab, fonttools) si installano come spiegato nel "
             "README, sezione Installazione: in un ambiente virtuale con  pip install -r "
             "requirements.txt, oppure con il gestore di pacchetti della distribuzione.")

main()
