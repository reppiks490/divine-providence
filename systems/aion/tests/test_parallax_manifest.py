import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from aion.parallax_manifest import scan_archives


class ManifestTests(unittest.TestCase):
    def test_preserves_physical_members_duplicate_headers_and_logical_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "charts.zip"
            content = 'time,close,close,note\n1,2,3,"two\nlines"\n1,4,5,same-clock\n'
            with ZipFile(path, "w") as archive:
                archive.writestr("NQ, 20.csv", content)
                archive.writestr("copy/NQ, 20.csv", content)
                archive.writestr("__MACOSX/._NQ, 20.csv", "not a source")
            result = scan_archives([path])
            self.assertEqual(result["counts"]["physical_csv_members"], 2)
            self.assertEqual(result["counts"]["parsed_csv_members"], 2)
            self.assertEqual(result["counts"]["logical_data_rows"], 4)
            self.assertEqual(result["counts"]["unique_byte_contents"], 1)
            self.assertEqual(result["counts"]["records_in_exact_duplicate_groups"], 2)
            first, second = result["members"]
            self.assertNotEqual(first["physical_source_id"], second["physical_source_id"])
            self.assertEqual(first["headers"][2], {"position": 2, "name": "close"})
            self.assertEqual(first["duplicate_header_names"], ["close"])
            self.assertFalse(first["source_identity_verified"])
            self.assertFalse(result["execution_authorized"])

    def test_malformed_member_is_visible_and_not_counted_as_parsed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr("bad.csv", b"\xff\xfe")
            result = scan_archives([path])
            self.assertEqual(result["counts"]["physical_csv_members"], 1)
            self.assertEqual(result["counts"]["parsed_csv_members"], 0)
            self.assertEqual(result["members"][0]["status"], "parse_error")


    def test_preserves_tick_range_and_chart_family_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "multi.zip"
            content = "time,open,high,low,close,MP POC,MP VAH,MP VAL\n1,1,2,0,1,1,2,0\n"
            with ZipFile(path, "w") as archive:
                archive.writestr("Renko/CME_NQ1!, 10R.csv", content)
                archive.writestr("Tick/CME_NQ1!, 1000T.csv", content)
                archive.writestr("Heikin Ashi/CME_NQ1!, 20.csv", content)
            result = scan_archives([path])
            claims = {row["member_name"]: row["representation_claim"] for row in result["members"]}
            self.assertEqual(claims["Renko/CME_NQ1!, 10R.csv"]["family"], "renko")
            self.assertEqual(claims["Renko/CME_NQ1!, 10R.csv"]["price_geometry"], "renko")
            self.assertEqual(claims["Renko/CME_NQ1!, 10R.csv"]["sampling_domain"], "event")
            self.assertEqual(claims["Renko/CME_NQ1!, 10R.csv"]["construction"], "range")
            self.assertEqual(claims["Tick/CME_NQ1!, 1000T.csv"]["family"], "unknown")
            self.assertEqual(claims["Tick/CME_NQ1!, 1000T.csv"]["construction"], "tick")
            self.assertEqual(claims["Heikin Ashi/CME_NQ1!, 20.csv"]["family"], "heikin_ashi")
            self.assertEqual(claims["Heikin Ashi/CME_NQ1!, 20.csv"]["price_geometry"], "heikin_ashi")
            self.assertIn("market_profile_fields", claims["Heikin Ashi/CME_NQ1!, 20.csv"]["schema_tags"])
            self.assertTrue(all(not x["authoritative"] for x in claims.values()))


    def test_documented_candidate_archive_is_regular_candle_family(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Csv first 60.zip"
            content = "time,open,high,low,close,MP POC,MP VAH,MP VAL\n1,1,2,0,1,1,2,0\n"
            with ZipFile(path, "w") as archive:
                archive.writestr("Csv first 60/BATS_AAPL, 1.csv", content)
            result = scan_archives([path])
            claim = result["members"][0]["representation_claim"]
            self.assertEqual(claim["family"], "regular_candles")
            self.assertEqual(claim["price_geometry"], "standard_ohlc")
            self.assertEqual(claim["construction"], "time_bar")
            self.assertIn("market_profile_fields", claim["schema_tags"])
            self.assertFalse(claim["authoritative"])


    def test_candidate_archive_uses_documented_regular_candle_family(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Csv first 60.zip"
            content = "time,open,high,low,close,MP POC,MP VAH,MP VAL\n1,1,2,0,1,1,2,0\n"
            with ZipFile(path, "w") as archive:
                archive.writestr("Csv first 60/BATS_AAPL, 1.csv", content)
            result = scan_archives([path])
            claim = result["members"][0]["representation_claim"]
            self.assertEqual(claim["family"], "regular_candles")
            self.assertEqual(claim["sampling_domain"], "time")
            self.assertEqual(claim["construction"], "time_bar")
            self.assertIn("market_profile_fields", claim["schema_tags"])
            self.assertFalse(claim["authoritative"])


if __name__ == "__main__":
    unittest.main()
