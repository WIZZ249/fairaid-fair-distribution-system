def calculate_vulnerability_score(person):
    score = 0

    if person['age'] >= 65:
        score += 20

    if person['disability'] == "Yes":
        score += 25

    if person['monthly_income'] < 20:
        score += 30
    elif person['monthly_income'] < 50:
        score += 15

    if person['household_size'] >= 5:
        score += 10

    if person['displaced'] == "Yes":
        score += 20

    return score


def explain_score(person):
    explanation = []

    if person['age'] >= 65:
        explanation.append("Elderly Priority")

    if person['disability'] == "Yes":
        explanation.append("Disability Support")

    if person['monthly_income'] < 20:
        explanation.append("Extreme Poverty")
    elif person['monthly_income'] < 50:
        explanation.append("Low Income")

    if person['household_size'] >= 5:
        explanation.append("Large Household")

    if person['displaced'] == "Yes":
        explanation.append("Displaced Status")

    return ", ".join(explanation)