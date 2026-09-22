# Resource links

Local copies listed here were removed from the repository on 21 September 2026 because each can be retrieved from a stable public URL (SEC EDGAR archives are permanent, accession-numbered documents) or is a derived copy of a file that is still stored. Nothing that code parses or that a delivered report links to was removed. The machine-readable record, including full SHA-256 hashes, is [`resource_changes.json`](resource_changes.json); the validators accept a removal only when it appears there. The original files also remain in git history (commit `bef7b32`).

## Restoring and verifying a filing

SEC requires a descriptive `User-Agent` (fair-access policy); set `SEC_USER_AGENT="Name email@domain"` as for `common/code/fetch_company_data.py`. SEC's CDN appends one per-request `<script src="/…">` tag before `</body>`, so a fresh download differs from the archived bytes by that tag only. Verify with the content hash:

```python
import requests
from common.code.preservation import content_sha256
from common.code.fetch_company_data import SEC_HEADERS
data = requests.get(url, headers=SEC_HEADERS, timeout=60).content
assert content_sha256(data) == record["content_sha256"]
```

All 136 retired filings were downloaded on 21 September 2026 and matched their recorded content hash.

## What stays local, and why

| Kept locally | Why |
|---|---|
| SEC XBRL `companyfacts_*.json` and `submissions_*.json` | Live API responses that change with every filing; the dated snapshot cannot be re-fetched. Parsed by the analyses. |
| Daily prices, futures, FX, VIX and FRED series (`data/market_data`, `*/data/raw`) | Vendor series are revised and re-adjusted; parsed directly by every model. |
| Cboe option snapshot, aggregator pages, iShares fund pages, Materion IR PDFs and releases | Live or rotating pages; a later visit cannot reproduce the dated evidence. |
| Earnings-release exhibits (`historical_attribution/sources/earnings/*_release.html`) | Parsed by `event_analysis.py` for dates, EPS and margins. |
| `ELMT_history.html`, `ELMT_financing_8K.html`, `ELMT_2026-08-13_10-Q.html` | Parsed by, or cited by path in, `context_analysis.py` / `ELMT_case.json`. |
| MTRN 10-Ks, the July 2026 10-Q, the 2026 proxy, USGS Mineral Commodity Summaries 2026 and other report evidence | Linked from the delivered investment report; the 2025 10-K is also parsed by `validate_research.py`. |
| Web extracts (`USGS_beryllium_extract.txt`, `BLS_Treasury_web_extract.txt`, `event_and_historical_research_web.txt`) | Primary evidence in their own right; the underlying pages were not downloadable. |
| `data/raw/submissions_MTRN.json` in `historical_attribution` | Byte-identical to `MTRN/data/financial_data/submissions_MTRN.json`, but each study reads its own input snapshot and the endpoint is live. |

## MTRN investment report — SEC filings (9)

Archived for the dated MTRN investment report, but neither parsed by code nor linked from it. Financial values in the report come from the retained XBRL company facts.

| Removed local copy | Form | Filed | Period | Source URL | Content SHA-256 (first 12) |
|---|---|---|---|---|---|
| `report/company_filings/10-Q_2025-05-01_mtrn-20250328.htm` | 10-Q | 2025-05-01 | 2025-03-28 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465725000059/mtrn-20250328.htm> | `df9f61ba7a98` |
| `report/company_filings/10-Q_2025-07-30_mtrn-20250627.htm` | 10-Q | 2025-07-30 | 2025-06-27 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465725000144/mtrn-20250627.htm> | `96f516d45e77` |
| `report/company_filings/10-Q_2025-10-30_mtrn-20250926.htm` | 10-Q | 2025-10-30 | 2025-09-26 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465725000191/mtrn-20250926.htm> | `6345eaa58f99` |
| `report/company_filings/8-K_2026-01-23_mtrn-20260123.htm` | 8-K | 2026-01-23 | 2026-01-23 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465726000002/mtrn-20260123.htm> | `24fe80fcc8be` |
| `report/company_filings/8-K_2026-02-12_mtrn-20260212.htm` | 8-K | 2026-02-12 | 2026-02-12 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465726000006/mtrn-20260212.htm> | `0efd7ccdd9c7` |
| `report/company_filings/10-Q_2026-04-29_mtrn-20260403.htm` | 10-Q | 2026-04-29 | 2026-04-03 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465726000029/mtrn-20260403.htm> | `d4ffd258f4b0` |
| `report/company_filings/8-K_2026-04-29_mtrn-20260429.htm` | 8-K | 2026-04-29 | 2026-04-29 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465726000026/mtrn-20260429.htm> | `1c7efa6bba5f` |
| `report/company_filings/8-K_2026-05-07_mtrn-20260507.htm` | 8-K | 2026-05-07 | 2026-05-07 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465726000031/mtrn-20260507.htm> | `c4be0c382308` |
| `report/company_filings/8-K_2026-08-05_mtrn-20260805.htm` | 8-K | 2026-08-05 | 2026-08-05 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465726000042/mtrn-20260805.htm> | `4245c99b20a4` |

## Historical attribution — earnings 8-K primary documents (119)

The 8-K cover document was fetched only to locate its EX-99 earnings-release exhibit. The exhibit (`<same name>_release.html`) remains local and is what `event_analysis.py` parses; 8-Ks without an exhibit were excluded before any parsing (see `event_exclusions.csv`). The `filing_path` values in `earnings_index.json`, `earnings_announcements.csv` and `event_exclusions.csv` keep these original paths as provenance identifiers.

### MTRN (26)

| Accession | Filed | Source URL | Content SHA-256 (first 12) |
|---|---|---|---|
| 0001104657-21-000008 | 2021-02-18 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465721000008/mtrn-20210218.htm> | `2cbb82152463` |
| 0001104657-21-000042 | 2021-04-29 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465721000042/mtrn-20210429.htm> | `9a4ce86e7140` |
| 0001104657-21-000076 | 2021-08-03 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465721000076/mtrn-20210803.htm> | `3c2d49630cca` |
| 0001104657-21-000104 | 2021-11-02 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465721000104/mtrn-20211102.htm> | `4b656e53e596` |
| 0001104657-22-000015 | 2022-02-17 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465722000015/mtrn-20220217.htm> | `0a04df688377` |
| 0001104657-22-000059 | 2022-04-21 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465722000059/mtrn-20220421.htm> | `a3b3fc1b1db1` |
| 0001104657-22-000070 | 2022-04-28 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465722000070/mtrn-20220428.htm> | `ae982c773a7f` |
| 0001104657-22-000123 | 2022-08-03 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465722000123/mtrn-20220803.htm> | `830f5de62c39` |
| 0001104657-22-000154 | 2022-11-02 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465722000154/mtrn-20221102.htm> | `811b425bdd88` |
| 0001104657-23-000015 | 2023-02-16 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465723000015/mtrn-20230216.htm> | `44d2db6b9b5e` |
| 0001104657-23-000062 | 2023-05-03 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465723000062/mtrn-20230503.htm> | `df7d0915be18` |
| 0001104657-23-000121 | 2023-08-02 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465723000121/mtrn-20230802.htm> | `04c56e25a100` |
| 0001104657-23-000149 | 2023-11-01 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465723000149/mtrn-20231101.htm> | `f82de192ec6b` |
| 0001104657-24-000007 | 2024-01-19 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465724000007/mtrn-20240119.htm> | `c7541cca6d2e` |
| 0001104657-24-000015 | 2024-02-15 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465724000015/mtrn-20240215.htm> | `e875ff4ec21b` |
| 0001104657-24-000063 | 2024-05-02 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465724000063/mtrn-20240501.htm> | `0fe9259f320c` |
| 0001104657-24-000112 | 2024-08-05 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465724000112/mtrn-20240805.htm> | `80b95f0e97fd` |
| 0001104657-24-000143 | 2024-10-30 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465724000143/mtrn-20241030.htm> | `dbc442f638ef` |
| 0001104657-25-000019 | 2025-02-19 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465725000019/mtrn-20250219.htm> | `246e210a4c3e` |
| 0001104657-25-000056 | 2025-05-01 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465725000056/mtrn-20250501.htm> | `4a2ccc5d0bb1` |
| 0001104657-25-000140 | 2025-07-30 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465725000140/mtrn-20250730.htm> | `3fa07a537361` |
| 0001104657-25-000186 | 2025-10-29 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465725000186/mtrn-20251029.htm> | `4a1e2890ebe9` |
| 0001104657-26-000002 | 2026-01-23 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465726000002/mtrn-20260123.htm> | `24fe80fcc8be` |
| 0001104657-26-000006 | 2026-02-12 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465726000006/mtrn-20260212.htm> | `0efd7ccdd9c7` |
| 0001104657-26-000026 | 2026-04-29 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465726000026/mtrn-20260429.htm> | `1c7efa6bba5f` |
| 0001104657-26-000042 | 2026-08-05 | <https://www.sec.gov/Archives/edgar/data/1104657/000110465726000042/mtrn-20260805.htm> | `4245c99b20a4` |

### ENTG (23)

| Accession | Filed | Source URL | Content SHA-256 (first 12) |
|---|---|---|---|
| 0001101302-21-000004 | 2021-02-02 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130221000004/entg-20210202.htm> | `cdbb67b2cfe0` |
| 0001101302-21-000036 | 2021-04-27 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130221000036/entg-20210427.htm> | `c0227dba374a` |
| 0001101302-21-000064 | 2021-07-27 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130221000064/entg-20210727.htm> | `866f6afb6dbf` |
| 0001101302-21-000075 | 2021-10-26 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130221000075/entg-20211026.htm> | `0e66df503855` |
| 0001101302-22-000006 | 2022-02-01 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130222000006/entg-20220201.htm> | `4ed6761abc55` |
| 0001101302-22-000021 | 2022-04-26 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130222000021/entg-20220426.htm> | `9d8060ed9dd9` |
| 0001101302-22-000038 | 2022-08-02 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130222000038/entg-20220802.htm> | `35d481ca6bd4` |
| 0001101302-22-000047 | 2022-11-02 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130222000047/entg-20221102.htm> | `9550c0f80a59` |
| 0001101302-23-000016 | 2023-02-14 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130223000016/entg-20230214.htm> | `b42376d4e4f1` |
| 0001101302-23-000065 | 2023-05-11 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130223000065/entg-20230511.htm> | `250782a8224c` |
| 0001101302-23-000077 | 2023-08-03 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130223000077/entg-20230803.htm> | `8a42822aded9` |
| 0001101302-23-000086 | 2023-11-02 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130223000086/entg-20231102.htm> | `bac896ce1c99` |
| 0001101302-24-000005 | 2024-02-13 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130224000005/entg-20240213.htm> | `06d76a58b1f8` |
| 0001101302-24-000037 | 2024-05-01 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130224000037/entg-20240501.htm> | `3b734f40ffa9` |
| 0001101302-24-000049 | 2024-07-31 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130224000049/entg-20240731.htm> | `d22419769c19` |
| 0001101302-24-000071 | 2024-11-04 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130224000071/entg-20241104.htm> | `1040d0e21058` |
| 0001101302-25-000010 | 2025-02-06 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130225000010/entg-20250206.htm> | `0996c844aa86` |
| 0001101302-25-000056 | 2025-05-07 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130225000056/entg-20250507.htm> | `e389f9145cd3` |
| 0001101302-25-000075 | 2025-07-30 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130225000075/entg-20250730.htm> | `79116ed24000` |
| 0001101302-25-000099 | 2025-10-30 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130225000099/entg-20251030.htm> | `4439fcd9ed04` |
| 0001101302-26-000009 | 2026-02-10 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130226000009/entg-20260210.htm> | `ad528a29b923` |
| 0001101302-26-000099 | 2026-04-30 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130226000099/entg-20260430.htm> | `d1739cba3c9b` |
| 0001101302-26-000146 | 2026-08-04 | <https://www.sec.gov/Archives/edgar/data/1101302/000110130226000146/entg-20260804.htm> | `015c502ac1ef` |

### CRS (47)

| Accession | Filed | Source URL | Content SHA-256 (first 12) |
|---|---|---|---|
| 0001193125-21-022687 | 2021-01-29 | <https://www.sec.gov/Archives/edgar/data/17843/000119312521022687/d105662d8k.htm> | `49c11520df3e` |
| 0001193125-21-022699 | 2021-01-29 | <https://www.sec.gov/Archives/edgar/data/17843/000119312521022699/d104186d8k.htm> | `7bc436eaf303` |
| 0001193125-21-143405 | 2021-04-30 | <https://www.sec.gov/Archives/edgar/data/17843/000119312521143405/d183656d8k.htm> | `edca6fa94955` |
| 0001193125-21-143444 | 2021-04-30 | <https://www.sec.gov/Archives/edgar/data/17843/000119312521143444/d184196d8k.htm> | `e57abb1a5901` |
| 0001193125-21-230646 | 2021-07-30 | <https://www.sec.gov/Archives/edgar/data/17843/000119312521230646/d201492d8k.htm> | `2aa5b01c6f25` |
| 0001193125-21-230653 | 2021-07-30 | <https://www.sec.gov/Archives/edgar/data/17843/000119312521230653/d201506d8k.htm> | `abfd317156e7` |
| 0001193125-21-311248 | 2021-10-28 | <https://www.sec.gov/Archives/edgar/data/17843/000119312521311248/d247726d8k.htm> | `c749cf93a9f2` |
| 0001193125-21-311250 | 2021-10-28 | <https://www.sec.gov/Archives/edgar/data/17843/000119312521311250/d250803d8k.htm> | `e60c2d318613` |
| 0001193125-22-026962 | 2022-02-03 | <https://www.sec.gov/Archives/edgar/data/17843/000119312522026962/d286593d8k.htm> | `325de483d180` |
| 0001193125-22-027079 | 2022-02-03 | <https://www.sec.gov/Archives/edgar/data/17843/000119312522027079/d262603d8k.htm> | `33fdd50e43d7` |
| 0001193125-22-132928 | 2022-04-29 | <https://www.sec.gov/Archives/edgar/data/17843/000119312522132928/d766354d8k.htm> | `b4cd3038f1b2` |
| 0001193125-22-133041 | 2022-04-29 | <https://www.sec.gov/Archives/edgar/data/17843/000119312522133041/d766378d8k.htm> | `46966f050fdf` |
| 0001193125-22-209798 | 2022-08-02 | <https://www.sec.gov/Archives/edgar/data/17843/000119312522209798/d385150d8k.htm> | `c8d6a386b14e` |
| 0001193125-22-209829 | 2022-08-02 | <https://www.sec.gov/Archives/edgar/data/17843/000119312522209829/d369415d8k.htm> | `aedddebb2100` |
| 0001193125-22-262260 | 2022-10-13 | <https://www.sec.gov/Archives/edgar/data/17843/000119312522262260/d381569d8k.htm> | `60ab0ce012a8` |
| 0001193125-22-275047 | 2022-11-01 | <https://www.sec.gov/Archives/edgar/data/17843/000119312522275047/d418712d8k.htm> | `c98a5973b0e1` |
| 0001193125-22-275056 | 2022-11-01 | <https://www.sec.gov/Archives/edgar/data/17843/000119312522275056/d415706d8k.htm> | `f82cf060b7fd` |
| 0001193125-23-017576 | 2023-01-27 | <https://www.sec.gov/Archives/edgar/data/17843/000119312523017576/d405718d8k.htm> | `7bab43492b60` |
| 0001193125-23-017580 | 2023-01-27 | <https://www.sec.gov/Archives/edgar/data/17843/000119312523017580/d342851d8k.htm> | `5da30ffac80d` |
| 0001193125-23-130465 | 2023-05-01 | <https://www.sec.gov/Archives/edgar/data/17843/000119312523130465/d439871d8k.htm> | `497e4f087ad1` |
| 0001193125-23-130466 | 2023-05-01 | <https://www.sec.gov/Archives/edgar/data/17843/000119312523130466/d383627d8k.htm> | `cf7f66224046` |
| 0001193125-23-199106 | 2023-07-31 | <https://www.sec.gov/Archives/edgar/data/17843/000119312523199106/d511145d8k.htm> | `bb7490f86638` |
| 0001193125-23-199107 | 2023-07-31 | <https://www.sec.gov/Archives/edgar/data/17843/000119312523199107/d469319d8k.htm> | `f7bf9d9d4d8a` |
| 0001193125-23-267221 | 2023-10-31 | <https://www.sec.gov/Archives/edgar/data/17843/000119312523267221/d549448d8k.htm> | `8158f1dbb92c` |
| 0001193125-23-267222 | 2023-10-31 | <https://www.sec.gov/Archives/edgar/data/17843/000119312523267222/d543191d8k.htm> | `228eadacea9f` |
| 0001193125-24-018111 | 2024-01-29 | <https://www.sec.gov/Archives/edgar/data/17843/000119312524018111/d890653d8k.htm> | `6b30a26fb739` |
| 0001193125-24-018118 | 2024-01-29 | <https://www.sec.gov/Archives/edgar/data/17843/000119312524018118/d917906d8k.htm> | `7adec0fc12e0` |
| 0001193125-24-130672 | 2024-05-03 | <https://www.sec.gov/Archives/edgar/data/17843/000119312524130672/d631283d8k.htm> | `20d8471252ea` |
| 0001193125-24-130676 | 2024-05-03 | <https://www.sec.gov/Archives/edgar/data/17843/000119312524130676/d825973d8k.htm> | `d01a9a4d4c87` |
| 0001193125-24-187540 | 2024-07-29 | <https://www.sec.gov/Archives/edgar/data/17843/000119312524187540/d817637d8k.htm> | `fcd4fdbada22` |
| 0001193125-24-187545 | 2024-07-29 | <https://www.sec.gov/Archives/edgar/data/17843/000119312524187545/d873646d8k.htm> | `ee11755c930c` |
| 0001193125-24-246614 | 2024-10-29 | <https://www.sec.gov/Archives/edgar/data/17843/000119312524246614/d899707d8k.htm> | `495e88c214f5` |
| 0001193125-24-246616 | 2024-10-29 | <https://www.sec.gov/Archives/edgar/data/17843/000119312524246616/d901819d8k.htm> | `6992b6d08d76` |
| 0001193125-25-019378 | 2025-02-03 | <https://www.sec.gov/Archives/edgar/data/17843/000119312525019378/d899171d8k.htm> | `6c7e139af5de` |
| 0001193125-25-019386 | 2025-02-03 | <https://www.sec.gov/Archives/edgar/data/17843/000119312525019386/d901198d8k.htm> | `35d4b0397516` |
| 0001193125-25-103769 | 2025-04-29 | <https://www.sec.gov/Archives/edgar/data/17843/000119312525103769/d809330d8k.htm> | `ccf5e9c666bb` |
| 0001193125-25-103787 | 2025-04-29 | <https://www.sec.gov/Archives/edgar/data/17843/000119312525103787/d807987d8k.htm> | `df79598a7f50` |
| 0001193125-25-174450 | 2025-08-06 | <https://www.sec.gov/Archives/edgar/data/17843/000119312525174450/d80170d8k.htm> | `a1b283cd8ae5` |
| 0001193125-25-174452 | 2025-08-06 | <https://www.sec.gov/Archives/edgar/data/17843/000119312525174452/d78576d8k.htm> | `8053641c08b6` |
| 0000017843-25-000031 | 2025-10-23 | <https://www.sec.gov/Archives/edgar/data/17843/000001784325000031/crs-20251023.htm> | `fbd9c55bb9af` |
| 0000017843-25-000034 | 2025-10-23 | <https://www.sec.gov/Archives/edgar/data/17843/000001784325000034/crs-20251023.htm> | `7bfedc24ac37` |
| 0000017843-26-000005 | 2026-01-29 | <https://www.sec.gov/Archives/edgar/data/17843/000001784326000005/crs-20260129.htm> | `b8003724fad8` |
| 0000017843-26-000007 | 2026-01-29 | <https://www.sec.gov/Archives/edgar/data/17843/000001784326000007/crs-20260129.htm> | `292493ea2520` |
| 0000017843-26-000016 | 2026-04-29 | <https://www.sec.gov/Archives/edgar/data/17843/000001784326000016/crs-20260429.htm> | `01c5504dc6ba` |
| 0000017843-26-000018 | 2026-04-29 | <https://www.sec.gov/Archives/edgar/data/17843/000001784326000018/crs-20260429.htm> | `188b9a038530` |
| 0000017843-26-000028 | 2026-07-30 | <https://www.sec.gov/Archives/edgar/data/17843/000001784326000028/crs-20260730.htm> | `a21af43a255c` |
| 0000017843-26-000030 | 2026-07-30 | <https://www.sec.gov/Archives/edgar/data/17843/000001784326000030/crs-20260730.htm> | `e896e3da6da8` |

### ATI (23)

| Accession | Filed | Source URL | Content SHA-256 (first 12) |
|---|---|---|---|
| 0001628280-21-000940 | 2021-01-28 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828021000940/ati-20210128.htm> | `c1e72a85187f` |
| 0001628280-21-008035 | 2021-04-29 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828021008035/ati-20210429.htm> | `31076368981c` |
| 0001628280-21-015240 | 2021-08-03 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828021015240/ati-20210803.htm> | `9040bc5b9d85` |
| 0001628280-21-020694 | 2021-10-28 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828021020694/ati-20211028.htm> | `ac112dc0c096` |
| 0001628280-22-001628 | 2022-02-02 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828022001628/ati-20220202.htm> | `f21b8dd8c196` |
| 0001628280-22-012142 | 2022-05-04 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828022012142/ati-20220504.htm> | `6871771e6af1` |
| 0001628280-22-020867 | 2022-08-04 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828022020867/ati-20220804.htm> | `2905308442ff` |
| 0001628280-22-027662 | 2022-11-02 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828022027662/ati-20221102.htm> | `062bb10c27b1` |
| 0001628280-23-001965 | 2023-02-02 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828023001965/ati-20230202.htm> | `049f3fb74ad5` |
| 0001628280-23-015453 | 2023-05-04 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828023015453/ati-20230504.htm> | `58eb5b966436` |
| 0001628280-23-026573 | 2023-08-02 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828023026573/ati-20230802.htm> | `a24dbb9faa5f` |
| 0001628280-23-036216 | 2023-11-02 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828023036216/ati-20231102.htm> | `d818b4c4185a` |
| 0001628280-24-002807 | 2024-02-01 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828024002807/ati-20240201.htm> | `156315310752` |
| 0001628280-24-019185 | 2024-04-30 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828024019185/ati-20240430.htm> | `2757764bda37` |
| 0001628280-24-034973 | 2024-08-06 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828024034973/ati-20240806.htm> | `084833c4ee58` |
| 0001628280-24-044003 | 2024-10-29 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828024044003/ati-20241029.htm> | `487260422cf6` |
| 0001628280-25-003579 | 2025-02-04 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828025003579/ati-20250204.htm> | `16913d7ce5ff` |
| 0001628280-25-021324 | 2025-05-01 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828025021324/ati-20250501.htm> | `1d74224a6f43` |
| 0001628280-25-036845 | 2025-07-31 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828025036845/ati-20250731.htm> | `36b342fc9ecb` |
| 0001628280-25-046559 | 2025-10-28 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828025046559/ati-20251028.htm> | `2a6ba9881f48` |
| 0001628280-26-004793 | 2026-02-03 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828026004793/ati-20260203.htm> | `00599170da9e` |
| 0001628280-26-028589 | 2026-04-30 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828026028589/ati-20260430.htm> | `a9635a89c00a` |
| 0001628280-26-053856 | 2026-08-06 | <https://www.sec.gov/Archives/edgar/data/1018963/000162828026053856/ati-20260806.htm> | `73fee672b04b` |

## Historical attribution — ELMT SEC filings (8)

Context for the Elmet short-history and financing case. The values the study uses are recorded in `data/processed/ELMT_case.json`; the 13 August 2026 10-Q it cites stays local.

| Removed local copy | Form | Filed | Source URL | Content SHA-256 (first 12) |
|---|---|---|---|---|
| `sources/ELMT_2026-04-23_424B4.html` | 424B4 | 2026-04-23 | <https://www.sec.gov/Archives/edgar/data/2101698/000121390026047144/ea0270360-06.htm> | `b558268ac377` |
| `sources/ELMT_2026-04-24_8-K.html` | 8-K | 2026-04-24 | <https://www.sec.gov/Archives/edgar/data/2101698/000121390026047521/ea0287495-8k_elmet.htm> | `6f92af9693f4` |
| `sources/ELMT_2026-05-26_8-K.html` | 8-K | 2026-05-26 | <https://www.sec.gov/Archives/edgar/data/2101698/000121390026060728/ea0291413-8k_elmet.htm> | `01a059a65185` |
| `sources/ELMT_2026-05-29_10-Q.html` | 10-Q | 2026-05-29 | <https://www.sec.gov/Archives/edgar/data/2101698/000121390026062433/ea0291959-10q_elmet.htm> | `cc9d439a085a` |
| `sources/ELMT_2026-05-29_8-K.html` | 8-K | 2026-05-29 | <https://www.sec.gov/Archives/edgar/data/2101698/000121390026062434/ea0292205-8k_elmet.htm> | `0191bc026833` |
| `sources/ELMT_2026-08-13_8-K.html` | 8-K | 2026-08-13 | <https://www.sec.gov/Archives/edgar/data/2101698/000121390026088714/ea0301662-8k_elmet.htm> | `838cc148623e` |
| `sources/ELMT_2026-09-08_8-K.html` | 8-K | 2026-09-08 | <https://www.sec.gov/Archives/edgar/data/2101698/000121390026097862/ea0304152-8k_elmet.htm> | `1a4e53764cb2` |
| `sources/ELMT_2026-09-14_8-K.html` | 8-K | 2026-09-14 | <https://www.sec.gov/Archives/edgar/data/2101698/000121390026099734/ea0304682-8k_elmet.htm> | `d93a27a6a121` |

## Removed derived copies (24)

Plain-text renderings and working excerpts produced from documents that are still stored. No code, report or table read them. Regenerate a rendering with any HTML/PDF text extractor from the listed original.

| Removed file | Derived from (retained) |
|---|---|
| `report/company_filings/10-K_2022-02-17_mtrn-20211231.txt` | report/company_filings/10-K_2022-02-17_mtrn-20211231.htm |
| `report/company_filings/10-K_2023-02-16_mtrn-20221231.txt` | report/company_filings/10-K_2023-02-16_mtrn-20221231.htm |
| `report/company_filings/10-K_2024-02-15_mtrn-20231231.txt` | report/company_filings/10-K_2024-02-15_mtrn-20231231.htm |
| `report/company_filings/10-K_2025-02-19_mtrn-20241231.txt` | report/company_filings/10-K_2025-02-19_mtrn-20241231.htm |
| `report/company_filings/10-K_2026-02-12_mtrn-20251231.txt` | report/company_filings/10-K_2026-02-12_mtrn-20251231.htm |
| `report/company_filings/10-Q_2025-05-01_mtrn-20250328.txt` | report/company_filings/10-Q_2025-05-01_mtrn-20250328.htm |
| `report/company_filings/10-Q_2025-07-30_mtrn-20250627.txt` | report/company_filings/10-Q_2025-07-30_mtrn-20250627.htm |
| `report/company_filings/10-Q_2025-10-30_mtrn-20250926.txt` | report/company_filings/10-Q_2025-10-30_mtrn-20250926.htm |
| `report/company_filings/10-Q_2026-04-29_mtrn-20260403.txt` | report/company_filings/10-Q_2026-04-29_mtrn-20260403.htm |
| `report/company_filings/10-Q_2026-08-05_mtrn-20260703.txt` | report/company_filings/10-Q_2026-08-05_mtrn-20260703.htm |
| `report/company_filings/8-K_2026-01-23_mtrn-20260123.txt` | report/company_filings/8-K_2026-01-23_mtrn-20260123.htm |
| `report/company_filings/8-K_2026-02-12_mtrn-20260212.txt` | report/company_filings/8-K_2026-02-12_mtrn-20260212.htm |
| `report/company_filings/8-K_2026-04-29_mtrn-20260429.txt` | report/company_filings/8-K_2026-04-29_mtrn-20260429.htm |
| `report/company_filings/8-K_2026-05-07_mtrn-20260507.txt` | report/company_filings/8-K_2026-05-07_mtrn-20260507.htm |
| `report/company_filings/8-K_2026-08-05_mtrn-20260805.txt` | report/company_filings/8-K_2026-08-05_mtrn-20260805.htm |
| `report/company_filings/DEF14A_2026-03-26_mtrn-20260326.txt` | report/company_filings/DEF14A_2026-03-26_mtrn-20260326.htm |
| `report/earnings_materials/FY2025_release.txt` | report/earnings_materials/FY2025_release.htm |
| `report/earnings_materials/May_2026_investor.txt` | report/earnings_materials/May_2026_investor.pdf |
| `report/earnings_materials/Q1_2026_release.txt` | report/earnings_materials/Q1_2026_release.htm |
| `report/earnings_materials/Q2_2026_presentation.txt` | report/earnings_materials/Q2_2026_presentation.pdf |
| `report/earnings_materials/Q2_2026_release.txt` | report/earnings_materials/Q2_2026_release.htm |
| `data/processed_data/excerpts_K.txt` | text extracts of the retained MTRN filings (form K) |
| `data/processed_data/excerpts_Proxy.txt` | text extracts of the retained MTRN filings (form Proxy) |
| `data/processed_data/excerpts_Q.txt` | text extracts of the retained MTRN filings (form Q) |
