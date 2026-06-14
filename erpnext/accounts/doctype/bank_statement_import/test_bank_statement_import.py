# Copyright (c) 2020, Frappe Technologies and Contributors
# See license.txt

from erpnext.accounts.doctype.bank_statement_import.bank_statement_import import (
	is_camt053_format,
	is_mt940_format,
	parse_camt053,
	preprocess_mt940_content,
)
from erpnext.tests.utils import ERPNextTestSuite

CAMT053_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.10">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>STMT-001</MsgId><CreDtTm>2026-06-14T00:00:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>STMT-GBP</Id>
      <Acct><Id><IBAN>GB00WISE00000000000000</IBAN></Id><Ccy>GBP</Ccy></Acct>
      <Ntry>
        <Amt Ccy="GBP">2500.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>2026-02-10</Dt></BookgDt><ValDt><Dt>2026-02-10</Dt></ValDt>
        <AcctSvcrRef>TRANSFER-1001</AcctSvcrRef>
        <NtryDtls><TxDtls>
          <Refs><EndToEndId>FOUNDER</EndToEndId></Refs>
          <RmtInf><Ustrd>Director loan</Ustrd></RmtInf>
          <RltdPties><Dbtr><Nm>Lawrence Sinclair</Nm></Dbtr></RltdPties>
        </TxDtls></NtryDtls>
      </Ntry>
      <Ntry>
        <Amt Ccy="GBP">42.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>2026-02-23</Dt></BookgDt><AcctSvcrRef>CARD-2002</AcctSvcrRef>
        <NtryDtls><TxDtls>
          <Refs><EndToEndId>NOTPROVIDED</EndToEndId></Refs>
          <RmtInf><Ustrd>Hetzner hosting</Ustrd></RmtInf>
          <RltdPties><Cdtr><Nm>Hetzner Online GmbH</Nm></Cdtr></RltdPties>
        </TxDtls></NtryDtls>
      </Ntry>
      <Ntry>
        <Amt Ccy="GBP">99.99</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts><Cd>PDNG</Cd></Sts>
        <BookgDt><Dt>2026-06-14</Dt></BookgDt>
        <NtryDtls><TxDtls><RmtInf><Ustrd>Pending</Ustrd></RmtInf></TxDtls></NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""


class TestBankStatementImport(ERPNextTestSuite):
	"""Unit tests for Bank Statement Import functions"""

	def test_preprocess_mt940_content_with_long_statement_number(self):
		"""Test that statement numbers longer than 5 digits are truncated to last 5 digits"""
		# Test case with 6-digit statement number (167619 -> 67619)
		mt940_content = ":28C:167619/1"
		expected_content = ":28C:67619/1"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

	def test_preprocess_mt940_content_with_normal_statement_number(self):
		"""Test that statement numbers with 5 or fewer digits are unchanged"""
		# Test case with 5-digit statement number (should remain unchanged)
		mt940_content = ":28C:12345/1"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, mt940_content)  # Should be unchanged

		# Test case with 4-digit statement number (should remain unchanged)
		mt940_content = ":28C:1234/1"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, mt940_content)  # Should be unchanged

	def test_preprocess_mt940_content_without_sequence_number(self):
		"""Test statement number truncation without sequence number"""
		# Test case with long statement number but no sequence (no /1)
		mt940_content = ":28C:987654321"
		expected_content = ":28C:54321"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

	def test_preprocess_mt940_content_multiple_occurrences(self):
		"""Test multiple statement numbers in the same content"""
		mt940_content = """:28C:167619/1
:28C:987654/2"""
		expected_content = """:28C:67619/1
:28C:87654/2"""
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

	def test_preprocess_mt940_content_edge_cases(self):
		"""Test edge cases like empty content and content without :28C: tags"""
		# Test empty content
		self.assertEqual(preprocess_mt940_content(""), "")

		# Test content without :28C: tags
		content_without_28c = """:20:STARTUMSE
:25:12345678901234567890
:60F:C031002EUR0,00"""
		result = preprocess_mt940_content(content_without_28c)
		self.assertEqual(result, content_without_28c)  # Should be unchanged

	def test_preprocess_mt940_content_with_full_mt940_document(self):
		"""Test preprocessing with complete MT940 document"""
		mt940_content = """:20:STARTUMSE
:25:12345678901234567890
:28C:167619/1
:60F:C031002EUR0,00
:61:0310021002DR123,45NMSCNONREF//8327000090031789
:86:806?20EREF+NONREF?21MREF+M180031?22CRED+DE98ZZZ09999999999
:62F:C031002EUR-123,45
-"""
		expected_content = """:20:STARTUMSE
:25:12345678901234567890
:28C:67619/1
:60F:C031002EUR0,00
:61:0310021002DR123,45NMSCNONREF//8327000090031789
:86:806?20EREF+NONREF?21MREF+M180031?22CRED+DE98ZZZ09999999999
:62F:C031002EUR-123,45
-"""
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

	def test_is_mt940_format_detection(self):
		"""Test MT940 format detection function"""
		# Valid MT940 content with all required tags
		valid_mt940 = """:20:STARTUMSE
:25:12345678901234567890
:28C:167619/1
:60F:C031002EUR0,00
:61:0310021002DR123,45NMSCNONREF//8327000090031789"""
		self.assertTrue(is_mt940_format(valid_mt940))

		# Invalid MT940 content (CSV format)
		invalid_mt940 = """Date,Description,Amount
2023-01-01,Test Transaction,100.00
2023-01-02,Another Transaction,-50.00"""
		self.assertFalse(is_mt940_format(invalid_mt940))

		# Partially valid MT940 (missing some required tags)
		partial_mt940 = """:20:STARTUMSE
:25:12345678901234567890
:60F:C031002EUR0,00"""
		self.assertFalse(is_mt940_format(partial_mt940))

		# Empty content
		self.assertFalse(is_mt940_format(""))

	def test_preprocess_mt940_content_boundary_conditions(self):
		"""Test boundary conditions for statement number length"""
		# Test exactly 6 digits (should be truncated)
		mt940_content = ":28C:123456/1"
		expected_content = ":28C:23456/1"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

		# Test exactly 5 digits (should remain unchanged)
		mt940_content = ":28C:12345/1"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, mt940_content)

		# Test very long statement number
		mt940_content = ":28C:123456789012345/1"
		expected_content = ":28C:12345/1"  # Last 5 digits
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

	def test_preprocess_mt940_content_real_world_case(self):
		"""Test with real-world MT940 content that was failing in production"""
		# This is based on actual MT940 content that was causing parsing errors (sanitized)
		mt940_content = """{1:F0112345678901X0000000000}{2:I94012345678901XN}{4:
:20:STMTREF167619
:25:1234567890
:28C:167619/1
:60F:C250622USD0,00
:61:2507170717C100000,00NMSCNOREF
:86:BY EXAMPLE INST 123456/03-07-25/TESTBANK/CITY
:61:2507240724C1,00NMSCNEFTINW-1234567890
:86:NEFT TEST123456789 EXAMPLE MERCHANT SERVICES
:61:2507310731D305,62NMSCTBMS-1234567890
:86:Chrg: Debit Card Annual Fee 1234 for 2025
:61:2508030803D1066,00NMSC123456789
:86:PCD/1234/EXAMPLE DOMAIN/01234567890123/23:27
:61:2508060806D2000,00NMSCUPI-123456789
:86:UPI/TEST USER/123456789/PaidViaTestApp
:61:2508140814D5000,00NMSCUPI-123456789
:86:UPI/TEST USER/123456789/PaidViaTestApp
:61:2509190919D900,00NMSCUPI-123456789
:86:UPI/EXAMPLE MERCHANT/123456789/Pay
:61:2509190919D2606,00NMSCUPI-123456789
:86:UPI/JOHN DOE/123456789/PaidViaTestApp
:62F:C250922USD88123,38
-}"""

		# Expected result with statement number 167619 truncated to 67619
		expected_content = """{1:F0112345678901X0000000000}{2:I94012345678901XN}{4:
:20:STMTREF167619
:25:1234567890
:28C:67619/1
:60F:C250622USD0,00
:61:2507170717C100000,00NMSCNOREF
:86:BY EXAMPLE INST 123456/03-07-25/TESTBANK/CITY
:61:2507240724C1,00NMSCNEFTINW-1234567890
:86:NEFT TEST123456789 EXAMPLE MERCHANT SERVICES
:61:2507310731D305,62NMSCTBMS-1234567890
:86:Chrg: Debit Card Annual Fee 1234 for 2025
:61:2508030803D1066,00NMSC123456789
:86:PCD/1234/EXAMPLE DOMAIN/01234567890123/23:27
:61:2508060806D2000,00NMSCUPI-123456789
:86:UPI/TEST USER/123456789/PaidViaTestApp
:61:2508140814D5000,00NMSCUPI-123456789
:86:UPI/TEST USER/123456789/PaidViaTestApp
:61:2509190919D900,00NMSCUPI-123456789
:86:UPI/EXAMPLE MERCHANT/123456789/Pay
:61:2509190919D2606,00NMSCUPI-123456789
:86:UPI/JOHN DOE/123456789/PaidViaTestApp
:62F:C250922USD88123,38
-}"""

		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

		# Verify that the problematic statement number was actually changed
		self.assertIn(":28C:67619/1", result)
		self.assertNotIn(":28C:167619/1", result)

		# Verify that other content remains unchanged
		self.assertIn(":20:STMTREF167619", result)  # Reference should remain unchanged
		self.assertIn("UPI/TEST USER/123456789/PaidViaTestApp", result)

	def test_preprocess_mt940_content_whitespace_variants(self):
		"""Test handling of whitespace and different line endings"""
		# Test with trailing spaces
		mt940_content = ":28C:167619/1   \n"
		expected_content = ":28C:67619/1   \n"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

		# Test with Windows line endings (CRLF)
		mt940_content = ":28C:167619/1\r\n"
		expected_content = ":28C:67619/1\r\n"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

		# Test with leading spaces (should not match as it's not line start)
		mt940_content = "   :28C:167619/1\n"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, mt940_content)  # Should remain unchanged

	def test_is_camt053_format_detection(self):
		"""camt.053 detection by namespace hint or root statement element."""
		self.assertTrue(is_camt053_format(CAMT053_SAMPLE))
		self.assertTrue(is_camt053_format("<x xmlns='...camt.053.001.02'></x>"))
		self.assertFalse(is_camt053_format("Date,Description,Amount\n2026-01-01,Test,100"))
		self.assertFalse(is_camt053_format(""))

	def test_parse_camt053_basic(self):
		"""camt.053 parsing: amounts, Cr/Dr direction, dates, currency."""
		rows = parse_camt053(CAMT053_SAMPLE)

		# Only the two BOOKED entries; the PDNG entry is skipped.
		self.assertEqual(len(rows), 2)

		credit, debit = rows[0], rows[1]
		# Money in -> deposit column; money out -> withdrawal column.
		self.assertEqual(credit["deposit"], 2500.00)
		self.assertEqual(credit["withdrawal"], "")
		self.assertEqual(debit["withdrawal"], 42.00)
		self.assertEqual(debit["deposit"], "")
		# Booking date and currency.
		self.assertEqual(credit["date"], "2026-02-10")
		self.assertEqual(credit["currency"], "GBP")

	def test_parse_camt053_references_and_counterparty(self):
		"""Reference falls back past NOTPROVIDED; counterparty matches direction."""
		credit, debit = parse_camt053(CAMT053_SAMPLE)

		# Incoming: counterparty is the payer (Dbtr).
		self.assertIn("Lawrence Sinclair", credit["description"])
		self.assertEqual(credit["reference"], "TRANSFER-1001")

		# Outgoing: counterparty is the payee (Cdtr); EndToEndId "NOTPROVIDED"
		# is ignored, so the reference falls back to AcctSvcrRef.
		self.assertIn("Hetzner Online GmbH", debit["description"])
		self.assertEqual(debit["reference"], "CARD-2002")

	def test_parse_camt053_skips_pending_entries(self):
		"""Pending (PDNG) entries must never be imported as booked transactions."""
		rows = parse_camt053(CAMT053_SAMPLE)
		self.assertTrue(all(r["date"] != "2026-06-14" for r in rows))

	def test_parse_camt053_bktxcd_reference_fallback(self):
		"""A card entry with no AcctSvcrRef/EndToEndId falls back to the
		proprietary BkTxCd/Prtry/Cd id; BookgDt given as DtTm is trimmed to a date."""
		xml = (
			'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.10">'
			"<BkToCstmrStmt><Stmt><Ntry>"
			'<Amt Ccy="GBP">1.29</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts><Cd>BOOK</Cd></Sts>'
			"<BookgDt><DtTm>2026-06-08T00:59:54.238316+07:00</DtTm></BookgDt>"
			"<BkTxCd><Prtry><Cd>CARD-3893862515</Cd></Prtry></BkTxCd>"
			"<AddtlNtryInf>Card transaction issued by Anthropic</AddtlNtryInf>"
			"</Ntry></Stmt></BkToCstmrStmt></Document>"
		)
		rows = parse_camt053(xml)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["reference"], "CARD-3893862515")
		self.assertEqual(rows[0]["date"], "2026-06-08")
		self.assertEqual(rows[0]["withdrawal"], 1.29)

	def test_parse_camt053_reversal_does_not_flip_sign(self):
		"""Per ISO 20022, CdtDbtInd states the actual direction of the booking and
		RvslInd is informational ("If CdtDbtInd is CRDT and ReversalIndicator is
		Yes, the original operation was a debit entry"). A reversal of a debit is
		itself a credit, so a CRDT+RvslInd entry must stay a deposit, not a
		withdrawal, and the reversal is noted in the description only."""
		xml = (
			'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.10">'
			"<BkToCstmrStmt><Stmt><Ntry>"
			'<Amt Ccy="GBP">100.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>'
			"<RvslInd>true</RvslInd><Sts><Cd>BOOK</Cd></Sts>"
			"<BookgDt><Dt>2026-03-01</Dt></BookgDt><AcctSvcrRef>REV-1</AcctSvcrRef>"
			"<AddtlNtryInf>Refund of earlier card charge</AddtlNtryInf>"
			"</Ntry></Stmt></BkToCstmrStmt></Document>"
		)
		rows = parse_camt053(xml)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["deposit"], 100.00)  # increase — NOT flipped
		self.assertEqual(rows[0]["withdrawal"], "")
		self.assertIn("Reversal", rows[0]["description"])

	def test_parse_camt053_multiple_statements_and_currencies(self):
		"""A document may carry several Stmt blocks (one per currency, as Wise
		exports). Entries from every statement are returned, each with its own
		currency taken from the Amt @Ccy attribute."""
		xml = (
			'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.10"><BkToCstmrStmt>'
			"<Stmt><Acct><Ccy>GBP</Ccy></Acct><Ntry>"
			'<Amt Ccy="GBP">10.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts><Cd>BOOK</Cd></Sts>'
			"<BookgDt><Dt>2026-03-01</Dt></BookgDt><AddtlNtryInf>GBP card</AddtlNtryInf></Ntry></Stmt>"
			"<Stmt><Acct><Ccy>USD</Ccy></Acct><Ntry>"
			'<Amt Ccy="USD">2003.40</Amt><CdtDbtInd>CRDT</CdtDbtInd><Sts><Cd>BOOK</Cd></Sts>'
			"<BookgDt><Dt>2026-04-08</Dt></BookgDt><AddtlNtryInf>Topped up account</AddtlNtryInf></Ntry></Stmt>"
			"</BkToCstmrStmt></Document>"
		)
		rows = parse_camt053(xml)
		self.assertEqual(len(rows), 2)
		self.assertEqual(rows[0]["currency"], "GBP")
		self.assertEqual(rows[0]["withdrawal"], 10.00)
		self.assertEqual(rows[1]["currency"], "USD")
		self.assertEqual(rows[1]["deposit"], 2003.40)

	def test_parse_camt053_empty_statement(self):
		"""A statement with no entries (e.g. an opened-but-unused currency) yields
		no rows rather than erroring."""
		xml = (
			'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.10">'
			"<BkToCstmrStmt><Stmt><Acct><Ccy>EUR</Ccy></Acct></Stmt></BkToCstmrStmt></Document>"
		)
		self.assertEqual(parse_camt053(xml), [])

	def test_parse_camt053_description_assembly(self):
		"""Description joins AddtlNtryInf + each RmtInf/Ustrd + counterparty,
		de-duplicated and pipe-separated."""
		xml = (
			'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.10">'
			"<BkToCstmrStmt><Stmt><Ntry>"
			'<Amt Ccy="USD">90.43</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts><Cd>BOOK</Cd></Sts>'
			"<BookgDt><Dt>2026-03-03</Dt></BookgDt><AcctSvcrRef>INV 3477</AcctSvcrRef>"
			"<AddtlNtryInf>Sent money to EAST AGILE LIMITED</AddtlNtryInf>"
			"<NtryDtls><TxDtls>"
			"<RmtInf><Ustrd>INV 3477</Ustrd><Ustrd>Development services</Ustrd></RmtInf>"
			"<RltdPties><Cdtr><Nm>East Agile Limited</Nm></Cdtr></RltdPties>"
			"</TxDtls></NtryDtls></Ntry></Stmt></BkToCstmrStmt></Document>"
		)
		row = parse_camt053(xml)[0]
		self.assertEqual(row["reference"], "INV 3477")
		parts = row["description"].split(" | ")
		self.assertEqual(parts[0], "Sent money to EAST AGILE LIMITED")
		self.assertIn("Development services", parts)
		self.assertIn("East Agile Limited", parts)
