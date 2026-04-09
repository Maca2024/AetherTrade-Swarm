"""
AETHERTRADE-SWARM — Shared FastAPI Dependencies
Provides simulator and database client as dependency-injected singletons.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from models.database import DatabaseClient, get_db
from utils.data_simulator import DataSimulator, get_simulator


def get_simulator_dep() -> DataSimulator:
    return get_simulator()


def get_db_dep() -> DatabaseClient:
    return get_db()


SimulatorDep = Annotated[DataSimulator, Depends(get_simulator_dep)]
DatabaseDep = Annotated[DatabaseClient, Depends(get_db_dep)]
