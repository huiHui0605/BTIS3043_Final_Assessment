# BTIS3043 – Artificial Intelligence Final Assessment
### Predicate + Fuzzy Reasoning eBook Recommendation System (2026B)

A small intelligent system that queries three academic eBook datasets using **predicate (crisp/boolean) reasoning** to find records satisfying defined conditions, then applies **fuzzy reasoning** to score and rank how well those records suit two fixed scenarios:

- **Scenario 1** – Artificial Intelligence, Programming & Mathematical Foundations
- **Scenario 2** – Cybersecurity & Secure Computing

---

## 1. Project Structure

```
BTIS3043_Final_Assessment/
├── Dataset/
│   ├── BTIS3043_Dataset_A_Existing_eBook_Collection.xlsx      # Dataset A
│   ├── BTIS3043_Dataset_B_Academic_eBook_Catalogue.xlsx       # Dataset B
│   └── BTIS3043_Dataset_C_eBook_Acquisition_Catalogue.xlsx    # Dataset C
├── data_loader.py          # Loads and cleans all three datasets
├── predicate_engine.py     # Crisp predicate (boolean) query logic
├── fuzzy_engine.py         # Fuzzy membership functions and scoring
├── scenarios.py            # Runs predicate + fuzzy evaluation per scenario/dataset
├── report_generator.py     # Builds the formatted Excel results workbook
├── main.py                 # Entry point – runs both scenarios end-to-end
├── test_suite.py           # Unit tests for loader, predicate and fuzzy engines
├── output/
│   └── scenario_results.xlsx   # Generated results (created by main.py)
└── README.md
```

## 2. Requirements

- Python 3.10+
- Packages:
  ```bash
  pip install pandas numpy openpyxl
  ```

## 3. How to Run

From the project root folder:

```bash
python main.py
```

This will:
1. Load and clean Dataset A, B and C via `data_loader.py`.
2. Run **Scenario 1** and **Scenario 2** through the predicate engine (`predicate_engine.py`) to get predicate-only matches for every dataset.
3. Run the fuzzy engine (`fuzzy_engine.py`) over the predicate-passed records to compute topic relevance, recency, format suitability, affordability (Dataset C) and collection support (Dataset A) scores, then rank records by a weighted fuzzy score.
4. Print a summary of dataset sizes and predicate match counts to the console.
5. Generate `output/scenario_results.xlsx`, containing predicate-only results, fuzzy-enhanced/ranked results, and a summary analysis sheet for both scenarios across all three datasets.

To run the unit tests:

```bash
python -m unittest test_suite.py
```

## 4. Datasets

| Dataset | Description | Key fields used |
|---|---|---|
| **A** – Existing eBook Collection | Current subscriptions/collection (no discipline or price fields) | Title, Recommended by, Copyright Year, Quantity |
| **B** – Academic eBook Catalogue | Largest dataset, 4-level discipline hierarchy | Title, Discipline (Level 1–4), Copyright, eBook Format |
| **C** – eBook Acquisition / Licensing Catalogue | Only dataset with both format and price | Title, Discipline, Category, Copyright Year, eBook Format, April List Price (USD) |

Each dataset is processed independently — they are **not merged**, per the assignment's minimum requirements.

## 5. Method Summary

### Predicate reasoning (`predicate_engine.py`)
- Crisp, rule-based keyword matching (regex, word-boundary aware) against Title/Discipline/Category fields.
- Scenario-specific keyword sets (AI / Programming / Mathematics for Scenario 1; Direct / Generic / Related security terms for Scenario 2), plus exclusion lists to filter out false positives (e.g. "food security", "Adobe Illustrator").
- Combined boolean predicate: `topic_pass AND year_pass AND format_pass` → produces the **predicate-only result set**.

### Fuzzy reasoning (`fuzzy_engine.py`)
- **Recency**: triangular/ramp membership functions for *Modern / Recent / Old* (based on Copyright Year, 2018–2024 range).
- **Affordability** (Dataset C only): triangular/ramp membership functions for *Cheap / Moderate / Expensive* (USD 100–300 range).
- **Topic relevance**: graded relevance score depending on match strength (direct discipline match > keyword match).
- **Format suitability** and **Collection support** (Dataset A): additional weighted factors.
- **Aggregation**: weighted sum per dataset (weights differ since available attributes differ — e.g. Dataset C includes affordability, Dataset A includes collection support instead) → produces the **fuzzy-enhanced, ranked result set**.

### Output
`report_generator.py` builds a multi-sheet Excel workbook (`output/scenario_results.xlsx`) with predicate-only results, fuzzy-enhanced/ranked results, and a summary analysis sheet, for both scenarios across all three datasets.

## 6. Notes

- Datasets are queried independently and not standardised into a common schema, per the assignment's minimum requirements.
- All three datasets are included in the output even where a scenario returns few or no matching records (e.g. Scenario 2 typically returns fewer matches, since cybersecurity content is a narrow slice of a general academic collection).
- See the accompanying technical report (PDF) for full predicate/fuzzy design justification, scenario outputs, and comparison/analysis.
