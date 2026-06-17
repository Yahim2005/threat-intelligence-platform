"""Rate limiter simple, basé sur une fenêtre glissante en mémoire.
Usage :
    limiter = RateLimiter(max_calls=5, period_seconds=30)
    limiter.wait_if_needed()  # bloque si la limite serait dépassée
"""
import time
from collections import deque


class RateLimiter:
    """Limite le nombre d'appels à max_calls par fenêtre de period_seconds.
    Implémentation "fenêtre glissante" : on garde l'horodatage des derniers
    appels, et on calcule combien de temps attendre avant le prochain.
    """

    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self._call_times: deque[float] = deque()

    def wait_if_needed(self) -> None:
        """Bloque (time.sleep) si nécessaire pour respecter la limite, puis
        enregistre cet appel."""
        now = time.monotonic()

        # Retire les appels devenus trop vieux pour compter dans la fenêtre actuelle.
        while self._call_times and now - self._call_times[0] >= self.period_seconds:
            self._call_times.popleft()

        if len(self._call_times) >= self.max_calls:
            # La fenêtre est pleine : on attend que le plus vieil appel sorte de la fenêtre.
            oldest = self._call_times[0]
            sleep_time = self.period_seconds - (now - oldest)
            if sleep_time > 0:
                time.sleep(sleep_time)
            now = time.monotonic()
            # Nettoyage après l'attente.
            while self._call_times and now - self._call_times[0] >= self.period_seconds:
                self._call_times.popleft()

        self._call_times.append(now)