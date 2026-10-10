"""Run in a secure Railway shell with DATABASE_URL set. Password is never echoed."""
import getpass
from sqlalchemy import select
from main import Base,engine,SessionLocal,Account,hash_password
Base.metadata.create_all(engine)
email=input('Reviewer email: ').strip().lower()
name=input('Reviewer name: ').strip()
college=input('Review organization: ').strip()
password=getpass.getpass('Password (at least 12 characters): ')
if len(password)<12 or not email or not name or not college:raise SystemExit('Valid reviewer details and a long password are required.')
with SessionLocal() as s:
    if s.scalar(select(Account).where(Account.email==email)):raise SystemExit('Account exists. No role was modified.')
    s.add(Account(email=email,name=name,college=college,role='reviewer',password=hash_password(password)))
    s.commit()
print('Reviewer created.')
