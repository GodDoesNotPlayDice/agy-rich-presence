# Antigravity Discord Rich Presence - PowerShell Installer for Windows
$ErrorActionPreference = "Stop"

Write-Host "`n🌟 Installing Antigravity Discord Rich Presence for Windows...`n" -ForegroundColor Cyan

$PluginDir = "$HOME\.gemini\config\plugins\agy-rich-presence"
if (Test-Path $PluginDir) {
    Remove-Item -Recurse -Force $PluginDir
}
New-Item -ItemType Directory -Path $PluginDir -Force | Out-Null

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($ScriptDir -and (Test-Path "$ScriptDir\plugin.json")) {
    # Installed from cloned repo
    Copy-Item -Path "$ScriptDir\*" -Destination $PluginDir -Recurse -Force
} else {
    # Download from GitHub repository archive
    Write-Host "📦 Downloading latest release from GitHub..." -ForegroundColor Yellow
    $ZipUrl = "https://github.com/GodDoesNotPlayDice/agy-rich-presence/archive/refs/heads/main.zip"
    $ZipFile = "$env:TEMP\agy-rich-presence.zip"
    $ExtractDir = "$env:TEMP\agy-extracted"
    
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipFile -UseBasicParsing
    Expand-Archive -Path $ZipFile -DestinationPath $ExtractDir -Force
    Copy-Item -Path "$ExtractDir\agy-rich-presence-main\*" -Destination $PluginDir -Recurse -Force
    
    Remove-Item -Force $ZipFile -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $ExtractDir -ErrorAction SilentlyContinue
}

# Detect Python command on Windows (py, python, or python3)
$PyCmd = "python"
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PyCmd = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PyCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PyCmd = "python3"
}

# Adapt hooks.json for detected Python command
$HooksFile = "$PluginDir\hooks.json"
if (Test-Path $HooksFile) {
    (Get-Content $HooksFile) -replace 'python3', $PyCmd | Set-Content $HooksFile
}

Write-Host "✅ Plugin files installed to:" -ForegroundColor Green
Write-Host "   $PluginDir`n"

# Check if Discord Named Pipe exists
$DiscordRunning = $false
for ($i = 0; $i -lt 10; $i++) {
    if (Test-Path "\\.\pipe\discord-ipc-$i") {
        $DiscordRunning = $true
        Write-Host "✅ Discord IPC pipe detected: \\.\pipe\discord-ipc-$i" -ForegroundColor Green
        break
    }
}
if (-not $DiscordRunning) {
    Write-Host "⚠️  Discord is not running right now. Open Discord to see your rich presence." -ForegroundColor Yellow
}

# Launch daemon in background
$DaemonScript = "$PluginDir\scripts\discord_rpc_daemon.py"
if (Test-Path $DaemonScript) {
    Start-Process -FilePath $PyCmd -ArgumentList "`"$DaemonScript`"" -WindowStyle Hidden
    Write-Host "🚀 Started Discord RPC daemon in background." -ForegroundColor Cyan
}

Write-Host "`n🎉 Installation complete!" -ForegroundColor Green
Write-Host "✨ Now whenever you open `"agy`" in PowerShell, Windows Terminal, or CMD, Discord will show your status automatically.`n"
