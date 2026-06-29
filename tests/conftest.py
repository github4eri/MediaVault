import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

TEST_DB_URL = "sqlite:///./test_mediavault.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def reset_db():
    import models
    from database import Base
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db(reset_db):
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    import main
    import database

    def override_get_db():
        yield db

    main.app.dependency_overrides[main.get_db] = override_get_db
    main.app.dependency_overrides[database.get_db] = override_get_db

    # Patch SessionLocal so the startup event also writes to the test DB
    with patch.object(main, "SessionLocal", TestSessionLocal):
        with patch("vision.analyze_media", return_value="tag1, tag2"):
            with patch("media_service.vision.analyze_media", return_value="tag1, tag2"):
                with TestClient(main.app, raise_server_exceptions=True) as c:
                    yield c

    main.app.dependency_overrides.clear()


@pytest.fixture
def admin_client(client, db):
    client.post("/login", data={"username": "admin", "password": "admin123"})
    return client


@pytest.fixture
def guest_client(client, db):
    from security import get_password_hash
    import models
    if not db.query(models.User).filter_by(username="guest").first():
        db.add(models.User(username="guest", hashed_password=get_password_hash("guest")))
        db.commit()
    client.post("/login", data={"username": "guest", "password": "guest"})
    return client
