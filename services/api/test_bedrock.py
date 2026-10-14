from nexa_api.bedrock_service import generate_household_briefing


context = {
    "presence": [
        {
            "occupant_name": "Obumneme",
            "status": "home",
        }
    ],
    "visitors": [
        {
            "name": "Ada Okafor",
            "purpose": "Family visit",
        }
    ],
    "deliveries": [
        {
            "description": "MacBook Pro",
            "carrier": "DHL",
            "status": "expected",
        }
    ],
    "tasks": [
        {
            "title": "Call the electrician tomorrow",
            "status": "open",
        }
    ],
}


print(generate_household_briefing(context))