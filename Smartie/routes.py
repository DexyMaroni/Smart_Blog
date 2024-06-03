import os 
import secrets
from PIL import Image
from flask import render_template, flash, url_for, redirect, request, abort
from Smartie.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, RequestResetForm, ResetPasswordForm, CommentForm, ReplyForm,  PostForm, UpdateCommentForm
from Smartie.models import User, Post, Comment, Reply
from Smartie import app, db, bcrypt, mail
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from Smartie.forms import CommentForm, UpdateCommentForm
from datetime import datetime, timezone
from flask import request
from flask_paginate import Pagination, get_page_parameter

@app.route("/")
def landing_page():
    ''' Returns a landing page. '''
    return render_template('landing_page.html', title ="Landing Page")


@app.route("/comment/<int:comment_id>/delete", methods=['POST'])
@login_required
def delete_comment(comment_id):
     """
     Deletes a comment by its ID if the user is logged in and is the author of the comment.
     
     Parameters:
         comment_id (int): The ID of the comment to be deleted.
     
     Returns:
         redirect: A redirect to the post page of the comment's post.
     
     Raises:
         abort(403): If the user is not logged in or is not the author of the comment.
     """
     comment = Comment.query.get_or_404(comment_id)
     if comment.author != current_user:
         abort(403)
     post_id = comment.post_id
     db.session.delete(comment)
     db.session.commit()
     flash('Your comment has been deleted!', 'success')
     return redirect(url_for('post', post_id=post_id))
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


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def post(post_id):
    post = Post.query.get_or_404(post_id)
    form = CommentForm()
    reply_form = ReplyForm()
    
    # Handle comment submission
    if form.validate_on_submit() and 'parent_id' not in request.form:
        comment = Comment(content=form.content.data, author=current_user, post_id=post.id)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been posted!', 'success')
        return redirect(url_for('post', post_id=post.id))
    
    # Handle reply submission
    if reply_form.validate_on_submit() and 'parent_id' in request.form:
        parent_id = request.form.get("parent_id")
        parent_comment = Comment.query.get_or_404(parent_id)
        reply = Comment(content=reply_form.content.data, author=current_user, post_id=post.id, parent_id=parent_comment.id)
        db.session.add(reply)
        db.session.commit()
        flash('Your reply has been posted!', 'success')
        return redirect(url_for('post', post_id=post.id))
    
    # Pagination for comments
    page = request.args.get('page', 1, type=int)
    comments = Comment.query.filter_by(post_id=post.id, parent_id=None).paginate(page=page, per_page=5)
    
    return render_template('post.html', title=post.title, post=post, comments=comments, form=form, reply_form=reply_form)


    
    return render_template('post.html', title=post.title, post=post, comments=comments, form=form)

# Route to delete a comment
@app.route("/comment/<int:comment_id>/delete", methods=['POST'])
@login_required
def delete_comment(comment_id):
    """
    Deletes a comment by its ID if the user is logged in and is the author of the comment.
    
    Parameters:
        comment_id (int): The ID of the comment to be deleted.
    
    Returns:
        redirect: A redirect to the post page of the comment's post.
    
    Raises:
        abort(403): If the user is not logged in or is not the author of the comment.
    """
    abort(403)
    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    flash('Your comment has been deleted!', 'success')
    return redirect(url_for('post', post_id=post_id))

@app.route("/comment/<int:comment_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    """
    Edit a comment with the given comment_id.

    Parameters:
        comment_id (int): The ID of the comment to be edited.

    Returns:
        flask.Response: The response object containing the rendered template or a redirect to the post page.

    Raises:
        403: If the current user is not the author of the comment.
    """
    comment = Comment.query.get_or_404(comment_id)
    if comment.author != current_user:
        abort(403)
    form = CommentForm()
    if form.validate_on_submit():
        comment.content = form.content.data
        db.session.commit()
        flash('Your comment has been updated!', 'success')
        return redirect(url_for('post', post_id=comment.post_id))
    elif request.method == 'GET':
        form.content.data = comment.content
    return render_template('edit_comment.html', title='Edit Comment', form=form)


@app.route("/comment/<int:comment_id>/reply", methods=['GET', 'POST'])
@login_required
def reply_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    form = ReplyForm()
    if form.validate_on_submit():
        reply = Reply(content=form.content.data, user_id=current_user.id, comment_id=comment.id)
        db.session.add(reply)
        db.session.commit()
        flash('Your reply has been posted!', 'success')
        return redirect(url_for('post', post_id=comment.post_id))
    return render_template('reply.html', title='Reply to Comment', form=form, comment=comment)


@app.route("/reply/<int:reply_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_reply(reply_id):
    reply = Reply.query.get_or_404(reply_id)
    if reply.author != current_user:
        abort(403)
    form = ReplyForm()
    if form.validate_on_submit():
        reply.content = form.content.data
        db.session.commit()
        flash('Your reply has been updated!', 'success')
        return redirect(url_for('post', post_id=reply.comment.post_id))
    elif request.method == 'GET':
        form.content.data = reply.content
    return render_template('edit_reply.html', title='Edit Reply', form=form, reply=reply)

@app.route("/reply/<int:reply_id>/delete", methods=['POST'])
@login_required
def delete_reply(reply_id):
    reply = Reply.query.get_or_404(reply_id)
    if reply.author != current_user:
        abort(403)
    db.session.delete(reply)
    db.session.commit()
    flash('Your reply has been deleted!', 'success')
    return redirect(url_for('post', post_id=reply.comment.post_id))


@app.route("/comment/<int:comment_id>/downvote", methods=['POST'])
@login_required
def downvote_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.downvotes += 1
    db.session.commit()
    flash('Comment downvoted!', 'success')
    return redirect(request.referrer)



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
    """
    Handles the HTTP 404 error by rendering the '404.html' template and returning it with a 404 status code.

    :param error: The HTTP 404 error object.
    :type error: werkzeug.exceptions.HTTPException

    :return: A tuple containing the rendered '404.html' template and the 404 status code.
    :rtype: tuple[str, int]
    """


@app.errorhandler(401)
def page_not_found(error):
        """
        Handles the HTTP 401 error by rendering the '401.html' template and returning it with a 401 status code.
        
        :param error: The HTTP 401 error object.
        :type error: werkzeug.exceptions.HTTPException
        
        :return: A tuple containing the rendered '401.html' template and the 401 status code.
        :rtype: tuple[str, int]
        """

@app.errorhandler(404)
def page_not_found(error):
    """
    Handles the HTTP 404 error by rendering the '500.html' template and returning it with a 500 status code.

    :param error: The HTTP 404 error object.
    :type error: werkzeug.exceptions.HTTPException

    :return: A tuple containing the rendered '500.html' template and the 500 status code.
    :rtype: tuple[str, int]
    """


# Route to update a comment
@app.route("/comment/<int:comment_id>/update", methods=['GET', 'POST'])
@login_required
def update_comment(comment_id):
    """
    Updates a comment with the given comment_id if the user is logged in and is the author of the comment.
    
    :param comment_id: The ID of the comment to be updated.
    :type comment_id: int
    
    :return: If the comment is successfully updated, redirects to the post page of the comment's post with a success message.
             If the user is not logged in or is not the author of the comment, returns a 403 error.
             If the comment is not found, returns a 404 error.
    :rtype: flask.Response
    """
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






@app.route("/comment/<int:comment_id>/upvote", methods=['POST'])
@login_required
def upvote_comment(comment_id):
    """
    Updates the upvotes count of a comment with the given comment_id if the user is logged in.
    
    :param comment_id: The ID of the comment to be upvoted.
    :type comment_id: int
    
    :return: Redirects to the post page of the comment's post with a success message.
             If the user is not logged in, returns a 403 error.
             If the comment is not found, returns a 404 error.
    :rtype: flask.Response
    """
    comment = Comment.query.get_or_404(comment_id)
    if current_user == comment.author:
        abort(403)
    comment.upvotes += 1
    db.session.commit()
    flash('Comment upvoted!', 'success')
    return redirect(url_for('post', post_id=comment.post_id))


