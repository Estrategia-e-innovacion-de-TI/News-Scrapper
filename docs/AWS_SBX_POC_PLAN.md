# PLAN DE DESPLIEGUE AWS SBX PoC — News Radar MVP

**Fecha:** 2026-03-16  
**Objetivo:** Despliegue cost-efficient en AWS Sandbox para validación del sistema.  
**Presupuesto objetivo:** < $50 USD/mes

---

## 1. Arquitectura AWS

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS SBX Account                       │
│                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────────┐ │
│  │ EventBridge  │────▶│ ECS Fargate  │────▶│ S3 Bucket   │ │
│  │ (Scheduler)  │     │ (Task)       │     │ (Artifacts) │ │
│  └──────────────┘     └──────┬───────┘     └─────────────┘ │
│                              │                              │
│                              ▼                              │
│                    ┌──────────────────┐                     │
│                    │ Secrets Manager  │                     │
│                    │ (API keys)       │                     │
│                    └──────────────────┘                     │
│                              │                              │
│                              ▼                              │
│                    ┌──────────────────┐                     │
│                    │ SNS Topic        │                     │
│                    │ (Notifications)  │                     │
│                    └────────┬─────────┘                     │
│                             │                               │
│                             ▼                               │
│                    ┌──────────────────┐                     │
│                    │ Email (SES/SNS)  │                     │
│                    └──────────────────┘                     │
│                                                              │
│  ┌──────────────┐                                           │
│  │ ECR          │  ← Docker image del pipeline              │
│  │ (Registry)   │                                           │
│  └──────────────┘                                           │
│                                                              │
│  ┌──────────────┐                                           │
│  │ CloudWatch   │  ← Logs + métricas                        │
│  │ (Monitoring) │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Justificación: ECS Fargate vs Lambda

| Criterio | Lambda | ECS Fargate | Decisión |
|----------|--------|-------------|----------|
| Timeout | 15 min max | Sin límite | **Fargate** ✓ |
| Memoria | 10 GB max | Configurable | Fargate |
| Playwright | Difícil (layer size) | Docker nativo | **Fargate** ✓ |
| Cold start | ~2-5s | ~30-60s | Lambda |
| Costo idle | $0 | $0 (task-based) | Empate |
| Complejidad | Baja | Media | Lambda |

**Decisión:** ECS Fargate. El pipeline puede exceder 15 min con muchas fuentes, y Playwright requiere un entorno Docker completo.

**Alternativa económica:** Para runs cortos (adhoc < 5 min, sin Playwright), Lambda es viable como segunda opción.

---

## 3. Componentes

### 3.1 Docker Image

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright (opcional, solo si se necesita)
RUN pip install playwright && playwright install chromium --with-deps

COPY extractor/ extractor/
COPY catalog.yaml terms_vigilancia.yaml ./

ENTRYPOINT ["python", "-m", "extractor.main"]
```

**Tamaño estimado:** ~800 MB (con Playwright), ~200 MB (sin Playwright)

### 3.2 S3 Bucket Structure

```
s3://news-radar-sbx-artifacts/
├── aras/
│   └── YYYY-MM-DD/
│       ├── articles.jsonl
│       ├── run_report.json
│       └── results.xlsx
├── riesgos/
│   └── YYYY-MM-DD/
│       ├── articles.jsonl
│       ├── run_report.json
│       └── results.xlsx
├── vigilancia/
│   ├── weekly/
│   │   └── YYYY-WNN/
│   │       ├── articles.jsonl
│   │       ├── run_report.json
│   │       └── top10_summary.md
│   └── historical/
│       └── YYYY-QN/
│           ├── candidates.jsonl
│           ├── clusters.json
│           └── powerbi_data.json
├── search/
│   ├── papers/
│   ├── repos/
│   └── patents/
└── reports/
    └── run_history.jsonl
```

### 3.3 Secrets Manager

| Secret | Contenido | Uso |
|--------|-----------|-----|
| `news-radar/github-token` | GITHUB_TOKEN | Search repos |
| `news-radar/openai-key` | OPENAI_API_KEY | Clasificación LLM (futuro) |
| `news-radar/smtp-config` | host, port, user, pass | Email newsletters (futuro) |

### 3.4 EventBridge Schedules

| Schedule | Cron | Comando |
|----------|------|---------|
| Vigilancia News Semanal | `cron(0 6 ? * MON *)` | `--focus vigilancia_news --days 7` |
| Search Papers | `cron(0 6 1 * ? *)` | `--mode papers --since-days 30` |
| Search Repos | `cron(0 8 1 * ? *)` | `--mode repos --since-days 30` |
| Search Patents | `cron(0 6 1 1,4,7,10 ? *)` | `--mode patents --since-days 90` |

Nota: ARAS y Riesgos son ad-hoc (bajo demanda), no programados.

### 3.5 SNS Notifications

- Topic: `news-radar-alerts`
- Suscriptores: email del equipo
- Eventos: run_failed, run_completed (opcional), degradation_detected

---

## 4. Estimación de Costos

### 4.1 ECS Fargate

| Recurso | Configuración | Uso estimado | Costo/mes |
|---------|---------------|-------------|-----------|
| vCPU | 0.5 vCPU | ~4 runs/semana × 10 min = 2.7 hrs/mes | ~$0.10 |
| Memoria | 1 GB | ~2.7 hrs/mes | ~$0.03 |
| **Subtotal Fargate** | | | **~$0.13** |

### 4.2 Otros Servicios

| Servicio | Uso estimado | Costo/mes |
|----------|-------------|-----------|
| S3 | ~100 MB storage + requests | ~$0.05 |
| ECR | 1 image ~800 MB | ~$0.08 |
| Secrets Manager | 3 secrets | ~$1.20 |
| CloudWatch Logs | ~500 MB/mes | ~$0.25 |
| EventBridge | ~20 invocaciones/mes | ~$0.00 |
| SNS | ~50 notificaciones/mes | ~$0.00 |
| **Subtotal otros** | | **~$1.58** |

### 4.3 LLM (futuro, estimación)

| Provider | Uso estimado | Costo/mes |
|----------|-------------|-----------|
| OpenAI GPT-4o-mini | ~50 docs × 2K tokens input + 500 output | ~$0.50 |
| Bedrock Claude Haiku | ~50 docs × 2K tokens | ~$0.30 |

### 4.4 Total Estimado

| Componente | Costo/mes |
|------------|-----------|
| Fargate | $0.13 |
| Servicios AWS | $1.58 |
| LLM (futuro) | $0.50 |
| **TOTAL** | **~$2.21** |

Muy por debajo del presupuesto de $50/mes. Hay margen para escalar.

---

## 5. IaC (Infrastructure as Code)

### Opción recomendada: AWS CDK (Python)

```
infra/
├── app.py                    # CDK app entry point
├── stacks/
│   ├── pipeline_stack.py     # ECS Fargate + ECR + EventBridge
│   ├── storage_stack.py      # S3 + Secrets Manager
│   └── monitoring_stack.py   # CloudWatch + SNS
├── cdk.json
└── requirements.txt
```

### Alternativa: SAM (Serverless Application Model)

Si se opta por Lambda para runs cortos:

```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  ExtractorFunction:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: python3.12
      Handler: lambda_handler.handler
      Timeout: 900
      MemorySize: 1024
      Events:
        WeeklySchedule:
          Type: Schedule
          Properties:
            Schedule: cron(0 6 ? * MON *)
```

---

## 6. Pipeline CI/CD

```
GitHub Push → GitHub Actions → Build Docker → Push ECR → Update ECS Task Definition
```

### GitHub Actions Workflow

```yaml
name: Deploy to AWS SBX
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2
      - name: Build and push Docker image
        run: |
          docker build -t news-radar .
          docker tag news-radar:latest $ECR_REGISTRY/news-radar:latest
          docker push $ECR_REGISTRY/news-radar:latest
      - name: Update ECS task definition
        run: aws ecs update-service --cluster news-radar --service extractor --force-new-deployment
```

---

## 7. Seguridad

- IAM roles con least privilege (ECS task role solo accede a S3, Secrets Manager, SNS)
- Secrets Manager para todas las credenciales (no env vars)
- VPC con subnets privadas para Fargate tasks
- S3 bucket con encryption at rest (SSE-S3)
- CloudWatch Logs con retention de 30 días
- No exponer endpoints públicos en SBX

---

## 8. Pasos de Implementación

1. Crear cuenta AWS SBX (o usar existente)
2. Crear ECR repository
3. Build y push Docker image
4. Crear S3 bucket con estructura de prefijos
5. Crear Secrets Manager entries
6. Crear ECS cluster + task definition + service
7. Crear EventBridge schedules
8. Crear SNS topic + suscripciones
9. Crear CloudWatch dashboards
10. Validar con run manual: `aws ecs run-task --cluster news-radar --task-definition extractor`
