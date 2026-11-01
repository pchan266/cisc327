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

# Feature 2: Add an equipment item 
def test_create_equipment_returns_expected_fields(client):
    response = client.post(
        "/equipment",
        json={"name": "Kayak", "category": "Boat", "total_units": 4},
    )
    assert response.status_code == 201
    item = response.get_json()
 
    assert item["name"] == "Kayak"
    assert item["category"] == "Boat"
    assert item["total_units"] == 4
    assert item["available_units"] == 4
    assert item["is_available"] is True
    assert "id" in item
 
def test_create_equipment_defaults_to_one_unit(client):
    response = client.post("/equipment", json={"name": "Tent", "category": "Camping"})
    item = response.get_json()
    assert item["total_units"] == 1
    assert item["available_units"] == 1
 
 
def test_create_equipment_is_persisted_and_ids_are_unique(client):
    first = make_equipment(client, name="First")
    second = make_equipment(client, name="Second")
 
    assert first["id"] != second["id"]
    fetched = client.get(f"/equipment/{first['id']}").get_json()
    assert fetched == first
 
 
def test_create_equipment_can_start_out_of_service(client):
    item = make_equipment(client, is_available=False)
    assert item["is_available"] is False
    assert client.get(f"/equipment/{item['id']}").get_json()["is_available"] is False
 
 
def test_create_equipment_missing_name_does_not_create_item(client):
    """A request without a name must never leave a partial record behind."""
    try:
        client.post("/equipment", json={"category": "Boat", "total_units": 1})
    except KeyError:
        pass
    assert client.get("/equipment").get_json() == []
 
 
def test_create_equipment_missing_name_returns_400(client):
    """DOCUMENTED DEFECT: invalid input should be rejected with a 4xx error.
    create_equipment indexes data["name"] directly, so a missing field raises
    KeyError (HTTP 500) instead of returning a 400 response."""
    response = client.post("/equipment", json={"category": "Boat", "total_units": 1})
    assert response.status_code == 400
 
 
def test_create_equipment_via_ui_form_then_visible_in_api(client):
    response = client.post(
        "/ui/equipment",
        data={"name": "Snowshoes", "category": "Winter", "total_units": "3"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Snowshoes" in response.data
 
    items = client.get("/equipment").get_json()
    assert len(items) == 1
    assert items[0]["name"] == "Snowshoes"
    assert items[0]["total_units"] == 3
    assert items[0]["available_units"] == 3

 # Feature 3: View one equipment item
def test_get_equipment_returns_the_requested_item_only(client):
    kayak = make_equipment(client, name="Kayak")
    make_equipment(client, name="Bike")
 
    response = client.get(f"/equipment/{kayak['id']}")
    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == kayak["id"]
    assert body["name"] == "Kayak"
 
 
def test_get_equipment_nonexistent_id_returns_404_with_error(client):
    response = client.get("/equipment/9999")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}

 
def test_update_equipment_changes_fields_and_persists(client):
    item = make_equipment(client, name="Kayak", category="Boat", total_units=2)
 
    response = client.put(
        f"/equipment/{item['id']}",
        json={"name": "Tandem Kayak", "category": "Water Sports"},
    )
    assert response.status_code == 200
    updated = response.get_json()
    assert updated["name"] == "Tandem Kayak"
    assert updated["category"] == "Water Sports"
    fetched = client.get(f"/equipment/{item['id']}").get_json()
    assert fetched["name"] == "Tandem Kayak"
    assert fetched["category"] == "Water Sports"
 
 # Feature 4: Update an equipment item
def test_update_equipment_partial_update_keeps_other_fields(client):
    item = make_equipment(client, name="Kayak", category="Boat", total_units=2)
 
    client.put(f"/equipment/{item['id']}", json={"name": "Renamed"})
 
    fetched = client.get(f"/equipment/{item['id']}").get_json()
    assert fetched["name"] == "Renamed"
    assert fetched["category"] == "Boat"
    assert fetched["total_units"] == 2
    assert fetched["id"] == item["id"]
 
 
def test_update_equipment_does_not_affect_other_items(client):
    first = make_equipment(client, name="First")
    second = make_equipment(client, name="Second")
 
    client.put(f"/equipment/{first['id']}", json={"name": "changed"})
 
    assert client.get(f"/equipment/{second['id']}").get_json()["name"] == "Second"
 
 
def test_update_equipment_nonexistent_id_returns_404(client):
    response = client.put("/equipment/9999", json={"name": "null"})
    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}

#Feature 6: Delete an equipment item
def test_delete_equipment_removes_item_from_get_and_list(client):
    item = make_equipment(client)
 
    response = client.delete(f"/equipment/{item['id']}")
    assert response.status_code == 204
    assert response.data == b""
 
    assert client.get(f"/equipment/{item['id']}").status_code == 404
    assert client.get("/equipment").get_json() == []
 
 
def test_delete_equipment_twice_returns_404_the_second_time(client):
    item = make_equipment(client)
    assert client.delete(f"/equipment/{item['id']}").status_code == 204
 
    second = client.delete(f"/equipment/{item['id']}")
    assert second.status_code == 404
    assert second.get_json() == {"error": "Equipment not found"}
 
 
def test_delete_equipment_leaves_other_items_untouched(client):
    keep = make_equipment(client, name="Keep")
    remove = make_equipment(client, name="Remove")
 
    client.delete(f"/equipment/{remove['id']}")
 
    remaining = client.get("/equipment").get_json()
    assert [i["name"] for i in remaining] == ["Keep"]
    assert remaining[0]["id"] == keep["id"]
 
 
def test_delete_equipment_via_ui_button_removes_item(client):
    item = make_equipment(client, name="Canoe")
 
    response = client.post(f"/ui/equipment/{item['id']}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert client.get(f"/equipment/{item['id']}").status_code == 404
 
 
def test_ui_delete_of_nonexistent_equipment_does_not_error(client):
    make_equipment(client, name="Canoe")
 
    response = client.post("/ui/equipment/9999/delete", follow_redirects=True)
    assert response.status_code == 200
    assert len(client.get("/equipment").get_json()) == 1