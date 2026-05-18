# Teleprom

Teleprom to prosta aplikacja telepromptera w Pythonie dla Windows i macOS.

Autor: Marek Zettel

## Funkcje

- modalne okno telepromptera z płynnym przewijaniem tekstu
- regulacja prędkości przewijania, marginesu i pozycji startowej
- wybór czcionki, rozmiaru czcionki, koloru tekstu i tła
- import plików `.txt`, `.srt`, `.md`, `.markdown`, `.docx`, `.rtf`
- wklejanie tekstu bezpośrednio do edytora
- pełny ekran, pauza, reset i ręczne przewijanie
- opcjonalne odbicie lustrzane tekstu

## Uruchomienie

W katalogu projektu uruchom:

```powershell
python teleprompter.py
```

## Instalacja i skrót na pulpicie

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows.ps1
```

Możesz też dwukrotnie kliknąć `install_windows.bat`.

Instalator tworzy środowisko `.venv`, instaluje zależności, generuje ikonę `assets\teleprom.ico`, tworzy skrót `Teleprom` na pulpicie i uruchamia aplikację.

macOS:

```bash
chmod +x install_macos.sh run_macos.command
./install_macos.sh
```

Instalator tworzy środowisko `.venv`, instaluje zależności, tworzy skrót `Teleprom.command` na pulpicie i uruchamia aplikację.

Na części systemów macOS komenda może mieć nazwę:

```bash
python3 teleprompter.py
```

## Import DOCX

Import `.docx` działa bez dodatkowych pakietów przez wbudowany odczyt XML.
Dla lepszego odczytu tabel i akapitów można opcjonalnie zainstalować:

```bash
pip install python-docx
```

## Skróty w oknie promptera

- `Spacja` - start/pauza
- `Home` - reset do początku
- `F11` - pełny ekran
- `Esc` - zamknięcie okna
- `Strzałki`, `Page Up`, `Page Down` lub kółko myszy - ręczne przewijanie

## Pakowanie do aplikacji

Najprostsza ścieżka pakowania to PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name Teleprom teleprompter.py
```

Gotowy plik znajdziesz w katalogu `dist`.

## Publikacja na GitHub

Jeśli masz token GitHuba z dostępem do `zetmar-collab`, ustaw go w `GITHUB_TOKEN` albo `GH_TOKEN`, a potem uruchom:

```powershell
.\publish_github.ps1
```

Skrypt tworzy repo `zetmar-collab/Teleprom`, wypycha kod, tworzy tag `v1.0.0`, zakłada release i dodaje `Teleprom.zip` jako plik wydania.
