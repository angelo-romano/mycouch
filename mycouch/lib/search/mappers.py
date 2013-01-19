"""The list of search mappers is here."""

geo_mapper = {
    "properties": {
        "coordinates": {
            "type": "geo_point",
        },
    },
}

MAPPERS_BY_RESOURCE = {
    'city': geo_mapper,
    'minorlocality': geo_mapper,
}
