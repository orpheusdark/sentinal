# Project Sentinel - Setup AutoStart
# Run this script as Administrator to enable autostart

$taskName = "Sentinel-Surveillance"
$taskPath = "C:\Users\niran\Documents\GitHub\sentinal\start_sentinel.bat"
$workingDir = "C:\Users\niran\Documents\GitHub\sentinal"

# Create task to run at startup
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$taskPath`"" -WorkingDirectory $workingDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -RunLevel Highest

# Register the task
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Description "Start Project Sentinel surveillance system at Windows startup" -Force

Write-Host "✓ Task registered: $taskName"
Write-Host "✓ The application will now start automatically when Windows boots"
Write-Host ""
Write-Host "To disable autostart, run:"
Write-Host "  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
