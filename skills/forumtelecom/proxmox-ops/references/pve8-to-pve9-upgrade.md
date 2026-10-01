# Upgrade Proxmox VE 8.4 para 9.x

Use somente o guia oficial `https://pve.proxmox.com/wiki/Upgrade_from_8_to_9` e confirme a versão estável atual antes de agir.

## Fluxo obrigatório

1. Confirme nó standalone/cluster, ausência ou migração de guests, storage, espaço de root, console fora de banda e repositórios.
2. Atualize primeiro o PVE 8.4 e execute `pve8to9 --full` até não haver falhas.
3. Faça backup timestampado de `/etc`, `/etc/pve`, rede, APT, bootloader, Fail2ban, banco do pmxcfs e lista de pacotes; copie para outro host e valide SHA-256.
4. Em UEFI+GRUB, se o checker apontar `systemd-boot`, simule a remoção e obtenha confirmação antes de remover apenas o meta-pacote.
5. Migre valores ativos de `/etc/sysctl.conf` para `/etc/sysctl.d/*.conf`; PVE 9 não lê mais o arquivo legado.
6. Se a origem SSH usa Fail2ban, persista o IP confiável em `ignoreip` antes do upgrade; um reload/reboot remove exceções aplicadas apenas via `fail2ban-client`.
7. Troque Debian Bookworm por Trixie e configure o repositório PVE 9 correto. Preserve fontes antigas renomeando para `.disabled` em vez de apagá-las.
8. Rode `apt update`, `apt policy` e `apt-get -s dist-upgrade`. Interrompa se `proxmox-ve` for removido.
9. Execute o `dist-upgrade` dentro de `tmux`, `screen` ou `dtach`. Em host customizado, preserve conffiles com `--force-confold` e revise os arquivos `.dpkg-dist`/`.ucf-dist` depois.
10. Antes do reboot, valide `apt-get check`, `dpkg --audit`, serviços PVE, SSH, rede, GRUB e presença do kernel novo.
11. Reinicie somente com autorização explícita.
12. Depois do reboot, valide kernel, `pveversion -v`, `pve8to9 --full`, APT, serviços, NTP, storage, rede, SSH e HTTPS 8006.

## Armadilhas verificadas

- O pacote pode recriar `pve-enterprise.sources`; em host sem assinatura, desative-o e repita `apt update` até não haver erro 401.
- Chrony pode levar cerca de um minuto após o boot para resolver e selecionar as fontes; confirme com `chronyc sources -v` e `chronyc tracking` antes de diagnosticar falha.
- `ssh-keyscan` abre várias conexões e pode acionar Fail2ban; prefira uma conexão com `StrictHostKeyChecking=accept-new` quando a confiança inicial já foi aprovada.
- Não remova kernels antigos nem arquivos RRD legados durante o upgrade; faça essa limpeza em mudança separada e confirmada.
- Patches locais para remover o aviso de assinatura modificam arquivos do pacote e aparecem em `dpkg -V`; reporte, não remova sem autorização.

## Critério de sucesso

- PVE e Debian nas versões-alvo, kernel novo em execução.
- `pve8to9 --full` sem warnings/failures relevantes.
- `apt update`, `apt-get check` e `dpkg --audit` limpos.
- Nenhuma unit falhou; PVE, SSH, Fail2ban, NTP e storage ativos.
- Gerência SSH e HTTPS 8006 acessíveis externamente.
- Backups pré e pós-upgrade copiados e verificados fora do nó.
