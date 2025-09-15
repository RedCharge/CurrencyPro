from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import requests
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # needed for flash messages

# ---------------- API KEYS ----------------
EXCHANGE_API_KEY = "6a98bb7a5f8b3ab44cdee0a3"
CURRENCYFREAKS_API_KEY = "e89b09bac220405699db174c623ad232"
NEWS_API_KEY = "a4fb820d819142e389b430bddbc3cd89"

# ---------------- BASE URLS ----------------
EXCHANGE_API_URL = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/latest/USD"
CURRENCYFREAKS_URL = "https://api.currencyfreaks.com/v2.0/rates/timeseries"
NEWS_URL = "https://newsapi.org/v2/top-headlines?category=business&language=en"

# ---------------- 8 Top Rates ----------------
TOP_CURRENCIES = ["USD","EUR","GBP","JPY","CNY","GHS","NGN","AUD"]

# ---------------- 50+ CURRENCIES ----------------
CURRENCIES = {
    "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound", "JPY": "Japanese Yen",
    "CNY": "Chinese Yuan", "AUD": "Australian Dollar", "CAD": "Canadian Dollar",
    "CHF": "Swiss Franc", "INR": "Indian Rupee", "GHS": "Ghanaian Cedi",
    "NGN": "Nigerian Naira", "ZAR": "South African Rand", "EGP": "Egyptian Pound",
    "KES": "Kenyan Shilling", "UGX": "Ugandan Shilling", "TZS": "Tanzanian Shilling",
    "RUB": "Russian Ruble", "BRL": "Brazilian Real", "MXN": "Mexican Peso",
    "SAR": "Saudi Riyal", "AED": "UAE Dirham", "SGD": "Singapore Dollar",
    "MYR": "Malaysian Ringgit", "THB": "Thai Baht", "KRW": "South Korean Won",
    "IDR": "Indonesian Rupiah", "PHP": "Philippine Peso", "VND": "Vietnamese Dong",
    "ARS": "Argentine Peso", "CLP": "Chilean Peso", "COP": "Colombian Peso",
    "PEN": "Peruvian Sol", "PLN": "Polish Zloty", "CZK": "Czech Koruna",
    "HUF": "Hungarian Forint", "DKK": "Danish Krone", "NOK": "Norwegian Krone",
    "SEK": "Swedish Krona", "TRY": "Turkish Lira", "ILS": "Israeli Shekel",
    "QAR": "Qatari Riyal", "OMR": "Omani Rial", "KWD": "Kuwaiti Dinar",
    "BHD": "Bahraini Dinar", "JOD": "Jordanian Dinar", "LBP": "Lebanese Pound",
    "MAD": "Moroccan Dirham", "DZD": "Algerian Dinar", "TND": "Tunisian Dinar",
    "RSD": "Serbian Dinar", "HRK": "Croatian Kuna"
}

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- QUICK CONVERTER ----------------
@app.route("/convert", methods=["GET", "POST"])
def convert():
    result = None
    amount = 1
    from_currency = "USD"
    to_currency = "EUR"
    if request.method == "POST":
        amount = float(request.form["amount"])
        from_currency = request.form["from_currency"]
        to_currency = request.form["to_currency"]
        url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/pair/{from_currency}/{to_currency}/{amount}"
        response = requests.get(url).json()
        result = response.get("conversion_result", None)
    return render_template(
        "converter.html",
        result=result,
        amount=amount,
        from_currency=from_currency,
        to_currency=to_currency,
        currencies=CURRENCIES
    )

@app.route("/api/convert", methods=["POST"])
def api_convert():
    data = request.get_json()
    amount = float(data["amount"])
    from_currency = data["from_currency"]
    to_currency = data["to_currency"]
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/pair/{from_currency}/{to_currency}/{amount}"
    response = requests.get(url).json()
    return jsonify({"result": response.get("conversion_result", None)})

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    # --- Live Rates ---
    try:
        live_data = requests.get(EXCHANGE_API_URL).json()
        conversion_rates = live_data.get("conversion_rates", {})
        rates = {code: conversion_rates.get(code, 0) for code in TOP_CURRENCIES}
    except:
        rates = {code: 0 for code in TOP_CURRENCIES}

    # --- 7-Day USD → EUR History ---
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=6)
    history_labels = []
    history_values = []

    try:
        history_url = (
            f"{CURRENCYFREAKS_URL}?apikey={CURRENCYFREAKS_API_KEY}"
            f"&base=USD&symbols=EUR"
            f"&start_date={start_date.strftime('%Y-%m-%d')}"
            f"&end_date={end_date.strftime('%Y-%m-%d')}"
        )
        history_data = requests.get(history_url).json()
        history_rates = history_data.get("rates", {})
        last_known = None
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            history_labels.append(date_str)
            if date_str in history_rates and "EUR" in history_rates[date_str]:
                value = float(history_rates[date_str]["EUR"])
                history_values.append(value)
                last_known = value
            else:
                history_values.append(last_known if last_known else 0)
            current_date += timedelta(days=1)
    except:
        history_labels = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        history_values = [0]*7

    return render_template(
        "dashboard.html",
        rates=rates,
        labels=history_labels,
        values=history_values,
        currencies=CURRENCIES
    )

@app.route("/api/live-rates")
def api_live_rates():
    try:
        live_data = requests.get(EXCHANGE_API_URL).json()
        conversion_rates = live_data.get("conversion_rates", {})
        rates = {code: conversion_rates.get(code, 0) for code in TOP_CURRENCIES}
    except:
        rates = {code: 0 for code in TOP_CURRENCIES}
    return jsonify(rates)

@app.route("/api/finance-news")
def api_finance_news():
    try:
        res = requests.get(f"{NEWS_URL}&apiKey={NEWS_API_KEY}")
        data = res.json()
        articles = [ {
            "title": article["title"],
            "url": article["url"],
            "source": article["source"]["name"]
        } for article in data.get("articles", [])[:10] ]
    except Exception as e:
        print("Error fetching news:", e)
        articles = []
    return jsonify(articles)

# ---------------- ABOUT & SETTINGS ----------------
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/settings")
def settings():
    return render_template("settings.html")



# ---------------- MAIL CONFIG ----------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'redcharger000@gmail.com'   # your Gmail
app.config['MAIL_PASSWORD'] = 'mwgz jbnd hute ktqz'  # use App Password!
mail = Mail(app)


@app.route("/send_message", methods=["POST"])
def send_message():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    if not name or not email or not message:
        return "Missing fields", 400

    try:
        msg = Message(
            subject=f"New Contact Message from {name}",
            sender=email,
            recipients=["redcharger000@gmail.com"],  # your Gmail
            body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        )
        mail.send(msg)
        return "Message sent", 200
    except Exception as e:
        print("Error sending email:", e)
        return "Failed to send message", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
