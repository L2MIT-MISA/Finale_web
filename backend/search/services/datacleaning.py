import json

# --------------------------------------------------
# 1. LOAD THE ORIGINAL JSON FILE
# --------------------------------------------------

with open("data/donnees_brutes.json", "r", encoding="utf-8") as file:
    data = json.load(file)


# --------------------------------------------------
# 2. PROPERTIES WE DON'T NEED
# --------------------------------------------------

properties_to_remove = [
    "country_code",
    "city",
    "postcode",
    "iso3166_2",
    "address_line1",
    "address_line2",
    "details",
    "datasource",
    "distance",
    "place_id"
]


# --------------------------------------------------
# 3. LOOP THROUGH ALL PLACES
# --------------------------------------------------

for lieu in data["lieux"]:
    properties = lieu["properties"]
    for property_name in properties_to_remove:
        properties.pop(property_name, None)


# --------------------------------------------------
# 4. SAVE THE CLEANED JSON
# --------------------------------------------------

with open("data/cleaned_data.json", "w", encoding="utf-8") as file:
    json.dump(data, file, ensure_ascii=False, indent=2)


print("Cleaning finished!")
print(f"Number of places: {len(data['lieux'])}")
print("Saved as: data/cleaned_data.json")