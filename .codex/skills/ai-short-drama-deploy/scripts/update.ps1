[CmdletBinding()]
param(
    [ValidateSet('Status', 'Deploy')]
    [string]$Mode = 'Status',
    [switch]$SkipTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = 'E:\App\codex\AIShortDrama'
$sshKeyPath = 'D:\Soft\阿里云访问pem\tencent_hk01.pem'
$sshTarget = 'ubuntu@43.161.251.55'
$remoteDeployDir = '/opt/ai-short-drama/deploy'
$composeProject = 'ai-short-drama'
$healthUrl = 'https://mooncut.nodepass.net/api/health'
$sshOptions = @(
    '-o', 'ProxyCommand=none',
    '-o', 'ProxyJump=none',
    '-o', 'ConnectTimeout=10',
    '-o', 'StrictHostKeyChecking=accept-new',
    '-i', $sshKeyPath
)

function Invoke-Native {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,
        [string[]]$ArgumentList = @(),
        [switch]$Capture
    )

    if ($Capture) {
        $output = & $FilePath @ArgumentList 2>&1
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw "$FilePath failed with exit code $exitCode`n$($output -join [Environment]::NewLine)"
        }
        return ($output -join [Environment]::NewLine).Trim()
    }

    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath failed with exit code $LASTEXITCODE"
    }
}

function Invoke-Ssh {
    param(
        [Parameter(Mandatory)]
        [string]$Command,
        [switch]$Capture
    )

    $sshArguments = @($sshOptions) + @($sshTarget, $Command)
    Invoke-Native -FilePath 'ssh.exe' -ArgumentList $sshArguments -Capture:$Capture
}

function Test-PublicHealth {
    $output = & curl.exe --noproxy '*' --fail --silent --show-error $healthUrl 2>&1
    if ($LASTEXITCODE -ne 0 -or ($output -join '') -notmatch '"status":"ok"') {
        throw "Public health check failed: $($output -join [Environment]::NewLine)"
    }
    $output
}

function Show-ProductionStatus {
    Invoke-Ssh -Command "cd '$remoteDeployDir' && sudo docker compose -p '$composeProject' ps"
    Test-PublicHealth
}

if (-not (Test-Path -LiteralPath $projectRoot -PathType Container)) {
    throw "Project directory not found: $projectRoot"
}
if (-not (Test-Path -LiteralPath $sshKeyPath -PathType Leaf)) {
    throw "SSH key not found: $sshKeyPath"
}

if ($Mode -eq 'Status') {
    Show-ProductionStatus
    exit 0
}

$gitStatus = Invoke-Native -FilePath 'git.exe' -ArgumentList @('-C', $projectRoot, 'status', '--porcelain') -Capture
if ($gitStatus) {
    throw 'The Git worktree is not clean. Commit or resolve local changes before deploying.'
}

$revision = Invoke-Native -FilePath 'git.exe' -ArgumentList @('-C', $projectRoot, 'rev-parse', '--short=8', 'HEAD') -Capture
$backendImage = "ai-short-drama-backend:$revision"
$frontendImage = "ai-short-drama-frontend:$revision"
$temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) "ai-short-drama-deploy-$([guid]::NewGuid().ToString('N'))"
$localArchive = Join-Path $temporaryDirectory "images-$revision.tar"
$remoteArchive = "$remoteDeployDir/images-$revision.tar"
$archiveUploaded = $false
$deploymentSwitched = $false
$oldBackendImage = $null
$oldFrontendImage = $null

New-Item -ItemType Directory -Path $temporaryDirectory | Out-Null

try {
    if (-not $SkipTests) {
        Push-Location (Join-Path $projectRoot 'backend')
        try {
            Invoke-Native -FilePath 'uv.exe' -ArgumentList @('run', 'pytest')
        }
        finally {
            Pop-Location
        }

        Push-Location (Join-Path $projectRoot 'frontend')
        try {
            Invoke-Native -FilePath 'npm.cmd' -ArgumentList @('test')
        }
        finally {
            Pop-Location
        }
    }

    Invoke-Native -FilePath 'docker.exe' -ArgumentList @('build', '-t', $backendImage, (Join-Path $projectRoot 'backend'))
    Invoke-Native -FilePath 'docker.exe' -ArgumentList @('build', '-t', $frontendImage, (Join-Path $projectRoot 'frontend'))

    Invoke-Ssh -Command 'sudo /opt/ai-short-drama/backup.sh'
    $oldBackendImage = Invoke-Ssh -Command "cd '$remoteDeployDir' && sudo sed -n 's/^BACKEND_IMAGE=//p' .env" -Capture
    $oldFrontendImage = Invoke-Ssh -Command "cd '$remoteDeployDir' && sudo sed -n 's/^FRONTEND_IMAGE=//p' .env" -Capture
    if (-not $oldBackendImage -or -not $oldFrontendImage) {
        throw 'Could not read the current production image tags.'
    }

    Invoke-Native -FilePath 'docker.exe' -ArgumentList @('image', 'save', '--output', $localArchive, $backendImage, $frontendImage)
    $scpArguments = @($sshOptions) + @($localArchive, "${sshTarget}:$remoteArchive")
    $archiveUploaded = $true
    Invoke-Native -FilePath 'scp.exe' -ArgumentList $scpArguments

    Invoke-Ssh -Command "sudo docker load --input '$remoteArchive'"
    $deploymentSwitched = $true
    Invoke-Ssh -Command "cd '$remoteDeployDir' && sudo sed -i -E 's|^BACKEND_IMAGE=.*$|BACKEND_IMAGE=$backendImage|' .env && sudo sed -i -E 's|^FRONTEND_IMAGE=.*$|FRONTEND_IMAGE=$frontendImage|' .env"

    # Run the one-shot migration separately so its exit code and output are
    # unambiguous. The application services are started only after migration
    # succeeds, avoiding Compose's service_completed_successfully wait race.
    Invoke-Ssh -Command "cd '$remoteDeployDir' && sudo docker compose -p '$composeProject' up -d --wait db redis"
    $migrationOutput = Invoke-Ssh -Command "cd '$remoteDeployDir' && sudo docker compose -p '$composeProject' run --rm migrate" -Capture
    if ($migrationOutput) {
        Write-Output $migrationOutput
    }
    Invoke-Ssh -Command "cd '$remoteDeployDir' && sudo docker compose -p '$composeProject' up -d --no-deps backend worker"
    Invoke-Ssh -Command "cd '$remoteDeployDir' && sudo docker compose -p '$composeProject' up -d --no-deps frontend"

    $runningBackendImage = Invoke-Ssh -Command "sudo docker inspect --format '{{.Config.Image}}' ai-short-drama-backend-1" -Capture
    $runningWorkerImage = Invoke-Ssh -Command "sudo docker inspect --format '{{.Config.Image}}' ai-short-drama-worker-1" -Capture
    $runningFrontendImage = Invoke-Ssh -Command "sudo docker inspect --format '{{.Config.Image}}' ai-short-drama-frontend-1" -Capture
    if ($runningBackendImage -ne $backendImage -or $runningWorkerImage -ne $backendImage -or $runningFrontendImage -ne $frontendImage) {
        throw 'Production containers are not running the requested image tags.'
    }

    $healthy = $false
    for ($attempt = 1; $attempt -le 20; $attempt++) {
        try {
            Test-PublicHealth | Out-Null
            $healthy = $true
            break
        }
        catch {
            if ($attempt -eq 20) {
                throw
            }
            Start-Sleep -Seconds 3
        }
    }
    if (-not $healthy) {
        throw 'Production did not become healthy.'
    }

    Show-ProductionStatus
    Write-Output "DEPLOYED_REVISION=$revision"
}
catch {
    if ($deploymentSwitched -and $oldBackendImage -and $oldFrontendImage) {
        Write-Warning 'Deployment failed. Restoring the previous image tags; database migrations are not reversed.'
        try {
            Invoke-Ssh -Command "cd '$remoteDeployDir' && sudo sed -i -E 's|^BACKEND_IMAGE=.*$|BACKEND_IMAGE=$oldBackendImage|' .env && sudo sed -i -E 's|^FRONTEND_IMAGE=.*$|FRONTEND_IMAGE=$oldFrontendImage|' .env && sudo docker compose -p '$composeProject' up -d --no-deps backend worker frontend"
        }
        catch {
            Write-Warning "Automatic image rollback also failed: $($_.Exception.Message)"
        }
        try {
            Invoke-Ssh -Command "cd '$remoteDeployDir' && sudo docker compose -p '$composeProject' logs --tail 120 backend worker"
        }
        catch {
            Write-Warning "Could not read deployment logs: $($_.Exception.Message)"
        }
    }
    throw
}
finally {
    if ($archiveUploaded) {
        try {
            Invoke-Ssh -Command "sudo rm -f '$remoteArchive'"
        }
        catch {
            Write-Warning "Could not remove the remote image archive: $($_.Exception.Message)"
        }
    }
    if (Test-Path -LiteralPath $temporaryDirectory) {
        Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force
    }
}
