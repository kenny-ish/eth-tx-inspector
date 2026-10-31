import unittest

from tx import TRANSFER, erc20_transfers, fees


class TxTest(unittest.TestCase):
    def test_fees_1559(self):
        tx = {"gas": hex(100_000)}
        receipt = {"gasUsed": hex(21_000), "effectiveGasPrice": hex(3 * 10**9)}
        f = fees(tx, receipt, 2 * 10**9)
        self.assertEqual(f["fee"], 21_000 * 3 * 10**9)
        self.assertEqual(f["priority"], 10**9)
        self.assertNotIn("blob_fee", f)

    def test_blob_fee(self):
        f = fees({"gas": hex(21_000)}, {"gasUsed": hex(21_000), "effectiveGasPrice": hex(1), "blobGasUsed": hex(131072), "blobGasPrice": hex(2)}, 0)
        self.assertEqual(f["blob_fee"], 262144)
        self.assertIsNone(f["priority"])

    def test_erc20_transfer_parsing(self):
        a = "0x" + "0" * 24 + "11" * 20
        b = "0x" + "0" * 24 + "22" * 20
        logs = [
            {"address": "0xtoken", "topics": [TRANSFER, a, b], "data": hex(500)},
            {"address": "0xnft", "topics": [TRANSFER, a, b, hex(7)], "data": "0x"},
        ]
        self.assertEqual(erc20_transfers(logs), [("0xtoken", "0x" + "11" * 20, "0x" + "22" * 20, 500)])


if __name__ == "__main__":
    unittest.main()
