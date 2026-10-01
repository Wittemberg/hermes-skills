# WireGuard + Samba: decisões e endurecimento

## Matriz de exposição

| Necessidade | Configuração | Verificação |
|---|---|---|
| Acesso apenas pela WireGuard | `interfaces = <IP_VPN>/<prefixo>` + `bind interfaces only = yes` | `ss -lntup` mostra somente `<IP_VPN>:445` |
| Sem descoberta legada | `smb ports = 445`, `disable netbios = yes`, `nmbd` parado | Não há TCP 139 nem UDP 137/138 |
| Sem convidados | `map to guest = never`, `guest ok = no`, `valid users` | `smbclient` exige credencial |
| Firewall por túnel | ACCEPT em `-i <wg>` e `-s <rede_vpn>`, DROP em `! -i <wg>` para TCP/445 | `iptables -S`/`nft list ruleset` |
| Persistência | Salvar no mecanismo ativo e ler o arquivo salvo | Regra aparece no arquivo e serviço está habilitado |

## ACL sem alterar ownership

Use ACL quando o caminho pertence a `root` ou a uma aplicação:

```bash
setfacl -m u:smbshare:rwx /root /var/www
setfacl -m d:u:smbshare:rwx /root /var/www
getfacl -cp /root /var/www
```

A ACL padrão afeta objetos novos; ela não corrige automaticamente todos os objetos existentes. Para objetos existentes, aplique permissões por tipo, com uma lista de exclusão para segredos antes de qualquer operação recursiva.

## Regra de teste local

A restrição correta por interface pode fazer `smbclient //IP_VPN/...` executado no próprio servidor falhar, pois o kernel entrega a conexão local por `lo`. O teste prioritário é um cliente conectado à VPN. Se um teste local temporário for indispensável:

```bash
iptables -I INPUT 1 -i lo -p tcp --dport 445 -j ACCEPT
trap 'iptables -D INPUT -i lo -p tcp --dport 445 -j ACCEPT 2>/dev/null || true' EXIT
# execute somente o smbclient aqui
```

Depois confirme que a regra temporária não existe mais e que permanecem somente as regras da VPN.

## Credenciais

- Mantenha o arquivo de credencial `0600`, proprietário `root:root`.
- Não aplique ACL recursiva sobre a pasta de backups sem excluir o arquivo de credencial.
- Nunca coloque senha em `smb.conf`, no chat, no histórico ou em comando registrado.
- Use um usuário separado do administrador SSH/root e `nologin` para reduzir o impacto de vazamento.
