# Register daily link-vault scan as a Windows Scheduled Task
# Run once:
#   powershell -ExecutionPolicy Bypass -File scripts\register-daily-link-vault.ps1

$TaskName = "SecondBrain-DailyLinkVault"
$ScriptPath = Join-Path $PSScriptRoot "daily-link-vault.sh"
$BashPath = "C:\Program Files\Git\bin\bash.exe"

if (-not (Test-Path $BashPath)) {
    $BashPath = (Get-Command bash -ErrorAction SilentlyContinue).Source
    if (-not $BashPath) {
        Write-Error "bash not found. Install Git for Windows."
        exit 1
    }
}

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task '$TaskName'"
}

$Action = New-ScheduledTaskAction -Execute $BashPath -Argument "`"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -Daily -At "20:00"
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Scan vault for new connections between documents and create wikilinks" `
    -RunLevel Limited

Write-Host ""
Write-Host "Scheduled task '$TaskName' registered successfully."
Write-Host "  Trigger: Daily at 20:00"
Write-Host "  Action:  bash $ScriptPath"
