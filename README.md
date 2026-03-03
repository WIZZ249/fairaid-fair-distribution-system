# FairAid 🌍 | Fairness-Aware Humanitarian Aid Distribution

FairAid is a decision-support system designed to mitigate subjective bias in humanitarian relief efforts. Using a transparent scoring algorithm, it ensures resources reach the most vulnerable (elderly, displaced, and disabled) with full auditability.

## ⚖️ Scoring Methodology
The system calculates a **Vulnerability Score** based on weighted social parameters:
- **Demographics:** Priority for individuals aged 65+ and large households.
- **Economic Status:** Inverse weighting for monthly income.
- **Vulnerability:** High priority for disability and displacement status.

## 🚀 Key Features
- **Fairness Audit Dashboard:** Real-time monitoring of gender balance and demographic priority.
- **Explainable AI:** Every decision is accompanied by a human-readable justification.
- **Modern UI:** Clean, responsive interface for field workers.

## 🛠 Tech Stack
- **Backend:** Python, Flask
- **Data:** Pandas
- **Frontend:** HTML5, CSS3 (Custom dashboard)
