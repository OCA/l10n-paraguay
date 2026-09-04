# Pendências — SIPAP Batch Payment / Bancard QR

Este documento lista o que **não** foi implementado nesta rodada por depender de
informação que ainda não temos confirmada, e que portanto não deve ser implementado "por
suposição". Nenhum destes itens deve virar código sem que a confirmação/documentação
correspondente exista.

## 1. Documentação de integrador + sandbox da Bancard (API QR/Infonet)

Não temos, e não é pública, a documentação de integrador nem credenciais de sandbox para
o produto **Bancard QR/Infonet (SPI contactless)** — que é diferente do Bancard vPOS 2.0
(tokenização de cartão). Falta:

- Endpoints (base URL de sandbox e produção).
- Payload de geração de QR (campos obrigatórios/opcionais, formato de valor, moeda,
  expiração).
- Algoritmo e chave de assinatura HMAC usados no webhook de notificação.
- Formato exato da notificação de webhook (payload, headers, eventos possíveis).
- Política de retry/idempotência da Bancard em caso de falha de entrega do webhook.

Enquanto isso não existir, `l10n_py_account_payment_bancard_qr` permanece um esqueleto:
`_bancard_generate_qr_payload` levanta `NotImplementedError` e o webhook é fail-closed
por padrão (rejeita tudo, pois não há algoritmo de assinatura confirmado para validar).

## 2. Confirmação com o BCP do limiar SPI vs LBTR e campos obrigatórios do pain.001.001.09 para SIPAP

O exportador ISO 20022 (`l10n_py_account_batch_payment_iso20022`) marca a categoria de
transação (SPI/LBTR) no XML gerado, mas o valor de corte é lido de um parâmetro de
configuração com um default de placeholder — **não é um valor oficial**. Falta:

- Confirmar com o BCP o valor de corte real (e se ele é fixo ou pode variar por
  moeda/tipo de operação).
- Confirmar se o SIPAP exige alguma customização/extensão local sobre o schema genérico
  pain.001.001.09 (campos adicionais, convenções de preenchimento próprias do sistema
  paraguaio) além do que o schema ISO padrão já define.

## 3. Levantamento de layouts proprietários banco a banco

Para os bancos relevantes ao mercado PY / Nexxmed — Itaú PY, Banco Continental, BNF,
Sudameris, Banco Familiar — falta confirmar se o home banking corporativo de cada um
aceita ISO 20022 puro (pain.001.001.09) ou exige um layout proprietário (CSV/TXT
específico do banco). Para os que exigirem layout proprietário, documentar a
especificação completa do layout antes de implementar qualquer exportador específico
daquele banco. Nenhum exportador proprietário foi implementado nesta rodada — o
framework (`l10n_py_account_batch_payment`) já está pronto para recebê-los quando essa
informação existir, via `selection_add` em `res.bank.l10n_py_batch_export_code` e um
método `_l10n_py_export_<codigo>` em `account.batch.payment`.

## 4. Reconciliação de retorno de lote

Falta especificar o formato do arquivo de retorno do banco após o processamento do lote
(pode ser um `pain.002` — status report ISO 20022 — ou um formato proprietário do
banco/Bancard). Sem isso, o envio em lote implementado nesta rodada é "cego": sabemos
gerar e (presumivelmente) enviar o arquivo, mas não temos como confirmar
programaticamente, dentro do Odoo, se cada pagamento foi processado, rejeitado ou está
pendente.

## 5. Extensão do POS OWL para Bancard QR

Depende diretamente do item 1 (protocolo real da Bancard). Não implementada nesta rodada
— está fora de escopo desta rodada por decisão explícita, além de depender de informação
que ainda não existe.

## 6. Fluxo de estorno / timeout de QR dinâmico não pago

Falta especificar o comportamento esperado quando um QR dinâmico gerado expira sem
pagamento, e o fluxo de estorno de um QR pago indevidamente. Depende do item 1 (não há
documentação do produto real para basear esse fluxo).

## 7. ~~Dependência transitiva de módulo Enterprise~~ — RESOLVIDO

~~Durante a implementação do Módulo 1 foi confirmado que `account_batch_payment` é um
módulo Enterprise, do qual `l10n_py_account_batch_payment` dependia diretamente.~~

**Resolvido** (commit `35e7915`): `l10n_py_account_batch_payment` foi migrado para
depender de `account_payment_order` (OCA, repo `bank-payment`), não mais do
`account_batch_payment` Enterprise. Confirmado no manifest e no README do módulo — a
barreira para um PR público em `OCA/l10n-paraguay` está removida. Isso também obrigou a
revisão do ACL de `res.partner.bank`/`res.bank` (ver histórico do módulo) e foi a origem
da migração do dispatch Atlas para o novo framework.

## 8. Módulos Banco Atlas (`l10n_py_account_payment_atlas`, `l10n_py_account_batch_payment_atlas`, `l10n_py_account_payment_exterior_atlas`) — gaps conhecidos não cobertos por este documento

Este documento nasceu antes dos módulos Atlas existirem (o Módulo 1 original era só
SIPAP genérico/Bancard). Os gaps abaixo já estão documentados nos READMEs de cada
módulo, mas ficavam sem referência cruzada aqui — registrando para quem só consulta este
arquivo:

- **Verificação de assinatura da resposta do banco não implementada**
  (`l10n_py_account_payment_atlas`, `AtlasApiClient`): a chave pública do banco
  (`atlas_bank_public_key_pem`) é coletada e armazenada, mas nenhum método verifica a
  assinatura JWT da resposta contra ela — gap documentado no próprio docstring da classe
  e no README do módulo. O esquema de assinatura da resposta (`X-Atl-Auth` no retorno,
  JWT com `content-hash` = SHA256 do corpo, assinado pela chave privada do banco) **está
  documentado** nos PDFs de spec do banco (`docs/backlog/SIPAP/bancoAtlas/` no repo
  `elm-template`) — não é mais um gap "sem informação disponível", é trabalho pendente
  com especificação completa na mão.
- **Estado "Liquidado" (`settled`) do wizard de transferência ao exterior nunca é
  atingido** (`l10n_py_account_payment_exterior_atlas`): não existe endpoint documentado
  de consulta de liquidação para transferências ao exterior (diferente do
  `consultar-pago` que existe para Pago a Proveedores) — confirmado tanto no README do
  módulo quanto nos PDFs de spec do banco. Estado fica só como opção do Selection, sem
  mecanismo de transição.

Nenhum dos dois bloqueia o uso em produção do que já está implementado (dispatch,
reversão, saldo, cron de polling, transferência exterior cotizar/confirmar) — são
lacunas de escopo, não bugs.
