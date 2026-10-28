"""Guard regressions: no database, server or frontend build is started here."""

import asyncio
import io
import json
import tempfile
import unittest
from pathlib import Path

import httpx
from PIL import Image
from run_ci_frontend_e2e import create_fixture_media, public_fallback_media_references, validate_database
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles


class DisposableDatabaseGuardTests(unittest.TestCase):
    def target(self, url="postgresql://test:test@127.0.0.1:15432/ccf_e2e_ci"):
        return {
            "DATABASE_URL": url,
            "TEST_DATABASE_URL": url,
            "CCF_E2E_DATABASE_CONFIRM": "ccf_e2e_ci",
        }

    def test_accepts_confirmed_loopback_postgresql(self):
        env = self.target()
        self.assertEqual(validate_database(env), env["DATABASE_URL"])

    def test_rejects_remote_hosts_and_unsupported_databases(self):
        for url in (
            "postgresql://test:test@example.com/ccf_e2e_ci",
            "postgresql://test:test@127.0.0.1/ccf_db",
            "sqlite:///ccf_e2e_ci",
            "postgresql://test:test@127.0.0.1/ccf_e2e_ci?host=example.com",
            "postgresql://test:test@127.0.0.1/ccf_e2e_ci#options",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_database(self.target(url))

    def test_rejects_missing_or_wrong_confirmation(self):
        for confirmation in ("", "ccf_e2e_other"):
            env = self.target()
            env["CCF_E2E_DATABASE_CONFIRM"] = confirmation
            with self.subTest(confirmation=confirmation), self.assertRaises(ValueError):
                validate_database(env)

    def test_rejects_different_test_database(self):
        env = self.target()
        env["TEST_DATABASE_URL"] = "postgresql://test:test@127.0.0.1/ccf_e2e_other"
        with self.assertRaises(ValueError):
            validate_database(env)


class FixtureMediaTests(unittest.TestCase):
    def environment(self, scratch):
        root = Path(scratch)
        (root / "uploads").mkdir()
        (root / ".ccf-e2e-owner").write_text("run_ci_frontend_e2e")
        return {
            **DisposableDatabaseGuardTests().target(),
            "CCF_E2E_WORKDIR": str(root),
            "UPLOADS_DIR": str(root / "uploads"),
        }

    def test_nested_fixture_images_are_valid_and_served_with_image_metadata(self):
        with tempfile.TemporaryDirectory(prefix="ccf-e2e-") as scratch:
            env = self.environment(scratch)
            hero = "/api/static/cms/banner/fixture.webp"
            portrait = "/api/static/cms/pastors/fixture.webp"
            values = {
                "hero": hero,
                "content": json.dumps({"cards": [{"image": portrait}, {"duplicate": hero}]}),
                "external": "https://example.invalid/api/static/cms/remote.webp",
                "frontend_fallback": "/images/events/fixture.jpg",
            }
            paths = create_fixture_media(values, env)
            self.assertEqual(set(paths), {hero, portrait})
            self.assertEqual(len(list(Path(env["UPLOADS_DIR"]).rglob("*.webp"))), 2)
            for path in paths.values():
                self.assertTrue(path.is_relative_to(Path(scratch) / "uploads/cms"))
                with Image.open(path) as image:
                    self.assertEqual(image.format, "WEBP")
                    self.assertEqual(image.size, (16, 16))

            async def requests():
                app = Starlette(routes=[Mount("/api/static", app=StaticFiles(directory=env["UPLOADS_DIR"]))])
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://fixture") as client:
                    for url in paths:
                        response = await client.get(url)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.headers["content-type"], "image/webp")
                        self.assertEqual(int(response.headers["content-length"]), len(response.content))
                        with Image.open(io.BytesIO(response.content)) as image:
                            self.assertEqual(image.size, (16, 16))

            asyncio.run(requests())
            # Existing fixture content must never be overwritten on a repeated pass.
            original = paths[hero].read_bytes()
            create_fixture_media(values, env)
            self.assertEqual(paths[hero].read_bytes(), original)

    def test_refuses_non_owned_or_production_upload_paths(self):
        with tempfile.TemporaryDirectory(prefix="ccf-e2e-") as scratch:
            env = self.environment(scratch)
            for override in (
                {"UPLOADS_DIR": "/root/ccf/uploads"},
                {"CCF_E2E_WORKDIR": "/root/ccf"},
                {"DATABASE_URL": "postgresql://test@localhost/ccf_db", "TEST_DATABASE_URL": "postgresql://test@localhost/ccf_db"},
            ):
                with self.subTest(override=override), self.assertRaises(ValueError):
                    create_fixture_media("/api/static/cms/fixture.webp", {**env, **override})
            (Path(scratch) / ".ccf-e2e-owner").unlink()
            with self.assertRaises(ValueError):
                create_fixture_media("/api/static/cms/fixture.webp", env)
            self.assertEqual(list(Path(env["UPLOADS_DIR"]).rglob("*.webp")), [])

    def test_rejects_traversal_and_symlink_escape_before_writing(self):
        with tempfile.TemporaryDirectory(prefix="ccf-e2e-") as scratch, tempfile.TemporaryDirectory() as outside:
            env = self.environment(scratch)
            for url in (
                "/api/static/cms/../../escape.webp",
                "/api/static/cms/%2e%2e/escape.webp",
                "/api/static/cms/%252e%252e/escape.webp",
                "/api/static/cms/evil%5c..%5cescape.webp",
            ):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    create_fixture_media(["/api/static/cms/legitimate.webp", url], env)
            (Path(env["UPLOADS_DIR"]) / "cms").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                create_fixture_media("/api/static/cms/escape.webp", env)
            self.assertEqual(list(Path(outside).iterdir()), [])


class PublicFallbackMediaTests(unittest.TestCase):
    def test_includes_local_public_fallbacks_but_not_test_or_remote_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "page.tsx").write_text(
                '<img src="/api/static/cms/public-site/community.webp" />'
                '<img src="https://example.com/api/static/cms/remote.webp" />'
            )
            (root / "page.test.tsx").write_text('"/api/static/cms/test.webp"')
            self.assertEqual(public_fallback_media_references(root), {
                "/api/static/cms/public-site/community.webp",
            })


if __name__ == "__main__":
    unittest.main()
