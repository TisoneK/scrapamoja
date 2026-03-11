# Feature Proposal: Auto Encoding Detection
**Project:** Scrapamoja  
**Feature ID:** SCR-004  
**Status:** Proposed  
**Author:** TisoneK  
**Date:** March 2026  

---

## 1. Summary

Add automatic detection of the encoding format used in a captured API response, and route the raw bytes to the correct decoder without requiring manual configuration. Scrapamoja should be able to receive any response — JSON, gzip-compressed data, Brotli-compressed data, Protocol Buffer binary, or plain text — and identify what it is before attempting to decode it.

---

## 2. Problem

Not all API responses are JSON. Modern web platforms use a variety of encoding and compression formats to reduce bandwidth and improve performance:

- **JSON** — human-readable, the most common API format
- **Gzip** — compressed JSON or text, declared in the `Content-Encoding` header
- **Brotli** — a newer compression format, also declared in headers
- **Protocol Buffers (protobuf)** — a binary serialisation format used by Google and many large platforms
- **Plain text** — uncommon for APIs but present in some cases

The problem is that response headers are not always reliable. A response can claim to be `gzip` in its `Content-Encoding` header while the actual bytes are protobuf binary — as observed directly during the AiScore investigation. Trusting the header and attempting gzip decompression produces an error. Trying each format manually wastes time and produces fragile site-specific code.

Currently, Scrapamoja has no encoding detection layer. Each site module must handle decoding manually, leading to duplicated logic and brittle implementations.

---

## 3. Opportunity

Encoding formats have identifiable signatures in their raw bytes. By inspecting the first few bytes of a response — known as a "magic number" check — combined with header hints and content type, it is possible to reliably identify the encoding before attempting to decode it.

A centralised encoding detector means:

- Site modules never need to handle encoding themselves
- New encodings can be added in one place and immediately benefit all modules
- Failures produce clear, actionable error messages ("detected protobuf, no decoder registered") rather than cryptic byte errors

---

## 4. What This Feature Adds

- An **encoding detector** that inspects raw response bytes and headers to identify the format
- Support for detecting: JSON, gzip, Brotli, Protocol Buffers, and plain text
- A decoder registry that maps detected encodings to the appropriate decoder
- Clear error messages when an encoding is detected but no decoder is available
- A fallback mode that extracts readable strings from unrecognised binary formats
- Integration with the network interception layer so all captured responses pass through detection automatically

---

## 5. Who Benefits

- Every site module that deals with any response format other than plain JSON
- Developers adding new site modules — they get correct decoding for free without writing encoding logic
- The AiScore module specifically, where the response claims gzip but is actually protobuf binary

---

## 6. Discovery Context

This feature need was revealed in stages during the AiScore investigation:

1. `response.json()` failed with a UTF-8 decode error — the response was not plain JSON
2. The `Content-Encoding` header said `gzip` — but `gzip.decompress()` failed with "Not a gzipped file"
3. `zlib`, `zlib-wbits`, and `brotli` all failed
4. `latin-1` decoding succeeded but produced garbled binary mixed with readable strings
5. Hex dump analysis revealed the bytes were Protocol Buffer binary — a format with no standard header declaration

This sequence of failures — and the time spent working through each one — is exactly the problem this feature solves. An encoding detector would have identified protobuf from the magic bytes and routed to the correct decoder immediately.

---

## 7. Success Criteria

- The detector correctly identifies JSON, gzip, Brotli, protobuf, and plain text from raw bytes
- Correct identification occurs even when headers report an incorrect encoding
- All intercepted responses pass through the detector automatically
- Unrecognised formats trigger the string extraction fallback rather than a crash
- Adding a new encoding type requires changes in one place only
- Existing site modules are unaffected

---

## 8. Out of Scope

- Protobuf schema parsing and structured field extraction (covered by a separate feature)
- Compression of outgoing requests (not a current use case)
- Streaming response decoding (future consideration)

---

*Proposal prepared March 2026.*
