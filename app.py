from flask import Flask, render_template
import pandas as pd
from scoring import calculate_vulnerability_score, explain_score

app = Flask(__name__)

@app.route('/')
def index():
    data = pd.read_csv("data/sample_data.csv")

    data['vulnerability_score'] = data.apply(calculate_vulnerability_score, axis=1)
    data['explanation'] = data.apply(explain_score, axis=1)

    sorted_data = data.sort_values(by='vulnerability_score', ascending=False)

    return render_template("index.html", tables=sorted_data.to_dict(orient='records'))

if __name__ == "__main__":
    app.run(debug=True)