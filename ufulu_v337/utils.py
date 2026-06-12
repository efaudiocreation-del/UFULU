# utils.py
# UFULU RODEC EDITION – Funciones auxiliares compartidas

def normalizar(texto):
    """
    Elimina tildes y convierte a mayúsculas para hacer
    comparaciones robustas (ej. DÍA -> DIA, Amapiano -> AMAPIANO).
    """
    if not texto:
        return ""
    texto = str(texto).upper()
    for tilde, sin_tilde in zip("ÁÉÍÓÚ", "AEIOU"):
        texto = texto.replace(tilde, sin_tilde)
    return texto.strip()