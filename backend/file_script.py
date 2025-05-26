import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from app.converter import converter_arquivo

if __name__ == "__main__":
    caminho_arquivo = os.path.join("..", "folder_test", "Cópia de Check in Oficial Disruption.xlsx")

    resultado = converter_arquivo(caminho_arquivo)

    pasta = os.path.dirname(caminho_arquivo)
    nome_base = os.path.splitext(os.path.basename(caminho_arquivo))[0]
    nome_json = os.path.join(pasta, nome_base + ".json")

    with open(nome_json, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"Arquivo processado e salvo em {nome_json}")
