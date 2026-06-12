# genre_definitions.py
# UFULU RODEC EDITION – Definiciones centralizadas de géneros y rangos
# ------------------------------------------------------------------
# Para cambiar los géneros o los rangos de BPM solo hay que editar este archivo.
# Los demás módulos lo importan y se actualizan automáticamente.

# --- LISTA DE GÉNEROS (8 estilos del clasificador CLAP+SVM) ---
ESTILOS_UFULU = [
    "3-Step",
    "Bacardi",
    "Kwaito Amapiano",
    "Private school amapiano",
    "Quantum sound",
    "Sgija",
    "Sgubhu",
    "Tech amapiano",
]

# --- RANGOS DE BPM POR ESTILO (PARA LA ALERTA DE COHERENCIA) ---
# Basados en investigación de rangos típicos de cada subgénero Amapiano.
# Formato: "Estilo": (BPM_mínimo, BPM_máximo)
RANGOS_BPM = {
    "3-Step":                   (112, 122),
    "Bacardi":                  (110, 118),
    "Kwaito Amapiano":          (106, 118),
    "Private school amapiano":  (106, 116),
    "Quantum sound":            (108, 116),
    "Sgija":                    (112, 120),
    "Sgubhu":                   (118, 132),
    "Tech amapiano":            (120, 128),
}