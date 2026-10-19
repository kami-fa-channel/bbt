"""La riga di comando, provata come la userebbe una persona: un processo vero."""
import subprocess
import sys

from conftest import RADICE


def legatoria(*args, stdin=None):
    return subprocess.run([sys.executable, "-m", "legatoria", *map(str, args)], cwd=RADICE,
                          input=stdin, capture_output=True, text=True)


def test_versione():
    r = legatoria("--version")
    assert r.returncode == 0 and r.stdout.startswith("legatoria ")


def test_analisi_senza_generare_nulla(pdf_bianco, tmp_path):
    r = legatoria("imposizione", "-i", pdf_bianco(749), "-f", 4, "-g", 1, "-p", 4, "-n")
    assert r.returncode == 0
    assert "CONSIGLIATO" in r.stdout and "TABELLA INTERVALLI DI STAMPA" in r.stdout
    assert "Tranche 8   intervallo di stampa 337-384" in r.stdout
    assert not list(tmp_path.glob("*_booklet.pdf"))


def test_generazione_del_file(pdf_bianco, tmp_path):
    uscita = tmp_path / "libro.pdf"
    r = legatoria("imposizione", "-i", pdf_bianco(64), "-f", 4, "--segni", "-o", uscita)
    assert r.returncode == 0 and "Fatto:" in r.stdout and uscita.is_file()


def test_errori_chiari_e_codice_di_uscita(pdf_bianco):
    pdf = pdf_bianco(10)
    for args, messaggio in (
        (["-p", "9999"], "fuori dall'intervallo 1-11"),
        (["-p", "abc"], "'abc' non valida"),
        (["-f", "0"], "-f deve essere almeno 1"),
    ):
        r = legatoria("imposizione", "-i", pdf, *args, "-n")
        assert r.returncode == 1 and messaggio in r.stderr and r.stderr.startswith("Errore:")
    r = legatoria("imposizione", "-i", "/non/esiste.pdf", "-n")
    assert r.returncode == 1 and "non esiste" in r.stderr


def test_copertina_con_i_numeri_del_readme():
    r = legatoria("copertina", "-H", 210, "-L", 145, "-D", 48, "-u", 3, "-c", 3, "-g", 5)
    assert r.returncode == 0
    assert "216 x 143" in r.stdout and "246 x 382" in r.stdout


def test_copertina_interattiva():
    r = legatoria("copertina", stdin="210\n145\n48\n\n\n\n\n\n")
    assert r.returncode == 0 and "PEZZI DA TAGLIARE" in r.stdout


def test_copertina_incompleta_e_un_errore_di_uso():
    r = legatoria("copertina", "-H", 210)
    assert r.returncode == 2 and "servono -H, -L e -D" in r.stderr


def test_filo_indicato_da_riga_di_comando(pdf_bianco):
    pdf = pdf_bianco(749)
    generico = legatoria("imposizione", "-i", pdf, "-f", 4, "-n")
    mio = legatoria("imposizione", "-i", pdf, "-f", 4, "--filo", 0.4, "-n")
    assert mio.returncode == 0
    assert "mm di filo (0.4 mm per fascicolo, indicati da te)" in mio.stdout
    assert "mm di filo (" not in generico.stdout           # senza --filo il testo e' quello di sempre
    riga_generica = next(r for r in generico.stdout.splitlines() if r.startswith("Spessore del blocco"))
    assert "14.1-23.5 mm di filo" in riga_generica            # 47 fascicoli x 0,3-0,5
    riga_mia = next(r for r in mio.stdout.splitlines() if r.startswith("Spessore del blocco"))
    assert "18.8 mm di filo" in riga_mia                      # 47 x 0,4


def test_filo_non_valido_da_riga_di_comando(pdf_bianco):
    for valore in ("0", "-1"):
        r = legatoria("imposizione", "-i", pdf_bianco(16), "--filo=" + valore, "-n")
        assert r.returncode == 1 and "filo per fascicolo deve essere maggiore di zero" in r.stderr
        assert "ANALISI DELLA FASCICOLATURA" not in r.stdout      # errore subito, prima di stampare


def test_avviso_sul_filo_che_sembra_il_totale(pdf_bianco):
    r = legatoria("imposizione", "-i", pdf_bianco(64), "--filo", 16, "-n")
    assert r.returncode == 0 and "Attenzione: 16 mm di filo per fascicolo" in r.stdout


def test_il_filo_non_cambia_il_file_prodotto(pdf_bianco, tmp_path):
    pdf = pdf_bianco(64)
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    assert legatoria("imposizione", "-i", pdf, "-f", 4, "-o", a).returncode == 0
    assert legatoria("imposizione", "-i", pdf, "-f", 4, "--filo", 0.45, "-o", b).returncode == 0
    from pypdf import PdfReader
    assert len(PdfReader(str(a)).pages) == len(PdfReader(str(b)).pages) == 32


def test_lancio_classico_con_bbt_py():
    """python bbt.py funziona senza installare il pacchetto, e non e' un modulo del pacchetto."""
    r = subprocess.run([sys.executable, "bbt.py", "copertina", "-H", "210", "-L", "145", "-D", "48",
                        "-u", "3", "-c", "3", "-g", "5"], cwd=RADICE, capture_output=True, text=True)
    assert r.returncode == 0 and "246 x 382" in r.stdout
    r = subprocess.run([sys.executable, "bbt.py", "--version"], cwd=RADICE, capture_output=True, text=True)
    assert r.stdout.startswith("legatoria ")


def test_nessun_file_chiamato_come_il_pacchetto_accanto_al_pacchetto():
    """Regressione: un legatoria.py accanto alla cartella legatoria/ faceva fallire pip install ."""
    assert (RADICE / "legatoria").is_dir()
    assert not (RADICE / "legatoria.py").exists()
