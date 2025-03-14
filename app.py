from flask import Flask, render_template, session, redirect, url_for
from flask_cors import CORS
from models.user import db
from routes.api import api_bp
import os

app = Flask(__name__)
app.config.from_pyfile('config.py')
CORS(app)
db.init_app(app)

# Register blueprints
app.register_blueprint(api_bp)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/applications')
def applications():
    return render_template('applications.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=app.config['DEBUG'])
