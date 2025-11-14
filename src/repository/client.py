import logging
from typing import List

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
            Exception: If the nif number already exists (unique constraint violation)
        """
        logger.info(f"Creating client with nif number {client_data.nif}")

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

    async def get_all_clients(self) -> List[Client]:
        """
        Retrieve all clients from the database.

        Returns:
            List of all Client documents
        """
        logger.info("Retrieving all clients")

        try:
            # Use Beanie's find_all method
            clients = await Client.find_all().to_list()

            logger.info(f"Found {len(clients)} clients")
            return clients

        except Exception as e:
            logger.error(f"Error retrieving all clients: {str(e)}")
            raise

    async def get_by_nif(self, nif: str) -> Client | None:
        """
        Retrieve a client by its nif number.

        Args:
            nif: Client nif number

        Returns:
            Client document if found, None otherwise
        """
        logger.info(f"Retrieving client by nif number: {nif}")

        raise NotImplementedError("get_by_nif method not yet implemented")

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
