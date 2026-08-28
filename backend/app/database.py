"""SQLite connection via SQLModel. Loads seed JSON on startup if tables are empty."""
import json
import os
from typing import Optional
from pathlib import Path
from sqlmodel import SQLModel, Session, select, create_engine

from app.models.db_models import Village, Shelter, Route

DATA_DIR = Path(__file__).parent / "data"


def get_engine(db_url: str = "sqlite:///./relocation.db"):
    """Create a synchronous SQLite engine."""
    return create_engine(db_url, echo=False)


def create_tables(engine):
    """Create all tables defined by SQLModel models."""
    SQLModel.metadata.create_all(engine)


def get_session(engine):
    """Return a new Session."""
    return Session(engine)


def _load_json(filename: str) -> list:
    """Load a JSON file from the data directory."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Seed data file not found: {filepath}")
    with open(filepath, "r") as f:
        return json.load(f)


def seed_villages(session: Session) -> int:
    """Load villages from seed JSON. Returns count inserted."""
    existing = session.exec(select(Village)).all()
    if existing:
        return 0

    data = _load_json("seed_villages.json")
    for row in data:
        village = Village(**row)
        session.add(village)
    session.commit()
    return len(data)


def seed_shelters(session: Session) -> int:
    """Load shelters from seed JSON. Returns count inserted."""
    existing = session.exec(select(Shelter)).all()
    if existing:
        return 0

    data = _load_json("seed_shelters.json")
    for row in data:
        # Convert facilities list to JSON string for storage
        if isinstance(row.get("facilities"), list):
            row["facilities"] = json.dumps(row["facilities"])
        shelter = Shelter(**row)
        session.add(shelter)
    session.commit()
    return len(data)


def seed_routes(session: Session) -> int:
    """Load routes from seed JSON. Returns count inserted."""
    existing = session.exec(select(Route)).all()
    if existing:
        return 0

    data = _load_json("seed_routes.json")
    for row in data:
        route = Route(**row)
        session.add(route)
    session.commit()
    return len(data)


def load_all_seed_data(engine) -> dict:
    """
    Load all seed data into SQLite if tables are empty.
    Returns a summary dict of what was loaded.
    """
    create_tables(engine)
    summary = {"villages": 0, "shelters": 0, "routes": 0}

    with Session(engine) as session:
        summary["villages"] = seed_villages(session)
        summary["shelters"] = seed_shelters(session)
        summary["routes"] = seed_routes(session)

    return summary


def get_all_villages(engine) -> list:
    """Return all villages."""
    with Session(engine) as session:
        return list(session.exec(select(Village)).all())


def get_village_by_id(engine, village_id: str) -> Optional[Village]:
    """Return a single village by ID, or None."""
    with Session(engine) as session:
        return session.get(Village, village_id)


def get_all_shelters(engine) -> list:
    """Return all shelters."""
    with Session(engine) as session:
        return list(session.exec(select(Shelter)).all())


def get_shelters_by_village(engine, village_id: str) -> list:
    """Return shelters located in a specific village."""
    with Session(engine) as session:
        return list(
            session.exec(select(Shelter).where(Shelter.village_id == village_id)).all()
        )


def get_all_routes(engine) -> list:
    """Return all routes."""
    with Session(engine) as session:
        return list(session.exec(select(Route)).all())


def get_routes_from_village(engine, village_id: str) -> list:
    """Return all routes originating from a village."""
    with Session(engine) as session:
        return list(
            session.exec(
                select(Route).where(Route.from_village_id == village_id)
            ).all()
        )


def get_route_between(engine, from_id: str, to_id: str) -> Optional[Route]:
    """Return the route between two villages, or None."""
    with Session(engine) as session:
        return session.exec(
            select(Route).where(
                Route.from_village_id == from_id,
                Route.to_village_id == to_id,
            )
        ).first()
