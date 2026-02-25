from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load chatbot database
with open("database.json", "r") as file:
    database = json.load(file)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get_response", methods=["POST"])
def get_response():
    user_input = request.json["message"]
    response = "I don't understand that yet."
    
    # Convert user input to lowercase keywords
    user_keywords = set(user_input.lower().split())
    
    for entry in database:
        # Convert entry input to lowercase keywords
        entry_keywords = set(entry["input"].lower().split())
        
        # Check if any keyword from the entry matches the user input
        if entry_keywords & user_keywords:
            response = entry["response"]
            break
    
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(debug=True)