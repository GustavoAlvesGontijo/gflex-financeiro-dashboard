# 💰 GFlex Financeiro — Dashboard

Dashboard executivo das 7 empresas da aliança GFlex, consumindo as planilhas consolidadas de Pagamentos e Recebimentos.

## Arquitetura de Dados

Este repo é **público** (só código). Os dados ficam em repo **privado** separado:
- `gflex-financeiro-dashboard` (público) — código Streamlit
- `gflex-financeiro-data` (privado) — apenas xlsx consolidados

O loader baixa os xlsx via GitHub API autenticada (Personal Access Token nos secrets do Streamlit Cloud). **Dados nunca ficam expostos publicamente.**

## Rodar localmente

```bash
cd C:\BI-GFlex\dashboard
streamlit run app.py --server.port 8502
```

Fallback: se não houver secret `[github]`, lê do OneDrive local (`C:\Users\Gustavo Gontijo\OneDrive\GFlex Financeiro\`).

## Deploy no Streamlit Cloud

### 1. Criar links públicos dos 2 xlsx no OneDrive

Para cada arquivo em `C:\Users\Gustavo Gontijo\OneDrive\GFlex Financeiro\`:
- `União de Pagamentos.xlsx`
- `União de Recebimentos.xlsx`

**Passos:**
1. Botão direito no arquivo → **Compartilhar**
2. Clique em **"Qualquer pessoa com o link pode ver"** (ou "Específicos" se quiser restringir)
3. **Copiar link**
4. **IMPORTANTE:** troque o final do link de `?e=xxx` para `?download=1` — isso força download direto do xlsx (ao invés de abrir preview no OneDrive)

Exemplo:
- Link original: `https://1drv.ms/x/s!Abcd123?e=xyz`
- Link ajustado: `https://1drv.ms/x/s!Abcd123?download=1`

### 2. Publicar no Streamlit Cloud

1. Acesse https://share.streamlit.io
2. Login com a mesma conta GitHub (Gustavo)
3. **New app** → selecione o repo `gflex-financeiro-dashboard`
4. Branch: `master`
5. Main file: `app.py`
6. Python: 3.12

### 3. Configurar Secrets

Em **Advanced settings → Secrets**, cole:

```toml
[app]
password = "a_senha_que_juliano_vai_usar"

[data]
URL_PAGAMENTOS = "https://1drv.ms/.../?download=1"
URL_RECEBIMENTOS = "https://1drv.ms/.../?download=1"
```

### 4. Deploy

Clicar em **Deploy!**. Em ~2 min o app estará em `https://gflex-financeiro-XXXXX.streamlit.app/`

## Compartilhar com Juliano

1. Envie o link do app
2. Envie a senha configurada no secret `[app][password]`
3. Como o cache é de 5min, dados atualizam automaticamente conforme o script de consolidação roda no PC do Gustavo (a cada 30min)

## Arquitetura

```
PC do Gustavo (00:00, 00:30, 01:00, ...)
  ├── 04_consolidar_tudo.py lê 16 xlsx do servidor 192.168.10.200
  └── grava 2 xlsx consolidados no OneDrive

OneDrive do Gustavo
  └── 2 xlsx acessíveis via link público

Streamlit Cloud
  └── dashboard baixa via HTTPS a cada 5min (cache TTL)
      ├── aplica filtros globais (empresa, período, base de data)
      └── renderiza 9 páginas pra Juliano + Gustavo
```

## Páginas

| Página | Uso |
|---|---|
| **Home** | Tabela resumo por empresa + totais consolidados |
| **Painel do Dia** | Movimentação de dia/intervalo + detalhes |
| **Por Empresa** | Multi-seleção, exercício somado, plano de contas |
| **Fluxo de Caixa** | 4 seções: consolidado, por empresa, matriz, individual |
| **Projeção & Simulação** | Futuro por TIPO (Fixo/Var/Orç/Provisão) + simulador de atraso |
| **Atrasos** | Pagamentos atrasados + Inadimplência com sistema de "Ignorar" |
| **DRE** | Receita/Despesa/Resultado com filtros próprios |
| **Auditoria** | Erros de preenchimento nas planilhas |
| **Glossário** | Fórmula de cada KPI |

## Troubleshooting

- **"Fonte de dados não configurada"**: secrets faltando no Streamlit Cloud.
- **Dashboard lento ao carregar**: OneDrive pode demorar na primeira request. Após isso, cache de 5min é instantâneo.
- **Dados desatualizados**: aperte **🔁 Recarregar** na sidebar pra limpar cache e forçar re-download.
- **Erro 404 ao baixar**: link OneDrive expirou ou foi removido. Regenere e atualize secret.
