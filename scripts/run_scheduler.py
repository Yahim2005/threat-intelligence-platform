"""Lance tous les collecteurs activés selon leur fréquence définie dans sources.yaml.

Usage :
    python -m scripts.run_scheduler

Le script tourne en continu (Ctrl+C pour arrêter). Chaque collecteur est exécuté
une première fois immédiatement au démarrage, puis répété à son intervalle propre.
"""
import logging
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler

from collectors.registry import get_enabled_collectors, _load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def run_collector_safely(collector) -> None:
    """Exécute un collecteur en isolant toute exception.
    BaseCollector.run() gère déjà l'isolation interne (try/except sur chaque
    étape), mais cette fonction est une deuxième barrière de sécurité : même
    si run() laissait fuiter une exception inattendue, le scheduler ne doit
    jamais s'arrêter à cause d'un seul job en échec.
    """
    try:
        collector.run()
    except Exception as e:
        logger.error(f"[{collector.name}] Exception non interceptée par run() : {e}")


def main():
    scheduler = BackgroundScheduler(timezone="UTC")
    config_entries = {entry["name"]: entry for entry in _load_config()}
    collectors = get_enabled_collectors()

    if not collectors:
        logger.warning("Aucun collecteur activé trouvé dans sources.yaml.")
        sys.exit(1)

    for collector in collectors:
        entry = config_entries.get(collector.name, {})
        interval_minutes = entry.get("interval_minutes", 60)

        scheduler.add_job(
            run_collector_safely,
            "interval",
            minutes=interval_minutes,
            args=[collector],
            id=collector.name,
            next_run_time=None,  # déclenché manuellement juste après (run immédiat)
        )
        logger.info(
            f"Job planifié : [{collector.name}] toutes les {interval_minutes} min"
        )

    scheduler.start()
    logger.info(f"Scheduler démarré avec {len(collectors)} job(s).")

    # Premier run immédiat pour chaque collecteur, sans attendre le premier intervalle.
    for collector in collectors:
        scheduler.add_job(run_collector_safely, args=[collector])

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Arrêt du scheduler demandé...")
        scheduler.shutdown(wait=True)
        logger.info("Scheduler arrêté proprement.")


if __name__ == "__main__":
    main()