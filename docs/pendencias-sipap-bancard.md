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

## 7. Dependência transitiva de módulo Enterprise (achado durante a implementação, fora da lista original)

Durante a implementação do Módulo 1 foi confirmado (via inspeção direta do código-fonte
nos checkouts locais do erplivre-odoo/doodba-express) que `account_batch_payment` é um
módulo **Enterprise** no Odoo 18 (`license: OEEL-1`, localizado em
`odoo/custom/src/enterprise/`), não Community. `l10n_py_account_batch_payment` depende
diretamente dele, e `l10n_py_account_batch_payment_iso20022` depende transitivamente.
Isso:

- Funciona normalmente no ambiente KMEE, porque o `erplivre-odoo` já embarca Enterprise
  (gate `ENTERPRISE_ENABLE`).
- É uma barreira real para um PR público em `OCA/l10n-paraguay` nos termos usuais da
  política da OCA, que evita que módulos community dependam de addons Enterprise.

Isso precisa de uma decisão explícita antes de qualquer submissão de PR real: manter
como está (uso interno KMEE / fork privado), buscar uma alternativa Community para o
conceito de "lote de pagamentos" (reimplementar uma versão mínima própria, fora do
escopo desta rodada), ou confirmar com a comunidade OCA se há precedente aceito para
esse tipo de dependência opcional.
