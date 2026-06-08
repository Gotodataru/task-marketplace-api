import os
import time
import requests

BASE = os.getenv("E2E_BASE_URL", "http://localhost:8000")


def wait_api_ready(timeout=30):
    for _ in range(timeout):
        try:
            r = requests.get(f"{BASE}/healthz")
            if r.ok:
                print("✅ API доступен")
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("API не ответил на /healthz")


def test_full_flow():
    wait_api_ready()

    ts = int(time.time())
    email = f"customer{ts}@test.local"
    email_p = f"provider{ts}@test.local"
    password = "test123"

    # --- Регистрация заказчика и исполнителя ---
    r = requests.post(
        f"{BASE}/auth/register",
        json={"email": email, "password": password, "full_name": "Customer", "role": "customer"},
    )
    assert r.status_code == 200, f"Register failed: {r.text}"

    r = requests.post(
        f"{BASE}/auth/register",
        json={"email": email_p, "password": password, "full_name": "Provider", "role": "provider"},
    )
    assert r.status_code == 200, f"Register provider failed: {r.text}"

    # --- Логин ---
    r = requests.post(
        f"{BASE}/auth/login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    user_id = r.json().get("user_id")
    assert user_id is not None
    headers_c = {"Authorization": f"Bearer {token}"}

    r = requests.post(
        f"{BASE}/auth/login", json={"email": email_p, "password": password}
    )
    assert r.status_code == 200, f"Login provider failed: {r.text}"
    provider_id = r.json()["user_id"]

    r = requests.get(f"{BASE}/auth/me", headers=headers_c)
    assert r.status_code == 200, f"/me failed: {r.text}"
    assert r.json()["id"] == user_id

    # --- POST /jobs (с авторизацией) ---
    r = requests.post(
        f"{BASE}/jobs",
        json={
            "title": "Тестовое поручение",
            "price_rub": 100,
            "lat": 55.75,
            "lon": 37.61,
            "category": "carry",
            "address": "Москва, центр",
        },
        headers=headers_c,
    )
    assert r.status_code == 201, f"Job create failed: {r.text}"
    job_id = r.json()["id"]
    print("✅ Задание создано:", job_id)

    # --- Назначение исполнителя (заказчик) ---
    r_assign = requests.post(
        f"{BASE}/jobs/{job_id}/assign",
        json={"provider_id": provider_id},
        headers=headers_c,
    )
    assert r_assign.status_code == 200, f"Assign failed: {r_assign.text}"
    assert r_assign.json()["provider_id"] == provider_id
    assert r_assign.json()["status"] == "matched"
    print("✅ Исполнитель назначен")

    # --- presign media ---
    r = requests.post(f"{BASE}/media/presign-upload", headers=headers_c)
    assert r.status_code == 200, f"Presign failed: {r.text}"
    print("✅ Presigned URL получен")

    print("✅ E2E: auth, /me, jobs, assign, media")


if __name__ == "__main__":
    test_full_flow()
