<#
Spike 0.5: get a token as an Entra agent identity and print its claims.

The agent identity has no credential of its own. Its blueprint proves itself with its
client secret and asks for an exchange token aimed at one agent identity (fmi_path);
the agent identity then trades that token for an access token to a resource.
Flow: https://learn.microsoft.com/en-us/entra/agent-id/autonomous-agent-authentication-authorization-flow

Run it in your own terminal, not through the coding agent, so the secret and the tokens
never reach the agent's context. It never prints a secret or a token, only decoded claims.

    pwsh docs/spikes/get-agent-token.ps1 -TenantId <id> -BlueprintClientId <id> -AgentIdentityClientId <id>
#>
param(
    [Parameter(Mandatory)] [string] $TenantId,
    [Parameter(Mandatory)] [string] $BlueprintClientId,
    [Parameter(Mandatory)] [string] $AgentIdentityClientId
)
$ErrorActionPreference = 'Stop'
$tokenUrl = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"

# A JWT is three base64url parts: header.payload.signature. The payload holds the claims.
function Show-Claims([string] $Jwt, [string] $Label) {
    $payload = $Jwt.Split('.')[1].Replace('-', '+').Replace('_', '/')
    $payload += '=' * ((4 - $payload.Length % 4) % 4)
    $json = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload))
    Write-Host "`n=== ${Label}: claims ===" -ForegroundColor Cyan
    $json | ConvertFrom-Json | Format-List
}

function Get-Token([hashtable] $Body, [string] $Step) {
    try {
        return (Invoke-RestMethod -Method Post -Uri $tokenUrl -Body $Body).access_token
    } catch {
        # Entra's error body (error code, description, trace ID) holds no secrets.
        Write-Host "`n=== $Step failed ===" -ForegroundColor Red
        Write-Host $_.ErrorDetails.Message
        throw
    }
}

$secure = Read-Host 'Blueprint client secret (input hidden)' -AsSecureString
$secret = [Net.NetworkCredential]::new('', $secure).Password

try {
    # Step 1: the blueprint, acting for one agent identity, gets an exchange token (T1).
    $t1 = Get-Token -Step 'Step 1 (blueprint exchange token)' -Body @{
        client_id     = $BlueprintClientId
        scope         = 'api://AzureADTokenExchange/.default'
        grant_type    = 'client_credentials'
        client_secret = $secret
        fmi_path      = $AgentIdentityClientId
    }
    Show-Claims $t1 'T1 (blueprint, for the agent identity)'

    # Step 2: the agent identity uses T1 as its credential and gets a Graph token (T2).
    $t2 = Get-Token -Step 'Step 2 (agent identity token)' -Body @{
        client_id             = $AgentIdentityClientId
        scope                 = 'https://graph.microsoft.com/.default'
        grant_type            = 'client_credentials'
        client_assertion_type = 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer'
        client_assertion      = $t1
    }
    Show-Claims $t2 'T2 (agent identity, for Microsoft Graph)'
} finally {
    # Drop the secret and tokens from this session as soon as we are done.
    Remove-Variable secret, secure, t1, t2 -ErrorAction SilentlyContinue
}
