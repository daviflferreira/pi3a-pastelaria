"""Gera um certificado TLS autoassinado para o servidor (uso local/demonstração)."""
import datetime
import ipaddress

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from config import CERT_ARQUIVO, CHAVE_ARQUIVO


def main():
    chave = ec.generate_private_key(ec.SECP256R1())

    nome = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PI III-A Pastelaria"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    agora = datetime.datetime.now(datetime.timezone.utc)

    certificado = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)  # autoassinado: emissor = titular
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - datetime.timedelta(minutes=5))
        .not_valid_after(agora + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_cert_sign=True, crl_sign=False,
                content_commitment=False, key_encipherment=False, data_encipherment=False,
                key_agreement=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(chave.public_key()), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(chave.public_key()), critical=False
        )
        .sign(chave, hashes.SHA256())
    )

    CERT_ARQUIVO.parent.mkdir(exist_ok=True)
    CHAVE_ARQUIVO.write_bytes(
        chave.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    CERT_ARQUIVO.write_bytes(certificado.public_bytes(serialization.Encoding.PEM))
    print(f"Certificado criado em {CERT_ARQUIVO}")
    print(f"Chave privada criada em {CHAVE_ARQUIVO} (NÃO envie para o GitHub)")


if __name__ == "__main__":
    main()