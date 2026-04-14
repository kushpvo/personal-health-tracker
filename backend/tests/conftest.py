import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import create_access_token, hash_password
from app.db.database import Base, get_db
from app.db.models import User
from app.main import app


@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestingSession()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def create_user(test_db):
    def _create_user(username="user", password="password123", role="user", is_active=True):
        user = User(
            username=username,
            hashed_password=hash_password(password),
            role=role,
            is_active=is_active,
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        return user

    return _create_user


@pytest.fixture(scope="function")
def auth_headers():
    def _auth_headers(user, acting_as=None):
        token = create_access_token(user.id, user.role, acting_as=acting_as)
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers
