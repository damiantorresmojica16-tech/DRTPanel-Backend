import json
import os
import shutil
from urllib.request import Request, urlopen

RELEASE_URL = "https://api.github.com/repos/damiantorresmojica16-tech/DRTPanel-Backend/releases/tags/v1.0.0"
REQUIRED_ASSETS = {
    "Archive_modificado.zip",
    "Nuevo Archivo WinRAR.rar",
    "shaders_P0K3UG2TfecMBhWMMV2Fu8ReudIk3D NEBLUSA EXCLUSIVE",
    "shaders.P0K3UG2TfecMBhWMMV~2Fu8ReudIk~3D RGB EXCLUSIVE",
    "shaders.P0K3UG2TfecMBhWMMV~2Fu8ReudIk~3D CUADROS EXCLUSIVE",
    "shaders.P0K3UG2TfecMBhWMMV~2Fu8ReudIk~3D CARNE EXCLUSIVE",
    "assetindexer.U6Zffc4YIR3DslNj3cXvYGAqz58~3D BODY DISIMULADO",
    "assetindexer.U6Zffc4YIR3DslNj3cXvYGAqz58~3D NECK",
    "assetindexer.U6Zffc4YIR3DslNj3cXvYGAqz58~3D HEAD",
    "assetindexer.U6Zffc4YIR3DslNj3cXvYGAqz58~3D AIM DRAG",
    "PERSONAJES.MP4",
    "RGB.MP4",
    "NEBLUSA.MP4",
    "CUADROS.MP4",
}


def main():
    request = Request(RELEASE_URL, headers={"User-Agent": "DRTPanel-Render-deploy"})
    with urlopen(request, timeout=30) as response:
        release = json.load(response)

    available = {asset["name"]: asset["browser_download_url"] for asset in release["assets"]}
    missing = REQUIRED_ASSETS - available.keys()
    if missing:
        raise RuntimeError(f"Faltan archivos en el release v1.0.0: {', '.join(sorted(missing))}")

    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    for name in sorted(REQUIRED_ASSETS):
        request = Request(available[name], headers={"User-Agent": "DRTPanel-Render-deploy"})
        destination = os.path.join(uploads_dir, name)
        with urlopen(request, timeout=120) as response, open(destination, "wb") as output:
            shutil.copyfileobj(response, output)


if __name__ == "__main__":
    main()
