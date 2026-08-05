import pandas as pd
import numpy as np
import os

class DataLoader:
    """
    Responsible for finding, reading and cleaning the three source
    Excel catalogues (Dataset A, B and C) used by the rest of the system.

    Why this class exists:
        Each dataset comes from a different source spreadsheet with its
        own column names, quirks and missing-data patterns. Keeping all
        of that "cleaning" logic in one place means the rest of the
        codebase (predicate_engine, fuzzy_engine, scenarios, etc.) can
        assume it always receives a tidy, consistently-typed DataFrame,
        instead of every module having to defend against messy input.
    """

    def __init__(self, base_dir=None):
        # If the caller doesn't supply a folder, default to the "Dataset"
        # subfolder that sits next to this .py file. Using the file's own
        # location (rather than the current working directory) means the
        # loader still finds the data even if the script is run from
        # somewhere else on disk.
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Dataset")
        self.base_dir = base_dir

        # Pre-compute the full path to each of the three source workbooks
        # so the load_* methods below don't have to repeat this logic.
        self.path_a = os.path.join(base_dir, "BTIS3043_Dataset_A_Existing_eBook_Collection.xlsx")
        self.path_b = os.path.join(base_dir, "BTIS3043_Dataset_B_Academic_eBook_Catalogue.xlsx")
        self.path_c = os.path.join(base_dir, "BTIS3043_Dataset_C_eBook_Acquisition_Catalogue.xlsx")

    def load_dataset_a(self):
        """Loads and cleans Dataset A (Existing eBook Collection - Current Subscriptions)"""
        # Fail fast with a clear error if the file simply isn't there,
        # rather than letting pandas raise a more cryptic error later.
        if not os.path.exists(self.path_a):
            raise FileNotFoundError(f"Dataset A not found at {self.path_a}")

        df = pd.read_excel(self.path_a)
        # Strip stray leading/trailing whitespace from column headers
        # (common in hand-maintained spreadsheets) so later code can
        # refer to columns by exact name without guessing.
        df.columns = df.columns.str.strip()

        # Standardize columns: force numeric-looking columns to actual
        # numeric dtypes. errors='coerce' turns anything unparsable
        # (typos, blank cells, text) into NaN instead of crashing, so a
        # few dirty cells don't stop the whole dataset from loading.
        df['No.'] = pd.to_numeric(df['No.'], errors='coerce')
        df['Copyright Year'] = pd.to_numeric(df['Copyright Year'], errors='coerce')
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')

        # Fill missing values: replace blank Title/Author/Recommended-by
        # cells with an explicit placeholder so downstream string
        # matching (predicate/fuzzy engines) never has to special-case
        # NaN, and strip whitespace for consistent text comparisons.
        df['Title'] = df['Title'].fillna("Unknown Title").str.strip()
        df['Author'] = df['Author'].fillna("Unknown Author").str.strip()
        df['Recommended by'] = df['Recommended by'].fillna("Unknown").str.strip()

        # Drop duplicates on key column No.: rows with no record number
        # can't be reliably identified, so they're removed; remaining
        # rows are de-duplicated by that ID and the index is reset so
        # downstream code gets clean, contiguous row numbers.
        df = df.dropna(subset=['No.'])
        df = df.drop_duplicates(subset=['No.']).reset_index(drop=True)

        return df

    def load_dataset_b(self):
        """Loads and cleans Dataset B (Academic eBook Catalogue)"""
        if not os.path.exists(self.path_b):
            raise FileNotFoundError(f"Dataset B not found at {self.path_b}")

        df = pd.read_excel(self.path_b)
        df.columns = df.columns.str.strip()

        # Clean fields: coerce the publication year to numeric, and
        # backfill missing Title/Author/Format text so no code downstream
        # ever compares against a bare NaN.
        df['Copyright'] = pd.to_numeric(df['Copyright'], errors='coerce')
        df['Title'] = df['Title'].fillna("Unknown Title").str.strip()
        df['Author'] = df['Author'].fillna("Unknown Author").str.strip()
        df['eBook Format'] = df['eBook Format'].fillna("Unknown Format").str.strip()

        # Fill discipline levels: Dataset B classifies each book with up
        # to four nested discipline levels (e.g. Level 1 = broad subject,
        # Level 4 = most specific). Any level that's missing is set to
        # the literal string "None" (not NaN) so it can still be safely
        # concatenated into search text elsewhere without errors.
        for col in ['Discipline (Level 1)', 'Discipline (Level 2)', 'Discipline (Level 3)', 'Discipline (Level 4)']:
            if col in df.columns:
                df[col] = df[col].fillna("None").astype(str).str.strip()

        # Drop duplicates on key column eBook ISBN (removed to preserve catalogue duplicates)
        # Rows without an ISBN can't be identified, so those are dropped,
        # but rows that happen to share an ISBN are intentionally kept
        # (e.g. multiple catalogue entries for the same title are valid).
        df = df.dropna(subset=['eBook ISBN']).reset_index(drop=True)

        return df

    def load_dataset_c(self):
        """Loads and cleans Dataset C (Licensing Catalogue)"""
        if not os.path.exists(self.path_c):
            raise FileNotFoundError(f"Dataset C not found at {self.path_c}")

        df = pd.read_excel(self.path_c)
        df.columns = df.columns.str.strip()

        # Clean fields: Dataset C is the only dataset with pricing info,
        # so its price column is coerced to numeric alongside the year;
        # text fields get the same missing-value/whitespace treatment as
        # in the other two loaders, for consistent behaviour system-wide.
        df['Copyright Year'] = pd.to_numeric(df['Copyright Year'], errors='coerce')
        df['April List Price (USD)'] = pd.to_numeric(df['April List Price (USD)'], errors='coerce')
        df['Title'] = df['Title'].fillna("Unknown Title").str.strip()
        df['Author'] = df['Author'].fillna("Unknown Author").str.strip()
        df['eBook Format'] = df['eBook Format'].fillna("Unknown Format").str.strip()
        df['Category'] = df['Category'].fillna("None").astype(str).str.strip()
        df['Discipline'] = df['Discipline'].fillna("None").astype(str).str.strip()

        # Drop duplicates on key column VBID (removed to preserve catalogue duplicates)
        # No de-duplication is applied here (unlike Dataset A) - licensing
        # entries that repeat a vendor/book ID are treated as legitimate
        # separate catalogue lines, not accidental duplicates.
        df = df.reset_index(drop=True)

        return df

if __name__ == "__main__":
    # Simple manual smoke test: load all three datasets and print how
    # many rows survived cleaning, so a developer can quickly sanity-check
    # the loader without running the full evaluation pipeline.
    loader = DataLoader()
    a = loader.load_dataset_a()
    b = loader.load_dataset_b()
    c = loader.load_dataset_c()
    print("Dataset A size:", len(a))
    print("Dataset B size:", len(b))
    print("Dataset C size:", len(c))
