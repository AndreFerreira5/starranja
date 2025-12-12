import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.models.auth import User


@pytest.mark.asyncio
class TestAdminActions:
    async def test_admin_can_update_user(self, client: AsyncClient, admin_token: dict, registered_user: dict):
        """Test that an admin can update another user's profile"""
        admin_token = admin_token["token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Target user ID (from the registered_user fixture)
        target_user_id = registered_user["response"]["id"]

        # 2. Update Request
        new_name = "Updated By Admin"
        update_res = await client.patch(f"/auth/users/{target_user_id}", json={"full_name": new_name}, headers=headers)

        assert update_res.status_code == 200
        assert update_res.json()["full_name"] == new_name

    async def test_admin_can_delete_user(self, client: AsyncClient, admin_token: dict, test_session):
        """Test that an admin can delete a user"""
        # 1. Create a temporary user to delete
        temp_user_data = {
            "username": "todelete",
            "password": "Pass123!",
            "full_name": "To Delete",
            "email": "delete@test.com",
            "role": "mecanico",
        }

        admin_token = admin_token["token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        create_res = await client.post("/auth/register", json=temp_user_data, headers=headers)
        assert create_res.status_code == 201
        target_id = create_res.json()["id"]

        # 2. Delete the user
        delete_res = await client.delete(f"/auth/users/{target_id}", headers=headers)
        assert delete_res.status_code == 204

        # 3. Verify deletion in DB
        result = await test_session.execute(select(User).where(User.id == target_id))
        user_in_db = result.scalar_one_or_none()
        assert user_in_db is None

    async def test_non_admin_cannot_update(self, client: AsyncClient, registered_user: dict):
        """Test that a regular user CANNOT update a user"""
        # Login as regular user
        login_res = await client.post(
            "/auth/login",
            json={
                "username": registered_user["user_data"]["username"],
                "password": registered_user["user_data"]["password"],
            },
        )
        user_token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {user_token}"}

        target_id = registered_user["response"]["id"]

        # Try update
        res = await client.patch(f"/auth/users/{target_id}", json={"full_name": "Hacker Update"}, headers=headers)
        assert res.status_code == 403

    async def test_non_admin_cannot_delete(self, client: AsyncClient, registered_user: dict):
        """Test that a regular user CANNOT delete a user"""
        # Login as regular user
        login_res = await client.post(
            "/auth/login",
            json={
                "username": registered_user["user_data"]["username"],
                "password": registered_user["user_data"]["password"],
            },
        )
        user_token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {user_token}"}

        target_id = registered_user["response"]["id"]

        # Try delete
        res = await client.delete(f"/auth/users/{target_id}", headers=headers)
        assert res.status_code == 403

    async def test_update_non_existent_user(self, client: AsyncClient, admin_token: dict):
        """Test updating a UUID that doesn't exist"""
        # Use the token provided by the fixture directly
        headers = {"Authorization": f"Bearer {admin_token['token']}"}

        fake_id = "00000000-0000-0000-0000-000000000000"
        res = await client.patch(f"/auth/users/{fake_id}", json={"full_name": "Ghost"}, headers=headers)
        assert res.status_code == 404
