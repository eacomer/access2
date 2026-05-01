[CmdletBinding()]
param(
    [int]$Port = 3001,
    [int]$TimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$frontendDir = Join-Path $repoRoot "frontend"
$nextCmd = Join-Path $frontendDir "node_modules\.bin\next.cmd"
$readyUrl = "http://localhost:$Port/login"

function Test-Access2DemoReady {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return [pscustomobject]@{
            Ready = $true
            StatusCode = [int]$response.StatusCode
            Error = $null
        }
    } catch {
        return [pscustomobject]@{
            Ready = $false
            StatusCode = $null
            Error = $_.Exception.Message
        }
    }
}

function Get-Access2PortDiagnostics {
    param([int]$Port)

    try {
        Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
            Select-Object LocalAddress, LocalPort, State, OwningProcess
    } catch {
        Write-Host "Could not read TCP diagnostics: $($_.Exception.Message)"
    }
}

function Get-Access2PortOwnerIds {
    param([int]$Port)

    @(Get-Access2PortDiagnostics -Port $Port) |
        Where-Object { $_.State -eq "Listen" -or $_.State -eq "Bound" } |
        Select-Object -ExpandProperty OwningProcess -Unique
}

function Write-Access2StopCommand {
    param(
        [int]$LauncherProcessId,
        [int]$Port
    )

    $processIds = @($LauncherProcessId) + @(Get-Access2PortOwnerIds -Port $Port)
    $processIds = @($processIds | Where-Object { $_ } | Select-Object -Unique)
    if ($processIds.Count -gt 0) {
        Write-Host "To stop after the demo: Stop-Process -Id $($processIds -join ',')"
    } else {
        Write-Host "Stop the frontend from the terminal or process that started it."
    }
}

if (-not (Test-Path $frontendDir)) {
    throw "Frontend directory was not found: $frontendDir"
}

if (-not (Test-Path $nextCmd)) {
    throw "Next.js command was not found at $nextCmd. Run frontend dependency install first."
}

Write-Host "ACCESS2 demo frontend"
Write-Host "Repo root: $repoRoot"
Write-Host "Frontend:  $frontendDir"
Write-Host "URL:       $readyUrl"

$initial = Test-Access2DemoReady -Url $readyUrl
if ($initial.Ready) {
    Write-Host "Frontend is already reachable at $readyUrl (HTTP $($initial.StatusCode))."
    Write-Host "Use this URL for Selenium: --e2e-base-url http://localhost:$Port"
    Write-Host "Stop the existing frontend from the terminal or process that started it."
    exit 0
}

$portConnections = @(Get-Access2PortDiagnostics -Port $Port)
if ($portConnections.Count -gt 0) {
    Write-Host "Port $Port is already in use, but $readyUrl is not reachable."
    Write-Host "Latest readiness error: $($initial.Error)"
    Write-Host "Port diagnostics:"
    $portConnections | Format-Table | Out-String | Write-Host
    Write-Host "Stop the process that owns port $Port or choose a clean demo port, then rerun this script."
    exit 1
}

Write-Host "Starting current-workspace Next.js frontend on port $Port..."
$process = Start-Process `
    -FilePath $nextCmd `
    -ArgumentList @("dev", "-H", "0.0.0.0", "-p", "$Port") `
    -WorkingDirectory $frontendDir `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Started frontend process id $($process.Id)."
Write-Host "Waiting up to $TimeoutSeconds seconds for $readyUrl..."

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$lastResult = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    $lastResult = Test-Access2DemoReady -Url $readyUrl
    if ($lastResult.Ready) {
        Write-Host "Frontend is reachable at $readyUrl (HTTP $($lastResult.StatusCode))."
        Write-Host "Use this URL for Selenium: --e2e-base-url http://localhost:$Port"
        Write-Access2StopCommand -LauncherProcessId $process.Id -Port $Port
        exit 0
    }

    if ($process.HasExited) {
        Write-Host "Frontend process $($process.Id) exited before readiness."
        Write-Host "Latest readiness error: $($lastResult.Error)"
        exit 1
    }
}

Write-Host "Frontend did not become reachable before timeout."
if ($lastResult -and $lastResult.Error) {
    Write-Host "Latest readiness error: $($lastResult.Error)"
}
Write-Host "Process id: $($process.Id)"
Write-Host "Port diagnostics:"
Get-Access2PortDiagnostics -Port $Port | Format-Table | Out-String | Write-Host
Write-Access2StopCommand -LauncherProcessId $process.Id -Port $Port
exit 1
