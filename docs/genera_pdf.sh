#!/usr/bin/env bash
# genera_pdf.sh - Converte il manuale (docs/manuale.md) in un PDF con un aspetto
# curato: indice cliccabile (quello gia' scritto nel manuale), tabelle con le
# righe tipografiche giuste, formule del capitolo 8 rese come vera matematica.
#
# Uso:
#   docs/genera_pdf.sh                  # scrive docs/manuale.pdf
#   docs/genera_pdf.sh /tmp/output.pdf  # scrive dove indicato
#
# Dipendenze (nessuna e' fra quelle di bbt: servono solo per questo script):
#   - pandoc
#   - una distribuzione LaTeX con il motore xelatex, e i pacchetti lmodern e
#     fontspec (di norma inclusi in una installazione "recommended")
#   - il font DejaVu Sans Mono per il codice (quasi sempre gia' presente)
#   - il font Caladea per il testo; se manca lo script usa Liberation Serif,
#     quasi sempre presente, con un aspetto un po' meno curato
#
# Su Arch/Manjaro:
#   sudo pacman -S pandoc texlive-xetex texlive-fontsrecommended \
#                  texlive-langextra ttf-caladea ttf-dejavu ttf-liberation
# Su Debian/Ubuntu:
#   sudo apt install pandoc texlive-xetex texlive-latex-recommended \
#                     texlive-fonts-recommended fonts-crosextra-caladea \
#                     fonts-dejavu fonts-liberation

set -euo pipefail

QUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SORGENTE="$QUI/manuale.md"
DESTINAZIONE="${1:-$QUI/manuale.pdf}"

errore() {
    echo "Errore: $1" >&2
    exit 1
}

# Un font e' davvero installato solo se fontconfig lo fa corrispondere a se'
# stesso: altrimenti fc-match restituisce silenziosamente il font di ripiego
# piu' simile, e xelatex fallisce piu' avanti con un errore molto meno chiaro
# (mktextfm che cerca di generare un font bitmap per un nome che non esiste).
font_installato() {
    command -v fc-match >/dev/null 2>&1 || return 1
    [ "$(fc-match --format='%{family}\n' "$1" 2>/dev/null | head -1)" = "$1" ]
}

command -v pandoc >/dev/null 2>&1 || errore "manca pandoc. Installalo con il gestore di pacchetti del tuo sistema (vedi l'intestazione di questo script)."
command -v xelatex >/dev/null 2>&1 || errore "manca xelatex (fa parte di una distribuzione LaTeX). Installalo con il gestore di pacchetti del tuo sistema (vedi l'intestazione di questo script)."
[ -f "$SORGENTE" ] || errore "non trovo $SORGENTE."

FONT_TESTO="Caladea"
if ! font_installato "$FONT_TESTO"; then
    if font_installato "Liberation Serif"; then
        echo "Nota: manca il font Caladea, uso Liberation Serif al suo posto." \
             "Per il font previsto: sudo pacman -S ttf-caladea" \
             "(Debian/Ubuntu: sudo apt install fonts-crosextra-caladea)" >&2
        FONT_TESTO="Liberation Serif"
    else
        errore "mancano sia Caladea sia il suo ripiego Liberation Serif. Installa uno dei due (vedi l'intestazione di questo script), poi riprova."
    fi
fi

FONT_CODICE="DejaVu Sans Mono"
font_installato "$FONT_CODICE" \
    || errore "manca il font $FONT_CODICE. Installalo con il gestore di pacchetti del tuo sistema (vedi l'intestazione di questo script)."

pandoc "$SORGENTE" -o "$DESTINAZIONE" \
    --pdf-engine=xelatex \
    -V mainfont="$FONT_TESTO" \
    -V monofont="$FONT_CODICE" \
    -V fontsize=11pt \
    -V geometry:margin=2.5cm \
    -V colorlinks=true \
    -V linkcolor=blue \
    -V lang=it \
    --metadata title="Manuale di legatoria" \
    || errore "la conversione e' fallita (vedi il messaggio di pandoc/xelatex sopra). Se manca un font, i nomi si trovano con: fc-list | grep -i nome"

echo "Scritto: $DESTINAZIONE"
