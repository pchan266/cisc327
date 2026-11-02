def make_renter(client, name="A B", email="ab@example.com"):
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

# Delete a renter
 
def test_delete_renter_removes_it(client):
    renter = make_renter(client)
    assert client.delete(f"/renters/{renter['id']}").status_code in (200, 204)
    assert client.get(f"/renters/{renter['id']}").status_code == 404
 
 
def test_delete_renter_leaves_others_intact(client):
    ann = make_renter(client, "Ann", "ann@example.com")
    bob = make_renter(client, "Bob", "bob@example.com")
    client.delete(f"/renters/{ann['id']}")
    remaining = client.get("/renters").get_json()
    assert [r["id"] for r in remaining] == [bob["id"]]
 
 
#  Look up rentals by renter or equipment
 
def test_lookup_rentals_filters_by_renter(client):
    e1 = make_equipment(client, "Kayak", units=2)
    r1 = make_renter(client, "Ann", "a@example.com")
    r2 = make_renter(client, "Bob", "b@example.com")
    client.post("/rentals", json={"equipment_id": e1["id"], "renter_id": r1["id"]})
    client.post("/rentals", json={"equipment_id": e1["id"], "renter_id": r2["id"]})
    result = client.get(f"/rentals?renter_id={r1['id']}").get_json()
    assert len(result) == 1
    assert result[0]["renter_id"] == r1["id"]
 
 
def test_lookup_rentals_filters_by_equipment(client):
    kayak = make_equipment(client, "Kayak", units=2)
    bike = make_equipment(client, "Bike", "bike", units=2)
    renter = make_renter(client)
    client.post("/rentals", json={"equipment_id": kayak["id"], "renter_id": renter["id"]})
    client.post("/rentals", json={"equipment_id": bike["id"], "renter_id": renter["id"]})
    result = client.get(f"/rentals?equipment_id={bike['id']}").get_json()
    assert len(result) == 1
    assert result[0]["equipment_id"] == bike["id"]
# Check out equipment 
 
def test_checkout_reduces_available_units(client):
    equip = make_equipment(client, units=2)
    renter = make_renter(client)
    resp = client.post(
        "/rentals", json={"equipment_id": equip["id"], "renter_id": renter["id"]}
    )
    assert resp.status_code == 201
    rental = resp.get_json()
    assert rental["equipment_id"] == equip["id"]
    assert rental["renter_id"] == renter["id"]
    after = client.get(f"/equipment/{equip['id']}").get_json()
    assert after["available_units"] == 1
 
 
def test_checkout_rental_appears_in_rentals_list(client):
    equip = make_equipment(client, units=1)
    renter = make_renter(client)
    created = client.post(
        "/rentals", json={"equipment_id": equip["id"], "renter_id": renter["id"]}
    ).get_json()
    rentals = client.get("/rentals").get_json()
    assert len(rentals) == 1
    assert rentals[0]["id"] == created["id"]
    assert rentals[0].get("return_date") is None

# Overdue rentals (enhancement for R1)

def test_overdue_endpoint_lists_past_due_rental_with_details(client):
    rental = _checkout(client)
    store.rentals[rental["id"]].due_date = date.today() - timedelta(days=2)
    resp = client.get("/rentals/overdue")
    assert resp.status_code == 200
    result = resp.get_json()
    assert len(result) == 1
    assert result[0]["id"] == rental["id"]
    assert result[0]["status"] == "Overdue"
    assert result[0]["equipment_name"] == "Kayak 1"
    assert result[0]["renter_name"] == "A B"


def test_overdue_endpoint_excludes_on_time_and_returned_rentals(client):
    on_time = _checkout(client)
    returned = _checkout(client)
    store.rentals[returned["id"]].due_date = date.today() - timedelta(days=2)
    client.put(f"/rentals/{returned['id']}/return")
    assert client.get("/rentals/overdue").get_json() == []
    assert on_time["id"] in [r["id"] for r in client.get("/rentals/active").get_json()]


def test_active_endpoint_flags_each_rental_rented_or_overdue(client):
    fresh = _checkout(client)
    late = _checkout(client)
    store.rentals[late["id"]].due_date = date.today() - timedelta(days=1)
    statuses = {r["id"]: r["status"] for r in client.get("/rentals/active").get_json()}
    assert statuses[fresh["id"]] == "Rented"
    assert statuses[late["id"]] == "Overdue"