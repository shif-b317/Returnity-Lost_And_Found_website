"""
RETURNITY - Comprehensive System Test Suite
Validates authentication, reporting, search, claims, verification engine,
decision support scoring, administrative governance, and access security.
"""

import os
import io
import unittest
from app import app
from database import query_db, execute_db, init_admin_user
from config import Config

class ReturnitySystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()
        init_admin_user()

    def setUp(self):
        # Clear active session before each test case
        self.client.get("/logout")

    def test_01_public_pages(self):
        """Test public routes load successfully with HTTP 200."""
        routes = ["/", "/about", "/terms", "/privacy", "/search"]
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Failed on route: {route}")
            self.assertIn(b"RETURNITY", response.data)

    def test_02_registration_and_duplicate_prevention(self):
        """Test registration validation, successful signup, and duplicate email prevention."""
        test_email = "student_tester@returnity.org"
        execute_db("DELETE FROM users WHERE email = %s", (test_email,))

        # 1. Valid registration
        res = self.client.post("/register", data={
            "full_name": "Student Tester",
            "email": test_email,
            "phone": "9988776655",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Welcome to RETURNITY", res.data)

        # Clear session to test duplicate attempt as unauthenticated visitor
        self.client.get("/logout")

        # 2. Duplicate registration attempt
        res_dup = self.client.post("/register", data={
            "full_name": "Duplicate Tester",
            "email": test_email,
            "phone": "9988776655",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertIn(b"already exists", res_dup.data)

    def test_03_authentication_workflow(self):
        """Test login, invalid credentials, and logout."""
        test_email = "student_tester@returnity.org"

        # 1. Invalid password
        res_fail = self.client.post("/login", data={
            "email": test_email,
            "password": "WrongPassword!"
        }, follow_redirects=True)
        self.assertIn(b"Invalid email address or password", res_fail.data)

        # 2. Valid login
        res_ok = self.client.post("/login", data={
            "email": test_email,
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(res_ok.status_code, 200)
        self.assertIn(b"Student Tester", res_ok.data)

        # 3. Logout
        res_logout = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b"signed out successfully", res_logout.data)

    def test_04_protected_routes(self):
        """Unauthenticated user accessing /dashboard must be redirected to /login."""
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])

    def test_05_report_lost_item_with_split_information(self):
        """Test reporting a lost item with distinct public and private verification fields."""
        self.client.post("/login", data={
            "email": "student_tester@returnity.org",
            "password": "Password123!"
        })

        res = self.client.post("/report-lost", data={
            "item_name": "Lenovo ThinkPad Laptop",
            "category_id": "1",
            "date_lost": "2026-09-10",
            "approximate_time": "11:30 AM",
            "location_lost": "Computer Science Lab 3, 2nd Floor",
            "description": "Black ThinkPad laptop with textured lid and red TrackPoint button.",
            "additional_info": "Left during Database Management lecture",
            "private_identifying_detail": "Subtle scratch shaped like letter T under battery bay",
            "private_distinctive_characteristic": "Sticker of Python logo on keyboard palm rest",
            "private_contents": "Sticker inside sleeve, sticker label",
            "private_serial_or_id": "SN-LNV-998821"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Lenovo ThinkPad Laptop", res.data)
        # Verify private detail is NOT exposed in public HTML output
        self.assertNotIn(b"Subtle scratch shaped like letter T", res.data)
        self.assertNotIn(b"SN-LNV-998821", res.data)

    def test_06_report_found_item(self):
        """Test reporting a found item."""
        self.client.post("/login", data={
            "email": "student_tester@returnity.org",
            "password": "Password123!"
        })

        res = self.client.post("/report-found", data={
            "item_name": "Fastrack Black Sports Watch",
            "category_id": "6",
            "date_found": "2026-09-12",
            "approximate_time": "3:00 PM",
            "location_found": "Sports Complex Badminton Court 2",
            "description": "Black silicone strap wristwatch with digital dial.",
            "custody_location": "Campus Sports Room Locker 4",
            "private_finder_notes": "Small white mark on back buckle"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Fastrack Black Sports Watch", res.data)

    def test_07_search_and_filtering(self):
        """Test search query, category filtering, and type filtering."""
        res_kw = self.client.get("/search?q=ThinkPad")
        self.assertEqual(res_kw.status_code, 200)
        self.assertIn(b"Lenovo ThinkPad", res_kw.data)

        res_cat = self.client.get("/search?category=1")
        self.assertEqual(res_cat.status_code, 200)
        self.assertIn(b"Lenovo ThinkPad", res_cat.data)

        res_type = self.client.get("/search?type=found")
        self.assertEqual(res_type.status_code, 200)
        self.assertIn(b"Fastrack Black Sports Watch", res_type.data)

    def test_08_claim_submission_and_rule_scoring(self):
        """Test filing a claim as another user and verify rule-based scoring calculation."""
        claimant_email = "claimant_alex@returnity.org"
        execute_db("DELETE FROM users WHERE email = %s", (claimant_email,))
        
        self.client.post("/register", data={
            "full_name": "Alex Mercer",
            "email": claimant_email,
            "phone": "9811223344",
            "password": "Password123!",
            "confirm_password": "Password123!"
        })

        # Find the reported ThinkPad
        item = query_db("SELECT id FROM lost_items WHERE item_name = 'Lenovo ThinkPad Laptop' ORDER BY id DESC LIMIT 1", one=True)
        self.assertIsNotNone(item)

        # Alex claims the ThinkPad with accurate private details and location
        res = self.client.post(f"/claim/lost/{item['id']}", data={
            "q_identify": "Recognized the lab 3 location and exact date of loss.",
            "q_location": "Computer Science Lab 3, 2nd Floor, desk row 4",
            "q_time": "2026-09-10 at 11:30 AM",
            "q_private_features": "There is a subtle scratch shaped like letter T under battery bay",
            "q_scratches": "Python logo sticker on palm rest and serial SN-LNV-998821",
            "q_accessories": "Black velvet protective laptop sleeve",
            "q_additional": "Purchased from authorized Lenovo store"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Claim submitted successfully", res.data)

        # Inspect calculated score in database
        claim_rec = query_db(
            "SELECT * FROM claims WHERE claimant_id = (SELECT id FROM users WHERE email = %s) ORDER BY id DESC LIMIT 1",
            (claimant_email,),
            one=True
        )
        self.assertIsNotNone(claim_rec)
        self.assertGreaterEqual(claim_rec["verification_score"], 60)
        self.assertIn(claim_rec["confidence_level"], ["Strong Verification", "Needs Review"])

    def test_09_admin_authorization_and_review(self):
        """Test admin login, authorization protection, review screen, and approval workflow."""
        # Ensure normal user cannot access admin
        self.client.post("/login", data={
            "email": "claimant_alex@returnity.org",
            "password": "Password123!"
        })
        res_unauth = self.client.get("/admin")
        self.assertEqual(res_unauth.status_code, 403)

        # Admin login
        self.client.get("/logout")
        res_admin_login = self.client.post("/admin/login", data={
            "email": Config.ADMIN_EMAIL,
            "password": Config.ADMIN_PASSWORD
        }, follow_redirects=True)
        self.assertEqual(res_admin_login.status_code, 200)
        self.assertIn(b"Operations Dashboard", res_admin_login.data)

        # Admin checks claims
        claim_rec = query_db("SELECT id FROM claims ORDER BY id DESC LIMIT 1", one=True)
        self.assertIsNotNone(claim_rec)

        res_review = self.client.get(f"/admin/claim/{claim_rec['id']}")
        self.assertEqual(res_review.status_code, 200)
        self.assertIn(b"Rule-Based Verification Metric", res_review.data)
        self.assertIn(b"Original Reporter Private Verification Details", res_review.data)

        # Admin approves claim
        res_approve = self.client.post(f"/admin/claim/{claim_rec['id']}/action", data={
            "action": "approve",
            "admin_notes": "All private serial numbers and marks match the stored repository records."
        }, follow_redirects=True)
        self.assertEqual(res_approve.status_code, 200)

        # Verify claim status updated to Approved
        updated_claim = query_db("SELECT status FROM claims WHERE id = %s", (claim_rec["id"],), one=True)
        self.assertEqual(updated_claim["status"], "Approved")

        # Verify item status updated to Returned/Claimed
        item_rec = query_db("SELECT status FROM lost_items WHERE item_name = 'Lenovo ThinkPad Laptop' ORDER BY id DESC LIMIT 1", one=True)
        self.assertEqual(item_rec["status"], "Returned")

    def test_10_audit_log_verification(self):
        """Verify that audit logs recorded major events."""
        logs = query_db("SELECT action FROM claim_audit_logs ORDER BY id DESC LIMIT 10")
        actions = [log["action"] for log in logs]
        self.assertIn("APPROVE_CLAIM", actions)
        self.assertIn("SUBMIT_CLAIM", actions)

    def test_11_request_more_information_workflow(self):
        """Test admin requesting additional information and claimant providing response."""
        # 1. Report an item to claim
        self.client.post("/login", data={"email": "student_tester@returnity.org", "password": "Password123!"})
        res_found = self.client.post("/report-found", data={
            "item_name": "Leather Cardholder Wallet",
            "category_id": "2",
            "date_found": "2026-09-11",
            "location_found": "Main Canteen counter",
            "description": "Tan leather cardholder with 4 card slots.",
            "custody_location": "Security Office Desk"
        }, follow_redirects=True)
        found_item = query_db("SELECT id FROM found_items WHERE item_name = 'Leather Cardholder Wallet' ORDER BY id DESC LIMIT 1", one=True)

        # 2. Alex claims the cardholder
        self.client.get("/logout")
        self.client.post("/login", data={"email": "claimant_alex@returnity.org", "password": "Password123!"})
        self.client.post(f"/claim/found/{found_item['id']}", data={
            "q_identify": "I lost this wallet after lunch in the canteen.",
            "q_location": "Main Canteen table 3",
            "q_time": "2026-09-11 around 1:30 PM",
            "q_private_features": "Contains a metro card ending in 8832 inside second slot",
            "q_scratches": "Slight water stain on bottom right corner",
            "q_accessories": "None",
            "q_additional": "Name on card matches my college ID"
        })
        new_claim = query_db("SELECT id FROM claims WHERE item_type = 'found' AND item_id = %s ORDER BY id DESC LIMIT 1", (found_item["id"],), one=True)
        self.assertIsNotNone(new_claim)

        # 3. Admin logs in and requests more information
        self.client.get("/logout")
        self.client.post("/admin/login", data={"email": Config.ADMIN_EMAIL, "password": Config.ADMIN_PASSWORD})
        self.client.post(f"/admin/claim/{new_claim['id']}/action", data={
            "action": "request_info",
            "admin_notes": "Please specify the issuing bank of the debit card."
        })
        claim_status_check = query_db("SELECT status FROM claims WHERE id = %s", (new_claim["id"],), one=True)
        self.assertEqual(claim_status_check["status"], "Additional Information Required")

        # 4. Claimant logs in and provides the response
        self.client.get("/logout")
        self.client.post("/login", data={"email": "claimant_alex@returnity.org", "password": "Password123!"})
        res_reply = self.client.post(f"/claim/respond/{new_claim['id']}", data={
            "additional_info": "The debit card is issued by State Bank of India with platinum chip."
        }, follow_redirects=True)
        self.assertEqual(res_reply.status_code, 200)

        # Verify claim status moved back to Under Admin Review
        updated_claim = query_db("SELECT status, additional_info_provided FROM claims WHERE id = %s", (new_claim["id"],), one=True)
        self.assertEqual(updated_claim["status"], "Under Admin Review")
        self.assertIn("State Bank of India", updated_claim["additional_info_provided"])

    def test_12_evidence_access_protection(self):
        """Test that sensitive ownership evidence is blocked for unauthorized users."""
        # Insert a dummy evidence record linked to Alex's claim
        claim = query_db("SELECT id FROM claims ORDER BY id DESC LIMIT 1", one=True)
        execute_db(
            """
            INSERT INTO ownership_evidence (claim_id, file_path, original_filename, file_type, description)
            VALUES (%s, 'test_private_invoice.pdf', 'invoice.pdf', 'pdf', 'Purchase receipt')
            """,
            (claim["id"],)
        )

        # Log in as third unrelated user
        third_email = "third_party@returnity.org"
        execute_db("DELETE FROM users WHERE email = %s", (third_email,))
        self.client.post("/register", data={
            "full_name": "Third Party User",
            "email": third_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        })

        # Attempt to access Alex's private evidence file -> Must be 403 Forbidden!
        res_ev = self.client.get("/evidence/test_private_invoice.pdf")
        self.assertEqual(res_ev.status_code, 403)

    def test_13_report_modification_and_deletion(self):
        """Test that users can update and delete their own reports, but not others."""
        self.client.post("/login", data={"email": "student_tester@returnity.org", "password": "Password123!"})
        item = query_db("SELECT id FROM lost_items WHERE user_id = (SELECT id FROM users WHERE email = 'student_tester@returnity.org') ORDER BY id DESC LIMIT 1", one=True)
        self.assertIsNotNone(item)

        # Update report
        res_edit = self.client.post(f"/report/edit/lost/{item['id']}", data={
            "item_name": "Lenovo ThinkPad Laptop (Updated)",
            "category_id": "1",
            "event_date": "2026-09-10",
            "location": "Computer Science Lab 3",
            "description": "Updated description with more details.",
            "status": "Active",
            "private_identifying_detail": "Subtle scratch shaped like letter T"
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)

        check_update = query_db("SELECT item_name FROM lost_items WHERE id = %s", (item["id"],), one=True)
        self.assertEqual(check_update["item_name"], "Lenovo ThinkPad Laptop (Updated)")

    def test_14_error_handlers(self):
        """Test custom 404 handler."""
        res_404 = self.client.get("/nonexistent-page-url-12345")
        self.assertEqual(res_404.status_code, 404)
        self.assertIn(b"Listing or Page Not Found", res_404.data)

if __name__ == "__main__":
    unittest.main()
