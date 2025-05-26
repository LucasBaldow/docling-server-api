import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
from app.converter import converter_site, gerar_nome_arquivo_url

if __name__ == "__main__":
    url = "https://selektocapital.com.br/"
    resultado = converter_site(url)
    
    nome_json = gerar_nome_arquivo_url(url)
    with open(nome_json, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    
    print(f"Processamento concluído. Resultado salvo em {nome_json}")
