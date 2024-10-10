import pytest
from lecture_4.demo_service.core.users import UserService, UserInfo, UserRole, password_is_longer_than_8

def test_register_user():
    service = UserService()
    user_info = UserInfo(
        username="testuser",
        name="Test User",
        birthdate="2000-01-01T00:00:00",
        password="ValidPassword123"
    )
    user = service.register(user_info)
    assert user.uid == 1
    assert user.info.username == "testuser"
    assert user.info.role == UserRole.USER

def test_register_user_existing_username():
    service = UserService()
    user_info = UserInfo(
        username="testuser",
        name="Test User",
        birthdate="2000-01-01T00:00:00",
        password="ValidPassword123"
    )
    service.register(user_info)
    with pytest.raises(ValueError, match="username is already taken"):
        service.register(user_info)

def test_grant_admin():
    service = UserService()
    user_info = UserInfo(
        username="testuser",
        name="Test User",
        birthdate="2000-01-01T00:00:00",
        password="ValidPassword123"
    )
    user = service.register(user_info)
    service.grant_admin(user.uid)
    assert service.get_by_id(user.uid).info.role == UserRole.ADMIN

def test_password_is_longer_than_8():
    assert password_is_longer_than_8("ValidPass") is True
    assert password_is_longer_than_8("short") is False

def test_get_nonexistent_user():
    service = UserService()
    assert service.get_by_username("nonexistent") is None

def test_grant_admin_to_nonexistent_user():
    service = UserService()
    with pytest.raises(ValueError, match="user not found"):
        service.grant_admin(999)

