import datetime
from email import message
from attr import validate
from app import app
from io import BytesIO
from flask_mail import Mail, Message
from datetime import date
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
from flask import Flask, render_template,  redirect, url_for, session, request, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app.forms import SearchUser, LoginForm, AddUserForm, ChangePasswordForm, JobRequest, Jobapply, SendEmail
from app import db
from app.models import User, job_posting, applicants
import sys

mail = Mail(app)
# app = Flask(__name__)

@app.route('/')
def index():
    session['name'] = 'not logged in'
    if current_user.is_authenticated:
        session['name'] = current_user.fname +' '+ current_user.lname 
        return render_template('index.html')
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Authenticated users are redirected to home page.
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        # Query DB for user by username
        users = db.session.query(User).filter_by(username=form.username.data).first()
        if users is None or not users.check_password(form.password.data):
            print('Login failed', file=sys.stderr)
            return redirect(url_for('login'))
        login_user(users)
        # login_user is a flask_login function that starts a session
        print('Login successful', file=sys.stderr)
        return redirect(url_for('index'))
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = AddUserForm()
    if form.validate_on_submit():
        name = form.username.data
        fname = form.fname.data
        lname = form.lname.data
        email = form.email.data
        number = form.phone.data
        role = form.role.data
        pas = form.password.data
        #Query database to check username and email exist
        user = db.session.query(User).filter_by(username=name).first()
        em = db.session.query(User).filter_by(email=email).first()
        
        if user is None and em is None:
            #add email message
            # msg = MIMEMultipart('alternative')
            subject = 'Collaborative Information Center'
            message = '''
                This is a message to {fname} {lname} from Collaborative Information Center letting you know your registered
                Your username is {username} 
                Your phone number is {number}
                You signed up as a {role} 
            '''.format(fname=fname,lname=lname,username=name,number=number,role=role)
            
            # part2 = MIMEText(message, 'html')
            # msg.attach(part2)
            msg = Message(subject, recipients=[email], body = message)
            mail.send(msg)

            new = User(username=name,email=email,role=role,fname=fname,lname=lname,blocked=False)
            new.set_password(pas)
            db.session.add(new)
            db.session.commit()
            print('user created successfully')
            return redirect(url_for('index'))                
        else:
            print('Username or email already exists')
            return redirect(url_for('register'))

    return render_template('register.html', form=form)

@app.route('/Jrequest', methods=['GET', 'POST'])
@login_required
def Jrequest():
    form = JobRequest()
    if form.validate_on_submit():
        name = current_user.id
        pos = form.position.data
        end = form.end_date.data
        comp = form.company.data

        email = current_user.email
        fname = current_user.fname
        lname = current_user.lname
        today = today = date.today()
        subject = 'Job Request for {pos}'.format(pos=pos)
        message = '''
                Collaborative Information Center
                This is a message to {fname} {lname} from Collaborative Information Center letting you know about job
                Company name is {comp}
                This job was posted on {today}
                This job will expire on {end} meaning noone will be alowed to apply afterwards
            '''.format(fname=fname,lname=lname,comp=comp,today=today,end=end)
            
        msg = Message(subject, recipients=[email], body = message)
        mail.send(msg)

        p = job_posting(position=pos, end_time=end, user=name, company=comp)

        db.session.add(p)
        db.session.commit()

        return redirect(url_for('Jrequest'))
    return render_template('request.html', form=form)

@app.route('/apply/<id>', methods=['GET', 'POST'])
@login_required
def apply(id):
    form = apply
    session['id'] = id
    if request.method == 'POST':
        res = request.files['file']
        inf = request.form['info']
        add = request.form.get('address')

        job = db.session.query(job_posting).filter_by(jobid=id).first()        
        host = db.session.query(User).filter_by(user=job.user).first()
        comp = job.company
        pos = job.position
        end = job.end_time
        end = end.date()
        email = host.email
        fname = current_user.fname
        lname = current_user.lname
        today = today = date.today()
        subject = '{pos}'.format(pos=pos)
        message = '''
                Collaborative Information Center
                This is a message to {hfname} {hlname} from Collaborative Information Center 
                To let you know that {fname} {lname} is applying to this job 
                From this comapny {comp}
                This user applied to this job on {today}
                This job will expire on {end} meaning noone will be alowed to apply afterwards
            '''.format(fname=fname,lname=lname,today=today,end=end,hfname=host.fname, hlname=host.lname, comp=comp)
            
        msg = Message(subject, recipients=[email], body = message)
        mail.send(msg)

        a = applicants(JpostID=id, information=inf, employee=current_user.id, address=add, fileName = res.filename, resume=res.read())
        
        db.session.add(a)
        db.session.commit()
        return redirect(url_for('index'))
        
    return render_template('apply.html', form=form)

@app.route('/jobs', methods=['GET', 'POST'])
@login_required
def jobs():
    form = jobs
    current_time = datetime.datetime.utcnow()
    data = job_posting.query.with_entities(job_posting.position, job_posting.begin_time, job_posting.end_time, job_posting.company, job_posting.jobid)
    session['role'] = current_user.role
    session['now'] = current_time
    if request.method == 'POST':  
        if request.form.get('jobID') != 0:
            x = (request.form.get('jobID'))
            id = int(x)
            return redirect(url_for('apply', id=id))
    else:
        return render_template('jobs.html', form=form, data=data)
    return render_template('jobs.html', data=data)

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if not current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ChangePasswordForm()
    if form.new_pass.data == form.new_pass_retype.data:
        if form.validate_on_submit():
            users = db.session.query(User).filter_by(role = current_user.role).first()
            check_pass = users.check_password(form.old_pass.data)
            if check_pass:                            
                users.set_password(form.new_pass.data)                 
                db.session.commit()
                print('Password changed successfully', file=sys.stderr)
                return redirect(url_for('index'))
            else:
                print('Wrong Password Change failed', file=sys.stderr)
                return redirect(url_for('change_password'))
    else:
        print('new password not the same', file=sys.stderr)
        return redirect(url_for('change_passsword'))
    return render_template('change_password.html', form = form)

@app.route('/applications', methods=['GET', 'POST'])
def applications():
    job_data = []
    # session['view'] = False
    # session['delete'] = False
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            job_data = db.session.query(job_posting).all()
            return render_template("applications.html", data = job_data)
        else:
            job_data = db.session.query(job_posting).filter_by(user = current_user.id).all()
            # job_data = db.session.query(job_posting).all()
            return render_template("applications.html", data = job_data)
    return render_template('invalid_access.html')

@app.route('/view_applications', methods=['GET', 'POST'])
@login_required
def view_applications():
    form = apply
    session['id'] = request.form.get("jobid")
    id = request.form.get("jobid")
    try:
        if request.form['view'] == 'View Applications':
            pos = request.form.get("position")
            job_applications = db.session.query(applicants, User).select_from(applicants).filter_by(JpostID = id).join(User, User.id == applicants.employee).all()
            # files = send_file(BytesIO(job_applications.resume), attachment_filename=job_applications.fileName, as_attachment=True)
            # count = 0
            job_post = db.session.query(job_posting).filter_by(jobid = id).first()
            # for applicants,User in job_applications:
            #     x = job_applications.applicants.resume
            #     files[count]
            #     count+=1
            return render_template('job_applications.html', data = job_applications, post = job_post.position)
            # return render_template('job_applications.html', resumes=files, data = job_applications, post = job_post.position)
    except KeyError:
        pass
    if request.form['delete'] == 'Delete':
        db.session.query(job_posting).filter_by(jobid=id).delete()
        db.session.query(applicants).filter_by(JpostID=id).delete()
        db.session.commit()
        return redirect(url_for('index'))
    return "Error"



@app.route('/mail', methods=['GET', 'POST'])
def send_mail():
    mail_form = SendEmail()
    if mail_form.validate_on_submit():
        recipient = mail_form.email.data
        message = mail_form.message.data
        subject = 'Test Flask email'
        message = 'Testing'
        msg = Message(subject, recipients=[recipient], body = message)
        mail.send(msg)
        mail_form.email.data = ''
        mail_form.message.data = ''
    return render_template('mail.html', form=mail_form)


@app.route('/search_user/<id>', methods=['GET', 'POST'])
def search_by_name():
    form = SearchUser()
    if form.validate_on_submit():
        # Query DB table for matching name
        record = db.session.query(User).filter_by(Username = form.user.data).all()
        if record:
            return render_template('view_users.html', users=record)
        else:
            return render_template('not_found.html')
    return render_template('search.html', form=form)


# if __name__ == '__main__':
#     app.run(app, debug=True)