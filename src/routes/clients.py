from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.dependencies import get_client_repo
from src.exceptions.clients import (
    ClientDatabaseError,
    ClientNotFoundError,
    DuplicateClientEmailError,
    DuplicateClientNIFError,
)
from src.models.client import Client, ClientCreate, ClientUpdate
from src.repository.client import ClientRepo

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("/", response_model=Client, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    repo: Annotated[ClientRepo, Depends(get_client_repo)],
):
    """Create a new client. Handles duplicate NIF and Email validation."""
    try:
        return await repo.create_client(client_data)
    except DuplicateClientNIFError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "duplicate_nif", "message": str(e), "nif": client_data.nif},
        )
    except DuplicateClientEmailError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "duplicate_email", "message": str(e), "email": client_data.email},
        )
    except ClientDatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "database_error", "message": str(e)},
        )


@router.get("/{client_id}", response_model=Client)
async def get_client(
    client_id: str,
    repo: Annotated[ClientRepo, Depends(get_client_repo)],
):
    """Retrieve a client by ObjectId."""
    if not ObjectId.is_valid(client_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    try:
        client = await repo.get_by_id(ObjectId(client_id))
        return client
    except ClientNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with ID {client_id} not found",
        )
    except ClientDatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "database_error", "message": str(e)},
        )


@router.get("/", response_model=list[Client] | Client)
async def list_clients(
    repo: Annotated[ClientRepo, Depends(get_client_repo)],
    nif: str | None = None,
    email: str | None = None,
):
    """
    List clients OR Find by Filter.

    Query logic:
    - If ?nif={val} is present -> Returns single client by NIF
    - If ?email={val} is present -> Returns single client by email
    - Otherwise -> Returns all clients
    """
    try:
        # Search by NIF
        if nif:
            client = await repo.get_by_nif(nif)
            return client

        # Search by Email
        if email:
            client = await repo.get_by_email(email)
            return client

        # Return all clients
        return await repo.get_all_clients()

    except ClientNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ClientDatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "database_error", "message": str(e)},
        )


@router.patch("/{client_id}", response_model=Client)
async def update_client(
    client_id: str,
    update_data: ClientUpdate,
    repo: Annotated[ClientRepo, Depends(get_client_repo)],
):
    """Update client details using ClientUpdate schema."""
    if not ObjectId.is_valid(client_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    try:
        updated_client = await repo.update(ObjectId(client_id), update_data)
        return updated_client
    except ClientNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with ID {client_id} not found",
        )
    except DuplicateClientNIFError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "duplicate_nif", "message": str(e)},
        )
    except DuplicateClientEmailError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "duplicate_email", "message": str(e)},
        )
    except ClientDatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "database_error", "message": str(e)},
        )


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: str,
    repo: Annotated[ClientRepo, Depends(get_client_repo)],
):
    """Delete a client."""
    if not ObjectId.is_valid(client_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    try:
        success = await repo.delete(ObjectId(client_id))
        if not success:
            raise ClientNotFoundError(client_id)
        return None
    except ClientNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with ID {client_id} not found",
        )
    except ClientDatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "database_error", "message": str(e)},
        )
