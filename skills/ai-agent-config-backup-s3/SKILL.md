---
name: ai-agent-config-backup-s3
description: "Use when maintaining AI agent config backups to S3."
---

# Backup de configuracoes de agentes para S3

## Instalacao (perfil default)
- Script: /root/.local/bin/ai-config-backup (Python stdlib + AWS CLI).
- Origens: /root/.config/ai-config-backup/config.json.
- Testes: /root/.config/ai-config-backup/test_backup.py.
- Manual: /root/backups/ai-config-backup/README.txt.
- Status: /root/backups/ai-config-backup/last-success.json.
- Cron: /etc/cron.d/ai-config-backup; last-run.log na pasta do manual.
- Bucket: witt-hermes-bkp, conta 403052873442, us-east-1. Confirmar estado real.
- Escopo adicional atual: Samba em /etc/samba e /var/lib/samba; credencial root-only em /root/backups/samba-setup/smbshare-credentials.txt; WireGuard em /etc/wireguard; materiais OpenVPN em /root/server.conf.openvpn-mikrotik, /root/crontab.openvpn-mikrotik e /root/ovpn-client.crt; firewall persistente em /etc/iptables/rules.v4.
- Esses arquivos contêm chaves, certificados, hashes ou senhas: tratar todo pacote restaurado como segredo operacional.

## Procedimento
1. Carregar aws-storage e hermes-agent. Ler config, manual, status e cron sem expor segredos.
2. Validar identidade AWS, dono esperado, Lifecycle de 7 dias, ausencia de Status no versionamento, Block Public Access e criptografia. Nunca habilitar e depois suspender versionamento se o requisito e nunca versionado.
3. Rodar --dry-run. Escopo e allowlist; novas configuracoes fora das origens nao sao incluidas automaticamente. Nao incluir outros perfis sem autorizacao. Confirmar no inventario as origens de Samba, WireGuard, OpenVPN e firewall quando presentes.
4. Rodar python3 /root/.config/ai-config-backup/test_backup.py, quando o arquivo existir. Exigir falha para origem obrigatoria ausente ou sem arquivos incluidos.
5. Executar backup; conferir download, manifesto, checksums e status. Testar agendamento com ambiente reduzido equivalente ao cron.
6. Restaurar somente em diretorio privado novo, nunca em / ou configuracoes ativas. Verificar checksum e caminhos do tar antes de extrair. Credenciais Samba, chaves WireGuard, chaves/certificados OpenVPN e regras de firewall exigem revisão antes de qualquer restauração em produção.

## Cuidados
- ~/.local/bin/agy e binario grande; AGY usa ~/.gemini/antigravity-cli/. Incluir settings/token, nao binario/cache/conversations por padrao.
- Skills coexistem em Hermes, ~/.agents, ~/.claude e ~/.codex. Materializar links com deteccao de ciclos e destinos fora do escopo.
- SQLite selecionado usa sqlite3.backup e integrity_check para incluir WAL; nao copiar banco vivo isolado.
- Segredos dos agentes, Samba e VPNs estao no pacote: diretorios 0700, arquivos sensiveis 0600, bucket privado e HTTPS. AWS/SSH ficam fora; acesso AWS deve ser recuperavel separadamente.
- O escopo de VPN inclui /etc/wireguard, arquivos OpenVPN declarados na allowlist e, quando configurado, material de clientes; nao assumir que toda a arvore /etc/openvpn existe.
- O escopo de Samba inclui smb.conf, banco passdb/secrets em /var/lib/samba e a credencial SMB armazenada no backup local; nao expor conteudo desses arquivos no relatorio.
- O escopo de firewall inclui /etc/iptables/rules.v4; regras runtime podem divergir se nao forem persistidas nesse arquivo.
- Perfil AWS default existente e administrativo; recomendar identidade dedicada de menor privilegio. Nao imprimir nem incluir chaves AWS no pacote.
- Expiration Days=7 usa calendario UTC e processamento assincrono; nao prometer exclusao exatamente apos 168 horas. Conferir HeadObject Expiration.
- Nomes unicos e If-None-Match evitam sobrescrita sem versionamento. Usar S3 Standard para janela curta. Download integral de verificacao pode gerar transferencia cobrada.
- Cron grava log local; nao prometer alerta remoto inexistente.
- write_file pode recusar /etc: preparar arquivo na pasta da tarefa e usar install apos inspecionar destino. Falha de web_extract nao justifica mudar configuracao global; usar HTTP de leitura como alternativa.
