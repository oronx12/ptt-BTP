# create_admin.py
# Usage : python create_admin.py
# Lance UNE SEULE FOIS pour créer ton compte administrateur.
import getpass
from app import create_app, db
from app.models import User

app = create_app(env="development")

with app.app_context():
    email = input("Email admin : ").strip().lower()
    nom   = input("Nom        : ").strip()
    pwd   = getpass.getpass("Mot de passe : ")
    pwd2  = getpass.getpass("Confirmer   : ")

    if pwd != pwd2:
        print("Les mots de passe ne correspondent pas.")
        exit(1)

    if User.query.filter_by(email=email).first():
        print(f"Un utilisateur avec l'email {email} existe déjà.")
        exit(1)

    admin = User(email=email, nom=nom, role="admin")
    admin.set_password(pwd)
    db.session.add(admin)
    db.session.commit()
    print(f"\nCompte admin cree : {email} (ID {admin.id})")
    print("Lancez l'app avec setup.bat puis connectez-vous sur /login")
