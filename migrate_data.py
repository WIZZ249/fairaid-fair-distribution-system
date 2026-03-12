import pandas as pd
from app import app, db, Beneficiary

def migrate():
    with app.app_context():
        try:
            df = pd.read_csv('data/sample_data.csv')
            print("CSV found. Columns identified:", df.columns.tolist())
        except FileNotFoundError:
            print("Error: data/sample_data.csv not found.")
            return

        for index, row in df.iterrows():
            try:
                # Helper to find columns even if named slightly differently
                def get_val(options, default=0):
                    for opt in options:
                        if opt in row: return row[opt]
                    return default

                new_entry = Beneficiary(
                    name=get_val(['name', 'Name', 'Full Name'], 'Unknown'),
                    age=int(get_val(['age', 'Age'], 0)),
                    # This looks for 'income' or 'Income' or defaults to 0.0
                    income=float(get_val(['income', 'Income', 'monthly_income'], 0.0)),
                    is_displaced=bool(get_val(['is_displaced', 'displaced'], False)),
                    is_disabled=bool(get_val(['is_disabled', 'disabled'], False)),
                    vulnerability_score=float(get_val(['vulnerability_score', 'score'], 0.0)),
                    last_updated_by='System Migration'
                )
                db.session.add(new_entry)
            except Exception as e:
                print(f"Skipping row {index} due to error: {e}")
        
        db.session.commit()
        print(f"Success! Migration complete.")

if __name__ == "__main__":
    migrate()