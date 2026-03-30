param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$BackendPath = "C:\dev\access2\backend",
    [string]$AdminEmail = "admin@example.com",
    [string]$AdminPassword = "Admin123!",
    [string]$AdminFullName = "Bootstrap Admin",
    [string]$UserEmail = "demo@example.com",
    [string]$UserPassword = "Secret123!",
    [string]$UpdatedFullName = "Updated Name",
    [switch]$RunPytest
)

$ErrorActionPreference = "Stop"

$ScriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$LogDir = Join-Path $ScriptRoot "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogDir "verify-user-hardening-with-cleanup_$Timestamp.log"

$superToken = $null
$oldUserToken = $null
$userId = $null
$cleanupNeeded = $false

function Write-Log {
    param(
        [Parameter(Mandatory = $true)][string]$Level,
        [Parameter(Mandatory = $true)][string]$Message
    )

    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level.ToUpper(), $Message
    Add-Content -Path $LogFile -Value $line

    switch ($Level.ToUpper()) {
        "PASS"  { Write-Host $line -ForegroundColor Green }
        "FAIL"  { Write-Host $line -ForegroundColor Red }
        "WARN"  { Write-Host $line -ForegroundColor Yellow }
        default { Write-Host $line -ForegroundColor Cyan }
    }
}

function Write-Step {
    param([string]$Message)

    $divider = "=" * 58
    Write-Host ""
    Write-Host $divider -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Yellow
    Write-Host $divider -ForegroundColor Cyan

    Add-Content -Path $LogFile -Value ""
    Add-Content -Path $LogFile -Value $divider
    Add-Content -Path $LogFile -Value $Message
    Add-Content -Path $LogFile -Value $divider
}

function Complete-Step {
    param([string]$Message)
    Write-Log -Level "PASS" -Message $Message
}

function Fail-Step {
    param([string]$Message)
    Write-Log -Level "FAIL" -Message $Message
    throw $Message
}

function Invoke-Api {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [hashtable]$Headers,
        [object]$Body
    )

    $params = @{
        Method = $Method
        Uri    = $Uri
    }

    if ($Headers) {
        $params.Headers = $Headers
    }

    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 10)
    }

    return Invoke-RestMethod @params
}

function Invoke-ApiExpectFailure {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][int]$ExpectedStatusCode,
        [hashtable]$Headers,
        [object]$Body
    )

    try {
        $params = @{
            Method = $Method
            Uri    = $Uri
        }

        if ($Headers) {
            $params.Headers = $Headers
        }

        if ($null -ne $Body) {
            $params.ContentType = "application/json"
            $params.Body = ($Body | ConvertTo-Json -Depth 10)
        }

        Invoke-RestMethod @params | Out-Null
        Fail-Step "Expected HTTP $ExpectedStatusCode from $Method $Uri, but request succeeded."
    }
    catch {
        $response = $_.Exception.Response
        if (-not $response) {
            throw
        }

        $statusCode = [int]$response.StatusCode
        $responseBody = ""

        try {
            $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
        }
        catch {
            $responseBody = "<unable to read response body>"
        }

        if ($statusCode -ne $ExpectedStatusCode) {
            Fail-Step "Expected HTTP $ExpectedStatusCode but got HTTP $statusCode from $Method $Uri. Body: $responseBody"
        }

        Write-Log -Level "PASS" -Message "Got expected HTTP $statusCode from $Method $Uri"
        if ($responseBody) {
            Add-Content -Path $LogFile -Value $responseBody
            Write-Host $responseBody
        }
    }
}

function Ensure-Superuser {
    param(
        [string]$Path,
        [string]$Email,
        [string]$Password,
        [string]$FullName
    )

    Write-Step "Bootstrapping or confirming superuser"

    Push-Location $Path
    try {
        $env:PYTHONPATH = $PWD.Path

        $pythonCode = @"
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User

session = SessionLocal()
try:
    email = "$Email"
    user = session.query(User).filter(User.email == email).one_or_none()
    if user:
        print(f"Superuser already exists: {user.id}")
    else:
        user = User(
            email=email,
            full_name="$FullName",
            hashed_password=get_password_hash("$Password"),
            is_active=True,
            is_superuser=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"Superuser created: {user.id}")
finally:
    session.close()
"@

        $output = $pythonCode | py -3 2>&1
        $outputText = ($output | Out-String).Trim()

        if ($LASTEXITCODE -ne 0) {
            Fail-Step "Superuser bootstrap failed. Output: $outputText"
        }

        if ($outputText) {
            Add-Content -Path $LogFile -Value $outputText
            Write-Host $outputText
        }

        Complete-Step "Superuser bootstrap/confirmation completed"
    }
    finally {
        Pop-Location
    }
}

function Run-CommandAndLog {
    param(
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)][scriptblock]$ScriptBlock
    )

    Write-Step $Description
    try {
        $output = & $ScriptBlock 2>&1
        $outputText = ($output | Out-String).Trim()

        if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) {
            Fail-Step "$Description failed. Output: $outputText"
        }

        if ($outputText) {
            Add-Content -Path $LogFile -Value $outputText
            Write-Host $outputText
        }

        Complete-Step "$Description completed"
    }
    catch {
        Fail-Step "$Description failed. $($_.Exception.Message)"
    }
}

function Run-Pytests {
    param([string]$Path)

    Push-Location $Path
    try {
        Run-CommandAndLog -Description "Running full pytest suite" -ScriptBlock {
            py -3 -m pytest
        }

        Run-CommandAndLog -Description "Running targeted user tests" -ScriptBlock {
            py -3 -m pytest tests/test_users.py -v
        }
    }
    finally {
        Pop-Location
    }
}

function Reactivate-UserIfNeeded {
    if (-not $cleanupNeeded) {
        Write-Log -Level "INFO" -Message "Cleanup not needed."
        return
    }

    if (-not $superToken) {
        Write-Log -Level "WARN" -Message "Cleanup skipped because superuser token is unavailable."
        return
    }

    if (-not $userId) {
        Write-Log -Level "WARN" -Message "Cleanup skipped because target user id is unavailable."
        return
    }

    try {
        Write-Step "Cleanup: reactivating target user"

        $reactivatedUser = Invoke-Api `
            -Method "Patch" `
            -Uri "$BaseUrl/api/v1/users/$userId" `
            -Headers @{
                Authorization = "Bearer $superToken"
            } `
            -Body @{
                is_active = $true
            }

        if ($reactivatedUser.is_active -ne $true) {
            Write-Log -Level "FAIL" -Message "Cleanup reactivation call returned unexpected is_active value."
            return
        }

        $reactivatedUserJson = $reactivatedUser | ConvertTo-Json -Depth 10
        Add-Content -Path $LogFile -Value $reactivatedUserJson
        Write-Host $reactivatedUserJson

        Write-Log -Level "PASS" -Message "Cleanup reactivated target user successfully"
    }
    catch {
        Write-Log -Level "FAIL" -Message "Cleanup failed to reactivate target user: $($_.Exception.Message)"
    }
}

Write-Log -Level "INFO" -Message "Starting verification run"
Write-Log -Level "INFO" -Message "Log file: $LogFile"

try {
    Ensure-Superuser -Path $BackendPath -Email $AdminEmail -Password $AdminPassword -FullName $AdminFullName

    Write-Step "Logging in as superuser"
    $superLogin = Invoke-Api `
        -Method "Post" `
        -Uri "$BaseUrl/api/v1/auth/login" `
        -Body @{
            email = $AdminEmail
            password = $AdminPassword
        }

    $superToken = $superLogin.access_token
    if (-not $superToken) {
        Fail-Step "Superuser login did not return an access token."
    }
    Complete-Step "Superuser login succeeded"

    Write-Step "Logging in as normal user before deactivation"
    $normalLogin = Invoke-Api `
        -Method "Post" `
        -Uri "$BaseUrl/api/v1/auth/login" `
        -Body @{
            email = $UserEmail
            password = $UserPassword
        }

    $oldUserToken = $normalLogin.access_token
    if (-not $oldUserToken) {
        Fail-Step "Normal user login did not return an access token."
    }
    Complete-Step "Normal user login succeeded and token captured"

    Write-Step "Listing users as superuser"
    $users = Invoke-Api `
        -Method "Get" `
        -Uri "$BaseUrl/api/v1/users" `
        -Headers @{
            Authorization = "Bearer $superToken"
        }

    $usersJson = $users | ConvertTo-Json -Depth 10
    Add-Content -Path $LogFile -Value $usersJson
    Write-Host $usersJson
    Complete-Step "Superuser user-list request succeeded"

    Write-Step "Finding target user"
    $targetUser = $users | Where-Object { $_.email -eq $UserEmail } | Select-Object -First 1
    if (-not $targetUser) {
        Fail-Step "Could not find target user with email '$UserEmail' in /api/v1/users response."
    }

    $userId = $targetUser.id
    Write-Log -Level "INFO" -Message "Target user id: $userId"
    Complete-Step "Target user located"

    Write-Step "Updating target user's full_name"
    $updatedUser = Invoke-Api `
        -Method "Patch" `
        -Uri "$BaseUrl/api/v1/users/$userId" `
        -Headers @{
            Authorization = "Bearer $superToken"
        } `
        -Body @{
            full_name = $UpdatedFullName
        }

    if ($updatedUser.full_name -ne $UpdatedFullName) {
        Fail-Step "Expected full_name to be '$UpdatedFullName' but got '$($updatedUser.full_name)'."
    }

    $updatedUserJson = $updatedUser | ConvertTo-Json -Depth 10
    Add-Content -Path $LogFile -Value $updatedUserJson
    Write-Host $updatedUserJson
    Complete-Step "User full_name update verified"

    Write-Step "Deactivating target user"
    $deactivatedUser = Invoke-Api `
        -Method "Patch" `
        -Uri "$BaseUrl/api/v1/users/$userId" `
        -Headers @{
            Authorization = "Bearer $superToken"
        } `
        -Body @{
            is_active = $false
        }

    if ($deactivatedUser.is_active -ne $false) {
        Fail-Step "Expected is_active to be false after deactivation."
    }

    $cleanupNeeded = $true

    $deactivatedUserJson = $deactivatedUser | ConvertTo-Json -Depth 10
    Add-Content -Path $LogFile -Value $deactivatedUserJson
    Write-Host $deactivatedUserJson
    Complete-Step "User deactivation verified"

    Write-Step "Verifying deactivated user login fails with 403"
    Invoke-ApiExpectFailure `
        -Method "Post" `
        -Uri "$BaseUrl/api/v1/auth/login" `
        -ExpectedStatusCode 403 `
        -Body @{
            email = $UserEmail
            password = $UserPassword
        }

    Write-Step "Verifying old token is blocked on /api/v1/auth/me"
    Invoke-ApiExpectFailure `
        -Method "Get" `
        -Uri "$BaseUrl/api/v1/auth/me" `
        -ExpectedStatusCode 403 `
        -Headers @{
            Authorization = "Bearer $oldUserToken"
        }

    if ($RunPytest) {
        Run-Pytests -Path $BackendPath
    }

    Write-Log -Level "PASS" -Message "Verification completed successfully"
}
catch {
    Write-Log -Level "FAIL" -Message "Verification failed: $($_.Exception.Message)"
}
finally {
    Reactivate-UserIfNeeded
    Write-Host ""
    Write-Host "Log written to: $LogFile" -ForegroundColor Cyan
}