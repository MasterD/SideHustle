# Verification — 30 September 2026

## Conversion and archives

JavaScript syntax checks passed for core.js and app.js. Eleven Node assertions passed: BOM/CRLF parsing, SRT/VTT round trips, VTT metadata omission warnings, malformed input rejection, offset handling, markup/entity cleanup, Unicode wrapping, quoted/formula-safe CSV cells, review flags, unsafe ZIP name rejection and ZIP output creation.

Python's independent zipfile reader verified generated ZIP CRCs, exact entry counts and UTF-8 content including a non-ASCII filename and emoji. build.py validates the final customer archive and records its SHA-256 in dist/manifest.json. The archive contains exactly the toolkit, guide and two original examples. It excludes sales preparation, screenshots, test code and owner information.

## Browser checks

Chromium browser verification passed for:

- Working sample-to-transcript conversion on the review page.
- Subtitle-to-plain-text export with formatting tags and timings removed.
- Positive 1.5-second timing offset.
- Rejection of offsets that move a caption before zero.
- Blocking of old downloads after invalid settings.
- Multi-file import and actual clean-captions.zip download.
- Rejection of a malformed member with its filename, without a partial batch export.
- Clearing input/output and reloading the original sample.
- Working single-caption-file download.
- No horizontal overflow at a 390-pixel viewport.
- Full desktop visual inspection of the tool and proposed offer.

The browser test harness initially timed out waiting on a download event; a subsequent direct UI click verified the download and the browser's saved-file notification. No unresolved application error remained. The final rebuilt page includes a local data-URL favicon; the browser reported no application console errors on the toolkit.

## Practical limits

The tool was tested in current Chromium. Edge and Firefox support the standard APIs used but have not been independently tested. The customer artifact is self-contained with no external dependencies; its Content Security Policy disables network connections. Ordinary UTF-8 SRT and VTT are supported. Advanced VTT layout metadata is explicitly omitted. Readability flags do not verify accuracy against spoken audio.

## Gumroad launch and delivery

The existing draft `tzihvm` was resumed after the owner's reboot and published at US$9 once on 30 September 2026. The saved listing has its approved description, summary, custom URL, original 1280×720 cover and 600×600 thumbnail. Customer content contains setup instructions and the ZIP; the receipt contains the custom instructions and seller contact `tiaanbok@gmail.com`.

Public URL: https://tiaanbok0.gumroad.com/l/caption-cleanup-kit. The storefront also lists the product. Category: Software Development > Software & Plugins. Product type: Full application. Language: JavaScript. License attribute: Commercial. Seven relevant tags and the existing ratings setting were saved. The display name and bio were saved as Caption Cleanup Kit; the unused email subscribe form was hidden.

The signed-in creator checkout explicitly confirmed this was a test purchase and the payment method would not be charged. The owner approved completing its CAPTCHA. The test succeeded and opened the customer content page. An actual UI download saved `C:/Users/tiaan.botha/Downloads/Caption-Cleanup-Kit-v1.zip`.

Independent Python verification confirmed the delivered archive is byte-for-byte identical to the uploaded package, all CRCs are valid, and the exact four intended files are present. Size: 13,534 bytes. SHA-256: `c3431fd6b1642cad28b825077fe48cd92d94f057104a67cd45c1f6308ed312c9`.

The Gumroad Products table showed Published, US$9, zero genuine sales and US$0 revenue after the test. The test is not an income entry. Proof images are `gumroad-live.png` and `gumroad-delivery.png`.

The scheduled daily check was created successfully, automation `caption-shop-daily-check`. Its public-listing, checkout and aggregate-sales checks were exercised manually in this session. Future scheduled execution has not yet occurred. Receipt content and the customer access page were verified; actual email arrival, real-card payments, refunds, payout review and bank settlement remain untested. No paid promotion occurred during product launch.

On 30 September 2026 the owner authorized relevant advertising. A LinkedIn public post was verified through the successful-post notice and resulting page, including its product preview and tracked link. A Gumroad guide was verified in the Published table and public page; the storefront shows the product and guide sections. A Reddit submission was created but removed by platform filters, so it is recorded as filtered rather than active advertising. One moderator review request was submitted; the form cleared without an error, but moderator receipt/approval is not verified. Further Reddit promotion is held.

The existing heartbeat was updated, preserving its daily 09:00 schedule and target chat, to check sales, moderation and the authorized R0 campaign with saved posting limits. JSON campaign records parse successfully. The product archive was not rebuilt or modified; its SHA-256 still matches the exact delivered test package. The Gumroad Products table was checked again after the campaign setup and showed US$9, Published, zero genuine sales and US$0 revenue. Buyer traffic and campaign attribution remain unknown. Screenshots and exact placement URLs are stored under `marketing/`.
