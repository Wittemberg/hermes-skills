# Exemplo validado

Ambiente usado para validar este procedimento:

- Windows Server 2016
- PowerShell 5.1
- Win32-OpenSSH instalado por MSI
- serviço `sshd` Running / Automatic
- porta SSH personalizada: TCP 5822
- usuário administrativo: `Star.Suporte`
- chave pública RSA do cliente
- `Match Group administrators` usando `administrators_authorized_keys`
- PowerShell configurado como `DefaultShell`
- host Linux/Hermes com alias SSH já configurado
- alias utilizado: `awe-stardb3`

## Segundo ambiente validado (script único)

- Windows Server 2016 Datacenter 14393, PowerShell 5.1.14393.9507
- host `SRV-GRP2`, usuário de domínio `VIXTEC\TecnoTeam`, porta TCP 5822
- provisionado com a v1 de `hermes-ssh-setup.ps1` (sem hardening) colada no PowerShell administrativo;
  a v2 publicada em `Wittemberg/utilitarios` aplica o hardening por padrão
- alias no Hermes: `cloud-vixtec` (HostName 190.102.41.107, IdentityFile `~/.ssh/KW_Kronic.key`)
- primeira conexão com `-o BatchMode=yes -o StrictHostKeyChecking=accept-new` retornou
  hostname/whoami/PSVersion corretos e `sshd` Running/Automatic — sem senha.
- usuário de domínio no `~/.ssh/config`: `User VIXTEC\TecnoTeam` funciona sem escape adicional.
- hardening pendente após validação: `PasswordAuthentication no` e restringir firewall à origem do Hermes.

Validações executadas com sucesso na sessão remota:

```powershell
$PSVersionTable.PSVersion
whoami
hostname
Get-Service 'MSSQL$OASIS','MSSQL$NUCLEO'
```

Resultado:
- PowerShell 5.1 abriu diretamente via SSH;
- identidade remota correta;
- hostname correto;
- acesso aos serviços SQL OASIS e NUCLEO confirmado.

Os nomes, porta, usuário e privilégios acima são exemplo validado, não defaults universais.
