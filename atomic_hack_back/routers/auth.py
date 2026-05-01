from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas import UserCreate, UserLogin, UserRead

MAX_BCRYPT_BYTES = 72

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _prepare_secret(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_BCRYPT_BYTES:
        encoded = encoded[:MAX_BCRYPT_BYTES]
    return encoded


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_prepare_secret(plain_password), hashed_password)


def _hash_password(password: str) -> str:
    return pwd_context.hash(_prepare_secret(password))


@router.post("/registration", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def registration(payload: UserCreate, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=email, hashed_password=_hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=UserRead)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    user = db.query(User).filter(User.email == email).first()
    if not user or not _verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return user
