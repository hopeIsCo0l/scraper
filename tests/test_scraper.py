import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

from fsc_scraper.config import SECTIONS, BASE_URL
from fsc_scraper.manifest import Manifest
from fsc_scraper.extractor import extract_article_links, extract_document_links


class TestConfig(unittest.TestCase):
    def test_sections_structure(self):
        self.assertGreater(len(SECTIONS), 0)
        for key, section in SECTIONS.items():
            self.assertIn("name", section, f"Missing name in section {key}")
            self.assertIn("start_url", section, f"Missing start_url in section {key}")
            self.assertIn("pager_pattern", section, f"Missing pager_pattern in section {key}")
            self.assertTrue(section["start_url"].startswith(BASE_URL))
            self.assertIn("{page}", section["pager_pattern"])


class TestManifest(unittest.TestCase):
    def test_manifest_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir)
            manifest = Manifest(manifest_dir)

            doc_info = {
                "document_id": "123",
                "article_id": "456",
                "download_url": "https://www.fsc.gov.et/files/doc123.pdf",
                "article_title": "Test Legal Decision",
                "article_url": "https://www.fsc.gov.et/item/123",
                "link_text": "Download PDF",
            }

            key = manifest.make_key(doc_info)
            self.assertEqual(key, "doc_123")
            self.assertFalse(manifest.is_already_downloaded(doc_info))

            # Simulate writing file to disk
            test_file = manifest_dir / "supreme-court" / "doc_123.pdf"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_bytes(b"%PDF-1.4 test")

            manifest.record_success(
                doc_info=doc_info,
                filename="doc_123.pdf",
                relative_path="supreme-court/doc_123.pdf",
                file_size_bytes=len(b"%PDF-1.4 test"),
                section_name="supreme-court",
            )
            self.assertTrue(manifest.is_already_downloaded(doc_info))

            # Test reload persistence
            reloaded_manifest = Manifest(manifest_dir)
            self.assertTrue(reloaded_manifest.is_already_downloaded(doc_info))
            self.assertEqual(reloaded_manifest.entries[key]["file_size_bytes"], len(b"%PDF-1.4 test"))


class TestExtractor(unittest.TestCase):
    def test_extract_article_links(self):
        html = """
        <html>
            <body>
                <article>
                    <h2><a href="/detail/case-100">Case Volume 100</a></h2>
                </article>
                <article>
                    <a href="/login">Login</a>
                </article>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        articles = extract_article_links(soup, "https://www.fsc.gov.et/listing")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["url"], "https://www.fsc.gov.et/detail/case-100")
        self.assertEqual(articles[0]["title"], "Case Volume 100")

    def test_extract_document_links(self):
        html = """
        <html>
            <body>
                <h1>Volume 1 Details</h1>
                <a href="/Portals/0/Documents/Decision_Vol_1.pdf">Download Volume 1 (PDF)</a>
                <a href="/DesktopModules/EasyDNNNews/DocumentDownload.ashx?DocumentId=300">Download Attachment</a>
                <a href="https://other.com/ignore.png">Image</a>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        docs = extract_document_links(soup, "https://www.fsc.gov.et/detail/1")
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0]["download_url"], "https://www.fsc.gov.et/Portals/0/Documents/Decision_Vol_1.pdf")
        self.assertEqual(docs[1]["document_id"], "300")


if __name__ == "__main__":
    unittest.main()
