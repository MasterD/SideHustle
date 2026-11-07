"""Exercise real HTTP requests against a temporary, local database.

These checks focus on business rules and the local request boundary. They never
open social accounts, send notifications or touch the developer's demo database.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.parse import urlencode

from hub.application import create_application
from server import make_server


class BusinessHubIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "test.sqlite3"
        self.server = make_server("127.0.0.1", 0, self.database_path)
        # Keep test output focused on assertions, without muting the normal server.
        original_handler = self.server.RequestHandlerClass

        class QuietRequestHandler(original_handler):
            def log_message(self, format, *arguments):
                pass

        self.server.RequestHandlerClass = QuietRequestHandler
        self.server_thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.server_thread.start()
        self.port = self.server.server_address[1]
        self.origin = f"http://127.0.0.1:{self.port}"

        status, session, _ = self.request("GET", "/api/session")
        self.assertEqual(status, 200, session)
        self.csrf_token = session["csrfToken"]
        self.demo_company_id = session["defaultCompanyId"]

        status, company, _ = self.write(
            "POST", "/api/companies", {"name": "QA Studio", "slug": "qa-studio"}
        )
        self.assertEqual(status, 201, company)
        self.company_id = company["id"]
        self.company_slug = company["slug"]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=5)
        self.temporary_directory.cleanup()

    def request(self, method, path, body=None, headers=None):
        """Use a new connection for each request, including concurrent bookings."""
        request_headers = {"Accept": "application/json"}
        if body is not None:
            body = json.dumps(body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            response_body = response.read()
            response_headers = dict(response.getheaders())
            try:
                payload = json.loads(response_body) if response_body else None
            except json.JSONDecodeError:
                payload = response_body.decode("utf-8", errors="replace")
            return response.status, payload, response_headers
        finally:
            connection.close()

    def write(self, method, path, body, headers=None):
        request_headers = {
            "Origin": self.origin,
            "X-CSRF-Token": self.csrf_token,
        }
        if headers:
            request_headers.update(headers)
        return self.request(method, path, body, request_headers)

    def company_path(self, resource, company_id=None):
        return f"/api/companies/{company_id or self.company_id}/{resource}"

    def public_path(self, resource="", slug=None):
        suffix = f"/{resource}" if resource else ""
        return f"/api/public/{slug or self.company_slug}{suffix}"

    def create_lead(self, **overrides):
        data = {
            "name": "Casey Example",
            "email": "casey@example.test",
            "phone": "+27 00 000 0000",
            "message": "Please contact me about the workshop.",
            "source": "manual",
            "status": "new",
            "value": 1000,
            "commissionRate": 10,
        }
        data.update(overrides)
        status, lead, _ = self.write("POST", self.company_path("leads"), data)
        self.assertEqual(status, 201, lead)
        return lead

    def create_service(self, **overrides):
        data = {
            "name": "Appointment test",
            "description": "An appointment used by the integration tests.",
            "durationMinutes": 60,
            "price": 250,
            "active": True,
        }
        data.update(overrides)
        status, service, _ = self.write("POST", self.company_path("services"), data)
        self.assertEqual(status, 201, service)
        return service

    def future_slot(self, service):
        status, settings, _ = self.write(
            "PATCH",
            self.company_path("settings"),
            {"bookingDays": [1, 2, 3, 4, 5, 6, 7], "openingTime": "08:00", "closingTime": "18:00"},
        )
        self.assertEqual(status, 200, settings)
        date = (datetime.now().date() + timedelta(days=7)).isoformat()
        query = urlencode({"serviceId": service["id"], "date": date})
        status, result, _ = self.request("GET", self.public_path(f"slots?{query}"))
        self.assertEqual(status, 200, result)
        self.assertTrue(result["slots"], result)
        return result["slots"][0]

    def booking_data(self, service, slot, **overrides):
        data = {
            "name": "Morgan Example",
            "email": "morgan@example.test",
            "phone": "+27 00 000 0001",
            "serviceId": service["id"],
            "startAt": slot["startAt"],
            "message": "A booking made by a local test.",
            "consent": True,
        }
        data.update(overrides)
        return data

    def create_campaign(self, **overrides):
        data = {
            "name": "Workshop launch",
            "objective": "bookings",
            "offer": "Book a plant styling session.",
            "plannedBudget": 500,
            "channels": ["website", "facebook", "instagram"],
        }
        data.update(overrides)
        status, campaign, _ = self.write("POST", self.company_path("campaigns"), data)
        self.assertEqual(status, 201, campaign)
        return campaign

    def test_company_scope_applies_to_reads_updates_and_export(self):
        lead = self.create_lead()
        demo_path = self.company_path(f"leads/{lead['id']}", self.demo_company_id)
        status, error, _ = self.write("PATCH", demo_path, {"status": "won"})
        self.assertEqual(status, 404, error)

        status, export, _ = self.request(
            "GET", self.company_path("export", self.demo_company_id)
        )
        self.assertEqual(status, 200, export)
        self.assertNotIn(lead["id"], {item["id"] for item in export["leads"]})

        status, ours, _ = self.request("GET", self.company_path("leads"))
        self.assertEqual(status, 200, ours)
        self.assertEqual([item["status"] for item in ours["leads"]], ["new"])

    def test_public_site_does_not_expose_unpublished_draft(self):
        _, before, _ = self.request("GET", self.public_path())
        new_headline = "A draft waiting for approval"
        status, edited, _ = self.write(
            "PATCH", self.company_path("website"), {"headline": new_headline}
        )
        self.assertEqual(status, 200, edited)
        self.assertEqual(edited["draft"]["headline"], new_headline)

        _, public_draft, _ = self.request("GET", self.public_path())
        self.assertEqual(public_draft["website"], before["website"])
        status, published, _ = self.write(
            "POST", self.company_path("website/publish"), {}
        )
        self.assertEqual(status, 200, published)
        _, public_published, _ = self.request("GET", self.public_path())
        self.assertEqual(public_published["website"]["headline"], new_headline)

    def test_other_company_cannot_update_services_posts_campaigns_or_bookings(self):
        service = self.create_service()
        slot = self.future_slot(service)
        _, booking, _ = self.request(
            "POST", self.public_path("bookings"), self.booking_data(service, slot),
            {"Origin": self.origin},
        )
        _, post, _ = self.write(
            "POST", self.company_path("posts"),
            {"title": "Private preparation", "body": "Not yet published.", "channels": ["website"]},
        )
        campaign = self.create_campaign()
        attempts = [
            ("PATCH", f"services/{service['id']}", {"price": 1}),
            ("PATCH", f"posts/{post['id']}", {"body": "Unwanted edit"}),
            ("POST", f"posts/{post['id']}/publish", {}),
            ("POST", f"campaigns/{campaign['id']}/run", {}),
            ("PATCH", f"bookings/{booking['id']}", {"status": "cancelled"}),
        ]
        for method, resource, data in attempts:
            with self.subTest(resource=resource):
                status, error, _ = self.write(
                    method, self.company_path(resource, self.demo_company_id), data
                )
                self.assertEqual(status, 404, error)

    def test_public_response_excludes_private_records_and_commission(self):
        self.create_lead()
        status, public, _ = self.request("GET", self.public_path())
        self.assertEqual(status, 200, public)
        self.assertNotIn("commissionRate", public["company"])
        for private_resource in ["leads", "bookings", "deliveries", "activity", "draft"]:
            self.assertNotIn(private_resource, public)

    def test_repeated_post_publish_has_one_delivery_per_channel(self):
        status, post, _ = self.write(
            "POST", self.company_path("posts"),
            {"title": "A studio update", "body": "New workshop dates.", "channels": ["website", "linkedin"]},
        )
        self.assertEqual(status, 201, post)
        publish_path = self.company_path(f"posts/{post['id']}/publish")
        first_status, first, _ = self.write("POST", publish_path, {})
        second_status, second, _ = self.write("POST", publish_path, {})
        self.assertEqual(first_status, 200, first)
        self.assertEqual(second_status, 200, second)
        self.assertEqual(first["post"]["id"], second["post"]["id"])
        _, result, _ = self.request("GET", self.company_path("deliveries"))
        self.assertEqual(len(result["deliveries"]), 2)
        statuses = {item["channel"]: item["status"] for item in result["deliveries"]}
        self.assertEqual(statuses, {"website": "published_local", "linkedin": "demo_ready"})
        _, public, _ = self.request("GET", self.public_path())
        self.assertIn(post["id"], {item["id"] for item in public["posts"]})

    def test_social_only_post_does_not_appear_on_website(self):
        status, post, _ = self.write(
            "POST", self.company_path("posts"),
            {"title": "Social only", "body": "An Instagram preparation.", "channels": ["instagram"]},
        )
        self.assertEqual(status, 201, post)
        status, result, _ = self.write(
            "POST", self.company_path(f"posts/{post['id']}/publish"), {}
        )
        self.assertEqual(status, 200, result)
        self.assertEqual(result["deliveries"][0]["status"], "demo_ready")
        _, public, _ = self.request("GET", self.public_path())
        self.assertNotIn(post["id"], {item["id"] for item in public["posts"]})

    def test_post_draft_edits_keep_live_copy_until_explicit_republication(self):
        status, post, _ = self.write(
            "POST", self.company_path("posts"),
            {"title": "Published title", "body": "The approved live message.", "channels": ["website", "instagram"]},
        )
        self.assertEqual(status, 201, post)
        post_path = self.company_path(f"posts/{post['id']}")
        publish_path = post_path + "/publish"
        status, published, _ = self.write("POST", publish_path, {})
        self.assertEqual(status, 200, published)

        status, draft, _ = self.write(
            "PATCH", post_path, {"title": "Edited title", "body": "A draft still being reviewed."}
        )
        self.assertEqual(status, 200, draft)
        self.assertEqual(draft["status"], "draft")
        _, public, _ = self.request("GET", self.public_path())
        live = next(item for item in public["posts"] if item["id"] == post["id"])
        self.assertEqual(live["title"], "Published title")
        self.assertEqual(live["body"], "The approved live message.")
        _, export, _ = self.request("GET", self.company_path("export"))
        self.assertEqual(export["posts"][0]["body"], "A draft still being reviewed.")
        self.assertEqual(export["publishedPosts"][0]["body"], "The approved live message.")

        status, republished, _ = self.write("POST", publish_path, {})
        self.assertEqual(status, 200, republished)
        _, public, _ = self.request("GET", self.public_path())
        live = next(item for item in public["posts"] if item["id"] == post["id"])
        self.assertEqual(live["title"], "Edited title")
        self.assertEqual(live["body"], "A draft still being reviewed.")
        _, log, _ = self.request("GET", self.company_path("deliveries"))
        self.assertEqual(len(log["deliveries"]), 4)

        # Removing a destination while drafting does not unpublish the live copy.
        status, draft, _ = self.write("PATCH", post_path, {"channels": ["instagram"]})
        self.assertEqual(status, 200, draft)
        _, public, _ = self.request("GET", self.public_path())
        self.assertIn(post["id"], {item["id"] for item in public["posts"]})
        status, social_only, _ = self.write("POST", publish_path, {})
        self.assertEqual(status, 200, social_only)
        self.assertEqual(social_only["post"]["status"], "prepared")
        _, public, _ = self.request("GET", self.public_path())
        self.assertNotIn(post["id"], {item["id"] for item in public["posts"]})
        _, export, _ = self.request("GET", self.company_path("export"))
        self.assertEqual(export["publishedPosts"], [])

    def test_campaign_run_is_idempotent_and_does_not_invent_leads(self):
        campaign = self.create_campaign()
        path = self.company_path(f"campaigns/{campaign['id']}/run")
        status, first, _ = self.write("POST", path, {})
        self.assertEqual(status, 200, first)
        status, second, _ = self.write("POST", path, {})
        self.assertEqual(status, 200, second)
        self.assertEqual(first["post"]["id"], second["post"]["id"])
        self.assertEqual(second["campaign"]["status"], "prepared")
        _, posts, _ = self.request("GET", self.company_path("posts"))
        _, deliveries, _ = self.request("GET", self.company_path("deliveries"))
        _, leads, _ = self.request("GET", self.company_path("leads"))
        self.assertEqual(len(posts["posts"]), 1)
        self.assertEqual(len(deliveries["deliveries"]), 3)
        self.assertEqual(leads["leads"], [])
        self.assertEqual(
            {item["channel"]: item["status"] for item in deliveries["deliveries"]},
            {"website": "published_local", "facebook": "demo_ready", "instagram": "demo_ready"},
        )

    def test_campaign_attribution_is_scoped_to_the_public_company(self):
        campaign = self.create_campaign()
        query = urlencode({"campaign": campaign["sourceCode"]})
        status, ours, _ = self.request("GET", self.public_path() + f"?{query}")
        self.assertEqual(status, 200, ours)
        self.assertEqual(ours["campaign"]["id"], campaign["id"])

        _, session, _ = self.request("GET", "/api/session")
        demo_company = next(item for item in session["companies"] if item["id"] == self.demo_company_id)
        status, other, _ = self.request("GET", self.public_path(slug=demo_company["slug"]) + f"?{query}")
        self.assertEqual(status, 200, other)
        self.assertFalse(other.get("campaign"))

        status, enquiry, _ = self.request(
            "POST", self.public_path("enquiries"),
            {"name": "Campaign Visitor", "email": "visitor@example.test", "message": "I saw the campaign.", "consent": True, "campaignCode": campaign["sourceCode"]},
            {"Origin": self.origin},
        )
        self.assertEqual(status, 201, enquiry)
        _, leads, _ = self.request("GET", self.company_path("leads"))
        self.assertEqual(len(leads["leads"]), 1)
        self.assertIn("campaign", leads["leads"][0]["source"].lower())

    def test_booking_creation_creates_a_lead_and_hides_its_slot(self):
        service = self.create_service()
        slot = self.future_slot(service)
        status, booking, _ = self.request(
            "POST", self.public_path("bookings"), self.booking_data(service, slot),
            {"Origin": self.origin},
        )
        self.assertEqual(status, 201, booking)
        self.assertEqual(booking["status"], "requested")
        _, leads, _ = self.request("GET", self.company_path("leads"))
        self.assertEqual(len(leads["leads"]), 1)
        self.assertEqual(booking["leadId"], leads["leads"][0]["id"])
        query = urlencode({"serviceId": service["id"], "date": slot["startAt"][:10]})
        _, available, _ = self.request("GET", self.public_path(f"slots?{query}"))
        self.assertNotIn(slot["startAt"], {item["startAt"] for item in available["slots"]})

    def test_concurrent_requests_cannot_reserve_the_same_time(self):
        service = self.create_service()
        slot = self.future_slot(service)
        data = self.booking_data(service, slot)
        start_together = threading.Barrier(2)

        def reserve():
            start_together.wait(timeout=5)
            return self.request("POST", self.public_path("bookings"), data, {"Origin": self.origin})

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: reserve(), range(2)))
        self.assertEqual(sorted(result[0] for result in results), [201, 409], results)
        _, bookings, _ = self.request("GET", self.company_path("bookings"))
        _, leads, _ = self.request("GET", self.company_path("leads"))
        self.assertEqual(len(bookings["bookings"]), 1)
        self.assertEqual(len(leads["leads"]), 1)

    def test_adjacent_appointments_are_allowed(self):
        service = self.create_service()
        first_slot = self.future_slot(service)
        status, first_booking, _ = self.request(
            "POST", self.public_path("bookings"), self.booking_data(service, first_slot),
            {"Origin": self.origin},
        )
        self.assertEqual(status, 201, first_booking)
        second_slot = {"startAt": first_booking["endAt"]}
        status, next_booking, _ = self.request(
            "POST", self.public_path("bookings"), self.booking_data(service, second_slot),
            {"Origin": self.origin},
        )
        self.assertEqual(status, 201, next_booking)
        self.assertEqual(next_booking["startAt"], first_booking["endAt"])

    def test_reservations_conflict_across_services_and_status_changes(self):
        first_service = self.create_service()
        second_service = self.create_service(name="Long appointment", durationMinutes=90)
        slot = self.future_slot(first_service)
        _, first_booking, _ = self.request(
            "POST", self.public_path("bookings"), self.booking_data(first_service, slot),
            {"Origin": self.origin},
        )
        overlapping_slot = dict(slot)
        overlapping_slot["startAt"] = (datetime.fromisoformat(slot["startAt"]) + timedelta(minutes=30)).isoformat()
        status, error, _ = self.request(
            "POST", self.public_path("bookings"), self.booking_data(second_service, overlapping_slot),
            {"Origin": self.origin},
        )
        self.assertEqual(status, 409, error)

        status, cancelled, _ = self.write(
            "PATCH", self.company_path(f"bookings/{first_booking['id']}"), {"status": "cancelled"}
        )
        self.assertEqual(status, 200, cancelled)
        status, replacement, _ = self.request(
            "POST", self.public_path("bookings"), self.booking_data(second_service, slot),
            {"Origin": self.origin},
        )
        self.assertEqual(status, 201, replacement)
        status, error, _ = self.write(
            "PATCH", self.company_path(f"bookings/{first_booking['id']}"), {"status": "confirmed"}
        )
        self.assertEqual(status, 409, error)

    def test_booking_rejects_foreign_service_outside_hours_and_no_consent(self):
        service = self.create_service()
        slot = self.future_slot(service)
        status, error, _ = self.request(
            "POST", self.public_path("bookings"), self.booking_data(service, slot, consent=False),
            {"Origin": self.origin},
        )
        self.assertEqual(status, 400, error)
        outside_hours = dict(slot)
        outside_hours["startAt"] = datetime.fromisoformat(slot["startAt"]).replace(hour=2).isoformat()
        status, error, _ = self.request(
            "POST", self.public_path("bookings"), self.booking_data(service, outside_hours),
            {"Origin": self.origin},
        )
        self.assertEqual(status, 400, error)

        _, session, _ = self.request("GET", "/api/session")
        demo_slug = next(item["slug"] for item in session["companies"] if item["id"] == self.demo_company_id)
        status, error, _ = self.request(
            "POST", self.public_path("bookings", demo_slug), self.booking_data(service, slot),
            {"Origin": self.origin},
        )
        self.assertEqual(status, 404, error)

    def test_inactive_services_are_hidden_and_cannot_be_booked(self):
        service = self.create_service()
        slot = self.future_slot(service)
        status, updated, _ = self.write(
            "PATCH", self.company_path(f"services/{service['id']}"), {"active": False}
        )
        self.assertEqual(status, 200, updated)
        _, website, _ = self.request("GET", self.public_path())
        self.assertNotIn(service["id"], {item["id"] for item in website["services"]})
        status, error, _ = self.request(
            "POST", self.public_path("bookings"), self.booking_data(service, slot),
            {"Origin": self.origin},
        )
        self.assertIn(status, [400, 404], error)

    def test_conversion_metrics_and_scoped_export_use_saved_values(self):
        first = self.create_lead(name="Won visitor", value=1250, commissionRate=8)
        second = self.create_lead(name="Qualified visitor", value=750, commissionRate=20)
        status, won, _ = self.write(
            "PATCH", self.company_path(f"leads/{first['id']}"), {"status": "won", "notes": "Client confirmed conversion."}
        )
        self.assertEqual(status, 200, won)
        self.write("PATCH", self.company_path(f"leads/{second['id']}"), {"status": "qualified"})
        _, overview, _ = self.request("GET", self.company_path("overview"))
        self.assertEqual(overview["metrics"]["convertedValue"], 1250)
        self.assertEqual(overview["metrics"]["pipelineValue"], 750)
        self.assertEqual(overview["metrics"]["estimatedCommission"], 100)

        status, export, headers = self.request("GET", self.company_path("export"))
        self.assertEqual(status, 200, export)
        self.assertIn("attachment", headers.get("Content-Disposition", ""))
        self.assertEqual(export["company"]["id"], self.company_id)
        self.assertEqual({item["id"] for item in export["leads"]}, {first["id"], second["id"]})
        self.assertNotIn("csrfToken", json.dumps(export))

    def test_lead_search_and_status_filter_apply_together(self):
        first = self.create_lead(name="Avery Visitor")
        self.create_lead(name="Avery Other", status="qualified")
        self.create_lead(name="Sam Example")
        query = urlencode({"search": "Avery", "status": "new"})
        status, result, _ = self.request("GET", self.company_path(f"leads?{query}"))
        self.assertEqual(status, 200, result)
        self.assertEqual([item["id"] for item in result["leads"]], [first["id"]])

    def test_cross_origin_admin_and_public_writes_are_rejected(self):
        status, error, _ = self.write(
            "PATCH", self.company_path("settings"), {"name": "Unwanted change"},
            {"Origin": "https://unrelated.example"},
        )
        self.assertEqual(status, 403, error)
        status, error, _ = self.request(
            "POST", self.public_path("enquiries"),
            {"name": "Visitor", "email": "visitor@example.test", "message": "Cross-origin attempt", "consent": True},
            {"Origin": "https://unrelated.example"},
        )
        self.assertEqual(status, 403, error)
        _, leads, _ = self.request("GET", self.company_path("leads"))
        self.assertEqual(leads["leads"], [])

    def test_admin_writes_require_the_session_csrf_token(self):
        for token in [None, "incorrect-token"]:
            headers = {"Origin": self.origin}
            if token:
                headers["X-CSRF-Token"] = token
            status, error, _ = self.request(
                "PATCH", self.company_path("settings"), {"name": "Unauthorized change"}, headers
            )
            self.assertEqual(status, 403, error)
        _, settings, _ = self.request("GET", self.company_path("settings"))
        self.assertEqual(settings["name"], "QA Studio")

    def test_unexpected_host_and_oversized_request_are_rejected(self):
        status, error, _ = self.request("GET", "/api/session", headers={"Host": "unrelated.example"})
        self.assertIn(status, [400, 403], error)
        # Reject the declared size before reading the body. Sending a megabyte
        # after early rejection can reset a Windows socket before its 413 arrives.
        status, error, _ = self.request(
            "POST", self.public_path("enquiries"),
            headers={"Origin": self.origin, "Content-Type": "application/json", "Content-Length": "1000000"},
        )
        self.assertEqual(status, 413, error)

    def test_public_submission_limit_stops_inserts_and_provides_retry_guidance(self):
        data = {
            "name": "Local form visitor",
            "email": "limited@example.test",
            "message": "An enquiry used to exercise the submission limit.",
            "consent": True,
        }
        for _ in range(20):
            status, result, _ = self.request(
                "POST", self.public_path("enquiries"), data, {"Origin": self.origin}
            )
            self.assertEqual(status, 201, result)
        status, error, headers = self.request(
            "POST", self.public_path("enquiries"), data, {"Origin": self.origin}
        )
        self.assertEqual(status, 429, error)
        self.assertEqual(headers.get("Retry-After"), "60")
        _, leads, _ = self.request("GET", self.company_path("leads"))
        self.assertEqual(len(leads["leads"]), 20)

    def test_invalid_money_and_unknown_status_do_not_change_a_lead(self):
        lead = self.create_lead()
        path = self.company_path(f"leads/{lead['id']}")
        for update in [{"value": -1}, {"value": 10 ** 1000}, {"commissionRate": 101}, {"status": "paid"}]:
            status, error, _ = self.write("PATCH", path, update)
            self.assertEqual(status, 400, error)
        _, result, _ = self.request("GET", self.company_path("leads"))
        saved = result["leads"][0]
        self.assertEqual(saved["value"], lead["value"])
        self.assertEqual(saved["commissionRate"], lead["commissionRate"])
        self.assertEqual(saved["status"], "new")


class PersistenceTests(unittest.TestCase):
    def test_restart_keeps_records_and_does_not_seed_a_second_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "persistent.sqlite3"
            first_application = create_application(path)
            companies = first_application.companies()
            company_id = companies[0]["id"]
            before = first_application.list_leads(company_id)["leads"]
            lead = first_application.create_lead(
                company_id,
                {"name": "Persistence Visitor", "email": "persistent@example.test", "message": "Keep this enquiry."},
            )

            restarted_application = create_application(path)
            self.assertEqual(restarted_application.companies(), companies)
            after = restarted_application.list_leads(company_id)["leads"]
            self.assertEqual(len(after), len(before) + 1)
            self.assertIn(lead["id"], {item["id"] for item in after})


if __name__ == "__main__":
    unittest.main()
