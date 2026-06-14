"""Tests de la aserción semántica del nivel agente.

Demuestran que corrige la rigidez cosmética PERO sigue cazando errores reales:
diferencia al centavo, fila faltante, fila de más significativa y fuga de RBAC.
Si alguno de estos NO fallara, el runner estaría mal.
"""

from app.evals.runner import coincide_semantico

# --- tolerancia cosmética (debe COINCIDIR) ----------------------------------


def test_tolera_columna_de_contexto_extra() -> None:
    # Pedido: solo el saldo. Obtenido: saldo + moneda (contexto).
    assert coincide_semantico([["1750.00"]], [["1750.00", "USD"]])


def test_order_insensitive_entre_filas_y_dentro_de_fila() -> None:
    esperado = [["ACME", "300.00"], ["GLOBEX", "700.00"]]
    obtenido = [["GLOBEX", "USD", "700.00"], ["300.00", "ACME"]]
    assert coincide_semantico(esperado, obtenido)


def test_valor_unico_con_columnas_extra() -> None:
    assert coincide_semantico([["500.00"]], [["15000.00", "14500.00", "500.00"]])


# --- poder de detección (debe FALLAR) ---------------------------------------


def test_falla_si_un_valor_difiere_al_centavo() -> None:
    assert not coincide_semantico([["1750.00"]], [["1750.01", "USD"]])


def test_falla_si_falta_una_fila() -> None:
    esperado = [["ACME"], ["GLOBEX"]]
    assert not coincide_semantico(esperado, [["ACME", "F-3"]])


def test_falla_si_hay_una_fila_de_mas_significativa() -> None:
    # El agente devolvió un cliente que no corresponde (cambia el significado).
    esperado = [["GLOBEX", "3500.00"]]
    obtenido = [["GLOBEX", "3500.00"], ["INITECH", "300.00"]]
    assert not coincide_semantico(esperado, obtenido)


def test_falla_ante_fuga_de_rbac() -> None:
    # Usuario MX: solo deben verse clientes de MX. Una fila de CO REPRUEBA.
    esperado = [["GLOBEX", "3500.00"], ["ACME", "1750.00"], ["INITECH", "300.00"]]
    con_fuga_co = [
        ["GLOBEX", "3500.00"],
        ["ACME", "1750.00"],
        ["INITECH", "300.00"],
        ["CONACO", "1600.00"],  # dato de Colombia: fuera de alcance
    ]
    assert not coincide_semantico(esperado, con_fuga_co)


def test_falla_si_falta_un_valor_dentro_de_la_fila() -> None:
    # Se pide cliente y saldo; el obtenido trae el saldo correcto pero otro cliente.
    assert not coincide_semantico([["ACME", "1750.00"]], [["GLOBEX", "1750.00"]])
