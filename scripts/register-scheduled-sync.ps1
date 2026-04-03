# Register the ClickUp sync as a Windows Scheduled Task
# Run this once as Administrator:
#   powershell -ExecutionPolicy Bypass -File scripts\register-scheduled-sync.ps1
#
# To remove:
#   Unregister-ScheduledTask -TaskName "SecondBrain-ClickUpSync" -Confirm:$false

$TaskName = "SecondBrain-ClickUpSync"
$ScriptPath = Join-Path $PSScriptRoot "scheduled-sync.sh"
$BashPath = "C:\Program Files\Git\bin\bash.exe"

# Check if bash exists
if (-not (Test-Path $BashPath)) {
    $BashPath = (Get-Command bash -ErrorAction SilentlyContinue).Source
    if (-not $BashPath) {
        Write-Error "bash not found. Install Git for Windows."
        exit 1
    }
}

# Remove existing task if present
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task '$TaskName'"
}

# Create the task
$Action = New-ScheduledTaskAction -Execute $BashPath -Argument "`"$ScriptPath`""
$Trigger1 = New-ScheduledTaskTrigger -Daily -At "07:00"
$Trigger2 = New-ScheduledTaskTrigger -Daily -At "13:00"
$Trigger = @($Trigger1, $Trigger2)
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Sync ClickUp documents to Obsidian vault and re-index QMD" `
    -RunLevel Limited

Write-Host ""
Write-Host "Scheduled task '$TaskName' registered successfully."
Write-Host "  Trigger: Daily at 07:00 and 13:00"
Write-Host "  Action:  bash $ScriptPath"
Write-Host ""
Write-Host "To run manually:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "To remove:        Unregister-ScheduledTask -TaskName '$TaskName'"
