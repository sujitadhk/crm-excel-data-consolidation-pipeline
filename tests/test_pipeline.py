import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pipeline import clean_customers, parse_mixed_dates  # noqa: E402


def test_mixed_dates_parsed():
    s = pd.Series(["2024-03-05", "05/03/2024", "Mar 05, 2024"])
    assert parse_mixed_dates(s).nunique() == 1


def test_country_standardised_and_dupes_removed():
    crm = pd.DataFrame({"CustomerID": ["C1", "C1"], "Full Name": [" A B ", " A B "],
                        "Email": ["A@X.COM", "A@X.COM"], "Country": ["NEPAL", "NEPAL"],
                        "Segment": ["SMB", "SMB"], "Signup Date": ["2024-01-01", "2024-01-01"]})
    df, stats = clean_customers(crm)
    assert len(df) == 1 and stats["duplicates_removed"] == 1
    assert df.iloc[0]["country"] == "Nepal" and df.iloc[0]["email"] == "a@x.com"
