param([string]$Destination = "$HOME/.agents/skills/supermesh-x")
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path $Destination) { Remove-Item -Recurse -Force $Destination }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
Copy-Item -Recurse -Force $Source $Destination
Write-Output "Installed SuperMesh-X to $Destination"
