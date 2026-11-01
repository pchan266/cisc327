'''
Tests for Table B features 1-8
Phoebe Chan
20477667
'''
# Helpers
def make_equipment(client, name="Kayak", category="Boat", total_units=2, **extra):
    payload = {"name": name, "category": category, "total_units": total_units}
    payload.update(extra)
    response = client.post("/equipment", json=payload)
    assert response.status_code == 201
    return response.get_json()

def make_renter(client, name="firstname lastname", email="example@email.com"):
    response = client.post("/renters", json={"name": name, "email": email})
    assert response.status_code == 201
    return response.get_json()
 
 
def checkout(client, equipment_id, renter_id):
    response = client.post(
        "/rentals", json={"equipment_id": equipment_id, "renter_id": renter_id}
    )
    assert response.status_code == 201
    return response.get_json()
 
 # Feature 1: List all equipment
def test_list_equipment_returns_every_created_item_with_fields(client):
    make_equipment(client, name="Kayak", category="Boat", total_units=3)
    make_equipment(client, name="Road Bike", category="Bike", total_units=5)
    make_equipment(client, name="Helmet", category="Safety", total_units=10)
 
    response = client.get("/equipment")
    assert response.status_code == 200
    items = response.get_json()
 
    assert len(items) == 3
    assert {i["name"] for i in items} == {"Kayak", "Road Bike", "Helmet"}
    bike = next(i for i in items if i["name"] == "Road Bike")
    assert bike["category"] == "Bike"
    assert bike["total_units"] == 5
    assert bike["available_units"] == 5
 
 
def test_list_equipment_supports_at_least_150_items(client):
    """R7: the system must support at least 150 items."""
    for n in range(150):
        make_equipment(client, name=f"Item {n}", total_units=1)
 
    items = client.get("/equipment").get_json()
    assert len(items) == 150
    assert len({i["id"] for i in items}) == 150  # every id is unique
 
 
def test_list_equipment_reflects_a_rental_in_available_units(client):
    item = make_equipment(client, total_units=3)
    renter = make_renter(client)
    checkout(client, item["id"], renter["id"])
 
    listed = client.get("/equipment").get_json()[0]
    assert listed["total_units"] == 3
    assert listed["available_units"] == 2
 
 
def test_equipment_ui_page_lists_items(client):
    make_equipment(client, name="Paddleboard")
 
    response = client.get("/ui/equipment")
    assert response.status_code == 200
    assert b"Paddleboard" in response.data
 
 
def test_equipment_has_single_status_field(client):
    """DOCUMENTED DEFECT (R8): each item should carry exactly one status of
    Available, Rented, Overdue or Out of Service. Equipment only exposes an
    is_available boolean, so there is no status field."""
    item = make_equipment(client)
    assert item.get("status") in {"Available", "Rented", "Overdue", "Out of Service"}
 
 