# Antigravity Discord Rich Presence - PowerShell Uninstaller for Windows
Write-Host "`n🗑️  Uninstalling Antigravity Discord Rich Presence...`n" -ForegroundColor Yellow

# Terminate running daemon process
$PidFile = "$HOME\.gemini\antigravity-cli\discord_rpc_daemon.pid"
if (Test-Path $PidFile) {
    try {
        $DaemonPid = (Get-Content $PidFile -ErrorAction SilentlyContinue).Trim()
        if ($DaemonPid) {
            Stop-Process -Id $DaemonPid -Force -ErrorAction SilentlyContinue
            Write-Host "🛑 Stopped daemon (PID: $DaemonPid)"
        }
    } catch {}
    Remove-Item -Force $PidFile -ErrorAction SilentlyContinue
}

# Stop any dangling python daemon instances
Get-Process -Name "python*", "py*" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*discord_rpc_daemon.py*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

$PluginDir = "$HOME\.gemini\config\plugins\agy-rich-presence"
if (Test-Path $PluginDir) {
    Remove-Item -Recurse -Force $PluginDir
    Write-Host "✅ Removed $PluginDir"
}

Remove-Item -Force "$HOME\.gemini\antigravity-cli\discord_rpc_state.json" -ErrorAction SilentlyContinue

Write-Host "`n🎉 Uninstalled successfully.`n" -ForegroundColor Green
