#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 Construcción de Subconjuntos (Subset Construction)
 SI2002 - Formal Languages - Assignment 2
 Basado en: Kozen, Dexter C. (1997). "Automata and Computability", Lecture 6.
================================================================================

¿QUÉ HACE ESTE PROGRAMA?
-------------------------
Recibe la descripción de uno o varios NFA (autómatas finitos no deterministas)
y, para cada uno, calcula el DFA (autómata finito determinista) equivalente
usando el algoritmo de Construcción de Subconjuntos.

¿CÓMO SE USA?
-------------
Por consola (leyendo lo que el usuario escriba o pegue):
    python3 subset_construction.py

Redirigiendo un archivo por la entrada estándar (modo "batch" / evaluación):
    python3 subset_construction.py < entrada.txt

Indicando el archivo de entrada explícitamente (modo "subir archivo"):
    python3 subset_construction.py -i entrada.txt

Guardando el resultado en un archivo de salida:
    python3 subset_construction.py -i entrada.txt -o salida.txt

Generando además diagramas en formato Graphviz (.dot) de cada DFA resultante
(función extra opcional mencionada en el enunciado):
    python3 subset_construction.py -i entrada.txt --dot diagramas.dot

Ver también COMO_EJECUTAR.md para una guía paso a paso mucho más detallada.

IMPORTANTE: cuando la entrada viene de un archivo o de una tubería (pipe),
el programa NO imprime menús ni mensajes adicionales: solo imprime el
resultado exigido por el enunciado ("Do not print extra lines"). El menú
interactivo solo aparece cuando se ejecuta directamente en una terminal
sin redirigir nada.
"""

import sys
import os
import re
import argparse
from collections import deque

# --------------------------------------------------------------------------
# 1. UTILIDADES DE TOKENIZACIÓN Y PARSEO
# --------------------------------------------------------------------------
#
# El reto de parsear la entrada es que un conjunto de estados se escribe
# como "{1 5}" -> es decir, CON ESPACIOS ADENTRO DE LAS LLAVES. Si uno separa
# la línea simplemente por espacios (str.split()), "{1 5}" se rompe en dos
# pedazos: "{1" y "5}". Para evitar ese error, usamos una expresión regular
# que reconoce como "un solo token" o bien:
#   (a) un grupo completo entre llaves "{ ... }" (sin importar los espacios
#       que tenga adentro), o
#   (b) una secuencia de caracteres sin espacios (por ejemplo "0" o "3").
#
# Así, tokenizar "1 {1 5} 0" da exactamente: ["1", "{1 5}", "0"]

TOKEN_RE = re.compile(r"\{[^}]*\}|\S+")


def tokenizar(linea: str):
    """Separa una línea de texto en tokens, respetando los grupos {a b c}."""
    return TOKEN_RE.findall(linea)


def parsear_conjunto(token: str) -> frozenset:
    """
    Convierte un token en un conjunto (frozenset) de enteros.

    - "0"      -> frozenset()               (conjunto vacío, según el enunciado)
    - "{1 5}"  -> frozenset({1, 5})
    - "{}"     -> frozenset()                (por robustez, llaves vacías también
                                               se tratan como conjunto vacío)
    """
    token = token.strip()
    if token == "0":
        return frozenset()
    if not (token.startswith("{") and token.endswith("}")):
        raise ValueError(
            f"Token de transición inválido: '{token}'. "
            "Se esperaba '0' o un conjunto tipo '{1 5}'."
        )
    interior = token[1:-1].strip()
    if interior == "":
        return frozenset()
    # Aceptamos tanto espacios como comas como separadores, por si el
    # archivo de entrada usa la notación con comas mostrada en el enunciado
    # (p. ej. "{1, 5}") en lugar de la notación sin comas del ejemplo real
    # de datos (p. ej. "{1 5}").
    partes = re.split(r"[\s,]+", interior)
    return frozenset(int(p) for p in partes if p != "")


class LectorDeLineas:
    """
    Envoltorio simple sobre el texto de entrada que entrega una línea "útil"
    cada vez que se le pide. Se descartan líneas completamente vacías para
    dar algo de tolerancia a espacios en blanco accidentales en el archivo
    de entrada, sin cambiar en nada el contenido real de los datos.
    """

    def __init__(self, texto: str):
        self._lineas = [l for l in texto.splitlines() if l.strip() != ""]
        self._pos = 0

    def siguiente(self) -> str:
        if self._pos >= len(self._lineas):
            raise ValueError(
                "Entrada incompleta: se esperaban más líneas de las que se "
                "recibieron. Revisa el formato del archivo de entrada."
            )
        linea = self._lineas[self._pos]
        self._pos += 1
        return linea


# --------------------------------------------------------------------------
# 2. LECTURA DE UN NFA (UN CASO) DESDE LA ENTRADA
# --------------------------------------------------------------------------

def leer_nfa(lector: LectorDeLineas):
    """
    Lee un NFA completo (un caso) desde el lector de líneas, siguiendo
    exactamente el formato del enunciado:

        n                      -> número de estados (estados = 1..n)
        s1 s2 ... sk           -> estados iniciales S
        a b c ...              -> alfabeto (en el orden que se usará luego)
        f1 f2 ... fm           -> estados finales F
        <n líneas de tabla>    -> una por estado, en orden 1..n

    Devuelve: (n, S, alfabeto, F, delta)
      - delta es un diccionario: delta[estado][simbolo] = frozenset(destinos)
    """
    n = int(lector.siguiente().strip())

    S = [int(x) for x in lector.siguiente().split()]
    alfabeto = lector.siguiente().split()
    F = set(int(x) for x in lector.siguiente().split())

    delta = {}
    for _ in range(n):
        fila = tokenizar(lector.siguiente())
        if len(fila) != len(alfabeto) + 1:
            raise ValueError(
                f"Fila de transición inválida: se esperaban "
                f"{len(alfabeto) + 1} columnas (estado + {len(alfabeto)} "
                f"símbolos) pero se encontraron {len(fila)} en: {fila}"
            )
        estado = int(fila[0])
        delta[estado] = {}
        for simbolo, token in zip(alfabeto, fila[1:]):
            delta[estado][simbolo] = parsear_conjunto(token)

    return n, S, alfabeto, F, delta


# --------------------------------------------------------------------------
# 3. EL ALGORITMO: CONSTRUCCIÓN DE SUBCONJUNTOS
# --------------------------------------------------------------------------

def construccion_de_subconjuntos(S, alfabeto, F, delta):
    """
    Implementa el algoritmo de Kozen (Lecture 6):

        Q'      = subconjuntos de Q alcanzables desde S
        q0'     = S                                   (el conjunto S completo)
        delta'(A, a) = unión de delta(q, a) para cada q en A
        F'      = { A en Q' : A ∩ F ≠ ∅ }

    Solo se generan y numeran los subconjuntos que son REALMENTE alcanzables
    (búsqueda en anchura desde el estado inicial), no las 2^n combinaciones
    posibles. El conjunto vacío, si aparece, se convierte en un estado
    "trampa" (sink state) con auto-transición en todos los símbolos, para
    que el DFA resultante sea completo (función de transición total).

    Devuelve:
      - id_inicial      : id (entero, 1-based) del estado inicial del DFA
      - lista_estados   : lista de frozensets; lista_estados[i-1] es el
                           subconjunto de estados NFA que representa el
                           estado "i" del DFA
      - transiciones    : dict  transiciones[id][simbolo] = id_destino
      - finales         : conjunto de ids que son estados finales del DFA
    """
    inicial = frozenset(S)

    lista_estados = []          # índice 0 -> id 1, índice 1 -> id 2, ...
    id_de_conjunto = {}         # frozenset -> id (1-based)
    transiciones = {}           # id -> {simbolo: id_destino}

    def obtener_id(conjunto: frozenset) -> int:
        """Devuelve el id ya asignado a 'conjunto', o le asigna uno nuevo."""
        if conjunto not in id_de_conjunto:
            id_de_conjunto[conjunto] = len(lista_estados) + 1
            lista_estados.append(conjunto)
        return id_de_conjunto[conjunto]

    id_inicial = obtener_id(inicial)

    cola = deque([inicial])
    descubiertos = {inicial}

    while cola:
        actual = cola.popleft()
        id_actual = id_de_conjunto[actual]
        transiciones[id_actual] = {}

        for simbolo in alfabeto:
            # delta'(actual, simbolo) = unión de delta(q, simbolo) para q en 'actual'
            piezas = [delta.get(q, {}).get(simbolo, frozenset()) for q in actual]
            destino = frozenset().union(*piezas) if piezas else frozenset()

            id_destino = obtener_id(destino)
            transiciones[id_actual][simbolo] = id_destino

            if destino not in descubiertos:
                descubiertos.add(destino)
                cola.append(destino)

    finales = {
        id_ for conjunto, id_ in id_de_conjunto.items() if conjunto & F
    }

    return id_inicial, lista_estados, transiciones, finales


# --------------------------------------------------------------------------
# 4. FORMATO DE SALIDA
# --------------------------------------------------------------------------
#
# El enunciado deja libre el formato exacto de salida (solo exige mostrar
# la tabla de M, indicar el estado inicial y los finales, y "no imprimir
# líneas de más"). Para que la salida sea clara, verificable a mano y
# fácil de re-usar, se adopta un formato QUE ESPEJA el formato de entrada:
#
#   n_dfa                   -> número de estados del DFA
#   id_inicial               -> UN solo estado inicial (ya es determinista)
#   a b ...                  -> mismo alfabeto, mismo orden
#   f1 f2 ...  (o "0")       -> estados finales del DFA (o "0" si no hay)
#   n_dfa líneas de tabla    -> "id  destino_a  destino_b ..." (sin llaves,
#                                porque en un DFA cada destino es UN solo
#                                estado, nunca un conjunto)
#
# Esta decisión de diseño se explica en el README y en la guía de
# sustentación.

def formatear_salida(id_inicial, lista_estados, transiciones, finales, alfabeto):
    n_dfa = len(lista_estados)
    lineas = []
    lineas.append(str(n_dfa))
    lineas.append(str(id_inicial))
    lineas.append(" ".join(alfabeto))

    finales_ordenados = sorted(finales)
    lineas.append(" ".join(str(f) for f in finales_ordenados) if finales_ordenados else "0")

    for id_ in range(1, n_dfa + 1):
        fila = [str(id_)]
        for simbolo in alfabeto:
            fila.append(str(transiciones[id_][simbolo]))
        lineas.append(" ".join(fila))

    return "\n".join(lineas)


# --------------------------------------------------------------------------
# 4-bis. VERSIÓN "LEGIBLE PARA HUMANOS" (solo para que el estudiante
#        entienda su propia salida — NO reemplaza el formato oficial)
# --------------------------------------------------------------------------
#
# El formato oficial (formatear_salida) es intencionalmente "seco" — sin
# etiquetas de texto — porque el enunciado exige "no imprimir líneas de
# más" y un corrector automático espera un formato fijo, línea por línea.
#
# Esta función NO cambia ni reemplaza ese formato oficial: solo genera,
# de manera opcional (bandera --legible), una explicación en español de
# qué representa cada número, para que el propio estudiante pueda revisar
# o sustentar su resultado sin tener que "traducir" el formato a mano.

def _texto_conjunto(conjunto: frozenset) -> str:
    """Muestra un frozenset como texto legible, p. ej. {1, 2, 4} o ∅."""
    if not conjunto:
        return "∅"
    return "{" + ", ".join(str(x) for x in sorted(conjunto)) + "}"


def formatear_legible(caso_num, id_inicial, lista_estados, transiciones, finales, alfabeto):
    n_dfa = len(lista_estados)
    finales_ordenados = sorted(finales)

    lineas = []
    lineas.append("=" * 70)
    lineas.append(f" CASO {caso_num} — Autómata Determinista (DFA) resultante")
    lineas.append("=" * 70)
    lineas.append(f"Número de estados del DFA : {n_dfa}")
    lineas.append(
        f"Estado inicial            : {id_inicial}  "
        f"(equivale al conjunto {_texto_conjunto(lista_estados[id_inicial - 1])} del NFA original)"
    )
    lineas.append(f"Alfabeto                  : {', '.join(alfabeto)}")
    if finales_ordenados:
        lineas.append(
            f"Estado(s) final(es)       : {', '.join(str(f) for f in finales_ordenados)}"
        )
    else:
        lineas.append("Estado(s) final(es)       : (ninguno)")
    lineas.append("")
    lineas.append("Tabla de transiciones:")

    for id_ in range(1, n_dfa + 1):
        conjunto = lista_estados[id_ - 1]
        etiquetas = []
        if id_ == id_inicial:
            etiquetas.append("INICIAL")
        if id_ in finales:
            etiquetas.append("FINAL")
        if not conjunto:
            etiquetas.append("TRAMPA/∅")
        sufijo_etiquetas = f"  [{', '.join(etiquetas)}]" if etiquetas else ""

        destinos = "   ".join(
            f"--{simbolo}--> {transiciones[id_][simbolo]}" for simbolo in alfabeto
        )
        lineas.append(
            f"  Estado {id_:<3} (conjunto NFA {_texto_conjunto(conjunto)}){sufijo_etiquetas}"
        )
        lineas.append(f"      {destinos}")

    lineas.append("")
    return "\n".join(lineas)


# --------------------------------------------------------------------------
# 5. FUNCIÓN EXTRA (OPCIONAL): DIAGRAMA EN FORMATO GRAPHVIZ (.dot)
# --------------------------------------------------------------------------
#
# El enunciado menciona como característica OPCIONAL la posibilidad de
# imprimir los autómatas como diagramas. Aquí se genera una representación
# en formato Graphviz DOT, que se puede visualizar en línea (por ejemplo en
# https://dreampuf.github.io/GraphvizOnline/) o con la herramienta `dot`
# instalada localmente: `dot -Tpng diagramas.dot -o diagramas.png`

def generar_dot(caso_num, id_inicial, lista_estados, transiciones, finales, alfabeto):
    lineas = [f"digraph DFA_caso_{caso_num} {{", "  rankdir=LR;"]
    lineas.append('  nodo_ficticio [shape=point];')
    lineas.append(f"  nodo_ficticio -> {id_inicial};")

    for id_ in range(1, len(lista_estados) + 1):
        forma = "doublecircle" if id_ in finales else "circle"
        etiqueta = "{" + ",".join(str(x) for x in sorted(lista_estados[id_ - 1])) + "}"
        lineas.append(f'  {id_} [shape={forma}, label="{id_}\\n{etiqueta}"];')

    for id_ in range(1, len(lista_estados) + 1):
        for simbolo in alfabeto:
            destino = transiciones[id_][simbolo]
            lineas.append(f'  {id_} -> {destino} [label="{simbolo}"];')

    lineas.append("}")
    return "\n".join(lineas)


# --------------------------------------------------------------------------
# 6. ORQUESTACIÓN: RESOLVER TODOS LOS CASOS DE UNA ENTRADA
# --------------------------------------------------------------------------

def resolver_entrada(texto_entrada: str):
    """
    Lee y resuelve TODOS los casos de la entrada, aplicando la construcción
    de subconjuntos a cada uno.

    Devuelve una lista de "casos resueltos", donde cada elemento es una
    tupla con toda la información cruda necesaria para luego generar
    cualquiera de los formatos de salida (oficial, legible, .dot):

        (caso_num, id_inicial, lista_estados, transiciones, finales, alfabeto)

    Separar "resolver" de "formatear" permite generar varias
    representaciones distintas (la oficial, la legible para humanos, y el
    diagrama .dot) a partir de un único cálculo, sin repetir el algoritmo.
    """
    lector = LectorDeLineas(texto_entrada)
    c = int(lector.siguiente().strip())

    casos_resueltos = []

    for caso_num in range(1, c + 1):
        n, S, alfabeto, F, delta = leer_nfa(lector)
        id_inicial, lista_estados, transiciones, finales = construccion_de_subconjuntos(
            S, alfabeto, F, delta
        )
        casos_resueltos.append(
            (caso_num, id_inicial, lista_estados, transiciones, finales, alfabeto)
        )

    return casos_resueltos


# --------------------------------------------------------------------------
# 7. INTERFAZ DE LÍNEA DE COMANDOS / MENÚ INTERACTIVO
# --------------------------------------------------------------------------

def menu_interactivo():
    """
    Menú simple que solo se muestra cuando el programa se ejecuta
    directamente en una terminal (sin redirigir la entrada ni pasar -i).
    Permite elegir entre escribir/pegar la entrada a mano o indicar la
    ruta de un archivo.
    """
    print("=" * 70)
    print(" Construcción de Subconjuntos (NFA -> DFA) ")
    print("=" * 70)
    print("¿Cómo deseas dar la entrada?")
    print("  1) Escribir o pegar la entrada manualmente en la consola")
    print("  2) Indicar la ruta de un archivo de entrada")
    opcion = input("Elige una opción (1/2): ").strip()

    if opcion == "2":
        ruta = input("Ruta del archivo de entrada: ").strip()
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    else:
        print("Pega o escribe la entrada. Termina con una línea que contenga solo EOF:")
        lineas = []
        while True:
            try:
                linea = input()
            except EOFError:
                break
            if linea.strip() == "EOF":
                break
            lineas.append(linea)
        return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser(
        description="Construcción de Subconjuntos: convierte un NFA en un DFA equivalente."
    )
    parser.add_argument(
        "-i", "--input", dest="archivo_entrada", default=None,
        help="Ruta del archivo de entrada. Si se omite, se lee de la entrada estándar "
             "(o se muestra un menú si se ejecuta en una terminal interactiva)."
    )
    parser.add_argument(
        "-o", "--output", dest="archivo_salida", default=None,
        help="Ruta del archivo donde escribir el resultado. Si se omite, se imprime "
             "por la salida estándar."
    )
    parser.add_argument(
        "--dot", dest="archivo_dot", default=None,
        help="(Opcional) Ruta del archivo .dot donde guardar los diagramas Graphviz "
             "de los DFA resultantes."
    )
    parser.add_argument(
        "--legible", dest="archivo_legible", nargs="?", const="__CONSOLA__",
        default=None,
        help="(Opcional) Muestra ADEMÁS una versión explicada en español, con "
             "etiquetas, del estado inicial, los finales y la tabla de "
             "transiciones (no reemplaza el formato oficial exigido por el "
             "enunciado). Si se usa sin valor, se imprime en pantalla después "
             "del resultado oficial. Si se le da una ruta (--legible salida.txt), "
             "se guarda en ese archivo en vez de imprimirse."
    )
    args = parser.parse_args()

    # --- Obtener el texto de entrada ---
    if args.archivo_entrada:
        with open(args.archivo_entrada, "r", encoding="utf-8") as f:
            texto_entrada = f.read()
    elif not sys.stdin.isatty():
        # La entrada viene redirigida desde un archivo o una tubería (pipe):
        # NO se muestra ningún menú ni mensaje, solo se procesa y se imprime
        # el resultado (requisito de "no imprimir líneas de más").
        texto_entrada = sys.stdin.read()
    else:
        # Se está ejecutando directamente en una terminal: se ofrece el menú.
        texto_entrada = menu_interactivo()

    # --- Resolver (un único cálculo, reutilizado para todos los formatos) ---
    try:
        casos_resueltos = resolver_entrada(texto_entrada)
    except Exception as e:
        # Cualquier error de formato se reporta de forma clara y se detiene
        # el programa con código de salida distinto de 0.
        sys.stderr.write(f"Error al procesar la entrada: {e}\n")
        sys.exit(1)

    # --- Formato OFICIAL (el que exige el enunciado) ---
    resultados_oficiales = [
        formatear_salida(id_inicial, lista_estados, transiciones, finales, alfabeto)
        for (_, id_inicial, lista_estados, transiciones, finales, alfabeto) in casos_resueltos
    ]
    salida_final = "\n".join(resultados_oficiales)

    if args.archivo_salida:
        with open(args.archivo_salida, "w", encoding="utf-8") as f:
            f.write(salida_final + "\n")
    else:
        print(salida_final)

    # --- Formato LEGIBLE (opcional, solo para entender/sustentar) ---
    if args.archivo_legible:
        textos_legibles = [
            formatear_legible(caso_num, id_inicial, lista_estados, transiciones, finales, alfabeto)
            for (caso_num, id_inicial, lista_estados, transiciones, finales, alfabeto) in casos_resueltos
        ]
        salida_legible = "\n".join(textos_legibles)

        if args.archivo_legible == "__CONSOLA__":
            print()  # línea en blanco para separar visualmente de lo oficial
            print(salida_legible)
        else:
            with open(args.archivo_legible, "w", encoding="utf-8") as f:
                f.write(salida_legible + "\n")

    # --- Escribir los diagramas .dot, si se pidieron ---
    if args.archivo_dot:
        diagramas_dot = [
            generar_dot(caso_num, id_inicial, lista_estados, transiciones, finales, alfabeto)
            for (caso_num, id_inicial, lista_estados, transiciones, finales, alfabeto) in casos_resueltos
        ]
        with open(args.archivo_dot, "w", encoding="utf-8") as f:
            f.write("\n\n".join(diagramas_dot) + "\n")


if __name__ == "__main__":
    main()