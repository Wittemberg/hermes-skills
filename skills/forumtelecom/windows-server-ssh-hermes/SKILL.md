---
name: windows-server-ssh-hermes
description: >
  Configura e valida acesso SSH do Hermes/Linux a Windows Server usando Win32-OpenSSH,
  autenticação por chave pública e PowerShell como shell remoto. Inclui instalação em
  Windows Server 2016, porta SSH personalizada, firewall, ACL de authorized_keys,
  aliases no ~/.ssh/config e diagnóstico de falhas.
version: 1.0.0
author: TecnoTeam
platforms:
  - windows
  - linux
metadata:
  hermes:
    tags:
      - ssh
      - windows-server
      - powershell
      - openssh
      - hermes
      - remote-admin
    category: infrastructure
    requires_toolsets: []
---

# Windows Server via SSH para Hermes

## Objetivo

Permitir que um host Linux/Hermes acesse Windows Server remotamente por SSH e execute
PowerShell de forma confiável, preferencialmente por chave pública.

Fluxo esperado:

```text
Hermes/Linux
    |
    | ssh <alias>
    v
Windows Server / Win32-OpenSSH
    |
    v
PowerShell
    |
    +-- Serviços
    +-- Firewall
    +-- Registry
    +-- Arquivos
    +-- SQLCMD/SQL Server
```

## Regras operacionais

1. Diagnosticar antes de instalar ou alterar.
2. Fazer backup de `sshd_config` antes de editar.
3. Validar com `sshd.exe -t` antes de reiniciar `sshd`.
4. Criar/liberar a nova porta no firewall antes de reiniciar em porta personalizada.
5. Nunca desabilitar senha antes de comprovar login por chave.
6. Não sobrescrever `authorized_keys` se já houver chaves: preservar e adicionar.
7. Não copiar chave privada para o Windows Server.
8. Chave privada fica somente no cliente/Hermes.
9. Para contas administrativas, respeitar `administrators_authorized_keys`.
10. Executar mudanças remotas destrutivas somente com aprovação explícita do operador.
11. Preferir usuário dedicado para automação quando o ambiente permitir.

---

# 0. Caminho rápido: uma linha (padrão)

O script canônico vive no repositório padrão de ferramentas pessoais
`Wittemberg/utilitarios` (público; clone local em `/root/projetos/utilitarios`):

```text
https://github.com/Wittemberg/utilitarios/blob/main/windows/hermes-ssh-setup.ps1
```

No Windows, PowerShell como Administrador, logado com a conta que o Hermes usará:

```powershell
[Net.ServicePointManager]::SecurityProtocol='Tls12'; irm https://raw.githubusercontent.com/Wittemberg/utilitarios/main/windows/hermes-ssh-setup.ps1 | iex
```

Variáveis opcionais (definir ANTES do `irm`):

| Variável              | Padrão            | Efeito                                                     |
|-----------------------|-------------------|------------------------------------------------------------|
| `HERMES_SSH_PORT`     | `5822`            | Porta TCP do sshd                                          |
| `HERMES_SSH_ALLOW`    | `177.136.234.234` | Origens do firewall (lista por vírgula, CIDR ok) ou `Any`  |
| `HERMES_SSH_PASSWORD` | `no`              | `yes` mantém login por senha                               |

O que faz, nesta ordem (idempotente, Windows Server 2016+/PS 5.1): pre-checks (admin, x64,
TLS 1.2) → instala Win32-OpenSSH v9.8.3.0 por MSI com SHA-256 verificado (pula se `sshd` já
existir) → sshd Automatic/Running → regra de firewall própria `OpenSSH Server - TCP <porta>
(Hermes)` restrita a `HERMES_SSH_ALLOW`, criada ANTES de trocar a porta → backup + `Port`,
`PubkeyAuthentication yes`, `PasswordAuthentication no`, `PermitEmptyPasswords no`, `Match
Group administrators` → `sshd -t` (restaura backup e aborta se falhar) → chave em
`administrators_authorized_keys` e `%USERPROFILE%\.ssh\authorized_keys` com ACL por SID →
DefaultShell = PowerShell → restart sshd → confirma LISTEN → resumo com comando de teste e
de rollback.

Hardening é o padrão: senha desligada e origem restrita ao IP do Hermes. Isso é seguro porque a
chave pública é gravada no mesmo run, antes do restart; se a chave privada correspondente não
estiver no Hermes, use `HERMES_SSH_PASSWORD='yes'` na primeira execução e endureça depois.

O script nunca remove regras de firewall existentes — apenas AVISA sobre a regra legada aberta
`OpenSSH Server - TCP <porta>` (v1) e a regra do MSI `OpenSSH SSH Server Preview (sshd)` (TCP 22),
com o comando para removê-las/desabilitá-las após validar o acesso. Fazer isso só após o teste
da seção 12 passar, porque uma regra aberta anula a restrição de origem.

Para outro cliente/chave: editar `$PublicKey` (a chave embutida é a RSA `computador@NITRO5`,
cuja privada é `~/.ssh/KW_Kronic.key` no Hermes). Para trocar a versão do MSI, atualizar
`$MsiUrl` e `$MsiSha256` juntos — baixar e calcular o hash no Hermes antes (a release não
publica SHA-256 no corpo). Após editar: validar parse com pwsh (container
`mcr.microsoft.com/powershell:lts-ubuntu-22.04`), commit, push com `~/.ssh/chavewit` e conferir
que o hash da URL raw bate com o arquivo local.

Lições:
- Preferir a última release estável da linha já validada (9.8.x) à mais nova (10.x) sem histórico no 2016.
- `Set-Content -Encoding ascii` no sshd_config: UTF-8 com BOM quebra o parser do sshd.
- Diretivas globais (`Port`, `PasswordAuthentication`...) precisam ficar antes de qualquer `Match`; a função `Set-SshdDirective` substitui a linha (mesmo comentada) ou insere no topo e nunca edita dentro de `Match`.
- Gravar a chave nos DOIS arquivos cobre tanto o cenário com `Match Group administrators` quanto sem.
- Restringir `RemoteAddress` no firewall não adianta se outra regra na mesma porta estiver aberta — auditar com `Get-NetFirewallPortFilter | ? LocalPort -eq <porta>`.
- Publicação em repositório GitHub é ação externa: exige aprovação explícita do operador.

Depois de rodar, validar do Hermes com o alias (seção 12).

---

# 1. Diagnóstico do Windows

PowerShell como Administrador:

```powershell
$PSVersionTable

Get-Service sshd -ErrorAction SilentlyContinue
Get-Command ssh.exe -ErrorAction SilentlyContinue
Get-Command sshd.exe -ErrorAction SilentlyContinue

Get-ChildItem "C:\Program Files\OpenSSH" -ErrorAction SilentlyContinue
Get-ChildItem "C:\Windows\System32\OpenSSH" -ErrorAction SilentlyContinue
```

Arquitetura:

```powershell
Get-CimInstance Win32_OperatingSystem |
    Select-Object OSArchitecture
```

No Windows Server 2016, o OpenSSH pode não existir como Windows Capability. Não presumir
que `Add-WindowsCapability` funcionará. O método validado nesta skill usa Win32-OpenSSH MSI.

---

# 2. TLS 1.2 e conectividade

Em PowerShell 5.1 antigo, habilitar TLS 1.2 para downloads HTTPS:

```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
```

Teste:

```powershell
$r = Invoke-WebRequest `
    -Uri "https://github.com/PowerShell/Win32-OpenSSH" `
    -UseBasicParsing `
    -ErrorAction Stop

$r.StatusCode
```

Se necessário:

```powershell
Test-NetConnection github.com -Port 443
Resolve-DnsName github.com
```

---

# 3. Descobrir release e baixar Win32-OpenSSH

Não hard-code uma versão eternamente. Consultar releases:

```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Releases = Invoke-RestMethod `
    -Uri "https://api.github.com/repos/PowerShell/Win32-OpenSSH/releases" `
    -Headers @{ "User-Agent" = "PowerShell" }

$Releases |
    Where-Object {
        $_.assets.name -match "OpenSSH-Win64.*\.msi$"
    } |
    Select-Object -First 10 `
        tag_name,
        prerelease,
        published_at,
        @{N="MSI";E={
            ($_.assets |
                Where-Object name -match "OpenSSH-Win64.*\.msi$").name
        }} |
    Format-Table -AutoSize
```

Selecionar conscientemente a versão compatível. Baixar o asset Win64 e verificar SHA-256
contra o valor publicado pela release antes da instalação.

Exemplo genérico:

```powershell
$MSI = "C:\OpenSSH-Win64.msi"

Invoke-WebRequest `
    -Uri "<URL_DO_ASSET_OFICIAL>" `
    -OutFile $MSI `
    -UseBasicParsing

Get-FileHash $MSI -Algorithm SHA256
```

---

# 4. Instalar OpenSSH Server

Instalar somente Server:

```powershell
$MSI = "C:\OpenSSH-Win64.msi"

$Process = Start-Process `
    -FilePath "msiexec.exe" `
    -ArgumentList "/i `"$MSI`" ADDLOCAL=Server /qn /norestart" `
    -Wait `
    -PassThru

Write-Host "ExitCode MSI:" $Process.ExitCode
```

Esperado:

```text
ExitCode MSI: 0
```

Validar:

```powershell
Get-Service sshd

Get-ChildItem "C:\Program Files\OpenSSH" |
    Where-Object {$_.Name -match "sshd|ssh-keygen|ssh.exe"} |
    Select-Object Name, Length
```

O serviço deve estar `Running` e preferencialmente `Automatic`.

---

# 5. Configurar porta personalizada

Config efetiva típica:

```text
C:\ProgramData\ssh\sshd_config
```

Backup:

```powershell
$Config = "C:\ProgramData\ssh\sshd_config"

Copy-Item `
    $Config `
    "$Config.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

Exemplo com porta 5822:

```text
Port 5822
```

Após editar, SEMPRE validar:

```powershell
& "C:\Program Files\OpenSSH\sshd.exe" -t
Write-Host "ExitCode:" $LASTEXITCODE
```

Esperado:

```text
ExitCode: 0
```

Não reiniciar se houver erro de sintaxe.

---

# 6. Firewall

Criar a regra antes de trocar/reiniciar o listener:

```powershell
New-NetFirewallRule `
    -DisplayName "OpenSSH Server - TCP 5822" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 5822 `
    -Action Allow `
    -Profile Any
```

Depois:

```powershell
Restart-Service sshd
Start-Sleep -Seconds 2

Get-NetTCPConnection `
    -State Listen `
    -LocalPort 5822 `
    -ErrorAction SilentlyContinue |
    Format-Table LocalAddress,LocalPort,State,OwningProcess -AutoSize
```

Esperado:

```text
0.0.0.0  5822  Listen
::       5822  Listen
```

Em produção, quando a topologia for conhecida, considerar restringir `RemoteAddress`
no firewall ao IP/rede do host Hermes ou VPN de administração.

---

# 7. Chave pública

## Usuário comum

Normalmente:

```text
C:\Users\<USUARIO>\.ssh\authorized_keys
```

## Usuário membro de Administrators

Verificar o final de:

```powershell
Get-Content "C:\ProgramData\ssh\sshd_config" |
    Select-Object -Last 30
```

Se houver:

```text
Match Group administrators
       AuthorizedKeysFile __PROGRAMDATA__/ssh/administrators_authorized_keys
```

a chave deve ser gravada em:

```text
C:\ProgramData\ssh\administrators_authorized_keys
```

Adicionar sem destruir chaves existentes:

```powershell
$AuthorizedKeys = "C:\ProgramData\ssh\administrators_authorized_keys"
$PublicKey = '<CHAVE_PUBLICA_COMPLETA>'

if (-not (Test-Path $AuthorizedKeys)) {
    New-Item -ItemType File -Path $AuthorizedKeys -Force | Out-Null
}

$Existing = Get-Content $AuthorizedKeys -ErrorAction SilentlyContinue

if ($Existing -notcontains $PublicKey) {
    Add-Content `
        -Path $AuthorizedKeys `
        -Value $PublicKey `
        -Encoding ascii
}
```

ACL para arquivo de administradores:

```powershell
icacls "C:\ProgramData\ssh\administrators_authorized_keys" /inheritance:r
icacls "C:\ProgramData\ssh\administrators_authorized_keys" /grant "SYSTEM:F"
icacls "C:\ProgramData\ssh\administrators_authorized_keys" /grant "*S-1-5-32-544:F"

icacls "C:\ProgramData\ssh\administrators_authorized_keys"
```

Usar SID `S-1-5-32-544` evita dependência do idioma do Windows.

Nunca armazenar a chave privada nesse arquivo.

---

# 8. Testar autenticação antes de endurecer

Do host Hermes/Linux:

```bash
ssh -p 5822 USUARIO@IP_DO_WINDOWS
```

Ou especificando chave:

```bash
ssh -i ~/.ssh/CHAVE_PRIVADA -p 5822 USUARIO@IP_DO_WINDOWS
```

Só depois de autenticação por chave comprovada considerar `PasswordAuthentication no`.

---

# 9. PowerShell como shell padrão

Sem configuração adicional, Win32-OpenSSH pode abrir `cmd.exe`.

Definir PowerShell 5.1:

```powershell
New-ItemProperty `
    -Path "HKLM:\SOFTWARE\OpenSSH" `
    -Name DefaultShell `
    -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
    -PropertyType String `
    -Force
```

Validar:

```powershell
Get-ItemProperty `
    -Path "HKLM:\SOFTWARE\OpenSSH" `
    -Name DefaultShell
```

Reiniciar somente SSH:

```powershell
Restart-Service sshd
```

Reconectar e validar:

```powershell
$PSVersionTable.PSVersion
whoami
hostname
```

---

# 10. Configurar alias no host Hermes

Arquivo:

```text
~/.ssh/config
```

Exemplo:

```sshconfig
Host awe-stardb3
    HostName <IP_OU_DNS>
    User Star.Suporte
    Port 5822
    IdentityFile ~/.ssh/<CHAVE_PRIVADA>
    IdentitiesOnly yes
```

Permissões no Linux:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/config
chmod 600 ~/.ssh/<CHAVE_PRIVADA>
```

Teste:

```bash
ssh awe-stardb3
```

Se funcionar, o Hermes pode usar o alias sem conhecer repetidamente IP, porta ou caminho
da chave.

---

# 11. Executar PowerShell remotamente

Teste simples:

```bash
ssh awe-stardb3 'hostname'
```

Como o shell padrão é PowerShell, comandos PowerShell podem ser enviados:

```bash
ssh awe-stardb3 'Get-Service sshd'
```

Exemplo SQL Server:

```bash
ssh awe-stardb3 'Get-Service "MSSQL$OASIS","MSSQL$NUCLEO"'
```

Para scripts complexos, ter cuidado com quoting entre Bash -> SSH -> PowerShell.
Preferir scripts `.ps1` bem definidos ou comandos simples quando possível.

---

# 12. Como o Hermes deve operar

Quando o usuário disser que o alias já está configurado, por exemplo `awe-stardb3`,
não pedir novamente IP/porta/chave. Testar primeiro:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 awe-stardb3 'hostname; whoami'
```

Se retornar corretamente, usar o alias.

Antes de alteração relevante, coletar estado.

Exemplo:

```bash
ssh awe-stardb3 'Get-Service sshd'
```

Para SQL:

```bash
ssh awe-stardb3 'Get-Service "MSSQL$OASIS","MSSQL$NUCLEO"'
```

O Hermes deve distinguir:
- diagnóstico somente leitura;
- mudança reversível;
- reinício/interrupção;
- comando destrutivo.

Reinício de Windows, parada/reinício de SQL, DROP DATABASE, remoção de arquivos,
alterações de firewall que possam cortar acesso e mudanças equivalentes exigem confirmação.

---

# 13. Hardening após validação

O script da seção 0 já aplica `PasswordAuthentication no` e firewall restrito por padrão. Em
instalações manuais ou feitas com a v1 do script, aplicar somente depois que chave pública
estiver comprovadamente funcionando:

- `PasswordAuthentication no` (ou simplesmente re-executar o script da seção 0, que é idempotente);
- restringir firewall ao IP/rede administrativa e remover regras abertas na mesma porta;
- usar conta exclusiva para Hermes;
- conceder apenas privilégios necessários;
- manter chave privada protegida;
- remover chaves antigas;
- revisar logs do OpenSSH.

Antes de desabilitar senha, manter uma sessão administrativa existente aberta e testar
uma NOVA sessão SSH com chave.

---

# 14. Troubleshooting

Consulte `references/troubleshooting.md`.

# 15. Critério de conclusão

O acesso está pronto quando:

```text
sshd = Running / Automatic
porta escolhida = LISTEN
firewall = permite origem desejada
sshd.exe -t = exit 0
chave pública = aceita
ssh <alias> = conecta sem senha
shell remoto = PowerShell
hostname/whoami = corretos
```
