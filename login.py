from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Flask app setup
app = Flask(__name__)
app.secret_key = "your_secret_key"

# Example users for authentication
users = {
    "admin": "password123",  # username: password
    "user1": "mypassword",
}

# Data preprocessing (unchanged)
def clean_data(x):
    return str.lower(x.replace(" ", ""))

def create_soup(x):
    return x['title'] + ' ' + x['director'] + ' ' + x['cast'] + ' ' + x['listed_in'] + ' ' + x['description']

def get_recommendations(title, cosine_sim):
    global result
    title = title.replace(' ', '').lower()
    idx = indices[title]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:11]
    movie_indices = [i[0] for i in sim_scores]
    result = netflix_overall['title'].iloc[movie_indices]
    result = result.to_frame()
    result = result.reset_index()
    del result['index']
    return result

# Load Netflix data
netflix_overall = pd.read_csv('netflix_titles.csv')
netflix_data = pd.read_csv('netflix_titles.csv').fillna('')
new_features = ['title', 'director', 'cast', 'listed_in', 'description']
netflix_data = netflix_data[new_features]
for feature in new_features:
    netflix_data[feature] = netflix_data[feature].apply(clean_data)
netflix_data['soup'] = netflix_data.apply(create_soup, axis=1)
count = CountVectorizer(stop_words='english')
count_matrix = count.fit_transform(netflix_data['soup'])
cosine_sim2 = cosine_similarity(count_matrix, count_matrix)
netflix_data = netflix_data.reset_index()
indices = pd.Series(netflix_data.index, index=netflix_data['title'])

# Routes
@app.route('/')
def login():
    return render_template('login.html')  # Login page

@app.route('/login', methods=['POST'])
def login_user():
    username = request.form['username']
    password = request.form['password']
    if username in users and users[username] == password:
        session['username'] = username  # Store username in session
        return redirect(url_for('index'))  # Redirect to movie page
    else:
        return "Invalid username or password! <a href='/'>Try Again</a>"

@app.route('/index')
def index():
    if 'username' not in session:  # Check if logged in
        return redirect(url_for('login'))
    return render_template('index.html')  # Main page

@app.route('/about', methods=['POST'])
def getvalue():
    if 'username' not in session:  # Check if logged in
        return redirect(url_for('login'))
    moviename = request.form['moviename']
    get_recommendations(moviename, cosine_sim2)
    df = result
    return render_template('result.html', tables=[df.to_html(classes='data')], titles=df.columns.values)

@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove username from session
    return redirect(url_for('login'))  # Redirect to login page

if __name__ == '__main__':
    app.run(debug=False)
