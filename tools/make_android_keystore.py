"""Create the self-signed release keystore for the Android app (PKCS#12).

Run once:  python tools/make_android_keystore.py

The generated keystore lives in android/keystore/fidexe-release.p12 and is
committed so that every CI build produces an APK signed with the same key
(updates install on top of the previous version). The password is public on
purpose: this is a sideloading key, not a Play Store upload key.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parent.parent
ANDROID = ROOT / "android"
KEYSTORE = ANDROID / "keystore" / "fidexe-release.p12"
PROPS = ANDROID / "keystore.properties"

ALIAS = "fidexe"
PASSWORD = "fidexe-remote-2024"


def main() -> None:
    if KEYSTORE.exists():
        print("keystore already exists:", KEYSTORE)
        return
    KEYSTORE.parent.mkdir(parents=True, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "FIDEXE Remote"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FIDEXE"),
            x509.NameAttribute(NameOID.COUNTRY_NAME, "RU"),
        ]
    )
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=365 * 30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    blob = pkcs12.serialize_key_and_certificates(
        name=ALIAS.encode(),
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(PASSWORD.encode()),
    )
    KEYSTORE.write_bytes(blob)
    PROPS.write_text(
        "storeFile=keystore/fidexe-release.p12\n"
        "storePassword=%s\n"
        "keyAlias=%s\n"
        "keyPassword=%s\n"
        "storeType=PKCS12\n" % (PASSWORD, ALIAS, PASSWORD),
        encoding="utf-8",
    )
    print("wrote", KEYSTORE, KEYSTORE.stat().st_size, "bytes")
    print("wrote", PROPS)


if __name__ == "__main__":
    main()
