# Feature Proposal: Protobuf Binary Decoding
**Project:** Scrapamoja  
**Feature ID:** SCR-005  
**Status:** Proposed  
**Author:** TisoneK  
**Date:** March 2026  

---

## 1. Summary

Add the ability for Scrapamoja to decode Protocol Buffer (protobuf) binary responses from API endpoints into readable, structured Python data. This unlocks a class of high-value data sources — particularly platforms built on Google infrastructure or enterprise backends — that use protobuf instead of JSON as their wire format.

---

## 2. Problem

Protocol Buffers is a binary serialisation format created by Google. Unlike JSON, which is human-readable text, protobuf encodes data as compact binary — significantly smaller and faster to transmit, but completely unreadable without a decoder.

Many major platforms use protobuf for their internal APIs, including sports data providers, mapping services, financial platforms, and any product built heavily on Google Cloud infrastructure. When Scrapamoja intercepts a protobuf response, the raw bytes are meaningless without a way to decode them.

The challenge is that protobuf decoding normally requires a `.proto` schema file — a definition of the data structure. Without the schema, the bytes cannot be formally decoded into named fields. However, schema files are internal to the platform and never publicly exposed.

---

## 3. Opportunity

There are two viable approaches to protobuf decoding without a schema:

**Approach A — Heuristic String Extraction**  
Protobuf binary always contains readable strings embedded between binary framing bytes. These strings — team names, league names, match IDs, URLs — can be extracted using byte pattern matching even without the schema. Numeric values (odds, scores, totals) appear as IEEE float or varint sequences adjacent to the strings. This approach produces usable data without any schema knowledge.

**Approach B — Dynamic Field Mapping**  
Tools like `protobuf-inspector` can analyse binary protobuf data and produce a generic field map — field numbers, types, and raw values — without a schema. By observing multiple responses and correlating field numbers with known values (e.g. a field that always contains a known team name), a working schema can be reverse-engineered over time.

Scrapamoja should implement Approach A as the primary method and Approach B as an advanced option for contributors who want to build more structured decoders.

---

## 4. What This Feature Adds

- A **protobuf decoder** that extracts readable strings and numeric sequences from binary protobuf data without requiring a schema file
- Output structured as a Python dictionary with extracted strings grouped by proximity to numeric values
- A separate **schema-based decoder path** for use when a reverse-engineered `.proto` file is available
- Integration with the encoding detection layer so protobuf responses are automatically routed to this decoder
- Per-site decoder configuration allowing site modules to specify field mappings as they are discovered
- Developer tooling to inspect raw protobuf bytes and identify field patterns during module development

---

## 5. Who Benefits

- Developers building modules for any platform that uses protobuf APIs
- The AiScore module specifically — confirmed to return protobuf binary for all match and odds data
- Any future module targeting Google-backed or enterprise data platforms

---

## 6. Discovery Context

Discovered during the AiScore integration sprint. After the encoding detector ruled out JSON, gzip, and Brotli, a hex dump of the raw response bytes was analysed:

```
Raw bytes preview: b'z\xb0\xcd\x03\n\xba\x01\n\x0f48vrqw9s3ij...'
Content-Encoding: gzip  ← incorrect header
Content-Type: application/octet-stream  ← the real clue
```

The `application/octet-stream` content type, combined with the binary byte pattern, identified the format as protobuf. Applying `latin-1` decoding revealed readable strings (team names, league names, match IDs, country codes) embedded within binary framing — confirming that heuristic string extraction is viable as a first-pass decoder.

The extracted data included:

- League names (NBA, Euroleague, Korean Basketball League, etc.)
- Team names (Golden State Warriors, Brooklyn Nets, Cleveland Cavaliers, etc.)
- Match IDs (alphanumeric strings ~15 characters)
- Numeric sequences consistent with odds values (0.83, 0.91, 225.5, etc.)

---

## 7. Success Criteria

- The decoder extracts all readable strings from a protobuf binary response
- Numeric values adjacent to strings are extracted and associated correctly
- Output is a structured Python dictionary usable by the site module
- The decoder handles malformed or partially readable protobuf gracefully without crashing
- Schema-based decoding works correctly when a `.proto` mapping is provided
- The AiScore module successfully produces team names, match IDs, and odds values using this decoder

---

## 8. Out of Scope

- Formal protobuf schema reverse engineering (a manual research task, not a code feature)
- Encoding detection (covered by a separate feature)
- Decoding protobuf streams or chunked transfers (future consideration)

---

*Proposal prepared March 2026.*
