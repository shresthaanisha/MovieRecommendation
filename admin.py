from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'many random bytes'

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'mydatabase'

mysql = MySQL(app)

# Admin Dashboard - Displays the movies list
@app.route('/admin')
def admin():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM movies")  # Fetch all movies
    data = cur.fetchall()
    cur.close()
    return render_template('admin.html', movies=data)

# Insert a new movie
@app.route('/add_movie', methods=['GET', 'POST'])
def add_movie():
    if request.method == 'POST':
        title = request.form['title']
        overview = request.form['overview']
        vote_count = request.form['vote_count']
        vote_average = request.form['vote_average']

        # Insert data into the database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO movies (title, overview, vote_count, vote_average) VALUES (%s, %s, %s, %s)",
                    (title, overview, vote_count, vote_average))
        mysql.connection.commit()
        flash('Movie added successfully!')
        return redirect(url_for('admin'))  # Redirect to the admin page after adding

    return render_template('add_movies.html')  # Show the add movie form

# Delete a movie
@app.route('/delete/<string:id_data>', methods=['GET'])
def delete(id_data):
    flash("Record has been deleted successfully!")
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM movies WHERE id=%s", (id_data,))
    mysql.connection.commit()
    return redirect(url_for('admin'))  # Redirect to the admin page after deleting

# Edit a movie
@app.route('/update/<string:id_data>', methods=['GET', 'POST'])
def update(id_data):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM movies WHERE id=%s", (id_data,))
    movie = cur.fetchone()

    if request.method == 'POST':
        title = request.form['title']
        overview = request.form['overview']
        vote_count = request.form['vote_count']
        vote_average = request.form['vote_average']

        cur.execute("""
            UPDATE movies
            SET title=%s, overview=%s, vote_count=%s, vote_average=%s
            WHERE id=%s
        """, (title, overview, vote_count, vote_average, id_data))
        mysql.connection.commit()
        flash('Movie updated successfully!')
        return redirect(url_for('admin'))

    return render_template('update_movie.html', movie=movie)  # Show the edit movie form

if __name__ == "__main__":
    app.run(debug=True)
