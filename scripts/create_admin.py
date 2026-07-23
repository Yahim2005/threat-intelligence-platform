"""
Script de création d'un compte admin en base de production (Neon).
Usage : python scripts/create_admin.py
"""
import sys
import os
from pathlib import Path

# Ajoute la racine du projet au path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

from app.security import hash_password

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("❌  DATABASE_URL introuvable dans .env")

EMAIL = os.getenv("cirt@antic.cm")
PASSWORD = os.getenv("jesuisducirt")
FULL_NAME = os.getenv("Admin Antic", "ANTIC CIRT Admin")

if not EMAIL or not PASSWORD:
    sys.exit(
        "Erreur : définis ADMIN_EMAIL et ADMIN_PASSWORD en variables "
        "d'environnement avant de lancer ce script (jamais en dur dans le code).\n"
        "Exemple : ADMIN_EMAIL=toi@antic.cm ADMIN_PASSWORD=xxx python scripts/create_admin.py"
    )

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

with Session() as db:
    # Vérifie si l'utilisateur existe déjà
    existing = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": EMAIL},
    ).fetchone()

    if existing:
        print(f"⚠️  Un compte existe déjà pour {EMAIL} (id={existing[0]})")
        print("   Mise à jour du rôle → admin et du mot de passe...")
        db.execute(
            text("""
                UPDATE users
                SET role = 'admin',
                    hashed_password = :pwd,
                    is_active = true
                WHERE email = :email
            """),
            {"pwd": hash_password(PASSWORD), "email": EMAIL},
        )
        db.commit()
        print("✅  Compte mis à jour avec le rôle admin.")
    else:
        user_id = str(uuid4())
        db.execute(
            text("""
                INSERT INTO users (id, email, full_name, hashed_password, role, is_active)
                VALUES (:id, :email, :full_name, :pwd, 'admin', true)
            """),
            {
                "id": user_id,
                "email": EMAIL,
                "full_name": FULL_NAME,
                "pwd": hash_password(PASSWORD),
            },
        )
        db.commit()
        print(f"✅  Compte admin créé : {EMAIL}  (id={user_id})")

print("\nConnexion de test :")
print(f"  POST /auth/login  ->  identifier={EMAIL}  (mot de passe non affiché)")
