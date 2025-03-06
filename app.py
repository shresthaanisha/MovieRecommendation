import pandas as pd
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask_mysqldb import MySQL
import bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField
from wtforms.validators import DataRequired, Email, ValidationError
from wtforms.validators import DataRequired, Email, Length, ValidationError
import pickle

# Flask application setup
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Secret key for session management

# Database configuration for MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # Adjust if needed
app.config['MYSQL_DB'] = 'mydatabase'  # Replace with your actual database name

# Initialize MySQL connection
mysql = MySQL(app)

# Load the Netflix dataset
netflix_overall = pd.read_csv('netflix_titles.csv').fillna('')  # Make sure your dataset path is correct
popular_df = pickle.load(open('popular_movie_df.pkl', 'rb'))  # Preprocessed pickle file for popular movies

# Data preprocessing functions
def clean_data(x):
    """Clean the input by making it lowercase and removing spaces."""
    return str.lower(x.replace(" ", ""))

def create_soup(x):
    """Create a 'soup' column by combining various attributes of the movie."""
    return f"{x['title']} {x['director']} {x['cast']} {x['listed_in']} {x['description']}"

def preprocess_netflix_data():
    """Apply cleaning functions and calculate cosine similarity matrix."""
    global netflix_overall, count_matrix, cosine_sim2, indices

    # Apply cleaning and create a 'soup' column
    netflix_overall['title'] = netflix_overall['title'].apply(clean_data)
    netflix_overall['director'] = netflix_overall['director'].apply(clean_data)
    netflix_overall['cast'] = netflix_overall['cast'].apply(clean_data)
    netflix_overall['listed_in'] = netflix_overall['listed_in'].apply(clean_data)
    netflix_overall['description'] = netflix_overall['description'].apply(clean_data)
    netflix_overall['soup'] = netflix_overall.apply(create_soup, axis=1)

    # Initialize CountVectorizer and compute the cosine similarity matrix
    count = CountVectorizer(stop_words='english')
    count_matrix = count.fit_transform(netflix_overall['soup'])
    cosine_sim2 = cosine_similarity(count_matrix, count_matrix)

    # Create a mapping of movie titles to their corresponding index
    indices = pd.Series(netflix_overall.index, index=netflix_overall['title'])

# Preprocess data at startup
preprocess_netflix_data()

# Recommendation function to get similar movies based on the title
def get_recommendations(title, cosine_sim):
    """Returns top 10 movie recommendations based on cosine similarity."""
    title = clean_data(title)  # Clean the input title
    if title not in indices:
        return None  # Return None if the movie is not in the dataset

    idx = indices[title]
    sim_scores = list(enumerate(cosine_sim[idx]))  # Get similarity scores
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)  # Sort by similarity
    sim_scores = sim_scores[1:11]  # Top 10 similar movies (excluding the input movie itself)

    movie_indices = [i[0] for i in sim_scores]
    return netflix_overall['title'].iloc[movie_indices].reset_index(drop=True)

# Routes
@app.route('/')
def front():
    """Render the front page with popular movies."""
    top_movies = popular_df.sort_values(by='avg_vote', ascending=False).head(8).to_dict('records')
    return render_template('front.html', movies=top_movies)

@app.route('/index')
def index():
    """Render the index page."""
    return render_template('index.html')

# Registration form
class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data

        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Store user data into the database
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password.decode('utf-8')))
        mysql.connection.commit()
        cursor.close()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html', form=form)



@app.route('/about', methods=['POST'])
def getvalue():
    """Get movie recommendations when a movie is submitted by the user."""
    moviename = request.form['moviename']
    recommendations = get_recommendations(moviename, cosine_sim2)
    if recommendations is None:
        flash("Movie not found in the dataset. Please try another.", "danger")
        return redirect('/')
    
    return render_template('result.html', tables=[recommendations.to_frame().to_html(classes='data')])



@app.route('/dashboard')
def dashboard():
    """Render the dashboard page for logged-in users."""
    if 'user_id' in session:
        user_id = session['user_id']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        return render_template('dashboard.html', user=user)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login for both users and admins."""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cursor = mysql.connection.cursor()

        # Check in users table
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user:
            try:
                # Verify the password with bcrypt
                if bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):  # Assuming password is the 4th column
                    session['user_id'] = user[0]  # Store user ID in session
                    return redirect(url_for('dashboard'))
            except ValueError:
                flash("Password hash invalid. Please reset your password.", "danger")
                return redirect(url_for('login'))
        
        # Check in admin table
        cursor.execute("SELECT * FROM admin WHERE email=%s", (email,))
        admin = cursor.fetchone()

        if admin:
            try:
                # Verify the password for admin
                if bcrypt.checkpw(password.encode('utf-8'), admin[3].encode('utf-8')):  # Assuming password is the 4th column
                    session['admin_logged_in'] = True
                    return redirect(url_for('admindashboard'))
            except ValueError:
                flash("Admin password hash invalid. Please reset your password.", "danger")
                return redirect(url_for('login'))
        
        cursor.close()
        flash("Login failed. Check your email and password.", "danger")
    return render_template('login.html')



@app.route('/logout')
def logout():
    """Logout the user or admin."""
    session.pop('user_id', None)
    session.pop('admin_logged_in', None)
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))

@app.route('/admindashboard', methods=['GET', 'POST'])
def admindashboard():
    """Render the admin dashboard and handle movie addition."""
    if not session.get('admin_logged_in'):
        return redirect('/login')

    global netflix_overall  # Declare netflix_overall as global

    if request.method == 'POST':
        try:
            # Gather movie data from the form
            new_data = {
                'show_id': str(uuid.uuid4()),  # Generate a unique ID
                'type': request.form.get('type', 'Movie'),
                'title': request.form.get('title', '').strip().lower(),
                'director': request.form.get('director', '').strip().lower(),
                'cast': request.form.get('cast', '').strip().lower(),
                'country': request.form.get('country', 'Unknown'),
                'date_added': request.form.get('date_added', ''),
                'release_year': request.form.get('release_year', ''),
                'rating': request.form.get('rating', ''),
                'duration': request.form.get('duration', ''),
                'listed_in': request.form.get('listed_in', '').strip().lower(),
                'description': request.form.get('description', '').strip(),
            }

            # Generate 'soup' field by combining other attributes
            new_data['soup'] = (
                new_data['title'] + ' ' + 
                new_data['director'] + ' ' +
                new_data['cast'] + ' ' +
                new_data['listed_in'] + ' ' +
                new_data['description']
            ).strip()

            # Convert the new movie data into a DataFrame
            new_movie_df = pd.DataFrame([new_data])

            # Use pd.concat to add the new movie to the existing DataFrame
            netflix_overall = pd.concat([netflix_overall, new_movie_df], ignore_index=True)

            # Recalculate similarity matrix and save the updated CSV
            preprocess_netflix_data()
            netflix_overall.to_csv('netflix_titles.csv', index=False)
            flash("Movie added successfully!", "success")
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    return render_template('admindashboard.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout."""
    session.pop('admin_logged_in', None)
    flash("Admin logged out successfully.", "success")
    return redirect('/login')

# Run the app
if __name__ == '__main__':
    app.run(debug=False)  # Set debug to False in production
