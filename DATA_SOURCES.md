# Data source and reuse

## Original data

- Agency: U.S. Geological Survey (USGS), Earthquake Hazards Program
- Feed: `2.5_month.csv`, real-time M2.5+ earthquake monthly summary CSV
- Original URL: https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_month.csv
- Snapshot downloaded: **2026-10-16 UTC**
- Preserved original snapshot: `data/source/usgs_earthquakes_snapshot.csv`
- Credit: **U.S. Geological Survey**
- Feed documentation: https://earthquake.usgs.gov/earthquakes/feed/v1.0/

## Licensing / public domain

USGS states that data wholly created by U.S. federal employees during official duties are generally U.S. public-domain works and directs USGS publishers to apply CC0 to appropriate datasets where applicable.

- Policy: https://www.usgs.gov/data-management/data-licensing
- USGS reuse guidance: https://pubs.usgs.gov/documentation/faq
- Some USGS-hosted material or contributions from non-federal partners may carry different terms. This demo uses the USGS-generated earthquake feed itself, not third-party imagery, text or logos. It does not imply USGS endorsement.
- Public-domain status within the United States and CC0 are not identical legal statuses worldwide; source-specific terms remain controlling.

## Transformation and synthetic issues

`scripts/prepare_demo.py` deterministically selects the first **180 unique source records** with valid IDs, timestamps and coordinates, splits them into three **English-language CSV files**, and changes header spellings to simulate common export inconsistencies.

For testing *only*, it then adds:
- 6 copied records with duplicate event IDs
- 3 blank event IDs
- 3 non-numeric latitude fields
- 3 blank timestamps

**The added errors are synthetic, not USGS observations.**

`data/input/` and `data/output/` are modified illustrative datasets; never use them for research or hazard decisions.

## Software license

Source code in this repository is MIT licensed. The federal source data retain their original status and are *not* covered by our MIT notice.
