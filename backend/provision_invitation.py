"""Issue a one-use reviewer invitation from an authorized backend shell."""
import argparse,hashlib,secrets
from datetime import datetime,timedelta,timezone
from main import Base,engine,SessionLocal,ReviewerInvite

def issue(days=7):
    code=secrets.token_urlsafe(32)
    expires=(datetime.now(timezone.utc)+timedelta(days=days)).isoformat()
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        s.add(ReviewerInvite(digest=hashlib.sha256(code.encode()).hexdigest(),expires=expires));s.commit()
    return code,expires

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--days',type=int,default=7)
    args=parser.parse_args()
    if not 1<=args.days<=30:parser.error('Expiry must be between 1 and 30 days.')
    code,expires=issue(args.days)
    print('Invitation code (share privately): '+code);print('Expires UTC: '+expires)
