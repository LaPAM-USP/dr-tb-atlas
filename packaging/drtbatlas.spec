# PyInstaller spec for the DR-TBAtlas desktop app.
#
# Build from the repository root with:
#     pip install -r requirements.txt -r packaging/requirements-build.txt
#     pyinstaller packaging/drtbatlas.spec
#
# The result is dist/DR-TBAtlas/ (Windows and Linux) or dist/DR-TBAtlas.app
# (macOS). PyInstaller cannot cross-compile, so each platform is built on its
# own machine; .github/workflows/release.yml does this on GitHub Actions.

import os
import sys

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

ROOT = os.path.dirname(SPECPATH)
APP_NAME = "DR-TBAtlas"

# Generated at runtime into the user's cache (see launcher.py), never bundled.
DATA_EXCLUDES = {"tracks", "h37rv.prokaryote.gff3"}

datas = [(os.path.join(ROOT, "assets"), "assets")]
for name in sorted(os.listdir(os.path.join(ROOT, "data"))):
    if name not in DATA_EXCLUDES and not name.startswith("."):
        datas.append((os.path.join(ROOT, "data", name), "data"))

# Dash serves the JavaScript and CSS shipped inside these packages.
for package in ("dash", "dash_bootstrap_components", "dash_jbrowse"):
    datas += collect_data_files(package)
datas += copy_metadata("dash")

a = Analysis(
    [os.path.join(ROOT, "launcher.py")],
    pathex=[ROOT],
    datas=datas,
    hiddenimports=["app"],
    excludes=["pytest", "gunicorn", "IPython", "matplotlib", "PIL"],
)
pyz = PYZ(a.pure)

icon = os.path.join(ROOT, "assets", "icon.png")

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    console=False,
    icon=icon,
)
coll = COLLECT(exe, a.binaries, a.datas, name=APP_NAME)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=icon,
        bundle_identifier="br.usp.lapam.drtbatlas",
        info_plist={"NSHighResolutionCapable": True},
    )
