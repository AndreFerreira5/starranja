import logging

from bson import ObjectId

from src.models.client import Client, ClientCreate, ClientUpdate

logger = logging.getLogger(__name__)


class ClientRepo:
    def __init__(self, db):
        self.db = db
        self.collection = "clients"

    async def create_client(self, client_data: ClientCreate) -> Client:
        """
        Create a new client.

        Args:
            client_data: Dictionary with client data
        Returns:
            Created client data with _id, createdAt, and updatedAt fields

        Raises:
            Exception: If the license plate already exists (unique constraint violation)
        """
        logger.info(f"Creating client with license plate {client_data.license_plate}")

        raise NotImplementedError("create_client method not yet implemented")

    async def get_by_id(self, client_id: ObjectId) -> Client | None:
        """
        Retrieve a client by its ID.

        Args:
            client_id: MongoDB ObjectId of the client

        Returns:
            Client document if found, None otherwise
        """
        logger.info(f"Retrieving client by ID: {client_id}")

        raise NotImplementedError("get_by_id method not yet implemented")

    async def get_by_nif(self, nif: str) -> Client | None:
        """
        Retrieve a client by its license plate.

        Args:
            license_plate: Client license plate number

        Returns:
            Client document if found, None otherwise
        """
        logger.info(f"Retrieving client by license plate: {nif}")

        raise NotImplementedError("get_by_license_plate method not yet implemented")

    async def update(self, client_id: ObjectId, update_data: ClientUpdate) -> Client | None:
        """
        Update an existing client.

        Args:
            client_id: MongoDB ObjectId of the client to update
            update_data: ClientUpdate object with fields to update

        Returns:
            Updated client document if found, None otherwise
        """
        logger.info(f"Updating client: {client_id}")

        raise NotImplementedError("update method not yet implemented")

    async def delete(self, client_id: ObjectId) -> bool:
        """
        Delete a client from the database.

        Args:
            client_id: MongoDB ObjectId of the client to delete

        Returns:
            True if client was deleted, False if not found

        Note:
            Consider implementing soft delete or checking for active work orders
            before allowing deletion (business rule validation)
        """
        logger.info(f"Deleting client: {client_id}")

        raise NotImplementedError("delete method not yet implemented")
