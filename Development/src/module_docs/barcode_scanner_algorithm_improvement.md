# Barcode Scanner Retained-Candidate Buffering

## Purpose

The production HID scanner occasionally delivered one character more than
`0.05` seconds after the preceding character. The former algorithm treated that
single gap as a candidate boundary, discarded the already received prefix, and
could emit a valid-looking suffix. A lookup for that suffix then correctly
opened Product Management because the truncated code did not exist.

The implemented retained-candidate design prevents one moderate scheduling or
HID delivery delay from removing a barcode prefix. It also avoids returning the
global fast-key threshold to `0.10`, which production testing showed could make
rapid keyboard entry hang or lose characters.

## Implemented Algorithm

`modules/devices/scanner.py` maintains one candidate session:

1. The first printable character starts the candidate.
2. Every later printable character is appended, including characters arriving
   above the short fast-key threshold.
3. Inter-key gaps are recorded as timing evidence.
4. Enter completes and classifies the entire candidate.
5. Only scanner-like candidates emit `barcode_scanned`.
6. An unfinished candidate is abandoned only after the longer inactivity
   timeout.

Elapsed intervals use `time.monotonic()` so wall-clock corrections cannot alter
duration measurements.

## Separate Timing Decisions

The constants in `config.py` have distinct responsibilities:

- `SCANNER_KEY_INTERVAL_SECONDS = 0.05`: identifies individual scanner-fast
  gaps and drives short-lived UI Enter protection. It does not reset the
  candidate.
- `SCANNER_CANDIDATE_INACTIVITY_SECONDS = 0.75`: abandons an unfinished
  candidate and permits a genuinely new one to start.
- `SCANNER_MAX_AVERAGE_GAP_SECONDS = 0.10`: maximum average character gap used
  by final classification.
- `SCANNER_MIN_FAST_GAP_RATIO = 0.70`: required proportion of gaps at or below
  the fast threshold for short/custom codes.
- `SCANNER_LONG_CODE_MIN_LENGTH = 8`: longer sequences may qualify from a
  scanner-like average even when Windows delays several individual events.
- `SCANNER_UI_SETTLE_MS = 30`: lets pending Qt scanner-key events drain before
  restoring or finalizing a field.
- `SCANNER_UI_SUPPRESS_SECONDS = 0.90`: protects the UI from a scanner's Enter
  suffix after scanner-fast activity.

This policy preserves short internal product-code support while allowing a
normal long barcode to survive one or more moderate delivery delays. Manual
text shorter than the long-code boundary must show a clear majority of 0.05
second gaps before it can be classified as scanner input.

## UI Behaviour

`BarcodeManager` remains responsible for focus and routing policy. The scanner
listener only classifies the completed key sequence.

Printable characters are no longer speculatively swallowed merely because the
latest gap is fast. They may briefly reach an editable widget while the input
is ambiguous. If Enter confirms a scan, `BarcodeManager` restores non-product
code fields to their pre-scan value after the short settling delay.
Product-code overrides reapply the full barcode after the same delay and do
not run leak cleanup against that authoritative value.

Qt's event filter captures the pre-scan value before inserting the first
candidate character; listener-side focus capture remains a fallback.

Enter/Return protection still begins during scanner-fast activity because
waiting for final classification would allow the scanner suffix to activate a
button or submit a form. Very fast manual typing can therefore still briefly
cause Enter suppression, but its printable characters remain intact.

Existing routing protections remain unchanged:

- protected quantity and payment fields reject scans;
- scanner-blocked modals do not route scans to the cart;
- dialog overrides accept scans only in product-code fields;
- `HOLD_LOADED` prevents scanner additions to the active sales table;
- successful main-window scans return focus to `salesTable`.

## Diagnostics

The independent `live_logs/barcode_scanner_trace.log` now distinguishes:

- `candidate_rejected`: Enter completed a sequence that failed length, timing,
  or inactivity classification;
- `candidate_abandoned`: a new printable character arrived after the 0.75
  second inactivity boundary;
- normal accepted candidates: counted in the periodic summary rather than
  logged individually.

Rejected-candidate records include average and maximum gap, fast-gap count and
ratio, and the classification reason. The trace remains separate from
`error.log` and from the Diagnostics menu.

## Production Test Checklist

- Repeatedly scan known 12/13-digit products and confirm the exact full code is
  always added or incremented.
- Scan under representative POS load and rapidly repeat trigger pulls.
- Confirm unknown full barcodes open the intended ADD workflow.
- Type slowly and rapidly in ordinary dialog fields; verify no printable
  characters hang or disappear.
- Verify short internal codes still scan successfully.
- Scan with focus in quantity, CASH, NETS, PAYNOW, VOUCHER, and TENDER fields;
  verify values restore and the cart is unchanged.
- Test allowed product-code fields, forbidden dialog fields, generic modals,
  and the `HOLD_LOADED` state.
- Confirm the scanner Enter suffix does not activate PAY, CLOSE, or another
  focused/default button.

## Known HID Limitation

Without a scanner-specific prefix or a dedicated serial/COM channel, Windows
presents scanner and keyboard input as the same events. A long barcode-length
string typed manually at scanner-like speed can therefore remain ambiguous.
The timing classifier and focus/routing protections reduce this risk but cannot
prove device identity. A configured unique scanner prefix is the preferred
future hardening if the hardware and deployment process support it.

Rapid repeated scans into an ordinary non-barcode dialog field may overlap its
candidate snapshots and deferred restoration timers, leaving scanner text in
that field. Isolated rejected scans restore correctly. Repeated scanning into a
non-scan field is outside the supported cashier workflow and is accepted as a
limitation of the HID design.
