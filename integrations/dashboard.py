import os
from flask import Flask, render_template_string
import csv

app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Expenses Dashboard</title>
    <style>
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even){ background-color: #f9f9f9; }
    </style>
</head>
<body>
    <h1>Expenses Dashboard</h1>
    <table>
        <tr><th>Date</th><th>Amount</th><th>Category</th></tr>
        {% for exp in expenses %}
        <tr>
            <td>{{ exp.Date }}</td>
            <td>{{ exp.Amount }}</td>
            <td>{{ exp.Category }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

@app.route('/')
def dashboard():
    expenses = []
    csv_file = os.path.join(os.path.dirname(__file__), 'expenses.csv')
    if os.path.isfile(csv_file):
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                expenses.append(row)
    return render_template_string(TEMPLATE, expenses=expenses)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
