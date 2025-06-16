import os
import zipfile
import tempfile
import shutil
import json
from pathlib import Path
from backend.converter import converter_arquivo

# Script local para converter zips com muitos arquivos em json

def main():
    # 1) Define caminhos
    desktop = Path.home() / "Desktop"
    zip_name = "file.zip"
    zip_path = desktop / zip_name
    output_zip = desktop / "resultados_json.zip"

    if not zip_path.exists():
        print(f"❌ ZIP não encontrado em {zip_path}")
        return

    # 2) Pasta temporária para extração
    temp_dir = Path(tempfile.mkdtemp(prefix="docling_"))
    print(f"📂 Extraindo em {temp_dir}")

    # 3) Extrair tudo do ZIP
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(temp_dir)
    print("✅ Extração concluída.")

    # 4) Converter cada arquivo em JSON
    json_dir = temp_dir / "jsons"
    json_dir.mkdir(exist_ok=True)
    for file_path in temp_dir.rglob("*"):
        if file_path.is_file():
            try:
                print(f"🔄 Convertendo {file_path.name}...")
                result = converter_arquivo(str(file_path))
                json_path = json_dir / f"{file_path.stem}.json"
                with open(json_path, "w", encoding="utf-8") as jf:
                    json.dump(result, jf, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"⚠️ Erro em {file_path.name}: {e}")

    print(f"✅ Conversão concluída. JSONs em {json_dir}")

    # 5) Empacotar todos os JSONs num ZIP
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf_out:
        for json_file in json_dir.iterdir():
            zf_out.write(json_file, arcname=json_file.name)
    print(f"📦 Novo ZIP criado em {output_zip}")

    # 6) Limpar temporários
    shutil.rmtree(temp_dir)
    print("🧹 Limpeza concluída.")

if __name__ == "__main__":
    main()
