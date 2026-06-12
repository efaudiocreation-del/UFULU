# extraer_generos_clasificar.py
import re
text = open('clasificar.py', encoding='utf-8').read()
generos = re.findall(r'"(\w[\w ]+)":\s*\[', text)
print("Generos en clasificar.py:")
for g in generos:
    print(f"  - {g}")
