#!/usr/bin/env python3
"""Build Mind Gym as an Android APK without the Android SDK.

Needs: JDK (javac, java, keytool) and three jars in TOOLS dir:
  android-all.jar (org.robolectric:android-all, compile classpath only)
  dx.jar          (com.jakewharton.android.repackaged:dalvik-dx)
  apksig.jar      (com.android.tools.build:apksig)
Usage: python3 build.py <tools_dir> <out.apk>
"""
import os, struct, subprocess, sys, zipfile, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOLS, OUT = sys.argv[1], sys.argv[2]
PKG = "com.mindgym.app"
VERSION_CODE, VERSION_NAME = 3, "3.0"
ANDROID_NS = "http://schemas.android.com/apk/res/android"

# ---------- Android binary XML (AXML) ----------
ATTR_IDS = {  # public framework attribute ids
    "label": 0x01010001, "icon": 0x01010002, "name": 0x01010003, "exported": 0x01010010,
    "screenOrientation": 0x0101001E, "configChanges": 0x0101001F, "minSdkVersion": 0x0101020C,
    "versionCode": 0x0101021B, "versionName": 0x0101021C, "targetSdkVersion": 0x01010270,
    "allowBackup": 0x01010280, "hardwareAccelerated": 0x010102D3,
}
T_REF, T_STR, T_INT, T_HEX, T_BOOL = 0x01, 0x03, 0x10, 0x11, 0x12


def string_pool(strings):
    offs, data = [], b""
    for s in strings:
        offs.append(len(data))
        enc = s.encode("utf-16-le")
        data += struct.pack("<H", len(s)) + enc + b"\0\0"
    while len(data) % 4:
        data += b"\0"
    hdr = 28
    start = hdr + 4 * len(strings)
    size = start + len(data)
    return struct.pack("<HHIIIIII", 0x0001, hdr, size, len(strings), 0, 0, start, 0) + \
        b"".join(struct.pack("<I", o) for o in offs) + data


def axml(tree):
    """tree = (tag, [(ns_android:bool, name, type, value)], [children])"""
    android_names, other = [], []

    def collect(n):
        tag, attrs, kids = n
        for a in attrs:
            (android_names if a[0] else other).append(a[1])
            if a[2] == T_STR:
                other.append(a[3])
        other.append(tag)
        for k in kids:
            collect(k)
    collect(tree)
    android_names = sorted(set(android_names), key=lambda x: ATTR_IDS[x])
    strings = list(android_names)
    for s in ["android", ANDROID_NS] + other:
        if s not in strings:
            strings.append(s)
    idx = {s: i for i, s in enumerate(strings)}
    NONE = 0xFFFFFFFF
    body = b""
    body += struct.pack("<HHIIIII", 0x0100, 16, 24, 1, NONE, idx["android"], idx[ANDROID_NS])

    def elem(n):
        nonlocal body
        tag, attrs, kids = n
        attrs = sorted(attrs, key=lambda a: (0, ATTR_IDS[a[1]]) if a[0] else (1, a[1]))
        size = 16 + 20 + 20 * len(attrs)
        body += struct.pack("<HHIII", 0x0102, 16, size, 1, NONE)
        body += struct.pack("<IIHHHHHH", NONE, idx[tag], 20, 20, len(attrs), 0, 0, 0)
        for is_android, name, typ, val in attrs:
            ns = idx[ANDROID_NS] if is_android else NONE
            if typ == T_STR:
                raw, data = idx[val], idx[val]
            elif typ == T_BOOL:
                raw, data = NONE, 0xFFFFFFFF if val else 0
            else:
                raw, data = NONE, val
            body += struct.pack("<IIIHBBI", ns, idx[name], raw, 8, 0, typ, data)
        for k in kids:
            elem(k)
        body += struct.pack("<HHIIIII", 0x0103, 16, 24, 1, NONE, NONE, idx[tag])
    elem(tree)
    body += struct.pack("<HHIIIII", 0x0101, 16, 24, 1, NONE, idx["android"], idx[ANDROID_NS])
    pool = string_pool(strings)
    resmap = struct.pack("<HHI", 0x0180, 8, 8 + 4 * len(android_names)) + \
        b"".join(struct.pack("<I", ATTR_IDS[n]) for n in android_names)
    total = 8 + len(pool) + len(resmap) + len(body)
    return struct.pack("<HHI", 0x0003, 8, total) + pool + resmap + body


A = lambda name, typ, val: (True, name, typ, val)
ICON_ID = 0x7F010000
manifest = ("manifest", [(False, "package", T_STR, PKG), A("versionCode", T_INT, VERSION_CODE), A("versionName", T_STR, VERSION_NAME)], [
    ("uses-sdk", [A("minSdkVersion", T_INT, 24), A("targetSdkVersion", T_INT, 34)], []),
    ("uses-permission", [A("name", T_STR, "android.permission.INTERNET")], []),
    ("uses-permission", [A("name", T_STR, "android.permission.VIBRATE")], []),
    ("queries", [], [("intent", [], [("action", [A("name", T_STR, "android.intent.action.TTS_SERVICE")], [])])]),
    ("application", [A("label", T_STR, "Mind Gym"), A("icon", T_REF, ICON_ID), A("allowBackup", T_BOOL, True), A("hardwareAccelerated", T_BOOL, True)], [
        ("activity", [A("name", T_STR, PKG + ".MainActivity"), A("exported", T_BOOL, True), A("screenOrientation", T_INT, 1),
                      A("configChanges", T_HEX, 0x04A0)], [  # keyboardHidden|orientation|screenSize
            ("intent-filter", [], [
                ("action", [A("name", T_STR, "android.intent.action.MAIN")], []),
                ("category", [A("name", T_STR, "android.intent.category.LAUNCHER")], []),
            ]),
        ]),
    ]),
])

# ---------- resources.arsc with one drawable (the launcher icon) ----------
def arsc(icon_path):
    gpool = string_pool([icon_path])
    tpool = string_pool(["drawable"])
    kpool = string_pool(["icon"])
    spec = struct.pack("<HHIBBHI", 0x0202, 16, 20, 1, 0, 0, 1) + struct.pack("<I", 0)
    config = bytearray(64)
    struct.pack_into("<I", config, 0, 64)
    struct.pack_into("<H", config, 14, 640)  # xxxhdpi
    thdr = 8 + 1 + 1 + 2 + 4 + 4 + 64
    entries = struct.pack("<HHI", 8, 0, 0) + struct.pack("<HBBI", 8, 0, T_STR, 0)
    tsize = thdr + 4 + len(entries)
    ttype = struct.pack("<HHIBBHII", 0x0201, thdr, tsize, 1, 0, 0, 1, thdr + 4) + bytes(config) + struct.pack("<I", 0) + entries
    phdr = 288
    name = PKG.encode("utf-16-le").ljust(256, b"\0")
    psize = phdr + len(tpool) + len(kpool) + len(spec) + len(ttype)
    pkg = struct.pack("<HHII", 0x0200, phdr, psize, 0x7F) + name + \
        struct.pack("<IIIII", phdr, 1, phdr + len(tpool), 1, 0) + tpool + kpool + spec + ttype
    total = 12 + len(gpool) + len(pkg)
    return struct.pack("<HHII", 0x0002, 12, total, 1) + gpool + pkg

# ---------- launcher icon ----------
def make_icon(path):
    from PIL import Image, ImageDraw
    S = 768
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((24, 24, S - 24, S - 24), radius=170, fill=(14, 22, 20, 255))
    import math
    cols = [(240, 138, 85), (229, 181, 58), (109, 156, 240), (238, 116, 166), (181, 138, 240), (76, 195, 217)]
    cx = cy = S / 2
    for i, c in enumerate(cols):
        a = -math.pi / 2 + i * math.pi / 3
        x, y = cx + 205 * math.cos(a), cy + 205 * math.sin(a)
        d.line((cx, cy, x, y), fill=(47, 196, 174, 255), width=22)
    for i, c in enumerate(cols):
        a = -math.pi / 2 + i * math.pi / 3
        x, y = cx + 205 * math.cos(a), cy + 205 * math.sin(a)
        d.ellipse((x - 70, y - 70, x + 70, y + 70), fill=c + (255,))
    d.ellipse((cx - 92, cy - 92, cx + 92, cy + 92), fill=(47, 196, 174, 255))
    im.resize((192, 192), Image.LANCZOS).quantize(colors=48, method=Image.Quantize.FASTOCTREE).save(path, optimize=True)

# ---------- aligned zip ----------
def write_apk(path, entries):
    with open(path, "wb") as raw:
        zf = zipfile.ZipFile(raw, "w")
        for name, data, stored in entries:
            zi = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
            zi._compresslevel = 9
            if stored:
                off = raw.tell() + 30 + len(name.encode()) + 6
                pad = (-off) % 4
                zi.extra = struct.pack("<HH", 0xD935, pad + 2) + struct.pack("<H", 4) + b"\0" * pad
            zf.writestr(zi, data)
        zf.close()


def main():
    work = tempfile.mkdtemp()
    java = os.path.join(HERE, "src")
    cls = os.path.join(work, "classes")
    os.makedirs(cls)
    srcs = [os.path.join(dp, f) for dp, _, fs in os.walk(java) for f in fs if f.endswith(".java")]
    subprocess.check_call(["javac", "-nowarn", "-Xlint:-options", "--release", "8", "-cp", os.path.join(TOOLS, "android-all.jar"), "-d", cls] + srcs)
    dex = os.path.join(work, "classes.dex")
    subprocess.check_call(["java", "-cp", os.path.join(TOOLS, "dx.jar"), "com.android.dx.command.Main", "--dex", "--min-sdk-version=24", "--output=" + dex, cls])
    icon = os.path.join(work, "icon.png")
    make_icon(icon)
    html = open(os.path.join(ROOT, "index.html"), "rb").read()
    head = b'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no"><style>html{color-scheme:light dark}body{margin:0}img{max-width:100%}[hidden]{display:none!important}:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style></head><body>'
    page = head + html + b"</body></html>"
    unsigned = os.path.join(work, "unsigned.apk")
    write_apk(unsigned, [
        ("AndroidManifest.xml", axml(manifest), False),
        ("classes.dex", open(dex, "rb").read(), False),
        ("resources.arsc", arsc("res/drawable/icon.png"), True),
        ("res/drawable/icon.png", open(icon, "rb").read(), True),
        ("assets/index.html", page, False),
    ])
    ks = os.path.join(HERE, "mindgym-release.p12")
    if not os.path.exists(ks):
        subprocess.check_call(["keytool", "-genkeypair", "-keystore", ks, "-storetype", "PKCS12", "-alias", "mg", "-keyalg", "RSA",
                               "-keysize", "2048", "-validity", "10000", "-storepass", "mindgym", "-keypass", "mindgym", "-dname", "CN=Mind Gym"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    signer = os.path.join(work, "sign")
    os.makedirs(signer)
    subprocess.check_call(["javac", "-nowarn", "-cp", os.path.join(TOOLS, "apksig.jar"), "-d", signer, os.path.join(HERE, "Sign.java")])
    subprocess.check_call(["java", "--add-exports=java.base/sun.security.x509=ALL-UNNAMED", "--add-exports=java.base/sun.security.pkcs=ALL-UNNAMED", "--add-exports=java.base/sun.security.util=ALL-UNNAMED", "-cp", signer + os.pathsep + os.path.join(TOOLS, "apksig.jar"), "Sign", ks, "mindgym", unsigned, OUT])
    shutil.copy(icon, os.path.join(HERE, "icon-192.png"))
    shutil.rmtree(work)
    print("built", OUT, os.path.getsize(OUT), "bytes")


main()
