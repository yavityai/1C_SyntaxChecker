function Test-DockerEngine {
    try {
        docker info *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Assert-DockerReady {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw @"
Docker CLI не найден.

Установите Docker Desktop: https://www.docker.com/products/docker-desktop/
"@
    }

    if (Test-DockerEngine) {
        return
    }

    $pipeMissing = -not (Test-Path "\\.\pipe\dockerDesktopLinuxEngine")

    if ($pipeMissing) {
        throw @"
Docker Desktop не запущен (pipe dockerDesktopLinuxEngine недоступен).

Что сделать:
  1. Запустите Docker Desktop из меню Пуск
  2. Дождитесь статуса "Docker Desktop is running" (иконка кита в трее)
  3. Повторите: .\scripts\install.ps1   (если образ ещё не собран)
              .\scripts\start.ps1
"@
    }

    throw @"
Docker установлен, но engine не отвечает.

Попробуйте:
  1. Перезапустить Docker Desktop
  2. В Docker Desktop: Settings → General → Use the WSL 2 based engine (включено)
  3. В PowerShell: docker info
"@
}
