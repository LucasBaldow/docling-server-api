from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import shutil
import os
import zipfile
import json
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
from converter import converter_arquivo, processar_pasta, converter_site, gerar_nome_arquivo_url


app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Olá, mundo!"} 

# Endpoint para um único arquivo
@app.post("/upload-file/")
async def upload_file(file: UploadFile = File(...)):
    print(f"Arquivo recebido: {file.filename}")  # Verifica se o arquivo foi realmente recebido
    try:
        temp_file = f"temp_{file.filename}"
        print(f"Arquivo recebido: {file.filename}")  # Log do nome do arquivo
        print(f"Extensão do arquivo: {file.filename.split('.')[-1]}")  # Log da extensão
        
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        resultado = converter_arquivo(temp_file)
        json_file = temp_file + ".json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        
        return FileResponse(json_file, filename=os.path.basename(json_file))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar o arquivo: {e}")


@app.post("/upload-zip/")
async def upload_zip(zip_file: UploadFile = File(...)):
    try:
        # 1) Salvar o ZIP recebido
        temp_zip = "temp_upload.zip"
        with open(temp_zip, "wb") as buf:
            shutil.copyfileobj(zip_file.file, buf)

        # 2) Extrair tudo em temp_folder
        temp_folder = "temp_folder"
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)
        os.makedirs(temp_folder)
        with zipfile.ZipFile(temp_zip, "r") as zf:
            zf.extractall(temp_folder)

        # 3) Processar recursivamente e obter {relpath: resultado}
        resultados = processar_pasta(temp_folder)

        # 4) Preparar pasta de saída (flat)
        output_folder = "output_jsons"
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        os.makedirs(output_folder)

        # 5) Para cada item, gravar JSON no nível raiz, usando só o nome-base do arquivo
        for relpath, conteudo in resultados.items():
            # ignora qualquer subpasta: pega apenas o nome do arquivo
            nome_original = os.path.basename(relpath)  
            base, _ = os.path.splitext(nome_original)
            json_name = f"{base}.json"
            json_path = os.path.join(output_folder, json_name)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(conteudo, f, ensure_ascii=False, indent=2)

        # 6) Zipar todos os JSONs (flat)
        output_zip = "resultados_json.zip"
        if os.path.exists(output_zip):
            os.remove(output_zip)
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(output_folder):
                zf.write(os.path.join(output_folder, fname), arcname=fname)

        # 7) Retornar o ZIP final para download
        return FileResponse(output_zip, filename=output_zip)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar o arquivo ZIP: {e}")




# Endpoint para URL
@app.post("/process-url/")
async def process_url(url: str):
    try:
        resultado = converter_site(url)
        nome_json = gerar_nome_arquivo_url(url)
        with open(nome_json, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        
        return FileResponse(nome_json, filename=nome_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar a URL: {e}")
