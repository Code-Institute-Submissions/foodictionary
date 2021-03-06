# DEPENDENCIES --------------------------------------------#
import os
import pymongo
import math
import random
from flask import Flask, flash, render_template, redirect, request, url_for, request, session, g, abort
from flask_toastr import Toastr
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# CONNECT TO MONGODB DATABASE -----------------------------#
app = Flask(__name__)
toastr = Toastr(app)
app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://localhost')
app.secret_key = os.getenv('SECRET_KEY', 'randomstring123')

mongo = PyMongo(app)

# VARIABLES -----------------------------------------------#
recipes = mongo.db.recipes
recipeCategory = mongo.db.recipeCategory
allergens = mongo.db.allergens
skillLevel = mongo.db.skillLevel
userDB = mongo.db.users


# HOMEPAGE ------------------------------------------------#
@app.route('/')
@app.route('/home')
def home():
    tags = recipes.distinct('recipe_tags')
    random.shuffle(tags)
    username = session.get('username')
    return render_template('home.html', recipes=recipes.find().sort('date_time', pymongo.DESCENDING),
                           recipeCategory=list(recipeCategory.find()), page=1, tags=tags, page_title='FOODictionary - Home page')


# RANDOM MEAL PAGE ----------------------------------------#
@app.route('/random_meal')
def random_meal():
    return render_template('random_meal.html', recipeCategory=list(recipeCategory.find()), page_title='FOODictionary - Random Recipe')


# USER LOGIN AND REGISTRATION -----------------------------#
@app.route('/register')
def register():
    return render_template('register.html', page_title='FOODictionary - Register')


@app.route('/signup', methods=['POST'])
def signup():
    session.permanent = True
    #app.permanent_session_lifetime = timedelta(minutes=30)
    author_name = request.form.get('author_name')
    username = request.form.get('username').lower()
    password = generate_password_hash(request.form.get('password'))
    session['username'] = username
    user = userDB.find_one({'username': username})

    if user is None:
        userDB.insert_one({
            'author_name': author_name,
            'username': username,
            'password': password
        })
        session['logged_in'] = True
        flash('Welcome to FOODictionary ' + author_name + '!', 'success')
        return redirect('home')
    else:
        session['logged_in'] = False
        flash('Username already exists, please try again.', 'success')
    return register()


@app.route('/login')
def login():
    if not session.get('logged_in'):
        return render_template('login.html', page_title='FOODictionary - Log in')
    else:
        return redirect('home', page_title='FOODictionary - Home page')


@app.route('/signin', methods=['POST'])
def signin():
    username = request.form['username'].lower()
    password = request.form['password']
    session['username'] = username
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)
    user = userDB.find_one({'username': username})

    if not user:
        session['logged_in'] = False
        flash('User ' + session['username'] +
              ' is not registered. Please try again.', 'warning')
        return render_template('login.html')
    elif not check_password_hash(user['password'], password):
        session['logged_in'] = False
        flash('Wrong Password, please try again.', 'warning')
        return render_template('login.html')
    else:
        session['logged_in'] = True
        flash('Welcome back ' +
              user['author_name'].capitalize() + '!', 'success')
        return redirect('home')


@app.route('/logout', methods=['GET'])
def logout():
    session['logged_in'] = False
    session['username'] = None
    flash('You are now logged out!', 'success')
    return redirect('home')


# RECIPES SECTION #

# ---------------------------------------------------- #
# ------------- browse_recipes.html ------------------ #
# ---------------------------------------------------- #
# BROWSE RECIPE CATEGORIES --------------------------------#
@app.route('/browse_recipes/<recipe_category_name>/<page>', methods=['GET'])
def browse_recipes(recipe_category_name, page):
    tags = recipes.distinct("recipe_tags")
    random.shuffle(tags)
    # Count the number of recipes in the Database
    all_recipes = recipes.find({'recipe_category_name': recipe_category_name}).sort([('date_time', pymongo.DESCENDING),
                                                                                     ('_id', pymongo.ASCENDING)])
    count_recipes = all_recipes.count()

    # Variables for Pagination
    offset = (int(page) - 1) * 6
    limit = 6

    recipe_pages = recipes.find({'recipe_category_name': recipe_category_name}).sort([("date_time", pymongo.DESCENDING),
                                                                                      ("_id", pymongo.ASCENDING)]).skip(offset).limit(limit)
    total_no_of_pages = int(math.ceil(count_recipes/limit))

    return render_template('browse_recipes.html',
                           recipes=recipe_pages, recipeCategory=list(recipeCategory.find()), count_recipes=count_recipes, total_no_of_pages=total_no_of_pages,
                           page=page, recipe_category_name=recipe_category_name, tags=tags, page_title='FOODictionary - Browse Recipes')

# UPDATE AS A FAVORITE RECIPE --------------------------------------------#
@app.route('/add_favorite_recipe_browse_recipes/<recipe_id>/<recipe_category_name>?page=<page>&destination=<destination>', methods=['GET'])
def add_favorite_recipe_browse_recipes(recipe_id, recipe_category_name, page, destination):
    recipes.update({'_id': ObjectId(recipe_id)},
                   {
        '$set': {
            'favorite': True
        }
    })
    return redirect(url_for(destination, recipe_category_name=recipe_category_name, page=page))

# REMOVE AS A FAVORITE RECIPE --------------------------------------------#
@app.route('/remove_favorite_recipe_browse_recipes/<recipe_id>/<recipe_category_name>?page=<page>&destination=<destination>', methods=['GET'])
def remove_favorite_recipe_browse_recipes(recipe_id, recipe_category_name, page, destination):
    recipes.update({'_id': ObjectId(recipe_id)},
                   {
        '$set': {
            'favorite': False
        }
    })
    return redirect(url_for(destination, recipe_category_name=recipe_category_name, page=page))


# ---------------------------------------------------- #
# ------------- add_recipe.html ---------------------- #
# ---------------------------------------------------- #
@app.route('/add_recipe')
def add_recipe():
    return render_template('add_recipe.html', recipes=recipes.find(), recipeCategory=list(recipeCategory.find()),
                           skillLevel=skillLevel.find(), allergens=allergens.find(), userDB=userDB.find(), page_title='FOODictionary - Add a  Recipe')


@app.route('/insert_recipe', methods=['POST'])
def insert_recipe():
    username = session.get('username')
    user = userDB.find_one({'username': username})
    # Request Recipe tags and split into array based on comma
    recipe_tags = request.form.get('recipe_tags')
    recipe_tags_split = [x.strip() for x in recipe_tags.split(',')]
    complete_recipe = {
        'recipe_name': request.form.get('recipe_name'),
        'recipe_description': request.form.get('recipe_description'),
        'recipe_category_name': request.form.get('recipe_category_name'),
        'allergen_type': request.form.getlist('allergen_type'),
        'recipe_prep_time': request.form.get('recipe_prep_time'),
        'recipe_cook_time': request.form.get('recipe_cook_time'),
        'recipe_serves': request.form.get('recipe_serves'),
        'recipe_difficulty': request.form.get('recipe_difficulty'),
        'recipe_image': request.form.get('recipe_image'),
        'recipe_ingredients':  request.form.getlist('recipe_ingredients'),
        'recipe_method':  request.form.getlist('recipe_method'),
        'date_time': datetime.now(),
        'author_name': user['username'],
        'favorite': request.form.get('favorite') == 'on',
        'recipe_tags': recipe_tags_split
    }
    recipes.insert_one(complete_recipe)
    return redirect(url_for('add_recipe'))


# --------------------------------------------------- #
# ---------------- Delete Recipe -------------------- #
# --------------------------------------------------- #

@app.route('/delete_recipe/<recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    recipes.delete_one({'_id': ObjectId(recipe_id)})
    return redirect(url_for('my_recipes', page=1))


# ---------------------------------------------------- #
# ------------- edit_recipes.html -------------------- #
# ---------------------------------------------------- #

@app.route('/edit_recipe/<recipe_id>')
def edit_recipe(recipe_id):
    return render_template('edit_recipe.html', recipeCategory=list(recipeCategory.find()),
                           allergens=allergens.find(), skillLevel=skillLevel.find(), page=1, recipes=recipes.find_one({'_id': ObjectId(recipe_id)}))


@app.route('/update_recipe/<recipe_id>', methods=['POST'])
def update_recipe(recipe_id):
    recipe_tags = request.form.get('recipe_tags')
    recipe_tags_split = [x.strip() for x in recipe_tags.split(',')]
    recipes.update({'_id': ObjectId(recipe_id)},
                   {
        '$set': {
            'recipe_name': request.form.get('recipe_name'),
            'recipe_description': request.form.get('recipe_description'),
            'recipe_category_name': request.form.get('recipe_category_name'),
            'allergen_type': request.form.getlist('allergen_type'),
            'recipe_prep_time': request.form.get('recipe_prep_time'),
            'recipe_cook_time': request.form.get('recipe_cook_time'),
            'recipe_serves': request.form.get('recipe_serves'),
            'recipe_difficulty': request.form.get('recipe_difficulty'),
            'recipe_image': request.form.get('recipe_image'),
            'recipe_ingredients':  request.form.getlist('recipe_ingredients'),
            'recipe_method':  request.form.getlist('recipe_method'),
            'recipe_tags': recipe_tags_split,
            'favorite': request.form.get('favorite')
        }
    })
    return redirect(url_for('my_recipes', page=1))

# --------------------------------------------------------- #
# ------------------ recipe.html ------------------------- #
# --------------------------------------------------------- #

# MY RECIPE (see my individual recipe in recipe.html) ----- #
@app.route('/recipe_page/<recipe_id>', methods=['GET'])
def recipe_page(recipe_id):
    username = session.get('username')
    logged_in = session.get('logged_in')
    user = userDB.find_one({'username': username})
    if not user:
        return render_template('recipe.html', recipe=recipes.find_one({'_id': ObjectId(recipe_id)}), recipe_id=recipe_id, recipeCategory=list(recipeCategory.find()),  page=1)
    else:
        return render_template('recipe.html', recipe=recipes.find_one({'_id': ObjectId(recipe_id)}), recipe_id=recipe_id, recipeCategory=list(recipeCategory.find()),
                               user=user, page=1, page_title='FOODictionary - Recipe')

# UPDATE AS A FAVORITE RECIPE --------------------------------------------#
@app.route('/add_favorite_recipe_page/<recipe_id>', methods=['GET'])
def add_favorite_recipe_page(recipe_id):
    recipes.update({'_id': ObjectId(recipe_id)},
                   {
        '$set': {
            'favorite': True
        }
    })
    return redirect(url_for('recipe_page', recipe_id=recipe_id))


# REMOVE AS A FAVORITE RECIPE --------------------------------------------#
@app.route('/remove_favorite_recipe_page/<recipe_id>', methods=['GET'])
def remove_favorite_recipe_page(recipe_id):
    recipes.update({'_id': ObjectId(recipe_id)},
                   {
        '$set': {
            'favorite': False
        }
    })
    return redirect(url_for('recipe_page', recipe_id=recipe_id))

# ------------------------------------------------------------ #
# ------------------ my_recipes.html ------------------------- #
# ------------------------------------------------------------ #

# MY RECIPE's (see my my_recipes.html) ----------------------- #
@app.route('/my_recipes/<page>', methods=['GET'])
def my_recipes(page):
    username = session.get('username')
    user = userDB.find_one({'username': username})

    all_recipes = recipes.find({'author_name': username}).sort(
        [('date_time', pymongo.DESCENDING), ('_id', pymongo.ASCENDING)])
    count_recipes = all_recipes.count()

    offset = (int(page) - 1) * 6
    limit = 6
    total_no_of_pages = int(math.ceil(count_recipes/limit))
    recipe_pages = recipes.find({'author_name': username}).sort([("date_time", pymongo.DESCENDING),
                                                                 ("_id", pymongo.ASCENDING)]).skip(offset).limit(limit)

    return render_template('my_recipes.html',
                           recipes=recipe_pages.sort('date_time', pymongo.DESCENDING), count_recipes=count_recipes,
                           total_no_of_pages=total_no_of_pages, page=page, author_name=username, recipeCategory=list(recipeCategory.find()), page_title='FOODictionary - My Recipes')

# -------------------------------------------------------------- #
# ------------------ my_favorite_recipes.html ------------------ #
# -------------------------------------------------------------- #

# MY FAVORITE RECIPE's ----------------------------------------- #
@app.route('/my_favorite_recipes/<page>', methods=['GET'])
def my_favorite_recipes(page):
    username = session.get('username')
    user = userDB.find_one({'username': username})

    all_recipes = recipes.find({'author_name': username, 'favorite': True}).sort(
        [('date_time', pymongo.DESCENDING), ('_id', pymongo.ASCENDING)])
    count_recipes = all_recipes.count()

    offset = (int(page) - 1) * 6
    limit = 6
    total_no_of_pages = int(math.ceil(count_recipes/limit))
    recipe_pages = recipes.find({'author_name': username, 'favorite': True}).sort([("date_time", pymongo.DESCENDING),
                                                                                   ("_id", pymongo.ASCENDING)]).skip(offset).limit(limit)

    return render_template('my_favorite_recipes.html',
                           recipes=recipe_pages.sort('date_time', pymongo.DESCENDING), count_recipes=count_recipes, author_name=username, recipeCategory=list(recipeCategory.find()), total_no_of_pages=total_no_of_pages, page=page, page_title='FOODictionary - My Favorite recipes')

# UPDATE AS A FAVORITE RECIPE --------------------------------------------#
@app.route('/add_favorite_recipe/<recipe_id>?page=<page>&destination=<destination>', methods=['GET'])
def add_favorite_recipe(recipe_id, page, destination):
    recipes.update({'_id': ObjectId(recipe_id)},
                   {
        '$set': {
            'favorite': True
        }
    })
    return redirect(url_for(destination, page=page))

# REMOVE AS A FAVORITE RECIPE --------------------------------------------#
@app.route('/remove_favorite_recipe/<recipe_id>?page=<page>&destination=<destination>', methods=['GET'])
def remove_favorite_recipe(recipe_id, page, destination):
    recipes.update({'_id': ObjectId(recipe_id)},
                   {
        '$set': {
            'favorite': False
        }
    })
    return redirect(url_for(destination, page=page))

# ADD TO FAVORITE MEAL SECTION  --------------------------------------------#
@app.route('/recipe_favorite/<recipe_id>', methods=['POST'])
def recipe_favorite(recipe_id):
    username = session.get('username')
    user = userDB.find_one({'username': username})
    new_favorite = request.form['favorite']
    recipe = recipes.find_one({'_id': ObjectId(recipe_id)})

    for new_favorite in recipe['favorite']:
        overall_favorite = favorite['favorite']

    recipes.update({'_id': ObjectId(recipe_id)},
                   {'$set': {
                       'favorite': 'testFavorite'
                   }})

    userDB.update({"username": username},
                  {'$addToSet':
                   {'favorite': recipe_id}})
    return redirect(url_for('recipe_page', recipe_id=recipe_id))

# ---------------------------------------------------- #
# ------------- keyword_search.html ------------------ #
# ---------------------------------------------------- #


@app.route('/keyword_search', methods=['POST'])
def receive_keyword():
    return redirect(url_for('keyword_search', keyword=request.form.get('keyword'), page=1))


@app.route('/keyword_search/<keyword>/<page>', methods=['GET'])
def keyword_search(keyword, page):
    recipes.create_index(
        [('recipe_name', 'text'), ('recipe_ingredients', 'text'), ('recipe_category_name', 'text')])

    all_recipes = recipes.find({'$text': {'$search': keyword}}).sort(
        [('date_time', pymongo.DESCENDING), ('_id', pymongo.ASCENDING)])
    count_recipes = all_recipes.count()

    offset = (int(page) - 1) * 6
    limit = 6
    total_no_of_pages = int(math.ceil(count_recipes/limit))

    recipe_pages = recipes.find({'$text': {'$search': keyword}}).sort([("date_time", pymongo.DESCENDING),
                                                                       ("_id", pymongo.ASCENDING)]).skip(offset).limit(limit)

    return render_template('keyword_search.html', keyword=keyword,
                           search_results=recipe_pages.sort(
                               'date_time', pymongo.DESCENDING), count_recipes=count_recipes, recipeCategory=list(recipeCategory.find()),
                           total_no_of_pages=total_no_of_pages, page=page, page_title='FOODictionary - Search by Keyword')

# UPDATE AS A FAVORITE RECIPE --------------------------------------------#
@app.route('/add_favorite_recipe_keyword_search/<recipe_id>/<keyword>?page=<page>', methods=['GET'])
def add_favorite_recipe_keyword_search(recipe_id, keyword, page):
    recipes.update({'_id': ObjectId(recipe_id)},
                   {
        '$set': {
            'favorite': True
        }
    })
    return redirect(url_for('keyword_search', keyword=keyword, page=page))

# REMOVE AS A FAVORITE RECIPE --------------------------------------------#
@app.route('/remove_favorite_recipe_keyword_search/<recipe_id>/<keyword>?page=<page>', methods=['GET'])
def remove_favorite_recipe_keyword_search(recipe_id, keyword, page):
    recipes.update({'_id': ObjectId(recipe_id)},
                   {
        '$set': {
            'favorite': False
        }
    })
    return redirect(url_for('keyword_search', keyword=keyword, page=page))

# ------------------------------------------------------- #
# -------------------- tag_search.html ------------------ #
# ------------------------------------------------------- #


@app.route('/tag_search', methods=['GET'])
def receive_tag():
    return redirect(url_for('tag_search', keyword=request.form.get('tag'), page=1))


@app.route('/tag_search/<tag>/<page>', methods=['GET'])
def tag_search(tag, page):
    recipes.create_index([('recipe_tags', pymongo.ASCENDING)])

    all_recipes = recipes.find({'recipe_tags': tag}).sort(
        [('date_time', pymongo.DESCENDING), ('_id', pymongo.ASCENDING)])
    count_recipes = all_recipes.count()

    offset = (int(page) - 1) * 6
    limit = 6
    total_no_of_pages = int(math.ceil(count_recipes/limit))

    recipe_pages = recipes.find({'recipe_tags': tag}).sort([("date_time", pymongo.DESCENDING),
                                                            ("_id", pymongo.ASCENDING)]).skip(offset).limit(limit)

    return render_template('tag_search.html', tag=tag,
                           search_results=recipe_pages.sort(
                               'date_time', pymongo.DESCENDING), count_recipes=count_recipes, recipeCategory=list(recipeCategory.find()),
                           total_no_of_pages=total_no_of_pages, page=page, page_title='FOODictionary - Search by Tag')

# UPDATE AS A FAVORITE RECIPE --------------------------------------------#
@app.route('/add_favorite_recipe_tag_search/<recipe_id>/<tag>?page=<page>', methods=['GET'])
def add_favorite_recipe_tag_search(recipe_id, tag, page):
    recipes.update({'_id': ObjectId(recipe_id)},
                   {
        '$set': {
            'favorite': True
        }
    })
    return redirect(url_for('tag_search', tag=tag, page=page))

# REMOVE AS A FAVORITE RECIPE --------------------------------------------#
@app.route('/remove_favorite_recipe_tag_search/<recipe_id>/<tag>?page=<page>', methods=['GET'])
def remove_favorite_recipe_tag_search(recipe_id, tag, page):
    recipes.update({'_id': ObjectId(recipe_id)},
                   {
        '$set': {
            'favorite': False
        }
    })
    return redirect(url_for('tag_search', tag=tag, page=page))

# -------------------------------------------------------------- #
# ----------------------- Error Pages -------------------------- #
# -------------------------------------------------------------- #


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html', page=1, page_title='FOODictionary - 404 Error Page'), 404


@app.errorhandler(405)
def page_not_found(error):
    return render_template('405.html', page=1, page_title='FOODictionary - 405 Method Not Allowed'), 405


@app.errorhandler(500)
def something_wrong(error):
    return render_template('500.html', page=1, page_title='FOODictionary - 500 Error'), 500


if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=(os.environ.get('PORT')),
            debug=False)
