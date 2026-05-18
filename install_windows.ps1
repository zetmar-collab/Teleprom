$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ProjectDir ".venv"
$AssetsDir = Join-Path $ProjectDir "assets"
$IconPath = Join-Path $AssetsDir "teleprom.ico"
$AppPath = Join-Path $ProjectDir "teleprompter.py"
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Teleprom.lnk"

function Get-PythonCommand {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @("py", "-3")
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @("python")
    }
    throw "Nie znaleziono Pythona. Zainstaluj Python 3 ze strony https://www.python.org/downloads/ i uruchom instalator ponownie."
}

function Write-TelepromIcon {
    param([string]$Path)

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null

    $width = 64
    $height = 64
    $xorSize = $width * $height * 4
    $andStride = [int]([Math]::Floor(($width + 31) / 32)) * 4
    $andSize = $andStride * $height
    $imageSize = 40 + $xorSize + $andSize

    $fs = [System.IO.File]::Create($Path)
    $bw = New-Object System.IO.BinaryWriter($fs)
    try {
        $bw.Write([UInt16]0)
        $bw.Write([UInt16]1)
        $bw.Write([UInt16]1)
        $bw.Write([byte]$width)
        $bw.Write([byte]$height)
        $bw.Write([byte]0)
        $bw.Write([byte]0)
        $bw.Write([UInt16]1)
        $bw.Write([UInt16]32)
        $bw.Write([UInt32]$imageSize)
        $bw.Write([UInt32]22)

        $bw.Write([UInt32]40)
        $bw.Write([Int32]$width)
        $bw.Write([Int32]($height * 2))
        $bw.Write([UInt16]1)
        $bw.Write([UInt16]32)
        $bw.Write([UInt32]0)
        $bw.Write([UInt32]$xorSize)
        $bw.Write([Int32]0)
        $bw.Write([Int32]0)
        $bw.Write([UInt32]0)
        $bw.Write([UInt32]0)

        for ($y = $height - 1; $y -ge 0; $y--) {
            for ($x = 0; $x -lt $width; $x++) {
                $r = 21; $g = 25; $b = 35
                $dx = $x - 32
                $dy = $y - 32
                if (($dx * $dx + $dy * $dy) -lt 900) {
                    $r = 32; $g = 40; $b = 51
                }
                if ($x -ge 13 -and $x -le 51 -and $y -ge 10 -and $y -le 54) {
                    $r = 244; $g = 244; $b = 238
                    if ($x -le 15 -or $x -ge 49 -or $y -le 12 -or $y -ge 52) {
                        $r = 32; $g = 178; $b = 170
                    }
                    elseif (($y -ge 21 -and $y -le 24) -or ($y -ge 31 -and $y -le 34) -or ($y -ge 41 -and $y -le 44)) {
                        if ($x -ge 22 -and $x -le 42) {
                            $r = 25; $g = 25; $b = 25
                        }
                    }
                }
                $bw.Write([byte]$b)
                $bw.Write([byte]$g)
                $bw.Write([byte]$r)
                $bw.Write([byte]255)
            }
        }

        for ($i = 0; $i -lt $andSize; $i++) {
            $bw.Write([byte]0)
        }
    }
    finally {
        $bw.Close()
        $fs.Close()
    }
}

Write-Host "Instaluję Teleprom..."
$pythonCommand = Get-PythonCommand

if (!(Test-Path $VenvDir)) {
    $pythonArgs = @()
    if ($pythonCommand.Length -gt 1) {
        $pythonArgs = $pythonCommand[1..($pythonCommand.Length - 1)]
    }
    & $pythonCommand[0] @($pythonArgs + @("-m", "venv", $VenvDir))
}

$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$PythonwExe = Join-Path $VenvDir "Scripts\pythonw.exe"
if (!(Test-Path $PythonwExe)) {
    $PythonwExe = $PythonExe
}

& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r (Join-Path $ProjectDir "requirements.txt")

Write-TelepromIcon -Path $IconPath

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $PythonwExe
$shortcut.Arguments = "`"$AppPath`""
$shortcut.WorkingDirectory = $ProjectDir
$shortcut.IconLocation = $IconPath
$shortcut.Description = "Teleprom - teleprompter autorstwa Marek Zettel"
$shortcut.Save()

Write-Host "Gotowe."
Write-Host "Skrót utworzony: $ShortcutPath"
Write-Host "Uruchamiam aplikację..."
Start-Process -FilePath $PythonwExe -ArgumentList "`"$AppPath`"" -WorkingDirectory $ProjectDir
