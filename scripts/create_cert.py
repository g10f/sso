#!/usr/bin/env python

import os
import uuid
import subprocess

from OpenSSL import crypto


def create_self_signed_cert(cert_dir, cn, serial=int(uuid.uuid4().hex, 16)):
    """
    create a new
    self-signed cert and keypair and write them into that directory.
    """
    # create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 1024)

    # create a self-signed cert
    cert = crypto.X509()
    cert.set_version(2)
    cert.get_subject().CN = cn
    cert.set_serial_number(serial)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(1 * 365 * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.add_extensions([
       crypto.X509Extension("basicConstraints", True, "CA:FALSE"),
       crypto.X509Extension("keyUsage", True, "digitalSignature"),
       crypto.X509Extension("extendedKeyUsage", True, "clientAuth"),
    ])

    cert.sign(k, 'sha1')
    fingerprint = cert.digest('sha1').replace(':','').lower()

    cert_file = os.path.join(cert_dir, "%s.crt" % fingerprint)
    key_file = os.path.join(cert_dir, "%s.key" % fingerprint)
    pub_file = os.path.join(cert_dir, "%s.pub" % fingerprint)

    with open(cert_file, "wt") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    with open(key_file, "wt") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
    with open(pub_file, "wt") as f:
        output = subprocess.check_output(["openssl", "x509", "-in", cert_file, "-pubkey", "-noout"])
        f.write(output)
    
  
def main():
    create_self_signed_cert("../certs", "sso.kagyu.net")
    
if __name__ == "__main__":
    main()
