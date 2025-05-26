import os
import json
from docling.document_converter import DocumentConverter
import pandas as pd
from urllib.parse import urlparse

def converter_site(url):
    converter = DocumentConverter()
    try:
        result = converter.convert(url)
        doc_dict = result.document.export_to_dict()
        texts = []
        for item in doc_dict.get("texts", []):
            text_content = item.get("text")
            if text_content and text_content.strip():
                texts.append(text_content.strip())
        return {"texts": texts}
    except Exception as e:
        return {"error": f"Erro ao processar o site {url}: {e}"}

def gerar_nome_arquivo_url(url):
    hostname = urlparse(url).hostname
    if not hostname:
        hostname = "site_output"
    return f"{hostname}.json"


def get_file_ext(file):
    return os.path.splitext(file)[-1].lower()

def converter_arquivo(source):
    file_ext = get_file_ext(source)
    print(f"Extensão do arquivo: {file_ext}")
    saida = {}

    if file_ext in [".pdf", ".docx", ".pptx", ".md", ".adoc", ".asciidoc", ".html", ".xhtml", ".csv", ".png", ".jpeg", ".tiff", ".bmp", ".webp"]:
        converter = DocumentConverter()
        try:
            result = converter.convert(source)
            doc_dict = result.document.export_to_dict()
            texts = [t["text"] for t in doc_dict.get("texts", []) if "text" in t]
            saida = {"texts": texts}
        except Exception as e:
            saida = {"error": f"Erro ao processar documento (Docling): {e}"}

    elif file_ext == ".xlsx":
        try:
            excel = pd.ExcelFile(source)
            excel_data = {}
            for sheet in excel.sheet_names:
                df = pd.read_excel(source, sheet_name=sheet)
                excel_data[sheet] = df.to_dict(orient="records")
            saida = {"sheets": excel_data}
        except Exception as e:
            saida = {"error": f"Erro ao processar Excel: {e}"}

    else:
        saida = {"error": f"Formato de arquivo não suportado: {file_ext}"}

    return saida

def processar_pasta(pasta_path):
    resultados = {}

    # percorre recursivamente todas as subpastas
    for root, _, files in os.walk(pasta_path):
        for fname in files:
            caminho = os.path.join(root, fname)
            print(f"Processando arquivo: {caminho}")

            # chave no dict: caminho relativo dentro de pasta_path
            rel = os.path.relpath(caminho, pasta_path)
            resultados[rel] = converter_arquivo(caminho)

            # gravar o JSON ao lado do arquivo (opcional)
            nome_json_local = caminho + ".json"
            with open(nome_json_local, "w", encoding="utf-8") as f:
                json.dump(resultados[rel], f, ensure_ascii=False, indent=2)

    return resultados
