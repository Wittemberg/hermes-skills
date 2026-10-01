# Operações e Diretrizes em Servidores com TSplus Remote Access

## Regra Fundamental de Segurança
- **NUNCA** alterar, sobrescrever ou contornar as configurações de restrição de aplicativos do TSplus (`AppControl.ini`, `WinXshell.ini`, `assigned.ini`, `DefApp.ini`).
- **NUNCA** adicionar atribuições coringas globais como `[*] 1=Microsoft Remote Desktop` ou setar `alwaydesktop=yes` para contornar problemas de logon, pois isso concede acesso irrestrito à área de trabalho completa e quebra a segurança/confinamento dos usuários.
- **NUNCA** remover `C:\wsession\logonsession.exe` da chave `Winlogon\Userinit` em ambientes TSplus ativos.

## Causa Raiz de Travamentos no Logon RDP / TSplus
Quando novos logons travam na tela de "Bem-vindo" ou retornam a mensagem de que os serviços de Área de Trabalho Remota estão ocupados, a causa **não** é o controle de aplicativos do TSplus, mas sim deadlocks na pilha do Windows / SCM / RPC:

1. **AppReadiness:**
   - Deadlock do serviço tentando provisionar apps UWP/AppX na sessão.
   - Solução: Desativar serviço (`Set-Service AppReadiness -StartupType Disabled; Stop-Service AppReadiness -Force`).

2. **Smart Card e Propagação de Certificados (`CertPropSvc`, `ScDeviceEnum`, `SCardSvr`):**
   - Retêm threads de RPC e centenas de handles por processo `LogonUI.exe`.
   - Solução: Desativar os 3 serviços (`StartupType Disabled`) e aplicar `fDisableCcm = 1` em `HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp` e `fEnableSmartCard = 0` nas diretivas de Terminal Services.

3. **Serviços Per-User de Sincronização (`CDPUserSvc`, `OneSyncSvc`, `WpnUserService`):**
   - Geram timeouts de 30s no SCM (Event ID 7009/7000).
   - Solução: Configurar `UserServiceFlags = 0` no registro dos templates de serviço.

4. **Catálogo de Criptografia Corrompido (`catroot2`):**
   - Bloqueia validação de assinaturas de binários no logon.
   - Solução: Parar `CryptSvc`, renomear pasta `catroot2` e reiniciar `CryptSvc`.

5. **Animações de Primeiro Logon:**
   - Aplicar `EnableFirstLogonAnimation = 0` em `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System`.
