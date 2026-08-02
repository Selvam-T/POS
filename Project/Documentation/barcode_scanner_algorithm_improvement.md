# Barcode Scanner Buffering Algorithm Improvement

> Temporary production tracing is currently enabled to diagnose intermittent
> lost scans without changing this algorithm. See `barcode_scanner_trace.md`.

## Purpose

This document records an intermittent barcode truncation issue, the current
configuration-based mitigation, and a possible long-term redesign of the HID
keyboard-wedge buffering algorithm. It is intended for future consideration;
it does not describe an implemented algorithm change.

Related documents:

- [scanner_input_infocus.md](scanner_input_infocus.md) describes scanner focus,
  UI protection, modal blocking, and routing.
- [barcode_manager.md](barcode_manager.md) describes `BarcodeManager`, dialog
  overrides, and completed-scan routing.

## Current Architecture

The barcode scanner operates as a USB HID keyboard wedge. Windows presents
scanner output as ordinary keyboard events, and `pynput` observes those events.
There is no dedicated scanner data channel or device identity at this layer, so
the application distinguishes scanner input from manual typing primarily by
timing.

`modules/devices/scanner.py` owns raw key buffering:

1. Record the time of each key press.
2. Compare the interval with `SCANNER_KEY_INTERVAL_SECONDS` from `config.py`.
3. Append the character when the interval is within the threshold.
4. Replace the buffer with the latest character when the interval exceeds the
   threshold.
5. On Enter, emit the buffer as `barcode_scanned` when it contains at least
   three characters, then clear it.

`modules/devices/barcode_manager.py` receives the completed barcode and routes
it to a dialog override, a protected/blocked context, or the sales table. If a
sales-table lookup does not find the emitted code, the missing-scan workflow
opens Product Management on the ADD tab with that code.

`SCANNER_UI_SUPPRESS_SECONDS` serves a different purpose. It prevents the
scanner's trailing Enter from activating forms or default buttons during the
scanner-like window. It does not construct the barcode buffer and cannot restore
or remove barcode digits.

## Observed Issue

The existing product code `5028197552916` was scanned repeatedly. Most scans
correctly added the product to the sales table or incremented its quantity.
Intermittently, Product Management opened on ADD as though the product did not
exist. Observed incomplete values included:

- `028197552916`, which is the complete code without its first digit `5`.
- A visible final digit `6` in the ADD product-code field during one occurrence.
- A small number of other apparent partial-code occurrences.

The missing-prefix example closely matches the current buffer-reset behavior.
If the interval between `5` and `0` exceeds the configured threshold, the code
replaces the buffer containing `5` with `0`, appends the remaining fast events,
and emits `028197552916` when Enter arrives. The database lookup correctly
reports that truncated code as missing, so Product Management correctly opens
for the incorrect input it received.

A one-character barcode cannot be emitted directly by the current scanner
class because its minimum emitted length is three characters. A lone visible
`6` is therefore more likely to be a native HID character temporarily leaking
into the focused widget, a residual UI-cleanup effect, or part of a later scan
while the Product Management dialog is opening. Once that dialog opens,
continued scans may be routed through its barcode override, which makes visual
observations during rapid repeated testing harder to associate with a single
physical scan.

## Why a Normal Physical Scan Can Exceed the Threshold

The operator's speed between trigger pulls is not the measurement used by the
algorithm. The important measurement is the elapsed time between individual
digit key events within one barcode.

Even when the scanner decodes and transmits a complete barcode normally, one
observed interval can be extended by:

- Windows thread scheduling;
- `pynput` listener scheduling;
- temporary application or CPU load;
- USB/HID delivery and driver scheduling;
- other system activity delaying callback execution.

Consequently, a pause measured by the application does not necessarily mean
the scanner paused or failed to read the label. A crumpled or damaged label
usually causes a no-read or a checksum failure at the scanner. It would not
normally remove the corresponding digit position from an otherwise correctly
decoded barcode.

## Current Implemented Mitigation

`SCANNER_KEY_INTERVAL_SECONDS` was temporarily increased from `0.05` seconds to
`0.10` seconds. Although this increased tolerance for delayed scanner key
delivery, production testing showed that fast manual typing could be classified
as scanner activity, momentarily suppressing or swallowing widget input.

The setting was therefore returned to `0.05` seconds. At that value, repeated
13-digit physical scans were captured correctly and product-code widget input
remained smooth. Temporary anomaly-focused tracing remains enabled to collect
evidence if the original intermittent lost-scan condition recurs.

This setting has a tradeoff: increasing it makes fast manual typing more likely
to resemble scanner input. The current focus protection and routing rules reduce
the UI impact, but the interval should not be increased repeatedly without
testing. More importantly, a threshold increase reduces the probability of the
failure but retains the underlying all-or-nothing reset behavior. Any individual
event delayed beyond the new threshold can still discard a valid prefix.

## Proposed Long-Term Design

### Design Principle

Do not discard an existing candidate because of one moderately delayed key.
Retain all printable characters until Enter, record their timing evidence, and
classify the completed candidate using the whole sequence.

Conceptually, replace:

```text
character -> character -> gap above threshold -> discard prefix -> continue
```

with:

```text
first printable character -> retain complete candidate -> Enter -> evaluate
```

For example:

```text
5 0 2 8 1 9 7 5 5 2 9 1 6 Enter
  ^ one interval is delayed
```

The `0` would still be appended. The delayed interval would lower the timing
confidence, but it would not transform the candidate into `028197552916`.

### Suggested Candidate Session

A future scanner listener could maintain a candidate session containing:

- the complete character buffer;
- the timestamp of the first character;
- the timestamp of the most recent character;
- every inter-key interval, or counters derived from them;
- the number and proportion of scanner-fast intervals;
- whether Enter completed the sequence;
- optional format and checksum results.

Suggested processing flow:

1. The first printable character starts a candidate session.
2. Every following printable character is appended; a moderately slow interval
   does not erase earlier characters.
3. Each interval is recorded as timing evidence.
4. Enter completes and evaluates the candidate.
5. Emit it only when the combined timing, length, context, and optional format
   evidence classify it as scanner-like.
6. Clear the candidate after emission, rejection, or a substantially longer
   abandonment timeout.

### Separate Fast-Key and Abandonment Thresholds

One threshold currently serves both classification and buffer reset. The future
design should separate those decisions:

- **Fast-key threshold:** approximately `0.10` seconds. This contributes one
  piece of evidence that the sequence is scanner-like.
- **Abandonment timeout:** approximately `0.50` to `1.00` seconds. Only this
  substantially longer idle period should terminate an incomplete session.

These values are starting points and require measurement with the production
scanner and POS hardware. Separating them prevents an ordinary scheduling delay
from being treated as the end of one sequence and the start of another.

### Whole-Sequence Classification

Instead of requiring every interval to be fast, classification could require
most intervals to be fast. A starting policy might require:

- completion by the scanner's Enter suffix;
- at least five characters for a normal external barcode;
- 70 to 80 percent of inter-key intervals at or below `0.10` seconds;
- no interval above the abandonment timeout;
- a total duration consistent with scanner delivery;
- an allowed focus or routing context.

These are proposed values, not established production constants. Timing data
should be collected before finalizing them.

The application currently permits short internal product codes, and the raw
scanner class currently accepts a minimum length of three. External retail
barcodes and manually entered internal shortcut codes should ideally have
separate policies. Increasing the scanner candidate minimum must not prevent
cashiers from typing valid short internal codes through their intended manual
workflow.

### Use a Monotonic Clock

Elapsed intervals should use `time.monotonic()` rather than `time.time()`.
A monotonic clock is intended for duration measurement and cannot jump because
the operating-system wall clock is corrected. This change would not solve HID
scheduling delays by itself, but it would make timing comparisons more reliable.

### Barcode Format and Checksum Evidence

Standard retail formats can provide evidence independent of timing:

- EAN-13: 13 numeric digits with a valid checksum;
- UPC-A: 12 numeric digits with a valid checksum;
- EAN-8 and other formats enabled on the production scanner, if applicable.

`5028197552916` is a valid EAN-13 candidate. A valid length and checksum provide
strong evidence that the retained sequence is complete scanner data.

Checksum validation should be used as positive classification evidence rather
than as a universal requirement. The product database also supports custom and
short internal codes that may not use a retail checksum. The implementation
must preserve those workflows explicitly.

### Focus and UI Routing Remain Separate

The scanner listener should determine whether a complete key sequence resembles
a scan. `BarcodeManager` should continue determining whether that scan is
allowed in the current UI context and where it should be routed. The buffering
redesign should not weaken:

- protected manual fields;
- modal scanner blocking;
- dialog barcode overrides;
- held-receipt protections;
- scanner Enter suppression;
- cleanup of native HID characters that reach focused widgets.

## Stronger Hardware-Assisted Options

### Unique Scanner Prefix

If supported by the Honeywell scanner, configure a prefix that is unlikely to
come from ordinary typing, followed by the existing Enter suffix. For example:

```text
<F9>5028197552916<Enter>
```

The application could begin a scanner session only after receiving the prefix.
This greatly reduces ambiguity between scanner and keyboard input and can allow
more tolerant internal timing. The chosen prefix must not conflict with POS
shortcuts, and scanner configuration must be consistent across deployed units.

### Serial/COM Mode

Serial/COM mode provides a dedicated scanner data channel rather than injecting
keyboard events. It offers the clearest separation between manual typing and
scanner data and avoids focused-widget character leakage. It also requires
device configuration, port discovery/reconnection handling, deployment support,
and a different input integration, so it is a larger operational change.

## Proposed Implementation Order

If the current `0.10`-second mitigation later proves insufficient, consider the
following sequence:

1. Add temporary diagnostic capture of candidate characters and inter-key
   intervals without recording unrelated manual-field contents.
2. Use `time.monotonic()` for duration measurement.
3. Retain the entire printable candidate until Enter.
4. Introduce separate fast-key and abandonment thresholds.
5. Classify using the proportion of fast intervals and total duration.
6. Add EAN/UPC length and checksum evidence while retaining explicit support
   for custom/internal codes.
7. Re-run focus, modal, dialog-override, and leak-cleanup tests.
8. Consider a scanner prefix if supported and operationally manageable.
9. Consider Serial/COM mode only if HID ambiguity remains unacceptable.

## Test Plan for a Future Change

### Physical Scanner Tests

- Scan several known EAN-13 products at least 50 times each.
- Vary the delay between trigger pulls.
- Perform isolated scans and rapid consecutive scans.
- Repeat while the POS is idle and under representative application load.
- Confirm every accepted code exactly matches the printed barcode.
- Confirm existing products only add or increment and never open ADD.
- Scan unknown but valid barcodes and confirm the intended ADD workflow.
- Scan damaged or poorly positioned labels and confirm they do not create
  misleading partial accepted codes.

### Keyboard and Classification Tests

- Type slowly in normal editable fields and press Enter.
- Type rapidly in normal editable fields and press Enter.
- Type valid short internal product codes through their intended workflow.
- Confirm manual text is not routed to the sales table as a scan.
- Confirm one artificially delayed scanner digit does not discard the prefix.
- Confirm an idle period beyond the abandonment timeout starts a new session.
- Confirm candidates shorter than the scanner minimum are not emitted.

### UI Routing Regression Tests

- Scan on the main sales-table surface.
- Scan with each protected manual field focused.
- Scan in allowed product-code fields in scanner-aware dialogs.
- Scan in forbidden fields in those dialogs.
- Scan while a generic scanner-blocked modal is open.
- Confirm the trailing Enter never submits an unrelated form or button.
- Confirm rejected scans restore or clean leaked HID text as designed.

### Format Tests

- Valid and invalid EAN-13 checksums.
- Valid and invalid UPC-A checksums.
- Other scanner symbologies actually enabled in production.
- Alphanumeric and short internal codes.
- Leading-zero codes, ensuring they remain strings and retain their zeros.

## Acceptance Criteria

A future redesign should be considered successful when:

- a single moderate event delay cannot remove an already received prefix;
- repeated valid scans always produce the exact full code;
- existing-product scans do not enter the missing-product ADD workflow;
- ordinary manual typing is not routed as a barcode;
- short internal-code workflows continue to operate;
- focus, modal, override, held-receipt, Enter-suppression, and cleanup behavior
  remain correct;
- timing constants and hardware assumptions are documented and verified on the
  production POS environment.

## Current Recommendation

Retain `SCANNER_KEY_INTERVAL_SECONDS = 0.05` because production testing found
that `0.10` interfered with fast manual keyboard input. Treat suffix-only product codes or intermittent unexpected ADD
dialogs as possible scanner-buffer timing symptoms. Before increasing the
threshold again, compare repeated output in a plain text editor and the scanner
test utility, then collect inter-key timing evidence. Adopt the session-based
algorithm only with the physical, keyboard, and UI regression testing described
above.
