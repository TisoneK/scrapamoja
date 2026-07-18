# LiveFeed `Get1x2_VZip` — decoded sample

Endpoint: `GET /service-api/LiveFeed/Get1x2_VZip?count=10&lng=en&gr=650&mode=4&country=87&top=true&partner=189&virtualSports=true&noFilterBlockEvent=true`

One trimmed live event (public odds; captured 2026-07-18 via Kenya proxy). Key legend is in `../../RECON.md`.

```json
{
  "Success": true,
  "note": "one live event from Get1x2_VZip, trimmed for schema reference (public odds data; no cookies/tokens)",
  "Value": [
    {
      "R": 300,
      "SC": {
        "FS": {
          "S1": 118,
          "S2": 126
        },
        "PS": [
          {
            "Key": 1,
            "Value": {
              "S1": 19,
              "S2": 20,
              "NF": "1st quarter"
            }
          },
          {
            "Key": 2,
            "Value": {
              "S1": 21,
              "S2": 38,
              "NF": "2nd quarter"
            }
          },
          {
            "Key": 3,
            "Value": {
              "S1": 33,
              "S2": 34,
              "NF": "3rd quarter"
            }
          },
          {
            "Key": 4,
            "Value": {
              "S1": 42,
              "S2": 23,
              "NF": "4th quarter"
            }
          },
          {
            "Key": 5,
            "Value": {
              "S1": 3,
              "S2": 11,
              "N": "1 Overtime",
              "NF": "1 Overtime"
            }
          }
        ],
        "CP": 5,
        "CPS": "1 Overtime",
        "TS": 68,
        "TD": -1,
        "TR": -1,
        "I": "",
        "ST": "<statistics[] omitted>",
        "SLS": "2 min remaining"
      },
      "ZP": 737248980,
      "HMH": 1,
      "INS": true,
      "U": 1784350799,
      "I": 737248980,
      "N": 240458,
      "T": 300,
      "CO": 9,
      "E": [
        {
          "T": 402,
          "C": 1.025,
          "CV": "1.025",
          "B": true,
          "G": 101
        },
        {
          "T": 7,
          "P": 7.5,
          "C": 1.825,
          "CV": "1.825",
          "B": true,
          "G": 2
        },
        {
          "T": 8,
          "P": -7.5,
          "C": 1.98,
          "CV": "1.98",
          "B": true,
          "G": 2
        },
        {
          "T": 401,
          "C": 12.5,
          "CV": "12.5",
          "B": true,
          "G": 101
        }
      ],
      "AE": [
        {
          "G": 2,
          "ME": [
            {
              "T": 8,
              "P": -7.5,
              "C": 1.98,
              "CV": "1.98",
              "B": true,
              "G": 2,
              "CE": 1
            },
            {
              "T": 7,
              "P": 7.5,
              "C": 1.825,
              "CV": "1.825",
              "B": true,
              "G": 2,
              "CE": 1
            }
          ]
        }
      ],
      "EC": 4,
      "TG": "",
      "V": "Including Overtime",
      "VE": "Including Overtime",
      "PN": "",
      "TN": "Quarter",
      "DI": "",
      "SS": 3,
      "HSRT": true,
      "SST": 1,
      "HSI": true,
      "STI": "6a5903825e99bd05c64ec84e",
      "S": 1784342700,
      "O1": "Minnesota Timberwolves",
      "O2": "Los Angeles Clippers",
      "O1I": 6882,
      "O2I": 6892,
      "O1C": 153,
      "O1CT": "Minneapolis",
      "O2C": 153,
      "O2CT": "Los Angeles",
      "O1E": "Minnesota Timberwolves",
      "O2E": "Los Angeles Clippers",
      "SI": 3,
      "SN": "Basketball",
      "L": "NBA. Summer League",
      "LI": 75093,
      "CN": "United States",
      "COI": 153,
      "HLU": true,
      "SGI": "6a5903825e99bd05c64ec84d",
      "KI": 1,
      "CID": 1,
      "IV": 12,
      "SmI": 23197,
      "HHTHS": true,
      "TNS": "Quarters",
      "SUBA": true
    }
  ]
}
```
