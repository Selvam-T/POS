
# PayNow Dynamic QR Code Generator (SGQR / EMVCo)

## 1. Purpose

This guide explains how a POS application generates a **PayNow Dynamic QR code** so that when a customer scans it with any Singapore banking app, the **payment page opens with the amount already filled**.

The QR code must follow the **SGQR / PayNow format**, which is based on the **EMVCo Merchant Presented QR specification**.

This document summarizes the key concepts and implementation considerations in a clear and practical order.

---

# 2. Standard QR vs PayNow QR

## Standard QR

A normal QR code simply contains any text or data.

Example:

MERCHANT=ABC SHOP  
AMOUNT=12.50  
UEN=201940352W

This works for normal QR readers but **banking apps will reject it** because it does not follow the payment specification.

Typical error:

QR Code not valid

---

## PayNow / SGQR QR

Singapore payment QR codes follow a structured standard called:

**EMVCo Merchant Presented QR**

The payload inside the QR must be encoded in **TLV format**:

Tag + Length + Value

Example concept:

54 05 12.50

Meaning:

Tag: 54  
Length: 05  
Value: 12.50

This structure allows bank apps to recognize the QR as a **payment request**.

---

# 3. SGQR Structure

Singapore uses a unified QR framework called **SGQR**.

Hierarchy:

EMVCo QR Standard  
↓  
SGQR specification  
↓  
PayNow QR

A valid PayNow QR must follow the **EMVCo specification**.

---

# 4. Static QR vs Dynamic QR

## Static QR

Contains only the merchant identifier.

Customer manually enters the payment amount.

Example content:

merchant UEN

Pros:

- reusable QR

Cons:

- customer must type the amount
- higher chance of mistakes

---

## Dynamic QR

Contains:

- merchant identifier
- transaction amount
- transaction reference

Example concept:

UEN  
Amount  
Receipt reference

When scanned:

bank app opens  
amount already filled

Dynamic QR is the **standard method used by POS systems**.

---

# 5. Merchant Information Required

Minimum merchant data required:

Merchant Name: Anumani Trading Pte Ltd  
Merchant City: Singapore  
Country Code: SG  
Currency: SGD  
PayNow Proxy Type: UEN  
PayNow Proxy Value: 201940352W  

Important:

The **UEN must be registered with the bank as a PayNow Corporate proxy**.

Merchant Category Code (MCC) is usually:

0000

---

# 6. Transaction Information

The POS system supplies transaction data for the dynamic QR.

Amount: calculated by POS  
Reference: receipt number

Example:

Amount = 12.50  
Reference = 20260312-0001

The reference allows the merchant to **match incoming payments to receipts**.

---

# 7. QR Validity Period

Dynamic QR codes normally expire.

Typical industry practice in Singapore:

POS terminal: ~5 minutes  
Online checkout: ~5 minutes  
Invoice QR: hours or days  
Static QR: no expiry

Most POS systems use:

5 minutes

This prevents customers from paying an **old transaction QR**.

---

# 8. EMV Payload Fields

The QR payload contains several mandatory fields.

00 – Payload format indicator  
01 – Dynamic QR flag  
26 – Merchant account information  
52 – Merchant category code  
53 – Currency  
54 – Amount  
58 – Country code  
59 – Merchant name  
60 – Merchant city  
62 – Transaction reference  
63 – CRC checksum

Example simplified structure:

000201  
010212  
26...  
52040000  
5303702  
540512.50  
5802SG  
59MERCHANT NAME  
60SINGAPORE  
62REFERENCE  
6304CRC  

---

# 9. PayNow Merchant Template

Inside Tag **26** is the PayNow-specific merchant block.

It contains:

00 – SG.PAYNOW identifier  
01 – proxy type  
02 – proxy value  
03 – editable flag  
04 – expiry

Conceptual example:

SG.PAYNOW  
UEN  
201940352W  
expiry date

This tells the bank that the QR is a **PayNow payment request**.

---

# 10. Currency Code

EMVCo requires **numeric currency codes**.

Singapore Dollar:

702

Not:

SGD

---

# 11. CRC Checksum

Every EMV QR ends with a **CRC checksum**.

Example ending:

6304ABCD

If the CRC is incorrect:

bank app rejects QR

The CRC ensures the payload has not been corrupted.

---

# 12. QR Image Generation

Once the payload string is built, it is converted into a QR image.

Typical libraries used:

- qrcode
- Pillow

Important settings:

- high error correction
- adequate border around QR

---

# 13. PayNow Branding

To match PayNow style, QR modules can use the PayNow purple color.

Common purple used:

#8F1F7C

Background should remain **white** for scanning reliability.

---

# 14. Logo Overlay

Most payment QR displays include the **PayNow logo in the center**.

Guidelines:

- logo size ≤ ~15% of QR width
- place logo on a white plate
- use high QR error correction

Structure:

QR modules  
↓  
white rounded plate  
↓  
PayNow logo

---

# 15. Visual Layout Improvements

Professional payment displays typically include:

- white margin around QR
- rounded white card background
- PayNow logo in center
- expiry text below QR

Layout example:

white card  
↓  
QR code  
↓  
PayNow logo  
↓  
Valid till text

These are **visual improvements only** and do not affect the payment payload.

---

# 16. File Paths for Production

Avoid hardcoded absolute paths.

Use **relative paths from the application directory** so the software works on any computer.

Example structure:

Project  
 ├ assets  
 │   └ images  
 │       └ paynow_logo.png  
 └ modules  
     └ payment  

---

# 17. Overall QR Generation Flow

Typical POS process:

1 POS calculates transaction amount  
2 POS generates receipt number  
3 application builds EMV payload  
4 CRC checksum is calculated  
5 payload converted into QR image  
6 logo and styling applied  
7 QR displayed to customer  

Customer experience:

customer scans QR  
bank app opens payment page  
amount already filled  
customer confirms payment  

---

# 18. Summary

Generating a working PayNow QR involves two layers.

Payment Layer:

Correct EMVCo structured payload containing:

- merchant proxy (UEN)
- amount
- transaction reference
- CRC

Visual Layer:

Rendering the QR with:

- logo overlay
- proper colors
- clear margins
- readable layout

When both layers are implemented correctly, the QR:

- scans reliably
- works across Singapore banking apps
- looks professional on POS displays.
