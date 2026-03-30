#!/usr/bin/env python3
"""Sorteo de personas con probabilidades ponderadas."""
import numpy as np

personas = ['Juli', 'Sebas', 'Daniel', 'Isa', 'José', 'Tavo', 'Santi', 'Juanpa', 'Juan', 'Gise', 'Simón']
# Probabilidades iguales para todos
n = len(personas)
probs = np.ones(n) / n

def seleccionar_sin_repeticion(lista_personas, lista_probs, cantidad):
    seleccion1 = np.random.choice(lista_personas, size=cantidad, replace=False, p=lista_probs)
    seleccion2 = np.random.choice(lista_personas, size=cantidad, replace=False, p=lista_probs)
    return seleccion1, seleccion2

resultado = seleccionar_sin_repeticion(personas, probs, 3)
print("Selección de personas día 1:", list(resultado[0]))
print("Selección de personas día 2:", list(resultado[1]))
