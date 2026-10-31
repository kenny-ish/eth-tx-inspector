# eth-tx-inspector

Shows the details of one EVM transaction in the terminal, using only JSON-RPC.

```bash
python tx.py 0x<hash>
python tx.py 0x<hash> --rpc https://mainnet.base.org
```

It reports

- status, block, timestamp, from and to (or the created contract), value and nonce
- the transaction type: legacy, EIP-2930, EIP-1559, EIP-4844 blob or EIP-7702 set-code, with the
  blob count and blob fee or the number of 7702 authorizations
- gas limit and gas used, the effective gas price, the block's base fee and the priority fee the
  sender paid on top, and the total fee in the native token
- the function called, when the 4-byte selector is a common one (transfers, approvals, WETH, v2
  swaps, Universal Router `execute`, `multicall`)
- every ERC-20 `Transfer` in the receipt, with token symbol and amount

It calls `eth_getTransactionByHash`, `eth_getTransactionReceipt` and `eth_getBlockByNumber`, plus
`symbol()` and `decimals()` for tokens that appear in the logs.

## Tests

```bash
python -m unittest -v
```
