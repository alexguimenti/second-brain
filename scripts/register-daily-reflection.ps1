# Register the daily reflection as a Windows Scheduled Task
# Run this once:
#   powershell -ExecutionPolicy Bypass -File scripts\register-daily-reflection.ps1
#
# To remove:
#   Unregister-ScheduledTask -TaskName "SecondBrain-DailyReflection" -Confirm:$false

$TaskName = "SecondBrain-DailyReflection"
$ScriptPath = Join-Path $PSScriptRoot "daily-reflection.sh"
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
$Trigger = New-ScheduledTaskTrigger -Daily -At "19:00"
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Review daily log and update MEMORY.md with important decisions and lessons" `
    -RunLevel Limited

Write-Host ""
Write-Host "Scheduled task '$TaskName' registered successfully."
Write-Host "  Trigger: Daily at 19:00"
Write-Host "  Action:  bash $ScriptPath"
Write-Host ""
Write-Host "To run manually:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "To remove:        Unregister-ScheduledTask -TaskName '$TaskName'"
