---
name: samba-file-sharing-ops
description: "Use when configuring Samba shares over VPN."
version: 1.0.0
author: Hermes Agent / Forum Telecom
license: MIT
metadata:
  hermes:
    tags: [samba, smb, cifs, linux-file-server, wireguard, vpn, acl, iptables]
    related_skills: [active-directory-ops, docker-ops, opnsense-ops, pfsense-ops]
---
# Samba em Linux com acesso restrito por VPN

Skill para operar Samba em servidores Linux de produção, com foco em compartilhamento para Windows, restrição por WireGuard/OpenVPN, autenticação local, ACLs e validação funcional.

## Regras permanentes

1. Comece sempre por descoberta somente leitura: distribuição, interfaces/rotas VPN, pacotes/serviços Samba, firewall, caminhos e permissões.
2. Faça backup de `smb.conf` e das regras de firewall antes de mudar qualquer configuração; informe os caminhos no relatório.
3. Nunca exponha SMB na interface pública. Restrinja em três camadas: `interfaces`/`bind interfaces only`, firewall por interface/rede VPN e ausência de NetBIOS quando descoberta legada não for necessária.
4. Não use guest. Crie um usuário SMB dedicado, sem shell interativo, com senha guardada em arquivo root-only ou cofre; nunca mostre a senha no chat nem em logs.
5. Preserve permissões existentes. Para árvores com arquivos sensíveis, aplique ACL específica ao usuário do Samba e exclua explicitamente arquivos de credenciais, chaves privadas, tokens, `.env` e backups secretos.
6. Valide sintaxe com `testparm`, estado do serviço, socket de escuta, firewall efetivo e acesso real com `smbclient` antes de concluir.
7. Verifique persistência da regra de firewall em arquivo/serviço de restauração; uma regra aplicada apenas em runtime não é uma solução completa.
8. Não reinicie servidor, container hospedeiro ou túnel VPN para configurar Samba. Reiniciar apenas o daemon Samba quando necessário e reportar a interrupção curta.

## Procedimento padrão

### 1. Descobrir o ambiente

```bash
cat /etc/os-release
ip -brief addr
ip route
wg show                         # se WireGuard for usado
systemctl is-active smbd nmbd 2>/dev/null || true
dpkg-query -W 'samba*' 'smbclient' 2>/dev/null || true
ufw status verbose 2>/dev/null || true
nft list ruleset 2>/dev/null
iptables -S INPUT 2>/dev/null
stat -c '%A %U:%G %n' /caminho/da/pasta
```

Identifique a interface e a rede VPN reais. Não presuma que `wg0`, `10.10.1.0/24` ou qualquer outro nome/endereço exista.

### 2. Fazer backup antes da mudança

```bash
install -d -m 700 /root/backups/samba-setup
cp -a /etc/samba/smb.conf /root/backups/samba-setup/smb.conf.pre-$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
nft list ruleset > /root/backups/samba-setup/nftables.pre-$(date +%Y%m%d-%H%M%S).nft 2>/dev/null || true
iptables-save > /root/backups/samba-setup/iptables.pre-$(date +%Y%m%d-%H%M%S).rules 2>/dev/null || true
```

### 3. Instalar somente o necessário

Em Debian/Ubuntu:

```bash
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y samba smbclient acl iptables-persistent
```

Use `smbclient` para o teste funcional e `acl` quando a árvore compartilhada não puder ter ownership/permissões amplamente alterados.

### 4. Criar identidade SMB dedicada

```bash
useradd --system --no-create-home --shell /usr/sbin/nologin smbshare
```

Crie a senha com entrada mascarada ou um cofre. Para automação não interativa, forneça a senha duas vezes ao `smbpasswd -a -s`; uma única linha pode resultar em `Unable to get new password` e o usuário não entrar no passdb.

```bash
printf '%s\n%s\n' "$SMB_PASSWORD" "$SMB_PASSWORD" | smbpasswd -a -s smbshare
smbpasswd -e smbshare
pdbedit -L
```

Não deixe `SMB_PASSWORD` persistente em histórico, processo ou arquivo sem proteção. Prefira gerar/armazenar a credencial em arquivo `0600` acessível somente ao administrador.

### 5. Configurar Samba mínimo e moderno

Use uma configuração explícita. Exemplo para uma rede VPN `10.10.1.0/24`, endereço VPN do servidor `10.10.1.1`, e dois compartilhamentos:

```ini
[global]
   workgroup = WORKGROUP
   server string = Linux file server
   server role = standalone server
   security = user
   map to guest = never
   guest ok = no

   interfaces = 10.10.1.1/24
   bind interfaces only = yes
   smb ports = 445
   disable netbios = yes
   name resolve order = host

   log file = /var/log/samba/log.%m
   max log size = 1000
   logging = file
   load printers = no
   printing = bsd
   printcap name = /dev/null

[home]
   path = /root
   browseable = yes
   read only = no
   guest ok = no
   valid users = smbshare
   force user = smbshare
   create mask = 0660
   directory mask = 0770
   inherit acls = yes
   nt acl support = yes
   map acl inherit = yes

[www]
   path = /var/www
   browseable = yes
   read only = no
   guest ok = no
   valid users = smbshare
   force user = smbshare
   create mask = 0660
   directory mask = 0770
   inherit acls = yes
   nt acl support = yes
   map acl inherit = yes
```

Antes de iniciar:

```bash
testparm -s
```

Prefira o endereço IP da VPN em `interfaces` quando o daemon abortar ao tentar resolver o nome da interface WireGuard. O parâmetro deve continuar restrito ao endereço VPN; não remova `bind interfaces only`.

### 6. Conceder acesso sem abrir a árvore inteira

Para uma pasta cuja propriedade não deve ser alterada:

```bash
setfacl -m u:smbshare:rwx /root /var/www
setfacl -m d:u:smbshare:rwx /root /var/www
```

A ACL padrão afeta objetos novos; ela não corrige automaticamente todos os objetos existentes. Para objetos existentes, aplique permissões por tipo, com uma lista de exclusão para segredos antes de qualquer operação recursiva. Depois de aplicar ACLs, remova qualquer ACL adicional do arquivo de credencial e restaure `chmod 600`.

### 7. Restringir firewall à VPN

Exemplo iptables para WireGuard `wg0` e rede `10.10.1.0/24`:

```bash
iptables -C INPUT -i wg0 -s 10.10.1.0/24 -p tcp --dport 445 -j ACCEPT 2>/dev/null || \
iptables -I INPUT 1 -i wg0 -s 10.10.1.0/24 -p tcp --dport 445 -j ACCEPT
iptables -C INPUT ! -i wg0 -p tcp --dport 445 -j DROP 2>/dev/null || \
iptables -I INPUT 1 ! -i wg0 -p tcp --dport 445 -j DROP
```

Se NetBIOS estiver desabilitado, não abra UDP 137/138 nem TCP 139. Use acesso direto por `\\10.10.1.1\share` ou DNS interno.

Salve a regra no mecanismo de persistência instalado e leia de volta o arquivo salvo para confirmar a porta 445 nas duas regras. Não declare persistência sem verificar o arquivo e o serviço responsável.

### 8. Habilitar o daemon correto

```bash
systemctl disable --now nmbd
systemctl enable smbd
systemctl restart smbd
systemctl is-active smbd
ss -lntup | grep -E ':(445|139)\\b'
```

O resultado esperado neste perfil é apenas TCP `10.10.1.1:445`; qualquer escuta em `0.0.0.0:445`, interface pública ou porta 139 exige correção antes de concluir.

### 9. Validar funcionalmente

Crie um arquivo de credenciais temporário com modo `0600`, preenchido por cofre ou variável protegida, execute os testes e remova-o ao final:

```bash
umask 077
printf 'username = smbshare\\npassword = %s\\ndomain = WORKGROUP\\n' "$SMB_PASSWORD" > /root/.smbclient-test-credentials
smbclient -L //10.10.1.1 -A /root/.smbclient-test-credentials --option='client min protocol=SMB2'
smbclient //10.10.1.1/www -A /root/.smbclient-test-credentials --option='client min protocol=SMB2' \
  -c 'put /root/samba-verification.txt .samba-verification.txt; dir .samba-verification.txt; del .samba-verification.txt'
rm -f /root/.smbclient-test-credentials
```

O teste deve confirmar autenticação, listar todos os shares esperados e provar escrita/leitura/remoção de um arquivo temporário. Nunca use um arquivo real do usuário como fixture.

Um teste originado no próprio servidor pode ser bloqueado pela regra “somente `wg0`”, porque a conexão sai por `lo`. Nesse caso, prefira testar de um cliente WireGuard. Se for indispensável um teste local, adicione uma exceção temporária para `lo`, use `trap` para removê-la sempre e confirme as regras finais depois.

## Diagnóstico rápido

- `testparm` passa, mas `smbd` aborta ao iniciar: teste `interfaces` com o endereço IP VPN em vez do nome da interface; confirme logs do serviço.
- `NT_STATUS_LOGON_FAILURE`: valide se o usuário Unix existe, se foi adicionado ao passdb com duas linhas de senha e se está habilitado com `pdbedit -L`.
- `NT_STATUS_ACCESS_DENIED`: verifique ACL de todos os diretórios-pai, ACL do arquivo e `valid users`; `force user` não corrige permissão de travessia ausente.
- Timeout local, mas cliente VPN deve funcionar: confira se o firewall permite somente `wg0`; o teste local usa `lo`, não a VPN.
- Porta 139 aberta sem necessidade: pare/desabilite `nmbd`, mantenha `disable netbios = yes` e revalide `ss`.
- Regra sumiu após reboot: leia o arquivo persistente e o status do serviço de restauração; runtime e persistência são estados diferentes.

## Checklist de encerramento

- [ ] Backup de configuração e firewall criado.
- [ ] Usuário SMB dedicado, sem guest e sem shell interativo.
- [ ] `testparm` válido.
- [ ] `smbd` ativo e habilitado.
- [ ] `nmbd` parado quando NetBIOS não é necessário.
- [ ] Socket somente no endereço/interface VPN.
- [ ] Firewall permite 445 somente na VPN e bloqueia fora dela.
- [ ] Persistência da regra verificada por leitura.
- [ ] ACLs não expõem credenciais ou chaves.
- [ ] Listagem e teste de escrita executados com `smbclient`.
- [ ] Caminhos de backup e credencial informados no relatório sem revelar a senha.

Consulte `references/wireguard-samba-hardening.md` para a matriz de decisões e os detalhes de firewall/ACL.