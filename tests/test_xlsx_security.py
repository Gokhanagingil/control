import io
import unittest
import warnings
from zipfile import ZipFile, ZIP_DEFLATED

import xlsx_io


class WorkbookAttackTests(unittest.TestCase):
    def setUp(self):
        base = xlsx_io.make_xlsx({"A": [["code"], ["ok"]], "B": [["code"]]})
        with ZipFile(io.BytesIO(base)) as z:
            self.files = {n: z.read(n) for n in z.namelist()}

    def archive(self, extra=None):
        buf = io.BytesIO()
        with warnings.catch_warnings(), ZipFile(buf, "w", ZIP_DEFLATED) as z:
            warnings.simplefilter("ignore", UserWarning)
            for n, data in self.files.items():
                z.writestr(n, data)
            if extra:
                z.writestr(extra, self.files[extra])
        return buf.getvalue()

    def test_reject_dtd_even_when_utf16(self):
        part = "xl/workbook.xml"
        self.files[part] = ('<?xml version="1.0" encoding="UTF-16"?>'
                            '<!DOCTYPE x [<!ENTITY a "untrusted">]><x>&a;</x>').encode("utf-16")
        with self.assertRaisesRegex(ValueError, "XML"):
            xlsx_io.read_xlsx(self.archive())

    def test_duplicate_zip_entry_rejected(self):
        with self.assertRaisesRegex(ValueError, "tekrarlı dosya"):
            xlsx_io.read_xlsx(self.archive("xl/worksheets/sheet1.xml"))

    def test_repeated_worksheet_part_rejected(self):
        rel = "xl/_rels/workbook.xml.rels"
        self.files[rel] = self.files[rel].replace(b"sheet2.xml", b"sheet1.xml")
        with self.assertRaisesRegex(ValueError, "tekrar kullanılan"):
            xlsx_io.read_xlsx(self.archive())

    def test_long_cell_reference_rejected(self):
        part = "xl/worksheets/sheet1.xml"
        self.files[part] = self.files[part].replace(b'r="A1"', b'r="' + b"A"*500 + b'1"')
        with self.assertRaisesRegex(ValueError, "adres"):
            xlsx_io.read_xlsx(self.archive())
