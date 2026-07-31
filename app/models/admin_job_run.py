"""
Modèle AdminJobRun — trace toute exécution de job déclenchée depuis
l'admin (POST /admin/jobs/{name}/run, /admin/email-digest/send-now), pour
tous les types de jobs (collecteurs, corrélation, clustering, recalcul des
scores, séquence "Lancer tout", envoi du digest email).

Ne remplace PAS collection_runs : reste la source de vérité pour les
statistiques de collecte utilisées ailleurs dans l'app. AdminJobRun couvre
spécifiquement ce qui a été déclenché depuis cette interface (voir
app/admin_job_runner.py), y compris les jobs (corrélation, clustering,
recalcul des scores) qui n'ont jamais eu de suivi jusqu'ici.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AdminJobRun(Base):
    __tablename__ = "admin_job_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    job_name: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    exit_code: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(Text)
