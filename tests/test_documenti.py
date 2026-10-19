"""I documenti: README.md e docs/manuale.md.

Non giudicano il contenuto: controllano che rimandi, ancore, indice e link non si
rompano quando si modifica il testo (per esempio rinumerando un capitolo).
"""
import re
import subprocess
import sys

import pytest

from conftest import RADICE

README = RADICE / "README.md"
MANUALE = RADICE / "docs" / "manuale.md"
DOCUMENTI = [README, MANUALE]
ID = ["README", "manuale"]


def leggi(percorso):
    return percorso.read_text(encoding="utf-8")


def senza_codice(testo):
    return re.sub(r"(?s)```.*?```", "", testo)


def slug(titolo):
    """L'ancora che GitHub ricava da un'intestazione."""
    t = re.sub(r"[`*]", "", titolo.lower())
    t = re.sub(r"[^\w\s-]", "", t)
    return re.sub(r"\s", "-", t.strip())


def intestazioni(testo):
    return [(len(m.group(1)), m.group(2).strip())
            for m in re.finditer(r"(?m)^(#{1,6}) (.+)$", senza_codice(testo))]


def ancore(testo):
    return [slug(t) for _, t in intestazioni(testo)]


def sezioni_del_manuale():
    """{'13': 'cucitura', '16.6': 'le tre misure e le formule', ...} dalle intestazioni numerate."""
    out = {}
    for _, t in intestazioni(leggi(MANUALE)):
        m = re.match(r"(\d+(?:\.\d+)?)\.? (.*)", t)
        if m:
            out[m.group(1)] = t
    return out


@pytest.mark.parametrize("doc", DOCUMENTI, ids=ID)
def test_nessuna_ancora_duplicata(doc):
    a = ancore(leggi(doc))
    assert len(a) == len(set(a)), sorted({x for x in a if a.count(x) > 1})


@pytest.mark.parametrize("doc", DOCUMENTI, ids=ID)
def test_i_link_relativi_puntano_a_file_e_ancore_esistenti(doc):
    testo = senza_codice(leggi(doc))
    controllati = 0
    for m in re.finditer(r"!?\[[^\]]*\]\(([^)\s]+)\)", testo):
        bersaglio = m.group(1)
        if re.match(r"(https?:|mailto:)", bersaglio):
            continue
        percorso, _, ancora = bersaglio.partition("#")
        file = (doc.parent / percorso).resolve() if percorso else doc
        assert file.exists(), f"{doc.name}: manca {bersaglio}"
        if ancora and file.suffix == ".md":
            assert ancora in ancore(leggi(file)), f"{doc.name}: l'ancora '#{ancora}' non esiste in {file.name}"
        controllati += 1
    assert controllati > 5


def test_le_immagini_del_readme_esistono_e_non_sono_enormi():
    immagini = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", leggi(README))
    assert len(immagini) >= 3
    for i in immagini:
        file = RADICE / i
        assert file.is_file(), i
        assert file.stat().st_size < 250_000, f"{i} pesa {file.stat().st_size // 1024} KB"


def test_l_indice_del_manuale_corrisponde_alle_intestazioni():
    testo = leggi(MANUALE)
    indice = re.findall(r"(?m)^(\d+)\. \[([^\]]+)\]\(#([^)]+)\)$", testo)
    capitoli = [(m.group(1), m.group(2)) for m in re.finditer(r"(?m)^## (\d+)\. (.+)$", testo)]
    assert [(n, t) for n, t, _ in indice] == capitoli
    for n, t, a in indice:
        assert a == slug(f"{n}. {t}")


def test_l_indice_del_manuale_nel_readme_corrisponde_al_manuale():
    voci = re.findall(r"(?m)^(\d+)\. \[([^\]]+)\]\(docs/manuale\.md#([^)]+)\)$", leggi(README))
    capitoli = [(m.group(1), m.group(2)) for m in re.finditer(r"(?m)^## (\d+)\. (.+)$", leggi(MANUALE))]
    assert [(n, t) for n, t, _ in voci] == capitoli


def test_capitoli_e_paragrafi_del_manuale_sono_numerati_senza_buchi():
    sezioni = sezioni_del_manuale()
    capitoli = sorted(int(n) for n in sezioni if "." not in n)
    assert capitoli == list(range(1, len(capitoli) + 1)) and len(capitoli) == 17
    for capo in capitoli:
        sotto = sorted(int(n.split(".")[1]) for n in sezioni if n.startswith(f"{capo}."))
        assert sotto == list(range(1, len(sotto) + 1)), f"capitolo {capo}: {sotto}"


def test_i_rimandi_interni_del_manuale_puntano_a_sezioni_che_esistono():
    sezioni = sezioni_del_manuale()
    testo = senza_codice(leggi(MANUALE))
    rimandi = 0
    for m in re.finditer(r"(?i)\b(?:capitol[oi]|paragraf[oi]|metodo)\s+(\d+(?:\.\d+)?)((?:\s+e\s+\d+(?:\.\d+)?)?)", testo):
        for n in [m.group(1)] + re.findall(r"\d+(?:\.\d+)?", m.group(2)):
            assert n in sezioni, f"rimando a '{n}' ({m.group(0)!r}) ma nel manuale non c'e'"
            rimandi += 1
    for m in re.finditer(r"\*\*(\d+\.\d+)\*\*", testo):          # i rimandi in grassetto del capitolo sulle guardie
        assert m.group(1) in sezioni, m.group(0)
    assert rimandi >= 15


def test_i_link_del_readme_al_manuale_dicono_il_numero_giusto():
    """Il testo del link ('capitolo 16.6') deve essere la sezione a cui punta."""
    sezioni = sezioni_del_manuale()
    per_ancora = {slug(t): n for n, t in sezioni.items()}
    trovati = 0
    for m in re.finditer(r"\[(?:capitolo )?(\d+(?:\.\d+)?)\]\(docs/manuale\.md#([^)]+)\)", leggi(README)):
        assert per_ancora.get(m.group(2)) == m.group(1), f"{m.group(0)} punta a {per_ancora.get(m.group(2))}"
        trovati += 1
    assert trovati >= 15


def test_il_readme_non_ha_piu_rimandi_a_capitoli_senza_link():
    """Ogni 'capitolo N' del README e' un link al manuale: se resta scoperto e' un numero
    che non e' stato rinumerato."""
    testo = senza_codice(leggi(README))
    for m in re.finditer(r"(?i)capitol[oi] (\d+(?:\.\d+)?)", testo):
        prima = testo[max(0, m.start() - 1):m.start()]
        assert prima == "[" or "manuale" in testo[max(0, m.start() - 40):m.end() + 40], \
            f"rimando senza link: {testo[max(0, m.start() - 40):m.end() + 40]!r}"


def test_le_opzioni_citate_nei_documenti_esistono_nel_programma():
    def aiuto(*a):
        return subprocess.run([sys.executable, "-m", "legatoria", *a, "-h"], cwd=RADICE,
                              capture_output=True, text=True).stdout
    esistenti = set(re.findall(r"--[a-z][a-z-]+", aiuto("imposizione") + aiuto("copertina") + aiuto()))
    citate = set()
    for doc in DOCUMENTI:
        citate |= set(re.findall(r"`(--[a-z][a-z-]+)", leggi(doc)))
    assert citate, "nessuna opzione citata?"
    assert not (citate - esistenti), sorted(citate - esistenti)
