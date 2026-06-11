from pathlib import Path
from collectors.urlhaus import parse_csv

FIXTURE = (Path(__file__).parent / "fixtures" / "urlhaus_sample.csv").read_text()


def test_parse_ignore_comments():
    """Les lignes # doivent être ignorées."""
    rows = parse_csv(FIXTURE)
    assert len(rows) == 3


def test_parse_colonnes_presentes():
    """Les colonnes essentielles doivent exister."""
    rows = parse_csv(FIXTURE)
    assert "url" in rows[0]
    assert "dateadded" in rows[0]
    assert "threat" in rows[0]


def test_parse_urls_non_vides():
    """Aucune URL vide ne doit passer."""
    rows = parse_csv(FIXTURE)
    for row in rows:
        assert row["url"].strip() != ""


def test_parse_format_date():
    """La date doit être parseable."""
    from datetime import datetime
    rows = parse_csv(FIXTURE)
    date_str = rows[0]["dateadded"].strip()
    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    assert dt.year == 2024