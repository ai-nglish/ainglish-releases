# CLARIN / VLO discovery hand-off

## Recommended route

Publish the prepared Ainglish training-pack listing through Mozilla Data Collective first. CLARIN
announced in July 2026 that Mozilla Data Collective metadata is indexed by the Virtual Language
Observatory (VLO), while the data remains hosted and governed at Mozilla. That route gives this one
small static dataset a reviewed datasheet and CLARIN discovery without inventing a direct repository
deposit or operating an OAI-PMH endpoint.

After the Mozilla listing is live:

1. record its stable public URL;
2. wait for the next VLO harvest;
3. search VLO for the exact title `Ainglish training pack v3`;
4. verify version, language, licence, creator, resource type and landing-page URL; and
5. record the observed VLO URL and date. Until step 4 succeeds, describe VLO indexing as planned,
   not completed.

## Metadata values

| Discovery field | Value |
|---|---|
| Title | Ainglish training pack v3 |
| Alternative title | Ainglish release 3 public-domain training data |
| Description | Train-only JSONL, Parquet, Dolma and Croissant projections of 19 ratified Ainglish agent-communication constructs and 63 reviewed Ainglish to careful-English usage pairs, bound to a frozen source release. |
| Resource type | Corpus / dataset |
| Modality | Written language |
| Language | English (`en`) |
| Script / encoding | Latin; UTF-8 |
| Subject | controlled language; natural-language processing; agent communication; training data; artificial intelligence |
| Version | 3 |
| Publication date | 2026-09-02 |
| Creator | The Ainglish Project |
| Publisher / rights holder | Starsol Ltd, company number 06002018 |
| Licence | CC0-1.0 |
| Access | Public / unrestricted by the dataset licence |
| Landing page | https://ainglish.org/training |
| Download / manifest | https://ainglish.org/training/ainglish-training-v3/MANIFEST.json |
| Croissant metadata | https://ainglish.org/training/ainglish-training-v3/metadata/croissant.json |
| Related source release | https://ainglish.org/releases/ainglish-core-v3/MANIFEST.json |
| Related source DOI | https://doi.org/10.5281/zenodo.22095468 |
| Register digest | `ee8978f9ab5adb252aa244dc1a0dbb5abaa81f499758ec18c95caf5dcfa863b8` |
| Contact | `[authorised human uploader: full legal name and organisation email]` |

The listed DOI identifies the related core language release, not this training pack. Do not enter it
as the training pack's own identifier. Use the Mozilla listing URL or a separately minted persistent
identifier if the repository assigns one.

## Direct CLARIN alternative

If Mozilla declines the listing, CLARIN's guidance for a few static records is to submit metadata to
the Language Resource Inventory, which is converted to CMDI for VLO discovery. A deposit at a
CLARIN B-centre is another route when long-term repository preservation is wanted. Give the curator
the field table above, the pack datasheet, the archive, and the public artifact URLs.

Do not manufacture a CMDI file before choosing a receiving repository. A valid CMDI record needs a
repository-specific metadata profile and self-link or persistent identifier, and its Resources
section should point explicitly to the files or landing page it describes. Those values belong to
the receiving centre's workflow. If a curator requests a CMDI draft, obtain the chosen profile ID
and assigned self-link first, then map the values above into that profile.

## Acceptance check

A successful discovery record must show all of the following without relying on free-text search:

- exact title and version;
- English written-language resource / corpus classification;
- CC0-1.0 and public access;
- Starsol Ltd as publisher and the Ainglish Project as creator;
- a live landing page or resource link;
- the release-3 source relationship; and
- no assertion that VLO, CLARIN or Mozilla independently validated Ainglish comprehension.
