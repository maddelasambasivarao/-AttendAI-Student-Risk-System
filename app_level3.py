import sqlite3, json, os, glob
from flask import Flask, request, redirect, session, Response, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
import joblib
from datetime import datetime
from face_module import add_face, recognize_face

app = Flask(__name__)
app.secret_key = "attendai_secret_key_123"

MODEL_PATH = "AttendAI_model.pkl"
model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None

def init_db():
    con = sqlite3.connect("AttendAI.db")
    con.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TEXT
    )""")
    for col in ["full_name TEXT", "roll_no TEXT", "course TEXT", "branch TEXT"]:
        try: con.execute(f"ALTER TABLE users ADD COLUMN {col}")
        except: pass
    con.execute("""CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT, full_name TEXT, roll_no TEXT, course TEXT, branch TEXT,
        prev INTEGER, assign_val INTEGER, study INTEGER,
        late INTEGER, marks INTEGER, result TEXT, confidence REAL, reason TEXT, date TEXT
    )""")
    for col in ["full_name TEXT", "roll_no TEXT", "course TEXT", "branch TEXT"]:
        try: con.execute(f"ALTER TABLE predictions ADD COLUMN {col}")
        except: pass
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username,password,created_at,full_name,roll_no,course,branch) VALUES (?,?,?,?,?,?,?)", 
                    ("admin", generate_password_hash("admin123"), datetime.now().strftime("%Y-%m-%d"), "Admin User", "22CS001", "B.Tech", "CSE"))
    con.commit(); con.close()
init_db()

def get_profile(username):
    con = sqlite3.connect("AttendAI.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone(); con.close(); return row

LOGIN_HTML = """<!DOCTYPE html><html><head><title>AttendAI - Login</title>
<style>body{font-family:Arial;background:#0f172a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
.card{background:#1e293b;padding:35px;border-radius:15px;width:340px}
input{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:none;box-sizing:border-box}
button{width:100%;padding:12px;background:#3b82f6;color:white;border:none;border-radius:8px;cursor:pointer;font-weight:bold;margin-top:10px}
a{color:#60a5fa;text-decoration:none;font-size:14px}.links{display:flex;justify-content:space-between;margin-top:15px}</style></head>
<body><div class="card"><h2>AttendAI Login</h2>
<form method="POST"><input name="username" placeholder="Username" required><input name="password" type="password" placeholder="Password" required><button type="submit">Login</button></form>
<div class="links"><a href="/register">Create New Account</a><a href="/forgot">Forgot Password?</a></div></div></body></html>"""

REGISTER_HTML = """<!DOCTYPE html><html><head><title>Create Account</title>
<style>body{font-family:Arial;background:#0f172a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
.card{background:#1e293b;padding:35px;border-radius:15px;width:340px}
input{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:none;box-sizing:border-box}
button{width:100%;padding:12px;background:#10b981;color:white;border:none;border-radius:8px;cursor:pointer;font-weight:bold;margin-top:10px}
a{color:#60a5fa;text-decoration:none;font-size:14px;display:block;text-align:center;margin-top:15px}</style></head>
<body><div class="card"><h2>Create Account</h2>
<form method="POST"><input name="username" placeholder="New Username" required><input name="password" type="password" placeholder="New Password" required><input name="confirm" type="password" placeholder="Confirm Password" required><button type="submit">Register</button></form>
<a href="/login">Already have account? Login</a>{% if msg %}<p style="color:#f87171;text-align:center">{{msg}}</p>{% endif %}</div></body></html>"""

FORGOT_HTML = """<!DOCTYPE html><html><head><title>Forgot Password</title>
<style>body{font-family:Arial;background:#0f172a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
.card{background:#1e293b;padding:35px;border-radius:15px;width:340px}
input{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:none;box-sizing:border-box}
button{width:100%;padding:12px;background:#f59e0b;color:white;border:none;border-radius:8px;cursor:pointer;font-weight:bold;margin-top:10px}
a{color:#60a5fa;text-decoration:none;font-size:14px;display:block;text-align:center;margin-top:15px}</style></head>
<body><div class="card"><h2>Forgot Password</h2>
<form method="POST"><input name="username" placeholder="Your Username" required><input name="newpass" type="password" placeholder="New Password" required><input name="confirm" type="password" placeholder="Confirm New Password" required><button type="submit">Reset Password</button></form>
<a href="/login">Back to Login</a>{% if msg %}<p style="color:{% if success %}#22c55e{% else %}#f87171{% endif %};text-align:center">{{msg}}</p>{% endif %}</div></body></html>"""

DASHBOARD_HTML = """
<!DOCTYPE html><html><head><title>AttendAI Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{font-family:Arial;background:#0f172a;color:white;margin:0;padding:20px}
.card{background:#1e293b;padding:22px;border-radius:15px;margin-bottom:22px}
.top-row{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:22px}
.stats-row{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:15px;margin-bottom:22px}
input{padding:11px;margin:5px;border-radius:7px;border:none;width:135px}
.p-input{width:90%;background:#0f172a;color:white;border:1px solid #334155;margin:6px 0}
button{padding:11px 16px;background:#3b82f6;color:white;border:none;border-radius:8px;cursor:pointer;margin:5px;font-weight:bold}
table{width:100%;border-collapse:collapse}th,td{padding:9px;border-bottom:1px solid #334155;font-size:13px}
.safe{color:#22c55e;font-weight:bold}.risk{color:#ef4444;font-weight:bold}
canvas{background:white;border-radius:12px;padding:15px}
.user-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
@media(max-width:800px){.top-row,.stats-row{grid-template-columns:1fr 1fr}}
</style></head>
<body>
<h1>Welcome to AttendAI <a href="/logout" style="float:right"><button style="background:#ef4444">Logout</button></a></h1>

<div class="stats-row">
<div class="card" style="text-align:center;border-left:4px solid #3b82f6;margin:0;padding:15px"><h2 style="margin:0;color:#3b82f6">{{total}}</h2><small>Total Predictions</small></div>
<div class="card" style="text-align:center;border-left:4px solid #22c55e;margin:0;padding:15px"><h2 style="margin:0;color:#22c55e">{{safe_count}}</h2><small>SAFE Students</small></div>
<div class="card" style="text-align:center;border-left:4px solid #ef4444;margin:0;padding:15px"><h2 style="margin:0;color:#ef4444">{{risk_count}}</h2><small>RISK Students</small></div>
<div class="card" style="text-align:center;border-left:4px solid #f59e0b;margin:0;padding:15px"><h2 style="margin:0;color:#f59e0b">{{avg_conf}}%</h2><small>Avg Confidence</small></div>
</div>

<div class="top-row">
<div class="card" style="border:2px solid #22c55e;margin-bottom:0">
<h3>👤 User Details</h3>
<form method="POST" action="/update_profile">
<div class="user-grid">
<div><b>Full Name</b><br><input class="p-input" name="full_name" value="{{profile['full_name'] or ''}}" placeholder="Your Name" required></div>
<div><b>Roll No</b><br><input class="p-input" name="roll_no" value="{{profile['roll_no'] or ''}}" placeholder="22CS001" required></div>
<div><b>Course</b><br><input class="p-input" name="course" value="{{profile['course'] or ''}}" placeholder="B.Tech" required></div>
<div><b>Branch</b><br><input class="p-input" name="branch" value="{{profile['branch'] or ''}}" placeholder="CSE" required></div>
</div>
<button type="submit" style="background:#22c55e;width:100%;margin-top:12px">💾 Save</button>
</form>
</div>

<div class="card" style="border:2px solid #f59e0b;margin-bottom:0">
<h3>📸 Face Recognition</h3>
<p style="color:#94a3b8;font-size:14px">Logged in as: {{user}} | {{ (profile['full_name'] or 'Admin').title() }}</p>
<a href="/add_face"><button style="background:#f59e0b;width:100%">📸 Add My Face</button></a>
<a href="/recognize"><button style="background:#10b981;width:100%">✅ Mark Attendance</button></a>
<a href="/face_history"><button style="background:#8b5cf6;width:100%">📜 Face History</button></a>
</div>
</div>

<div class="card">
<h3>🎯 Predict Student Risk</h3>
<form method="POST" action="/predict">
<input name="prev" type="number" placeholder="Prev %" required>
<input name="assign" type="number" placeholder="Assignments" required>
<input name="study" type="number" placeholder="Study Hrs" required>
<input name="late" type="number" placeholder="Late" required>
<input name="marks" type="number" placeholder="Marks" required>
<button>Predict</button>
</form>
{% if result %}<h2 class="{{result.lower()}}">Result: {{result}} - {{confidence}}%</h2><p>{{reason}}</p>{% endif %}
{% if dup_msg %}<h3 style="color:#fbbf24">⚠️ {{dup_msg}}</h3>{% endif %}
</div>

<div class="top-row">
<div class="card"><h3>📊 AttendAI - Prediction Confidence Analytics</h3><canvas id="myChart" height="140"></canvas></div>
<div class="card"><h3>🥧 SAFE vs RISK - Risk Intelligence</h3><canvas id="pieChart" height="140"></canvas></div>
</div>

<div class="card" style="overflow-x:auto">
<h3>📜 User History</h3>
<div style="max-height:350px; overflow-y:auto; border:1px solid #334155; border-radius:10px">
<table style="min-width:800px">
<tr style="background:#0f172a; position:sticky; top:0"><th>Date</th><th>Name (Snapshot)</th><th>Prev</th><th>Assign</th><th>Study</th><th>Late</th><th>Marks</th><th>Result</th><th>Conf</th></tr>
{% for row in history %}
<tr>
<td style="white-space:nowrap">{{row[13]}}</td>
<td><b>{{ (row[2] or profile['full_name'] or user).title() }}</b><br><small style="color:#94a3b8">{{row[3] or ''}} | {{row[5] or ''}}</small></td>
<td>{{row[6]}}</td><td>{{row[7]}}</td><td>{{row[8]}}</td><td>{{row[9]}}</td><td>{{row[10]}}</td>
<td class="{{row[11].lower()}}">{{row[11]}}</td><td>{{row[12]}}%</td>
</tr>
{% endfor %}
</table>
</div>
<br>
<a href="/download"><button>Download CSV</button></a>
<a href="/users"><button style="background:#8b5cf6">Show Users DB</button></a>
</div>

<script>
new Chart(document.getElementById('myChart'), {
  type: 'bar',
  data: { labels: {{ labels | safe }}, datasets: [{ label: 'Confidence %', data: {{ values | safe }}, backgroundColor: {{ colors | safe }}, borderWidth:1, borderRadius:8 }] },
  options: { responsive:true, scales:{ y:{ beginAtZero:true, max:100 } } }
});
new Chart(document.getElementById('pieChart'), {
  type: 'doughnut',
  data: { labels: ['SAFE','RISK'], datasets: [{ data: [{{safe_count}}, {{risk_count}}], backgroundColor: ['#22c55e','#ef4444'], borderWidth:0 }] },
  options: { responsive:true, plugins:{ legend:{ labels:{ color:'white' } } } }
});
</script>
</body></html>
"""

USERS_HTML = """<!DOCTYPE html><html><head><title>Users</title>
<style>body{font-family:Arial;background:#0f172a;color:white;padding:20px}.card{background:#1e293b;padding:20px;border-radius:12px}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #334155}</style></head>
<body><div class="card"><h2>All Users - DB Stored Details</h2><table><tr><th>ID</th><th>Username</th><th>Full Name</th><th>Roll No</th><th>Course</th><th>Branch</th><th>Created</th></tr>{% for u in users %}<tr><td>{{u[0]}}</td><td>{{u[1]}}</td><td>{{u[4]}}</td><td>{{u[5]}}</td><td>{{u[6]}}</td><td>{{u[7]}}</td><td>{{u[3]}}</td></tr>{% endfor %}</table><br><a href="/dashboard"><button style="padding:10px 15px;background:#3b82f6;color:white;border:none;border-radius:8px">Back</button></a></div></body></html>"""

@app.route("/")
def home(): return redirect("/login")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=request.form["username"]; p=request.form["password"]
        con=sqlite3.connect("AttendAI.db"); cur=con.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (u,)); user=cur.fetchone(); con.close()
        if user and check_password_hash(user[2], p):
            session["user"]=u; return redirect("/dashboard")
        return render_template_string(LOGIN_HTML + "<p style='color:#f87171;text-align:center'>Invalid Login!</p>")
    return render_template_string(LOGIN_HTML)

@app.route("/register", methods=["GET","POST"])
def register():
    msg=None
    if request.method=="POST":
        u=request.form["username"]; p=request.form["password"]; c=request.form["confirm"]
        if p!=c: msg="Passwords do not match!"
        else:
            try:
                con=sqlite3.connect("AttendAI.db"); cur=con.cursor()
                cur.execute("INSERT INTO users (username,password,created_at) VALUES (?,?,?)", (u, generate_password_hash(p), datetime.now().strftime("%Y-%m-%d")))
                con.commit(); con.close(); return redirect("/login")
            except: msg="Username already exists!"
    return render_template_string(REGISTER_HTML, msg=msg)

@app.route("/forgot", methods=["GET","POST"])
def forgot():
    msg=None; success=False
    if request.method=="POST":
        u=request.form["username"]; np=request.form["newpass"]; c=request.form["confirm"]
        if np!=c: msg="Passwords do not match!"
        else:
            con=sqlite3.connect("AttendAI.db"); cur=con.cursor()
            cur.execute("SELECT * FROM users WHERE username=?", (u,)); user=cur.fetchone()
            if not user: msg="Username not found!"
            else:
                cur.execute("UPDATE users SET password=? WHERE username=?", (generate_password_hash(np), u))
                con.commit(); msg="Password Reset Successful! Go to Login."; success=True
            con.close()
    return render_template_string(FORGOT_HTML, msg=msg, success=success)

@app.route("/dashboard")
def dashboard():
    if "user" not in session: return redirect("/login")
    profile = get_profile(session["user"])
    con=sqlite3.connect("AttendAI.db"); cur=con.cursor()
    cur.execute("SELECT * FROM predictions WHERE username=? ORDER BY id DESC LIMIT 10", (session["user"],)); rows=cur.fetchall(); con.close()
    rows_rev=list(reversed(rows))
    labels=json.dumps([f"ID-{r[0]}" for r in rows_rev]); values=json.dumps([r[12] for r in rows_rev]); colors=json.dumps(["#22c55e" if r[11]=="SAFE" else "#ef4444" for r in rows_rev])
    safe_count=sum(1 for r in rows if r[11]=='SAFE'); risk_count=sum(1 for r in rows if r[11]=='RISK')
    total=len(rows); avg_conf=round(sum(r[12] for r in rows)/len(rows),1) if rows else 0
    return render_template_string(DASHBOARD_HTML, user=session["user"], profile=profile, history=rows, labels=labels, values=values, colors=colors, safe_count=safe_count, risk_count=risk_count, total=total, avg_conf=avg_conf, result=None, dup_msg=None)

@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "user" not in session: return redirect("/login")
    con=sqlite3.connect("AttendAI.db"); cur=con.cursor()
    cur.execute("UPDATE users SET full_name=?, roll_no=?, course=?, branch=? WHERE username=?", (request.form.get("full_name"), request.form.get("roll_no"), request.form.get("course"), request.form.get("branch"), session["user"]))
    con.commit(); con.close(); return redirect("/dashboard")

@app.route("/predict", methods=["POST"])
def predict():
    if "user" not in session: return redirect("/login")
    profile = get_profile(session["user"])
    prev=int(request.form.get("prev",0))
    assign_val=int(request.form.get("assign") or 0)
    study=int(request.form.get("study",0)); late=int(request.form.get("late",0)); marks=int(request.form.get("marks",0))
    con=sqlite3.connect("AttendAI.db"); cur=con.cursor()
    cur.execute("SELECT id FROM predictions WHERE username=? AND prev=? AND assign_val=? AND study=? AND late=? AND marks=?", 
                (session["user"], prev, assign_val, study, late, marks))
    if cur.fetchone():
        cur.execute("SELECT * FROM predictions WHERE username=? ORDER BY id DESC LIMIT 10", (session["user"],)); rows=cur.fetchall(); con.close()
        rows_rev=list(reversed(rows)); labels=json.dumps([f"ID-{r[0]}" for r in rows_rev]); values=json.dumps([r[12] for r in rows_rev]); colors=json.dumps(["#22c55e" if r[11]=="SAFE" else "#ef4444" for r in rows_rev])
        safe_count=sum(1 for r in rows if r[11]=='SAFE'); risk_count=sum(1 for r in rows if r[11]=='RISK'); total=len(rows); avg_conf=round(sum(r[12] for r in rows)/len(rows),1) if rows else 0
        return render_template_string(DASHBOARD_HTML, user=session["user"], profile=profile, history=rows, labels=labels, values=values, colors=colors, safe_count=safe_count, risk_count=risk_count, total=total, avg_conf=avg_conf, result=None, dup_msg=f"Duplicate! Same data already exists!")
    risk_points=0
    if prev<75: risk_points+=2
    if prev<50: risk_points+=2
    if assign_val<4: risk_points+=1
    if study<6: risk_points+=2
    if late>8: risk_points+=2
    if late>15: risk_points+=2
    if marks<60: risk_points+=1
    if marks<40: risk_points+=2
    if risk_points>=3: result="RISK"; confidence=round(85+risk_points*2.5,1)
    else: result="SAFE"; confidence=round(90+(10-risk_points)*0.8,1)
    reason=f"Prev {prev}%, Assign {assign_val}, Study {study}h, Late {late}, Marks {marks} => {result} {confidence}%"
    cur.execute("INSERT INTO predictions (username,full_name,roll_no,course,branch,prev,assign_val,study,late,marks,result,confidence,reason,date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (session["user"], profile['full_name'], profile['roll_no'], profile['course'], profile['branch'], prev, assign_val, study, late, marks, result, confidence, reason, datetime.now().strftime("%Y-%m-%d %H:%M")))
    con.commit(); cur.execute("SELECT * FROM predictions WHERE username=? ORDER BY id DESC LIMIT 10", (session["user"],)); rows=cur.fetchall(); con.close()
    rows_rev=list(reversed(rows)); labels=json.dumps([f"ID-{r[0]}" for r in rows_rev]); values=json.dumps([r[12] for r in rows_rev]); colors=json.dumps(["#22c55e" if r[11]=="SAFE" else "#ef4444" for r in rows_rev])
    safe_count=sum(1 for r in rows if r[11]=='SAFE'); risk_count=sum(1 for r in rows if r[11]=='RISK'); total=len(rows); avg_conf=round(sum(r[12] for r in rows)/len(rows),1) if rows else 0
    return render_template_string(DASHBOARD_HTML, user=session["user"], profile=profile, history=rows, labels=labels, values=values, colors=colors, safe_count=safe_count, risk_count=risk_count, total=total, avg_conf=avg_conf, result=result, confidence=confidence, reason=reason, dup_msg=None)

@app.route("/download")
def download():
    if "user" not in session: return redirect("/login")
    con=sqlite3.connect("AttendAI.db"); cur=con.cursor(); cur.execute("SELECT * FROM predictions WHERE username=?", (session["user"],)); rows=cur.fetchall(); con.close()
    def generate():
        yield "ID,Username,FullName,Roll,Course,Branch,Prev,Assign,Study,Late,Marks,Result,Confidence,Reason,Date\n"
        for r in rows: yield ",".join([str(x).replace(","," ") for x in r])+"\n"
    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=Predictions.csv"})

@app.route("/users")
def show_users():
    if "user" not in session: return redirect("/login")
    con=sqlite3.connect("AttendAI.db"); cur=con.cursor(); cur.execute("SELECT * FROM users"); users=cur.fetchall(); con.close()
    return render_template_string(USERS_HTML, users=users)

@app.route("/add_face")
def add_face_route():
    if "user" not in session: return redirect("/login")
    try: msg = add_face(session["user"])
    except Exception as e: msg = f"Error: {e}"
    return f"<body style='background:#0f172a;color:white;font-family:Arial;padding:30px'><h2>{msg}</h2><br><a href='/dashboard'><button style='padding:10px 15px;background:#3b82f6;color:white;border:none;border-radius:8px'>Back</button></a></body>"

@app.route("/recognize")
def recognize_route():
    if "user" not in session: return redirect("/login")
    try: result = recognize_face()
    except Exception as e: result = f"Error: {e}"
    return f"<body style='background:#0f172a;color:white;font-family:Arial;padding:30px'><h2>{result}</h2><br><a href='/dashboard'><button style='padding:10px 15px;background:#3b82f6;color:white;border:none;border-radius:8px'>Back</button></a></body>"

@app.route("/face_history")
def face_history():
    if "user" not in session: return redirect("/login")
    faces = glob.glob("faces/*.jpg")+glob.glob("faces/*.png")
    html="<body style='background:#0f172a;color:white;font-family:Arial;padding:20px'><h2>Registered Faces</h2><ul>"
    for f in faces: html+=f"<li>{f}</li>"
    html+="</ul><br><a href='/dashboard'><button style='padding:10px 15px;background:#3b82f6;color:white;border:none;border-radius:8px'>Back</button></a></body>"
    return html

@app.route("/logout")
def logout(): session.clear(); return redirect("/login")

if __name__=="__main__":
    init_db()
    app.run(debug=True, port=5000)