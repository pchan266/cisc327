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
# View one renter
 
def test_get_renter_matches_created(client):
    created = make_renter(client)
    resp = client.get(f"/renters/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created
 
 
def test_get_renter_returns_correct_one_among_many(client):
    make_renter(client, "Ann", "ann@example.com")
    bob = make_renter(client, "Bob", "bob@example.com")
    fetched = client.get(f"/renters/{bob['id']}").get_json()
    assert fetched["name"] == "Bob"
    assert fetched["email"] == "bob@example.com"
 
 
# Update a renter
 
def test_update_renter_name_persists(client):
    renter = make_renter(client, "Ann", "ann@example.com")
    resp = client.put(f"/renters/{renter['id']}", json={"name": "Ann Lee"})
    assert resp.status_code == 200
    after = client.get(f"/renters/{renter['id']}").get_json()
    assert after["name"] == "Ann Lee"
    assert after["email"] == "ann@example.com"
 
 
def test_update_renter_email_persists(client):
    renter = make_renter(client, "Ann", "ann@example.com")
    client.put(f"/renters/{renter['id']}", json={"email": "new@example.com"})
    after = client.get(f"/renters/{renter['id']}").get_json()
    assert after["email"] == "new@example.com"
    assert after["name"] == "Ann"