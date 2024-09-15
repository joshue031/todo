import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime
import sqlite3
import uuid
import markdown

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data'

# Ensure that the upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS categories
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  category_id INTEGER,
                  date_time TEXT NOT NULL,
                  description TEXT NOT NULL,
                  completed INTEGER DEFAULT 0,
                  markdown_content TEXT,
                  FOREIGN KEY (category_id) REFERENCES categories(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS attachments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  task_id INTEGER,
                  file_name TEXT NOT NULL,
                  file_path TEXT NOT NULL,
                  FOREIGN KEY (task_id) REFERENCES tasks(id))''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

# Category rules
@app.route('/add_category', methods=['POST'])
def add_category():
    name = request.form['name']
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    category_id = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"id": category_id, "name": name})

@app.route('/update_category/<int:category_id>', methods=['POST'])
def update_category(category_id):
    name = request.form['name']
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/get_categories')
def get_categories():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM categories")
    categories = [{"id": row[0], "name": row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(categories)

@app.route('/delete_category/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    # Delete the tasks associated with this category
    c.execute("DELETE FROM tasks WHERE category_id = ?", (category_id,))
    # Delete the category
    c.execute("DELETE FROM categories WHERE id = ?", (category_id,))

    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route('/move_category/<int:category_id>/up', methods=['POST'])
def move_category_up(category_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    # Get the current category's ID
    c.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
    current_category = c.fetchone()

    if current_category:
        current_id = current_category[0]
        # Move the current category up by swapping with the previous one
        c.execute("SELECT id FROM categories WHERE id < ? ORDER BY id DESC LIMIT 1", (current_id,))
        previous_category = c.fetchone()

        if previous_category:
            previous_id = previous_category[0]

            # Use a temporary value for swapping
            temp_id = -1  # Assuming all real IDs are positive integers

            # Update tasks with the previous category to use a temporary ID
            c.execute("UPDATE tasks SET category_id = ? WHERE category_id = ?", (temp_id, previous_id))
            # Swap the category IDs
            c.execute("UPDATE categories SET id = ? WHERE id = ?", (temp_id, previous_id))
            c.execute("UPDATE categories SET id = ? WHERE id = ?", (previous_id, current_id))
            c.execute("UPDATE categories SET id = ? WHERE id = ?", (current_id, temp_id))
            # Update tasks with the new category ID
            c.execute("UPDATE tasks SET category_id = ? WHERE category_id = ?", (previous_id, current_id))
            c.execute("UPDATE tasks SET category_id = ? WHERE category_id = ?", (current_id, temp_id))

    conn.commit()
    conn.close()

    return jsonify({"success": True})


@app.route('/move_category/<int:category_id>/down', methods=['POST'])
def move_category_down(category_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    # Get the current category's ID
    c.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
    current_category = c.fetchone()

    if current_category:
        current_id = current_category[0]
        # Move the current category down by swapping with the next one
        c.execute("SELECT id FROM categories WHERE id > ? ORDER BY id ASC LIMIT 1", (current_id,))
        next_category = c.fetchone()

        if next_category:
            next_id = next_category[0]

            # Use a temporary value for swapping
            temp_id = -1  # Assuming all real IDs are positive integers

            # Update tasks with the next category to use a temporary ID
            c.execute("UPDATE tasks SET category_id = ? WHERE category_id = ?", (temp_id, next_id))
            # Swap the category IDs
            c.execute("UPDATE categories SET id = ? WHERE id = ?", (temp_id, next_id))
            c.execute("UPDATE categories SET id = ? WHERE id = ?", (next_id, current_id))
            c.execute("UPDATE categories SET id = ? WHERE id = ?", (current_id, temp_id))
            # Update tasks with the new category ID
            c.execute("UPDATE tasks SET category_id = ? WHERE category_id = ?", (next_id, current_id))
            c.execute("UPDATE tasks SET category_id = ? WHERE category_id = ?", (current_id, temp_id))

    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route('/add_task', methods=['POST'])
def add_task():
    category_id = request.form['category_id']
    date_time = request.form['date_time']
    description = request.form['description']
    
    markdown_content = f"# {description}\n"  # Automatically insert the title as a markdown header
    
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("INSERT INTO tasks (category_id, date_time, description, markdown_content) VALUES (?, ?, ?, ?)",
              (category_id, date_time, description, markdown_content))
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({"id": task_id, "category_id": category_id, "date_time": date_time, "description": description, "completed": 0})


@app.route('/update_task/<int:task_id>', methods=['POST'])
def update_task(task_id):
    description = request.form.get('description')
    date_time = request.form.get('date_time')  # Expecting ISO 8601 format

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET description = ?, date_time = ? WHERE id = ?", (description, date_time, task_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route('/edit_task/<int:task_id>')
def edit_task(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Fetch the task description (title) from the database
    c.execute("SELECT description FROM tasks WHERE id = ?", (task_id,))
    task = c.fetchone()
    
    task_title = task[0] if task else "Edit Task"  # Default to "Edit Task" if no task is found
    
    conn.close()
    
    return render_template('edit_task.html', task_id=task_id, task_title=task_title)

@app.route('/get_tasks/<int:category_id>')
def get_tasks(category_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    # Order by completed first, then date_time
    c.execute("""
        SELECT id, category_id, date_time, description, completed 
        FROM tasks 
        WHERE category_id = ? 
        ORDER BY completed ASC, date_time DESC
    """, (category_id,))
    tasks = [{"id": row[0], "category_id": row[1], "date_time": row[2], "description": row[3], "completed": row[4]} for row in c.fetchall()]
    conn.close()
    return jsonify(tasks)

@app.route('/complete_task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    # Toggle the completed status
    c.execute("UPDATE tasks SET completed = 1 - completed WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    c.execute("DELETE FROM attachments WHERE task_id = ?", (task_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/get_task_content/<int:task_id>')
def get_task_content(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("SELECT markdown_content FROM tasks WHERE id = ?", (task_id,))
    content = c.fetchone()
    conn.close()
    return jsonify({"content": content[0] if content else ""})

@app.route('/save_task_content/<int:task_id>', methods=['POST'])
def save_task_content(task_id):
    content = request.form.get('content', '')
    
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET markdown_content = ? WHERE id = ?", (content, task_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route('/upload_file/<int:task_id>', methods=['POST'])
def upload_file(task_id):
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = str(uuid.uuid4()) + '_' + file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        c.execute("INSERT INTO attachments (task_id, file_name, file_path) VALUES (?, ?, ?)",
                  (task_id, file.filename, file_path))
        attachment_id = c.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"id": attachment_id, "file_name": file.filename, "file_path": file_path})

@app.route('/get_attachments/<int:task_id>')
def get_attachments(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("SELECT id, file_name, file_path FROM attachments WHERE task_id = ?", (task_id,))
    attachments = [{"id": row[0], "file_name": row[1], "file_path": row[2]} for row in c.fetchall()]
    conn.close()
    return jsonify(attachments)

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        # Create a subdirectory based on the current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        date_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_date)

        if not os.path.exists(date_folder):
            os.makedirs(date_folder)

        # Save the file with a unique identifier
        filename = str(uuid.uuid4()) + '_' + file.filename
        file_path = os.path.join(date_folder, filename)
        file.save(file_path)

        # Return the file path for inserting into markdown
        file_url = f'/uploads/{current_date}/{filename}'
        return jsonify({"file_url": file_url})

@app.route('/uploads/<path:filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    init_db()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
