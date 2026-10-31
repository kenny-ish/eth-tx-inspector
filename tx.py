"""Inspect an EVM transaction by hash."""
import argparse
import json
import time
import urllib.request

TYPES = {0: "legacy", 1: "EIP-2930 access list", 2: "EIP-1559", 3: "EIP-4844 blob", 4: "EIP-7702 set code"}
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
SELECTORS = {
    "a9059cbb": "transfer(address,uint256)", "095ea7b3": "approve(address,uint256)",
    "23b872dd": "transferFrom(address,address,uint256)", "d0e30db0": "deposit()", "2e1a7d4d": "withdraw(uint256)",
    "38ed1739": "swapExactTokensForTokens(...)", "7ff36ab5": "swapExactETHForTokens(...)",
    "3593564c": "execute(bytes,bytes[],uint256) [Universal Router]", "ac9650d8": "multicall(bytes[])",
    "04e45aaf": "exactInputSingle(...) [SwapRouter02]", "a22cb465": "setApprovalForAll(address,bool)",
    "42842e0e": "safeTransferFrom(address,address,uint256)",
}


def rpc(url, method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "eth-tx-inspector"})
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.load(r)
    if "error" in resp:
        raise RuntimeError(resp["error"].get("message"))
    return resp["result"]


def h(v):
    return int(v, 16) if v else 0


def fees(tx, receipt, base_fee):
    gas_used = h(receipt["gasUsed"])
    price = h(receipt.get("effectiveGasPrice") or tx.get("gasPrice"))
    out = {"gas_used": gas_used, "gas_limit": h(tx["gas"]), "price": price, "fee": gas_used * price,
           "priority": max(0, price - base_fee) if base_fee else None}
    if receipt.get("blobGasUsed"):
        out["blob_fee"] = h(receipt["blobGasUsed"]) * h(receipt.get("blobGasPrice"))
    return out


def erc20_transfers(logs):
    out = []
    for log in logs:
        t = log["topics"]
        if len(t) == 3 and t[0] == TRANSFER and log["data"] not in ("0x", ""):
            out.append((log["address"], "0x" + t[1][-40:], "0x" + t[2][-40:], h(log["data"])))
    return out


def token_meta(url, token, cache):
    if token not in cache:
        try:
            raw = bytes.fromhex(rpc(url, "eth_call", [{"to": token, "data": "0x95d89b41"}, "latest"])[2:])
            sym = raw.rstrip(b"\0").decode() if len(raw) == 32 else raw[64:64 + int.from_bytes(raw[32:64], "big")].decode()
            dec = h(rpc(url, "eth_call", [{"to": token, "data": "0x313ce567"}, "latest"]))
        except Exception:
            sym, dec = token[:8], 18
        cache[token] = (sym, dec)
    return cache[token]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hash")
    ap.add_argument("--rpc", default="https://ethereum-rpc.publicnode.com")
    a = ap.parse_args()

    tx = rpc(a.rpc, "eth_getTransactionByHash", [a.hash])
    if not tx:
        raise SystemExit("transaction not found")
    receipt = rpc(a.rpc, "eth_getTransactionReceipt", [a.hash])
    if not receipt:
        print("pending (no receipt yet)")
        return
    block = rpc(a.rpc, "eth_getBlockByNumber", [tx["blockNumber"], False])
    f = fees(tx, receipt, h(block.get("baseFeePerGas")))
    t = h(tx.get("type"))
    gwei = lambda wei: f"{wei / 1e9:.4f} gwei"

    print(f"status     {'success' if h(receipt['status']) == 1 else 'FAILED'}")
    print(f"block      {h(tx['blockNumber'])}  ({time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(h(block['timestamp'])))})")
    print(f"type       {t} {TYPES.get(t, 'unknown')}")
    print(f"from       {tx['from']}  (nonce {h(tx['nonce'])})")
    print(f"to         {tx['to'] or 'contract creation -> ' + receipt.get('contractAddress', '?')}")
    print(f"value      {h(tx['value']) / 1e18:.6f}")
    sel = tx["input"][2:10]
    if sel:
        print(f"method     0x{sel} {SELECTORS.get(sel, '(unknown selector)')}")
    print(f"gas        {f['gas_used']:,} / {f['gas_limit']:,} ({f['gas_used'] / f['gas_limit']:.1%})")
    print(f"gas price  {gwei(f['price'])}" + (f" = base {gwei(h(block['baseFeePerGas']))} + tip {gwei(f['priority'])}" if f["priority"] is not None else ""))
    print(f"fee        {f['fee'] / 1e18:.8f}")
    if t == 3:
        print(f"blobs      {len(tx.get('blobVersionedHashes', []))}, blob fee {f.get('blob_fee', 0) / 1e18:.8f}")
    if t == 4:
        print(f"7702 auths {len(tx.get('authorizationList', []))}")

    transfers = erc20_transfers(receipt["logs"])
    if transfers:
        print(f"\nERC-20 transfers ({len(transfers)})")
        cache = {}
        for token, frm, to, amount in transfers:
            sym, dec = token_meta(a.rpc, token, cache)
            print(f"  {amount / 10 ** dec:>20,.6f} {sym:<8} {frm[:10]}... -> {to[:10]}...")
    print(f"\n{len(receipt['logs'])} logs total")


if __name__ == "__main__":
    main()
