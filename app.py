from flask import Flask, render_template, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash,check_password_hash
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager,UserMixin, login_user, login_required, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField,BooleanField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo
import redis
import json
import os

# ---------------- Necessary definitions -------------------------  
appi = Flask(__name__)
appi.config['SECRET_KEY']="thisissecret"
# username = "postgres"
# password = "postgres"
# dbname = "todos"
# appi.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
appi.config.from_pyfile('config.cfg')
db=SQLAlchemy(appi)  
migrate = Migrate(appi, db)
CSRFProtect(appi)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(appi)
redis_client = redis.StrictRedis(host='redis-service',port=6379,decode_responses=True)
application=appi

# ---------------- Models -------------------------
class User(UserMixin,db.Model):
    __tablename__="users"
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(20))
    surname = db.Column(db.String(20))
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200), unique=True)
    jobs = db.relationship('Project',backref='user')
    
    def __init__(self,name,surname,email,password):
        
        self.email = email
        self.password=generate_password_hash(password)
        self.name = name
        self.surname = surname
    
    def __repr__(self):
        return f"< Name:{self.name} {self.surname} Email: {self.email} >"

class Project(db.Model):
    __tablename__="projects"
    id = db.Column(db.Integer,primary_key=True)
    project_name=db.Column(db.String(50))
    project_description = db.Column(db.String())
    user_id = db.Column(db.Integer,db.ForeignKey("users.id"))
    is_finished = db.Column(db.Boolean())
    jobs = db.relationship('Job',backref='project')
    def __init__(self,project_name,project_description,user_id):
        self.project_name=project_name
        self.project_description = project_description
        self.is_finished=False
        self.user_id=user_id

class Job(db.Model):
    __tablename__="jobs"
    id = db.Column(db.Integer,primary_key=True)
    job_name = db.Column(db.String(50))
    job_description = db.Column(db.String(500))
    is_in_progress = db.Column(db.Boolean())
    is_finished = db.Column(db.Boolean())
    project_id = db.Column(db.Integer,db.ForeignKey("projects.id"))
    
    def __init__(self,job_name,job_description,project_id):
        self.job_name=job_name
        self.job_description = job_description
        self.is_in_progress=False
        self.is_finished=False
        self.project_id=project_id
    
    def __repr__(self):
        return "Job Name: "+self.job_name+" - Job Description: "+self.job_description+" - In Progress: "+str(self.is_in_progress)+" - Finished: "+str(self.is_finished)

# ---------------- Flask Forms -------------------------
class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    surname = StringField('Surname', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Passsword',validators=[DataRequired()])
    submit = SubmitField('Sign In')

class PasswordChangeForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    new_password = PasswordField('New Password',validators=[DataRequired()])
    new_password_confirm = PasswordField("Confirm Password", validators=[DataRequired()])
    submit = SubmitField('Save Changes')

class UpdateUserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    surname = StringField('Surname', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Save Changes')

class ProjectForm(FlaskForm):
    project_name = StringField("Project Name: ",validators=[DataRequired()])
    project_description = TextAreaField("Project Description: ",validators=[DataRequired()])
    submit = SubmitField('Add This Project')

class JobUpdateForm(FlaskForm):
    job_name = StringField("Job Name: ",validators=[DataRequired()])
    job_description = TextAreaField("Job Description: ",validators=[DataRequired()])
    is_in_progress = BooleanField("Change in Progress")
    is_finished = BooleanField("Change Finished")
    submit = SubmitField('Save Changes')

class JobAddForm(FlaskForm):
    job_name = StringField("Job Name: ",validators=[DataRequired()])
    job_description = TextAreaField("Job Description: ",validators=[DataRequired()])
    submit = SubmitField('Save Changes')
    
# ---------------- API Design -------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@appi.route("/")
def index():
    return render_template("index.html")

@appi.route("/register",methods=["GET","POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if form.password.data==form.confirm_password.data:
            user = User(form.name.data,form.surname.data,form.email.data,form.password.data)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for("login"))
    return render_template("register.html",form=form)

@appi.route("/login",methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(User.email==form.email.data).first()
        password_hash = user.password
        if check_password_hash(password_hash,form.password.data):
            session["user_id"] = user.id
            login_user(user)
            return redirect(url_for("user_index"))
    return render_template("login.html",form=form)

@appi.route("/user_index")
@login_required
def user_index():
    user = User.query.filter(User.id==session.get("user_id")).first()
    name_surname = user.name +" "+ user.surname
    return render_template("user/user_index.html",name_surname=name_surname)

@appi.route("/projects")
@login_required
def show_projects(): # Tüm Projeleri göster
    session["project_id"]=None
    user_id=session.get("user_id")
    projects = Project.query.filter_by(user_id=session.get("user_id")).with_entities(Project.project_name,Project.id, Project.project_description).all()
    return render_template("user/projects.html",projects=projects)

@appi.route("/add_new_project",methods=["GET","POST"])
@login_required
def add_new_project():
    form = ProjectForm()
    if form.validate_on_submit():
        project_name = form.project_name.data
        project_description=form.project_description.data
        user_id=session.get("user_id")
        project = Project(project_name,project_description,user_id)
        db.session.add(project)
        db.session.commit()
        # project_temp = Project.query.order_by(Project.project_id.desc()).first()
        # json_data = jsonify({'project_id': project_temp.id, 'project_name': project.project_name,'project_description': project.project_description,'user_id':project.user_id})
        # redis_client.set(f"projects:{user_id}",json_data)
        return redirect(url_for("show_projects"))
    return render_template("user/add_new_project.html",form=form)

@appi.route("/my_project/<int:project_id>")
@login_required
def my_project(project_id):
    session["project_id"]=project_id
    jobs = Job.query.filter_by(project_id=project_id).all()
    print(jobs)
    undone_jobs=[]
    in_progress_jobs=[]
    finished_jobs=[]
    for job in jobs:
        if job.is_in_progress==False and job.is_finished==False:
            undone_jobs.append((job.id,job.job_name))
        elif job.is_in_progress==True and job.is_finished==False:
            in_progress_jobs.append((job.id,job.job_name))
        elif job.is_in_progress==False and job.is_finished==True:
            finished_jobs.append((job.id,job.job_name))    
    return render_template("user/my_project.html",undone_jobs=undone_jobs,in_progress_jobs=in_progress_jobs,finished_jobs=finished_jobs)

@appi.route("/my_project/jobs/<int:job_id>")
@login_required
def details(job_id):
    cached_data = redis_client.get(f"jobs:{job_id}")
    if cached_data:
        job = json.loads(cached_data)
        print(job)
        message= "Data From Cache"
    else:
        job = Job.query.filter_by(id=job_id).first()
        data = {'id':job_id,'job_name':job.job_name,'job_description':job.job_description,'is_in_progress':job.is_in_progress,'is_finished':job.is_finished}
        json_data = json.dumps(data)
        redis_client.setex(f"jobs:{job_id}",60,json_data)
        message="Veri Düz alındı" 
    return render_template("user/details.html",job=job,message=message)

@appi.route("/my_project/jobs/update/<int:job_id>",methods=["GET","POST"])
@login_required
def update_job(job_id):
    form = JobUpdateForm()
    job = Job.query.filter_by(id=job_id).first()
    if form.validate_on_submit():
        # redis_client.delete(f"jobs:{job_id}")
        job.job_name=form.job_name.data
        job.job_description=form.job_description.data
        job.is_in_progress = form.is_in_progress.data
        job.is_finished = form.is_finished.data
        db.session.commit()
        data = {'id':job_id,'job_name':job.job_name,'job_description':job.job_description,'is_in_progress':job.is_in_progress,'is_finished':job.is_finished}
        json_data = json.dumps(data)
        redis_client.setex(f"jobs:{job_id}",60,json_data)
        return redirect(url_for("my_project",project_id=session.get("project_id")))
    return render_template("user/update_job.html",job=job,form=form)

@appi.route("/logout")
@login_required
def logout():
    logout_user()
    session["user_id"]=None
    return redirect(url_for("login"))

@appi.route("/update_user",methods=["GET","POST"])
@login_required
def update_user():
    form = UpdateUserForm()
    user = User.query.filter_by(id=session.get("user_id")).first()
    if form.validate_on_submit():
        user.name=form.name.data
        user.surname=form.surname.data
        user.email=form.email.data
        db.session.commit()
        return redirect(url_for("user_index"))
    return render_template("user/update_user.html",user=user,form=form)

@appi.route("/update_user/change_password",methods=["GET","POST"])
@login_required
def change_password():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        user = User.query.filter_by(id=session.get("user_id")).first()
        if check_password_hash(user.password,form.old_password.data):
            if form.new_password==form.new_password_confirm:
                user.password = generate_password_hash(form.new_password.data)
                db.session.commit()
                return redirect(url_for("user_index"))
    return render_template("user/change_password.html",form=form)

@appi.route("/my_project/add_new_job", methods=["GET","POST"])
@login_required
def add_new_job():
    form = JobAddForm()
    if form.validate_on_submit():
        job_name=form.job_name.data
        job_description=form.job_description.data
        job = Job(job_name,job_description,session.get("project_id"))
        db.session.add(job)
        db.session.commit()
        job_temp = Job.query.order_by(Job.id.desc()).first()
        print(job_temp)
        data = {'id':job_temp.id,'job_name':job.job_name,'job_description':job.job_description,'is_in_progress':job.is_in_progress,'is_finished':job.is_finished}
        job_id = int(job_temp.id)
        json_data = json.dumps(data)
        redis_client.set(f"jobs:{job_id}",json_data)
        return redirect(url_for("my_project",project_id=session.get("project_id")))
    return render_template("user/add_new_job.html",form=form)

@appi.route("/delete_project/<int:project_id>")
@login_required
def delete_project(project_id):
    project = Project.query.filter_by(id=project_id).first()
    jobs=Job.query.filter_by(id=project_id).all()
    for job in jobs:
        db.session.delete(job)
    redis_client.delete(f"jobs:{project_id}")
    redis_client.delete(f"projects:{project_id}")
    db.session.delete(project)
    db.session.commit()
    return redirect(url_for("show_projects"))
    
@appi.route("/delete_job/<int:job_id>")
@login_required
def delete_job(job_id):    
    job = Job.query.filter_by(id=job_id).first()
    redis_client.delete(f"jobs:{job_id}")
    db.session.delete(job)
    db.session.commit()
    return redirect(url_for("my_project",project_id=session.get("project_id")))
    
if __name__=="__main__":
    db.create_all()
    appi.run()
