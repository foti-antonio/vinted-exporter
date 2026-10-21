"""Offline unit tests; no Vinted requests or browser launch."""
import argparse
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from vinted_export import check_profile_url, download_images, non_negative_float, non_negative_int, slugify


class TestTextAndArguments(unittest.TestCase):
    def test_slugify_accents_and_punctuation(self):
        self.assertEqual(slugify("Giacca Nike – Blu / M"), "giacca-nike-blu-m")

    def test_slugify_empty_fallback(self):
        self.assertEqual(slugify("🎉"), "articolo")

    def test_valid_profile_url(self):
        link = "https://www.vinted.it/member/123456-utente"
        self.assertEqual(check_profile_url(link), link)

    def test_reject_foreign_host_subdomain(self):
        for value in (
            "http://www.vinted.it/member/1234",
            "https://www.vinted.it.evil.example/member/1234",
            "https://vinted.it/items/1234",
            "https://example.com/member/1234",
        ):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                check_profile_url(value)

    def test_max_non_negative(self):
        self.assertEqual(non_negative_int("0"), 0)
        self.assertEqual(non_negative_int("5"), 5)
        for value in ("-2", "1.5", "abc"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                non_negative_int(value)

    def test_delay_non_negative_and_finite(self):
        self.assertEqual(non_negative_float("2.5"), 2.5)
        for value in ("-1", "nan", "inf", "wat"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                non_negative_float(value)


class FakeResponse:
    def __init__(self, ok=True, status=200, content_type="image/webp", body=b"fakeimage"):
        self.ok = ok
        self.status = status
        self.headers = {"content-type": content_type}
        self._body = body

    def body(self):
        return self._body


class FakeRequest:
    def __init__(self, response):
        self.response = response

    def get(self, url, timeout):
        return self.response


class TestImageDownload(unittest.TestCase):
    def test_saves_webp(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = SimpleNamespace(request=FakeRequest(FakeResponse()))
            saved, errors = download_images(context, ["https://images.vinted.net/photo.webp"], Path(tmp))
            self.assertEqual(saved, ["01.webp"])
            self.assertEqual(errors, [])
            self.assertEqual((Path(tmp) / "01.webp").read_bytes(), b"fakeimage")

    def test_reject_non_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = SimpleNamespace(request=FakeRequest(FakeResponse(content_type="text/html")))
            saved, errors = download_images(context, ["https://images.vinted.net/a"], Path(tmp))
            self.assertEqual(saved, [])
            self.assertEqual(len(errors), 1)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_reports_http_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = SimpleNamespace(request=FakeRequest(FakeResponse(ok=False, status=403)))
            saved, errors = download_images(context, ["https://images.vinted.net/a"], Path(tmp))
            self.assertEqual(saved, [])
            self.assertIn("403", errors[0])


if __name__ == "__main__":
    unittest.main()
