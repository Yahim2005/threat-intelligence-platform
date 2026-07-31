"""
Digest email périodique des IOCs pertinents pour le Cameroun.

Filtre : IOCs actifs, cameroon_relevance >= seuil configurable, et dont le
first_seen est postérieur au dernier envoi RÉUSSI (email_digest_log.sent_at)
-- un IOC n'est donc jamais renvoyé deux fois. S'il n'y a jamais eu d'envoi
réussi, tous les IOCs actuellement pertinents sont inclus (premier envoi).

email_digest_log n'est alimenté que lors d'un envoi réel (voir
scripts/send_email_digest.py) -- jamais en --dry-run, pour ne pas faire
avancer le filigrane sur un simple aperçu.
"""
from __future__ import annotations

import html
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.models.email_digest_log import EmailDigestLog
from app.models.email_recipient import EmailRecipient
from app.models.enums import IndicatorStatus
from app.models.indicator import Indicator

DEFAULT_MIN_RELEVANCE = int(os.getenv("EMAIL_DIGEST_MIN_RELEVANCE", "3"))
DEFAULT_MAX_IOCS = int(os.getenv("EMAIL_DIGEST_MAX_IOCS", "30"))
MIN_DAYS_BETWEEN_SENDS = 3


# ---------------------------------------------------------------------------
# Filigrane / cadence
# ---------------------------------------------------------------------------

def get_last_successful_sent_at(session: Session) -> datetime | None:
    last = (
        session.query(EmailDigestLog)
        .order_by(EmailDigestLog.sent_at.desc())
        .first()
    )
    return last.sent_at if last else None


def should_send_now(session: Session) -> bool:
    """
    Vrai s'il n'y a jamais eu d'envoi, ou si >= MIN_DAYS_BETWEEN_SENDS jours
    se sont écoulés depuis le dernier envoi réussi. Le workflow GitHub tourne
    tous les jours ; c'est cette fonction qui garantit un espacement réel de
    3 jours (un cron */3 sur le jour du mois ne le garantirait pas).
    """
    last_sent = get_last_successful_sent_at(session)
    if last_sent is None:
        return True
    if last_sent.tzinfo is None:
        last_sent = last_sent.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_sent >= timedelta(days=MIN_DAYS_BETWEEN_SENDS)


# ---------------------------------------------------------------------------
# Contenu du digest
# ---------------------------------------------------------------------------

def get_digest_indicators(
    session: Session,
    min_relevance: int = DEFAULT_MIN_RELEVANCE,
    max_iocs: int = DEFAULT_MAX_IOCS,
) -> list[Indicator]:
    """
    Plafonné à max_iocs pour rester lisible dans un email : quand plus de
    candidats existent que la limite, on garde les plus récents (tri par
    first_seen DESC avant le LIMIT) -- jamais un échantillon arbitraire.
    """
    last_sent = get_last_successful_sent_at(session)

    query = session.query(Indicator).filter(
        Indicator.status == IndicatorStatus.active,
        Indicator.cameroon_relevance >= min_relevance,
    )
    if last_sent is not None:
        query = query.filter(Indicator.first_seen > last_sent)
    else:
        query = query.filter(Indicator.first_seen.isnot(None))

    return query.order_by(Indicator.first_seen.desc()).limit(max_iocs).all()


def get_active_recipients(session: Session) -> list[EmailRecipient]:
    return (
        session.query(EmailRecipient)
        .filter(EmailRecipient.is_active.is_(True))
        .order_by(EmailRecipient.email)
        .all()
    )


def _threat_name_for(indicator: Indicator) -> str:
    threats = indicator.threats
    if not threats:
        return "Non classifié"
    return threats[0].name


def build_digest_html(indicators: list[Indicator]) -> str:
    """
    Tableau HTML lisible : Valeur, 1ère observation, Menace associée, Tags,
    Source. Génère un email court "aucun nouvel IOC" si la liste est vide,
    plutôt que de ne rien envoyer silencieusement.
    """
    rows_html: list[str] = []
    for ind in indicators:
        value = html.escape(ind.value)
        tag_names = {t.name for t in ind.tags}
        # Signal court (sigle <=4 caracteres) : le typosquat monitor le
        # marque lui-meme comme "potential" plutot que "confirmed", trop de
        # collisions statistiques possibles pour etre fiable sans verification
        # manuelle. On le garde visible (le signal peut etre reel) mais on le
        # signale clairement au lecteur plutot que de le faire disparaitre.
        needs_review = "typosquat:potential" in tag_names
        if needs_review:
            value = (
                f'{value} <span style="display:inline-block;margin-left:6px;'
                f'padding:1px 6px;border-radius:8px;background:#fef3c7;'
                f'color:#92400e;font-size:10px;font-weight:bold;">A VERIFIER</span>'
            )
        first_seen = ind.first_seen.strftime("%Y-%m-%d %H:%M") if ind.first_seen else "—"
        threat_name = html.escape(_threat_name_for(ind))
        tags = html.escape(", ".join(sorted(tag_names)) or "—")
        source = html.escape(ind.source.name if ind.source else "—")
        rows_html.append(f"""
          <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #ede8e3;font-family:monospace;font-size:13px;">{value}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #ede8e3;font-size:13px;white-space:nowrap;">{first_seen}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #ede8e3;font-size:13px;">{threat_name}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #ede8e3;font-size:12px;color:#8b7355;">{tags}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #ede8e3;font-size:13px;">{source}</td>
          </tr>""")

    if not rows_html:
        body = """
          <p style="font-size:14px;color:#555;">
            Aucun nouvel IOC pertinent pour le Cameroun depuis le dernier envoi.
            Ce message confirme que le système de veille est toujours actif.
          </p>"""
    else:
        body = f"""
          <p style="font-size:14px;color:#555;">{len(indicators)} nouvel(aux) IOC(s) pertinent(s) pour le Cameroun.</p>
          <table style="border-collapse:collapse;width:100%;font-family:Arial,sans-serif;">
            <thead>
              <tr style="background:#faf8f5;">
                <th style="text-align:left;padding:8px 12px;font-size:12px;color:#8b7355;text-transform:uppercase;">Valeur de l'IOC</th>
                <th style="text-align:left;padding:8px 12px;font-size:12px;color:#8b7355;text-transform:uppercase;">1ère observation</th>
                <th style="text-align:left;padding:8px 12px;font-size:12px;color:#8b7355;text-transform:uppercase;">Menace associée</th>
                <th style="text-align:left;padding:8px 12px;font-size:12px;color:#8b7355;text-transform:uppercase;">Tags</th>
                <th style="text-align:left;padding:8px 12px;font-size:12px;color:#8b7355;text-transform:uppercase;">Source</th>
              </tr>
            </thead>
            <tbody>{''.join(rows_html)}</tbody>
          </table>"""

    return f"""<!doctype html>
<html>
<body style="margin:0;padding:24px;background:#faf8f5;font-family:Arial,sans-serif;">
  <div style="max-width:800px;margin:0 auto;background:#ffffff;border:1px solid #ede8e3;border-radius:12px;padding:24px;">
    <h1 style="font-size:18px;color:#2c1810;margin:0 0 4px 0;">Digest IOC Cameroun — ANTIC/CIRT</h1>
    <p style="font-size:12px;color:#999;margin:0 0 20px 0;">Généré le {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</p>
    {body}
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Envoi SMTP
# ---------------------------------------------------------------------------

def send_digest_email(
    recipient_emails: list[str],
    html_body: str,
    subject: str = "Digest IOC Cameroun — ANTIC/CIRT",
) -> None:
    """
    Envoi SMTP standard (smtplib + email.mime, aucune dépendance tierce).
    Configuré via SMTP_HOST/SMTP_PORT/SMTP_USERNAME/SMTP_PASSWORD/SMTP_FROM_EMAIL.
    """
    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL", username or "noreply@example.com")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(recipient_emails)
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(host, port, timeout=30) as server:
        if os.getenv("SMTP_USE_TLS", "true").lower() != "false":
            server.starttls()
        if username and password:
            server.login(username, password)
        server.sendmail(from_email, recipient_emails, msg.as_string())


def log_successful_send(session: Session, recipient_count: int, ioc_count: int) -> EmailDigestLog:
    log = EmailDigestLog(recipient_count=recipient_count, ioc_count=ioc_count)
    session.add(log)
    session.commit()
    session.refresh(log)
    return log
