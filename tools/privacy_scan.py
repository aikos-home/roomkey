"""Privacy scan: run before every push.

    python tools/privacy_scan.py --denylist PATH [--root CHECKOUT]
    (or set ROOMKEY_DENYLIST=PATH; KLINGELBOX_DENYLIST works too)

Taken from the sibling project Klingelbox (github.com/aikos-home/intercom, MIT) with two
additions: RoomKey's documented example entity ids, its own `roomkey_test_*` DEV stand-ins and
service verbs (input_boolean.turn_on …) are allowed, and packed files are opened (see below).

The denylist is a private text file that is never committed. One term per line:
  - plain words match case-insensitively as whole words, "_" counts as a word break
    ("anna" does not hit "Johanna", but hits "anna_notes.txt");
  - terms with punctuation (".lan", "10.0.") match as plain substrings;
  - lines starting with "!" are allowed phrases that are blanked out before matching
    (e.g. a public repository URL that contains a name);
  - "#" starts a comment.

Built-in checks, no denylist needed: private IPv4 addresses, MAC addresses, e-mail
addresses, Home Assistant entity ids and GPS positions in photo metadata.

Binary files are scanned as Latin-1 text, so names inside STEP headers are found too.
Packed data is opened first and only the parts that can hold text are read; compressed
bytes look like random words and would only give false alarms:
  - ZIP containers (FreeCAD .FCStd, .3mf, .gcode.3mf, gerber .zip): the file names and
    every member, nested containers included, reported as `container!member`;
  - PNG: every chunk except the pixel data, zTXt/iTXt/iCCP decompressed;
  - JPEG: every segment (EXIF, XMP, comments) but not the image data;
  - PDF: zlib streams decompressed, other streams (embedded images) skipped;
  - binary STL: the 80-byte header only.
A file that cannot be opened counts as a finding: check it by hand.

Exit code 1 if anything is found.
"""
import argparse
import io
import os
import re
import subprocess
import sys
import zipfile
import zlib

BUILTIN = {
    "private IPv4": re.compile(r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),
    "MAC address": re.compile(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b"),
    "e-mail address": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "HA entity id": re.compile(r"\b(?:binary_sensor|input_boolean|input_text|input_number|input_select|"
                               r"automation|device_tracker|person|zone|notify)\.[a-z0-9_]{3,}\b"),
}
ALLOWED_EMAILS = {"noreply@anthropic.com"}
# Generic defaults documented in RoomKey's configs — examples, not anyone's real entities.
ALLOWED_ENTITY_IDS = {"binary_sensor.doorbell_button", "binary_sensor.doorstation_call_active",
                      # aikos contract entities (aikos features/sprechen.md §4b A), the same in every home
                      "binary_sensor.aikos_front_door", "binary_sensor.aikos_quiet_hours", "sensor.aikos_people",
                      "sensor.aikos_call_log"}
ALLOWED_OBJECT_PREFIXES = ("roomkey_test_",            # RoomKey's own DEV stand-ins
                           "aikos_")                    # aikos's own entities (same rule as aikos-home/aikos)
SERVICE_VERBS = {"turn_on", "turn_off", "toggle", "reload", "trigger", "select_option", "set_value"}
GPS = "GPS position in photo metadata"


def allowed_entity(eid):
    obj = eid.split(".", 1)[1]
    return eid in ALLOWED_ENTITY_IDS or obj.startswith(ALLOWED_OBJECT_PREFIXES) or obj in SERVICE_VERBS


def repo_files(root):
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                         cwd=root, capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f]


def load_denylist(path):
    terms, allowed = [], []
    for line in open(path, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("!"):
            allowed.append(line[1:].strip().lower())
        else:
            terms.append(line.lower())
    return terms, allowed


def exif_has_gps(tiff):
    """True if an EXIF block (TIFF layout) has a GPS sub-directory with a latitude in it."""
    order = {b"II": "little", b"MM": "big"}.get(tiff[:2])
    if not order:
        return False
    u16 = lambda p: int.from_bytes(tiff[p:p + 2], order)
    u32 = lambda p: int.from_bytes(tiff[p:p + 4], order)
    ifd = u32(4)
    for i in range(min(u16(ifd), 500)):
        if u16(ifd + 2 + 12 * i) == 0x8825:                 # GPSInfo
            gps = u32(ifd + 2 + 12 * i + 8)
            return any(u16(gps + 2 + 12 * k) == 2 for k in range(min(u16(gps), 100)))   # GPSLatitude
    return False


def png_parts(raw):
    """Every chunk but IDAT (pixel data), compressed text decompressed."""
    out, gps, pos = [], False, 8
    while pos + 12 <= len(raw):
        n = int.from_bytes(raw[pos:pos + 4], "big")
        kind, data = raw[pos + 4:pos + 8], raw[pos + 8:pos + 8 + n]
        pos += 12 + n
        if kind == b"IDAT":
            continue
        if kind in (b"zTXt", b"iCCP"):                       # keyword 0 method zlib-data
            key, _, rest = data.partition(b"\0")
            data = key + b"\0" + zlib.decompress(rest[1:])
        elif kind == b"iTXt":                                # keyword 0 flag method language 0 keyword 0 text
            key, _, rest = data.partition(b"\0")
            flag, rest = rest[:1], rest[2:]
            lang, _, rest = rest.partition(b"\0")
            tkey, _, text = rest.partition(b"\0")
            data = b"\0".join([key, lang, tkey, zlib.decompress(text) if flag == b"\1" else text])
        elif kind == b"eXIf":
            gps = gps or exif_has_gps(data)
        out.append(kind + b" " + data)
        if kind == b"IEND":
            out.append(raw[pos:])                            # anything appended after the image
            break
    return b"\n".join(out), gps


def jpeg_parts(raw):
    """Every segment (EXIF, XMP, comments, tables) without the entropy-coded image data."""
    out, gps, pos = [], False, 2
    while pos + 4 <= len(raw):
        if raw[pos] != 0xFF:                                 # image data: jump to the next marker
            pos = raw.find(b"\xff", pos + 1)
            if pos < 0:
                break
            continue
        m = raw[pos + 1]
        if m == 0xFF:                                        # fill byte
            pos += 1
            continue
        if m in (0x00, 0x01) or 0xD0 <= m <= 0xD7:           # stuffed byte, TEM, restart markers
            pos += 2
            continue
        if m == 0xD9:                                        # end of image
            out.append(raw[pos + 2:])
            break
        n = int.from_bytes(raw[pos + 2:pos + 4], "big")
        data = raw[pos + 4:pos + 2 + n]
        if m == 0xE1 and data.startswith(b"Exif\0\0"):
            gps = gps or exif_has_gps(data[6:])
        out.append(data)
        pos += 2 + n
    return b"\n".join(out), gps


def pdf_text(raw):
    """The file with every zlib stream decompressed and every other stream left out."""
    def inflate(m):
        try:
            return b"stream\n" + zlib.decompressobj().decompress(m.group(1)) + b"\nendstream"
        except zlib.error:
            return b"stream\nendstream"
    return re.sub(rb"stream\r?\n(.*?)endstream", inflate, raw, flags=re.S)


def binary_stl(raw):
    return len(raw) >= 84 and len(raw) == 84 + 50 * int.from_bytes(raw[80:84], "little")


def pieces(label, raw, depth=0):
    """Yield (label, bytes to scan) for a file, or (label, str) for a finding that is not text."""
    try:
        if raw[:4] == b"PK\x03\x04":
            if depth >= 4:
                raise ValueError("containers nested too deep")
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                yield label + " (file names)", "\n".join(z.namelist()).encode("utf-8") + b"\n" + z.comment
                for info in z.infolist():
                    if not info.is_dir():
                        yield from pieces(f"{label}!{info.filename}", z.read(info), depth + 1)
        elif raw[:8] == b"\x89PNG\r\n\x1a\n" or raw[:3] == b"\xff\xd8\xff":
            text, gps = (png_parts if raw[:1] == b"\x89" else jpeg_parts)(raw)
            if gps:
                yield label, GPS
            yield label, text
        elif raw[:5] == b"%PDF-":
            yield label, pdf_text(raw)
        elif binary_stl(raw):
            yield label, raw[:80]
        else:
            yield label, raw
    except Exception as e:
        yield label, f"could not be opened ({type(e).__name__}: {e}), check it by hand"


def scan(label, raw, patterns, allowed):
    hits = 0
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    low = text.lower()
    for a in allowed:
        low = low.replace(a, " " * len(a))
    for t, rx in patterns:
        for m in rx.finditer(low):
            line = low.count("\n", 0, m.start()) + 1
            print(f"{label}:{line}: denylisted term '{t}'")
            hits += 1
    for name, rx in BUILTIN.items():
        for m in rx.finditer(text):
            if name == "e-mail address" and m.group(0).lower() in ALLOWED_EMAILS:
                continue
            if name == "HA entity id" and allowed_entity(m.group(0)):
                continue
            line = text.count("\n", 0, m.start()) + 1
            print(f"{label}:{line}: {name}: {m.group(0)}")
            hits += 1
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--denylist", default=os.environ.get("ROOMKEY_DENYLIST") or os.environ.get("KLINGELBOX_DENYLIST"))
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    help="git checkout to scan (default: this one)")
    args = ap.parse_args()
    terms, allowed = ([], [])
    if args.denylist:
        terms, allowed = load_denylist(args.denylist)
    else:
        print("warning: no denylist given, running the built-in checks only")
    patterns = []
    for t in terms:
        if re.fullmatch(r"[\wÀ-ɏ]+", t):
            patterns.append((t, re.compile(r"(?<![^\W_])" + re.escape(t) + r"(?![^\W_])")))
        else:
            patterns.append((t, re.compile(re.escape(t))))
    hits = 0
    for rel in repo_files(args.root):
        path = os.path.join(args.root, rel)
        if not os.path.isfile(path):
            continue
        for label, data in pieces(rel, open(path, "rb").read()):
            if isinstance(data, str):
                print(f"{label}: {data}")
                hits += 1
            else:
                hits += scan(label, data, patterns, allowed)
    print(f"{hits} finding(s)" if hits else "clean")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
