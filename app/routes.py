from flask import Blueprint, render_template

main = Blueprint("main", __name__)

@main.route("/")
def code_entry():
    return render_template("code_entry.html")