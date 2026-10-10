from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'my_default_secret_key')

def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'registration'),
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('todos'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password').encode('utf-8')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and bcrypt.checkpw(password, user['password_hash'].encode('utf-8')):
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            return redirect(url_for('todos'))
        else:
            error = 'Invalid email or password.'
            
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password').encode('utf-8')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
      
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            error = 'Email Already Exists.'
        else:
            hashed_password = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
            cursor.execute("INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)", 
                           (name, email, hashed_password))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('login'))
            
        cursor.close()
        conn.close()
        
    return render_template('register.html', error=error)



@app.route('/todos', methods=['GET', 'POST'])
def todos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'all')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM todos WHERE user_id = %s"
    params = [user_id]
    
    if search_query:
        query += " AND title LIKE %s"
        params.append(f"%{search_query}%")
        
    if status_filter == 'open':
        query += " AND is_done = 0"
    elif status_filter == 'done':
        query += " AND is_done = 1"
        
    query += " ORDER BY created_at DESC"
    
    cursor.execute(query, tuple(params))
    todos_list = cursor.fetchall()
    
  
    cursor.execute("SELECT COUNT(*) as open_count FROM todos WHERE user_id = %s AND is_done = 0", (user_id,))
    open_count_result = cursor.fetchone()
    open_count = open_count_result['open_count'] if open_count_result else 0
    
    cursor.close()
    conn.close()
    
    return render_template('todos.html', todos=todos_list, open_count=open_count, search_query=search_query, status_filter=status_filter, user_name=session.get('user_name', 'User'))

@app.route('/add-todo', methods=['POST'])
def add_todo():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    title = request.form.get('title')
    due_date = request.form.get('due_date') or None
    
    if title:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO todos (user_id, title, due_date) VALUES (%s, %s, %s)", 
                       (session['user_id'], title, due_date))
        conn.commit()
        cursor.close()
        conn.close()
        
    return redirect(url_for('todos'))

@app.route('/toggle-todo/<int:todo_id>')
def toggle_todo(todo_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE todos SET is_done = NOT is_done WHERE todo_id = %s AND user_id = %s", (todo_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('todos'))

@app.route('/delete-todo/<int:todo_id>')
def delete_todo(todo_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE todo_id = %s AND user_id = %s", (todo_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('todos'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)