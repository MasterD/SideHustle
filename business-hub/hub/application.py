"""Business rules for the local demo. All resource lookups include company ID."""

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import re
import sqlite3
import uuid

from .storage import Database
from .validation import (
    ApiError, business_timezone, channels_field, choice_field, contact_fields,
    number_field, parse_datetime, parse_time, text_field,
)


LEAD_STATUSES = ("new", "contacted", "qualified", "won", "lost")
BOOKING_STATUSES = ("requested", "confirmed", "completed", "cancelled")
SITE_FIELDS = ("headline", "subheadline", "about", "ctaLabel", "announcement")


def new_id():
    return uuid.uuid4().hex


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def query_value(query, key, default=""):
    value = query.get(key, default)
    return value[0] if isinstance(value, list) and value else value


def company_from_row(row):
    return {"id": row["id"], "slug": row["slug"], "name": row["name"],
            **json.loads(row["settings_json"])}


def service_from_row(row):
    return {"id": row["id"], "name": row["name"], "description": row["description"],
            "durationMinutes": row["duration_minutes"], "price": row["price"],
            "active": bool(row["active"]), "createdAt": row["created_at"]}


def lead_from_row(row):
    return {"id": row["id"], "name": row["name"], "email": row["email"],
            "phone": row["phone"], "message": row["message"], "source": row["source"],
            "status": row["status"], "value": row["value"],
            "commissionRate": row["commission_rate"], "notes": row["notes"],
            "createdAt": row["created_at"], "updatedAt": row["updated_at"]}


def booking_from_row(row):
    return {"id": row["id"], "name": row["name"], "email": row["email"],
            "phone": row["phone"], "serviceId": row["service_id"],
            "serviceName": row["service_name"], "startAt": row["start_at"],
            "endAt": row["end_at"], "status": row["status"],
            "message": row["message"], "leadId": row["lead_id"],
            "createdAt": row["created_at"]}


def post_from_row(row):
    return {"id": row["id"], "title": row["title"], "body": row["body"],
            "channels": json.loads(row["channels_json"]), "status": row["status"],
            "createdAt": row["created_at"], "updatedAt": row["updated_at"]}


def campaign_from_row(row):
    return {"id": row["id"], "name": row["name"], "objective": row["objective"],
            "offer": row["offer"], "plannedBudget": row["planned_budget"],
            "channels": json.loads(row["channels_json"]), "status": row["status"],
            "sourceCode": row["source_code"], "postId": row["post_id"],
            "createdAt": row["created_at"]}


def delivery_from_row(row):
    return {"id": row["id"], "title": row["title"], "channel": row["channel"],
            "status": row["status"], "createdAt": row["created_at"],
            "postId": row["post_id"]}


def activity_from_row(row):
    return {"id": row["id"], "message": row["message"], "createdAt": row["created_at"]}


class Application:
    def __init__(self, database_path, seed=True):
        self.database = Database(database_path)
        self.backfill_published_posts()
        if seed:
            self.seed_demo()

    def backfill_published_posts(self):
        """Preserve live posts when opening a database from the first version.

        Only already-published content is eligible. An unpublished edited
        draft cannot safely be reconstructed from its delivery history.
        """
        with self.database.connection(write=True) as connection:
            rows = connection.execute("SELECT * FROM posts WHERE status = 'published'").fetchall()
            for row in rows:
                post = post_from_row(row)
                if "website" in post["channels"]:
                    connection.execute("""INSERT OR IGNORE INTO published_posts
                        (post_id, company_id, snapshot_json, published_at) VALUES (?, ?, ?, ?)""",
                        (post["id"], row["company_id"], encode(post), post["updatedAt"]))

    def company_row(self, connection, company_id):
        row = connection.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
        if row is None:
            raise ApiError(404, "Company was not found.")
        return row

    def company_by_slug(self, connection, slug):
        row = connection.execute("SELECT * FROM companies WHERE slug = ?", (slug,)).fetchone()
        if row is None:
            raise ApiError(404, "Website was not found.")
        return row

    def scoped_row(self, connection, table, company_id, resource_id):
        # Table names come only from our route handlers, never from user input.
        row = connection.execute(
            f"SELECT * FROM {table} WHERE company_id = ? AND id = ?",
            (company_id, resource_id),
        ).fetchone()
        if row is None:
            raise ApiError(404, "This record was not found for the selected company.")
        return row

    def record_activity(self, connection, company_id, message):
        connection.execute("INSERT INTO activity VALUES (?, ?, ?, ?)",
                           (new_id(), company_id, message, timestamp()))

    def companies(self):
        with self.database.connection() as connection:
            return [{"id": row["id"], "name": row["name"], "slug": row["slug"]}
                    for row in connection.execute("SELECT * FROM companies ORDER BY created_at, rowid")]

    def create_company(self, data):
        with self.database.connection(write=True) as connection:
            return self._create_company(connection, data)

    def _create_company(self, connection, data):
        name = text_field(data, "name", 120, required=True)
        slug = text_field(data, "slug", 60, required=True).lower()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ApiError(400, "slug may contain lowercase letters, numbers, and single hyphens.")
        settings = {
            "tagline": "A little more possibility, every day.",
            "description": "Tell your customers what makes your business special.",
            "email": "hello@example.test", "phone": "+27 10 000 0000",
            "address": "Johannesburg, South Africa", "timezone": "Africa/Johannesburg",
            "currency": "ZAR", "accentColor": "#315fe7", "commissionRate": 0,
            "bookingDays": [1, 2, 3, 4, 5], "openingTime": "09:00", "closingTime": "17:00",
        }
        website = {
            "headline": f"Welcome to {name}",
            "subheadline": "Thoughtful services, made personal.",
            "about": settings["description"], "ctaLabel": "Book a visit", "announcement": "",
        }
        company_id = new_id()
        try:
            connection.execute("INSERT INTO companies VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (company_id, slug, name, encode(settings), encode(website), encode(website), timestamp()))
        except sqlite3.IntegrityError:
            raise ApiError(409, "That website address is already in use. Choose another slug.")
        self._create_service(connection, company_id, {
            "name": "Discovery consultation", "description": "Let's discuss what you need.",
            "durationMinutes": 60, "price": 350, "active": True,
        })
        self.record_activity(connection, company_id, f"Created {name} and its local website.")
        return company_from_row(self.company_row(connection, company_id))

    def get_settings(self, company_id):
        with self.database.connection() as connection:
            return company_from_row(self.company_row(connection, company_id))

    def update_settings(self, company_id, data):
        with self.database.connection(write=True) as connection:
            row = self.company_row(connection, company_id)
            current = company_from_row(row)
            if "slug" in data and data["slug"] != row["slug"]:
                raise ApiError(400, "The website slug is fixed when a company is created.")
            settings = json.loads(row["settings_json"])
            name = text_field(data, "name", 120, required=True, default=current["name"])
            lengths = {"tagline": 200, "description": 5000, "email": 254,
                       "phone": 40, "address": 300, "timezone": 80, "currency": 3,
                       "accentColor": 7, "openingTime": 5, "closingTime": 5}
            for field, maximum in lengths.items():
                if field in data:
                    settings[field] = text_field(data, field, maximum)
            business_timezone(settings["timezone"])
            if not re.fullmatch(r"[A-Z]{3}", settings["currency"]):
                raise ApiError(400, "currency must be a three-letter uppercase currency code.")
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", settings["accentColor"]):
                raise ApiError(400, "accentColor must be a six-digit hex color, such as #315fe7.")
            if settings["email"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", settings["email"]):
                raise ApiError(400, "Please provide a valid company email address.")
            opening = parse_time(settings["openingTime"], "openingTime")
            closing = parse_time(settings["closingTime"], "closingTime")
            if opening >= closing:
                raise ApiError(400, "Closing time must be later than opening time on the same day.")
            if "bookingDays" in data:
                days = data["bookingDays"]
                if not isinstance(days, list) or any(type(day) is not int or day not in range(1, 8) for day in days):
                    raise ApiError(400, "bookingDays must be a list of weekdays from 1 (Monday) to 7 (Sunday).")
                settings["bookingDays"] = sorted(set(days))
            if "commissionRate" in data:
                settings["commissionRate"] = number_field(data, "commissionRate", maximum=100)
            connection.execute("UPDATE companies SET name = ?, settings_json = ? WHERE id = ?",
                               (name, encode(settings), company_id))
            self.record_activity(connection, company_id, "Updated business settings.")
            return company_from_row(self.company_row(connection, company_id))

    def list_services(self, company_id):
        with self.database.connection() as connection:
            self.company_row(connection, company_id)
            return {"services": [service_from_row(row) for row in connection.execute(
                "SELECT * FROM services WHERE company_id = ? ORDER BY created_at, rowid", (company_id,))]}

    def create_service(self, company_id, data):
        with self.database.connection(write=True) as connection:
            self.company_row(connection, company_id)
            service = self._create_service(connection, company_id, data)
            self.record_activity(connection, company_id, f"Added service: {service['name']}.")
            return service

    def _service_fields(self, data, current=None):
        current = current or {}
        fields = {"name": text_field(data, "name", 150, True, current.get("name", "")),
                  "description": text_field(data, "description", 2000, default=current.get("description", "")),
                  "price": round(number_field(data, "price", current.get("price", 0)), 2)}
        duration = data.get("durationMinutes", current.get("durationMinutes", 60))
        if type(duration) is not int or not 15 <= duration <= 480 or duration % 15:
            raise ApiError(400, "durationMinutes must be a multiple of 15, between 15 and 480.")
        active = data.get("active", current.get("active", True))
        if type(active) is not bool:
            raise ApiError(400, "active must be true or false.")
        return {**fields, "durationMinutes": duration, "active": active}

    def _create_service(self, connection, company_id, data):
        fields = self._service_fields(data)
        service_id = new_id()
        connection.execute("INSERT INTO services VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (service_id, company_id, fields["name"], fields["description"],
                            fields["durationMinutes"], fields["price"], int(fields["active"]), timestamp()))
        return service_from_row(self.scoped_row(connection, "services", company_id, service_id))

    def update_service(self, company_id, service_id, data):
        with self.database.connection(write=True) as connection:
            row = self.scoped_row(connection, "services", company_id, service_id)
            fields = self._service_fields(data, service_from_row(row))
            connection.execute("""UPDATE services SET name = ?, description = ?, duration_minutes = ?,
                price = ?, active = ? WHERE company_id = ? AND id = ?""",
                (fields["name"], fields["description"], fields["durationMinutes"], fields["price"],
                 int(fields["active"]), company_id, service_id))
            self.record_activity(connection, company_id, f"Updated service: {fields['name']}.")
            return service_from_row(self.scoped_row(connection, "services", company_id, service_id))

    def list_leads(self, company_id, query=None):
        query = query or {}
        search = str(query_value(query, "search")).strip().lower()
        status = query_value(query, "status")
        if status and status not in LEAD_STATUSES:
            raise ApiError(400, "Choose a valid lead status.")
        with self.database.connection() as connection:
            self.company_row(connection, company_id)
            rows = connection.execute("SELECT * FROM leads WHERE company_id = ? ORDER BY created_at DESC, rowid DESC", (company_id,))
            leads = [lead_from_row(row) for row in rows]
            if status:
                leads = [lead for lead in leads if lead["status"] == status]
            if search:
                leads = [lead for lead in leads if search in " ".join(
                    str(lead[field]) for field in ("name", "email", "phone", "message", "source")).lower()]
            return {"leads": leads}

    def _create_lead(self, connection, company_id, data, created_at=None):
        company = company_from_row(self.company_row(connection, company_id))
        name, email, phone = contact_fields(data)
        lead_id = new_id()
        created = created_at or timestamp()
        connection.execute("INSERT INTO leads VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (lead_id, company_id, name, email, phone,
                            text_field(data, "message", 5000), text_field(data, "source", 180, default="manual"),
                            choice_field(data, "status", LEAD_STATUSES, "new"),
                            round(number_field(data, "value"), 2),
                            number_field(data, "commissionRate", company["commissionRate"], 100),
                            text_field(data, "notes", 10000), created, created))
        return lead_from_row(self.scoped_row(connection, "leads", company_id, lead_id))

    def create_lead(self, company_id, data):
        with self.database.connection(write=True) as connection:
            lead = self._create_lead(connection, company_id, data)
            self.record_activity(connection, company_id, f"Added lead: {lead['name']}.")
            return lead

    def update_lead(self, company_id, lead_id, data):
        with self.database.connection(write=True) as connection:
            current = lead_from_row(self.scoped_row(connection, "leads", company_id, lead_id))
            status = choice_field(data, "status", LEAD_STATUSES, current["status"])
            value = round(number_field(data, "value", current["value"]), 2)
            commission = number_field(data, "commissionRate", current["commissionRate"], 100)
            notes = text_field(data, "notes", 10000, default=current["notes"])
            connection.execute("""UPDATE leads SET status = ?, value = ?, commission_rate = ?,
                notes = ?, updated_at = ? WHERE company_id = ? AND id = ?""",
                (status, value, commission, notes, timestamp(), company_id, lead_id))
            self.record_activity(connection, company_id, f"Updated {current['name']}'s lead to {status}.")
            return lead_from_row(self.scoped_row(connection, "leads", company_id, lead_id))

    def list_bookings(self, company_id):
        with self.database.connection() as connection:
            self.company_row(connection, company_id)
            return {"bookings": [booking_from_row(row) for row in connection.execute(
                "SELECT * FROM bookings WHERE company_id = ? ORDER BY start_at DESC, rowid DESC", (company_id,))]}

    def _has_booking_conflict(self, connection, company_id, start, end, exclude_id=None):
        for row in connection.execute("""SELECT id, start_at, end_at FROM bookings
            WHERE company_id = ? AND status IN ('requested', 'confirmed')""", (company_id,)):
            if row["id"] != exclude_id and start < parse_datetime(row["end_at"]) and end > parse_datetime(row["start_at"]):
                return True
        return False

    def _booking_window(self, company, service, start):
        local = start.astimezone(business_timezone(company["timezone"]))
        end = local + timedelta(minutes=service["durationMinutes"])
        opening = datetime.combine(local.date(), parse_time(company["openingTime"], "openingTime"), local.tzinfo)
        closing = datetime.combine(local.date(), parse_time(company["closingTime"], "closingTime"), local.tzinfo)
        if local <= datetime.now(local.tzinfo):
            raise ApiError(400, "Choose a future appointment time.")
        if local.date() > datetime.now(local.tzinfo).date() + timedelta(days=365):
            raise ApiError(400, "Bookings are available up to one year ahead.")
        if local.isoweekday() not in company["bookingDays"] or local < opening or end > closing:
            raise ApiError(400, "That time is outside the business's booking hours.")
        if local.second or local.microsecond or (local - opening).total_seconds() % (30 * 60):
            raise ApiError(400, "Choose one of the available appointment slots.")
        return local, end

    def list_slots(self, slug, query):
        service_id = query_value(query, "serviceId")
        date_text = query_value(query, "date")
        try:
            if not isinstance(date_text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text):
                raise ValueError()
            selected_date = date.fromisoformat(date_text)
        except ValueError:
            raise ApiError(400, "date must be a valid date in YYYY-MM-DD format.")
        with self.database.connection() as connection:
            company = company_from_row(self.company_by_slug(connection, slug))
            service = service_from_row(self.scoped_row(connection, "services", company["id"], service_id))
            if not service["active"]:
                raise ApiError(400, "This service is not currently available.")
            tz = business_timezone(company["timezone"])
            now = datetime.now(tz)
            if selected_date < now.date() or selected_date > now.date() + timedelta(days=365):
                return {"slots": []}
            if selected_date.isoweekday() not in company["bookingDays"]:
                return {"slots": []}
            start = datetime.combine(selected_date, parse_time(company["openingTime"], "openingTime"), tz)
            closing = datetime.combine(selected_date, parse_time(company["closingTime"], "closingTime"), tz)
            slots = []
            while start + timedelta(minutes=service["durationMinutes"]) <= closing:
                end = start + timedelta(minutes=service["durationMinutes"])
                if start > now and not self._has_booking_conflict(connection, company["id"], start, end):
                    slots.append({"startAt": start.isoformat(timespec="seconds"),
                                  "endAt": end.isoformat(timespec="seconds"), "label": start.strftime("%H:%M")})
                start += timedelta(minutes=30)
            return {"slots": slots}

    def _campaign_source(self, connection, company_id, data):
        code = text_field(data, "campaignCode", 100)
        if not code:
            return "website"
        campaign = connection.execute("SELECT * FROM campaigns WHERE company_id = ? AND source_code = ?",
                                      (company_id, code)).fetchone()
        if campaign is None:
            raise ApiError(400, "The campaign link is not valid for this business.")
        return f"campaign:{code}"

    def create_booking(self, slug, data):
        if data.get("consent") is not True:
            raise ApiError(400, "Please consent to processing this booking inquiry.")
        name, email, phone = contact_fields(data)
        message = text_field(data, "message", 5000)
        start = parse_datetime(data.get("startAt"))
        service_id = text_field(data, "serviceId", 100, required=True)
        with self.database.connection(write=True) as connection:
            company = company_from_row(self.company_by_slug(connection, slug))
            service = service_from_row(self.scoped_row(connection, "services", company["id"], service_id))
            if not service["active"]:
                raise ApiError(400, "This service is not currently available.")
            start, end = self._booking_window(company, service, start)
            if self._has_booking_conflict(connection, company["id"], start, end):
                raise ApiError(409, "That appointment was just taken. Please choose another time.")
            lead = self._create_lead(connection, company["id"], {
                "name": name, "email": email, "phone": phone, "message": message,
                "source": self._campaign_source(connection, company["id"], data),
                "value": service["price"], "notes": "Consent given to process this booking inquiry.",
            })
            booking_id = new_id()
            connection.execute("INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (booking_id, company["id"], name, email, phone, service_id, service["name"],
                                start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds"),
                                "requested", message, lead["id"], timestamp()))
            self.record_activity(connection, company["id"], f"New booking request from {name} for {service['name']}.")
            return booking_from_row(self.scoped_row(connection, "bookings", company["id"], booking_id))

    def create_enquiry(self, slug, data):
        if data.get("consent") is not True:
            raise ApiError(400, "Please consent to processing this inquiry.")
        name, email, phone = contact_fields(data)
        message = text_field(data, "message", 5000, required=True)
        with self.database.connection(write=True) as connection:
            company = company_from_row(self.company_by_slug(connection, slug))
            lead = self._create_lead(connection, company["id"], {
                "name": name, "email": email, "phone": phone, "message": message,
                "source": self._campaign_source(connection, company["id"], data),
                "notes": "Consent given to process this inquiry.",
            })
            self.record_activity(connection, company["id"], f"New website inquiry from {name}.")
            return {"id": lead["id"], "message": "Your inquiry has been received. The business will contact you."}

    def update_booking(self, company_id, booking_id, data):
        status = choice_field(data, "status", BOOKING_STATUSES)
        with self.database.connection(write=True) as connection:
            row = self.scoped_row(connection, "bookings", company_id, booking_id)
            if status in ("requested", "confirmed") and self._has_booking_conflict(
                connection, company_id, parse_datetime(row["start_at"]), parse_datetime(row["end_at"]), booking_id
            ):
                raise ApiError(409, "This appointment overlaps another active booking.")
            connection.execute("UPDATE bookings SET status = ? WHERE company_id = ? AND id = ?",
                               (status, company_id, booking_id))
            self.record_activity(connection, company_id, f"Marked {row['name']}'s booking {status}.")
            return booking_from_row(self.scoped_row(connection, "bookings", company_id, booking_id))

    def list_posts(self, company_id):
        with self.database.connection() as connection:
            self.company_row(connection, company_id)
            return {"posts": [post_from_row(row) for row in connection.execute(
                "SELECT * FROM posts WHERE company_id = ? ORDER BY created_at DESC, rowid DESC", (company_id,))]}

    def _create_post(self, connection, company_id, data):
        title = text_field(data, "title", 200, required=True)
        body = text_field(data, "body", 10000, required=True)
        channels = channels_field(data)
        if data.get("status", "draft") != "draft":
            raise ApiError(400, "New posts start as drafts. Use Prepare & publish to publish them.")
        post_id = new_id()
        now = timestamp()
        connection.execute("INSERT INTO posts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (post_id, company_id, title, body, encode(channels), "draft", now, now))
        return post_from_row(self.scoped_row(connection, "posts", company_id, post_id))

    def create_post(self, company_id, data):
        with self.database.connection(write=True) as connection:
            self.company_row(connection, company_id)
            post = self._create_post(connection, company_id, data)
            self.record_activity(connection, company_id, f"Saved post draft: {post['title']}.")
            return post

    def update_post(self, company_id, post_id, data):
        with self.database.connection(write=True) as connection:
            current = post_from_row(self.scoped_row(connection, "posts", company_id, post_id))
            title = text_field(data, "title", 200, True, current["title"])
            body = text_field(data, "body", 10000, True, current["body"])
            channels = channels_field(data, current["channels"])
            changed = (title, body, channels) != (current["title"], current["body"], current["channels"])
            status = "draft" if changed else current["status"]
            connection.execute("""UPDATE posts SET title = ?, body = ?, channels_json = ?, status = ?,
                updated_at = ? WHERE company_id = ? AND id = ?""",
                (title, body, encode(channels), status, timestamp(), company_id, post_id))
            self.record_activity(connection, company_id, f"Updated post draft: {title}.")
            return post_from_row(self.scoped_row(connection, "posts", company_id, post_id))

    def _publish_post(self, connection, company_id, post_id):
        post = post_from_row(self.scoped_row(connection, "posts", company_id, post_id))
        content_hash = hashlib.sha256(encode({"title": post["title"], "body": post["body"]}).encode()).hexdigest()
        created = 0
        for channel in post["channels"]:
            status = "published_local" if channel == "website" else "demo_ready"
            result = connection.execute("""INSERT OR IGNORE INTO deliveries
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (new_id(), company_id, post_id, post["title"], channel, status, content_hash, timestamp()))
            created += result.rowcount
        # Prepared social content never implies publication to an external account.
        status = "published" if "website" in post["channels"] else "prepared"
        connection.execute("UPDATE posts SET status = ?, updated_at = ? WHERE company_id = ? AND id = ?",
                           (status, timestamp(), company_id, post_id))
        published_post = post_from_row(self.scoped_row(connection, "posts", company_id, post_id))
        if "website" in post["channels"]:
            # A separate immutable copy lets the dashboard edit a draft while
            # visitors keep seeing the previous published text. Only this
            # explicit publish action replaces the live website version.
            connection.execute("""INSERT INTO published_posts
                (post_id, company_id, snapshot_json, published_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(post_id) DO UPDATE SET snapshot_json = excluded.snapshot_json,
                    published_at = excluded.published_at""",
                (post_id, company_id, encode(published_post), timestamp()))
        else:
            # Removing the website channel in a draft has no public effect.
            # Publishing that channel selection explicitly removes the post.
            connection.execute("DELETE FROM published_posts WHERE company_id = ? AND post_id = ?",
                               (company_id, post_id))
        if created:
            self.record_activity(connection, company_id, f"Prepared {post['title']}; local website published where selected. Social channels remain demo preparations.")
        deliveries = [delivery_from_row(row) for row in connection.execute(
            "SELECT * FROM deliveries WHERE company_id = ? AND post_id = ? AND content_hash = ? ORDER BY rowid",
            (company_id, post_id, content_hash)) if row["channel"] in post["channels"]]
        return {"post": published_post, "deliveries": deliveries}

    def publish_post(self, company_id, post_id):
        with self.database.connection(write=True) as connection:
            return self._publish_post(connection, company_id, post_id)

    def list_campaigns(self, company_id):
        with self.database.connection() as connection:
            self.company_row(connection, company_id)
            return {"campaigns": [campaign_from_row(row) for row in connection.execute(
                "SELECT * FROM campaigns WHERE company_id = ? ORDER BY created_at DESC, rowid DESC", (company_id,))]}

    def _create_campaign(self, connection, company_id, data):
        campaign_id = new_id()
        connection.execute("INSERT INTO campaigns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (campaign_id, company_id, text_field(data, "name", 200, required=True),
                            choice_field(data, "objective", ("leads", "bookings", "awareness"), "leads"),
                            text_field(data, "offer", 5000, required=True),
                            round(number_field(data, "plannedBudget"), 2), encode(channels_field(data)),
                            "draft", f"offer-{uuid.uuid4().hex[:12]}", None, timestamp()))
        return campaign_from_row(self.scoped_row(connection, "campaigns", company_id, campaign_id))

    def create_campaign(self, company_id, data):
        with self.database.connection(write=True) as connection:
            self.company_row(connection, company_id)
            campaign = self._create_campaign(connection, company_id, data)
            self.record_activity(connection, company_id, f"Saved campaign plan: {campaign['name']}.")
            return campaign

    def run_campaign(self, company_id, campaign_id):
        with self.database.connection(write=True) as connection:
            campaign = campaign_from_row(self.scoped_row(connection, "campaigns", company_id, campaign_id))
            post_id = campaign["postId"]
            if not post_id:
                post = self._create_post(connection, company_id, {
                    "title": campaign["name"], "body": campaign["offer"], "channels": campaign["channels"],
                })
                post_id = post["id"]
                connection.execute("UPDATE campaigns SET post_id = ?, status = 'prepared' WHERE company_id = ? AND id = ?",
                                   (post_id, company_id, campaign_id))
                self.record_activity(connection, company_id, f"Prepared campaign: {campaign['name']}. Planned budget is recorded only; no ad spend.")
            result = self._publish_post(connection, company_id, post_id)
            return {"campaign": campaign_from_row(self.scoped_row(connection, "campaigns", company_id, campaign_id)), **result}

    def _website(self, row):
        return {"draft": json.loads(row["website_draft_json"]), "published": json.loads(row["website_published_json"])}

    def get_website(self, company_id):
        with self.database.connection() as connection:
            return self._website(self.company_row(connection, company_id))

    def update_website(self, company_id, data):
        with self.database.connection(write=True) as connection:
            row = self.company_row(connection, company_id)
            website = self._website(row)
            for field in SITE_FIELDS:
                if field in data:
                    website["draft"][field] = text_field(data, field, 5000 if field in ("about", "announcement") else 500,
                                                        required=field in ("headline", "ctaLabel"))
            connection.execute("UPDATE companies SET website_draft_json = ? WHERE id = ?", (encode(website["draft"]), company_id))
            self.record_activity(connection, company_id, "Saved website draft.")
            return website

    def publish_website(self, company_id):
        with self.database.connection(write=True) as connection:
            row = self.company_row(connection, company_id)
            connection.execute("UPDATE companies SET website_published_json = website_draft_json WHERE id = ?", (company_id,))
            self.record_activity(connection, company_id, "Published website changes locally.")
            return self._website(self.company_row(connection, company_id))

    def public_website(self, slug, query=None):
        with self.database.connection() as connection:
            row = self.company_by_slug(connection, slug)
            company = company_from_row(row)
            company_id = company["id"]
            # Public contact/business settings are safe; commission settings belong to the dashboard.
            company.pop("commissionRate", None)
            services = [service_from_row(item) for item in connection.execute(
                "SELECT * FROM services WHERE company_id = ? AND active = 1 ORDER BY rowid", (company_id,))]
            posts = [json.loads(item["snapshot_json"]) for item in connection.execute("""SELECT * FROM published_posts
                WHERE company_id = ? ORDER BY published_at DESC, rowid DESC""", (company_id,))]
            campaign = None
            code = query_value(query or {}, "campaign")
            if code:
                campaign_row = connection.execute("SELECT * FROM campaigns WHERE company_id = ? AND source_code = ?",
                                                  (company_id, code)).fetchone()
                if campaign_row:
                    full = campaign_from_row(campaign_row)
                    campaign = {key: full[key] for key in ("id", "name", "objective", "offer", "sourceCode")}
            return {"company": company, "website": json.loads(row["website_published_json"]),
                    "services": services, "posts": posts[:12], "campaign": campaign}

    def list_deliveries(self, company_id):
        with self.database.connection() as connection:
            self.company_row(connection, company_id)
            return {"deliveries": [delivery_from_row(row) for row in connection.execute(
                "SELECT * FROM deliveries WHERE company_id = ? ORDER BY created_at DESC, rowid DESC", (company_id,))]}

    def list_activity(self, company_id):
        with self.database.connection() as connection:
            self.company_row(connection, company_id)
            return {"activity": [activity_from_row(row) for row in connection.execute(
                "SELECT * FROM activity WHERE company_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 100", (company_id,))]}

    def overview(self, company_id):
        company = self.get_settings(company_id)
        leads = self.list_leads(company_id)["leads"]
        bookings = self.list_bookings(company_id)["bookings"]
        campaigns = self.list_campaigns(company_id)["campaigns"]
        activity = self.list_activity(company_id)["activity"]
        metrics = {
            "newLeads": sum(lead["status"] == "new" for lead in leads),
            "confirmedBookings": sum(booking["status"] == "confirmed" for booking in bookings),
            "pipelineValue": round(sum(lead["value"] for lead in leads if lead["status"] in ("new", "contacted", "qualified")), 2),
            "convertedValue": round(sum(lead["value"] for lead in leads if lead["status"] == "won"), 2),
            "estimatedCommission": round(sum(lead["value"] * lead["commissionRate"] / 100 for lead in leads if lead["status"] == "won"), 2),
        }
        tz = business_timezone(company["timezone"])
        today = datetime.now(tz).date()
        counts = {today - timedelta(days=index): 0 for index in range(14)}
        for lead in leads:
            created_day = parse_datetime(lead["createdAt"]).astimezone(tz).date()
            if created_day in counts:
                counts[created_day] += 1
        daily = [{"date": day.isoformat(), "count": count} for day, count in sorted(counts.items())]
        return {"company": company, "metrics": metrics, "leads": leads[:8], "bookings": bookings[:8],
                "campaigns": campaigns[:8], "activity": activity[:8], "dailyLeads": daily}

    def export(self, company_id):
        with self.database.connection() as connection:
            # One read snapshot keeps related records consistent while other
            # browser requests write. Export includes all activity, not just
            # the most recent dashboard feed.
            connection.execute("BEGIN")
            row = self.company_row(connection, company_id)
            result = {"exportedAt": timestamp(), "formatVersion": 1,
                      "company": company_from_row(row), "website": self._website(row)}
            serializers = {"services": service_from_row, "leads": lead_from_row,
                           "bookings": booking_from_row, "posts": post_from_row,
                           "campaigns": campaign_from_row, "deliveries": delivery_from_row,
                           "activity": activity_from_row}
            for table, serialize in serializers.items():
                result[table] = [serialize(item) for item in connection.execute(
                    f"SELECT * FROM {table} WHERE company_id = ? ORDER BY created_at, rowid", (company_id,))]
            result["publishedPosts"] = [json.loads(item["snapshot_json"]) for item in connection.execute(
                "SELECT * FROM published_posts WHERE company_id = ? ORDER BY published_at, rowid", (company_id,))]
            return result

    def dispatch(self, method, path, query=None, body=None):
        """Return a JSON payload; HTTP status/security are handled by routes.py."""
        query = query or {}
        body = body or {}
        parts = [part for part in path.strip("/").split("/") if part]
        if parts == ["api", "companies"] and method == "POST":
            return self.create_company(body)
        if len(parts) >= 3 and parts[:2] == ["api", "public"]:
            slug = parts[2]
            resource = parts[3] if len(parts) == 4 else "" if len(parts) == 3 else None
            if method == "GET" and resource == "":
                return self.public_website(slug, query)
            if method == "GET" and resource == "slots":
                return self.list_slots(slug, query)
            if method == "POST" and resource == "bookings":
                return self.create_booking(slug, body)
            if method == "POST" and resource == "enquiries":
                return self.create_enquiry(slug, body)
        if len(parts) >= 4 and parts[:2] == ["api", "companies"]:
            company_id, resource = parts[2:4]
            resource_id = parts[4] if len(parts) > 4 else None
            action = parts[5] if len(parts) == 6 else None
            if len(parts) > 6:
                raise ApiError(404, "This API endpoint was not found.")
            if len(parts) == 4:
                getters = {"overview": self.overview, "settings": self.get_settings,
                           "leads": lambda cid: self.list_leads(cid, query), "bookings": self.list_bookings,
                           "services": self.list_services, "posts": self.list_posts,
                           "campaigns": self.list_campaigns, "website": self.get_website,
                           "deliveries": self.list_deliveries, "activity": self.list_activity, "export": self.export}
                creators = {"leads": self.create_lead, "services": self.create_service,
                            "posts": self.create_post, "campaigns": self.create_campaign}
                updaters = {"settings": self.update_settings, "website": self.update_website}
                if method == "GET" and resource in getters:
                    return getters[resource](company_id)
                if method == "POST" and resource in creators:
                    return creators[resource](company_id, body)
                if method == "PATCH" and resource in updaters:
                    return updaters[resource](company_id, body)
            if len(parts) == 5:
                updaters = {"leads": self.update_lead, "bookings": self.update_booking,
                            "services": self.update_service, "posts": self.update_post}
                if method == "PATCH" and resource in updaters:
                    return updaters[resource](company_id, resource_id, body)
                if method == "POST" and resource == "website" and resource_id == "publish":
                    return self.publish_website(company_id)
            if len(parts) == 6 and method == "POST":
                if resource == "posts" and action == "publish":
                    return self.publish_post(company_id, resource_id)
                if resource == "campaigns" and action == "run":
                    return self.run_campaign(company_id, resource_id)
        raise ApiError(404, "This API endpoint was not found.")

    def seed_demo(self):
        """Seed only an empty database. Everything is fictional and persists afterwards."""
        with self.database.connection(write=True) as connection:
            if connection.execute("SELECT COUNT(*) FROM companies").fetchone()[0]:
                return
            company = self._create_company(connection, {"name": "Juniper Studio", "slug": "juniper-studio"})
            company_id = company["id"]
            settings = {key: value for key, value in company.items() if key not in ("id", "name", "slug")}
            settings.update({"tagline": "Make room for a little green.",
                             "description": "Plant styling, thoughtful workshops, and greener spaces. We help homes and small businesses find their natural rhythm.",
                             "email": "hello@juniper.example.test", "phone": "+27 10 000 0142",
                             "address": "Demo studio · Johannesburg, South Africa", "commissionRate": 5})
            website = {"headline": "A greener space. A brighter day.",
                       "subheadline": "Thoughtful plant styling and hands-on workshops for spaces you love.",
                       "about": settings["description"], "ctaLabel": "Find your green", "announcement": "Our spring workshop calendar is open. Come grow something good."}
            connection.execute("UPDATE companies SET settings_json = ?, website_draft_json = ?, website_published_json = ? WHERE id = ?",
                               (encode(settings), encode(website), encode(website), company_id))
            first_service = connection.execute("SELECT id FROM services WHERE company_id = ?", (company_id,)).fetchone()[0]
            connection.execute("UPDATE services SET name = ?, description = ?, duration_minutes = ?, price = ? WHERE id = ?",
                               ("Plant styling consultation", "A personal plan to bring greenery into your home or workspace.", 60, 650, first_service))
            workshop = self._create_service(connection, company_id, {"name": "Terrarium workshop", "description": "Build a miniature green world with a guided studio session.", "durationMinutes": 90, "price": 480})
            self._create_service(connection, company_id, {"name": "Plant care check-in", "description": "Practical advice to help your plants thrive.", "durationMinutes": 30, "price": 250})
            demo_people = [("Alex Morgan", "new", 650), ("Jamie Reed", "qualified", 2800),
                           ("Casey Green", "won", 1950), ("Taylor Ellis", "contacted", 480),
                           ("Sam Rivera", "new", 650), ("Jordan Lee", "won", 3400),
                           ("Drew Parker", "lost", 480), ("Riley Adams", "qualified", 1250)]
            for index, (name, status, value) in enumerate(demo_people):
                created = (datetime.now(timezone.utc) - timedelta(days=index * 2)).isoformat(timespec="seconds")
                self._create_lead(connection, company_id, {"name": name, "email": f"demo{index + 1}@example.test",
                    "phone": "", "message": "Synthetic demo inquiry about greener spaces.",
                    "source": ["website", "manual", "referral"][index % 3], "status": status,
                    "value": value, "notes": "Fictional sample record for this local demo."}, created)
            company = company_from_row(self.company_row(connection, company_id))
            next_day = datetime.now(business_timezone(company["timezone"])).date() + timedelta(days=1)
            while next_day.isoweekday() not in company["bookingDays"]:
                next_day += timedelta(days=1)
            for index, (name, service_id, service_name, duration, status) in enumerate([
                ("Avery Stone", first_service, "Plant styling consultation", 60, "confirmed"),
                ("Quinn Brooks", workshop["id"], workshop["name"], 90, "requested"),
            ]):
                start = datetime.combine(next_day, time(10 + index * 3), business_timezone(company["timezone"]))
                lead = self._create_lead(connection, company_id, {"name": name, "email": f"booking-demo{index}@example.test",
                    "message": "Synthetic appointment request.", "source": "website", "value": 650 if index == 0 else 480,
                    "notes": "Fictional sample booking."})
                connection.execute("INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (new_id(), company_id, name, lead["email"], "", service_id, service_name,
                     start.isoformat(timespec="seconds"), (start + timedelta(minutes=duration)).isoformat(timespec="seconds"),
                     status, "Fictional sample booking.", lead["id"], timestamp()))
            post = self._create_post(connection, company_id, {"title": "Small spaces, big green energy",
                "body": "A sunny corner and the right plant can change how a room feels. Book a styling consultation to find your perfect match.",
                "channels": ["website", "instagram", "facebook"]})
            self._publish_post(connection, company_id, post["id"])
            self._create_post(connection, company_id, {"title": "A little care goes a long way", "body": "This week's plant care tip: check your soil before reaching for the watering can.", "channels": ["website", "instagram"]})
            self._create_campaign(connection, company_id, {"name": "Spring studio sessions", "objective": "bookings",
                "offer": "Bring a little green into your week. Explore our terrarium workshops and book your studio session.",
                "plannedBudget": 500, "channels": ["website", "instagram", "facebook"]})
            self._create_campaign(connection, company_id, {"name": "Greener workspaces", "objective": "leads",
                "offer": "A thoughtful plant plan for your team. Start with a personal workspace styling consultation.",
                "plannedBudget": 350, "channels": ["website", "linkedin"]})
            self.record_activity(connection, company_id, "Loaded fictional demo records. No external accounts, leads, or spending are involved.")


def create_application(database_path, seed=True):
    return Application(database_path, seed=seed)
