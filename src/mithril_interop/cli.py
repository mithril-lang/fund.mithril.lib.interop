"""Standalone CLI and one-request JSON RPC for the Mithril adapter."""
import argparse
import base64
import json
import sys
from pathlib import Path
from . import Refusal
from . import native_xml as xml, link16, hla

ROOT = Path(__file__).resolve().parents[2]

def loopback():
    """Real UDP read-back, including transmitter and fixed-format Signal PDUs."""
    with link16.UDPTransport() as receiver, link16.UDPTransport(allowed_peers=[receiver.address]) as sender:
        receiver.allowed.add(sender.address)
        transmitter = link16.encode_transmitter()
        signal = link16.encode_signal([0x12345, 0x23456], network=link16.Network(npg=7, net=3))
        packets = []
        for packet in [transmitter, signal]:
            sent = sender.send(packet, receiver.address)
            received = receiver.receive()
            if received["bytesHex"] != packet.hex():
                raise Refusal("UDP binary read-back mismatch")
            packets.append({"sentBytes": sent, "received": received["decoded"]})
        return {"transport": "udp-loopback", "binaryReadBack": True,
                "tsaLevel": 0, "rfEffects": False, "packets": packets}

def rpc(request):
    operation = request.get("operation")
    if operation == "xml-import":
        return xml.import_xml(base64.b64decode(request["bytesBase64"], validate=True),
                              request["standard"], request["version"], request.get("schemaManifest"))
    if operation == "xml-export":
        return {"bytesBase64": base64.b64encode(xml.export_xml(request["artifact"])).decode()}
    if operation == "xml-patch":
        return xml.patch_xml(request["artifact"], request["patches"], request.get("schemaManifest"))
    if operation == "xml-project":
        return xml.project(request["artifact"], request["profile"], request.get("strict", False))
    if operation == "link16-encode":
        words = [int(word, 16) for word in request["wordsHex"]]
        return {"bytesHex": link16.encode_signal(words, link16.Radio(**request.get("radio", {})),
                                                  link16.Network(**request.get("network", {})),
                                                  jtids_header=request.get("jtidsHeader", 0)).hex()}
    if operation == "link16-decode":
        return link16.UDPTransport.decode(bytes.fromhex(request["bytesHex"]))
    if operation == "link16-loopback":
        return loopback()
    if operation == "link16-send":
        peer = tuple(request["peer"])
        with link16.UDPTransport(tuple(request.get("bind", ["127.0.0.1", 0])), request["allowedPeers"]) as transport:
            count = transport.send(bytes.fromhex(request["bytesHex"]), peer)
        return {"sentBytes": count, "peer": list(peer), "deliveryConfirmed": False, "rfEffects": False}
    if operation == "link16-receive":
        with link16.UDPTransport(tuple(request["bind"]), request["allowedPeers"], request.get("timeout", 2)) as transport:
            return transport.receive()
    if operation == "hla-exercise":
        return hla.exercise(request.get("executable", ROOT / "build/native/mithril-hla"),
                            request.get("fom", ROOT / "examples/mithril-fom.xml"),
                            endpoint=request.get("endpoint", "thread://"))
    raise Refusal("unsupported host operation")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("rpc")
    sub.add_parser("link16-loopback")
    h = sub.add_parser("hla-exercise")
    h.add_argument("--executable", default=str(ROOT / "build/native/mithril-hla"))
    h.add_argument("--fom", default=str(ROOT / "examples/mithril-fom.xml"))
    h.add_argument("--endpoint", default="thread://")
    p = sub.add_parser("xml-import")
    p.add_argument("path")
    p.add_argument("--standard", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--schema-manifest")
    p = sub.add_parser("xml-export")
    p.add_argument("artifact")
    p.add_argument("output")
    p = sub.add_parser("xml-project")
    p.add_argument("artifact")
    p.add_argument("profile")
    p.add_argument("--strict", action="store_true")
    p = sub.add_parser("xml-patch")
    p.add_argument("artifact")
    p.add_argument("patches")
    p.add_argument("--schema-manifest")
    p = sub.add_parser("link16-decode")
    p.add_argument("path")
    args = parser.parse_args()
    try:
        if args.command == "rpc":
            data = sys.stdin.buffer.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024:
                raise Refusal("RPC input limit exceeded")
            result = rpc(json.loads(data))
        elif args.command == "xml-import":
            result = xml.import_xml(Path(args.path).read_bytes(), args.standard, args.version, args.schema_manifest)
        elif args.command == "xml-export":
            data = xml.export_xml(json.loads(Path(args.artifact).read_text()))
            # Do not silently overwrite an existing native document.
            with Path(args.output).open("xb") as output:
                output.write(data)
            result = {"exported": str(Path(args.output).resolve()), "sha256": xml.sha(data)}
        elif args.command == "xml-project":
            result = xml.project(json.loads(Path(args.artifact).read_text()), json.loads(Path(args.profile).read_text()), args.strict)
        elif args.command == "xml-patch":
            result = xml.patch_xml(json.loads(Path(args.artifact).read_text()), json.loads(Path(args.patches).read_text()), args.schema_manifest)
        elif args.command == "link16-loopback":
            result = loopback()
        elif args.command == "link16-decode":
            result = link16.UDPTransport.decode(Path(args.path).read_bytes())
        else:
            result = hla.exercise(args.executable, args.fom, endpoint=args.endpoint)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (Refusal, ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
