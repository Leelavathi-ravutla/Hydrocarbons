from flask import Flask, render_template, request, flash, jsonify,get_flashed_messages,Response,session,redirect,url_for
import numpy as np
import pickle
import pandas as pd
import mysql.connector
from flask_session import Session
from key import secret_key,salt,salt2
from itsdangerous import URLSafeTimedSerializer
from stoken import token
from cmail import sendmail
import mysql.connector.pooling


app = Flask(__name__)
app.secret_key = b'filesystem'
app.config['SESSION_TYPE']='filesystem'

conn=mysql.connector.pooling.MySQLConnectionPool(host='localhost',user='root',password="admin",db='skin',pool_name='DED',pool_size=3, pool_reset_session=True)

try:
    mydb=conn.get_connection()
    cursor = mydb.cursor(buffered=True)
    cursor.execute('CREATE TABLE IF NOT EXISTS users (uid INT PRIMARY KEY auto_increment, username VARCHAR(50), password VARCHAR(15), email VARCHAR(60))')

except Exception as e:
    print(e)
finally:
    if mydb.is_connected():
        mydb.close()

# Giving the Label Encoded Values and Original Values in a dictionary format and assgining it to a variable. 
Parameter_Code  = {
"FDS" : 0,"TDS" : 1,"TSS" : 2,}

Analysis_Method_Code  = {
"FDS-G-105" : 0,"TDS-G-105" : 1,"TSS-G" : 2,}

Quality  = {
0:"Fair",1:"Poor",2:"Suspect",}

# Loading the Model pickle file
model =  pickle.load(open('dtree.pkl','rb'))


@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('username'):
        return redirect(url_for('index'))
    if request.method=='POST':
        print(request.form)
        name=request.form['name']
        password=request.form['password']
        try:
            mydb=conn.get_connection()
            cursor=mydb.cursor(buffered=True)
        except Exception as e:
            print(e)
        else:
            cursor.execute('SELECT count(*) from users where username=%s and password=%s',[name,password])
            count=cursor.fetchone()[0]
            cursor.close()
            if count==1:
                session['username']=name
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password')
                return render_template('login.html')
        finally:
            if mydb.is_connected():
                mydb.close()
    return render_template('login.html')

@app.route('/registration',methods=['GET','POST'])
def registration():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        try:
            mydb=conn.get_connection()
            cursor=mydb.cursor(buffered=True)
        except Exception as e:
            print(e)
        else:
            cursor.execute('SELECT COUNT(*) FROM users WHERE username = %s', [username])
            count=cursor.fetchone()[0]
            cursor.execute('select count(*) from users where email=%s',[email])
            count1=cursor.fetchone()[0]
            cursor.close()
            if count==1:
                flash('username already in use')
                return render_template('registration.html')
            elif count1==1:
                flash('Email already in use')
                return render_template('registration.html')
            data={'username':username,'password':password,'email':email}
            subject='Email Confirmation'
            body=f"Thanks for signing up\n\nfollow this link for further steps-{url_for('confirm',token=token(data,salt),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('Confirmation link sent to mail')
            return redirect(url_for('login'))
        finally:
            if mydb.is_connected():
                mydb.close()
    return render_template('registration.html')

@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt,max_age=180)
    except Exception as e:
        #print(e)
        return 'Link Expired register again'
    else:
        try:
            mydb=conn.get_connection()
            cursor=mydb.cursor(buffered=True)
        except Exception as e:
            print(e)
        else:
            username=data['username']
            cursor.execute('select count(*) from users where username=%s',[username])
            count=cursor.fetchone()[0]
            if count==1:
                cursor.close()
                flash('You are already registerterd!')
                return redirect(url_for('login'))
            else:
                cursor.execute('insert into users(username,password,email) values(%s,%s,%s)',(data['username'], data['password'], data['email']))
                mydb.commit()
                cursor.close()
                flash('Details registered!')
                return redirect(url_for('login'))
        finally:
            if mydb.is_connected():
                mydb.close()


@app.route('/forget',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        try:
            mydb=conn.get_connection()
            cursor=mydb.cursor(buffered=True)
        except Exception as e:
            print(e)
        else:
            cursor.execute('select count(*) from users where email=%s',[email])
            count=cursor.fetchone()[0]
            cursor.close()
            if count==1:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('SELECT email from users where email=%s',[email])
                status=cursor.fetchone()[0]
                cursor.close()
                subject='Forget Password'
                confirm_link=url_for('reset',token=token(email,salt=salt2),_external=True)
                body=f"Use this link to reset your password-\n\n{confirm_link}"
                sendmail(to=email,body=body,subject=subject)
                flash('Reset link sent check your email')
                return redirect(url_for('login'))
            else:
                flash('Invalid email id')
                return render_template('forgot.html')
        finally:
            if mydb.is_connected():
                mydb.close()
    return render_template('forgot.html')


@app.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Link Expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                try:
                    mydb=conn.get_connection()
                    cursor=mydb.cursor(buffered=True)
                except Exception as e:
                    print(e)
                else:
                    cursor.execute('update users set password=%s where email=%s',[newpassword,email])
                    mydb.commit()
                    flash('Reset Successful')
                    return redirect(url_for('login'))
                finally:
                    if mydb.is_connected():
                        mydb.close()
            else:
                flash('Passwords mismatched')
                return render_template('newpassword.html')
        return render_template('newpassword.html')

@app.route('/logout')
def logout():
    if session.get('username'):
        session.pop('username')
        flash('Successfully logged out')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))

# Creating the function funtion to accept inputs and creating an 2d array and predicting the result.
@app.route('/',methods=['GET','POST'])
def index():
    if session.get('username'):
        if request.method == 'POST':
            depth = float(request.form['depth'])
            parameter_code = int(request.form['parameter'])
            analysis_method_code = int(request.form['analysis'])
            value = float(request.form['value'])

            user_input = np.array([[depth,parameter_code,analysis_method_code,value]])
            result = Quality[model.predict(user_input)[0]]
            return render_template('index.html',Parameter_Code=Parameter_Code,Analysis_Method_Code=Analysis_Method_Code,result=result)
        return render_template('index.html',Parameter_Code=Parameter_Code,Analysis_Method_Code=Analysis_Method_Code)
    else:
        return redirect(url_for('login'))

@app.route('/result/<results>')
def result(results):
    if session.get('username'):
        water_quality_details = {
        "Fair": {
            "agriculture": "Water of fair quality can generally be used for irrigation without significant negative effects on crop growth.",
            "drinking": "Fair quality water may require treatment before consumption to remove contaminants and ensure it meets safe drinking water standards."
        },
        "Poor": {
            "agriculture": "Water of poor quality may have adverse effects on crop growth and soil health if used for irrigation without proper management.",
            "drinking": "Poor quality water is not suitable for drinking without extensive treatment to remove contaminants and ensure safety."
        },
        "Suspect": {
            "agriculture": "Water quality that is suspect may pose risks to crop health and soil quality if used for irrigation. It is advisable to assess and monitor water quality closely.",
            "drinking": "Suspect water quality indicates potential contamination and should not be used for drinking without thorough testing and treatment to ensure safety."
        }
    }

        display = water_quality_details[results]
        return render_template('fair.html',display=display)
    else:
        return redirect(url_for('login'))

if __name__=="__main__":
    app.run(use_reloader=True,debug=True)