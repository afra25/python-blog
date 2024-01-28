from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request, g
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

#GRAVATAR
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////mnt/c/Users/aramf/OneDrive/Documents/Programming/Python_100 Days/Day 69/instance/posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
# TODO: Create a User table for all your registered users. 
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, unique=False, nullable=False)

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")

    comments = relationship("Comment", back_populates="parent_post")

    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text : Mapped[str] = mapped_column(Text, nullable=False)

    #connect to User
    author_id : Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    #connect to BlogPost
    post_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")





with app.app_context():
    db.create_all()

#DECORATORS
def admin_required(f):

    @wraps(f)
    def wrapper_function():
        if current_user.id != 1:
            return abort(403, "Error 403: You don't have permission to access this page")
        return f()

    return wrapper_function


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=["GET", "POST"])
def register():
    form =  RegisterForm()

    if form.validate_on_submit():
        # get form data
        name = form.name.data
        email = form.email.data
        password = form.password.data
        password_rep = form.password_repeat.data

        #check if user exists
        if not db.session.execute(db.select(User).where(User.email == email)).scalar() or not db.session.execute(db.select(User).where(User.email == email)).scalar():
            #check if passwords match
            if password == password_rep:
                password_hash = generate_password_hash(password, salt_length=8)

                #create new user
                new_user = User(
                    name = name,
                    email = email,
                    password = password_hash
                )

                #add user to database
                db.session.add(new_user)
                db.session.commit()

                #login user
                login_user(new_user)

                #send to homepage
                return redirect(url_for('get_all_posts'))

            else:
                flash("Your passwords didn't match. Please retry.")

        else:
            flash(f"There alreaedy is an account with this email address or username. Log in instead.")
            return redirect(url_for('login'))

    return render_template("register.html", form=form)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=["GET","POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        # get form data
        email_name = form.email_username.data
        password = form.password.data

        # check email/name
        user = db.session.execute(db.select(User).where(User.name == email_name)).scalar()
        if not user:
            user = db.session.execute(db.select(User).where(User.email == email_name)).scalar()

        # if no user
        if not user:
            flash("Incorrect email or username. Try again.")       

        #check password
        else:
            if check_password_hash(user.password, password):
                login_user(user)

                #send to homepage
                return redirect(url_for('get_all_posts'))
            else:
                flash("Incorrect password. Try again.")

    return render_template("login.html", form=form)


@app.route('/logout', methods=["GET", "POST"])
def logout():

    logout_user()

    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():

    posts = db.session.query(BlogPost).all()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated, user=current_user)



# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    #comments
    form = CommentForm()
    requested_post = db.get_or_404(BlogPost, post_id)

    if form.validate_on_submit():
        comment = form.comment.data

        new_comment = Comment(
            text = comment,

            author_id = current_user.id,
            comment_author = current_user,

            post_id = post_id,
            parent_post = db.get_or_404(BlogPost, post_id)
        )
    
        db.session.add(new_comment)
        db.session.commit()

    return render_template("post.html", post=requested_post, form=form)


# TODO: Use a decorator so only an admin user can create a new post

@app.route("/new-post", methods=["GET", "POST"])
@admin_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_required
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_required
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True, port=5002)