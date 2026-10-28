import base64
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import stat
import warnings
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.parse import quote

from dotenv import dotenv_values
import pyotp

from automation.totp_import import (
    TotpImportError, check_app_code, decode_export, inspect_export, main, save_secret,
)


# Fixture independente: MigrationPayload v1 com o segredo público do RFC 6238,
# nome "Conta de teste", emissor PJe, SHA1, seis dígitos e TOTP.
ACCOUNT = bytes.fromhex(
    "0a143132333435363738393031323334353637383930"
    "120e436f6e7461206465207465737465"
    "1a03504a65200128013002"
)
PAYLOAD = bytes([10, len(ACCOUNT)]) + ACCOUNT + bytes.fromhex("10011801")
EXPECTED_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


def uri(data=PAYLOAD):
    return "otpauth-migration://offline?data=" + quote(base64.b64encode(data).decode(), safe="")


class GoogleExportTests(unittest.TestCase):
    def test_decodes_public_fixture_and_matches_rfc_totp(self):
        account = decode_export(uri())
        self.assertEqual(account.secret, EXPECTED_SECRET)
        self.assertEqual((account.name, account.issuer), ("Conta de teste", "PJe"))
        self.assertEqual(pyotp.TOTP(account.secret).at(59), "287082")
        self.assertNotIn(EXPECTED_SECRET, repr(account))

    def test_accepts_zbar_prefix_and_base64_padding(self):
        self.assertEqual(decode_export("QR-Code:" + uri() + "\n").secret, EXPECTED_SECRET)

    def test_accepts_legacy_zero_or_omitted_version_and_batch_defaults(self):
        body = bytes([10, len(ACCOUNT)]) + ACCOUNT
        for metadata in (b"", b"\x10\x00", b"\x10\x00\x18\x00\x20\x00", b"\x10\x01\x18\x00"):
            with self.subTest(metadata=metadata):
                self.assertEqual(decode_export(uri(body + metadata)).secret, EXPECTED_SECRET)

    def test_unspecified_enums_use_documented_import_defaults(self):
        for account in (ACCOUNT[:-6], ACCOUNT[:-6] + b"\x20\x00\x28\x00\x30\x00"):
            exported = decode_export(uri(bytes([10, len(account)]) + account))
            self.assertEqual(pyotp.TOTP(exported.secret).at(59), "287082")

    def test_version_two_accepts_only_the_same_validated_account_structure(self):
        payload = PAYLOAD.replace(b"\x10\x01\x18\x01", b"\x10\x02\x18\x01")
        account = decode_export(uri(payload))
        self.assertEqual(account.secret, EXPECTED_SECRET)
        self.assertEqual(pyotp.TOTP(account.secret).at(59), "287082")
        for old, replacement in ((b"\x20\x01", b"\x20\x02"), (b"\x28\x01", b"\x28\x02"), (b"\x30\x02", b"\x30\x01")):
            with self.subTest(parameter=old), self.assertRaises(TotpImportError):
                decode_export(uri(payload.replace(old, replacement)))
        with self.assertRaises(TotpImportError):
            decode_export(uri(payload + b"\x20\x01"))

    def test_future_version_stays_rejected_but_can_be_diagnosed(self):
        content = uri(PAYLOAD.replace(b"\x10\x01\x18\x01", b"\x10\x03\x18\x01"))
        with self.assertRaisesRegex(TotpImportError, "não suportada: 3"):
            decode_export(content)
        metadata = inspect_export(content)
        self.assertEqual(metadata, {
            "version": 3, "version_present": True, "batch_size": 1,
            "batch_index": 0, "account_count": 1,
            "parameters": [{"algorithm_enum": 1, "digits_enum": 1, "type_enum": 2}],
        })
        self.assertNotIn(EXPECTED_SECRET, str(metadata))
        self.assertNotIn("Conta de teste", str(metadata))

    def test_preserves_unescaped_plus_and_accepts_urlsafe_base64(self):
        payload = PAYLOAD + bytes.fromhex("a20604fbfeffff")  # Campo desconhecido, bytes.
        encoded = base64.b64encode(payload).decode()
        self.assertIn("+", encoded)
        self.assertEqual(decode_export("otpauth-migration://offline?data=" + encoded).secret, EXPECTED_SECRET)
        self.assertEqual(decode_export("otpauth-migration://offline?data=" + base64.urlsafe_b64encode(payload).decode()).secret, EXPECTED_SECRET)

    def test_rejects_multiple_accounts_or_partial_batches(self):
        for payload in (
            bytes([10, len(ACCOUNT)]) + ACCOUNT + PAYLOAD,
            PAYLOAD[:-1] + b"\x02",
            PAYLOAD + b"\x20\x01",
        ):
            with self.subTest(payload=payload), self.assertRaises(TotpImportError):
                decode_export(uri(payload))

    def test_rejects_incompatible_parameters_before_saving(self):
        for old, replacement in ((b"\x20\x01", b"\x20\x02"), (b"\x28\x01", b"\x28\x02"), (b"\x30\x02", b"\x30\x01")):
            with self.subTest(parameter=old), self.assertRaisesRegex(TotpImportError, "TOTP, SHA1 e 6"):
                decode_export(uri(PAYLOAD.replace(old, replacement)))

    def test_rejects_truncated_malformed_or_ambiguous_data(self):
        contents = [
            "otpauth-migration://offline?data=...",
            uri() + "&data=AAAA",
            "https://example.test/?data=AAAA",
            uri(PAYLOAD[:-1]),
            uri(b"\x0a\xff\xff\xff\xff\x01"),
            uri(b"\x80" * 11),
            uri(b"\x00"),
            uri(PAYLOAD.replace(b"\x10\x01\x18\x01", b"\x10\x03\x18\x01")),
        ]
        for content in contents:
            with self.subTest(case=contents.index(content)), self.assertRaises(TotpImportError) as raised:
                decode_export(content)
            self.assertNotIn(content, str(raised.exception))
            self.assertNotIn(EXPECTED_SECRET, str(raised.exception))

    def test_duplicate_secret_field_is_rejected(self):
        duplicate = ACCOUNT + b"\x0a\x01x"
        with self.assertRaisesRegex(TotpImportError, "duplicado"):
            decode_export(uri(bytes([10, len(duplicate)]) + duplicate + b"\x10\x01\x18\x01"))


class LocalImportTests(unittest.TestCase):
    def test_diagnostic_does_not_write_or_echo_private_content(self):
        output = io.StringIO()
        with patch("getpass.getpass", return_value=uri()), patch("automation.totp_import.save_secret") as write, redirect_stdout(output):
            self.assertEqual(main(["--titular", "cristiano", "--diagnostico"]), 0)
            write.assert_not_called()
        self.assertIn("Versão: 1", output.getvalue())
        for private in (uri(), EXPECTED_SECRET, "Conta de teste"):
            self.assertNotIn(private, output.getvalue())

    def test_accidentally_passing_export_as_argument_does_not_echo_it(self):
        output = io.StringIO()
        with redirect_stderr(output), self.assertRaises(SystemExit) as raised:
            main(["--titular", "cristiano", uri()])
        self.assertEqual(raised.exception.code, 2)
        self.assertNotIn(uri(), output.getvalue())

    def test_hidden_input_is_required(self):
        import getpass

        def insecure_input(*args, **kwargs):
            warnings.warn("No echo control", getpass.GetPassWarning)

        with patch("getpass.getpass", side_effect=insecure_input), patch("automation.totp_import.save_secret") as write, redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--titular", "cristiano", "--salvar"]), 2)
            write.assert_not_called()

    def test_writes_only_selected_key_and_restricts_permissions(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("# configuração local\nPJE_TOTP_SECRET='murilo-original'\nPJE_CRISTIANO_TOTP_SECRET='cristiano-original'\nPOSTGRES_PASSWORD='unchanged'\n")
            original = dotenv_values(path)
            key, changed = save_secret(path, decode_export(uri()), "cristiano")
            self.assertEqual(key, "PJE_CRISTIANO_TOTP_SECRET")
            self.assertTrue(changed)
            self.assertEqual(dotenv_values(path), {**original, key: EXPECTED_SECRET})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertTrue(path.read_text().startswith("# configuração local\n"))
            self.assertEqual(list(Path(directory).glob(".env.import-*")), [])

    def test_murilo_uses_current_legacy_or_prefixed_key(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            for original, expected in (("PJE_TOTP_SECRET='old'\n", "PJE_TOTP_SECRET"), ("PJE_MURILO_TOTP_SECRET='old'\n", "PJE_MURILO_TOTP_SECRET")):
                path.write_text(original)
                self.assertEqual(save_secret(path, decode_export(uri()), "murilo"), (expected, True))

    def test_identical_secret_is_reported_without_replacing_file(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            content = "# preservar\nPJE_CRISTIANO_TOTP_SECRET='" + EXPECTED_SECRET + "'\n"
            path.write_text(content)
            inode = path.stat().st_ino
            self.assertEqual(save_secret(path, decode_export(uri()), "cristiano"), ("PJE_CRISTIANO_TOTP_SECRET", False))
            self.assertEqual(path.read_text(), content)
            self.assertEqual(path.stat().st_ino, inode)

    def test_concurrent_edit_is_preserved(self):
        from automation import totp_import
        original_set_key = totp_import.set_key
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("PJE_TOTP_SECRET='old'\n")

            def edited_during_import(*args, **kwargs):
                original_set_key(*args, **kwargs)
                path.write_text("PJE_TOTP_SECRET='user-edited'\n")

            with patch.object(totp_import, "set_key", side_effect=edited_during_import):
                with self.assertRaisesRegex(TotpImportError, "editado durante"):
                    save_secret(path, decode_export(uri()), "cristiano")
            self.assertEqual(path.read_text(), "PJE_TOTP_SECRET='user-edited'\n")
            self.assertEqual(list(Path(directory).glob(".env.import-*")), [])

    def test_cli_does_not_disclose_export_secret_or_app_code(self):
        account = decode_export(uri())
        app_code = pyotp.TOTP(account.secret).now()
        output = io.StringIO()
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("PJE_TOTP_SECRET='murilo-original'\n")
            with patch("automation.totp_import.ROOT_ENV", path), patch("getpass.getpass", side_effect=[uri(), app_code]), redirect_stdout(output), redirect_stderr(output):
                self.assertEqual(main(["--titular", "cristiano", "--salvar"]), 0)
            self.assertEqual(dotenv_values(path)["PJE_CRISTIANO_TOTP_SECRET"], EXPECTED_SECRET)
        for private in (uri(), EXPECTED_SECRET, app_code):
            self.assertNotIn(private, output.getvalue())

    def test_code_mismatch_prevents_any_write(self):
        with patch("getpass.getpass", side_effect=[uri(), "123456"]), patch("pyotp.TOTP.verify", return_value=False), patch("automation.totp_import.save_secret") as write, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--titular", "cristiano", "--salvar"]), 2)
            write.assert_not_called()

    def test_version_two_does_not_bypass_matching_code_before_write(self):
        content = uri(PAYLOAD.replace(b"\x10\x01\x18\x01", b"\x10\x02\x18\x01"))
        with patch("getpass.getpass", side_effect=[content, "123456"]), patch("pyotp.TOTP.verify", return_value=False), patch("automation.totp_import.save_secret") as write, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--titular", "cristiano", "--salvar"]), 2)
            write.assert_not_called()

    def test_inspection_does_not_modify_env(self):
        with patch("getpass.getpass", return_value=uri()), patch("automation.totp_import.save_secret") as write, redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--titular", "cristiano"]), 0)
            write.assert_not_called()

    def test_invalid_app_code_shape_is_rejected(self):
        for code in ("12345", "abcdef", "١٢٣٤٥٦"):
            with self.assertRaises(TotpImportError):
                check_app_code(decode_export(uri()), code)
