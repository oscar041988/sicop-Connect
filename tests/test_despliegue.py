"""Plantillas de systemd (lección 8, encargo B): que los comandos existan y el ciclo empiece en dry-run.

No reemplaza `systemd-analyze verify` en el servidor (guía 17.5): solo atrapa errores antes de llegar ahí.
"""

import configparser
import shlex
from pathlib import Path

import pytest

from app.cli import build_parser

SYSTEMD = Path(__file__).resolve().parent.parent / "deploy" / "systemd"
UNIDADES = ("sicop-web.service", "sicop-migrate.service", "sicop-cycle.service", "sicop-cycle.timer")


def _leer(nombre):
    unidad = configparser.ConfigParser(interpolation=None, strict=False)
    unidad.optionxform = str  # systemd distingue mayúsculas
    unidad.read(SYSTEMD / nombre, encoding="utf-8")
    return unidad


def test_estan_las_cuatro_unidades_con_fin_de_linea_lf():
    for nombre in UNIDADES:
        assert b"\r\n" not in (SYSTEMD / nombre).read_bytes(), f"{nombre} tiene CRLF: systemd lo leería mal"


@pytest.mark.parametrize("nombre", [n for n in UNIDADES if n.endswith(".service")])
def test_servicios_sin_root_con_la_configuracion_privada(nombre):
    servicio = _leer(nombre)["Service"]
    assert (servicio["User"], servicio["Group"]) == ("sicop", "sicop")
    assert servicio["EnvironmentFile"] == "/etc/sicop-connect/app.env"
    assert servicio["UMask"] == "0077"
    assert "--reload" not in servicio["ExecStart"]


@pytest.mark.parametrize("nombre", ["sicop-migrate.service", "sicop-cycle.service"])
def test_el_comando_de_la_cli_existe(nombre):
    partes = shlex.split(_leer(nombre)["Service"]["ExecStart"])
    assert partes[:3] == ["/opt/sicop-connect/.venv/bin/python", "-m", "app.cli"]
    build_parser().parse_args(partes[3:])   # falla si el comando o sus opciones no existen


def test_el_ciclo_empieza_en_dry_run_con_datos_reales():
    args = build_parser().parse_args(shlex.split(_leer("sicop-cycle.service")["Service"]["ExecStart"])[3:])
    assert (args.command, args.origen, args.dry_run, args.send) == ("run-cycle", "real", True, False)


def test_el_timer_es_de_lunes_a_viernes_a_las_8_de_costa_rica():
    timer = _leer("sicop-cycle.timer")["Timer"]
    assert timer["OnCalendar"] == "Mon..Fri *-*-* 08:00:00 America/Costa_Rica"
    assert (timer["Persistent"], timer["Unit"]) == ("false", "sicop-cycle.service")


def test_el_panel_solo_escucha_dentro_del_servidor():
    exec_start = _leer("sicop-web.service")["Service"]["ExecStart"]
    assert "--host 127.0.0.1" in exec_start and "--workers 1" in exec_start
