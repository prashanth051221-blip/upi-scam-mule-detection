# Archive

Files replaced in the October 2026 rework. Nothing here is used by the current system. They are kept for the record and for the before/after comparison.

| Folder | What it holds |
|---|---|
| `original_model/` | The first Isolation Forest (PaySim-style training, 30 features) and its feature code. `train_and_evaluate.py` scores it on the new test week ("0. Original model" in RESULTS.md). `duplicate_copy_from_app/` holds the identical copy that sat inside `fraud_detection_app/models/`. |
| `old_apps_and_tests/` | The single-transaction app, the first batch dashboard, the old tests (which checked loading only, not detection), the old demo-data generator and the old READMEs. |
| `old_demo_data/` | The October demo CSVs. They had no labels, and IDs like `MULE_DEST_502` gave the answer away. |
| `old_reports/` | The progress report as submitted on 5 Oct (it contains two references that could not be found and must not be reused), the first status report and deck, the two extra presentation PDFs, and their generators. |
| `not_part_of_this_project/` | The ML Lab SVM/KNN notebook (a separate course assignment). |
