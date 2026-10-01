# Troubleshooting — Win32-OpenSSH / Windows Server

## `Permission denied (publickey,password,keyboard-interactive)`

Verificar:
1. usuário correto;
2. chave privada correta no cliente;
3. chave pública correspondente no servidor;
4. se usuário é Administrator;
5. bloco `Match Group administrators`;
6. ACL do `administrators_authorized_keys`;
7. logs do OpenSSH.

Para administradores:

```powershell
Get-Content C:\ProgramData\ssh\sshd_config | Select-Object -Last 30
icacls C:\ProgramData\ssh\administrators_authorized_keys
```

## Conecta por senha mas não por chave

Causa comum: chave colocada em `C:\Users\<user>\.ssh\authorized_keys` enquanto
`Match Group administrators` redireciona para `C:\ProgramData\ssh\administrators_authorized_keys`.

## `Connection refused`

No Windows:

```powershell
Get-Service sshd
Get-NetTCPConnection -State Listen
```

Confirmar porta do `sshd_config`.

## Timeout

Verificar:

```powershell
Get-NetFirewallRule -DisplayName "*OpenSSH*"
```

No cliente:

```bash
ssh -vvv awe-stardb3
```

Verificar roteamento/NAT/VPN/firewall intermediário.

## sshd não inicia depois de editar config

Não insistir em restart.

```powershell
& "C:\Program Files\OpenSSH\sshd.exe" -t
$LASTEXITCODE
```

Restaurar backup do `sshd_config` se necessário.

## SSH abre CMD em vez de PowerShell

```powershell
Get-ItemProperty HKLM:\SOFTWARE\OpenSSH -Name DefaultShell
```

Valor esperado:

```text
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
```

## Alias não funciona no Hermes

```bash
ssh -G awe-stardb3
ssh -vvv awe-stardb3
```

Verificar:

```bash
ls -la ~/.ssh
cat ~/.ssh/config
```

Não exibir conteúdo de chave privada em logs/chat.

## Teste não interativo para Hermes

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 awe-stardb3 'hostname; whoami'
```

`BatchMode=yes` é útil para detectar se a automação ainda depende de senha/prompts.
