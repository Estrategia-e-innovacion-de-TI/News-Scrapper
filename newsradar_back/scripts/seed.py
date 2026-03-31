"""Seed the PostgreSQL database with sample data."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import random
from datetime import datetime, timedelta

import yaml
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from newsradar_api.infrastructure.driven_adapters.db_models import (
    Base, Document, Cluster, Trend, Topic, Subscription,
    EvidenceSpan, PipelineRun, TrendmapSnapshot,
)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://newsradar:newsradar@localhost:5432/newsradar"
)


async def seed():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Topics — from terms_vigilancia.yaml
        terms_path = os.path.join(os.path.dirname(__file__), "..", "..", "shared", "terms_vigilancia.yaml")
        with open(terms_path) as f:
            terms_data = yaml.safe_load(f)

        DISPLAY_NAMES = {
            "ia_ml": "IA y Machine Learning",
            "blockchain": "Blockchain y DeFi",
            "computacion_cuantica": "Computación Cuántica",
            "ciberseguridad": "Ciberseguridad",
            "fintech": "Fintech",
            "cloud_datos": "Cloud y Datos",
            "banca_digital": "Banca Digital",
            "papers": "Papers Académicos",
            "repos": "Repositorios GitHub",
            "patents": "Patentes",
        }
        topics = []
        for group_id, group_data in terms_data.items():
            terms_list = group_data.get("terms", [])
            display_name = DISPLAY_NAMES.get(group_id, group_id.replace("_", " ").title())
            topics.append(Topic(group_id=group_id, display_name=display_name, term_count=len(terms_list)))
        session.add_all(topics)

        # ARAS Documents
        aras_docs = []
        companies = ["Ecopetrol", "Bancolombia", "Grupo Argos", "ISA", "Nutresa"]
        aras_categories = ["Lavado de activos", "Fraude", "Corrupción", "Ambiental", "Social"]
        sources = ["eltimepo", "elcolombiano", "infobae", "larepublica"]
        for i in range(30):
            company = random.choice(companies)
            cat = random.choice(aras_categories)
            src = random.choice(sources)
            text_body = f"Análisis de riesgo ARAS para {company}. Hallazgos relevantes en categoría {cat}."
            aras_docs.append(Document(
                run_id=f"aras-run-{i:04d}",
                source_id=src,
                pipeline_class="news",
                title=f"Noticia ARAS #{i+1}: {company} - {cat}",
                url=f"https://example.com/aras/{i+1}",
                published_at=datetime.now() - timedelta(days=random.randint(1, 90)),
                fetched_at=datetime.now(),
                text=text_body,
                excerpt=text_body[:200],
                raw_len=len(text_body),
                text_len=len(text_body),
                hash=f"aras-hash-{i:06d}",
                fetch_method="http",
                query_type="aras",
                category=cat,
                severity=random.choice(["H", "M", "L"]),
                severity_confidence=round(random.uniform(0.3, 1.0), 2),
                relevance_score=random.randint(40, 100),
            ))
        session.add_all(aras_docs)

        # Riesgos Documents
        riesgos_docs = []
        presets = ["ciber", "fraude", "operacional", "ambiental_social"]
        for i in range(25):
            preset = random.choice(presets)
            text_body = f"Análisis de riesgo emergente en categoría {preset}."
            src = random.choice(["darkreading", "securityweek", "cyberscoop", "hackernews"])
            riesgos_docs.append(Document(
                run_id=f"riesgos-run-{i:04d}",
                source_id=src,
                pipeline_class="news",
                title=f"Riesgo Emergente #{i+1}: {preset.replace('_', ' ').title()}",
                url=f"https://example.com/riesgos/{i+1}",
                published_at=datetime.now() - timedelta(days=random.randint(1, 60)),
                fetched_at=datetime.now(),
                text=text_body,
                excerpt=text_body[:200],
                raw_len=len(text_body),
                text_len=len(text_body),
                hash=f"riesgos-hash-{i:06d}",
                fetch_method="http",
                query_type="riesgos",
                category=preset.replace("_", " ").title(),
                severity=random.choice(["H", "M", "L"]),
                severity_confidence=round(random.uniform(0.3, 1.0), 2),
                relevance_score=random.randint(40, 100),
            ))
        session.add_all(riesgos_docs)

        # Clusters
        clusters = [
            Cluster(
                cluster_id="c1", label="IA Generativa en Banca",
                category="Inteligencia Artificial",
                summary="Adopción de modelos generativos para atención al cliente y análisis de riesgo.",
                keywords=["LLM", "chatbot", "GPT", "banca digital"], item_count=42,
                impact_score=0.92, horizon_score=0.7, avg_score=0.85,
                x_embed=0.3, y_embed=0.8, relevance="alta",
            ),
            Cluster(
                cluster_id="c2", label="Ciberseguridad Zero Trust",
                category="Ciberseguridad",
                summary="Implementación de arquitecturas zero trust en el sector financiero.",
                keywords=["zero trust", "SASE", "microsegmentación"], item_count=28,
                impact_score=0.85, horizon_score=0.5, avg_score=0.78,
                x_embed=-0.2, y_embed=0.4, relevance="alta",
            ),
            Cluster(
                cluster_id="c3", label="Blockchain y Tokenización",
                category="Blockchain",
                summary="Tokenización de activos reales y CBDCs en Latinoamérica.",
                keywords=["tokenización", "CBDC", "DeFi", "stablecoin"], item_count=15,
                impact_score=0.6, horizon_score=0.8, avg_score=0.55,
                x_embed=0.6, y_embed=-0.1, relevance="media",
            ),
            Cluster(
                cluster_id="c4", label="Open Banking APIs",
                category="Banca Digital",
                summary="Evolución de APIs abiertas y estándares de interoperabilidad bancaria.",
                keywords=["open banking", "API", "PSD2", "interoperabilidad"], item_count=20,
                impact_score=0.75, horizon_score=0.6, avg_score=0.7,
                x_embed=-0.5, y_embed=-0.3, relevance="alta",
            ),
            Cluster(
                cluster_id="c5", label="RegTech y Compliance Automatizado",
                category="Regulación",
                summary="Automatización de procesos de cumplimiento regulatorio con IA.",
                keywords=["regtech", "compliance", "KYC", "AML"], item_count=18,
                impact_score=0.7, horizon_score=0.4, avg_score=0.65,
                x_embed=0.1, y_embed=0.2, relevance="media",
            ),
        ]
        session.add_all(clusters)

        # Trends
        trends = [
            Trend(
                trend="LLMs en atención al cliente", category="Inteligencia Artificial",
                direction="creciente", momentum=0.88,
                maturity_stage="peak_of_inflated_expectations",
                description="Adopción masiva de chatbots basados en LLM en banca retail.",
                impact_on_finance="Alto impacto en reducción de costos operativos de contact center.",
            ),
            Trend(
                trend="Zero Trust Architecture", category="Ciberseguridad",
                direction="creciente", momentum=0.75,
                maturity_stage="slope_of_enlightenment",
                description="Migración de perímetro tradicional a microsegmentación.",
                impact_on_finance="Reducción de superficie de ataque y costos de incidentes.",
            ),
            Trend(
                trend="CBDCs en Latinoamérica", category="Blockchain",
                direction="estable", momentum=0.45,
                maturity_stage="trough_of_disillusionment",
                description="Pilotos de monedas digitales de bancos centrales en la región.",
                impact_on_finance="Potencial disrupción en pagos transfronterizos.",
            ),
            Trend(
                trend="Quantum-safe Cryptography", category="Ciberseguridad",
                direction="creciente", momentum=0.35,
                maturity_stage="trigger",
                description="Preparación para amenazas de computación cuántica.",
                impact_on_finance="Inversión preventiva en migración criptográfica.",
            ),
            Trend(
                trend="Embedded Finance", category="Banca Digital",
                direction="creciente", momentum=0.82,
                maturity_stage="peak_of_inflated_expectations",
                description="Integración de servicios financieros en plataformas no financieras.",
                impact_on_finance="Nuevos canales de distribución y competencia de neobancos.",
            ),
            Trend(
                trend="ESG Scoring Automatizado", category="Regulación",
                direction="creciente", momentum=0.6,
                maturity_stage="slope_of_enlightenment",
                description="Uso de IA para scoring ESG automatizado en portafolios.",
                impact_on_finance="Cumplimiento regulatorio y atracción de inversión sostenible.",
            ),
            Trend(
                trend="Metaverso Bancario", category="Banca Digital",
                direction="decreciente", momentum=0.15,
                maturity_stage="trough_of_disillusionment",
                description="Sucursales virtuales en metaverso pierden tracción.",
                impact_on_finance="Inversiones en metaverso bancario se redirigen a IA.",
            ),
        ]
        session.add_all(trends)

        await session.commit()
        print("Seed completed: 6 topics, 30 ARAS docs, 25 riesgos docs, 5 clusters, 7 trends")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
