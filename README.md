# Mithril Interop

Native host adapters for Mithril mission models. This repository separates XML
custody and schema validation, DIS Link 16 simulation transport, and actual HLA
RTI services from the language's pure typed IR and model admission.

Implemented and locally exercised:

- Native XML import, byte-identical re-export, guarded native edits, explicit
  XPath projections and offline SHA-256-pinned XSD 1.1 validation. The public
  OpenC2SIM schema accepts the included command fixture and rejects invalid codes.
- SISO-STD-002-2021 DIS 7 Transmitter and fixed-format Signal PDU codecs, opaque
  75-bit J words, actual allowlisted UDP send/receive and loopback read-back.
  The generated PDUs are also parsed by independent OpenDIS code in the tests.
- IEEE 1516e connect/create/join, publish/subscribe, name reservation, object
  registration/attribute update, interaction send/receive, regulation,
  constrained time, requests/grants, resign/destroy/disconnect using **OpenRTI**.
  The in-process RTI exercise passed. A separate TCP `rtinode` test is provided;
  its handshake timed out on this macOS host and remains an unverified gate.

## Run

Requires Python 3.11+, CMake, Git and a C++17 compiler. All dependencies and
builds are local to this checkout; no global RTI installation is required.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
./scripts/build-hla.sh
.venv/bin/python scripts/fetch-c2sim-schema.py
.venv/bin/mithril-interop link16-loopback
.venv/bin/mithril-interop hla-exercise
.venv/bin/mithril-interop xml-import examples/c2sim-command.xml \
  --standard c2sim --version OpenC2SIM-SMX-LOX-1.0.1 \
  --schema-manifest .cache/schemas/c2sim/manifest.json
.venv/bin/python -m unittest discover -s tests -v
```

Optional independent DIS validation: `pip install opendis==1.0`. It is a test
dependency, not part of the adapter runtime. Python 3.11/3.12 avoids compiling
its older NumPy dependency on newer Python versions.

Mithril's `mission-native/invoke!` calls the one-request JSON RPC using an
explicit Python executable and adapter checkout. The standalone language entry
point is `bin/mithril-interop.cljk`. Projected XML records must also pass
`mission/compile-document`; native XML parsing does not bypass typed admission.

## Boundaries

This is working native transport and RTI code, with deliberately explicit
subsets. It is not a claim of full DoD/NATO accreditation or complete standards
conformance. Link 16 support is **simulation over DIS/UDP**, TSA level 0, MTI 0,
SISO version 2021. There is no RF waveform, terminal crypto, TDMA scheduling,
high-fidelity network entry, or interpretation/generation of tactical J-series
field meanings. The XML adapter keeps data it does not project. An XSD receipt
records validation against the selected schema bytes, not ontology equivalence
or command execution. The included FOM is a Mithril FOM, not an RPR/Link 16 FOM.

For DM2, C-BML, JC3IEDM and MIM native XML, supply the exact version's authorized
schema bundle and mapping profile. The host supports this path but those
complete official schema bundles have not been obtained or tested here. The
MSDL example demonstrates native parsing/projection and is not asserted to be
XSD-conformant. C2SIM has an independently pinned public-schema test.

See [the design and adapter contracts](docs/design.md) for source formats,
schema manifests, RPC operations, HLA services and remaining protocol work.
