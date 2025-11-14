import logging
from typing import List

from beanie import PydanticObjectId
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

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
        logger.info(f"Creating new client: {client_data.name}")

        try:
            # Check for duplicate NIF first (mongomock may not enforce unique index)
            existing_client = await Client.find_one(Client.nif == client_data.nif)
            if existing_client:
                raise ValueError(f"Client with NIF {client_data.nif} already exists")

            # Create Client document from ClientCreate data
            client = Client(**client_data.model_dump())

            # Insert into database
            await client.insert()

            logger.info(f"Successfully created client with id: {client.id}")
            return client

        except DuplicateKeyError as e:
            logger.error(f"Duplicate NIF: {client_data.nif}")
            raise ValueError(f"Client with NIF {client_data.nif} already exists") from e
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating client: {str(e)}")
            raise

    async def get_by_id(self, client_id: ObjectId) -> Client | None:
        """
        Retrieve a client by its ID.

        Args:
            client_id: MongoDB ObjectId of the client

        Returns:
            Client document if found, None otherwise
        """

        logger.info(f"Retrieving client with id: {client_id}")

        try:
            # Convert to PydanticObjectId if needed
            if isinstance(client_id, str):
                client_id = PydanticObjectId(client_id)

            # Use Beanie's get method
            client = await Client.get(client_id)

            logger.info(f"Successfully retrieved client with id: {client_id}")

            return client

        except Exception as e:
            logger.error(f"Error retrieving client by ID: {str(e)}")
            raise

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

        logger.info(f"Retrieving client with nif: {nif}")

        try:
            # Use Beanie's find_one method with filter
            client = await Client.find_one(Client.nif == nif)

            logger.info(f"Successfully retrieved client with nif: {nif}")

            return client

        except Exception as e:
            logger.error(f"Error retrieving client by NIF: {str(e)}")
            raise

    async def update(self, client_id: ObjectId, update_data: ClientUpdate) -> Client | None:
        """
        Update an existing client.

        Args:
            client_id: MongoDB ObjectId of the client to update
            update_data: ClientUpdate object with fields to update

        Returns:
            Updated client document if found, None otherwise
        """
        logger.info(f"Updating client with id: {client_id}")
        try:
            # Get the existing client
            client = await Client.get(client_id)

            if not client:
                return None

            # Get only the fields that were explicitly set (exclude unset fields)
            update_dict = update_data.model_dump(exclude_unset=True)

            # If updating NIF, check for duplicates
            if 'nif' in update_dict:
                existing_client = await Client.find_one(Client.nif == update_dict['nif'])
                if existing_client and existing_client.id != client_id:
                    raise ValueError(f"Cannot update: NIF already exists")

            # Update the client fields
            for field, value in update_dict.items():
                setattr(client, field, value)

            # Save the updated client
            await client.save()

            logger.info(f"Successfully updated client with id: {client_id}")

            return client

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating client: {str(e)}")
            raise

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

        logger.info(f"Deleting client with id: {client_id}")

        try:
            # Get the client
            client = await Client.get(client_id)

            if not client:
                return False

            # Delete the client
            await client.delete()

            logger.info(f"Successfully deleted client: {client_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting client: {str(e)}")
            raise
