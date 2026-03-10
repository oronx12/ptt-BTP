@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

echo.
echo ============================================================
echo   PTT BTP — Installation et lancement
echo ============================================================
echo.

:: ── Répertoire du script comme répertoire de travail ──────────────────────
cd /d "%~dp0"

:: ── Vérification Python ───────────────────────────────────────────────────
echo [1/5] Vérification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERREUR : Python n'est pas installé ou introuvable dans le PATH.
    echo  Téléchargez Python 3.11+ sur https://www.python.org/downloads/
    echo  Cochez "Add Python to PATH" lors de l'installation.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo    %%v détecté.

:: ── Création de l'environnement virtuel ──────────────────────────────────
echo.
echo [2/5] Environnement virtuel...
if exist "venv\Scripts\activate.bat" (
    echo    Environnement virtuel existant détecté — réutilisation.
) else (
    echo    Création de l'environnement virtuel...
    python -m venv venv
    if errorlevel 1 (
        echo  ERREUR : Impossible de créer l'environnement virtuel.
        pause
        exit /b 1
    )
    echo    Environnement virtuel créé.
)

:: ── Activation du venv ────────────────────────────────────────────────────
call venv\Scripts\activate.bat

:: ── Mise à jour de pip ───────────────────────────────────────────────────
echo.
echo [3/5] Mise à jour de pip...
python -m pip install --upgrade pip --quiet
echo    pip à jour.

:: ── Installation des dépendances ─────────────────────────────────────────
echo.
echo [4/5] Installation des dépendances (requirements.txt)...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo  ERREUR : L'installation des dépendances a échoué.
    echo  Vérifiez votre connexion internet et relancez setup.bat.
    pause
    exit /b 1
)
echo    Dépendances installées.

:: ── Création des répertoires nécessaires ─────────────────────────────────
if not exist "data\tmp" mkdir "data\tmp"

:: ── Vérification du fichier Excel modèle ─────────────────────────────────
echo.
echo [5/5] Vérification du fichier modèle Excel...
if exist "data\Projet_Routier_Topographie.xlsx" (
    echo    Fichier modèle trouvé : data\Projet_Routier_Topographie.xlsx
) else (
    echo.
    echo  ATTENTION : Fichier Excel modèle introuvable dans data\
    echo  Placez votre fichier dans : data\Projet_Routier_Topographie.xlsx
    echo  L'application démarrera mais les données Excel ne seront pas disponibles.
)

:: ── Lancement ─────────────────────────────────────────────────────────────
echo.
echo ============================================================
echo   Démarrage du serveur PTT BTP...
echo   → Ouvrez votre navigateur sur : http://localhost:5000
echo   → Appuyez sur CTRL+C pour arrêter le serveur
echo ============================================================
echo.

python run.py

echo.
echo Serveur arrêté.
pause
