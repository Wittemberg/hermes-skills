---
name: openvpn-site-to-site-ops
description: Use when configuring Linux-MikroTik OpenVPN tunnels.
metadata:
  hermes:
    tags: [openvpn, vpn, site-to-site, mikrotik, linux, routing, firewall]
    related_skills: [forumtelecom/mikrotik-ops]
---

# OpenVPN Site-to-Site Operations

Atue em português do Brasil, de forma direta, com comandos copiáveis e uma linha explicando cada comando. Preserve a separação entre diagnóstico, backup, mudança e validação. Nunca trate um túnel conectado como prova de roteamento funcional: valide o peer, o gateway remoto e um host real da LAN em ambos os sentidos.

## Procedimento obrigatório

### 1. Descobrir os dois lados

No Linux, identifique versão, serviço, interfaces, rotas, forwarding, firewall, porta e logs:

```bash
hostname; uname -a
systemctl status --no-pager openvpn-server@server
ip -4 addr; ip -4 route
sysctl net.ipv4.ip_forward
ss -lunpt | grep -E '1194|openvpn' || true
ufw status verbose
iptables-save
journalctl -u openvpn-server@server --no-pager -n 100
```

No MikroTik, identifique RouterOS, interfaces, endereços, rotas, firewall, bridge e cliente OVPN:

```rsc
/system resource print
/system identity print
/interface print detail
/interface bridge print detail
/interface bridge port print detail
/ip address print detail
/ip route print detail
/interface ovpn-client print detail
/ppp profile print detail
/ip firewall filter print detail stats
/ip firewall nat print detail stats
/log print where topics~"ovpn|route|firewall"
```

Compare literalmente as redes e pares anunciados. Não corrija `10.7.0.0/24` para `10.8.0.0/24` sem confirmar qual rede está ativa em cada ponta.

### 2. Fazer backup antes de alterar

Linux: copie configuração OpenVPN, script de rota, crontab e firewall para um diretório datado e informe o caminho.

```bash
D=/root/backups/openvpn-site-to-site-$(date +%Y%m%d-%H%M%S)
sudo mkdir -p "$D"
sudo cp -a /etc/openvpn/server/server.conf /etc/init.d/criarota.sh "$D"/
sudo crontab -l > "$D/root.crontab"
sudo iptables-save > "$D/iptables.save"
sudo ufw status numbered > "$D/ufw.status"
```

MikroTik: gere export e backup nativo antes da mudança:

```rsc
/export file=pre-openvpn
/system backup save name=pre-openvpn
```

Confirme com `/file print detail` que os dois arquivos foram realmente gravados.

### 3. Escolher topologia e autenticação

Para um único MikroTik usando o servidor Linux como OpenVPN server, use ponto-a-ponto explícito:

```text
Servidor: ifconfig 10.8.0.1 10.8.0.2
MikroTik: endereço dinâmico 10.8.0.2/32 no cliente OVPN
```

Não misture `ifconfig 10.8.0.1 10.8.0.2` com `topology subnet` ou tente forçar `/24` no perfil PPP: o RouterOS pode manter o túnel conectado, mas o peer e as rotas ficam inconsistentes.

Prefira certificado de cliente dedicado, assinado pela mesma CA do servidor, com `extendedKeyUsage=clientAuth`. Não reutilize o certificado do servidor.

No RouterOS 7.17+, `tls-auth` só deve ser usado quando o perfil `.ovpn` inline for importado com sucesso. Para configuração manual do `/interface ovpn-client`, valide primeiro quais propriedades existem na versão exata; em RouterOS 7.23.x, o método validado é mTLS com `certificate=`, `auth=sha256` e `cipher=aes256-cbc`, sem depender de `tls-auth` manual.

### 4. Configurar o servidor Linux

Configuração mínima validada para TCP e cliente RouterOS:

```conf
port 1194
proto tcp4-server
dev tun01
tls-server
ifconfig 10.8.0.1 10.8.0.2
ca /etc/openvpn/server/ca.crt
cert /etc/openvpn/server/server.crt
key /etc/openvpn/server/server.key
dh /etc/openvpn/server/dh2048.pem
auth SHA256
cipher AES-256-CBC
route 192.168.254.0 255.255.255.0 10.8.0.2
keepalive 10 120
persist-key
persist-tun
user nobody
group nogroup
status openvpn-status.log
log server.log
verb 3
```

Habilite forwarding de forma persistente e permita o tráfego VPN↔LAN no firewall. Evite regras duplicadas de masquerade; entre duas redes roteadas, preserve os IPs e faça NAT apenas se a LAN não tiver rota de retorno.

### 5. Configurar rota principal e fallback

A diretiva `route` do OpenVPN deve ser a rota principal. O fallback precisa ser idempotente e condicionado à existência do túnel:

```sh
#!/bin/sh
set -eu
VPN_IF=tun01
LAN_NET=192.168.254.0/24
VPN_PEER=10.8.0.2
if ip link show "$VPN_IF" >/dev/null 2>&1; then
    ip route replace "$LAN_NET" via "$VPN_PEER" dev "$VPN_IF"
fi
```

Use somente uma tarefa recorrente e uma tarefa de boot para o fallback. Não mantenha linhas duplicadas com `sudo route add` e `route add`: elas acumulam erros e rotas redundantes.

### 6. Configurar o MikroTik

Para o hEX com LAN em ether3-5:

Se a WAN estiver em DHCP durante a preparação, faça a migração em duas fases: crie primeiro o IP fixo e a rota padrão, confirme acesso pelo novo IP, e só então desabilite o DHCP client. Nunca remova ou desabilite o único endereço de gerenciamento antes de ter um caminho de acesso alternativo; uma troca de endereço pode derrubar a sessão SSH no meio da sequência. Depois da validação, desabilite endereços estáticos antigos para evitar IP duplicado, preservando-os durante a janela de rollback.

```rsc
/interface bridge add name=bridge-lan comment="LAN ether3-5"
/interface bridge port add bridge=bridge-lan interface=ether3
/interface bridge port add bridge=bridge-lan interface=ether4
/interface bridge port add bridge=bridge-lan interface=ether5
/ip address add address=192.168.254.1/24 interface=bridge-lan
```

Cliente OVPN manual validado:

```rsc
/ppp profile add name=profileVPNKW local-address=10.8.0.2 remote-address=10.8.0.1 change-tcp-mss=yes
/interface ovpn-client add name=ovpn-KRONIC connect-to=190.102.42.72 port=1194 protocol=tcp mode=ip user=ChangeMe password=unused profile=profileVPNKW certificate=ovpn-client.crt_0 auth=sha256 cipher=aes256-cbc add-default-route=no route-nopull=yes disabled=no
```

Ajuste o nome real do certificado importado; confirme-o com `/certificate print` antes de criar a interface.

Não adicione uma rota para `192.168.254.0/24` no MikroTik quando essa é a própria LAN local: o endereço conectado à bridge já cria a rota diretamente. A rota desse prefixo deve existir no servidor Linux apontando para o peer OVPN. No MikroTik, adicione apenas rotas para redes realmente remotas; para alcançar o peer do servidor em P2P, uma rota host explícita pode ser necessária:

```rsc
/ip route add dst-address=10.8.0.1/32 gateway=ovpn-KRONIC comment="VPN SERVER PEER"
```

### 7. Firewall e retorno

Permita em ambos os sentidos, restrito às redes do túnel e da LAN:

```rsc
/ip firewall filter add chain=forward action=accept src-address=10.8.0.0/24 dst-address=192.168.254.0/24 comment="VPN -> LAN"
/ip firewall filter add chain=forward action=accept src-address=192.168.254.0/24 dst-address=10.8.0.0/24 comment="LAN -> VPN"
```

No servidor Linux, permita `10.8.0.0/24` e `192.168.254.0/24` conforme o fluxo necessário. Atualize regras antigas da rede VPN somente depois de confirmar a rede efetiva.

### 8. Validar em camadas

1. Serviço e interface:

```bash
systemctl is-active openvpn-server@server
ip -4 addr show tun01
ip route show 192.168.254.0/24
```

2. Peer do túnel:

```bash
ping -c 4 -W 2 10.8.0.2
```

3. Gateway LAN a partir do servidor:

```bash
ping -c 4 -W 2 192.168.254.1
```

4. No MikroTik:

```rsc
/interface ovpn-client print detail
/ping 10.8.0.1 count=4
/ping 192.168.254.1 count=4
/ip route print detail
```

5. Host real da LAN: teste um computador em `192.168.254.31-199`. Sem link físico nas portas LAN, declare que somente gateway, túnel e DHCP foram validados; não declare acesso a PCs.

6. Verifique contadores das regras e logs OpenVPN. Conexão TLS sem pacotes ICMP ou sem contadores de `forward` não comprova conectividade.

## Armadilhas recorrentes

- Ao trocar WAN DHCP por IP fixo, mantenha o DHCP client desabilitado e confirme `ip address`, rota padrão, gateway e acesso pelo novo IP em uma nova sessão antes de encerrar a janela de mudança.
- Não declare a migração de WAN concluída apenas porque o IP fixo apareceu: teste gateway e um destino externo, e confirme que o DHCP client está `disabled`/`stopped`.
- Compare os endereços efetivamente ativos antes de editar: túnel `10.7.0.0/24` e objetivo `10.8.0.0/24` são configurações diferentes.
- Preserve P2P quando o servidor usa `ifconfig local remote`; adicionar `topology subnet` isoladamente pode quebrar o endereço dinâmico `/32` do RouterOS.
- Não use `certificate=none` quando o servidor exige certificado de cliente; a sessão pode falhar antes de qualquer teste de rota.
- Não confunda o flag `I` do cabeçalho de `/ip firewall ... print` com uma regra inválida; leia `print detail` da própria regra e valide contadores.
- Não exponha senhas, chaves privadas, `ca.key` ou conteúdo completo de certificados no relatório; informe apenas nomes, estado e caminho protegido do backup.
- Em RouterOS, nomes renomeados devem ser usados posteriormente: se `ether5` foi renomeada para `ether5-lan`, a porta da bridge deve referenciar `ether5-lan`.
- Valide a opção `route-nopull` após a conexão: se estiver `yes`, instale somente rotas de redes remotas manualmente; nunca adicione uma rota redundante para a própria LAN conectada.
- Depois de trocar a WAN, valide novamente o túnel: o cliente pode continuar marcado como `R` enquanto a sessão antiga ou a rota de retorno ainda está instável.
- Compare o CN do certificado observado no log/status OpenVPN com o certificado configurado no MikroTik; uma conexão TLS usando um cliente antigo não comprova que o certificado novo foi usado.
- Não declare o site-to-site concluído se o teste ao peer, ao gateway LAN e a um host real da LAN não tiverem sido executados nos dois sentidos.

## Relatório final

Informe em português:

- configuração aplicada e endpoints;
- caminho dos backups;
- estado do serviço e da interface OVPN;
- testes com perda, rota e contadores;
- o que não foi testado por falta de link/host real;
- pendências de produção, especialmente validação do certificado do servidor por SAN/CN e rotação de credenciais.

Para aprofundamento ocasional, consulte `references/linux-mikrotik-routing.md`.
