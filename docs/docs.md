# Worker / /worker/jobs
- Motor que decide quando correr coisas (ex.: ingerir supplier X a cada N minutos).
- Trabalha com worker_job.

# Ingest / /runs

- Lógica concreta do trabalho (ex.: ingest_supplier).
- Pode ser chamada:
  - pelo worker (automático)
  - ou manualmente via /runs (para debugging/forçar).

# Atualizações para a loja /catalog-update-stream

- Saída do sistema: “isto mudou, vai aplicar no Prestashop”.
- Fila de mensagens para consumidores externos.

# Resumo

- /worker/jobs = painel do cron/queue (tipo Horizon do Laravel, Sidekiq UI, etc.)
- /runs = endpoint “executa esta tarefa agora, à frente”.
- /catalog/update-stream = tabela/fila onde sai o payload final para o Prestashop.
