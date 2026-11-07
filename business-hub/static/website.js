// This page only reads the published website. Forms write to the public inbox;
// editing company data stays in the business dashboard.
const companySlug = decodeURIComponent(location.pathname.split("/").filter(Boolean)[1] || "juniper-studio");
const campaignCode = new URLSearchParams(location.search).get("campaign") || "";
const publicApi = `/api/public/${encodeURIComponent(companySlug)}`;
const bookingDialog = document.querySelector("#booking-dialog");
const enquiryDialog = document.querySelector("#enquiry-dialog");
const bookingForm = document.querySelector("#booking-form");
const enquiryForm = document.querySelector("#enquiry-form");
const serviceSelect = document.querySelector("#booking-service");
const dateInput = document.querySelector("#booking-date");
const slotsContainer = document.querySelector("#booking-slots");
let studio = null;
let slotsController = null;
let slotsRequestNumber = 0;
let availableSlotCount = 0;

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  let result;
  try {
    result = await response.json();
  } catch {
    throw new Error("The studio returned an unexpected response. Please try again.");
  }
  if (!response.ok) {
    const error = new Error(result.error || "We couldn’t save your request. Please try again.");
    error.status = response.status;
    throw error;
  }
  return result;
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function setText(selector, text) {
  document.querySelector(selector).textContent = text || "";
}

function showError(id, error) {
  const element = document.querySelector(id);
  element.textContent = error.message || "Something went wrong. Please try again.";
  element.hidden = false;
}

function clearError(id) {
  const element = document.querySelector(id);
  element.textContent = "";
  element.hidden = true;
}

function businessTimezone() {
  return studio?.company.timezone || "Africa/Johannesburg";
}

function todayInBusinessTimezone() {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: businessTimezone(), year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const part = type => parts.find(item => item.type === type).value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}

function suggestedBookingDate() {
  // Start tomorrow, then move to the next day the company accepts bookings.
  const date = new Date(`${todayInBusinessTimezone()}T12:00:00Z`);
  const openingDays = studio.company.bookingDays || [1, 2, 3, 4, 5];
  for (let day = 0; day < 8; day += 1) {
    date.setUTCDate(date.getUTCDate() + 1);
    const weekday = date.getUTCDay() || 7;
    if (openingDays.includes(weekday)) break;
  }
  return date.toISOString().slice(0, 10);
}

function money(amount) {
  return new Intl.NumberFormat("en-ZA", {
    style: "currency", currency: studio.company.currency || "ZAR", maximumFractionDigits: 0,
  }).format(Number(amount || 0));
}

function formatDate(value, includeTime = false) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-ZA", {
    timeZone: businessTimezone(), day: "numeric", month: "short", year: "numeric",
    ...(includeTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(date);
}

function renderHeadline(text) {
  // A plain-text published headline gets a small editorial flourish on its last
  // word. Text is always escaped by the DOM; customer content is never HTML.
  const heading = document.querySelector("#hero-heading");
  heading.replaceChildren();
  const words = text.match(/^(.*?)(\S+)\s*$/s);
  if (!words) { heading.textContent = text; return; }
  heading.append(document.createTextNode(words[1]), makeElement("em", "", words[2]));
}

function serviceIllustration(index) {
  // Hand-authored decorative SVGs share the blue/coral website palette.
  // Customer text never enters these markup strings.
  const drawings = [
    `<circle cx="107" cy="36" r="19" fill="#ff8169"/>
     <path d="M77 113V33" fill="none" stroke="#15223b" stroke-width="3"/>
     <path d="M77 91C46 93 26 73 30 47C59 45 79 64 77 91Z" fill="#315fe7"/>
     <path d="M77 69C98 73 123 54 125 30C102 27 80 43 77 69Z" fill="#15223b"/>
     <path d="M77 41C58 33 55 16 64 5C80 10 86 25 77 41Z" fill="#315fe7"/>
     <path d="M76 85L39 54M80 64L116 37" fill="none" stroke="#f3f6fc" stroke-width="2"/>
     <path d="M48 108H106L96 148H58Z" fill="#ff8169"/>
     <path d="M46 106H108V115H46Z" fill="#15223b"/>
     <path d="M62 125H92" stroke="#ffffff" stroke-width="3"/>`,
    `<path d="M24 146H139" stroke="#15223b" stroke-width="2"/>
     <path d="M62 111V54M62 97L38 73M62 77L83 54" fill="none" stroke="#15223b" stroke-width="3"/>
     <path d="M62 95C41 99 28 85 29 67C46 61 61 77 62 95Z" fill="#315fe7"/>
     <path d="M63 78C84 82 99 65 97 47C79 46 65 59 63 78Z" fill="#ff8169"/>
     <path d="M44 103H82L92 121L81 144H44L34 121Z" fill="#ffffff" stroke="#315fe7" stroke-width="2"/>
     <path d="M43 129H82L76 141H48Z" fill="#315fe7"/>
     <path d="M118 113V75" fill="none" stroke="#15223b" stroke-width="3"/>
     <path d="M118 96C103 97 95 86 98 75C111 74 120 84 118 96Z" fill="#15223b"/>
     <path d="M118 80C133 84 142 72 141 61C129 59 118 68 118 80Z" fill="#315fe7"/>
     <path d="M101 111H137L130 144H108Z" fill="#ff8169"/>`,
    `<circle cx="78" cy="77" r="57" fill="#ffffff"/>
     <path d="M78 123V24" fill="none" stroke="#15223b" stroke-width="3"/>
     <path d="M78 107C51 109 34 89 39 68C62 64 80 83 78 107Z" fill="#315fe7"/>
     <path d="M79 85C105 90 128 72 126 51C101 49 81 62 79 85Z" fill="#ff8169"/>
     <path d="M77 61C53 56 46 34 56 19C75 22 85 42 77 61Z" fill="#15223b"/>
     <path d="M79 39C97 43 111 29 109 13C91 13 80 24 79 39Z" fill="#315fe7"/>
     <path d="M48 117H108L99 151H57Z" fill="#15223b"/>
     <path d="M47 117H109V126H47Z" fill="#315fe7"/>
     <path d="M61 135H95" stroke="#ff8169" stroke-width="3"/>`,
  ];
  const art = makeElement("div", "service-art");
  art.setAttribute("aria-hidden", "true");
  art.innerHTML = `<svg viewBox="0 0 155 165">${drawings[index % drawings.length]}</svg>`;
  art.append(makeElement("span", "service-number", String(index + 1).padStart(2, "0")));
  art.append(makeElement("span", "service-category", "LEARN · CREATE · GROW"));
  return art;
}

function renderServices(services) {
  const grid = document.querySelector("#services-grid");
  grid.replaceChildren();
  serviceSelect.replaceChildren();
  if (!services.length) {
    const empty = makeElement("div", "empty-state");
    empty.append(makeElement("p", "", "New offerings are taking root. Send us an enquiry and we’ll help you find the right next step."));
    grid.append(empty);
  }
  services.forEach((service, index) => {
    const card = makeElement("article", "service-card");
    const content = makeElement("div", "service-content");
    content.append(makeElement("h3", "", service.name), makeElement("p", "", service.description));
    const meta = makeElement("div", "service-meta");
    meta.append(makeElement("span", "", `${service.durationMinutes} min`), makeElement("strong", "", Number(service.price) === 0 ? "Complimentary" : money(service.price)));
    const bookButton = makeElement("button", "service-book", "Make a booking");
    bookButton.type = "button";
    bookButton.append(makeElement("span", "", "↗"));
    bookButton.addEventListener("click", () => openBooking(service.id));
    content.append(meta, bookButton);
    card.append(serviceIllustration(index), content);
    grid.append(card);
    const option = makeElement("option", "", service.name);
    option.value = service.id;
    serviceSelect.append(option);
  });
  document.querySelectorAll("[data-book]").forEach(button => { button.disabled = !services.length; });
}

function renderPosts(posts) {
  const grid = document.querySelector("#posts-grid");
  grid.replaceChildren();
  if (!posts.length) {
    const empty = makeElement("div", "empty-state");
    empty.append(makeElement("p", "", "Our next studio note is on its way. Come back soon for fresh ideas and invitations."));
    grid.append(empty);
    return;
  }
  posts.slice(0, 6).forEach(post => {
    const card = makeElement("article", "post-card");
    const date = makeElement("time", "post-date", formatDate(post.publishedAt || post.createdAt));
    date.dateTime = post.publishedAt || post.createdAt || "";
    card.append(date, makeElement("h3", "", post.title), makeElement("p", "", post.body));
    const flourish = makeElement("span", "post-flourish", "✳");
    flourish.setAttribute("aria-hidden", "true");
    card.append(flourish);
    grid.append(card);
  });
}

function renderStudio(data) {
  studio = data;
  const { company, website, services, posts, campaign } = data;
  // Accept a hex brand color only. The stylesheet supplies the default palette.
  const brandColor = company.accentColor;
  if (typeof brandColor === "string" && /^#(?:[\da-f]{3}|[\da-f]{6})$/i.test(brandColor)) {
    document.documentElement.style.setProperty("--accent", brandColor);
  } else {
    document.documentElement.style.removeProperty("--accent");
  }
  document.querySelectorAll("[data-company-name]").forEach(element => { element.textContent = company.name; });
  document.title = `${company.name} · ${company.tagline || "Welcome to the studio"}`;
  document.querySelector('meta[name="description"]').content = company.description || website.subheadline || "";
  renderHeadline(website.headline || company.name);
  setText("#hero-subheadline", website.subheadline || company.description);
  setText("#about-text", website.about || company.description);
  setText("#footer-tagline", company.tagline);
  // Keep the directional arrow separate from the editable call-to-action label.
  const heroButton = document.querySelector("#hero-cta");
  heroButton.replaceChildren(document.createTextNode(website.ctaLabel || "Make a booking"));
  const arrow = makeElement("span", "", "↗");
  arrow.setAttribute("aria-hidden", "true");
  heroButton.append(arrow);
  const announcement = document.querySelector("#announcement");
  announcement.textContent = website.announcement || "";
  announcement.hidden = !website.announcement;
  const emailLink = document.querySelector("#contact-email");
  emailLink.textContent = company.email || "";
  emailLink.href = `mailto:${company.email || ""}`;
  emailLink.hidden = !company.email;
  const phoneLink = document.querySelector("#contact-phone");
  phoneLink.textContent = company.phone || "";
  phoneLink.href = `tel:${(company.phone || "").replace(/[^+\d]/g, "")}`;
  phoneLink.hidden = !company.phone;
  setText("#contact-address", company.address);
  const campaignBanner = document.querySelector("#campaign-banner");
  campaignBanner.hidden = !campaign?.offer;
  setText("#campaign-offer", campaign?.offer);
  const timezoneName = businessTimezone().split("/").at(-1).replaceAll("_", " ");
  setText("#booking-timezone", `· ${timezoneName} time`);
  renderServices(services || []);
  renderPosts(posts || []);
  document.querySelectorAll("[data-enquire]").forEach(button => { button.disabled = false; });
}

async function loadStudio() {
  document.querySelector("#load-error").hidden = true;
  const content = document.querySelector("#site-content");
  content.hidden = false;
  content.setAttribute("aria-busy", "true");
  document.querySelectorAll("[data-book], [data-enquire]").forEach(button => { button.disabled = true; });
  try {
    const query = campaignCode ? `?campaign=${encodeURIComponent(campaignCode)}` : "";
    renderStudio(await requestJson(`${publicApi}${query}`));
  } catch (error) {
    content.hidden = true;
    document.querySelector("#load-error").hidden = false;
    setText("#load-error-message", error.message || "Please check your connection and try again.");
  } finally {
    content.setAttribute("aria-busy", "false");
  }
}

function resetDialog(form, successId, errorId) {
  form.reset();
  form.hidden = false;
  document.querySelector(successId).hidden = true;
  clearError(errorId);
}

function openBooking(serviceId) {
  if (!studio?.services.length) return;
  resetDialog(bookingForm, "#booking-success", "#booking-error");
  if (serviceId) serviceSelect.value = serviceId;
  dateInput.min = todayInBusinessTimezone();
  dateInput.value = suggestedBookingDate();
  bookingDialog.showModal();
  loadAvailableSlots();
}

function openEnquiry() {
  if (!studio) return;
  resetDialog(enquiryForm, "#enquiry-success", "#enquiry-error");
  enquiryDialog.showModal();
}

async function loadAvailableSlots() {
  // Abort old date/service requests so a slow response cannot display times for
  // a previously selected day or offering.
  slotsController?.abort();
  slotsController = new AbortController();
  const requestNumber = ++slotsRequestNumber;
  availableSlotCount = 0;
  document.querySelector("#booking-submit").disabled = true;
  slotsContainer.replaceChildren(makeElement("p", "slots-message", "Finding available times…"));
  clearError("#booking-error");
  if (!serviceSelect.value || !dateInput.value || !dateInput.validity.valid) {
    slotsContainer.replaceChildren(makeElement("p", "slots-message", "Choose a service and a valid date to see available times."));
    return;
  }
  try {
    const query = new URLSearchParams({ serviceId: serviceSelect.value, date: dateInput.value });
    const result = await requestJson(`${publicApi}/slots?${query}`, { signal: slotsController.signal });
    if (requestNumber !== slotsRequestNumber) return;
    slotsContainer.replaceChildren();
    availableSlotCount = result.slots.length;
    if (!result.slots.length) {
      slotsContainer.append(makeElement("p", "slots-message", "No times available on this date. Try another day, or send us an enquiry."));
      return;
    }
    result.slots.forEach(slot => {
      const label = makeElement("label", "slot-option");
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "startAt";
      input.value = slot.startAt;
      input.required = true;
      label.append(input, makeElement("span", "", slot.label));
      slotsContainer.append(label);
    });
    document.querySelector("#booking-submit").disabled = false;
  } catch (error) {
    if (error.name === "AbortError" || requestNumber !== slotsRequestNumber) return;
    slotsContainer.replaceChildren(makeElement("p", "slots-message", "We couldn’t load available times. Choose a date again to retry."));
    showError("#booking-error", error);
  }
}

function contactFormData(form) {
  const fields = new FormData(form);
  const payload = {
    name: String(fields.get("name") || "").trim(),
    email: String(fields.get("email") || "").trim(),
    phone: String(fields.get("phone") || "").trim(),
    message: String(fields.get("message") || "").trim(),
    consent: fields.get("consent") === "on",
  };
  if (campaignCode) payload.campaignCode = campaignCode;
  return payload;
}

bookingForm.addEventListener("submit", async event => {
  event.preventDefault();
  if (!bookingForm.reportValidity()) return;
  clearError("#booking-error");
  const button = document.querySelector("#booking-submit");
  const fields = new FormData(bookingForm);
  const payload = { ...contactFormData(bookingForm), serviceId: fields.get("serviceId"), startAt: fields.get("startAt") };
  if (!payload.startAt) {
    showError("#booking-error", new Error("Please choose an available time for your visit."));
    return;
  }
  button.disabled = true;
  button.textContent = "Sending your request…";
  try {
    const booking = await requestJson(`${publicApi}/bookings`, { method: "POST", body: JSON.stringify(payload) });
    const service = studio.services.find(item => String(item.id) === String(payload.serviceId));
    setText("#booking-success-message", `${service?.name || "Your visit"} · ${formatDate(booking.startAt || payload.startAt, true)}. Your booking request is saved. The studio will contact you to confirm.`);
    bookingForm.hidden = true;
    document.querySelector("#booking-success").hidden = false;
    document.querySelector("#booking-success [data-close]").focus();
  } catch (error) {
    if (error.status === 409) {
      await loadAvailableSlots();
      showError("#booking-error", new Error("That time was just taken. Please choose another available time and send your request again."));
    } else {
      showError("#booking-error", error);
    }
  } finally {
    button.textContent = "Send booking request ↗";
    button.disabled = availableSlotCount === 0;
  }
});

enquiryForm.addEventListener("submit", async event => {
  event.preventDefault();
  if (!enquiryForm.reportValidity()) return;
  clearError("#enquiry-error");
  const button = document.querySelector("#enquiry-submit");
  button.disabled = true;
  button.textContent = "Sending your enquiry…";
  try {
    await requestJson(`${publicApi}/enquiries`, { method: "POST", body: JSON.stringify(contactFormData(enquiryForm)) });
    enquiryForm.hidden = true;
    document.querySelector("#enquiry-success").hidden = false;
    document.querySelector("#enquiry-success [data-close]").focus();
  } catch (error) {
    showError("#enquiry-error", error);
  } finally {
    button.disabled = false;
    button.textContent = "Send your enquiry ↗";
  }
});

document.querySelectorAll("[data-book]").forEach(button => button.addEventListener("click", () => openBooking()));
document.querySelectorAll("[data-enquire]").forEach(button => button.addEventListener("click", openEnquiry));
document.querySelectorAll("[data-close]").forEach(button => button.addEventListener("click", () => button.closest("dialog").close()));
// Native dialogs handle Escape and focus restoration. A click on the backdrop
// also closes the form, while clicking inside it leaves entered details intact.
[bookingDialog, enquiryDialog].forEach(dialog => {
  dialog.addEventListener("click", event => {
    if (event.target !== dialog) return;
    const rectangle = dialog.getBoundingClientRect();
    if (event.clientX < rectangle.left || event.clientX > rectangle.right || event.clientY < rectangle.top || event.clientY > rectangle.bottom) dialog.close();
  });
});
bookingDialog.addEventListener("close", () => { slotsController?.abort(); slotsRequestNumber += 1; });
serviceSelect.addEventListener("change", loadAvailableSlots);
dateInput.addEventListener("change", loadAvailableSlots);
document.querySelector("#retry-load").addEventListener("click", loadStudio);
setText("#year", new Date().getFullYear());
loadStudio();
