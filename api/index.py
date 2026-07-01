from flask import Flask, jsonify, request
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "ok": True,
        "message": "OTP Manager API",
        "endpoints": ["/otp", "/balance", "/number"]
    })

@app.route('/otp', methods=['GET'])
def get_otp():
    number = request.args.get('number')
    limit = int(request.args.get('limit', 30))
    page = int(request.args.get('page', 1))
    
    return jsonify({
        "ok": True,
        "data": [],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": 0,
            "total_pages": 0
        }
    })

@app.route('/balance', methods=['GET'])
def get_balance():
    return jsonify({
        "ok": True,
        "data": {
            "available_balance": 0,
            "currency": "USD",
            "pending_balance": 0,
            "last_updated": "2026-07-01T10:00:00Z"
        },
        "pagination": {
            "page": 1,
            "limit": 100,
            "total": 1,
            "total_pages": 1
        }
    })

@app.route('/number', methods=['GET'])
def get_number():
    return jsonify({
        "ok": True,
        "data": [],
        "pagination": {
            "page": 1,
            "limit": 100,
            "total": 0,
            "total_pages": 0
        }
    })

# Vercel requires this
app = app
