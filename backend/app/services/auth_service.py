from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.company import Company
from app.models.user import User, UserRole


@dataclass(slots=True)
class AuthResult:
    user: User
    access_token: str
    token_type: str = "bearer"


def _normalize_domain(domain: str) -> str:
    domain = domain.strip().lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def extract_domain_from_email(email: str) -> str:
    try:
        domain = email.split("@", maxsplit=1)[1]
    except IndexError as exc:
        raise APIError(status_code=400, code="invalid_email", detail="Email is invalid") from exc
    return _normalize_domain(domain)


def extract_domain_from_website(website: str) -> str:
    website = website.strip()
    if not website.startswith(("http://", "https://")):
        website = f"https://{website}"
    parsed = urlparse(website)
    netloc = parsed.netloc.split(":", maxsplit=1)[0]
    if not netloc:
        raise APIError(status_code=400, code="invalid_website", detail="Company website is invalid")
    return _normalize_domain(netloc)


def get_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email.lower())
    return db.scalar(stmt)


def register_candidate(db: Session, *, email: str, password: str, full_name: str) -> User:
    existing = get_user_by_email(db, email)
    if existing:
        raise APIError(status_code=400, code="email_in_use", detail="Email is already registered")

    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        role=UserRole.candidate,
        full_name=full_name.strip(),
        verified=True,
    )
    db.add(user)
    db.flush()
    return user


def register_hr(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    company_name: str,
    company_website: str,
) -> User:
    existing = get_user_by_email(db, email)
    if existing:
        raise APIError(status_code=400, code="email_in_use", detail="Email is already registered")

    email_domain = extract_domain_from_email(email)
    website_domain = extract_domain_from_website(company_website)

    if email_domain != website_domain:
        raise APIError(
            status_code=400,
            code="domain_mismatch",
            detail="HR email domain must match company website domain",
            data={"email_domain": email_domain, "website_domain": website_domain},
        )

    company_stmt = select(Company).where(Company.domain == website_domain)
    company = db.scalar(company_stmt)
    if company is None:
        company = Company(name=company_name.strip(), website=company_website.strip(), domain=website_domain)
        db.add(company)
        db.flush()
    else:
        company.name = company_name.strip() or company.name
        company.website = company_website.strip() or company.website

    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        role=UserRole.hr,
        full_name=full_name.strip(),
        verified=True,
        company_id=company.id,
    )
    db.add(user)
    db.flush()
    return user


def login(db: Session, *, email: str, password: str) -> AuthResult:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise APIError(status_code=401, code="invalid_credentials", detail="Invalid email or password")

    token = create_access_token(subject=str(user.id), role=user.role.value)
    return AuthResult(user=user, access_token=token)