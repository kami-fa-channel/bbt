"""Coerenza del progetto: i file di configurazione devono dire le stesse cose.

Alcune informazioni sono scritte in piu' posti a mano: le librerie (requirements.txt e
pyproject.toml), l'elenco dei pacchetti, la versione minima di Python (pyproject.toml,
README e integrazione continua).  Se se ne cambia una e ci si dimentica delle altre,
il programma funziona nella cartella del progetto ma si rompe dopo pip install .
"""
import importlib
import re

import pytest

from conftest import RADICE

try:
    import tomllib
except ImportError:                       # Python < 3.11: tomli arriva con pytest
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

pytestmark = pytest.mark.skipif(
    tomllib is None, reason="su Python < 3.11 serve tomli (lo installa gia' pytest)")


def pyproject():
    with open(RADICE / "pyproject.toml", "rb") as fh:
        return tomllib.load(fh)


def righe_requirements():
    righe = set()
    for riga in (RADICE / "requirements.txt").read_text(encoding="utf-8").splitlines():
        riga = riga.split("#")[0].strip()
        if riga:
            righe.add(riga)
    return righe


def test_requirements_txt_elenca_le_stesse_librerie_del_pyproject():
    p = pyproject()["project"]
    extra = p["optional-dependencies"]
    attese = set(p["dependencies"]) | set(extra["anteprima"]) | set(extra["cornice"])
    trovate = righe_requirements()
    assert trovate == attese, (
        f"solo in requirements.txt: {sorted(trovate - attese)}; "
        f"solo in pyproject.toml: {sorted(attese - trovate)}")


def test_i_pacchetti_elencati_sono_tutti_e_soli_quelli_che_esistono():
    """Un pacchetto non elencato in `packages` manca dopo pip install ."""
    elencati = set(pyproject()["tool"]["setuptools"]["packages"])
    base = RADICE / "legatoria"
    trovati = set()
    for cartella in [base, *(d for d in base.rglob("*") if d.is_dir())]:
        if cartella.name == "__pycache__" or not any(cartella.glob("*.py")):
            continue
        assert (cartella / "__init__.py").exists(), f"{cartella} ha moduli ma non __init__.py"
        trovati.add(".".join(cartella.relative_to(RADICE).parts))
    assert trovati == elencati, (
        f"esistono ma non sono elencati in pyproject.toml: {sorted(trovati - elencati)}; "
        f"elencati ma inesistenti: {sorted(elencati - trovati)}")


def test_il_comando_legatoria_punta_a_una_funzione_che_esiste():
    modulo, _, funzione = pyproject()["project"]["scripts"]["legatoria"].partition(":")
    assert callable(getattr(importlib.import_module(modulo), funzione))


def test_la_versione_dinamica_esiste_ed_e_ben_formata():
    attr = pyproject()["tool"]["setuptools"]["dynamic"]["version"]["attr"]
    modulo, _, nome = attr.rpartition(".")
    versione = getattr(importlib.import_module(modulo), nome)
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[.\-+]?[A-Za-z0-9.]+)?", versione), versione


def test_la_versione_minima_di_python_e_la_stessa_ovunque():
    minimo = re.fullmatch(r">=(\d+\.\d+)", pyproject()["project"]["requires-python"])
    assert minimo, "requires-python non e' nella forma '>=X.Y'"
    minimo = minimo.group(1)
    readme = (RADICE / "README.md").read_text(encoding="utf-8")
    assert f"Python {minimo} o più recente" in readme, f"il README non dice piu' 'Python {minimo} o più recente'"
    workflow = (RADICE / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    assert f'python: "{minimo}"' in workflow, f"il workflow non prova piu' Python {minimo}"


def test_i_file_citati_dal_pyproject_esistono():
    p = pyproject()
    assert (RADICE / p["project"]["readme"]).is_file()
    for f in p["project"]["license-files"]:
        assert (RADICE / f).is_file()
    for d in p["tool"]["pytest"]["ini_options"]["testpaths"]:
        assert (RADICE / d).is_dir()


def test_la_licenza_dichiarata_corrisponde_al_file():
    assert pyproject()["project"]["license"] == "MIT"
    assert (RADICE / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")
