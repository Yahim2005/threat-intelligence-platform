"""Registre des collecteurs : charge et instancie les collecteurs déclarés dans sources.yaml.

Usage :
    from collectors.registry import get_enabled_collectors, get_collector

    # Lancer tous les collecteurs activés
    for collector in get_enabled_collectors():
        collector.run()

    # Lancer un collecteur précis par nom
    collector = get_collector("abuse.ch - URLhaus")
    if collector:
        collector.run()
"""
import importlib
import logging
from pathlib import Path

import yaml

from collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# Chemin absolu vers sources.yaml, calculé relativement à ce fichier.
# Path(__file__) = .../collectors/registry.py
# .parent        = .../collectors/
# .parent.parent = .../ (racine du projet)
CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"


def _load_config() -> list[dict]:
    """Lit sources.yaml et retourne la liste brute des entrées."""
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("sources", [])


def _import_class(class_path: str) -> type:
    """Importe dynamiquement une classe depuis son chemin pointé.

    Exemple : 'collectors.urlhaus.URLhausCollector'
              → importe le module collectors.urlhaus
              → retourne la classe URLhausCollector
    """
    module_path, class_name = class_path.rsplit(".", 1)  # coupe au dernier point
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def get_enabled_collectors() -> list[BaseCollector]:
    """Retourne une liste d'instances de tous les collecteurs dont enabled=true."""
    collectors = []
    for entry in _load_config():
        if not entry.get("enabled", False):
            continue
        try:
            cls = _import_class(entry["class"])
            collectors.append(cls())
            logger.debug(f"Collecteur chargé : {entry['name']}")
        except Exception as e:
            logger.error(f"Impossible de charger '{entry.get('name')}' : {e}")
    return collectors


def get_collector(name: str) -> BaseCollector | None:
    """Retourne une instance du collecteur par nom, ou None s'il est introuvable."""
    for entry in _load_config():
        if entry.get("name") == name:
            try:
                return _import_class(entry["class"])()
            except Exception as e:
                logger.error(f"Impossible de charger '{name}' : {e}")
                return None
    logger.warning(f"Collecteur '{name}' non trouvé dans sources.yaml")
    return None