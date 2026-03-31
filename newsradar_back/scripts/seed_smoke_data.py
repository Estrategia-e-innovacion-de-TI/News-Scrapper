"""Seed canonical data for local smoke testing."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import os
import sys
import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from newsradar_api.infrastructure.driven_adapters.db_models import Document, Execution

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://newsradar:newsradar@localhost:5432/newsradar",
)


def _doc(
    run_id: str,
    execution_id,
    business_flow: str,
    source_id: str,
    source_type: str,
    title: str,
    *,
    category: str | None = None,
    risk_type: str | None = None,
    score: int = 75,
    days_ago: int = 0,
    index: int = 0,
) -> Document:
    published_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    text = f"{title}. Categoria {category or risk_type or 'general'}. Documento semilla para smoke local."
    return Document(
        execution_id=execution_id,
        run_id=run_id,
        business_flow=business_flow,
        source_id=source_id,
        source_type=source_type,
        pipeline_class="news",
        focus=[business_flow],
        title=title,
        url=f"https://smoke.local/{business_flow}/{index}",
        canonical_url=f"https://smoke.local/{business_flow}/{index}",
        source_url=f"https://smoke.local/{source_id}",
        published_at=published_at,
        fetched_at=published_at,
        language="es",
        text=text,
        excerpt=text[:240],
        raw_len=len(text),
        text_len=len(text),
        text_capped=False,
        hash=f"smoke-{business_flow}-{index:03d}",
        fetch_method="seed",
        status="ok",
        origin="smoke_seed",
        category=category,
        risk_type=risk_type,
        classifier_mode="seed",
        confidence=0.95,
        matched_keywords=[item for item in [category, risk_type] if item],
        materialized_events=[],
        relevance_score=score,
    )


async def seed() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(Document).where(Document.origin == "smoke_seed"))
        await session.execute(delete(Execution).where(Execution.run_key.in_(["smoke-tech", "smoke-risk"])))
        await session.commit()

        tech_execution_id = uuid.uuid4()
        risk_execution_id = uuid.uuid4()
        started_at = datetime.now(timezone.utc)

        session.add_all(
            [
                Execution(
                    id=tech_execution_id,
                    run_key="smoke-tech",
                    business_flow="tech_watch",
                    trigger_type="seed",
                    source_scope="vigilancia_news",
                    status="completed",
                    config_json={"seed": True},
                    metrics_json={"documents": 6},
                    started_at=started_at,
                    finished_at=started_at,
                ),
                Execution(
                    id=risk_execution_id,
                    run_key="smoke-risk",
                    business_flow="risk_mapping",
                    trigger_type="seed",
                    source_scope="riesgos_news",
                    status="completed",
                    config_json={"seed": True},
                    metrics_json={"documents": 6},
                    started_at=started_at,
                    finished_at=started_at,
                ),
            ]
        )

        tech_docs = [
            _doc("smoke-tech", tech_execution_id, "tech_watch", "smoke-news", "rss", "IA generativa para banca minorista", category="IA", score=91, days_ago=7, index=1),
            _doc("smoke-tech", tech_execution_id, "tech_watch", "smoke-news", "rss", "Copilotos de cumplimiento regulatorio", category="IA", score=84, days_ago=18, index=2),
            _doc("smoke-tech", tech_execution_id, "tech_watch", "smoke-paper", "paper", "Tokenizacion de activos bancarios", category="Blockchain", score=79, days_ago=27, index=3),
            _doc("smoke-tech", tech_execution_id, "tech_watch", "smoke-paper", "paper", "Agentes autonomos para onboarding digital", category="IA", score=88, days_ago=33, index=4),
            _doc("smoke-tech", tech_execution_id, "tech_watch", "smoke-patent", "patent", "Patentes de vision por computador para fraude", category="Vision", score=72, days_ago=44, index=5),
            _doc("smoke-tech", tech_execution_id, "tech_watch", "smoke-news", "rss", "Arquitecturas de datos para open finance", category="Cloud/Datos", score=70, days_ago=55, index=6),
        ]
        risk_docs = [
            _doc("smoke-risk", risk_execution_id, "risk_mapping", "smoke-wef", "institutional_report", "Ciberseguridad y ransomware en servicios financieros", risk_type="ciberseguridad", score=94, days_ago=5, index=101),
            _doc("smoke-risk", risk_execution_id, "risk_mapping", "smoke-allianz", "pdf", "Fraude digital y desinformacion", risk_type="desinformacion y malinformacion", score=86, days_ago=17, index=102),
            _doc("smoke-risk", risk_execution_id, "risk_mapping", "smoke-world-bank", "institutional_report", "Riesgo climatico y resiliencia operacional", risk_type="clima y naturaleza", score=82, days_ago=25, index=103),
            _doc("smoke-risk", risk_execution_id, "risk_mapping", "smoke-aon", "institutional_report", "Geopolitica y cadenas de suministro", risk_type="geopolitica", score=80, days_ago=39, index=104),
            _doc("smoke-risk", risk_execution_id, "risk_mapping", "smoke-marsh", "pdf", "Riesgo de IA y gobierno corporativo", risk_type="riesgo de ia", score=78, days_ago=48, index=105),
            _doc("smoke-risk", risk_execution_id, "risk_mapping", "smoke-news", "rss", "Contaminacion y conflictividad comunitaria", risk_type="clima y naturaleza", score=74, days_ago=61, index=106),
        ]
        session.add_all(tech_docs + risk_docs)
        await session.commit()

    await engine.dispose()
    print("Smoke seed completed: 2 executions, 12 documents")


if __name__ == "__main__":
    asyncio.run(seed())
