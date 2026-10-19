"""docs/genera_pdf.sh: lo script che converte il manuale in PDF.

Non richiede pandoc o xelatex per essere validato: controlla la sintassi bash,
i permessi e i messaggi d'errore quando una dipendenza manca (simulando un PATH
senza quella dipendenza).  La conversione vera si prova solo se pandoc e xelatex
sono presenti in questo ambiente.
"""
import os
import shutil
import subprocess

import pytest

from conftest import RADICE

SCRIPT = RADICE / "docs" / "genera_pdf.sh"


def esegui(*args, path=None, fontconfig=None):
    env = dict(os.environ)
    if path is not None:
        env["PATH"] = path
    if fontconfig is not None:
        env["FONTCONFIG_FILE"] = fontconfig
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=RADICE,
                          capture_output=True, text=True, env=env)


def fontconfig_senza(tmp_path, *nomi_famiglia):
    """Un FONTCONFIG_FILE che nasconde le famiglie indicate, cosi' fc-match non
    le trova piu' anche se i file dei font restano installati sul sistema.

    Riproduce il caso reale (Arch senza il pacchetto ttf-caladea): lo script
    deve accorgersene con fc-match, non scoprirlo dall'errore oscuro di xelatex.
    """
    rifiuti = "".join(f"<glob>{p}</glob>\n      " for f in nomi_famiglia
                      for p in _percorsi_famiglia(f))
    conf = tmp_path / "fonts.conf"
    conf.write_text(f'''<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>/usr/share/fonts</dir>
  <selectfont>
    <rejectfont>
      {rifiuti}
    </rejectfont>
  </selectfont>
  <cachedir>{tmp_path / "cache"}</cachedir>
</fontconfig>
''', encoding="utf-8")
    subprocess.run(["fc-cache", "-f"], env={**os.environ, "FONTCONFIG_FILE": str(conf)},
                   capture_output=True)
    return str(conf)


def _percorsi_famiglia(nome_famiglia):
    r = subprocess.run(["fc-list", "--format=%{file}\n", nome_famiglia],
                       capture_output=True, text=True)
    return [riga for riga in r.stdout.splitlines() if riga.strip()]


def path_con_solo(*comandi):
    """Un PATH minimo che contiene solo i comandi indicati, piu' quelli che lo
    script usa per calcolare la propria posizione (dirname: cd e pwd sono
    builtin di bash, ma dirname e' un binario esterno).

    Ricreata da zero a ogni chiamata: una cartella riusata fra un test e l'altro
    lascerebbe i collegamenti del test precedente, e un PATH "senza pandoc"
    troverebbe comunque il pandoc lasciato li' da un test passato prima."""
    cartella = RADICE / ".pytest_path_finto"
    shutil.rmtree(cartella, ignore_errors=True)
    cartella.mkdir()
    for nome in ("bash", "dirname", *comandi):
        trovato = shutil.which(nome)
        if trovato:
            (cartella / nome).symlink_to(trovato)
    return str(cartella)


def test_lo_script_esiste_ed_e_eseguibile():
    assert SCRIPT.is_file()
    assert os.access(SCRIPT, os.X_OK), "manca il permesso di esecuzione (chmod +x)"


def test_la_sintassi_bash_e_valida():
    r = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_messaggio_chiaro_se_manca_pandoc():
    r = esegui(path=path_con_solo())          # ne' pandoc ne' xelatex
    assert r.returncode != 0
    assert "pandoc" in r.stderr.lower()


def test_messaggio_chiaro_se_manca_xelatex():
    r = esegui(path=path_con_solo("pandoc"))  # pandoc c'e', xelatex no
    assert r.returncode != 0
    assert "xelatex" in r.stderr.lower()


def test_messaggio_chiaro_se_manca_il_manuale(tmp_path):
    finto = tmp_path / "docs" / "genera_pdf.sh"
    finto.parent.mkdir()
    shutil.copy(SCRIPT, finto)
    finto.chmod(0o755)
    r = subprocess.run(["bash", str(finto)], capture_output=True, text=True)
    assert r.returncode != 0
    assert "manuale.md" in r.stderr


SERVONO_FONT = not (shutil.which("fc-match") and shutil.which("fc-list") and shutil.which("fc-cache"))


@pytest.mark.skipif(SERVONO_FONT, reason="servono fc-match, fc-list e fc-cache per questi test")
def test_senza_caladea_usa_liberation_serif_e_avvisa(tmp_path):
    """Il caso reale: su un sistema senza il pacchetto del font (per esempio Arch
    senza ttf-caladea) lo script deve accorgersene da solo, avvisare con il nome
    esatto del pacchetto da installare, e produrre comunque il PDF con un font di
    ripiego — non fallire con l'errore oscuro di xelatex/mktextfm."""
    if not shutil.which("fc-match") or subprocess.run(
            ["fc-match", "--format=%{family}", "Liberation Serif"],
            capture_output=True, text=True).stdout.strip() != "Liberation Serif":
        pytest.skip("questo ambiente non ha Liberation Serif come ripiego")
    fc = fontconfig_senza(tmp_path, "Caladea")
    destinazione = tmp_path / "manuale.pdf"
    r = esegui(str(destinazione), fontconfig=fc)
    assert r.returncode == 0, r.stderr
    assert "Caladea" in r.stderr and "Liberation Serif" in r.stderr
    assert "ttf-caladea" in r.stderr, "l'avviso deve dare il nome del pacchetto da installare"
    if shutil.which("pandoc") and shutil.which("xelatex"):
        assert destinazione.is_file() and destinazione.read_bytes()[:5] == b"%PDF-"


@pytest.mark.skipif(SERVONO_FONT, reason="servono fc-match, fc-list e fc-cache per questi test")
def test_senza_caladea_ne_liberation_serif_errore_chiaro(tmp_path):
    fc = fontconfig_senza(tmp_path, "Caladea", "Liberation Serif")
    r = esegui(str(tmp_path / "manuale.pdf"), fontconfig=fc)
    assert r.returncode != 0
    assert "caladea" in r.stderr.lower() and "liberation serif" in r.stderr.lower()


@pytest.mark.skipif(SERVONO_FONT, reason="servono fc-match, fc-list e fc-cache per questi test")
def test_senza_dejavu_sans_mono_errore_chiaro(tmp_path):
    fc = fontconfig_senza(tmp_path, "DejaVu Sans Mono")
    r = esegui(str(tmp_path / "manuale.pdf"), fontconfig=fc)
    assert r.returncode != 0
    assert "dejavu sans mono" in r.stderr.lower()


@pytest.mark.skipif(not (shutil.which("pandoc") and shutil.which("xelatex")),
                    reason="servono pandoc e xelatex per una conversione vera")
def test_conversione_vera_in_pdf(tmp_path):
    destinazione = tmp_path / "manuale.pdf"
    r = esegui(str(destinazione))
    assert r.returncode == 0, r.stderr
    assert destinazione.is_file() and destinazione.stat().st_size > 10_000
    assert destinazione.read_bytes()[:5] == b"%PDF-"


@pytest.mark.skipif(not (shutil.which("pandoc") and shutil.which("xelatex")),
                    reason="servono pandoc e xelatex per una conversione vera")
def test_destinazione_di_default(tmp_path, monkeypatch):
    """Senza argomenti scrive docs/manuale.pdf, che .gitignore deve escludere."""
    predefinito = RADICE / "docs" / "manuale.pdf"
    predefinito.unlink(missing_ok=True)
    try:
        r = esegui()
        assert r.returncode == 0, r.stderr
        assert predefinito.is_file()
    finally:
        predefinito.unlink(missing_ok=True)
