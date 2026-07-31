"""
Déclenchement + suivi des jobs lancés depuis l'admin (collecteurs,
post-traitement, séquence "Lancer tout", envoi immédiat du digest email).

Factorisé ici (plutôt que dupliqué dans api/main.py et
api/email_recipients_routes.py) : un sous-processus est lancé en
arrière-plan, une ligne admin_job_runs est créée immédiatement
(status="running"), et un thread de fond attend sa fin pour mettre à jour
finished_at/status/exit_code -- le tout sans bloquer la réponse HTTP.
"""
from __future__ import annotations

import logging
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.database import SessionLocal
from app.models.admin_job_run import AdminJobRun

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _update_run(run_id: UUID, *, status: str, exit_code: int | None = None, detail: str | None = None) -> None:
    session = SessionLocal()
    try:
        run = session.query(AdminJobRun).filter_by(id=run_id).first()
        if not run:
            return
        run.status = status
        if exit_code is not None:
            run.exit_code = exit_code
        if detail is not None:
            run.detail = detail
        if status in ("success", "failed"):
            run.finished_at = datetime.utcnow()
        session.commit()
    finally:
        session.close()


def launch_tracked_job(job_name: str, args: list[str]) -> UUID:
    """
    Crée la ligne admin_job_runs (running), lance `args` en sous-processus,
    et démarre un thread qui attend sa fin pour finaliser le statut.
    Retourne l'id de la ligne créée.
    """
    session = SessionLocal()
    try:
        run = AdminJobRun(job_name=job_name, status="running")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    finally:
        session.close()

    proc = subprocess.Popen(
        args,
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    def _watch() -> None:
        exit_code = proc.wait()
        _update_run(run_id, status="success" if exit_code == 0 else "failed", exit_code=exit_code)

    threading.Thread(target=_watch, daemon=True).start()
    return run_id


def launch_run_all_sequence(job_name: str, steps: list[tuple[str, str]]) -> UUID:
    """
    Lance une séquence de modules Python les uns après les autres (chacun
    attendu avant de démarrer le suivant), en arrière-plan. `steps` est une
    liste de (label, module_path). Une seule ligne admin_job_runs suit
    l'ensemble ; sa colonne `detail` est mise à jour après chaque étape pour
    donner une visibilité de progression simple (texte, pas de structure JSON).
    """
    session = SessionLocal()
    try:
        run = AdminJobRun(job_name=job_name, status="running", detail=f"0/{len(steps)}")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    finally:
        session.close()

    def _run_sequence() -> None:
        for i, (label, module_path) in enumerate(steps, start=1):
            _update_run(run_id, status="running", detail=f"{i}/{len(steps)} : {label} (en cours)")
            try:
                result = subprocess.run(
                    ["python", "-m", module_path],
                    cwd=str(REPO_ROOT),
                    env=os.environ.copy(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if result.returncode != 0:
                    logger.warning("run_all : étape %s (%s) a échoué (code %s)", label, module_path, result.returncode)
                    _update_run(run_id, status="failed", exit_code=result.returncode, detail=f"{i}/{len(steps)} : {label} (échec)")
                    return
            except Exception as exc:
                logger.error("run_all : erreur sur l'étape %s (%s) : %s", label, module_path, exc)
                _update_run(run_id, status="failed", detail=f"{i}/{len(steps)} : {label} (erreur : {exc})")
                return

        _update_run(run_id, status="success", exit_code=0, detail=f"{len(steps)}/{len(steps)} : terminé")

    threading.Thread(target=_run_sequence, daemon=True).start()
    return run_id
