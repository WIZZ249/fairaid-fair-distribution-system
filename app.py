from flask import Flask, render_template
import pandas as pd
from scoring import calculate_vulnerability_score, explain_score

app = Flask(__name__)

@app.route('/')
def index():
    data = pd.read_csv("data/sample_data.csv")
    data['vulnerability_score'] = data.apply(calculate_vulnerability_score, axis=1)
    data['explanation'] = data.apply(explain_score, axis=1)
    
    # Calculate Fairness Metrics
    total_aid = len(data)
    female_pct = (data[data['gender'] == 'F'].shape[0] / total_aid) * 100
    displaced_pct = (data[data['displaced'] == 'Yes'].shape[0] / total_aid) * 100
    
    stats = {
        'total': total_aid,
        'female_representation': f"{female_pct:.1f}%",
        'displaced_priority': f"{displaced_pct:.1f}%"
    }

    sorted_data = data.sort_values(by='vulnerability_score', ascending=False)
    return render_template("index.html", tables=sorted_data.to_dict(orient='records'), stats=stats)

if __name__ == "__main__":
    app.run(debug=True)