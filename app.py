# import os

from flask import Flask, render_template, request, session, redirect
from flask_socketio import SocketIO,emit, join_room, leave_room
from cs50 import SQL
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required,usd


app = Flask(__name__)


# Custom filter
app.jinja_env.filters["usd"] = usd


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = 'secret123!'
Session(app)


socketio = SocketIO(app)
db = SQL("sqlite:///chat.db")
 

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response
 
 
@app.route('/')
@login_required
def index():
    rows = db.execute(
        "SELECT rname,username,status FROM info WHERE user_id = ? ", session["user_id"]
    )
    
    detail = db.execute(
        "SELECT name FROM users WHERE id = ? ", session["user_id"]
    )
    
    name = detail[0]['name']
    
    return render_template("index.html", name=name, rows=rows)



@app.route('/group')
@login_required
def group():
    rows = db.execute(
        "SELECT rname,username,status FROM info"
    )
    return render_template("groups.html", rows=rows)




@app.route('/chat')
@login_required
def chat():
    return render_template("chat.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)

        elif not request.form.get("password"):
            return apology("must provide password", 403)

        rows = db.execute(
            "SELECT * FROM users WHERE name = ?", request.form.get("username")
            )
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        return redirect("/")

    else:
        return render_template("login.html")
    
    
@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/login")



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        elif not request.form.get("confirmation"):
            return apology("must provide confirmation", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("must provide same confirmation and Password", 400)

        rows = db.execute(
            "SELECT * FROM users WHERE name = ?", request.form.get("username")
        )

        if len(rows) >= 1:
            return apology("username alreadt exits,try another one", 400)

        db.execute(
            "INSERT INTO users (name, password) VALUES (?, ?)",
            request.form.get("username"),
            generate_password_hash(request.form.get("password")),
        )

        return redirect("/login")
    else:
        return render_template("register.html")


@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    key = data['key']
    
    if room == "" or room == None or username == "" or username == None or key == None or key == "":
        emit('message',{'type': 'alert', 'msg': 'Enter a valid Room or/and Username or/and Key!'}, room=request.sid)
    
    else:
        rows = db.execute("SELECT * FROM info WHERE rname = ?", room)
        if len(rows) >= 1 :
            if int(key) == int(rows[0]['rid']):
                emit('message',{'type': 'alert', 'msg': 'Joined the Room Successfully!'}, room=request.sid)
                join_room(room)
                emit('status', {'msg': f'{username} has entered the room.'}, room=room)
                
                name = db.execute("SELECT username FROM info WHERE rname = ? AND username = ? AND user_id=?",
                          room, username,session["user_id"])
                if len(name)>=1:
                    db.execute("UPDATE info SET status = 'active' WHERE rname = ? AND username = ? AND user_id=?",
                              room, username,session["user_id"] )
                    print("hello")
                else:
                    db.execute("INSERT INTO info (rid, rname, username, status, user_id) VALUES (?, ?, ?, ?, ?)",
                       key,
                       room,
                       username,
                       'active',
                       session["user_id"])
                    
            else:
                emit('message',{'type': 'alert', 'msg': 'Wrong Key Please try again!!'}, room=request.sid)
        
        else:
            db.execute("INSERT INTO info (rid, rname, username, status, user_id) VALUES (?, ?, ?, ?, ?)",
                       key,
                       room,
                       username,
                       'active',
                       session["user_id"])
            emit('message',{'type': 'alert', 'msg': 'Created New Room Successfully!'}, room=request.sid)
            join_room(room)
            emit('status', {'msg': f'{username} has entered the room.'}, room=room)
        



@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    
    if room == "" or room == None or username == "" or username == None:
        emit('message',{'type': 'alert', 'msg': 'Enter a valid Room or/and Username'}, room=request.sid)
        
    else:
        rows = db.execute("SELECT status FROM info WHERE rname = ? AND username = ? AND user_id=?",
                          room, username,session["user_id"] 
                          )
        if len(rows) >= 1:
            if rows[0]['status'] == 'inactive':
                emit('message',{'type': 'alert', 'msg': 'Already left the group'}, room=request.sid)
            else:
                db.execute("UPDATE info SET status = 'inactive' WHERE rname = ? AND username = ? AND user_id=?",
                              room, username,session["user_id"] 
                              )
                leave_room(room)
                emit('status', {'msg': f'{username} has left the room.'}, room=room)
                emit('message',{'type': 'alert', 'msg': 'left the room '}, room=request.sid)
        else:
            emit('message',{'type': 'alert', 'msg': 'Enter a valid username or/and Room or/and unauthenticated!'}, room=request.sid)



@socketio.on('message')
def handle_message(data):
    room = data['room']
    message = data['message']
    if room == "" or room == None:
        emit('message',{'type': 'alert', 'msg': 'Must Join a Room!'}, room=request.sid)
    else:
      emit('message', {'msg': message}, room=room, include_self=False)


    
if __name__ == '__main__':
    socketio.run(app, host="127.0.0.1", port="5001")


