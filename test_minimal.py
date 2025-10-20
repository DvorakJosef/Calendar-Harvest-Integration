#!/usr/bin/env python3
"""
Absolute minimal Flask app to test if the issue is in our code
"""

from flask import Flask, render_template

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-key'

@app.route('/')
def index():
    return "<h1>Hello World!</h1><p>If you see this, Flask is working fine.</p>"

@app.route('/test')
def test():
    return render_template('login.html')

if __name__ == '__main__':
    print("🧪 Testing minimal Flask app on port 9001...")
    app.run(debug=True, port=9001, host='127.0.0.1')
