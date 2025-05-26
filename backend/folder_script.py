import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.converter import processar_pasta


if __name__ == "__main__":
    caminho_pasta = os.path.join("..", "folder_test") 
    resultado_final = processar_pasta(caminho_pasta)
    print(f"Processamento da pasta concluído. JSONs salvos na mesma pasta dos arquivos.")
