from flask import Flask, render_template, session, json, request
from flask_session import Session
from datetime import timedelta

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(days=14)
Session(app)
