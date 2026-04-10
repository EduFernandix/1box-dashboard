# 1BOX Self-Storage — Marketing & Operations Dashboard

## O que e a 1BOX?

A [1BOX Self-Storage](https://www.1box.nl/) e uma das maiores empresas de self-storage (deposito/opslagruimte) da Holanda. Fundada em 2017, hoje opera **28 locais** em 9 provincias holandesas, com mais de 10.000 unidades de armazenamento. O modelo e simples: pessoas e empresas alugam boxes de diversos tamanhos para guardar seus pertences, com acesso 365 dias por ano (06h-23h), seguranca com cameras e controle de acesso.

A 1BOX compete num mercado em crescimento, onde a aquisicao digital de clientes (Google Ads, SEO, redes sociais) e tao importante quanto a operacao fisica.

---

## Objetivo do Projeto

Construir um **dashboard centralizado em Streamlit** que unifique dados de marketing, vendas e operacoes da 1BOX. A ideia e que a equipe tenha uma visao unica de performance — desde o clique no anuncio ate a conversao em contrato de aluguel.

### O dashboard vai responder perguntas como:

- Quanto estamos gastando em Google Ads e qual o custo por lead por localizacao?
- Quais paginas do site convertem mais? De onde vem o trafego?
- Qual e a taxa de ocupacao por unidade/local?
- Quais campanhas estao gerando contratos de fato (nao so cliques)?
- Existem anomalias no trafego ou nas conversoes que precisam de atencao?

---

## Arquitetura Geral

```
Google Analytics 4 (GA4)  ──┐
Google Ads                  ──┤
CRM (a definir)             ──┼──▶  ETL Pipeline  ──▶  SQLite/PostgreSQL  ──▶  Streamlit Dashboard
Google Search Console       ──┤
Dados Operacionais          ──┘
```

O sistema funciona em camadas:

1. **Fetchers** — conectores que puxam dados de cada fonte (APIs do Google, CRM, planilhas)
2. **ETL Pipeline** — transforma, limpa e normaliza os dados num banco relacional
3. **Dashboard** — Streamlit com paginas por area (overview, campanhas, trafego, conversoes, alertas)
4. **Alertas** — regras automaticas que notificam a equipe sobre anomalias

---

## Integracoes Necessarias

### Ja planejadas

| Fonte | API / Metodo | Status |
|---|---|---|
| **Google Analytics 4** | `google-analytics-data` (Python SDK) | Em setup |
| **Google Ads** | `google-ads` (Python SDK) | Proximo |
| **Google Search Console** | `google-auth` + REST API | Planejado |

### A explorar

| Fonte | Descricao | Prioridade |
|---|---|---|
| **CRM** | Integracao com o CRM da 1BOX (Salesforce, HubSpot, Pipedrive, ou sistema proprio) para rastrear leads ate contrato | Alta |
| **Google Tag Manager** | Auditoria e configuracao de eventos/tags | Media |
| **Google Business Profile** | Reviews, buscas locais, direcoes | Media |
| **Meta Ads (Facebook/Instagram)** | Se houver campanhas ativas | Baixa |
| **Dados de ocupacao** | Sistema interno ou planilhas com taxa de ocupacao por local | Alta |
| **Dados financeiros** | Receita por local, ticket medio, churn | Media |

---

## Paginas do Dashboard (Planejado)

1. **Overview** — KPIs principais, mapa da Holanda com locais, tendencias
2. **Campanhas** — Performance de Google Ads por campanha, ad group, keyword
3. **Trafego & SEO** — Dados de GA4 + Search Console, paginas mais visitadas
4. **Conversoes** — Funil de conversao, de clique a contrato
5. **Localizacoes** — Performance por unidade/cidade
6. **Alertas** — Anomalias automaticas, quedas de performance

---

## Skills & Conhecimentos Necessarios

Para construir este projeto completo, as seguintes areas de conhecimento sao essenciais:

### Tracking & Analytics
- **Google Analytics 4** — configuracao de propriedade, eventos, dimensoes customizadas, API de dados
- **Google Tag Manager** — container setup, tags, triggers, data layer, debugging
- **Analytics Tracking** — plano de tracking, eventos de conversao, UTM parameters

### Publicidade Paga
- **Google Ads** — API, metricas de campanha, keywords, quality score, ROAS
- **Meta Ads** — caso existam campanhas no Facebook/Instagram

### SEO & Conteudo
- **SEO Audit** — technical SEO, on-page, crawling
- **Google Search Console** — performance de busca, indexacao
- **Schema Markup** — structured data para locais fisicos (LocalBusiness, SelfStorage)

### CRM & Vendas
- **Integracao com CRM** — API do sistema usado, mapeamento de leads/oportunidades
- **Funil de conversao** — de lead a contrato assinado

### Frontend & Visualizacao
- **Streamlit** — componentes, caching, multi-page apps
- **Plotly/Chart.js** — graficos interativos
- **Design de dashboard** — UX para dados, hierarquia de informacao

### Infraestrutura
- **Python** — backend, ETL, data processing
- **SQL** — queries para agregacao e reporting
- **Scheduling** — APScheduler ou cron para atualizacao automatica de dados

---

## Stack Tecnica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Dashboard | Streamlit |
| Graficos | Plotly, Chart.js (frontend HTML existente) |
| Banco de dados | SQLite (dev) → PostgreSQL (prod) |
| APIs Google | `google-analytics-data`, `google-ads`, `google-auth` |
| ETL | Scripts Python customizados |
| Scheduler | APScheduler |
| Deploy | A definir (Streamlit Cloud, VPS, Docker) |

---

## Status Atual

- Existe um **frontend HTML estatico** ([index.html](index.html)) com o visual do dashboard ja desenhado (KPI cards, graficos Chart.js, mapa da Holanda, tabelas por localizacao)
- O codigo Python anterior (Streamlit, fetchers, models, pipeline) foi removido para reconstrucao
- O pacote `google-analytics-data` esta instalado e pronto para uso
- Proximo passo: configurar a conexao real com GA4 e comecar a puxar dados

---

## Referencias

- [1BOX Self-Storage (site oficial)](https://www.1box.nl/)
- [1BOX Self-Storage (English)](https://www.1box.nl/en/)
- [1BOX no LinkedIn](https://nl.linkedin.com/company/1box-self-storage)
- [Google Analytics Data API (Python)](https://cloud.google.com/analytics/devguides/reporting/data/v1/quickstart-client-libraries)
- [Google Ads API (Python)](https://developers.google.com/google-ads/api/docs/client-libs/python)
