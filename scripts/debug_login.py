"""
Diagnostic du login admin — simule exactement ce que fait l'API.
Usage : python scripts/debug_login.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EMAIL = os.getenv("ADMIN_EMAIL")
PASSWORD = os.getenv("ADMIN_PASSWORD")

if not EMAIL or not PASSWORD:
    sys.exit(
        "Erreur : définis ADMIN_EMAIL et ADMIN_PASSWORD en variables "
        "d'environnement avant de lancer ce script.\n"
        "Exemple : ADMIN_EMAIL=toi@antic.cm ADMIN_PASSWORD=xxx python scripts/debug_login.py"
    )

print("1. Chargement de la config...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "NON DÉFINIE")
    jwt_key = os.getenv("JWT_SECRET_KEY", "NON DÉFINIE")
    print(f"   DATABASE_URL : {db_url[:40]}...")
    print(f"   JWT_SECRET_KEY : {'OK (' + str(len(jwt_key)) + ' chars)' if jwt_key != 'NON DÉFINIE' else 'MANQUANTE ❌'}")
except Exception as e:
    print(f"   ❌ {e}")
    sys.exit(1)

print("\n2. Connexion à la DB...")
try:
    from app.database import SessionLocal
    db = SessionLocal()
    from sqlalchemy import text
    db.execute(text("SELECT 1"))
    print("   Connexion OK ✅")
except Exception as e:
    print(f"   ❌ {e}")
    sys.exit(1)

print("\n3. Requête User ORM...")
try:
    from app.models.user import User
    user = db.query(User).filter(
        (User.email == EMAIL) | (User.phone == EMAIL)
    ).first()
    if user:
        print(f"   Utilisateur trouvé : {user.email}, rôle={user.role} ✅")
    else:
        print(f"   ❌ Aucun utilisateur avec email={EMAIL}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ {e}")
    sys.exit(1)

print("\n4. Vérification du mot de passe...")
try:
    from app.security import verify_password
    ok = verify_password(PASSWORD, user.hashed_password)
    print(f"   {'✅ Mot de passe correct' if ok else '❌ Mot de passe incorrect'}")
    if not ok:
        sys.exit(1)
except Exception as e:
    print(f"   ❌ {e}")
    sys.exit(1)

print("\n5. Génération du JWT...")
try:
    from app.security import create_access_token
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    print(f"   Token généré ✅ : {token[:50]}...")
except Exception as e:
    print(f"   ❌ {e}")
    sys.exit(1)

print("\n✅ Tout fonctionne — le login devrait marcher en prod.")
db.close()
