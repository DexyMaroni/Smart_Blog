import os 
import secrets
from PIL import Image
from flask import render_template, flash, url_for, redirect, request, abort
from Bluey_blog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, RequestResetForm, ResetPasswordForm
from Bluey_blog.models import User, Post, Comment
from Bluey_blog import app, db, bcrypt, mail
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from Bluey_blog.forms import CommentForm, UpdateCommentForm
from datetime import datetime, timezone

@app.route("/")
def landing_page():
    ''' Returns a landing page. '''
    return render_template('landing_page.html', title ="Landing Page")
 

@app.route("/home")
def home():
    ''' Returns a home page consisting of posts. '''
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(per_page=5)
    return render_template('home.html', posts = posts, title = "Home")


@app.route("/about")
def about():
    ''' Returns an about page that briefly talks about the developer and purpose of this project. '''
    return render_template('about.html')


@app.route("/register", methods=['GET', 'POST'])
def register():
    ''' Returns a registration page. '''
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    # Validating the data passed into the form
    if form.validate_on_submit(): 
        # Hashing the password and storing the hashed password to the database using the bcrypt module
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf=8') 
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f"Hurray!!! Your Account has been created!!! You are now able to log in", 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title= 'Register', form=form )


@app.route("/login", methods=['GET', 'POST'])
def login():
    ''' Returns a login page. '''
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        # The line to code below acts like a recover (from the database) and validate function.
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            # Logs in the user and redirects to the home page or next page.
            return redirect(next_page) if next_page else redirect(url_for('home')) 
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')

    return render_template('login.html', title= 'Login', form = form)


@app.route("/logout")
def logout():
    ''' A function that logs out a user. '''
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    ''' A function that uplods and saves an image. '''
    random_hex = secrets.token_hex(8) # Generating a token of 8 characters as the filename.
    _, f_ext = os.path.splitext(form_picture.filename) # Separating the file extension from the original filename.
    picture_fn = random_hex + f_ext # Joining the token with the file extension

    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn) # Setting a location for the image
    output_size = (125, 125) # Cropping the image
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path) # Saving the image
    return picture_fn # Returns the filename that acts as a pointer to the image file


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    ''' Returns a page that presents info on the user '''
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file # Sets image file for the user.

        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your Account Has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    # The database dosen't save the image file but the filename and location of the image for each user.
    return render_template('account.html', title='Account', image_file=image_file, form = form)


@app.route("/post/new",  methods=['GET', 'POST'])
@login_required
def new_post():
    ''' Returns a page that enables the user to create posts. '''
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title= form.title.data, content= form.content.data, author= current_user )
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success' )
        return redirect(url_for('home'))
    return render_template('create_post.html', title = 'New Post', form=form, legend= 'New Post')


@app.route("/post/<int:post_id>", methods= ['GET', 'POST'])
def post(post_id):
    ''' Returns a page that gives mor info on a users post '''
    post = Post.query.get_or_404(post_id)
    form = CommentForm() #Update
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, author=current_user, post=post)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been posted!', 'success')
        return redirect(url_for('post', post_id=post.id))
    comments = Comment.query.filter_by(post_id=post.id).all()
    return render_template('post.html', title=post.title, post=post, comments=comments, form=form)
    

@app.route("/post/<int:post_id>/update", methods= ['GET', 'POST'])
@login_required # Ensuring that only authorized user can proceed.
def update_post(post_id):
    ''' Enables the user to modify a post. '''
    post = Post.query.get_or_404(post_id) # Queries a specific post according to id.
    if post.author != current_user:
        abort(403)

    form = PostForm() # Calling the form model.
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title = 'Update Post', form=form, legend= 'Update Post' )


@app.route("/post/<int:post_id>/delete", methods= ['POST'])
@login_required
def delete_post(post_id):
    ''' Deletes a post. '''
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!!!', 'success')
    return redirect(url_for('home'))


@app.route("/user/<string:username>")
def user_posts(username):
    ''' Return a page that groups all posts related to a user. '''
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404() # Queries the database and filters by username and returns None if the user does not exist
    posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).paginate(per_page=5)
    return render_template('user_posts.html', posts = posts,  user= user)

def send_reset_email(user):
    ''' Sends an email with a reset token. '''
    token = user.get_reset_token()
    msg = Message('Password Reset Request ', sender='blueyblog@gmail.com', recipients=[user.email])
    msg.body = f'''To reset your password, visit the the following link: {url_for('reset_token', token=token, _external=True)}

    
If you did not make this request then simply ignore this email and no changes will be made. 

Regards Bluey INC. 
'''
    mail.send(msg)


@app.route("/reset_password",  methods=['GET', 'POST'])
def reset_request():
    ''' Peforms a password reset request'''
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash("An email has been sent with instructions to reset your password", 'info')
        return redirect(url_for('login'))
    return render_template('reset_requests.html', title = 'Reset Password', form = form)


@app.route("/reset_password/<token>",  methods=['GET', 'POST'])
def reset_token(token):
    ''' Generates a token and verfies the token. '''
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('Invalid or Expired Token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf=8') # Decodes the hashed password.
        user.password = hashed_password
        db.session.commit()
        flash(f"Hurray!!! Your Password has been Updated!!! You are now able to log in", 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title= 'Reset Password', form=form)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'),404


@app.errorhandler(401)
def page_not_found(error):
    return render_template('401.html'),401

@app.errorhandler(404)
def page_not_found(error):
    return render_template('500.html'),500


# Route to update a comment
# routes.py
@app.route("/comment/<int:comment_id>/update", methods=['GET', 'POST'])
@login_required
def update_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.author != current_user:
        abort(403)
    form = UpdateCommentForm()
    if form.validate_on_submit():
        comment.content = form.content.data
        Comment.date_posted = datetime.now()
        db.session.commit()
        flash('Your comment has been updated!', 'success')
        return redirect(url_for('post', post_id=comment.post_id))
    elif request.method == 'GET':
        form.content.data = comment.content
    return render_template('update_comment.html', title='Update Comment', form=form, current_user=current_user, comment= comment)


# Route to delete a comment
@app.route("/comment/<int:comment_id>/delete", methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.author != current_user:
        abort(403)
    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    flash('Your comment has been deleted!', 'success')
    return redirect(url_for('post', post_id=post_id))