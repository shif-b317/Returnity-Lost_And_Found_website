"""
Seed realistic initial listings and category items for demonstration.
All items are real database rows that can be claimed, verified, and searched.
"""

from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from database import query_db, execute_db, log_audit, init_admin_user

def seed_demo_listings():
    init_admin_user()

    # Create a demo student user if not present
    demo_user = query_db("SELECT id FROM users WHERE email = 'rohit.sharma@example.com'", one=True)
    if not demo_user:
        pw_hash = generate_password_hash("Student2026!", method="scrypt")
        res = execute_db(
            """
            INSERT INTO users (full_name, email, phone, password_hash, role, is_active)
            VALUES ('Rohit Sharma', 'rohit.sharma@example.com', '9876501234', %s, 'user', 1)
            """,
            (pw_hash,)
        )
        user_id = res["last_id"]
    else:
        user_id = demo_user["id"]

    # Check if lost items are populated
    lost_count = query_db("SELECT COUNT(*) AS c FROM lost_items", one=True)["c"]
    if lost_count < 2:
        today = date.today()
        # 1. Lost HP Laptop
        execute_db(
            """
            INSERT INTO lost_items (
                user_id, category_id, item_name, description, date_lost,
                approximate_time, location_lost, additional_info,
                private_identifying_detail, private_distinctive_characteristic,
                private_contents, private_serial_or_id, private_exact_location, status
            ) VALUES (
                %s, 1, 'HP Pavilion 15 Silver Laptop',
                'Silver finish 15-inch HP laptop with black protective sleeve. Intel Core i5 badge.',
                %s, '10:45 AM', 'Central Library Ground Floor Study Hall',
                'Left on table 14 near reference section',
                'Hairline crack on top left corner of screen frame',
                'VS Code sticker on lid and small dot on trackpad',
                'Sandisk 64GB flash drive inside front sleeve pocket',
                'SN: 5CD142890K', 'Table 14, Desk row facing west', 'Active'
            )
            """,
            (user_id, today - timedelta(days=2))
        )

        # 2. Lost Bifold Wallet
        execute_db(
            """
            INSERT INTO lost_items (
                user_id, category_id, item_name, description, date_lost,
                approximate_time, location_lost, additional_info,
                private_identifying_detail, private_distinctive_characteristic,
                private_contents, private_serial_or_id, private_exact_location, status
            ) VALUES (
                %s, 2, 'Brown Leather Bifold Wallet',
                'Dark brown textured leather wallet with embossed edge stitching.',
                %s, '1:15 PM', 'University Cafeteria Outdoor Seating',
                'Likely slipped out on bench',
                'Silver commemorative coin inside inner zippered pouch',
                'Faded monogram RS stamped on interior divider',
                'State Bank debit card, college smart card, metro token',
                'Card ending in 7741', 'Wooden bench near main cafeteria entrance', 'Active'
            )
            """,
            (user_id, today - timedelta(days=4))
        )

    # Check if found items are populated
    found_count = query_db("SELECT COUNT(*) AS c FROM found_items", one=True)["c"]
    if found_count < 2:
        today = date.today()
        # 1. Found Keys
        execute_db(
            """
            INSERT INTO found_items (
                user_id, category_id, item_name, description, date_found,
                approximate_time, location_found, additional_info,
                custody_location, private_finder_notes, status
            ) VALUES (
                %s, 3, 'Set of 3 Bike Keys on Red Lanyard',
                'Honda ignition key and two small brass padlock keys on a woven red cord lanyard.',
                %s, '4:20 PM', 'Two-Wheeler Parking Lot Stand B',
                'Found near parking slot 45',
                'Deposited with Main Gate Security Guard',
                'Lanyard has faded white text reading HONDA RACING', 'Active'
            )
            """,
            (user_id, today - timedelta(days=1))
        )

        # 2. Found Optical Glasses
        execute_db(
            """
            INSERT INTO found_items (
                user_id, category_id, item_name, description, date_found,
                approximate_time, location_found, additional_info,
                custody_location, private_finder_notes, status
            ) VALUES (
                %s, 9, 'Tortoiseshell Eyeglasses in Hard Case',
                'Prescription spectacles with rectangular tortoiseshell frames kept inside a matte black protective case.',
                %s, '11:00 AM', 'Seminar Hall Room 302',
                'Left on third row seat',
                'Department Office Room 101 Reception',
                'Case brand is Fastrack with microfibre cleaning cloth inside', 'Active'
            )
            """,
            (user_id, today - timedelta(days=3))
        )

    print("Demo data seeded successfully!")

if __name__ == "__main__":
    seed_demo_listings()
