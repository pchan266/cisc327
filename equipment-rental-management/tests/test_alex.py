def make_renter(client, name="A B", email="ab@example.com"):
    resp = client.post("/renters", json={"name": name, "email": email})
    assert resp.status_code == 201
    return resp.get_json()
# list all renters
def test_list_renters_empty_initially(client):
    resp = client.get("/renters")
    assert resp.status_code == 200
    assert resp.get_json() == []
 
 
def test_list_renters_contains_created_renters(client):
    make_renter(client, "Ann", "ann@example.com")
    make_renter(client, "Bob", "bob@example.com")
    renters = client.get("/renters").get_json()
    assert len(renters) == 2
    assert {r["name"] for r in renters} == {"Ann", "Bob"}
 
 
# Create a renter
 
def test_create_renter_returns_expected_fields(client):
    resp = client.post("/renters", json={"name": "Ann", "email": "ann@example.com"})
    assert resp.status_code == 201
    renter = resp.get_json()
    assert renter["name"] == "Ann"
    assert renter["email"] == "ann@example.com"
    assert "id" in renter and "membership_date" in renter
 
 
def test_create_renter_stores_phone_number(client):
    resp = client.post(
        "/renters",
        json={"name": "Ann", "email": "a@example.com", "phone": "6135551234"},
    )
    renter = client.get(f"/renters/{resp.get_json()['id']}").get_json()
    assert renter.get("phone") == "6135551234"