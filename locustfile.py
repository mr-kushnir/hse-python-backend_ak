from locust import HttpUser, TaskSet, task, between
import random

class UserBehavior(TaskSet):
    @task
    def register_user(self):
        """Регистрация нового пользователя"""
        username = f"testuser_{random.randint(1, 100000)}"
        response = self.client.post("/user-register", json={
            "username": username,
            "name": "Test User",
            "birthdate": "2000-01-01T00:00:00",
            "password": "validPassword123"
        })
        assert response.status_code == 200, f"Failed to register user: {response.text}"
        assert response.json()["username"] == username, "Registered username mismatch"

class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 5)  # Пауза между запросами
