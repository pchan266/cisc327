from datetime import date, timedelta
from unittest.mock import patch

from app import store

TARGET = "app.routes.rentals.send_notification"


def make_renter(client, name="Ann", email="ann@example.com"):
    resp = client.post("/renters", json={"name": name, "email": email})
    assert resp.status_code == 201
    return resp.get_json()


def make_equipment(client, name="Kayak 1", category="kayak", units=1):
    resp = client.post(
        "/equipment",
        json={"name": name, "category": category, "total_units": units},
    )
    assert resp.status_code == 201
    return resp.get_json()


def make_rental(client, overdue=True):
    equip = make_equipment(client)
    renter = make_renter(client)
    rental = client.post(
        "/rentals", json={"equipment_id": equip["id"], "renter_id": renter["id"]}
    ).get_json()
    if overdue:
        store.rentals[rental["id"]].due_date = date.today() - timedelta(days=2)
    return rental, renter


# ---- Notification: failure path (stub) ----

def test_overdue_reminder_failure_is_reported_and_rental_not_marked(client):
    rental, _ = make_rental(client)
    with patch(TARGET, return_value=False):  # stub: always fails
        resp = client.post(f"/rentals/{rental['id']}/overdue-reminder")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["notification_sent"] is False
    assert body["rental_id"] == rental["id"]
    assert not getattr(store.rentals[rental["id"]], "reminder_sent", False)


def test_overdue_reminder_can_be_retried_after_failure(client):
    rental, _ = make_rental(client)
    with patch(TARGET, return_value=False):
        client.post(f"/rentals/{rental['id']}/overdue-reminder")
    with patch(TARGET, return_value=True):
        resp = client.post(f"/rentals/{rental['id']}/overdue-reminder")
    assert resp.get_json()["notification_sent"] is True
    assert store.rentals[rental["id"]].reminder_sent is True


# ---- Notification: non-trigger paths (mock, assert_not_called) ----

def test_no_reminder_for_rental_that_is_not_overdue(client):
    rental, _ = make_rental(client, overdue=False)
    with patch(TARGET) as mock_send:
        resp = client.post(f"/rentals/{rental['id']}/overdue-reminder")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Rental is not overdue"
    mock_send.assert_not_called()


def test_no_reminder_for_returned_rental(client):
    rental, _ = make_rental(client)
    client.put(f"/rentals/{rental['id']}/return")
    with patch(TARGET) as mock_send:
        resp = client.post(f"/rentals/{rental['id']}/overdue-reminder")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Rental is not overdue"
    mock_send.assert_not_called()


def test_no_reminder_for_unknown_rental(client):
    with patch(TARGET) as mock_send:
        resp = client.post("/rentals/999/overdue-reminder")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Rental not found"
    mock_send.assert_not_called()


def test_no_reminder_when_renter_has_no_email(client):
    rental, renter = make_rental(client)
    store.renters[renter["id"]].email = ""
    with patch(TARGET) as mock_send:
        resp = client.post(f"/rentals/{rental['id']}/overdue-reminder")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Renter has no email"
    mock_send.assert_not_called()


# ---- Coverage-directed: renters.py ----

def test_update_unknown_renter_returns_404(client):
    resp = client.put("/renters/999", json={"name": "Ghost"})
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Renter not found"
    assert client.get("/renters").get_json() == []


def test_delete_unknown_renter_returns_404_and_keeps_others(client):
    ann = make_renter(client)
    resp = client.delete("/renters/999")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Renter not found"
    assert [r["id"] for r in client.get("/renters").get_json()] == [ann["id"]]


def test_update_renter_phone_persists(client):
    renter = make_renter(client)
    client.put(f"/renters/{renter['id']}", json={"phone": "6135559999"})
    after = client.get(f"/renters/{renter['id']}").get_json()
    assert after["phone"] == "6135559999"
    assert after["name"] == renter["name"]

# ---- Coverage-directed: views.py ----

def test_home_page_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.content_type
    assert len(resp.data) > 0


def test_renters_page_form_creates_renter(client):
    resp = client.post(
        "/ui/renters", data={"name": "Zed", "email": "zed@example.com"}
    )
    assert resp.status_code == 302  # redirects back to the renters page
    renters = client.get("/renters").get_json()
    assert len(renters) == 1
    assert renters[0]["name"] == "Zed"
    assert renters[0]["email"] == "zed@example.com"


def test_renters_page_lists_existing_renters(client):
    make_renter(client, "Maya", "maya@example.com")
    resp = client.get("/ui/renters")
    assert resp.status_code == 200
    assert b"Maya" in resp.data


def test_delete_renter_page_removes_renter(client):
    ann = make_renter(client, "Ann", "ann@example.com")
    bob = make_renter(client, "Bob", "bob@example.com")
    resp = client.post(f"/ui/renters/{ann['id']}/delete")
    assert resp.status_code == 302
    remaining = client.get("/renters").get_json()
    assert [r["id"] for r in remaining] == [bob["id"]]


def test_delete_renter_page_unknown_id_changes_nothing(client):
    ann = make_renter(client)
    resp = client.post("/ui/renters/999/delete")
    assert resp.status_code == 302
    assert [r["id"] for r in client.get("/renters").get_json()] == [ann["id"]]


def test_rentals_form_rejects_checkout_when_no_units_left(client):
    equip = make_equipment(client, units=1)
    renter = make_renter(client)
    client.post(
        "/rentals", json={"equipment_id": equip["id"], "renter_id": renter["id"]}
    )
    resp = client.post(
        "/ui/rentals",
        data={"equipment_id": equip["id"], "renter_id": renter["id"]},
    )
    assert resp.status_code == 400
    after = client.get(f"/equipment/{equip['id']}").get_json()
    assert after["available_units"] == 0
    assert len(client.get("/rentals").get_json()) == 1